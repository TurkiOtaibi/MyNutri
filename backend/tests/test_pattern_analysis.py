from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    DiaryEntry,
    DiaryDayStatus,
    DiaryDayStatusValue,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
    TargetProvenance,
)
from app.nutrition_rules.analysis import evaluate_contract_case, require_analysis_rules
from app.schemas import (
    AnalysisDayFactV1,
    AnalysisEvaluateCommandV2,
    AnalysisMetricFactV1,
    NutritionPatternAnalysisResponseV2,
)
from app.services import weekly_priorities as weekly_priority_service
from app.api.routes import nutrition_analysis as nutrition_analysis_route
from app.services import pattern_analysis
from app.services.pattern_analysis import (
    PatternAnalysisError,
    admin_monitoring,
    append_stale_events_for_date,
    evaluate_analysis,
    exact_revision,
)
from app.services.weekly_priorities import evaluate_recommendation


VECTORS = (
    Path(__file__).parents[2]
    / "docs/product/nutrition-quality-expansion/27A_W3_PATTERN_ANALYSIS_GOLDEN_VECTORS.json"
)


def _vectors() -> list[dict]:
    return json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"]


@pytest.mark.parametrize("vector", _vectors(), ids=lambda item: item["id"])
def test_frozen_golden_vectors_execute_production_rules(vector: dict) -> None:
    assert evaluate_contract_case(vector["kind"], vector["input"]) == vector["expected"]


def test_vector_corpus_contains_all_frozen_cases() -> None:
    vectors = _vectors()
    assert len(vectors) == 77
    assert len({vector["id"] for vector in vectors}) == 77


def test_withdrawn_pre_release_rules_version_has_no_runtime_dispatch() -> None:
    require_analysis_rules("w3-analysis-1.1.0")
    with pytest.raises(ValueError, match="UNSUPPORTED_ANALYSIS_RULE_VERSION"):
        require_analysis_rules("w3-analysis-1.0.0")


def _snapshot_v3(
    *,
    group_known: bool,
    reviewed_nova: bool,
    calories: float = 0,
    contributions: list[dict] | None = None,
) -> dict:
    optional = {
        "fiber_g": None,
        "added_sugar_g": None,
        "saturated_fat_g": None,
        "trans_fat_g": None,
        "sodium_mg": None,
        "potassium_mg": None,
        "cholesterol_mg": None,
        "calcium_mg": None,
        "iron_mg": None,
        "magnesium_mg": None,
        "zinc_mg": None,
        "selenium_mcg": None,
        "vitamin_b12_mcg": None,
        "folate_dfe_mcg": None,
        "vitamin_a_rae_mcg": None,
        "iodine_mcg": None,
    }
    return {
        "schema_version": 3,
        "food": {
            "food_id": None,
            "name": "Evidence",
            "brand": None,
            "food_category_key": "other",
            "grain_type": None,
            "baked_good_type": None,
            "grain_starch_type": None,
            "food_kind": "simple",
        },
        "captured_unit": {
            "nutrition_basis": "per_100g",
            "default_unit_type": "serving",
            "unit_amount": 100,
            "unit_basis": "g",
        },
        "nutrition": {
            "calories": calories,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            **optional,
        },
        "completeness": {
            "known_nutrient_count": 0,
            "total_nutrient_count": 16,
            "state": "all_unknown",
        },
        "food_groups": {
            "status": "known" if group_known else "unknown",
            "completeness": "complete" if group_known else "unknown",
            "contributions": contributions or [],
            "traits": [],
            "food_group_rules_version": "1.0.0",
        },
        "source": {
            "type": "official_product_label",
            "name": None,
            "reference": None,
            "reliability": "high",
            "source_reliability_rules_version": "1.0.0",
        },
        "nova": {
            "classification": "4" if reviewed_nova else "unknown",
            "review_status": "reviewed" if reviewed_nova else "unreviewed",
            "nova_rules_version": "1.0.0",
        },
        "versions": {
            "nutrition_registry_version": "2.0.0",
            "food_group_rules_version": "1.0.0",
            "source_reliability_rules_version": "1.0.0",
            "nova_rules_version": "1.0.0",
            "snapshot_schema_version": 3,
        },
    }


def _target_source(plan_id: UUID, effective_from, *, carb: float, fat: float):
    targets = SimpleNamespace(
        final_target_calories=2000,
        protein_g=100,
        carb_g=carb,
        fat_g=fat,
        additional_targets=[],
        safety_outcome="normal",
        calculation_engine_version="mifflin-st-jeor-v1",
        nutrition_registry_version="3.0.0",
    )
    targets.model_dump = lambda mode="json": {
        "final_target_calories": 2000,
        "protein_g": 100,
        "carb_g": carb,
        "fat_g": fat,
        "safety_outcome": "normal",
    }
    plan = SimpleNamespace(
        id=plan_id,
        effective_from=effective_from,
        effective_to=None,
        targets=targets,
    )
    return SimpleNamespace(plan=plan, targets=targets, target_provenance="versioned_plan")


