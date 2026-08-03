from datetime import date, datetime, timedelta, timezone
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import Settings, get_settings
from app.core.auth import PrincipalContext, get_principal_context
from app.core.calendar import current_diary_date, diary_calendar_authority
from app.db.session import get_session
from app.main import app
from app.models import (
    DiaryEntry,
    IdempotencyRecord,
    LegacyTargetTransitionSnapshot,
    Principal,
    Profile,
    TargetPlan,
    TargetPlanStatus,
    TargetProvenance,
)
from app.services.target_plans import (
    project_targets,
    project_week_target_context,
    target_for_date,
)
from app.schemas import ProfileResponse, ProfileUpsert
from app.services.profile import upsert_profile

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
    def override_principal(request: Request) -> PrincipalContext:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        return PrincipalContext(PRINCIPAL_B if token == "token-b" else PRINCIPAL_A)

    app.dependency_overrides[get_principal_context] = override_principal
    fixed_authority = diary_calendar_authority(
        datetime(2026, 7, 15, 21, 0, 0, tzinfo=timezone.utc)
    )
    monkeypatch.setattr(
        "app.services.target_plans.diary_calendar_authority", lambda: fixed_authority
    )
    monkeypatch.setattr("app.services.target_plans.current_diary_date", lambda: TODAY)
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


def _profile_state(profile: Profile) -> tuple:
    return (
        profile.sex,
        profile.birth_date,
        float(profile.height_cm),
        float(profile.weight_kg),
        profile.activity_level,
        profile.goal,
        float(profile.protein_per_kg),
        float(profile.fat_pct),
        float(profile.cut_intensity),
        profile.updated_at,
    )


@pytest.mark.parametrize("failure_point", ["calculation", "serialization", "flush", "commit"])
@pytest.mark.parametrize("existing", [False, True])
def test_plan008_profile_upsert_rolls_back_every_failure(
    target_plan_context, monkeypatch, failure_point: str, existing: bool
) -> None:
    client, session = target_plan_context
    principal_id = PRINCIPAL_A if existing else PRINCIPAL_B
    principal = PrincipalContext(principal_id)
    before = None
    if existing:
        created = client.put(
            "/profile", json=profile_payload(weight=80), headers=headers("token-a")
        )
        assert created.status_code == 200
        stored = session.exec(
            select(Profile).where(Profile.principal_id == principal_id)
        ).one()
        before = _profile_state(stored)

    payload = ProfileUpsert.model_validate(profile_payload(weight=92))

    def fail(*args, **kwargs):
        raise RuntimeError(f"injected {failure_point} failure")

    with monkeypatch.context() as patch:
        if failure_point == "calculation":
            patch.setattr("app.services.profile.calculate_targets", fail)
        elif failure_point == "serialization":
            patch.setattr(ProfileResponse, "model_validate", classmethod(fail))
        elif failure_point == "flush":
            patch.setattr(session, "flush", fail)
        else:
            patch.setattr(session, "commit", fail)

        with pytest.raises(RuntimeError, match=f"injected {failure_point} failure"):
            upsert_profile(session, principal, payload, TODAY)

    session.expire_all()
    stored_after = session.exec(
        select(Profile).where(Profile.principal_id == principal_id)
    ).first()
    if existing:
        assert stored_after is not None
        assert _profile_state(stored_after) == before
    else:
        assert stored_after is None


def preview(client: TestClient, payload: dict, token: str = "token-a") -> dict:
    response = client.post("/profile/preview", json=payload, headers=headers(token))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("height_cm", 100),
        ("height_cm", 250),
        ("weight_kg", 20),
        ("weight_kg", 300),
        ("protein_per_kg", 1.0),
        ("protein_per_kg", 3.0),
        ("fat_pct", 0.15),
        ("fat_pct", 0.40),
    ],
)
def test_plan008_valid_profile_boundaries_save(
    target_plan_context, field: str, value: float
) -> None:
    client, session = target_plan_context
    response = client.put(
        "/profile",
        json=profile_payload() | {field: value},
        headers=headers("token-a"),
    )

    assert response.status_code == 200, response.text
    stored = session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).one()
    stored_field = "cut_intensity" if field == "selected_cut_intensity" else field
    assert float(getattr(stored, stored_field)) == value


