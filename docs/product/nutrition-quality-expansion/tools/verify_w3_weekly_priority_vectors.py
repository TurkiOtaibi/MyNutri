#!/usr/bin/env python3
"""Standard-library reference oracle for Plan 033 design vectors."""

from __future__ import annotations

import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


TIER_ORDER = {"limit": 1, "positive": 2, "micronutrient": 3}
TERMINAL_GOAL_STATES = {"rejected", "completed", "ended", "archived"}


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
    if state != "eligible":
        return {"main": None, "secondary": None, "reason": state}
    if vector.get("complete_days", 4) < 4:
        return {"main": None, "secondary": None, "reason": "insufficient_complete_days"}
    candidates = [
        deepcopy(c)
        for c in vector.get("candidates", [])
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
        if candidate.get("conflict_group") == main.get("conflict_group"):
            continue
        if candidate.get("conflicts_with") == main["key"] or main.get("conflicts_with") == candidate["key"]:
            continue
        if vector.get("calories_relation") == "above_target" and candidate.get("action_mode") == "add":
            continue
        if candidate.get("secondary_justified") is True:
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
        ("active", "change"): "active",
        ("active", "pause"): "paused",
        ("paused", "resume"): "active",
        ("active", "complete"): "completed",
        ("completed", "evidence_reopened"): "active",
        ("active", "end"): "ended",
        ("paused", "end"): "ended",
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
        "evidence_reopened": "evidence_reopened",
        "end": "ended",
        "archive": "archived",
    }
    return goal_response(state, results[kind])


def validate(document: dict[str, Any]) -> tuple[int, list[str]]:
    failures: list[str] = []
    if document.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if not isinstance(document.get("seed"), int):
        failures.append("seed must be an integer")
    names: set[str] = set()
    passed = 0
    for vector in document.get("selection_vectors", []):
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
            continue
        names.add(name)
        for candidate in vector.get("candidates", []):
            if not math.isfinite(candidate.get("severity", 0)):
                failures.append(f"{name}: severity must be finite")
        actual = select(vector)
        if set(actual) != {"main", "secondary", "reason"}:
            failures.append(f"{name}: selection result shape violates capped contract")
        if actual != vector["expected"]:
            failures.append(f"{name}: expected {vector['expected']!r}, got {actual!r}")
        else:
            passed += 1
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
