from contextlib import contextmanager
from datetime import date, timedelta
import os
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import PrincipalContext
from app.models import DiaryEntry, Principal
from app.nutrition_rules.registry import NUTRIENTS
from app.schemas import DiaryNutrientTarget
from app.services.aggregation import (
    aggregate_nutrient,
    weekly_summary,
    weekly_summary_read_only,
)
from app.services import target_plans as target_plan_service


PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)
DEFINITIONS = {item.key: item for item in NUTRIENTS}


def _target(target_type: str, value: float | None = None, **bounds) -> DiaryNutrientTarget:
    return DiaryNutrientTarget(
        type=target_type,
        value=value,
        unit="g",
        source="versioned_plan",
        **bounds,
    )


def test_golden_coverage_states_preserve_null_and_known_zero() -> None:
    fiber = DEFINITIONS["fiber_g"]

    partial = aggregate_nutrient(fiber, [5, 0, None, 3], _target("minimum", 30))
    assert partial.model_dump() == {
        "key": "fiber_g",
        "amount": 8,
        "known_entry_count": 3,
        "total_entry_count": 4,
        "coverage_percent": 75,
        "coverage_state": "partial",
        "amount_qualifier": "at_least",
        "target": {
            "type": "minimum",
            "value": 30,
            "lower": None,
            "upper": None,
            "unit": "g",
            "source": "versioned_plan",
        },
        "evaluation": "indeterminate_partial_coverage",
        "progress_percent": None,
        "remaining": None,
        "available": None,
    }

    all_unknown = aggregate_nutrient(fiber, [None, None], None)
    assert all_unknown.amount is None
    assert all_unknown.coverage_percent == 0
    assert all_unknown.coverage_state == "all_unknown"
    assert all_unknown.amount_qualifier == "unavailable"

    empty = aggregate_nutrient(fiber, [], None)
    assert empty.amount is None
    assert empty.coverage_percent is None
    assert empty.coverage_state == "no_entries"

    known_zero = aggregate_nutrient(fiber, [0, 0], None)
    assert known_zero.amount == 0
    assert known_zero.known_entry_count == 2
    assert known_zero.coverage_state == "complete"
    assert known_zero.amount_qualifier == "exact"


def test_golden_partial_evaluation_is_asymmetric() -> None:
    fiber = DEFINITIONS["fiber_g"]
    sodium = DEFINITIONS["sodium_mg"]

    assert aggregate_nutrient(fiber, [32, None], _target("minimum", 30)).evaluation == "met_at_least"
    below = aggregate_nutrient(fiber, [20, None], _target("minimum", 30))
    assert below.evaluation == "indeterminate_partial_coverage"
    assert below.remaining is None

    exceeded = aggregate_nutrient(sodium, [2100, None], _target("maximum", 2000))
    assert exceeded.evaluation == "exceeded_at_least"
    within = aggregate_nutrient(sodium, [1500, None], _target("maximum", 2000))
    assert within.evaluation == "indeterminate_partial_coverage"
    assert within.available is None

    range_target = _target("range", lower=10, upper=20)
    assert aggregate_nutrient(fiber, [21, None], range_target).evaluation == "above_range_at_least"
    assert (
        aggregate_nutrient(fiber, [15, None], range_target).evaluation
        == "indeterminate_partial_coverage"
    )


def test_complete_evaluation_never_returns_negative_remaining_or_available() -> None:
    fiber = DEFINITIONS["fiber_g"]
    sodium = DEFINITIONS["sodium_mg"]

    met = aggregate_nutrient(fiber, [32], _target("minimum", 30))
    assert met.evaluation == "met"
    assert met.remaining == 0
    assert met.progress_percent == pytest.approx(106.666667)

    exceeded = aggregate_nutrient(sodium, [2100], _target("maximum", 2000))
    assert exceeded.evaluation == "exceeded"
    assert exceeded.available == 0

    monitor = aggregate_nutrient(
        DEFINITIONS["cholesterol_mg"], [100], _target("monitor_only")
    )
    assert monitor.evaluation is None
    assert monitor.progress_percent is None
    assert monitor.remaining is None
    assert monitor.available is None