@pytest.mark.parametrize(
    ("field", "value", "error_type"),
    [
        ("height_cm", 99.9, "greater_than_equal"),
        ("height_cm", 250.1, "less_than_equal"),
        ("weight_kg", 19.9, "greater_than_equal"),
        ("weight_kg", 300.1, "less_than_equal"),
        ("protein_per_kg", 0.9, "greater_than_equal"),
        ("protein_per_kg", 3.1, "less_than_equal"),
        ("fat_pct", 0.14, "greater_than_equal"),
        ("fat_pct", 0.41, "less_than_equal"),
    ],
)
def test_plan008_invalid_numeric_requests_return_422_without_profile(
    target_plan_context, field: str, value: float, error_type: str
) -> None:
    client, session = target_plan_context
    response = client.put(
        "/profile",
        json=profile_payload() | {field: value},
        headers=headers("token-a"),
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", field]
    assert error["type"] == error_type
    assert error["msg"]
    assert session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).first() is None


@pytest.mark.parametrize("path", ["/profile", "/profile/preview"])
@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_plan008_non_finite_raw_json_returns_stable_422_without_profile(
    target_plan_context, path: str, constant: str
) -> None:
    client, session = target_plan_context
    payload = json.dumps(profile_payload(), separators=(",", ":"))
    payload = payload.replace('"height_cm":175', f'"height_cm":{constant}')

    response = client.request(
        "PUT" if path == "/profile" else "POST",
        path,
        content=payload,
        headers={**headers("token-a"), "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == [
        {
            "type": "finite_number",
            "loc": ["body", "height_cm"],
            "msg": "Input should be a finite number",
            "input": constant,
        }
    ]
    assert session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).first() is None


@pytest.mark.parametrize(
    ("birth_date", "error_type"),
    [
        ("2020-07-28", "profile_age_below_minimum"),
        ("1920-07-26", "profile_age_above_maximum"),
        ("2031-01-01", "profile_birth_date_future"),
    ],
)
def test_plan008_invalid_birth_dates_return_422_without_profile(
    target_plan_context, monkeypatch, birth_date: str, error_type: str
) -> None:
    client, session = target_plan_context
    authority = type(
        "Authority",
        (),
        {
            "current_diary_date": date(2030, 7, 27),
            "calendar_timezone": "Asia/Riyadh",
            "next_rollover_at": datetime(2030, 7, 28, tzinfo=timezone.utc),
        },
    )()
    monkeypatch.setattr(
        "app.api.routes.profile.diary_calendar_authority", lambda: authority
    )
    response = client.put(
        "/profile",
        json=profile_payload() | {"birth_date": birth_date},
        headers=headers("token-a"),
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "birth_date"]
    assert error["type"] == error_type
    assert error["msg"]
    assert session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).first() is None


def activate(client: TestClient, payload: dict, key: str, token: str = "token-a"):
    result = preview(client, payload, token)
    body = {**payload, "confirmed": True, "expected_preview_hash": result["preview_hash"]}
    return client.post("/target-plans/activate", json=body, headers=headers(token, key))


@pytest.mark.parametrize(("token", "existing_profile"), [("token-b", False), ("token-a", True)])
def test_plan010_activation_captures_one_calendar_authority(
    target_plan_context, monkeypatch, token: str, existing_profile: bool
) -> None:
    client, _ = target_plan_context
    if existing_profile:
        saved = client.put("/profile", json=profile_payload(), headers=headers(token))
        assert saved.status_code == 200

    fixed = diary_calendar_authority(
        datetime(2026, 7, 15, 21, 0, 0, tzinfo=timezone.utc)
    )
    calls = 0

    def authority():
        nonlocal calls
        calls += 1
        return fixed

    monkeypatch.setattr("app.services.target_plans.diary_calendar_authority", authority)

    response = activate(client, profile_payload(weight=82), f"plan010-{token}", token)

    assert response.status_code == 201, response.text
    assert calls == 1


