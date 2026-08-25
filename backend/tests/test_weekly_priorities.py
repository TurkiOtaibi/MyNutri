from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select as sql_select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    BehaviorGoal,
    NutritionAnalysis,
    NutritionAnalysisRevision,
    Principal,
    WeeklyPriorityRecommendation,
)

from app.nutrition_rules.weekly_priority import (
    INFORMATIONAL_COPY_AR,
    STABLE_REPEAT_IDENTITY_FIELDS,
    WEEKLY_PRIORITY_COPY_VERSION,
    WEEKLY_PRIORITY_RULES_VERSION,
    action_day_qualifies,
    action_trackability,
    apply_goal_event,
    apply_repeat_event,
    evaluate_progress,
    select,
    validate_priority_versions,
)
from app.schemas import BehaviorGoalCommandV1, WeeklyPriorityAnalysisInputV1
import app.services.weekly_priorities as weekly_priority_service
from app.services.weekly_priorities import (
    _accepted_goal_window,
    _empty_progress,
    _finalization_boundary,
    _selection_input,
    evaluate_recommendation,
    goal_history,
    recompute_goal_progress,
)

VECTORS = (
    Path(__file__).parents[2]
    / "docs/product/nutrition-quality-expansion/28A_W3_WEEKLY_PRIORITY_AND_GOAL_GOLDEN_VECTORS.json"
)


def _vectors() -> dict:
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def test_all_frozen_plan033_vectors_exercise_production_rules() -> None:
    document = _vectors()
    assert tuple(document["repeat_request_identity_fields"]) == STABLE_REPEAT_IDENTITY_FIELDS
    passed = 0
    selections = {item["name"]: item for item in document["selection_vectors"]}
    for vector in document["selection_vectors"]:
        assert select(vector) == vector["expected"], vector["name"]
        passed += 1
    for vector in document["goal_vectors"]:
        state = deepcopy(vector["initial"])
        for goal_event in vector["events"]:
            assert apply_goal_event(state, goal_event) == goal_event["expected"], vector["name"]
        passed += 1
    repeats = {item["name"]: item for item in document["repeat_vectors"]}
    for vector in document["repeat_vectors"]:
        state, replays = deepcopy(vector["initial"]), {}
        for repeat_event in vector["events"]:
            source = deepcopy(state["source_goal"])
            assert apply_repeat_event(state, repeat_event, replays) == repeat_event["expected"], vector["name"]
            assert state["source_goal"] == source
        passed += 1
    for vector in document["progress_vectors"]:
        assert evaluate_progress(vector) == vector["expected"], vector["name"]
        passed += 1
    for vector in document["mutation_vectors"]:
        mutated = deepcopy(selections[vector["base_vector"]])
        if vector.get("candidate_index") is None:
            mutated[vector["field"]] = vector["value"]
        else:
            mutated["candidates"][vector["candidate_index"]][vector["field"]] = vector["value"]
        with pytest.raises(ValueError, match=vector["expected_error"]):
            select(mutated)
        passed += 1
    for vector in document["repeat_mutation_vectors"]:
        mutated = deepcopy(repeats[vector["base_vector"]])
        event = mutated["events"][vector["event_index"]]
        event[vector["field"]] = vector["value"]
        with pytest.raises(ValueError, match=vector["expected_error"]):
            apply_repeat_event(mutated["initial"], event, {})
        passed += 1
    for vector in document["repeat_identity_mutation_vectors"]:
        base = deepcopy(repeats[vector["base_vector"]])
        fields = list(STABLE_REPEAT_IDENTITY_FIELDS) + vector["fields_to_add"]
        state, replays, actual = base["initial"], {}, None
        for event in base["events"][: vector["event_index"] + 1]:
            actual = apply_repeat_event(state, event, replays, fields)
        assert actual["result"] == vector["expected_mutated_result"]
        passed += 1
    for vector in document["action_trackability_vectors"]:
        assert action_trackability(vector["action_key"]) == (
            vector["goal_trackability"],
            vector["goal_unavailable_reason"],
        )
        assert vector["rules_version"] == WEEKLY_PRIORITY_RULES_VERSION
        assert vector["copy_version"] == WEEKLY_PRIORITY_COPY_VERSION
        passed += 1
    for vector in document["informational_only_vectors"]:
        assert action_trackability(vector["action_key"]) == (
            "informational_only",
            "action_not_observable",
        )
        assert vector["copy_ar"] == INFORMATIONAL_COPY_AR
        assert vector["goal"] is None and vector["progress"] is None
        assert not vector["offer_created"] and vector["reminder_count"] == 0
        assert not vector["repeat_available"] and not vector["reduce_available"]
        passed += 1
    for vector in document["version_vectors"]:
        rules = vector["value"] if vector["kind"] == "rules" else WEEKLY_PRIORITY_RULES_VERSION
        copy = vector["value"] if vector["kind"] == "copy" else WEEKLY_PRIORITY_COPY_VERSION
        if vector["expected"] == "supported":
            validate_priority_versions(rules, copy)
        else:
            with pytest.raises(ValueError, match="unsupported weekly priority"):
                validate_priority_versions(rules, copy)
        passed += 1
    for vector in document["trackability_mutation_vectors"]:
        kind = vector["kind"]
        if kind == "classification":
            assert action_trackability(vector["action_key"])[0] != vector["value"]
        elif kind == "copy":
            assert vector["value"] != INFORMATIONAL_COPY_AR
        elif kind == "version_alias":
            with pytest.raises(ValueError, match="unsupported weekly priority"):
                validate_priority_versions(vector["value"], WEEKLY_PRIORITY_COPY_VERSION)
        else:
            assert vector["value"] is True
        passed += 1
    assert passed == 126


