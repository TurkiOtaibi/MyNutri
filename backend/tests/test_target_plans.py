from datetime import date, datetime, timedelta, timezone
import inspect
from uuid import UUID

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import PrincipalContext, get_principal_context
from app.core.calendar import diary_calendar_authority
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.models import (
    DefaultUnitType,
    DiaryEntry,
    Food,
    IdempotencyRecord,
    IdempotencyState,
    LegacyTargetTransitionSnapshot,
    NutritionBasis,
    NutritionDataSource,
    Principal,
    Profile,
    TargetPlan,
    TargetProvenance,
    UnitBasis,
    utcnow,
)
from app.schemas import ProfileUpsert, TargetPlanWriteRequest
from app.services import diary as diary_service
from app.services.profile import to_profile_response
from app.services.target_plans import (
    _legacy_hash,
    resolve_target_binding,
    resolve_week_target_context,
    target_for_date,
)

PRINCIPAL_A = UUID("00000000-0000-0000-0000-00000000000a")
PRINCIPAL_B = UUID("00000000-0000-0000-0000-00000000000b")
TODAY = date(2026, 7, 16)


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

    def override_principal(request: Request) -> PrincipalContext:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        return PrincipalContext(PRINCIPAL_B if token == "token-b" else PRINCIPAL_A)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_principal_context] = override_principal
    fixed_authority = diary_calendar_authority(
        datetime(2026, 7, 15, 21, 0, 0, tzinfo=timezone.utc)
    )
    monkeypatch.setattr(
        "app.services.target_plans.current_diary_date", lambda: TODAY
    )
    monkeypatch.setattr(
        "app.api.routes.target_plans.current_diary_date", lambda: TODAY
    )
    monkeypatch.setattr(
        "app.api.routes.profile.diary_calendar_authority", lambda: fixed_authority
    )
    monkeypatch.setattr(
        "app.services.aggregation.diary_calendar_authority", lambda: fixed_authority
    )
    monkeypatch.setattr(
        "app.api.routes.diary.diary_calendar_authority", lambda: fixed_authority
    )
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def headers(token: str = "token-a", key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {token}"}
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def preview(
    client: TestClient,
    payload: dict,
    effective_from: date = TODAY,
    token: str = "token-a",
) -> dict:
    response = client.post(
        "/profile/preview",
        json=payload | {"effective_from": effective_from.isoformat()},
        headers=headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def write_plan(
    client: TestClient,
    payload: dict,
    key: str,
    *,
    effective_from: date = TODAY,
    token: str = "token-a",
):
    result = preview(client, payload, effective_from, token)
    body = payload | {
        "effective_from": effective_from.isoformat(),
        "confirmed": True,
        "expected_preview_hash": result["preview_hash"],
    }
    return client.post(
        "/target-plans",
        json=body,
        headers=headers(token, key),
    )


def seed_legacy_profile(
    session: Session,
    payload: dict | None = None,
    principal_id: UUID = PRINCIPAL_A,
) -> dict:
    validated = ProfileUpsert.model_validate(payload or profile_payload())
    data = validated.model_dump()
    data["cut_intensity"] = data.pop("selected_cut_intensity")
    profile = Profile(principal_id=principal_id, **data)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return to_profile_response(profile, TODAY).model_dump(mode="json")


def seed_food(session: Session, principal_id: UUID = PRINCIPAL_A) -> Food:
    food = Food(
        principal_id=principal_id,
        name="Target binding food",
        normalized_name="target binding food",
        primary_category="other",
        subcategory="other",
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.g,
        unit_amount=1,
        unit_basis=UnitBasis.g,
        calories=100,
        protein_g=1,
        carb_g=2,
        fat_g=3,
        nutrition_data_source=NutritionDataSource.estimated,
    )
    session.add(food)
    session.commit()
    return food


def create_diary_entry(
    client: TestClient,
    food: Food,
    entry_date: date,
    token: str = "token-a",
):
    response = client.post(
        "/diary/entries",
        json={
            "food_id": str(food.id),
            "entry_date": entry_date.isoformat(),
            "quantity": 1,
            "meal_type": "breakfast",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response


def test_diary_create_preserves_principal_then_target_then_food_lock_order() -> None:
    source = inspect.getsource(diary_service.create_entry)
    symbols = [
        "_lock_owner_for_target_binding(",
        "resolve_target_binding(",
        "lock_food_namespace_for_logging(",
        "get_active_food_for_logging(",
    ]
    offsets = [source.index(symbol) for symbol in symbols]
    assert offsets == sorted(offsets)


def test_first_plan_can_be_effective_today(target_plan_context) -> None:
    client, session = target_plan_context
    response = write_plan(client, profile_payload(), "today")

    assert response.status_code == 201, response.text
    assert response.json()["plan"]["effective_from"] == TODAY.isoformat()
    assert response.json()["plan"]["revision"] == 1
    assert response.json()["replaced_plan"] is None
    assert set(response.json()["plan"]) == {
        "id",
        "effective_from",
        "revision",
        "targets",
        "created_at",
    }
    plan = session.exec(select(TargetPlan)).one()
    assert plan.revision == 1
    assert session.exec(select(Profile)).one().weight_kg == 80


def test_multiple_future_points_resolve_by_date(target_plan_context) -> None:
    client, _ = target_plan_context
    first_date = TODAY + timedelta(days=2)
    second_date = TODAY + timedelta(days=5)
    first = write_plan(client, profile_payload(80), "future-1", effective_from=first_date)
    second = write_plan(client, profile_payload(85), "future-2", effective_from=second_date)
    assert first.status_code == second.status_code == 201

    before = client.get(
        f"/target-plans/current?date={(TODAY + timedelta(days=1)).isoformat()}",
        headers=headers(),
    ).json()
    middle = client.get(
        f"/target-plans/current?date={(TODAY + timedelta(days=4)).isoformat()}",
        headers=headers(),
    ).json()
    after = client.get(
        f"/target-plans/current?date={(TODAY + timedelta(days=8)).isoformat()}",
        headers=headers(),
    ).json()
    assert before["plan"] is None
    assert middle["plan"]["id"] == first.json()["plan"]["id"]
    assert after["plan"]["id"] == second.json()["plan"]["id"]


def test_same_date_write_inserts_immutable_revision(target_plan_context) -> None:
    client, session = target_plan_context
    effective = TODAY + timedelta(days=2)
    first = write_plan(client, profile_payload(80), "revision-1", effective_from=effective)
    second = write_plan(client, profile_payload(84), "revision-2", effective_from=effective)

    assert first.status_code == second.status_code == 201
    assert second.json()["plan"]["revision"] == 2
    assert second.json()["replaced_plan"]["id"] == first.json()["plan"]["id"]
    assert second.json()["replaced_plan"]["revision"] == 1
    plans = session.exec(
        select(TargetPlan).order_by(TargetPlan.revision)
    ).all()
    assert [plan.revision for plan in plans] == [1, 2]
    assert [plan.calculation_document["profile_inputs"]["weight_kg"] for plan in plans] == [80, 84]

    current = client.get(
        f"/target-plans/current?date={effective.isoformat()}", headers=headers()
    )
    assert current.json()["plan"]["id"] == second.json()["plan"]["id"]


def test_past_write_is_rejected_atomically(target_plan_context) -> None:
    client, session = target_plan_context
    past = TODAY - timedelta(days=1)
    result = preview(client, profile_payload(), past)
    response = client.post(
        "/target-plans",
        json=profile_payload()
        | {
            "effective_from": past.isoformat(),
            "confirmed": True,
            "expected_preview_hash": result["preview_hash"],
        },
        headers=headers(key="past"),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TARGET_PLAN_EFFECTIVE_DATE_PAST"
    assert session.exec(select(TargetPlan)).all() == []
    assert session.exec(select(Profile)).all() == []
    assert session.exec(select(IdempotencyRecord)).all() == []


def test_midnight_boundary_rolls_back_every_write(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    dates = iter([TODAY, TODAY + timedelta(days=1)])
    monkeypatch.setattr(
        "app.services.target_plans._database_riyadh_date", lambda _session: next(dates)
    )
    response = write_plan(client, profile_payload(), "midnight")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TARGET_PLAN_DATE_BOUNDARY_CHANGED"
    assert session.exec(select(TargetPlan)).all() == []
    assert session.exec(select(Profile)).all() == []
    assert session.exec(select(IdempotencyRecord)).all() == []


def test_future_rebinding_uses_the_complete_affected_interval(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    seed_legacy_profile(session)
    food = seed_food(session)
    dates = [
        TODAY - timedelta(days=1),
        TODAY,
        TODAY + timedelta(days=1),
        TODAY + timedelta(days=3),
        TODAY + timedelta(days=4),
    ]
    entries = [create_diary_entry(client, food, value).json() for value in dates]
    later = write_plan(
        client,
        profile_payload(85),
        "later",
        effective_from=TODAY + timedelta(days=3),
    ).json()["plan"]
    earlier = write_plan(
        client,
        profile_payload(82),
        "earlier",
        effective_from=TODAY,
    ).json()["plan"]

    bound = {
        entry.entry_date: entry.target_plan_id
        for entry in session.exec(select(DiaryEntry)).all()
    }
    assert bound[dates[0]] is None
    assert str(bound[dates[1]]) == earlier["id"]
    assert str(bound[dates[2]]) == earlier["id"]
    assert str(bound[dates[3]]) == later["id"]
    assert str(bound[dates[4]]) == later["id"]
    assert entries[0]["target_provenance"] == "legacy_unversioned"


def test_same_date_revision_rebinds_today_and_future_only(target_plan_context) -> None:
    client, session = target_plan_context
    seed_legacy_profile(session)
    food = seed_food(session)
    past = create_diary_entry(client, food, TODAY - timedelta(days=1)).json()
    today = create_diary_entry(client, food, TODAY).json()
    first = write_plan(client, profile_payload(80), "same-1").json()["plan"]
    second = write_plan(client, profile_payload(83), "same-2").json()["plan"]

    rows = {str(row.id): row for row in session.exec(select(DiaryEntry)).all()}
    assert rows[past["id"]].target_plan_id is None
    assert str(rows[today["id"]].target_plan_id) == second["id"]
    assert first["id"] != second["id"]


def test_diary_create_binds_highest_revision_for_its_date(target_plan_context) -> None:
    client, session = target_plan_context
    first = write_plan(client, profile_payload(80), "bind-1").json()["plan"]
    second = write_plan(client, profile_payload(82), "bind-2").json()["plan"]
    food = seed_food(session)
    created = create_diary_entry(client, food, TODAY)
    assert created.json()["target_plan_id"] == second["id"]
    assert created.json()["target_plan_id"] != first["id"]


def test_new_namespace_idempotency_replays_clean_response(target_plan_context) -> None:
    client, session = target_plan_context
    result = preview(client, profile_payload(), TODAY)
    body = profile_payload() | {
        "effective_from": TODAY.isoformat(),
        "confirmed": True,
        "expected_preview_hash": result["preview_hash"],
    }
    first = client.post("/target-plans", json=body, headers=headers(key="replay"))
    replay = client.post("/target-plans", json=body, headers=headers(key="replay"))

    assert first.status_code == replay.status_code == 201
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json() == first.json()
    assert len(session.exec(select(TargetPlan)).all()) == 1
    record = session.exec(select(IdempotencyRecord)).one()
    assert record.operation == "target_plan.write"


def test_legacy_activation_replay_is_rehydrated_even_after_date_becomes_past(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    result = preview(client, profile_payload(), TODAY)
    body = profile_payload() | {
        "effective_from": TODAY.isoformat(),
        "confirmed": True,
        "expected_preview_hash": result["preview_hash"],
    }
    created = client.post(
        "/target-plans", json=body, headers=headers(key="legacy-replay")
    )
    plan = session.exec(select(TargetPlan)).one()
    current_record = session.exec(select(IdempotencyRecord)).one()
    session.delete(current_record)
    request = TargetPlanWriteRequest.model_validate(body)
    session.add(
        IdempotencyRecord(
            principal_id=PRINCIPAL_A,
            operation="target_plan.activate",
            idempotency_key="legacy-replay",
            request_hash=_legacy_hash(request, "target_plan.activate"),
            state=IdempotencyState.completed,
            response_status=201,
            response_document={
                "plan": {
                    "id": str(plan.id),
                    "effective_from": TODAY.isoformat(),
                    "status": "active",
                },
                "replaced_plan": None,
            },
            resource_type="target_plan",
            resource_id=plan.id,
            completed_at=utcnow(),
            expires_at=utcnow() + timedelta(days=1),
        )
    )
    session.commit()
    monkeypatch.setattr(
        "app.services.target_plans._database_riyadh_date",
        lambda _session: TODAY + timedelta(days=1),
    )

    replay = client.post(
        "/target-plans", json=body, headers=headers(key="legacy-replay")
    )
    assert created.status_code == replay.status_code == 201
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["plan"]["id"] == str(plan.id)
    assert "status" not in replay.json()["plan"]
    assert len(session.exec(select(TargetPlan)).all()) == 1


def test_ambiguous_legacy_replay_fails_closed(target_plan_context) -> None:
    client, session = target_plan_context
    created = write_plan(client, profile_payload(), "seed")
    plan = session.exec(select(TargetPlan)).one()
    session.delete(session.exec(select(IdempotencyRecord)).one())
    result = preview(client, profile_payload(), TODAY)
    body = profile_payload() | {
        "effective_from": TODAY.isoformat(),
        "confirmed": True,
        "expected_preview_hash": result["preview_hash"],
    }
    request = TargetPlanWriteRequest.model_validate(body)
    now = utcnow()
    for operation in ("target_plan.activate", "target_plan.replace"):
        session.add(
            IdempotencyRecord(
                principal_id=PRINCIPAL_A,
                operation=operation,
                idempotency_key="ambiguous",
                request_hash=_legacy_hash(request, operation),
                state=IdempotencyState.completed,
                response_status=201,
                response_document={"plan": {"id": str(plan.id)}, "replaced_plan": None},
                resource_type="target_plan",
                resource_id=plan.id,
                completed_at=now,
                expires_at=now + timedelta(days=1),
            )
        )
    session.commit()

    response = client.post(
        "/target-plans", json=body, headers=headers(key="ambiguous")
    )
    assert created.status_code == 201
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_REPLAY_AMBIGUOUS"
    assert len(session.exec(select(TargetPlan)).all()) == 1


def test_legacy_snapshot_bridges_until_first_future_plan(target_plan_context) -> None:
    client, session = target_plan_context
    legacy = seed_legacy_profile(session, profile_payload(78))
    effective = TODAY + timedelta(days=5)
    plan = write_plan(
        client, profile_payload(85), "transition", effective_from=effective
    )
    assert plan.status_code == 201
    snapshot = session.exec(select(LegacyTargetTransitionSnapshot)).one()
    assert snapshot.transition_date == TODAY

    before = client.get(
        f"/target-plans/current?date={(TODAY + timedelta(days=3)).isoformat()}",
        headers=headers(),
    ).json()
    on_date = client.get(
        f"/target-plans/current?date={effective.isoformat()}", headers=headers()
    ).json()
    assert before["target_source_detail"] == "legacy_transition_snapshot"
    assert before["targets"]["target_calories"] == legacy["targets"]["target_calories"]
    assert on_date["plan"]["id"] == plan.json()["plan"]["id"]


def test_first_future_plan_creates_transition_snapshot_for_new_profile(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    effective = TODAY + timedelta(days=5)

    response = write_plan(
        client, profile_payload(85), "new-profile-transition", effective_from=effective
    )

    assert response.status_code == 201
    snapshot = session.exec(select(LegacyTargetTransitionSnapshot)).one()
    assert snapshot.transition_date == TODAY
    before = client.get(
        f"/target-plans/current?date={(TODAY + timedelta(days=3)).isoformat()}",
        headers=headers(),
    ).json()
    assert before["target_source_detail"] == "legacy_transition_snapshot"


def test_legacy_profile_fallback_remains_date_bounded(target_plan_context) -> None:
    _, session = target_plan_context
    seed_legacy_profile(session)
    principal = PrincipalContext(PRINCIPAL_A)
    today = resolve_target_binding(
        session, principal, TODAY, authoritative_current_date=TODAY
    )
    future = resolve_target_binding(
        session,
        principal,
        TODAY + timedelta(days=1),
        authoritative_current_date=TODAY,
    )
    assert today.provenance == TargetProvenance.legacy_unversioned
    assert today.profile is not None
    assert future.provenance == TargetProvenance.no_target_source


def test_week_context_uses_one_bounded_plan_query_and_canonical_revisions(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    first = write_plan(client, profile_payload(80), "week-1").json()["plan"]
    second = write_plan(client, profile_payload(82), "week-2").json()["plan"]
    write_plan(
        client,
        profile_payload(85),
        "week-next",
        effective_from=TODAY + timedelta(days=3),
    )
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        context = resolve_week_target_context(
            session,
            PrincipalContext(PRINCIPAL_A),
            TODAY,
            TODAY + timedelta(days=6),
            authoritative_current_date=TODAY,
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    plan_queries = [
        statement
        for statement in statements
        if "FROM target_plan" in statement and statement.lstrip().upper().startswith("SELECT")
    ]
    assert len(plan_queries) == 1
    assert target_for_date(context, TODAY).plan.id == UUID(second["id"])
    assert target_for_date(context, TODAY).plan.id != UUID(first["id"])


def test_profile_current_and_week_reads_execute_no_dml_or_commit(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    write_plan(client, profile_payload(), "read-only")
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.strip().upper())

    def forbidden_commit() -> None:
        raise AssertionError("Target Plan read committed")

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    monkeypatch.setattr(session, "commit", forbidden_commit)
    try:
        assert client.get("/profile", headers=headers()).status_code == 200
        assert client.get("/target-plans/current", headers=headers()).status_code == 200
        assert (
            client.get(
                f"/diary/week?start={TODAY.isoformat()}", headers=headers()
            ).status_code
            == 200
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not any(
        statement.startswith(("INSERT", "UPDATE", "DELETE")) for statement in statements
    )


def test_history_is_revision_ordered_and_cursor_stable(target_plan_context) -> None:
    client, _ = target_plan_context
    write_plan(client, profile_payload(80), "history-1")
    write_plan(client, profile_payload(82), "history-2")
    write_plan(
        client,
        profile_payload(84),
        "history-3",
        effective_from=TODAY + timedelta(days=2),
    )

    first = client.get("/target-plans?limit=2", headers=headers())
    second = client.get(
        "/target-plans",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
        headers=headers(),
    )
    assert [item["effective_from"] for item in first.json()["items"]] == [
        (TODAY + timedelta(days=2)).isoformat(),
        TODAY.isoformat(),
    ]
    assert first.json()["items"][1]["revision"] == 2
    assert second.json()["items"][0]["revision"] == 1
    assert client.get(
        "/target-plans", params={"cursor": "bad"}, headers=headers()
    ).status_code == 422


def test_target_plan_reads_are_principal_scoped(target_plan_context) -> None:
    client, _ = target_plan_context
    write_plan(client, profile_payload(), "private", token="token-a")
    assert client.get("/target-plans", headers=headers("token-b")).json()["items"] == []
    current = client.get("/target-plans/current", headers=headers("token-b")).json()
    assert current["plan"] is None
    assert current["targets"] is None


def test_retired_routes_and_contract_fields_are_absent(target_plan_context) -> None:
    client, _ = target_plan_context
    for method, path in (
        ("POST", "/target-plans/activate"),
        ("POST", "/target-plans/pending/replace"),
        ("GET", "/target-plans/pending"),
    ):
        response = client.request(method, path, headers=headers())
        assert response.status_code == 404

    schema = app.openapi()
    assert "/target-plans/activate" not in schema["paths"]
    assert "/target-plans/pending/replace" not in schema["paths"]
    assert "/target-plans/pending" not in schema["paths"]
    summary = schema["components"]["schemas"]["TargetPlanSummary"]["properties"]
    assert set(summary) == {"id", "effective_from", "revision", "targets", "created_at"}
    assert "targets" not in schema["components"]["schemas"]["WeekSummary"]["properties"]


def test_profile_response_has_no_pending_plan(target_plan_context) -> None:
    client, _ = target_plan_context
    write_plan(client, profile_payload(), "profile-contract")
    response = client.get("/profile", headers=headers())
    assert response.status_code == 200
    assert "pending_plan" not in response.json()
    assert response.json()["effective_plan"]["revision"] == 1
