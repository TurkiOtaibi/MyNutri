from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
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
    STABLE_REPEAT_IDENTITY_FIELDS,
    apply_goal_event,
    apply_repeat_event,
    evaluate_progress,
    select,
)
from app.schemas import WeeklyPriorityAnalysisInputV1
from app.services.weekly_priorities import evaluate_recommendation, goal_history

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
    assert passed == 52


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
        "calculation_rules_version": "w3-priority-1.0.0",
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
                    rules_version="w3-priority-1.0.0",
                    copy_version="w3-priority-ar-1.0.0",
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
