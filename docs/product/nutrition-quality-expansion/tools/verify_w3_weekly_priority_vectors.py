#!/usr/bin/env python3
"""Standard-library reference oracle for Plan 033 design vectors."""

from __future__ import annotations

import json
import math
import sys
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any


RULE_META: dict[str, tuple[int, int, dict[str, str]]] = {
    "sodium_overage": (1, 10, {"replace": "replace_high_sodium_choice"}),
    "added_sugar_overage": (1, 20, {"replace": "replace_added_sugar_choice"}),
    "saturated_fat_overage": (1, 30, {"replace": "replace_saturated_fat_choice"}),
    "trans_fat_overage": (1, 40, {"replace": "replace_trans_fat_choice"}),
    "processed_meat_frequency": (1, 50, {"replace": "replace_processed_meat_choice"}),
    "sugary_drink_frequency": (1, 60, {"replace": "replace_sugary_drink_choice"}),
    "fruit_vegetable_gap": (2, 110, {"add": "add_fruit_or_vegetable", "replace": "replace_with_fruit_or_vegetable"}),
    "legumes_gap": (2, 120, {"add": "add_legumes", "replace": "replace_with_legumes"}),
    "whole_grain_share_gap": (2, 130, {"replace": "replace_with_whole_grain"}),
    "nuts_seeds_gap": (2, 140, {"add": "add_nuts_or_seeds", "replace": "replace_with_nuts_or_seeds"}),
    "seafood_gap": (2, 150, {"replace": "replace_with_seafood"}),
    "dairy_alternative_gap": (2, 160, {"add": "add_dairy_or_fortified_alternative", "replace": "replace_with_dairy_or_fortified_alternative"}),
    "fiber_gap": (2, 170, {"add": "add_fiber_source", "replace": "replace_with_fiber_source"}),
    "potassium_gap": (3, 210, {"review": "review_food_sources_potassium"}),
    "calcium_gap": (3, 220, {"review": "review_food_sources_calcium"}),
    "iron_gap": (3, 230, {"review": "review_food_sources_iron"}),
    "magnesium_gap": (3, 240, {"review": "review_food_sources_magnesium"}),
    "zinc_gap": (3, 250, {"review": "review_food_sources_zinc"}),
    "selenium_gap": (3, 260, {"review": "review_food_sources_selenium"}),
    "vitamin_b12_gap": (3, 270, {"review": "review_food_sources_vitamin_b12"}),
    "folate_dfe_gap": (3, 280, {"review": "review_food_sources_folate_dfe"}),
    "vitamin_a_rae_gap": (3, 290, {"review": "review_food_sources_vitamin_a_rae"}),
    "iodine_gap": (3, 300, {"review": "review_food_sources_iodine"}),
}
ALLOWED_INPUT_STATES = {
    "eligible",
    "invalid_analysis_input",
    "stale_analysis",
    "superseded_analysis",
    "safety_exclusion",
    "unsupported_version",
}
DAY_STATUSES = {"complete", "partial", "unregistered"}


