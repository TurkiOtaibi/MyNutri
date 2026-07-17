from datetime import date
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import PrincipalContext
from app.models import DiaryEntry, Principal
from app.nutrition_rules.registry import NUTRIENTS
from app.schemas import DiaryNutrientTarget
from app.services.aggregation import aggregate_nutrient, weekly_summary


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


def test_week_summary_rejects_malformed_snapshot_without_understating_totals() -> None:
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

        with pytest.raises(HTTPException) as raised:
            weekly_summary(session, PRINCIPAL, date(2026, 7, 12))

    assert raised.value.status_code == 409
    assert raised.value.detail["code"] == "DIARY_SUMMARY_DATA_INTEGRITY_ERROR"
    assert raised.value.detail["entries"][0]["cause"] == "INVALID_DIARY_SNAPSHOT_DATA"
