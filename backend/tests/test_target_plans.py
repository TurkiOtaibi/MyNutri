from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import Settings, get_settings
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.main import app
from app.models import (
    DiaryEntry,
    IdempotencyRecord,
    LegacyTargetTransitionSnapshot,
    Principal,
    Profile,
    TargetPlan,
    TargetProvenance,
)

PRINCIPAL_A = UUID("00000000-0000-0000-0000-00000000000a")
PRINCIPAL_B = UUID("00000000-0000-0000-0000-00000000000b")
TODAY = date(2026, 7, 16)
TOMORROW = date(2026, 7, 17)


def profile_payload(weight: float = 80, intensity: float = 0.2) -> dict:
    return {
        "sex": "male",
        "birth_date": "1990-01-01",
        "height_cm": 175,
        "weight_kg": weight,
        "activity_level": "moderate",
        "goal": "cut",
        "protein_per_kg": 1.2,
        "fat_pct": 0.25,
        "selected_cut_intensity": intensity,
    }


@pytest.fixture
def target_plan_context(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Principal(id=PRINCIPAL_A))
    session.add(Principal(id=PRINCIPAL_B))
    session.commit()
    settings = Settings(
        environment="test",
        principal_token_map={"token-a": PRINCIPAL_A, "token-b": PRINCIPAL_B},
        calendar_timezone="Asia/Riyadh",
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.services.target_plans.current_diary_date", lambda: TODAY)
    monkeypatch.setattr("app.services.target_plans.next_diary_date", lambda: TOMORROW)
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def headers(token: str, key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {token}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def preview(client: TestClient, payload: dict, token: str = "token-a") -> dict:
    response = client.post("/profile/preview", json=payload, headers=headers(token))
    assert response.status_code == 200, response.text
    return response.json()


def activate(client: TestClient, payload: dict, key: str, token: str = "token-a"):
    result = preview(client, payload, token)
    body = {**payload, "confirmed": True, "expected_preview_hash": result["preview_hash"]}
    return client.post("/target-plans/activate", json=body, headers=headers(token, key))


def test_current_legacy_profile_target_is_available_before_transition(
    target_plan_context,
) -> None:
    client, _ = target_plan_context
    created = client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    source = client.get(
        f"/target-plans/current?date={TODAY.isoformat()}", headers=headers("token-a")
    )
    assert source.status_code == 200
    assert source.json()["target_provenance"] == "legacy_unversioned"
    assert source.json()["target_source_detail"] == "no_preserved_target_source"
    assert source.json()["targets"] == created.json()["targets"]


def test_existing_legacy_activation_preserves_today_and_updates_profile_atomically(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    original = profile_payload(weight=80)
    created = client.put("/profile", json=original, headers=headers("token-a"))
    assert created.status_code == 200
    before = created.json()["targets"]

    changed = profile_payload(weight=90, intensity=0.25)
    response = activate(client, changed, "legacy-first")
    assert response.status_code == 201, response.text
    assert response.json()["plan"]["effective_from"] == TOMORROW.isoformat()
    assert response.json()["plan"]["status"] == "scheduled"

    profile = client.get("/profile", headers=headers("token-a")).json()
    assert profile["weight_kg"] == 90
    assert profile["selected_cut_intensity"] == 0.25
    today = client.get(
        f"/target-plans/current?date={TODAY.isoformat()}", headers=headers("token-a")
    ).json()
    assert today["target_source_detail"] == "legacy_transition_snapshot"
    assert today["target_provenance"] == "legacy_unversioned"
    assert today["targets"]["final_target_calories"] == before["final_target_calories"]
    tomorrow = client.get(
        f"/target-plans/current?date={TOMORROW.isoformat()}", headers=headers("token-a")
    ).json()
    assert tomorrow["target_source_detail"] == "effective_target_plan"
    assert tomorrow["targets"]["final_target_calories"] == response.json()["plan"]["targets"]["final_target_calories"]
    previous = client.get("/target-plans/current?date=2026-07-15", headers=headers("token-a")).json()
    assert previous["target_provenance"] == "no_target_source"
    assert previous["targets"] is None
    assert len(session.exec(select(LegacyTargetTransitionSnapshot)).all()) == 1


def test_idempotent_replay_and_payload_conflict_do_not_mutate(target_plan_context) -> None:
    client, session = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    payload = profile_payload(weight=82)
    result = preview(client, payload)
    body = {**payload, "confirmed": True, "expected_preview_hash": result["preview_hash"]}
    first = client.post("/target-plans/activate", json=body, headers=headers("token-a", "same"))
    replay = client.post("/target-plans/activate", json=body, headers=headers("token-a", "same"))
    assert first.status_code == replay.status_code == 201
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert first.json() == replay.json()

    other = profile_payload(weight=83)
    other_preview = preview(client, other)
    conflict = client.post(
        "/target-plans/activate",
        json={**other, "confirmed": True, "expected_preview_hash": other_preview["preview_hash"]},
        headers=headers("token-a", "same"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert len(session.exec(select(TargetPlan)).all()) == 1
    assert len(session.exec(select(LegacyTargetTransitionSnapshot)).all()) == 1


def test_idempotency_key_requires_visible_ascii(target_plan_context) -> None:
    client, session = target_plan_context
    payload = profile_payload()
    result = preview(client, payload)
    response = client.post(
        "/target-plans/activate",
        json={**payload, "confirmed": True, "expected_preview_hash": result["preview_hash"]},
        headers=headers("token-a", "contains space"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert session.exec(select(TargetPlan)).all() == []


def test_pending_replacement_reuses_original_transition_snapshot(target_plan_context) -> None:
    client, session = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert activate(client, profile_payload(weight=82), "first").status_code == 201
    snapshot = session.exec(select(LegacyTargetTransitionSnapshot)).one()
    original_document = snapshot.legacy_target_document.copy()

    replacement_payload = profile_payload(weight=84)
    result = preview(client, replacement_payload)
    response = client.post(
        "/target-plans/pending/replace",
        json={
            **replacement_payload,
            "replace_confirmed": True,
            "expected_preview_hash": result["preview_hash"],
        },
        headers=headers("token-a", "replace"),
    )
    assert response.status_code == 201, response.text
    assert response.json()["replaced_plan"]["status"] == "superseded_before_effective"
    session.refresh(snapshot)
    assert snapshot.legacy_target_document == original_document
    assert len(session.exec(select(LegacyTargetTransitionSnapshot)).all()) == 1
    assert len(session.exec(select(TargetPlan)).all()) == 2


def test_history_uses_an_opaque_stable_cursor(target_plan_context) -> None:
    client, _ = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert activate(client, profile_payload(weight=82), "first").status_code == 201
    replacement_payload = profile_payload(weight=84)
    replacement_preview = preview(client, replacement_payload)
    replacement = client.post(
        "/target-plans/pending/replace",
        json={
            **replacement_payload,
            "replace_confirmed": True,
            "expected_preview_hash": replacement_preview["preview_hash"],
        },
        headers=headers("token-a", "replace"),
    )
    assert replacement.status_code == 201

    first_page = client.get("/target-plans?limit=1", headers=headers("token-a"))
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["next_cursor"]
    second_page = client.get(
        "/target-plans",
        params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
        headers=headers("token-a"),
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]
    assert second_page.json()["next_cursor"] is None

    invalid = client.get(
        "/target-plans", params={"cursor": "not-a-cursor"}, headers=headers("token-a")
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_CURSOR"


def test_new_profile_activates_today_without_transition_snapshot(target_plan_context) -> None:
    client, session = target_plan_context
    snapshot = {
        "name": "Before activation",
        "calories": 100,
        "protein_g": 1,
        "carb_g": 2,
        "fat_g": 3,
    }
    entry = DiaryEntry(
        principal_id=PRINCIPAL_B,
        entry_date=TODAY,
        quantity=1,
        target_provenance=TargetProvenance.no_target_source,
        nutrition_snapshot=snapshot,
    )
    session.add(entry)
    session.commit()
    response = activate(client, profile_payload(), "new", token="token-b")
    assert response.status_code == 201, response.text
    assert response.json()["plan"]["status"] == "active"
    assert response.json()["plan"]["effective_from"] == TODAY.isoformat()
    assert session.exec(
        select(LegacyTargetTransitionSnapshot).where(
            LegacyTargetTransitionSnapshot.principal_id == PRINCIPAL_B
        )
    ).first() is None
    assert session.exec(select(Profile).where(Profile.principal_id == PRINCIPAL_B)).one()
    session.refresh(entry)
    assert entry.target_provenance == TargetProvenance.versioned_plan
    assert str(entry.target_plan_id) == response.json()["plan"]["id"]
    assert entry.nutrition_snapshot == snapshot


def test_preview_hash_rejects_stale_activation_without_partial_persistence(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    payload = profile_payload(weight=88)
    body = {**payload, "confirmed": True, "expected_preview_hash": "0" * 64}
    response = client.post("/target-plans/activate", json=body, headers=headers("token-a", "bad"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PREVIEW_RESULT_CHANGED"
    assert len(session.exec(select(TargetPlan)).all()) == 0
    assert len(session.exec(select(LegacyTargetTransitionSnapshot)).all()) == 0
    assert float(session.exec(select(Profile)).one().weight_kg) == 80


def test_target_plan_reads_are_principal_scoped(target_plan_context) -> None:
    client, _ = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert activate(client, profile_payload(weight=82), "private").status_code == 201
    assert client.get("/target-plans/pending", headers=headers("token-b")).json() is None
    assert client.get("/target-plans", headers=headers("token-b")).json()["items"] == []
    source = client.get(
        f"/target-plans/current?date={TOMORROW.isoformat()}", headers=headers("token-b")
    ).json()
    assert source["target_provenance"] == "no_target_source"
    assert source["plan"] is None


def test_transaction_failure_rolls_back_snapshot_profile_plan_and_idempotency(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    changed = profile_payload(weight=95)
    result = preview(client, changed)
    body = {**changed, "confirmed": True, "expected_preview_hash": result["preview_hash"]}
    real_commit = session.commit

    def fail_commit() -> None:
        raise RuntimeError("injected transaction failure")

    monkeypatch.setattr(session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="injected transaction failure"):
        client.post("/target-plans/activate", json=body, headers=headers("token-a", "fail"))
    monkeypatch.setattr(session, "commit", real_commit)
    session.expire_all()
    assert float(session.exec(select(Profile)).one().weight_kg) == 80
    assert session.exec(select(TargetPlan)).all() == []
    assert session.exec(select(LegacyTargetTransitionSnapshot)).all() == []
    assert session.exec(select(IdempotencyRecord)).all() == []


def test_riyadh_midnight_is_the_authoritative_activation_boundary() -> None:
    assert current_diary_date(datetime(2026, 7, 16, 20, 59, 59, tzinfo=timezone.utc)) == date(
        2026, 7, 16
    )
    assert current_diary_date(datetime(2026, 7, 16, 21, 0, 0, tzinfo=timezone.utc)) == date(
        2026, 7, 17
    )