def _persisted_producer_document(principal_id: UUID, analysis_id: UUID) -> dict:
    current_start = diary_calendar_authority().current_diary_date - timedelta(days=6)
    previous_start = current_start - timedelta(days=7)
    source_refs = [uuid4() for _ in range(4)]

    def day(day_date: date, index: int, *, complete: bool) -> dict:
        return {
            "date": day_date,
            "logging_status": "complete" if complete else "unregistered",
            "logging_status_version": 1 if complete else 0,
            "entry_count": 1 if complete else 0,
            "analysis_eligible": complete,
            "completed_at": datetime.now(timezone.utc) if complete else None,
            "snapshot_schema_versions": [3] if complete else [],
            "metric_values": ([{
                "metric_key": "nutrient:sodium_mg",
                "value": 1400,
                "value_state": "known",
                "known_entry_count": 1,
                "total_entry_count": 1,
                "amount_qualifier": "exact",
                "unit": "mg",
            }] if complete else []),
        }

    current_days = [day(current_start + timedelta(days=index), index, complete=index < 4) for index in range(7)]
    previous_days = [day(previous_start + timedelta(days=index), index, complete=False) for index in range(7)]
    refs = [
        {"source_ref": source_refs[index], "diary_date": current_start + timedelta(days=index), "source_version": "3"}
        for index in range(4)
    ]
    document = {
        "interface_version": 1,
        "principal_ref": principal_id,
        "source_analysis_id": analysis_id,
        "source_analysis_revision": 1,
        "generated_at": datetime.now(timezone.utc),
        "as_of_diary_date": current_start + timedelta(days=6),
        "calendar_timezone": "Asia/Riyadh",
        "period_start": current_start,
        "period_end": current_start + timedelta(days=6),
        "previous_period_start": previous_start,
        "previous_period_end": previous_start + timedelta(days=6),
        "analysis_rules_version": "w3-analysis-1.1.0",
        "nutrition_registry_version": "2.0.0",
        "food_group_rules_version": "1.0.0",
        "nova_rules_version": "1.0.0",
        "snapshot_schema_versions": [3],
        "target_plan_refs": [],
        "days": current_days,
        "previous_period": previous_days,
        "metric_facts": [{
            "metric_key": "nutrient:sodium_mg",
            "metric_kind": "daily_average",
            "unit": "mg",
            "aggregation": "average_numeric_days",
            "direction": "maximum",
            "target": {"type": "maximum", "value": 1000, "lower": None, "upper": None, "source_plan_ids": []},
            "current": {
                "value": 1400,
                "value_state": "known",
                "amount_qualifier": "exact",
                "complete_day_count": 4,
                "numeric_day_count": 4,
                "known_entry_count": 4,
                "total_entry_count": 4,
                "coverage_percent": 100,
                "confidence": "strong",
                "status": "above_target",
                "evidence_refs": refs,
            },
            "previous": {
                "value": None,
                "value_state": "unknown",
                "amount_qualifier": "unavailable",
                "complete_day_count": 0,
                "numeric_day_count": 0,
                "known_entry_count": 0,
                "total_entry_count": 0,
                "coverage_percent": None,
                "confidence": "unavailable",
                "status": "unavailable",
                "evidence_refs": [],
            },
            "comparison": {"status": "not_comparable", "reason": "unavailable_value", "difference": None, "normalized_adverse_delta": None},
            "persistence": {"kind": "same_direction_two_period", "qualifies": False, "reason": "missing_previous"},
            "contributors": {"current": [], "previous": []},
        }],
        "safety_flags": [],
    }
    return WeeklyPriorityAnalysisInputV1.model_validate(document).model_dump(mode="json")


