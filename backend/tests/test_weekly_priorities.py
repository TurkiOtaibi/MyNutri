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
    BehaviorGoalHistory,
    NutritionAnalysis,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
    WeeklyPriorityRecommendation,
)

from app.nutrition_rules.weekly_priority import (
    COPY_CATALOG,
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
from app.schemas import (
    BehaviorGoalCommandV1,
    PriorityV1,
    WeeklyPriorityAnalysisInputV1,
    WeeklyPriorityResultV1,
)
import app.services.weekly_priorities as weekly_priority_service
from app.services.weekly_priorities import (
    _accepted_goal_window,
    _empty_progress,
    _finalization_boundary,
    _goal_snapshot,
    _selection_input,
    RecommendationSourceValidation,
    evaluate_recommendation,
    command_goal,
    goal_history,
    process_due_goals,
    recompute_goal_progress,
    WeeklyPriorityError,
)
from app.api.routes.weekly_priorities import get_priority

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


def _trackable_recommendation_row(
    principal_id: UUID,
    source: WeeklyPriorityAnalysisInputV1,
    source_revision_id: UUID,
) -> WeeklyPriorityRecommendation:
    recommendation_id = uuid4()
    title, reason, action = COPY_CATALOG["fruit_vegetable_gap"]
    main = PriorityV1(
        rule_key="fruit_vegetable_gap",
        rank="main",
        category="positive",
        title_ar=title,
        reason_ar=reason,
        coverage_percent=100,
        complete_day_count=4,
        action_key="add_fruit_or_vegetable",
        action_ar=action,
        action_mode="add",
        goal_trackability="trackable",
        goal_unavailable_reason=None,
        goal_unavailable_copy_ar=None,
        rules_version=WEEKLY_PRIORITY_RULES_VERSION,
        copy_version=WEEKLY_PRIORITY_COPY_VERSION,
        facts_used=[
            {
                "metric_key": "group:fruit_vegetable_g_per_day",
                "value": 100,
                "unit": "g",
                "target": None,
                "comparison": "below_target",
                "period": "current",
            }
        ],
        evidence_refs=[],
        conflict_decisions=[],
    )
    result = WeeklyPriorityResultV1(
        recommendation_id=recommendation_id,
        source_analysis_id=source.source_analysis_id,
        source_analysis_revision=source.source_analysis_revision,
        period_start=source.period_start,
        period_end=source.period_end,
        generated_at=source.generated_at,
        expires_at=_finalization_boundary(source.period_end),
        status="selected",
        rules_version=WEEKLY_PRIORITY_RULES_VERSION,
        copy_version=WEEKLY_PRIORITY_COPY_VERSION,
        analysis_rules_version=source.analysis_rules_version,
        nutrition_registry_version=source.nutrition_registry_version,
        food_group_rules_version=source.food_group_rules_version,
        nova_rules_version=source.nova_rules_version,
        snapshot_schema_versions=source.snapshot_schema_versions,
        target_plan_refs=source.target_plan_refs,
        main=main,
        secondary=None,
        excluded_alternatives=[],
        none_reason=None,
        etag=f'"weekly-priority-{recommendation_id}"',
    )
    return WeeklyPriorityRecommendation(
        id=recommendation_id,
        principal_id=principal_id,
        source_analysis_revision_id=source_revision_id,
        source_analysis_id=source.source_analysis_id,
        source_analysis_revision=source.source_analysis_revision,
        period_start=source.period_start,
        period_end=source.period_end,
        as_of_diary_date=source.as_of_diary_date,
        evaluation_diary_date=source.as_of_diary_date,
        evaluation_mode="live",
        status="selected",
        rules_version=WEEKLY_PRIORITY_RULES_VERSION,
        copy_version=WEEKLY_PRIORITY_COPY_VERSION,
        analysis_rules_version=source.analysis_rules_version,
        source_versions={
            "nutrition_registry_version": source.nutrition_registry_version,
            "food_group_rules_version": source.food_group_rules_version,
            "nova_rules_version": source.nova_rules_version,
            "snapshot_schema_versions": source.snapshot_schema_versions,
        },
        result_document=result.model_dump(mode="json"),
        input_digest="1" * 64,
        content_hash="2" * 64,
        generated_at=source.generated_at,
        expires_at=result.expires_at,
    )


def _persist_trackable_graph(
    session: Session,
) -> tuple[
    UUID,
    WeeklyPriorityAnalysisInputV1,
    NutritionAnalysis,
    NutritionAnalysisRevision,
    WeeklyPriorityRecommendation,
]:
    principal_id, analysis_id, revision_id = uuid4(), uuid4(), uuid4()
    source = WeeklyPriorityAnalysisInputV1.model_validate(
        _persisted_producer_document(principal_id, analysis_id)
    )
    days = []
    for index, day in enumerate(source.days):
        if day.logging_status != "complete":
            days.append(day)
            continue
        days.append(
            day.model_copy(
                update={
                    "metric_values": [
                        day.metric_values[0].model_copy(
                            update={
                                "metric_key": "group:fruit_vegetable_g_per_day",
                                "value": 100.0 if index == 0 else 0.0,
                                "value_state": "known",
                                "unit": "g",
                            }
                        )
                    ]
                }
            )
        )
    source = source.model_copy(update={"days": days})
    document = source.model_dump(mode="json")
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    session.add(Principal(id=principal_id))
    session.commit()
    series = NutritionAnalysis(
        id=analysis_id,
        principal_id=principal_id,
        as_of_diary_date=source.as_of_diary_date,
        calendar_timezone="Asia/Riyadh",
    )
    session.add(series)
    session.commit()
    revision = NutritionAnalysisRevision(
        id=revision_id,
        analysis_id=analysis_id,
        principal_id=principal_id,
        revision=1,
        period_start=source.period_start,
        period_end=source.period_end,
        previous_period_start=source.previous_period_start,
        previous_period_end=source.previous_period_end,
        analysis_rules_version=source.analysis_rules_version,
        source_versions={},
        source_input_hash="1" * 64,
        content_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        complete_day_count=4,
        previous_complete_day_count=0,
        result_status="available",
        analysis_document=document,
    )
    session.add(revision)
    session.commit()
    series.current_revision_id = revision.id
    series.current_revision_number = revision.revision
    session.add(series)
    recommendation = _trackable_recommendation_row(principal_id, source, revision.id)
    session.add(recommendation)
    session.commit()
    return principal_id, source, series, revision, recommendation


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


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("stale", "PRIORITY_SOURCE_STALE"),
        ("superseded", "PRIORITY_SOURCE_SUPERSEDED"),
        ("unsupported", "UNSUPPORTED_PRIORITY_VERSION"),
    ],
)
def test_current_priority_route_emits_distinct_source_errors(
    mutation: str, expected_code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(
        weekly_priority_service,
        "get_settings",
        lambda: SimpleNamespace(weekly_priorities_display_enabled=True),
    )
    with Session(engine) as session:
        principal_id, _source, _series, revision, recommendation = (
            _persist_trackable_graph(session)
        )
        if mutation == "unsupported":
            recommendation.rules_version = "w3-priority-1.0.0"
            session.add(recommendation)
        else:
            session.add(
                NutritionAnalysisRevisionEvent(
                    revision_id=revision.id,
                    principal_id=principal_id,
                    event_type=(
                        "day_reopened"
                        if mutation == "stale"
                        else "superseded_by_revision"
                    ),
                    successor_revision_id=None,
                    reason="formal-review-source-oracle",
                )
            )
        session.commit()
        response = get_priority(PrincipalContext(principal_id), session)
        assert response.status_code in {409, 422}
        payload = json.loads(response.body)
        assert payload["error"]["code"] == expected_code


def test_idempotent_accept_replay_precedes_newer_source_rejection() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        principal_id, source, series, _revision, recommendation = _persist_trackable_graph(
            session
        )
        goal_id = uuid4()
        now = datetime.now(timezone.utc)
        goal = BehaviorGoal(
            id=goal_id,
            principal_id=principal_id,
            recommendation_id=recommendation.id,
            root_goal_id=goal_id,
            sequence_number=1,
            state="offered",
            version=1,
            rule_key="fruit_vegetable_gap",
            action_key="add_fruit_or_vegetable",
            weekly_target_count=3,
            day_mask=[],
            window_start=source.period_start,
            window_end=source.period_end,
            rules_version=WEEKLY_PRIORITY_RULES_VERSION,
            copy_version=WEEKLY_PRIORITY_COPY_VERSION,
            progress_document={},
            progress_revision=1,
            reminder_preference="disabled",
        )
        goal.progress_document = _empty_progress(
            goal, source.as_of_diary_date, now
        ).model_dump(mode="json")
        session.add(goal)
        session.commit()
        command = BehaviorGoalCommandV1(event="accept", expected_version=1)
        original, status, replayed = command_goal(
            session, PrincipalContext(principal_id), goal_id, command, "accept-on-r1"
        )
        assert status == 200 and not replayed

        next_document = source.model_copy(
            update={"source_analysis_revision": 2, "generated_at": datetime.now(timezone.utc)}
        ).model_dump(mode="json")
        next_revision = NutritionAnalysisRevision(
            id=uuid4(),
            analysis_id=series.id,
            principal_id=principal_id,
            revision=2,
            period_start=source.period_start,
            period_end=source.period_end,
            previous_period_start=source.previous_period_start,
            previous_period_end=source.previous_period_end,
            analysis_rules_version=source.analysis_rules_version,
            source_versions={},
            source_input_hash="3" * 64,
            content_hash="4" * 64,
            complete_day_count=4,
            previous_complete_day_count=0,
            result_status="available",
            analysis_document=next_document,
        )
        session.add(next_revision)
        session.commit()
        series.current_revision_id = next_revision.id
        series.current_revision_number = 2
        session.add(series)
        session.commit()

        replay, replay_status, replayed = command_goal(
            session, PrincipalContext(principal_id), goal_id, command, "accept-on-r1"
        )
        assert replay_status == 200 and replayed and replay == original
        with pytest.raises(WeeklyPriorityError) as captured:
            command_goal(
                session,
                PrincipalContext(principal_id),
                goal_id,
                BehaviorGoalCommandV1(event="edit", expected_version=2),
                "new-command-on-r2",
            )
        assert captured.value.code == "PRIORITY_SOURCE_SUPERSEDED"


def test_scheduled_job_revisits_finalized_goal_once_for_new_plan032_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        principal_id, source, series, revision, recommendation = _persist_trackable_graph(
            session
        )
        after_boundary = _finalization_boundary(source.period_end) + timedelta(minutes=1)
        source = source.model_copy(update={"generated_at": after_boundary})
        revision.analysis_document = source.model_dump(mode="json")
        recommendation.generated_at = after_boundary
        session.add(revision)
        session.add(recommendation)
        goal_id = uuid4()
        progress = {
            **_empty_progress(
                BehaviorGoal(
                    id=goal_id,
                    principal_id=principal_id,
                    recommendation_id=recommendation.id,
                    root_goal_id=goal_id,
                    sequence_number=1,
                    state="completed",
                    version=1,
                    rule_key="fruit_vegetable_gap",
                    action_key="add_fruit_or_vegetable",
                    weekly_target_count=1,
                    day_mask=[],
                    window_start=source.period_start,
                    window_end=source.period_end,
                    rules_version=WEEKLY_PRIORITY_RULES_VERSION,
                    copy_version=WEEKLY_PRIORITY_COPY_VERSION,
                    progress_document={},
                    progress_revision=1,
                    reminder_preference="disabled",
                    completed_at=after_boundary - timedelta(days=1),
                ),
                source.as_of_diary_date,
                after_boundary,
            ).model_dump(mode="json"),
            "progress_count": 1,
            "progress_percent": 100,
            "complete_day_count": 4,
            "unregistered_day_count": 3,
            "status": "achieved",
        }
        goal = BehaviorGoal(
            id=goal_id,
            principal_id=principal_id,
            recommendation_id=recommendation.id,
            root_goal_id=goal_id,
            sequence_number=1,
            state="completed",
            version=1,
            rule_key="fruit_vegetable_gap",
            action_key="add_fruit_or_vegetable",
            weekly_target_count=1,
            day_mask=[],
            window_start=source.period_start,
            window_end=source.period_end,
            rules_version=WEEKLY_PRIORITY_RULES_VERSION,
            copy_version=WEEKLY_PRIORITY_COPY_VERSION,
            progress_document=progress,
            progress_revision=1,
            last_progress_analysis_id=series.id,
            last_progress_analysis_revision_id=revision.id,
            last_progress_analysis_revision=1,
            reminder_preference="disabled",
            completed_at=after_boundary - timedelta(days=1),
        )
        session.add(goal)
        session.commit()
        monkeypatch.setattr(weekly_priority_service, "utcnow", lambda: after_boundary)
        monkeypatch.setattr(
            weekly_priority_service,
            "diary_calendar_authority",
            lambda: SimpleNamespace(current_diary_date=source.period_end + timedelta(days=2)),
        )
        first = process_due_goals(session)
        assert first["finalized"] == 1
        session.refresh(goal)
        assert goal.reviewed_at.replace(tzinfo=timezone.utc) == after_boundary

        changed_days = [
            day.model_copy(
                update={
                    "logging_status_version": day.logging_status_version + 1,
                    "metric_values": [
                        fact.model_copy(update={"value": 0.0})
                        for fact in day.metric_values
                    ],
                }
            )
            if day.logging_status == "complete"
            else day
            for day in source.days
        ]
        advanced = source.model_copy(
            update={
                "source_analysis_revision": 2,
                "generated_at": after_boundary + timedelta(minutes=1),
                "days": changed_days,
            }
        )
        next_revision = NutritionAnalysisRevision(
            id=uuid4(),
            analysis_id=series.id,
            principal_id=principal_id,
            revision=2,
            period_start=advanced.period_start,
            period_end=advanced.period_end,
            previous_period_start=advanced.previous_period_start,
            previous_period_end=advanced.previous_period_end,
            analysis_rules_version=advanced.analysis_rules_version,
            source_versions={},
            source_input_hash="5" * 64,
            content_hash="6" * 64,
            complete_day_count=4,
            previous_complete_day_count=0,
            result_status="available",
            analysis_document=advanced.model_dump(mode="json"),
        )
        session.add(next_revision)
        session.commit()
        series.current_revision_id = next_revision.id
        series.current_revision_number = 2
        session.add(series)
        session.commit()
        second = process_due_goals(session)
        assert second["recomputed"] == 1
        session.refresh(goal)
        assert goal.last_progress_analysis_revision_id == next_revision.id
        events = session.exec(
            sql_select(BehaviorGoalHistory).where(BehaviorGoalHistory.goal_id == goal.id)
        ).all()
        assert {item.event_type for item in events} == {
            "finalized_completed",
            "historical_evidence_changed",
        }
        third = process_due_goals(session)
        assert third["processed"] == 0
        assert len(
            session.exec(
                sql_select(BehaviorGoalHistory).where(
                    BehaviorGoalHistory.goal_id == goal.id
                )
            ).all()
        ) == 2


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
        # The API reads immutable history rows directly; repository ownership
        # constraints are rehearsed separately on PostgreSQL.
        for index in range(101):
            goal_id = uuid4()
            start = date(2026, 1, 1) + timedelta(days=index * 7)
            session.add(
                BehaviorGoalHistory(
                    goal_id=goal_id,
                    principal_id=principal_id,
                    root_goal_id=goal_id,
                    sequence_number=1,
                    goal_version=1,
                    event_type="end",
                    from_state="active",
                    to_state="ended",
                    actor_type="owner",
                    occurred_at=now + timedelta(seconds=index),
                    terms_progress_snapshot={
                        "goal_id": str(goal_id),
                        "recommendation_id": str(recommendation_id),
                        "root_goal_id": str(goal_id),
                        "previous_goal_id": None,
                        "sequence_number": 1,
                        "state": "ended",
                        "version": 1,
                        "rule_key": "fruit_vegetable_gap",
                        "action_key": "add_fruit_or_vegetable",
                        "action_copy_ar": "أضف حصة من الخضار أو الفاكهة.",
                        "goal_trackability": "trackable",
                        "goal_unavailable_reason": None,
                        "informational_copy_ar": None,
                        "weekly_target_count": 3,
                        "scheduled_day_mask": [],
                        "owner_note": None,
                        "reminder_preference": "disabled",
                        "window_start": start.isoformat(),
                        "window_end": (start + timedelta(days=6)).isoformat(),
                        "rules_version": "w3-priority-1.1.0",
                        "copy_version": "w3-priority-ar-1.1.0",
                        "source_analysis_id": str(uuid4()),
                        "source_analysis_revision_id": str(uuid4()),
                        "source_analysis_revision": 1,
                        "analysis_rules_version": "w3-analysis-1.1.0",
                        "source_versions": {},
                        "last_progress_analysis_id": None,
                        "last_progress_analysis_revision_id": None,
                        "last_progress_analysis_revision": None,
                        "progress_revision": 1,
                        "progress": {
                            **progress,
                            "window_start": start.isoformat(),
                            "window_end": (start + timedelta(days=6)).isoformat(),
                        },
                        "offered_at": now.isoformat(),
                        "accepted_at": now.isoformat(),
                        "deferred_at": None,
                        "deferred_until": None,
                        "changed_at": None,
                        "paused_at": None,
                        "resumed_at": None,
                        "completed_at": None,
                        "reviewed_at": None,
                        "rejected_at": None,
                        "ended_at": now.isoformat(),
                        "archived_at": None,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
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
        assert set(item.history_id for item in first.items).isdisjoint(
            item.history_id for item in second.items
        )


def test_goal_history_projection_is_immutable_after_current_goal_mutation() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        principal_id, source, _series, _revision, recommendation = (
            _persist_trackable_graph(session)
        )
        goal_id = uuid4()
        now = datetime.now(timezone.utc)
        goal = BehaviorGoal(
            id=goal_id,
            principal_id=principal_id,
            recommendation_id=recommendation.id,
            root_goal_id=goal_id,
            sequence_number=1,
            state="active",
            version=1,
            rule_key="fruit_vegetable_gap",
            action_key="add_fruit_or_vegetable",
            weekly_target_count=3,
            day_mask=[],
            window_start=source.period_start,
            window_end=source.period_end,
            rules_version=WEEKLY_PRIORITY_RULES_VERSION,
            copy_version=WEEKLY_PRIORITY_COPY_VERSION,
            progress_document={},
            progress_revision=1,
            reminder_preference="disabled",
            accepted_at=now,
        )
        goal.progress_document = _empty_progress(
            goal, source.as_of_diary_date, now
        ).model_dump(mode="json")
        session.add(goal)
        for version, event_type, state, progress_count in (
            (1, "accept", "active", 0),
            (2, "progress_updated", "active", 1),
            (3, "completed", "completed", 3),
            (4, "historical_evidence_changed", "completed", 2),
        ):
            goal.version = version
            goal.state = state
            goal.progress_revision = version
            goal.progress_document = {
                **goal.progress_document,
                "progress_count": progress_count,
                "progress_percent": round(progress_count * 100 / 3),
                "status": "achieved" if progress_count == 3 else "in_progress",
                "last_recomputed_at": (now + timedelta(minutes=version)).isoformat(),
            }
            if state == "completed":
                goal.completed_at = now + timedelta(minutes=version)
            session.add(
                BehaviorGoalHistory(
                    goal_id=goal.id,
                    principal_id=principal_id,
                    root_goal_id=goal.id,
                    sequence_number=1,
                    goal_version=version,
                    event_type=event_type,
                    from_state=None if version == 1 else "active",
                    to_state=state,
                    actor_type="owner" if version == 1 else "system",
                    terms_progress_snapshot=_goal_snapshot(goal, recommendation),
                    occurred_at=now + timedelta(minutes=version),
                )
            )
        session.add(goal)
        session.commit()
        before = goal_history(
            session, PrincipalContext(principal_id), 20, None
        ).model_dump(mode="json")
        goal.weekly_target_count = 7
        goal.day_mask = [0]
        goal.private_note = "mutable current row"
        goal.progress_document = {**goal.progress_document, "progress_count": 7}
        goal.updated_at = now + timedelta(days=1)
        session.add(goal)
        session.commit()
        after = goal_history(
            session, PrincipalContext(principal_id), 20, None
        ).model_dump(mode="json")
        assert after == before
        assert [item["snapshot"]["progress"]["progress_count"] for item in before["items"]] == [
            2,
            3,
            1,
            0,
        ]


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
    source_revision_id = uuid4()
    recommendation = _trackable_recommendation_row(
        principal_id, source, source_revision_id
    )
    validation = RecommendationSourceValidation(
        "VALID",
        revision=SimpleNamespace(
            id=source_revision_id,
            analysis_id=source.source_analysis_id,
            revision=source.source_analysis_revision,
        ),
        source=source,
    )
    goal_id = uuid4()
    goal = BehaviorGoal(
        id=goal_id,
        principal_id=principal_id,
        recommendation_id=recommendation.id,
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
    assert recompute_goal_progress(
        recorder,
        goal,
        source_override=source,
        recommendation=recommendation,
        source_validation=validation,
    )
    assert goal.state == "completed"
    completed_history = recorder.added[-1]
    assert completed_history.event_type == "completed"
    completed_snapshot = deepcopy(completed_history.terms_progress_snapshot)
    assert not recompute_goal_progress(
        recorder,
        goal,
        source_override=source,
        recommendation=recommendation,
        source_validation=validation,
    )

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
    assert recompute_goal_progress(
        recorder,
        goal,
        source_override=changed_source,
        recommendation=recommendation,
        source_validation=validation,
    )
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
    assert recompute_goal_progress(
        recorder,
        goal,
        source_override=restored_source,
        recommendation=recommendation,
        source_validation=validation,
    )
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
    assert recompute_goal_progress(
        recorder,
        goal,
        source_override=changed_source,
        recommendation=recommendation,
        source_validation=validation,
    )
    assert recorder.added[-1].event_type == "historical_evidence_changed"
    assert completed_history.terms_progress_snapshot == completed_snapshot