def complete_days(vector: dict[str, Any]) -> int:
    days = vector.get("days")
    if days is None:
        value = vector.get("complete_days", 4)
        if not isinstance(value, int) or value < 0:
            raise ValueError("complete_days must be a non-negative integer")
        return value
    if len(days) != 7:
        raise ValueError("structured days must contain exactly seven records")
    parsed_dates: list[date] = []
    complete = 0
    for day in days:
        try:
            parsed_dates.append(date.fromisoformat(day["date"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("every structured day requires an ISO date") from error
        status = day.get("logging_status")
        if status not in DAY_STATUSES:
            raise ValueError(f"unknown logging_status: {status!r}")
        if day.get("analysis_eligible") is not (status == "complete"):
            raise ValueError("analysis_eligible must be true exactly for complete days")
        if (
            not isinstance(day.get("entry_count"), int)
            or isinstance(day["entry_count"], bool)
            or day["entry_count"] < 0
        ):
            raise ValueError("entry_count must be a non-negative integer")
        if status == "complete":
            complete += 1
    if len(set(parsed_dates)) != 7 or parsed_dates != sorted(parsed_dates):
        raise ValueError("structured day dates must be unique and sorted")
    if any(right - left != timedelta(days=1) for left, right in zip(parsed_dates, parsed_dates[1:])):
        raise ValueError("structured day dates must be consecutive")
    return complete


def normalize_candidate(
    candidate: dict[str, Any], vector: dict[str, Any], day_count: int
) -> dict[str, Any]:
    normalized = deepcopy(candidate)
    key = normalized.get("key")
    if key not in RULE_META:
        raise ValueError(f"unknown priority key: {key!r}")
    tier, order, actions = RULE_META[key]
    if "secondary_justified" in normalized:
        raise ValueError("secondary_justified is derived and cannot be supplied")
    if normalized.get("tier", tier) != tier:
        raise ValueError(f"{key}: tier does not match closed vocabulary")
    if normalized.get("taxonomy_order", order) != order:
        raise ValueError(f"{key}: taxonomy_order does not match closed vocabulary")
    action_mode = normalized.get("action_mode", "review" if tier == 3 else "replace")
    if action_mode not in actions:
        raise ValueError(f"{key}: action_mode does not match closed vocabulary")
    if normalized.get("action_key", actions[action_mode]) != actions[action_mode]:
        raise ValueError(f"{key}: action_key does not match closed vocabulary")
    normalized.update(
        tier=tier,
        taxonomy_order=order,
        action_mode=action_mode,
        action_key=actions[action_mode],
        evidence_dimension=normalized.get("evidence_dimension", key),
        complete_days=day_count,
    )
    if normalized.get("derive_from_days"):
        days = [d for d in vector.get("days", []) if d["logging_status"] == "complete"]
        metric_key = normalized["metric_key"]
        target = normalized["target"]
        if not math.isfinite(target) or target <= 0:
            raise ValueError(f"{key}: target must be finite and positive")
        values: list[float] = []
        known_entries = 0
        total_entries = 0
        for day in days:
            total_entries += day["entry_count"]
            known_count = day.get("known_metric_entry_count")
            if (
                not isinstance(known_count, int)
                or isinstance(known_count, bool)
                or not 0 <= known_count <= day["entry_count"]
            ):
                raise ValueError(
                    f"{key}: known_metric_entry_count must be between zero and entry_count"
                )
            known_entries += known_count
            if day["entry_count"] == 0:
                values.append(0.0)
            elif metric_key in day.get("metrics", {}):
                value = day["metrics"][metric_key]
                if (
                    known_count == 0
                    or not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                ):
                    raise ValueError(f"{key}: known metric value must be finite")
                values.append(value)
            elif known_count != 0:
                raise ValueError(f"{key}: known metric count requires a metric value")
        if not values:
            raise ValueError(f"{key}: no complete-day metric evidence")
        normalized["coverage"] = (
            100.0 if total_entries == 0 else 100.0 * known_entries / total_entries
        )
        average = sum(values) / len(values)
        normalized["severity"] = round((target - average) / target, 6)
    if not math.isfinite(normalized.get("severity", math.nan)):
        raise ValueError(f"{key}: severity must be finite")
    return normalized


def rejection_is_suppressed(
    context: dict[str, Any], candidates: list[dict[str, Any]]
) -> bool:
    required_text = (
        "rejected_principal_ref",
        "current_principal_ref",
        "rejected_rule_key",
        "current_rule_key",
        "rejected_rules_version",
        "current_rules_version",
        "rejected_action_key",
    )
    if any(not isinstance(context.get(field), str) or not context[field] for field in required_text):
        raise ValueError("rejection context requires explicit non-empty identity fields")
    for field in (
        "rejected_analysis_revision",
        "current_analysis_revision",
        "new_complete_dates_after_rejection",
    ):
        if (
            not isinstance(context.get(field), int)
            or isinstance(context[field], bool)
            or context[field] < 0
        ):
            raise ValueError("rejection context revisions and day count must be non-negative integers")
    rejected_severity = context.get("rejected_severity")
    if (
        not isinstance(rejected_severity, (int, float))
        or isinstance(rejected_severity, bool)
        or not math.isfinite(rejected_severity)
    ):
        raise ValueError("rejected_severity must be finite")
    same_scope = (
        context.get("rejected_principal_ref") == context.get("current_principal_ref")
        and context.get("rejected_rule_key") == context.get("current_rule_key")
        and context.get("rejected_rules_version") == context.get("current_rules_version")
    )
    if not same_scope:
        return False
    matching = [candidate for candidate in candidates if candidate["key"] == context.get("current_rule_key")]
    if len(matching) != 1:
        raise ValueError("rejection context must resolve exactly one current rule candidate")
    current = matching[0]
    later_revision = context.get("current_analysis_revision", 0) > context.get(
        "rejected_analysis_revision", 0
    )
    new_complete_day = context.get("new_complete_dates_after_rejection", 0) >= 1
    severity_changed = round(current["severity"] - rejected_severity, 6) >= 0.10
    action_changed = current["action_key"] != context.get("rejected_action_key")
    return not (later_revision and new_complete_day and (severity_changed or action_changed))


def eligible_candidate(candidate: dict[str, Any]) -> bool:
    base = (
        candidate.get("actionable") is True
        and candidate.get("coverage", 0) >= 75
        and candidate.get("complete_days", 4) >= 4
        and candidate.get("excluded") is not True
    )
    if not base:
        return False
    if candidate["tier"] == 1:
        return candidate.get("repeat_events", 0) >= 2 and candidate["severity"] >= 0.10
    if candidate["tier"] == 2:
        return candidate["severity"] >= 0.20
    return candidate["severity"] >= 0.20 and candidate.get("persistent_weeks", 0) >= 2


def rank_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        candidate["tier"],
        -candidate["severity"],
        -candidate.get("coverage", 0),
        candidate.get("taxonomy_order", 9999),
        candidate["key"],
    )


def select(vector: dict[str, Any]) -> dict[str, Any]:
    state = vector.get("input_state", "eligible")
    if state not in ALLOWED_INPUT_STATES:
        raise ValueError(f"unknown input_state: {state!r}")
    if state != "eligible":
        return {"main": None, "secondary": None, "reason": state}
    day_count = complete_days(vector)
    if day_count < 4:
        return {"main": None, "secondary": None, "reason": "insufficient_complete_days"}
    normalized = [normalize_candidate(c, vector, day_count) for c in vector.get("candidates", [])]
    if vector.get("rejection_context") and rejection_is_suppressed(
        vector["rejection_context"], normalized
    ):
        return {
            "main": None,
            "secondary": None,
            "reason": "rejected_goal_suppression",
        }
    candidates = [
        c
        for c in normalized
        if eligible_candidate(c)
        and not (
            vector.get("calories_relation") == "above_target"
            and c.get("action_mode") == "add"
        )
    ]
    candidates.sort(key=rank_key)
    if not candidates:
        return {"main": None, "secondary": None, "reason": "no_eligible_priority"}
    main = candidates[0]
    secondary = None
    for candidate in candidates[1:]:
        if candidate["severity"] < 0.25:
            continue
        if candidate.get("conflict_group") == main.get("conflict_group"):
            continue
        if candidate["evidence_dimension"] == main["evidence_dimension"]:
            continue
        if candidate["action_key"] == main["action_key"]:
            continue
        if candidate.get("conflicts_with") == main["key"] or main.get("conflicts_with") == candidate["key"]:
            continue
        if vector.get("calories_relation") == "above_target" and candidate.get("action_mode") == "add":
            continue
        secondary = candidate
        break
    return {"main": main["key"], "secondary": secondary["key"] if secondary else None, "reason": "selected"}


def goal_response(state: dict[str, Any], result: str) -> dict[str, Any]:
    return {
        "result": result,
        "state": state["state"],
        "version": state["version"],
        "progress": state.get("progress"),
        "midweek_reminders": state.get("midweek_reminders", 0),
        "endweek_reviews": state.get("endweek_reviews", 0),
    }


def apply_goal_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event.get("expected_version") != state["version"]:
        return goal_response(state, "stale_version_conflict")
    kind = event["type"]
    current = state["state"]
    transitions = {
        ("offered", "accept"): "active",
        ("offered", "edit"): "active",
        ("offered", "defer"): "deferred",
        ("offered", "reject"): "rejected",
        ("deferred", "accept"): "active",
        ("deferred", "reject"): "rejected",
        ("active", "change"): "active",
        ("active", "pause"): "paused",
        ("paused", "resume"): "active",
        ("active", "complete"): "completed",
        ("active", "finalize_incomplete"): "incomplete",
        ("paused", "finalize_incomplete"): "incomplete",
        ("completed", "evidence_reopened"): "active",
        ("active", "end"): "ended",
        ("paused", "end"): "ended",
        ("incomplete", "end"): "ended",
        ("rejected", "archive"): "archived",
        ("completed", "archive"): "archived",
        ("ended", "archive"): "archived",
    }
    if kind == "progress":
        if current != "active":
            return goal_response(state, "suppressed")
        state["progress"] = event.get("derived_progress")
        state["version"] += 1
        return goal_response(state, "progress_updated")
    if kind == "midweek_reminder":
        if current != "active" or not event.get("midweek_eligible") or state.get("progress") not in {0, 0.0} or state.get("midweek_reminders", 0) >= 1 or event.get("opted_out"):
            return goal_response(state, "suppressed")
        state["midweek_reminders"] = 1
        state["version"] += 1
        return goal_response(state, "sent")
    if kind == "endweek_review":
        if current not in {"active", "paused"} or not event.get("endweek_eligible") or state.get("endweek_reviews", 0) >= 1:
            return goal_response(state, "suppressed")
        state["endweek_reviews"] = 1
        state["version"] += 1
        return goal_response(state, "sent")
    if kind == "finalize_incomplete" and (
        current not in {"active", "paused"}
        or event.get("window_ended") is not True
        or event.get("target_reached") is not False
    ):
        return goal_response(state, "invalid_transition")
    if (
        kind in {"accept", "edit"}
        and current in {"offered", "deferred"}
        and state.get("other_primary_exists") is True
    ):
        return goal_response(state, "primary_goal_exists")
    next_state = transitions.get((current, kind))
    if next_state is None:
        return goal_response(state, "invalid_transition")
    state["state"] = next_state
    state["version"] += 1
    results = {
        "accept": "accepted",
        "edit": "edited",
        "defer": "deferred",
        "reject": "rejected",
        "change": "changed",
        "pause": "paused",
        "resume": "resumed",
        "complete": "completed",
        "finalize_incomplete": "finalized_incomplete",
        "evidence_reopened": "evidence_reopened",
        "end": "ended",
        "archive": "archived",
    }
    return goal_response(state, results[kind])


def repeat_response(
    state: dict[str, Any], result: str, new_goal: dict[str, Any] | None = None
) -> dict[str, Any]:
    source = state["source_goal"]
    priority = state["current_priority"]
    return {
        "result": result,
        "source_goal_id": source["goal_id"],
        "source_state": source["state"],
        "source_version": source["version"],
        "source_window": [source["window_start"], source["window_end"]],
        "source_progress_status": source["progress_status"],
        "source_history_count": source["history_count"],
        "source_midweek_reminders": source.get("midweek_reminders", 0),
        "source_endweek_reviews": source.get("endweek_reviews", 0),
        "new_goal": deepcopy(new_goal),
        "created_goal_count": len(state.get("created_goal_ids", [])),
        "priority_main": priority.get("main_rule_key"),
        "priority_secondary": priority.get("secondary_rule_key"),
    }


def apply_repeat_event(
    state: dict[str, Any],
    event: dict[str, Any],
    replays: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if event.get("type") != "repeat":
        return repeat_response(state, "goal_state_conflict")
    key = event.get("idempotency_key")
    if not isinstance(key, str) or not key:
        raise ValueError("repeat requires a non-empty idempotency key")
    request_identity = {
        "source_goal_id": state["source_goal"]["goal_id"],
        "expected_version": event.get("expected_version"),
        "repeat_mode": event.get("repeat_mode"),
        "weekly_target_count": event.get("weekly_target_count"),
        "captured_diary_date": state["captured_diary_date"],
        "recommendation_id": state["current_priority"].get("recommendation_id"),
    }
    if key in replays:
        recorded = replays[key]
        if recorded["request"] != request_identity:
            return repeat_response(state, "idempotency_key_conflict")
        return deepcopy(recorded["response"])
    source = state["source_goal"]
    if event.get("expected_version") != source["version"]:
        return repeat_response(state, "goal_version_conflict")
    if source["state"] != "incomplete":
        return repeat_response(state, "goal_state_conflict")
    captured = date.fromisoformat(state["captured_diary_date"])
    old_start = date.fromisoformat(source["window_start"])
    old_end = date.fromisoformat(source["window_end"])
    if old_end - old_start != timedelta(days=6) or captured <= old_end:
        return repeat_response(state, "goal_state_conflict")
    if source["progress_status"] not in {"not_yet_reached", "insufficient_evidence"}:
        return repeat_response(state, "goal_state_conflict")
    if state.get("created_goal_ids"):
        return repeat_response(state, "goal_version_conflict")
    if state.get("other_primary_exists") is True:
        return repeat_response(state, "primary_goal_exists")
    priority = state["current_priority"]
    if (
        priority.get("status") != "selected"
        or priority.get("main_rule_key") != source["rule_key"]
        or priority.get("rules_version") != source["rules_version"]
        or priority.get("action_key") != source["action_key"]
    ):
        return repeat_response(state, "goal_repeat_priority_conflict")
    mode = event.get("repeat_mode")
    if mode == "same":
        if event.get("weekly_target_count") is not None:
            return repeat_response(state, "goal_state_conflict")
        new_target = source["weekly_target_count"]
        result = "repeated"
    elif mode == "reduce":
        new_target = event.get("weekly_target_count")
        if (
            not isinstance(new_target, int)
            or isinstance(new_target, bool)
            or not 1 <= new_target < source["weekly_target_count"]
        ):
            return repeat_response(state, "goal_state_conflict")
        result = "reduced_and_repeated"
    else:
        return repeat_response(state, "goal_state_conflict")
    new_goal_id = event.get("new_goal_id")
    if (
        not isinstance(new_goal_id, str)
        or not new_goal_id
        or new_goal_id == source["goal_id"]
        or new_goal_id in state.get("created_goal_ids", [])
    ):
        raise ValueError("repeat new_goal_id must be unique and distinct")
    old_snapshot = deepcopy(source)
    new_start = max(captured, old_end + timedelta(days=1))
    new_goal = {
        "goal_id": new_goal_id,
        "root_goal_id": old_snapshot.get("root_goal_id", old_snapshot["goal_id"]),
        "previous_goal_id": old_snapshot["goal_id"],
        "sequence_number": old_snapshot.get("sequence_number", 1) + 1,
        "state": "active",
        "version": 1,
        "window_start": new_start.isoformat(),
        "window_end": (new_start + timedelta(days=6)).isoformat(),
        "progress": 0,
        "progress_status": "unknown",
        "weekly_target_count": new_target,
        "rule_key": source["rule_key"],
        "action_key": source["action_key"],
        "rules_version": source["rules_version"],
        "recommendation_id": priority["recommendation_id"],
        "history_count": 1,
        "midweek_reminders": 0,
        "endweek_reviews": 0,
    }
    state.setdefault("created_goal_ids", []).append(new_goal_id)
    state["new_goal"] = deepcopy(new_goal)
    response = repeat_response(state, result, new_goal)
    replays[key] = {"request": request_identity, "response": deepcopy(response)}
    return response


def evaluate_progress(vector: dict[str, Any]) -> dict[str, Any]:
    target = vector.get("target_count")
    if not isinstance(target, int) or not 1 <= target <= 7:
        raise ValueError("progress target_count must be an integer from 1 to 7")
    complete = 0
    progress = 0
    for day in vector.get("days", []):
        status = day.get("logging_status")
        if status not in DAY_STATUSES:
            raise ValueError(f"unknown logging_status: {status!r}")
        if status == "complete":
            complete += 1
            if day.get("qualifies") is True:
                progress += 1
    if progress >= target:
        status = "achieved"
    elif vector.get("window_ended") and complete < 4:
        status = "insufficient_evidence"
    elif complete:
        status = "not_yet_reached" if vector.get("window_ended") else "in_progress"
    else:
        status = "unknown"
    return {
        "progress_count": progress,
        "target_count": target,
        "complete_day_count": complete,
        "progress_percent": min(100, round(100 * progress / target)),
        "status": status,
    }


def validate(document: dict[str, Any]) -> tuple[int, list[str]]:
    failures: list[str] = []
    if document.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if not isinstance(document.get("seed"), int):
        failures.append("seed must be an integer")
    names: set[str] = set()
    passed = 0
    selection_vectors = document.get("selection_vectors", [])
    for vector in selection_vectors:
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        try:
            actual = select(vector)
        except (KeyError, TypeError, ValueError) as error:
            failures.append(f"{name}: invalid selection vector: {error}")
            continue
        if set(actual) != {"main", "secondary", "reason"}:
            failures.append(f"{name}: selection result shape violates capped contract")
        if actual != vector["expected"]:
            failures.append(f"{name}: expected {vector['expected']!r}, got {actual!r}")
        else:
            passed += 1
    selections_by_name = {vector["name"]: vector for vector in selection_vectors}
    for vector in document.get("goal_vectors", []):
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        state = deepcopy(vector["initial"])
        ok = True
        for index, event in enumerate(vector["events"], start=1):
            actual = apply_goal_event(state, event)
            if actual != event["expected"]:
                failures.append(f"{name} event {index}: expected {event['expected']!r}, got {actual!r}")
                ok = False
        if ok:
            passed += 1
    repeat_vectors = document.get("repeat_vectors", [])
    for vector in repeat_vectors:
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        state = deepcopy(vector["initial"])
        replays: dict[str, dict[str, Any]] = {}
        ok = True
        for index, event in enumerate(vector["events"], start=1):
            source_before = deepcopy(state["source_goal"])
            try:
                actual = apply_repeat_event(state, event, replays)
            except (KeyError, TypeError, ValueError) as error:
                failures.append(f"{name} event {index}: invalid repeat vector: {error}")
                ok = False
                continue
            if actual != event["expected"]:
                failures.append(
                    f"{name} event {index}: expected {event['expected']!r}, got {actual!r}"
                )
                ok = False
            if actual["result"] in {"repeated", "reduced_and_repeated"} and state["source_goal"] != source_before:
                failures.append(f"{name} event {index}: repeat mutated frozen source goal")
                ok = False
        if ok:
            passed += 1
    for vector in document.get("progress_vectors", []):
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        try:
            actual = evaluate_progress(vector)
        except (KeyError, TypeError, ValueError) as error:
            failures.append(f"{name}: invalid progress vector: {error}")
            continue
        if actual != vector["expected"]:
            failures.append(f"{name}: expected {vector['expected']!r}, got {actual!r}")
        else:
            passed += 1
    for vector in document.get("mutation_vectors", []):
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        try:
            mutated = deepcopy(selections_by_name[vector["base_vector"]])
            if vector.get("candidate_index") is None:
                mutated[vector["field"]] = vector["value"]
            else:
                mutated["candidates"][vector["candidate_index"]][vector["field"]] = vector["value"]
            select(mutated)
        except (KeyError, TypeError, ValueError) as error:
            if vector["expected_error"] not in str(error):
                failures.append(f"{name}: wrong mutation error: {error}")
            else:
                passed += 1
        else:
            failures.append(f"{name}: mutation was accepted")
    repeats_by_name = {vector["name"]: vector for vector in repeat_vectors}
    for vector in document.get("repeat_mutation_vectors", []):
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        try:
            mutated = deepcopy(repeats_by_name[vector["base_vector"]])
            mutated["events"][vector["event_index"]][vector["field"]] = vector["value"]
            apply_repeat_event(mutated["initial"], mutated["events"][0], {})
        except (KeyError, TypeError, ValueError) as error:
            if vector["expected_error"] not in str(error):
                failures.append(f"{name}: wrong repeat mutation error: {error}")
            else:
                passed += 1
        else:
            failures.append(f"{name}: repeat mutation was accepted")
    if not names:
        failures.append("vectors must be non-empty")
    return passed, failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_w3_weekly_priority_vectors.py VECTORS.json", file=sys.stderr)
        return 2
    try:
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        passed, failures = validate(document)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"plan033: invalid vector document: {error}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"plan033: {passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