def test_production_orchestration_consumes_persisted_plan032_and_persists_result() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    principal_id, analysis_id, revision_id = uuid4(), uuid4(), uuid4()
    document = _persisted_producer_document(principal_id, analysis_id)
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with Session(engine) as session:
        session.add(Principal(id=principal_id))
        series = NutritionAnalysis(
            id=analysis_id,
            principal_id=principal_id,
            as_of_diary_date=date.fromisoformat(document["as_of_diary_date"]),
            calendar_timezone="Asia/Riyadh",
            current_revision_id=revision_id,
            current_revision_number=1,
        )
        session.add(series)
        session.add(NutritionAnalysisRevision(
            id=revision_id,
            analysis_id=analysis_id,
            principal_id=principal_id,
            revision=1,
            period_start=date.fromisoformat(document["period_start"]),
            period_end=date.fromisoformat(document["period_end"]),
            previous_period_start=date.fromisoformat(document["previous_period_start"]),
            previous_period_end=date.fromisoformat(document["previous_period_end"]),
            analysis_rules_version="w3-analysis-1.1.0",
            source_versions={
                "calculation_engine_version": "2.0.0",
                "source_reliability_rules_version": "1.0.0",
                "status_evidence_version": "1",
                "rules_manifest_hash": "0" * 64,
            },
            source_input_hash="1" * 64,
            content_hash=hashlib.sha256(canonical.encode()).hexdigest(),
            complete_day_count=4,
            previous_complete_day_count=0,
            result_status="available",
            analysis_document=document,
        ))
        session.commit()
        result = evaluate_recommendation(session, PrincipalContext(principal_id))
        assert result.status == "selected"
        assert result.main is not None
        assert result.main.rule_key == "sodium_overage"
        assert result.main.action_mode == "replace"
        assert result.main.goal_trackability == "informational_only"
        assert result.main.goal_unavailable_reason == "action_not_observable"
        assert result.main.goal_unavailable_copy_ar == INFORMATIONAL_COPY_AR
        assert result.analysis_rules_version == "w3-analysis-1.1.0"
        persisted = session.exec(sql_select(WeeklyPriorityRecommendation)).one()
        assert persisted.result_document["main"]["rule_key"] == "sodium_overage"
        assert evaluate_recommendation(session, PrincipalContext(principal_id)) == result