@pytest.mark.parametrize(
    ("token", "existing_profile", "expected_effective_from"),
    [
        ("token-b", False, date(2026, 12, 31)),
        ("token-a", True, date(2027, 1, 1)),
    ],
)
def test_plan010_midnight_crossing_cannot_skip_an_effective_date(
    target_plan_context,
    monkeypatch,
    token: str,
    existing_profile: bool,
    expected_effective_from: date,
) -> None:
    client, session = target_plan_context
    if existing_profile:
        saved = client.put("/profile", json=profile_payload(), headers=headers(token))
        assert saved.status_code == 200

    before_midnight = diary_calendar_authority(
        datetime(2026, 12, 30, 21, 0, 0, tzinfo=timezone.utc)
    )
    after_midnight = diary_calendar_authority(
        datetime(2026, 12, 31, 21, 0, 0, tzinfo=timezone.utc)
    )
    calls = 0

    def crossing_authority():
        nonlocal calls
        authority = before_midnight if calls == 0 else after_midnight
        calls += 1
        return authority

    monkeypatch.setattr(
        "app.api.routes.profile.diary_calendar_authority", lambda: before_midnight
    )
    monkeypatch.setattr(
        "app.services.target_plans.diary_calendar_authority", crossing_authority
    )

    response = activate(client, profile_payload(weight=82), f"midnight-{token}", token)

    assert response.status_code == 201, response.text
    assert calls == 1
    assert response.json()["plan"]["effective_from"] == expected_effective_from.isoformat()
    transitions = session.exec(
        select(LegacyTargetTransitionSnapshot).where(
            LegacyTargetTransitionSnapshot.principal_id
            == (PRINCIPAL_A if existing_profile else PRINCIPAL_B)
        )
    ).all()
    if existing_profile:
        assert len(transitions) == 1
        assert transitions[0].transition_date == before_midnight.current_diary_date
    else:
        assert transitions == []


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


def test_project_targets_selects_due_plan_without_lifecycle_dml(
    target_plan_context,
) -> None:
    client, session = target_plan_context

    fallback = client.put(
        "/profile", json=profile_payload(weight=67), headers=headers("token-b")
    )
    assert fallback.status_code == 200
    fallback_source = project_targets(
        session, PrincipalContext(PRINCIPAL_B), TODAY
    )
    assert fallback_source.target_source_detail == "no_preserved_target_source"
    assert fallback_source.targets is not None
    assert fallback_source.targets.model_dump(mode="json") == fallback.json()["targets"]

    created = client.put(
        "/profile", json=profile_payload(weight=80), headers=headers("token-a")
    )
    assert created.status_code == 200
    activation = activate(client, profile_payload(weight=82), "due-plan")
    assert activation.status_code == 201, activation.text
    due = session.exec(
        select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_A)
    ).one()
    assert due.status == TargetPlanStatus.scheduled
    lifecycle_before = (
        due.status,
        due.effective_to,
        due.activated_at,
        due.closed_at,
        due.superseded_at,
    )

    due_source = project_targets(session, PrincipalContext(PRINCIPAL_A), TOMORROW)
    assert due_source.target_source_detail == "effective_target_plan"
    assert due_source.plan is not None
    assert str(due_source.plan.id) == activation.json()["plan"]["id"]
    assert due_source.targets == due_source.plan.targets
    session.refresh(due)
    assert (
        due.status,
        due.effective_to,
        due.activated_at,
        due.closed_at,
        due.superseded_at,
    ) == lifecycle_before

    transition_source = project_targets(
        session, PrincipalContext(PRINCIPAL_A), TODAY
    )
    assert transition_source.target_source_detail == "legacy_transition_snapshot"
    assert transition_source.targets is not None
    transition_targets = transition_source.targets.model_dump(
        mode="json", exclude={"preview_hash"}
    )
    expected_transition_targets = created.json()["targets"].copy()
    expected_transition_targets.pop("preview_hash")
    assert transition_targets == expected_transition_targets

    no_source = project_targets(
        session,
        PrincipalContext(UUID("00000000-0000-0000-0000-00000000000c")),
        date(2026, 7, 15),
    )
    assert no_source.target_provenance == "no_target_source"
    assert no_source.targets is None