def _production_evidence_session(
    monkeypatch: pytest.MonkeyPatch,
    *,
    group_known: bool,
    reviewed_nova: bool,
    incompatible_carb: bool,
    contributions: list[dict] | None = None,
) -> tuple[Session, PrincipalContext]:
    principal_id = UUID("00000000-0000-0000-0000-000000000322")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Principal(id=principal_id))
    authority = diary_calendar_authority(datetime(2026, 8, 17, 9, tzinfo=timezone.utc))
    complete_dates = [
        authority.current_diary_date - timedelta(days=offset)
        for offset in (0, 1, 2, 3, 7, 8, 9, 10)
    ]
    for index, day in enumerate(complete_dates):
        session.add(
            DiaryDayStatus(
                principal_id=principal_id,
                diary_date=day,
                status=DiaryDayStatusValue.complete,
                version=1,
                entry_count=1,
                completed_at=datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
            )
        )
        session.add(
            DiaryEntry(
                principal_id=principal_id,
                entry_date=day,
                quantity=1,
                target_provenance=TargetProvenance.no_target_source,
                snapshot_schema_version=3,
                nutrition_snapshot=_snapshot_v3(
                    group_known=group_known,
                    reviewed_nova=reviewed_nova,
                    contributions=contributions,
                ),
            )
        )
    session.commit()
    plan_current = UUID("00000000-0000-4000-8000-000000000201")
    plan_previous = UUID("00000000-0000-4000-8000-000000000202")
    targets = {}
    for offset in range(14):
        day = authority.current_diary_date - timedelta(days=offset)
        current = offset <= 6
        targets[day] = _target_source(
            plan_current if current else plan_previous,
            day,
            carb=250 if current or not incompatible_carb else 260,
            fat=70,
        )
    monkeypatch.setattr(pattern_analysis, "diary_calendar_authority", lambda: authority)
    monkeypatch.setattr(
        pattern_analysis, "project_week_target_context", lambda *args, **kwargs: targets
    )
    monkeypatch.setattr(pattern_analysis, "target_for_date", lambda context, day: context[day])
    return session, PrincipalContext(principal_id)


def _metric(response, key: str) -> AnalysisMetricFactV1:
    return next(item for item in response.priority_input.metric_facts if item.metric_key == key)


def test_production_pipeline_preserves_unknown_group_and_incompatible_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _production_evidence_session(
        monkeypatch, group_known=False, reviewed_nova=False, incompatible_carb=True
    )
    response, status, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "production-unknown",
        '"analysis-none"',
    )
    assert status == 201
    for key in (
        "group:legumes_servings_per_period",
        "group:processed_meat_occurrence_days",
        "group:whole_grain_share_percent",
        "protein:source_diversity_count",
    ):
        fact = _metric(response, key)
        assert (fact.current.value, fact.current.value_state, fact.current.amount_qualifier) == (
            None,
            "unknown",
            "unavailable",
        )
    carb = _metric(response, "macro:carb_g_per_day")
    assert carb.target is None
    assert (carb.current.status, carb.previous.status) == (
        "target_incompatible",
        "target_incompatible",
    )
    assert (carb.comparison.status, carb.comparison.reason) == (
        "not_comparable",
        "target_incompatible",
    )
    assert (carb.persistence.qualifies, carb.persistence.reason) == (False, "target_changed")
    assert "incompatible_target" in response.priority_input.safety_flags
    persisted = session.exec(select(NutritionAnalysisRevision)).one()
    assert persisted.analysis_document == response.priority_input.model_dump(mode="json")
    session.close()