def test_goal_history_is_owner_scoped_cursor_stable_and_one_query_for_100_rows() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    principal_id, other_id, recommendation_id = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 8, 17, 9, tzinfo=timezone.utc)
    progress = {
        "window_start": "2026-08-10",
        "window_end": "2026-08-16",
        "progress_count": 1,
        "target_count": 3,
        "progress_percent": 33,
        "complete_day_count": 4,
        "partial_day_count": 0,
        "unregistered_day_count": 3,
        "status": "not_yet_reached",
        "as_of_diary_date": "2026-08-16",
        "source_day_versions": {},
        "calculation_rules_version": "w3-priority-1.1.0",
        "last_recomputed_at": now.isoformat(),
    }
    with Session(engine) as session:
        session.add(Principal(id=principal_id))
        session.add(Principal(id=other_id))
        session.commit()
        # The history projection only needs the immutable goal rows; repository
        # ownership constraints are rehearsed separately on PostgreSQL.
        for index in range(101):
            goal_id = uuid4()
            start = date(2026, 1, 1) + timedelta(days=index * 7)
            session.add(
                BehaviorGoal(
                    id=goal_id,
                    principal_id=principal_id,
                    recommendation_id=recommendation_id,
                    root_goal_id=goal_id,
                    sequence_number=1,
                    state="ended",
                    version=1,
                    rule_key="sodium_overage",
                    action_key="replace_high_sodium_choice",
                    weekly_target_count=3,
                    day_mask=[],
                    window_start=start,
                    window_end=start + timedelta(days=6),
                    rules_version="w3-priority-1.1.0",
                    copy_version="w3-priority-ar-1.1.0",
                    progress_document={**progress, "window_start": start.isoformat(), "window_end": (start + timedelta(days=6)).isoformat()},
                    progress_revision=1,
                    reminder_preference="disabled",
                    ended_at=now,
                )
            )
        session.commit()
        queries = 0

        def count_query(*_args):
            nonlocal queries
            queries += 1

        event.listen(engine, "before_cursor_execute", count_query)
        first = goal_history(session, PrincipalContext(principal_id), 100, None)
        event.remove(engine, "before_cursor_execute", count_query)
        assert len(first.items) == 100
        assert first.next_cursor is not None
        assert queries == 1
        second = goal_history(session, PrincipalContext(principal_id), 100, first.next_cursor)
        assert len(second.items) == 1
        assert set(item.goal_id for item in first.items).isdisjoint(item.goal_id for item in second.items)


@pytest.mark.parametrize(
    ("metric_key", "rule_key"),
    [
        ("group:processed_meat_occurrence_days", "processed_meat_frequency"),
        ("group:sugar_sweetened_beverage_occurrence_days", "sugary_drink_frequency"),
    ],
)
def test_minimize_occurrence_metrics_are_actionable_from_observed_production_evidence(
    metric_key: str, rule_key: str
) -> None:
    source = WeeklyPriorityAnalysisInputV1.model_validate(
        _persisted_producer_document(uuid4(), uuid4())
    )
    template = source.metric_facts[0]
    metric = template.model_copy(
        update={
            "metric_key": metric_key,
            "metric_kind": "occurrence_days",
            "aggregation": "distinct_positive_dates",
            "direction": "minimize",
            "target": None,
            "current": template.current.model_copy(update={"status": "observed", "value": 2.0}),
        }
    )
    days = [
        day.model_copy(
            update={
                "metric_values": [
                    fact.model_copy(update={"metric_key": metric_key, "unit": "days"})
                    for fact in day.metric_values
                ]
            }
        )
        for day in source.days
    ]
    vector, _ = _selection_input(
        source.model_copy(update={"days": days, "metric_facts": [metric]}), "eligible"
    )
    candidate = next(item for item in vector["candidates"] if item["key"] == rule_key)
    assert candidate["actionable"] is True
    assert candidate["repeat_events"] == 4


