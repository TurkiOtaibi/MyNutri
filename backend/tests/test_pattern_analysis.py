from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    DiaryDayStatus,
    DiaryDayStatusValue,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
)
from app.nutrition_rules.analysis import evaluate_contract_case
from app.schemas import AnalysisDayFactV1, AnalysisEvaluateCommandV1
from app.services import pattern_analysis
from app.services.pattern_analysis import (
    PatternAnalysisError,
    append_stale_events_for_date,
    evaluate_analysis,
    exact_revision,
)


VECTORS = Path(__file__).parents[2] / "docs/product/nutrition-quality-expansion/27A_W3_PATTERN_ANALYSIS_GOLDEN_VECTORS.json"


def _vectors() -> list[dict]:
    return json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"]


@pytest.mark.parametrize("vector", _vectors(), ids=lambda item: item["id"])
def test_frozen_golden_vectors_execute_production_rules(vector: dict) -> None:
    assert evaluate_contract_case(vector["kind"], vector["input"]) == vector["expected"]


def test_vector_corpus_contains_all_frozen_cases() -> None:
    vectors = _vectors()
    assert len(vectors) == 52
    assert len({vector["id"] for vector in vectors}) == 52


def _entry_fact(
    source_id: str,
    *,
    groups: dict[str, float],
    traits: frozenset[str] = frozenset(),
    nova: str | None = None,
    nova_calories: float | None = None,
) -> pattern_analysis._EntryFact:
    return pattern_analysis._EntryFact(
        entry=SimpleNamespace(
            id=UUID(source_id),
            entry_date=datetime(2026, 8, 17, tzinfo=timezone.utc).date(),
        ),
        nutrition={},
        groups=groups,
        group_known=True,
        traits=traits,
        nova=nova,
        nova_calories=nova_calories,
        registry_version="2.0.0",
        group_version="1.0.0",
        nova_version="1.0.0",
        source_version="snapshot-3",
    )


def test_daily_fruit_liquid_cap_is_applied_once_per_date() -> None:
    facts = [
        _entry_fact(
            "00000000-0000-4000-8000-000000000101",
            groups={"fruits": 100, "vegetables": 50},
            traits=frozenset({"fruit_liquid_100_percent"}),
        ),
        _entry_fact(
            "00000000-0000-4000-8000-000000000102",
            groups={"fruits": 100},
            traits=frozenset({"fruit_liquid_100_percent"}),
        ),
    ]
    assert pattern_analysis._day_metric_value(
        facts, "group:fruit_vegetable_g_per_day"
    ) == (200.0, 2, 2)


def test_nova4_occurrence_contributor_excludes_other_classes_and_deduplicates_date() -> None:
    diary_date = datetime(2026, 8, 17, tzinfo=timezone.utc).date()
    facts = [
        _entry_fact(
            "00000000-0000-4000-8000-000000000103",
            groups={},
            nova="1",
            nova_calories=900,
        ),
        _entry_fact(
            "00000000-0000-4000-8000-000000000104",
            groups={},
            nova="4",
            nova_calories=100,
        ),
        _entry_fact(
            "00000000-0000-4000-8000-000000000105",
            groups={},
            nova="4",
            nova_calories=200,
        ),
    ]
    day = AnalysisDayFactV1(
        date=diary_date,
        logging_status="complete",
        logging_status_version=1,
        entry_count=3,
        analysis_eligible=True,
        completed_at=datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
        snapshot_schema_versions=[3],
        metric_values=[],
    )
    contributors = pattern_analysis._contributors(
        [day],
        "nova:nova4_occurrence_days",
        {diary_date: facts},
        "days/7d",
    )
    assert [str(item.source_ref) for item in contributors] == [
        "00000000-0000-4000-8000-000000000105"
    ]


def _analysis_session(monkeypatch: pytest.MonkeyPatch) -> tuple[Session, PrincipalContext]:
    principal_id = UUID("00000000-0000-0000-0000-000000000321")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Principal(id=principal_id))
    authority = diary_calendar_authority(datetime(2026, 8, 17, 9, tzinfo=timezone.utc))
    for offset in range(4):
        day = authority.current_diary_date - timedelta(days=offset)
        session.add(
            DiaryDayStatus(
                principal_id=principal_id,
                diary_date=day,
                status=DiaryDayStatusValue.complete,
                version=1,
                entry_count=0,
                completed_at=datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
            )
        )
    session.commit()
    monkeypatch.setattr(pattern_analysis, "diary_calendar_authority", lambda: authority)
    return session, PrincipalContext(principal_id)


def test_evaluation_persists_immutable_revision_and_exact_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _analysis_session(monkeypatch)
    command = AnalysisEvaluateCommandV1(expected_current_revision=None)
    response, status, replayed = evaluate_analysis(
        session, principal, command, "first-evaluation", '"analysis-none"'
    )
    assert (status, replayed, response.source_analysis_revision) == (201, False, 1)
    replay, replay_status, was_replayed = evaluate_analysis(
        session, principal, command, "first-evaluation", '"wrong-but-replay-first"'
    )
    assert (replay_status, was_replayed, replay.model_dump(mode="json")) == (
        201,
        True,
        response.model_dump(mode="json"),
    )
    no_change, no_change_status, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV1(expected_current_revision=1),
        "no-change-evaluation",
        response.etag,
    )
    assert (no_change_status, no_change.source_analysis_revision) == (200, 1)
    assert len(session.exec(select(NutritionAnalysisRevision)).all()) == 1
    session.close()


def test_stale_event_is_append_only_and_cross_owner_revision_is_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _analysis_session(monkeypatch)
    response, _, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV1(expected_current_revision=None),
        "stale-source",
        '"analysis-none"',
    )
    original = session.exec(select(NutritionAnalysisRevision)).one()
    original_document = json.dumps(original.analysis_document, sort_keys=True)
    assert append_stale_events_for_date(
        session,
        principal.principal_id,
        response.as_of_diary_date,
        "day_reopened",
        "completed_day_reopened",
        2,
    ) == 1
    session.commit()
    assert json.dumps(session.get(NutritionAnalysisRevision, original.id).analysis_document, sort_keys=True) == original_document
    assert session.exec(select(NutritionAnalysisRevisionEvent)).one().event_type == "day_reopened"
    with pytest.raises(PatternAnalysisError) as hidden:
        exact_revision(
            session,
            PrincipalContext(UUID("00000000-0000-0000-0000-000000000999")),
            response.source_analysis_id,
            1,
        )
    assert (hidden.value.status_code, hidden.value.code) == (404, "RESOURCE_NOT_FOUND")
    session.close()