def test_monitoring_projects_closed_coverage_stale_and_latency_bands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _analysis_session(monkeypatch)
    evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "monitoring-source",
        '"analysis-none"',
    )
    revision = session.exec(select(NutritionAnalysisRevision)).one()
    revision.generated_at = datetime(2026, 8, 17, 8, 0, 0, tzinfo=timezone.utc)
    revision.finalized_at = datetime(2026, 8, 17, 8, 0, 0, 500000, tzinfo=timezone.utc)
    revision.analysis_document = {
        "metric_facts": [
            {
                "metric_key": "a",
                "current": {"coverage_percent": None},
                "previous": {"coverage_percent": 100},
            },
            {"metric_key": "b", "current": {"coverage_percent": 49.999}},
            {"metric_key": "c", "current": {"coverage_percent": 50}},
            {"metric_key": "d", "current": {"coverage_percent": 75}},
        ]
    }
    session.add(revision)
    session.add_all(
        [
            NutritionAnalysisRevisionEvent(
                revision_id=revision.id,
                principal_id=principal.principal_id,
                event_type="day_reopened",
                reason="first",
                source_day_version=1,
            ),
            NutritionAnalysisRevisionEvent(
                revision_id=revision.id,
                principal_id=principal.principal_id,
                event_type="day_reopened",
                reason="second",
                source_day_version=2,
            ),
            NutritionAnalysisRevisionEvent(
                revision_id=revision.id,
                principal_id=principal.principal_id,
                event_type="target_source_changed",
                reason="target",
                source_day_version=3,
            ),
        ]
    )
    session.commit()
    result = admin_monitoring(session, "2026-W34").model_dump(mode="json", by_alias=True)
    assert result["total_count"] == 1
    assert result["coverage_band_counts"] == {
        "unknown": 1,
        "0_to_lt_50": 1,
        "50_to_lt_75": 1,
        "75_to_100": 1,
    }
    assert result["stale_reason_counts"]["day_reopened"] == 1
    assert result["stale_reason_counts"]["target_source_changed"] == 1
    assert result["latency_band_counts"]["500_to_lt_1000_ms"] == 1
    session.close()


def test_unexpected_evaluation_failure_uses_stable_neutral_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise RuntimeError("private nutrition evidence")

    monkeypatch.setattr(nutrition_analysis_route, "evaluate_analysis", fail)
    response = nutrition_analysis_route.evaluate_v2(
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "stable-error",
        '"analysis-none"',
        PrincipalContext(UUID(int=1)),
        None,
    )
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body["error"]["code"] == "ANALYSIS_EVALUATION_FAILED"
    assert body["error"]["request_id"]
    assert "private nutrition evidence" not in response.body.decode()


def test_production_pipeline_preserves_observed_zero_and_degenerate_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _production_evidence_session(
        monkeypatch, group_known=True, reviewed_nova=True, incompatible_carb=False
    )
    response, _, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "production-zero",
        '"analysis-none"',
    )
    for key in (
        "group:legumes_servings_per_period",
        "group:processed_meat_occurrence_days",
        "protein:source_diversity_count",
    ):
        fact = _metric(response, key)
        assert (fact.current.value, fact.current.value_state) == (0, "explicit_zero")
    for key, value in (("macro:carb_g_per_day", 250), ("macro:fat_g_per_day", 70)):
        fact = _metric(response, key)
        assert fact.target is not None
        assert (fact.target.type, fact.target.lower, fact.target.upper) == ("range", value, value)
        assert len(fact.target.source_plan_ids) == 2
        assert fact.current.status == "below_target"
    carb_payload = _metric(response, "macro:carb_g_per_day").model_dump(mode="json")
    contradictory = {**carb_payload, "direction": "minimum"}
    with pytest.raises(ValueError, match="direction contradicts target type"):
        AnalysisMetricFactV1.model_validate(contradictory)
    false_null = {**carb_payload, "target": None}
    with pytest.raises(ValueError, match="target-relative status requires a target"):
        AnalysisMetricFactV1.model_validate(false_null)
    session.close()


def test_production_pipeline_mixed_known_unknown_uses_known_lower_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _production_evidence_session(
        monkeypatch, group_known=False, reviewed_nova=False, incompatible_carb=False
    )
    entries = session.exec(select(DiaryEntry).order_by(DiaryEntry.entry_date.desc())).all()
    contributions = [
        {
            "group_key": "whole_grains",
            "subtype_key": None,
            "amount_per_captured_unit": 50,
            "data_status": "known",
        },
        {
            "group_key": "refined_grains",
            "subtype_key": None,
            "amount_per_captured_unit": 50,
            "data_status": "known",
        },
        {
            "group_key": "legumes",
            "subtype_key": None,
            "amount_per_captured_unit": 80,
            "data_status": "known",
        },
        {
            "group_key": "processed_meat",
            "subtype_key": None,
            "amount_per_captured_unit": 10,
            "data_status": "known",
        },
    ]
    for entry in (entries[0], entries[4]):
        entry.nutrition_snapshot = _snapshot_v3(
            group_known=True,
            reviewed_nova=True,
            calories=100,
            contributions=contributions,
        )
        session.add(entry)
    session.commit()
    response, _, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "production-mixed",
        '"analysis-none"',
    )
    expected_values = {
        "group:legumes_servings_per_period": 1,
        "group:processed_meat_occurrence_days": 1,
        "group:whole_grain_share_percent": 50,
        "protein:source_diversity_count": 1,
    }
    for key, expected in expected_values.items():
        period = _metric(response, key).current
        assert (period.value, period.amount_qualifier) == (expected, "at_least")
        assert period.coverage_percent == 25
    session.close()