def test_trackable_predicates_use_closed_producer_shaped_facts() -> None:
    base = {
        "date": "2026-08-18",
        "logging_status": "complete",
        "analysis_eligible": True,
        "entry_count": 2,
    }
    trans_fact = {
        "metric_key": "nutrient:trans_fat_g",
        "value": 0,
        "value_state": "explicit_zero",
        "known_entry_count": 2,
        "total_entry_count": 2,
        "amount_qualifier": "exact",
        "unit": "g",
    }
    assert action_day_qualifies(
        "replace_trans_fat_choice", {**base, "metric_values": [trans_fact]}
    )
    assert not action_day_qualifies(
        "replace_trans_fat_choice",
        {**base, "metric_values": [{**trans_fact, "known_entry_count": 1}]},
    )
    for action_key, metric_key in (
        ("replace_processed_meat_choice", "protein:source_diversity_count"),
        ("add_fruit_or_vegetable", "group:fruit_vegetable_g_per_day"),
        ("replace_with_fruit_or_vegetable", "group:fruit_vegetable_g_per_day"),
        ("add_legumes", "group:legumes_servings_per_period"),
        ("replace_with_legumes", "group:legumes_servings_per_period"),
        ("replace_with_seafood", "group:seafood_servings_per_period"),
        ("add_dairy_or_fortified_alternative", "group:dairy_fortified_servings_per_day"),
        ("replace_with_dairy_or_fortified_alternative", "group:dairy_fortified_servings_per_day"),
    ):
        fact = {
            "metric_key": metric_key,
            "value": 1,
            "value_state": "known",
            "known_entry_count": 1,
            "total_entry_count": 2,
            "amount_qualifier": "exact",
            "unit": "count",
        }
        assert action_day_qualifies(action_key, {**base, "metric_values": [fact]})
        assert not action_day_qualifies(
            action_key,
            {**base, "metric_values": [{**fact, "value_state": "unknown", "value": None}]},
        )


def test_goal_commands_reject_cross_event_fields() -> None:
    with pytest.raises(ValueError):
        BehaviorGoalCommandV1(event="defer", expected_version=1, note="not allowed")
    with pytest.raises(ValueError):
        BehaviorGoalCommandV1(event="pause", expected_version=1, weekly_target_count=2)
    assert BehaviorGoalCommandV1(
        event="edit",
        expected_version=1,
        weekly_target_count=4,
        scheduled_day_mask=[0, 2, 4],
        reminder_preference="enabled",
        note="خطة أسبوعية",
    ).event == "edit"