def test_week_summary_rejects_malformed_snapshot_without_understating_totals(
    monkeypatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.add(
            DiaryEntry(
                principal_id=PRINCIPAL_ID,
                entry_date=date(2026, 7, 12),
                quantity=1,
                snapshot_schema_version=2,
                nutrition_snapshot={"schema_version": 2},
            )
        )
        session.commit()
        advance_calls = 0
        commit_calls = 0
        real_commit = session.commit

        def capture_advance(*_args, **_kwargs) -> None:
            nonlocal advance_calls
            advance_calls += 1

        def capture_commit() -> None:
            nonlocal commit_calls
            commit_calls += 1
            real_commit()

        monkeypatch.setattr(
            "app.services.target_plans._advance_lifecycle", capture_advance
        )
        monkeypatch.setattr(session, "commit", capture_commit)

        with pytest.raises(HTTPException) as raised:
            weekly_summary(session, PRINCIPAL, date(2026, 7, 12))

    assert advance_calls == 1
    assert commit_calls == 1
    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "DIARY_SUMMARY_DATA_INTEGRITY_ERROR"
    assert raised.value.detail["entries"][0]["cause"] == "INVALID_DIARY_SNAPSHOT_DATA"


@contextmanager
def _capture_selects(engine: Engine):
    statements: list[str] = []

    def capture(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        normalized = " ".join(statement.split())
        if normalized.lower().startswith("select "):
            statements.append(normalized)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def _seed_plan015_entries(session: Session, count: int, week_start: date) -> None:
    for offset in range(count):
        session.add(
            DiaryEntry(
                principal_id=PRINCIPAL_ID,
                entry_date=week_start + timedelta(days=offset),
                quantity=1,
                nutrition_snapshot={
                    "name": f"Plan 015 entry {offset}",
                    "calories": 100,
                    "protein_g": 10,
                    "carb_g": 15,
                    "fat_g": 4,
                },
            )
        )
    session.commit()


def _assert_plan015_read_only_query_budget(session: Session, count: int) -> None:
    week_start = date(2026, 7, 12)
    _seed_plan015_entries(session, count, week_start)
    engine = session.get_bind()
    with _capture_selects(engine) as statements:
        summary = weekly_summary_read_only(session, PRINCIPAL, week_start)

    assert len(summary.days) == 7
    assert sum(len(day.nutrient_aggregates) > 0 for day in summary.days) == 7
    # PLAN 031 adds two bounded projections: persisted day rows and legacy
    # entry-date counts. The budget remains constant as entry volume changes.
    assert len(statements) == 7


@pytest.mark.parametrize("entry_count", [0, 1, 7])
def test_plan015_admin_week_query_budget_is_fixed(entry_count: int) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
        _assert_plan015_read_only_query_budget(session, entry_count)


@pytest.mark.parametrize("entry_count", [0, 1, 7])
def test_plan015_owner_week_advances_and_commits_once(
    monkeypatch, entry_count: int
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
        week_start = date(2026, 7, 12)
        _seed_plan015_entries(session, entry_count, week_start)
        advance_calls = 0
        authority_calls = 0
        commit_calls = 0
        real_advance = target_plan_service._advance_lifecycle
        from app.services import aggregation as aggregation_service

        real_authority = aggregation_service.diary_calendar_authority
        real_commit = session.commit

        def capture_advance(*args, **kwargs) -> None:
            nonlocal advance_calls
            advance_calls += 1
            real_advance(*args, **kwargs)

        def capture_authority():
            nonlocal authority_calls
            authority_calls += 1
            return real_authority()

        def capture_commit() -> None:
            nonlocal commit_calls
            commit_calls += 1
            real_commit()

        monkeypatch.setattr(
            "app.services.target_plans._advance_lifecycle", capture_advance
        )
        monkeypatch.setattr(
            "app.services.aggregation.diary_calendar_authority",
            capture_authority,
        )
        monkeypatch.setattr(session, "commit", capture_commit)

        with _capture_selects(engine) as statements:
            weekly_summary(session, PRINCIPAL, week_start)

    assert advance_calls == 1
    assert authority_calls == 1
    assert commit_calls == 1
    assert len(statements) == 8


@pytest.fixture
def plan015_postgresql_session():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL Plan 015 budgets.")
    if make_url(url).get_backend_name() != "postgresql":
        pytest.fail("Plan 015 query budgets require PostgreSQL TEST_DATABASE_URL.")

    schema_name = f"isolated_plan015_{uuid4().hex}"
    admin_engine = create_engine(url, isolation_level="AUTOCOMMIT")
    test_engine = None
    schema_created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            schema_created = True
        test_engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema_name}"},
        )
        SQLModel.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            session.add(Principal(id=PRINCIPAL_ID))
            session.commit()
            yield session
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            with admin_engine.connect() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


@pytest.mark.parametrize("entry_count", [0, 1, 7])
def test_plan015_postgresql_admin_week_query_budget_is_fixed(
    plan015_postgresql_session: Session, entry_count: int
) -> None:
    _assert_plan015_read_only_query_budget(
        plan015_postgresql_session, entry_count
    )
    engine = plan015_postgresql_session.get_bind()
    with _capture_selects(engine) as statements:
        weekly_summary(
            plan015_postgresql_session,
            PRINCIPAL,
            date(2026, 7, 12),
        )
    assert len(statements) == 6