def test_production_pipeline_missing_target_is_distinct_and_suppresses_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _production_evidence_session(
        monkeypatch, group_known=True, reviewed_nova=True, incompatible_carb=False
    )
    missing = SimpleNamespace(plan=None, targets=None, target_provenance="no_target_source")
    monkeypatch.setattr(pattern_analysis, "target_for_date", lambda _context, _day: missing)
    response, _, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "production-missing-target",
        '"analysis-none"',
    )
    carb = _metric(response, "macro:carb_g_per_day")
    assert carb.target is None
    assert (carb.current.status, carb.previous.status) == ("observed", "observed")
    assert (carb.comparison.status, carb.comparison.reason) == (
        "not_comparable",
        "unavailable_value",
    )
    assert (carb.persistence.qualifies, carb.persistence.reason) == (
        False,
        "current_not_qualifying",
    )
    assert "missing_target" in response.priority_input.safety_flags
    assert "incompatible_target" not in response.priority_input.safety_flags
    session.close()


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
    assert pattern_analysis._day_metric_value(facts, "group:fruit_vegetable_g_per_day") == (
        200.0,
        2,
        2,
    )


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
    command = AnalysisEvaluateCommandV2(expected_current_revision=None)
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
        AnalysisEvaluateCommandV2(expected_current_revision=1),
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
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "stale-source",
        '"analysis-none"',
    )
    original = session.exec(select(NutritionAnalysisRevision)).one()
    original_document = json.dumps(original.analysis_document, sort_keys=True)
    assert (
        append_stale_events_for_date(
            session,
            principal.principal_id,
            response.as_of_diary_date,
            "day_reopened",
            "completed_day_reopened",
            2,
        )
        == 1
    )
    session.commit()
    assert (
        json.dumps(
            session.get(NutritionAnalysisRevision, original.id).analysis_document, sort_keys=True
        )
        == original_document
    )
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


def test_historical_refresh_preserves_original_series_and_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _production_evidence_session(
        monkeypatch,
        group_known=True,
        reviewed_nova=True,
        incompatible_carb=False,
    )
    original, status, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "historical-d0",
        '"analysis-none"',
    )
    assert status == 201
    s0 = original.source_analysis_id
    original_revision = session.exec(
        select(NutritionAnalysisRevision).where(
            NutritionAnalysisRevision.analysis_id == s0,
            NutritionAnalysisRevision.revision == 1,
        )
    ).one()
    with pytest.raises(weekly_priority_service.WeeklyPriorityError) as inactive:
        evaluate_recommendation(session, principal)
    assert (inactive.value.status_code, inactive.value.code) == (
        409,
        "WEEKLY_PRIORITY_INACTIVE_FOR_ANALYSIS_V2",
    )
    assert original_revision.analysis_document == original.priority_input.model_dump(mode="json")
    session.close()


def test_v2_public_response_rejects_version_metric_hash_and_etag_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, principal = _analysis_session(monkeypatch)
    response, _, _ = evaluate_analysis(
        session,
        principal,
        AnalysisEvaluateCommandV2(expected_current_revision=None),
        "closed-v2-contract",
        '"analysis-none"',
    )
    canonical = response.model_dump(mode="json")
    metric_keys = [item["metric_key"] for item in canonical["metric_summaries"]]
    assert len(metric_keys) == 32
    assert metric_keys == sorted(metric_keys)
    assert not any(key.startswith("nova:") for key in metric_keys)

    mutations = []
    for path, value in (
        (("source_versions", "analysis_rules_version"), "w3-analysis-1.1.0"),
        (("source_versions", "nutrition_registry_version"), "2.0.0"),
        (("source_versions", "calculation_engine_version"), "candidate"),
        (("source_versions", "snapshot_schema_versions"), [4, 3]),
        (("source_versions", "rules_manifest_hash"), "not-a-hash"),
        (("source_versions", "content_hash"), "0" * 64),
        (("etag",), '"analysis-malformed"'),
    ):
        candidate = copy.deepcopy(canonical)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        mutations.append(candidate)

    missing = copy.deepcopy(canonical)
    missing["metric_summaries"].pop()
    mutations.append(missing)
    duplicate = copy.deepcopy(canonical)
    duplicate["metric_summaries"][-1] = duplicate["metric_summaries"][0]
    mutations.append(duplicate)
    invented = copy.deepcopy(canonical)
    invented["metric_summaries"][0]["metric_key"] = "candidate:invented"
    mutations.append(invented)
    reordered = copy.deepcopy(canonical)
    reordered["metric_summaries"][0], reordered["metric_summaries"][1] = (
        reordered["metric_summaries"][1],
        reordered["metric_summaries"][0],
    )
    mutations.append(reordered)
    legacy_field = copy.deepcopy(canonical)
    legacy_field["source_versions"]["nova_rules_version"] = "1.0.0"
    mutations.append(legacy_field)

    for candidate in mutations:
        with pytest.raises(ValidationError):
            NutritionPatternAnalysisResponseV2.model_validate(candidate)
    session.close()