def test_plan015_bulk_context_matches_single_date_projection(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    created = client.put(
        "/profile", json=profile_payload(weight=80), headers=headers("token-a")
    )
    assert created.status_code == 200
    fallback_context = project_week_target_context(
        session,
        PrincipalContext(PRINCIPAL_A),
        TODAY,
        TOMORROW,
    )
    fallback_today = target_for_date(fallback_context, TODAY)
    fallback_tomorrow = target_for_date(fallback_context, TOMORROW)
    assert fallback_today.target_source_detail == "no_preserved_target_source"
    assert fallback_today.targets is not None
    assert fallback_today.targets.model_dump(mode="json") == created.json()["targets"]
    assert fallback_tomorrow.target_provenance == "no_target_source"

    activation = activate(client, profile_payload(weight=82), "plan015-bulk")
    assert activation.status_code == 201, activation.text

    week_start = TODAY - timedelta(days=2)
    week_end = week_start + timedelta(days=6)
    dates = [week_start + timedelta(days=offset) for offset in range(7)]
    expected = {
        requested: project_targets(
            session, PrincipalContext(PRINCIPAL_A), requested
        ).model_dump(mode="json")
        for requested in dates
    }

    context = project_week_target_context(
        session,
        PrincipalContext(PRINCIPAL_A),
        week_start,
        week_end,
    )
    actual = {
        requested: target_for_date(context, requested).model_dump(mode="json")
        for requested in dates
    }

    assert actual == expected
    assert actual[TODAY]["target_source_detail"] == "legacy_transition_snapshot"
    assert actual[TOMORROW]["target_source_detail"] == "effective_target_plan"
    assert actual[week_start]["target_provenance"] == "no_target_source"


def test_plan015_out_of_week_transition_blocks_profile_fallback_without_loading_history(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    created = client.put(
        "/profile", json=profile_payload(weight=80), headers=headers("token-a")
    )
    assert created.status_code == 200
    activation = activate(client, profile_payload(weight=82), "plan015-history")
    assert activation.status_code == 201, activation.text
    template_profile = session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).one()
    template_transition = session.exec(
        select(LegacyTargetTransitionSnapshot).where(
            LegacyTargetTransitionSnapshot.principal_id == PRINCIPAL_A
        )
    ).one()

    # The schema permits one transition per Profile. Extra historical rows for
    # other Principals verify that neither result size nor query count grows.
    extra_profiles = []
    for _ in range(20):
        principal_id = uuid4()
        session.add(Principal(id=principal_id))
        extra_profiles.append(
            Profile(
                principal_id=principal_id,
                sex=template_profile.sex,
                birth_date=template_profile.birth_date,
                height_cm=template_profile.height_cm,
                weight_kg=template_profile.weight_kg,
                activity_level=template_profile.activity_level,
                goal=template_profile.goal,
                protein_per_kg=template_profile.protein_per_kg,
                fat_pct=template_profile.fat_pct,
                cut_intensity=template_profile.cut_intensity,
            )
        )
    session.flush()
    session.add_all(extra_profiles)
    session.flush()
    for offset, profile in enumerate(extra_profiles, start=30):
        session.add(
            LegacyTargetTransitionSnapshot(
                principal_id=profile.principal_id,
                profile_id=profile.id,
                transition_date=TODAY - timedelta(days=offset),
                calendar_timezone="Asia/Riyadh",
                target_document_schema_version=1,
                legacy_target_document=template_transition.legacy_target_document,
            )
        )
    session.commit()

    week_start = TODAY - timedelta(days=14)
    week_end = week_start + timedelta(days=6)
    statements: list[str] = []
    engine = session.get_bind()

    def capture(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        if statement.lstrip().lower().startswith("select "):
            statements.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", capture)
    try:
        context = project_week_target_context(
            session,
            PrincipalContext(PRINCIPAL_A),
            week_start,
            week_end,
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert len(statements) == 4
    assert context.transitions_by_date == {}
    assert context.has_transition is True
    for offset in range(7):
        requested = week_start + timedelta(days=offset)
        bulk = target_for_date(context, requested)
        single = project_targets(
            session, PrincipalContext(PRINCIPAL_A), requested
        )
        assert bulk.model_dump(mode="json") == single.model_dump(mode="json")
        assert bulk.target_provenance == "no_target_source"
        assert bulk.targets is None


def test_plan015_bulk_context_matches_active_closed_and_scheduled_boundaries(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    active_response = activate(
        client,
        profile_payload(weight=75),
        "plan015-active",
        token="token-b",
    )
    assert active_response.status_code == 201, active_response.text

    active_context = project_week_target_context(
        session,
        PrincipalContext(PRINCIPAL_B),
        TODAY,
        TODAY + timedelta(days=6),
    )
    active_source = target_for_date(active_context, TODAY)
    assert active_source.plan is not None
    assert str(active_source.plan.id) == active_response.json()["plan"]["id"]

    scheduled_response = activate(
        client,
        profile_payload(weight=77),
        "plan015-scheduled",
        token="token-b",
    )
    assert scheduled_response.status_code == 201, scheduled_response.text
    plans = session.exec(
        select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_B)
    ).all()
    closed = next(plan for plan in plans if plan.status == TargetPlanStatus.active)
    scheduled = next(
        plan for plan in plans if plan.status == TargetPlanStatus.scheduled
    )
    closed.status = TargetPlanStatus.closed
    closed.effective_from = TODAY - timedelta(days=2)
    closed.effective_to = TOMORROW
    closed.closed_at = datetime.now(timezone.utc)
    session.add(closed)
    session.commit()

    week_start = TODAY - timedelta(days=2)
    week_end = week_start + timedelta(days=6)
    context = project_week_target_context(
        session,
        PrincipalContext(PRINCIPAL_B),
        week_start,
        week_end,
    )
    actual = {
        requested: target_for_date(context, requested).model_dump(mode="json")
        for requested in (week_start, TODAY, TOMORROW, week_end)
    }
    expected = {
        requested: project_targets(
            session, PrincipalContext(PRINCIPAL_B), requested
        ).model_dump(mode="json")
        for requested in actual
    }

    assert actual == expected
    assert actual[TODAY]["plan"]["id"] == str(closed.id)
    assert actual[TOMORROW]["plan"]["id"] == str(scheduled.id)


def test_owner_current_get_advances_due_target_lifecycle(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    active_response = activate(
        client, profile_payload(weight=80), "owner-active", token="token-b"
    )
    assert active_response.status_code == 201, active_response.text
    scheduled_response = activate(
        client, profile_payload(weight=82), "owner-scheduled", token="token-b"
    )
    assert scheduled_response.status_code == 201, scheduled_response.text

    plans = session.exec(
        select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_B)
    ).all()
    active = next(plan for plan in plans if plan.status == TargetPlanStatus.active)
    scheduled = next(
        plan for plan in plans if plan.status == TargetPlanStatus.scheduled
    )
    active.effective_from = TODAY - timedelta(days=1)
    assert active.effective_to is None
    assert active.closed_at is None
    assert scheduled.effective_from == TOMORROW
    assert scheduled.activated_at is None
    session.add(active)
    session.commit()

    monkeypatch.setattr(
        "app.services.target_plans.current_diary_date", lambda: TOMORROW
    )
    response = client.get(
        f"/target-plans/current?date={TOMORROW.isoformat()}",
        headers=headers("token-b"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["plan"]["id"] == str(scheduled.id)

    session.refresh(active)
    session.refresh(scheduled)
    assert active.status == TargetPlanStatus.closed
    assert active.effective_to == TOMORROW
    assert active.closed_at is not None
    assert scheduled.status == TargetPlanStatus.active
    assert scheduled.activated_at is not None
    assert scheduled.closed_at is None
    assert active.closed_at == scheduled.activated_at


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


def test_plan021_activation_and_replacement_complete_operation_ledgers(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    saved = client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert saved.status_code == 200

    activation_payload = profile_payload(weight=82)
    activation_preview = preview(client, activation_payload)
    activation_body = {
        **activation_payload,
        "confirmed": True,
        "expected_preview_hash": activation_preview["preview_hash"],
    }
    activation = client.post(
        "/target-plans/activate",
        json=activation_body,
        headers=headers("token-a", "plan021-activate-ledger"),
    )
    assert activation.status_code == 201, activation.text

    replacement_payload = profile_payload(weight=84)
    replacement_preview = preview(client, replacement_payload)
    replacement_body = {
        **replacement_payload,
        "replace_confirmed": True,
        "expected_preview_hash": replacement_preview["preview_hash"],
    }
    replacement = client.post(
        "/target-plans/pending/replace",
        json=replacement_body,
        headers=headers("token-a", "plan021-replace-ledger"),
    )
    assert replacement.status_code == 201, replacement.text

    session.expire_all()
    records = {
        record.operation: record
        for record in session.exec(
            select(IdempotencyRecord).where(
                IdempotencyRecord.principal_id == PRINCIPAL_A
            )
        ).all()
    }
    assert set(records) == {"target_plan.activate", "target_plan.replace"}
    for operation, response in (
        ("target_plan.activate", activation),
        ("target_plan.replace", replacement),
    ):
        record = records[operation]
        assert record.state == "completed"
        assert record.response_status == 201
        assert record.response_document == response.json()
        assert record.resource_type == "target_plan"
        assert str(record.resource_id) == response.json()["plan"]["id"]
        assert record.completed_at is not None

    activation_replay = client.post(
        "/target-plans/activate",
        json=activation_body,
        headers=headers("token-a", "plan021-activate-ledger"),
    )
    replacement_replay = client.post(
        "/target-plans/pending/replace",
        json=replacement_body,
        headers=headers("token-a", "plan021-replace-ledger"),
    )
    assert activation_replay.status_code == replacement_replay.status_code == 201
    assert activation_replay.headers["Idempotent-Replayed"] == "true"
    assert replacement_replay.headers["Idempotent-Replayed"] == "true"
    assert activation_replay.json() == activation.json()
    assert replacement_replay.json() == replacement.json()
    assert len(session.exec(select(TargetPlan)).all()) == 2
    assert len(session.exec(select(LegacyTargetTransitionSnapshot)).all()) == 1
    assert len(session.exec(select(IdempotencyRecord)).all()) == 2


def test_plan021_same_visible_key_is_independent_across_operations(
    target_plan_context,
) -> None:
    client, session = target_plan_context
    saved = client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert saved.status_code == 200
    shared_key = "plan021-shared-operation-key"

    activation_payload = profile_payload(weight=82)
    activation_preview = preview(client, activation_payload)
    activation_body = {
        **activation_payload,
        "confirmed": True,
        "expected_preview_hash": activation_preview["preview_hash"],
    }
    activation = client.post(
        "/target-plans/activate",
        json=activation_body,
        headers=headers("token-a", shared_key),
    )
    assert activation.status_code == 201, activation.text

    replacement_payload = profile_payload(weight=84)
    replacement_preview = preview(client, replacement_payload)
    replacement_body = {
        **replacement_payload,
        "replace_confirmed": True,
        "expected_preview_hash": replacement_preview["preview_hash"],
    }
    replacement = client.post(
        "/target-plans/pending/replace",
        json=replacement_body,
        headers=headers("token-a", shared_key),
    )
    assert replacement.status_code == 201, replacement.text

    session.expire_all()
    profile_before_replays = _profile_state(
        session.exec(select(Profile).where(Profile.principal_id == PRINCIPAL_A)).one()
    )
    plans_before_replays = tuple(
        sorted(
            (
                str(plan.id),
                str(plan.status),
                str(plan.predecessor_plan_id),
                str(plan.superseded_by_plan_id),
            )
            for plan in session.exec(
                select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_A)
            ).all()
        )
    )
    transition_before_replays = session.exec(
        select(LegacyTargetTransitionSnapshot).where(
            LegacyTargetTransitionSnapshot.principal_id == PRINCIPAL_A
        )
    ).one()
    transition_document_before_replays = transition_before_replays.legacy_target_document.copy()

    activation_replay = client.post(
        "/target-plans/activate",
        json=activation_body,
        headers=headers("token-a", shared_key),
    )
    replacement_replay = client.post(
        "/target-plans/pending/replace",
        json=replacement_body,
        headers=headers("token-a", shared_key),
    )
    assert activation_replay.status_code == replacement_replay.status_code == 201
    assert activation_replay.headers["Idempotent-Replayed"] == "true"
    assert replacement_replay.headers["Idempotent-Replayed"] == "true"
    assert activation_replay.json() == activation.json()
    assert replacement_replay.json() == replacement.json()

    changed_activation = profile_payload(weight=86)
    changed_activation_preview = preview(client, changed_activation)
    activation_conflict = client.post(
        "/target-plans/activate",
        json={
            **changed_activation,
            "confirmed": True,
            "expected_preview_hash": changed_activation_preview["preview_hash"],
        },
        headers=headers("token-a", shared_key),
    )
    changed_replacement = profile_payload(weight=88)
    changed_replacement_preview = preview(client, changed_replacement)
    replacement_conflict = client.post(
        "/target-plans/pending/replace",
        json={
            **changed_replacement,
            "replace_confirmed": True,
            "expected_preview_hash": changed_replacement_preview["preview_hash"],
        },
        headers=headers("token-a", shared_key),
    )
    assert activation_conflict.status_code == replacement_conflict.status_code == 409
    assert activation_conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert replacement_conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    session.expire_all()
    records = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == PRINCIPAL_A,
            IdempotencyRecord.idempotency_key == shared_key,
        )
    ).all()
    assert {(record.operation, str(record.resource_id)) for record in records} == {
        ("target_plan.activate", activation.json()["plan"]["id"]),
        ("target_plan.replace", replacement.json()["plan"]["id"]),
    }
    assert all(record.state == "completed" for record in records)
    assert _profile_state(
        session.exec(select(Profile).where(Profile.principal_id == PRINCIPAL_A)).one()
    ) == profile_before_replays
    assert tuple(
        sorted(
            (
                str(plan.id),
                str(plan.status),
                str(plan.predecessor_plan_id),
                str(plan.superseded_by_plan_id),
            )
            for plan in session.exec(
                select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_A)
            ).all()
        )
    ) == plans_before_replays
    session.refresh(transition_before_replays)
    assert transition_before_replays.legacy_target_document == transition_document_before_replays
    assert len(records) == 2


def test_plan021_replacement_rollback_leaves_no_ledger_and_retry_succeeds(
    target_plan_context, monkeypatch
) -> None:
    client, session = target_plan_context
    saved = client.put("/profile", json=profile_payload(), headers=headers("token-a"))
    assert saved.status_code == 200
    activation = activate(client, profile_payload(weight=82), "plan021-rollback-seed")
    assert activation.status_code == 201, activation.text
    activation_plan_id = activation.json()["plan"]["id"]

    replacement_payload = profile_payload(weight=84)
    replacement_preview = preview(client, replacement_payload)
    replacement_body = {
        **replacement_payload,
        "replace_confirmed": True,
        "expected_preview_hash": replacement_preview["preview_hash"],
    }
    real_commit = session.commit

    def fail_commit() -> None:
        raise RuntimeError("injected Plan 021 replacement commit failure")

    monkeypatch.setattr(session, "commit", fail_commit)
    with pytest.raises(
        RuntimeError, match="injected Plan 021 replacement commit failure"
    ):
        client.post(
            "/target-plans/pending/replace",
            json=replacement_body,
            headers=headers("token-a", "plan021-rollback-replace"),
        )
    monkeypatch.setattr(session, "commit", real_commit)

    session.expire_all()
    plans_after_rollback = session.exec(
        select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_A)
    ).all()
    records_after_rollback = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == PRINCIPAL_A
        )
    ).all()
    profile_after_rollback = session.exec(
        select(Profile).where(Profile.principal_id == PRINCIPAL_A)
    ).one()
    assert len(plans_after_rollback) == 1
    assert str(plans_after_rollback[0].id) == activation_plan_id
    assert plans_after_rollback[0].status == "scheduled"
    assert plans_after_rollback[0].superseded_by_plan_id is None
    assert [(record.operation, record.idempotency_key) for record in records_after_rollback] == [
        ("target_plan.activate", "plan021-rollback-seed")
    ]
    assert float(profile_after_rollback.weight_kg) == 82

    retry = client.post(
        "/target-plans/pending/replace",
        json=replacement_body,
        headers=headers("token-a", "plan021-rollback-replace"),
    )
    assert retry.status_code == 201, retry.text
    session.expire_all()
    replacement_record = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == PRINCIPAL_A,
            IdempotencyRecord.operation == "target_plan.replace",
            IdempotencyRecord.idempotency_key == "plan021-rollback-replace",
        )
    ).one()
    assert replacement_record.state == "completed"
    assert str(replacement_record.resource_id) == retry.json()["plan"]["id"]
    assert len(session.exec(select(TargetPlan)).all()) == 2
    assert len(session.exec(select(IdempotencyRecord)).all()) == 2


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