def test_producer_projection_rejects_misaligned_duplicate_and_non_finite_facts() -> None:
    document = _persisted_producer_document(uuid4(), uuid4())
    duplicate = deepcopy(document)
    duplicate["days"][1]["date"] = duplicate["days"][0]["date"]
    with pytest.raises(ValueError, match="sorted and unique"):
        WeeklyPriorityAnalysisInputV1.model_validate(duplicate)

    misaligned = deepcopy(document)
    misaligned["period_start"] = (
        date.fromisoformat(misaligned["period_start"]) + timedelta(days=1)
    ).isoformat()
    with pytest.raises(ValueError, match="seven days|align"):
        WeeklyPriorityAnalysisInputV1.model_validate(misaligned)

    non_finite = deepcopy(document)
    non_finite["metric_facts"][0]["current"]["value"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        WeeklyPriorityAnalysisInputV1.model_validate(non_finite)

    invalid_counts = deepcopy(document)
    invalid_counts["days"][0]["metric_values"][0]["known_entry_count"] = 2
    with pytest.raises(ValueError, match="known entry count exceeds total"):
        WeeklyPriorityAnalysisInputV1.model_validate(invalid_counts)


def test_accept_window_uses_one_diary_start_and_source_review_cap() -> None:
    recommendation = SimpleNamespace(period_end=date(2026, 8, 17))
    assert _accepted_goal_window(recommendation, date(2026, 8, 17)) == (
        date(2026, 8, 17),
        date(2026, 8, 23),
    )
    assert _accepted_goal_window(recommendation, date(2026, 8, 19)) == (
        date(2026, 8, 19),
        date(2026, 8, 24),
    )
    assert _finalization_boundary(date(2026, 8, 24)) == datetime(
        2026, 8, 26, 9, tzinfo=timezone.utc
    )


def test_completion_reopens_before_grace_and_late_evidence_creates_immutable_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before_boundary = datetime.now(timezone.utc)
    principal_id = uuid4()
    source = WeeklyPriorityAnalysisInputV1.model_validate(
        _persisted_producer_document(principal_id, uuid4())
    ).model_copy(update={"generated_at": before_boundary})
    fruit_days = []
    for index, day in enumerate(source.days):
        if day.logging_status != "complete":
            fruit_days.append(day)
            continue
        fact = day.metric_values[0].model_copy(
            update={
                "metric_key": "group:fruit_vegetable_g_per_day",
                "value": 100.0 if index == 0 else 0.0,
                "value_state": "known",
                "unit": "g",
            }
        )
        fruit_days.append(day.model_copy(update={"metric_values": [fact]}))
    source = source.model_copy(update={"days": fruit_days})
    goal_id = uuid4()
    goal = BehaviorGoal(
        id=goal_id,
        principal_id=principal_id,
        recommendation_id=uuid4(),
        root_goal_id=goal_id,
        sequence_number=1,
        state="active",
        version=1,
        rule_key="fruit_vegetable_gap",
        action_key="add_fruit_or_vegetable",
        weekly_target_count=1,
        day_mask=[],
        window_start=source.period_start,
        window_end=source.period_end,
        rules_version="w3-priority-1.1.0",
        copy_version="w3-priority-ar-1.1.0",
        progress_document={},
        progress_revision=1,
        reminder_preference="disabled",
    )
    goal.progress_document = _empty_progress(
        goal, source.as_of_diary_date, before_boundary
    ).model_dump(mode="json")

    class Recorder:
        def __init__(self):
            self.added = []

        def add(self, value):
            self.added.append(value)

    recorder = Recorder()
    monkeypatch.setattr(weekly_priority_service, "utcnow", lambda: before_boundary)
    assert recompute_goal_progress(recorder, goal, source_override=source)
    assert goal.state == "completed"
    completed_history = recorder.added[-1]
    assert completed_history.event_type == "completed"
    completed_snapshot = deepcopy(completed_history.terms_progress_snapshot)
    assert not recompute_goal_progress(recorder, goal, source_override=source)

    changed_day = source.days[0].model_copy(
        update={
            "logging_status_version": source.days[0].logging_status_version + 1,
            "metric_values": [
                source.days[0].metric_values[0].model_copy(
                    update={"value": 0.0, "value_state": "known"}
                )
            ],
        }
    )
    changed_source = source.model_copy(
        update={"days": [changed_day, *source.days[1:]], "generated_at": before_boundary}
    )
    assert recompute_goal_progress(recorder, goal, source_override=changed_source)
    assert goal.state == "active"
    assert recorder.added[-1].event_type == "evidence_reopened"

    restored_day = source.days[0].model_copy(
        update={"logging_status_version": source.days[0].logging_status_version + 2}
    )
    restored_source = source.model_copy(
        update={
            "days": [restored_day, *source.days[1:]],
            "generated_at": before_boundary + timedelta(minutes=1),
        }
    )
    monkeypatch.setattr(
        weekly_priority_service, "utcnow", lambda: before_boundary + timedelta(minutes=1)
    )
    assert recompute_goal_progress(recorder, goal, source_override=restored_source)
    assert goal.state == "completed"
    assert recorder.added[-1].event_type == "completed"

    after_boundary = _finalization_boundary(goal.window_end) + timedelta(minutes=1)
    monkeypatch.setattr(weekly_priority_service, "utcnow", lambda: after_boundary)
    late_day = changed_day.model_copy(
        update={"logging_status_version": source.days[0].logging_status_version + 3}
    )
    changed_source = changed_source.model_copy(
        update={"days": [late_day, *source.days[1:]], "generated_at": after_boundary}
    )
    assert recompute_goal_progress(recorder, goal, source_override=changed_source)
    assert recorder.added[-1].event_type == "historical_evidence_changed"
    assert completed_history.terms_progress_snapshot == completed_snapshot
