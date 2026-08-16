#!/usr/bin/env python3
"""Reference oracle for Plan 031 day-logging-status golden vectors.

This standard-library tool is design evidence. Application code must never import it.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


def public_status(state: dict[str, Any]) -> str:
    if state["record"]:
        return state["persisted_status"]
    return "partial" if state["entry_count"] > 0 else "unregistered"


def response(state: dict[str, Any], result: str) -> dict[str, Any]:
    return {
        "result": result,
        "public_status": public_status(state),
        "persisted_status": state["persisted_status"] if state["record"] else None,
        "entry_count": state["entry_count"],
        "version": state["version"],
    }


def apply_event(
    state: dict[str, Any],
    event: dict[str, Any],
    replays: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    kind = event["type"]

    if kind == "read":
        return response(state, "projected")

    if event.get("date_relation", "current") == "future":
        return response(state, "future_rejected")

    key = event.get("idempotency_key")
    replay_key = (kind, key) if key else None
    request_identity = {"type": kind, "expected_version": event.get("expected_version")}
    if replay_key and replay_key in replays:
        recorded = replays[replay_key]
        if recorded["request"] != request_identity:
            return response(state, "idempotency_key_conflict")
        replayed = deepcopy(recorded["response"])
        replayed["result"] = "replayed"
        return replayed

    if event.get("expected_version") != state["version"]:
        return response(state, "stale_version_conflict")

    current = public_status(state)
    if kind in {"create_entry", "edit_entry", "delete_entry"} and current == "complete":
        result = response(state, "day_complete_conflict")
    elif kind == "create_entry":
        state.update(record=True, persisted_status="partial")
        state["entry_count"] += 1
        state["version"] += 1
        result = response(state, "created")
    elif kind == "edit_entry":
        if state["entry_count"] == 0:
            result = response(state, "entry_not_found")
        else:
            state.update(record=True, persisted_status="partial")
            state["version"] += 1
            result = response(state, "edited")
    elif kind == "delete_entry":
        if state["entry_count"] == 0:
            result = response(state, "entry_not_found")
        else:
            state.update(record=True, persisted_status="partial")
            state["entry_count"] -= 1
            state["version"] += 1
            result = response(state, "deleted")
    elif kind == "complete":
        if current == "complete":
            result = response(state, "no_change")
        else:
            state.update(record=True, persisted_status="complete")
            state["version"] += 1
            result = response(state, "completed")
    elif kind == "reopen":
        if current != "complete":
            result = response(state, "no_change")
        else:
            state.update(record=True, persisted_status="partial")
            state["version"] += 1
            result = response(state, "reopened")
    else:
        raise ValueError(f"unknown event type: {kind}")

    if replay_key and result["result"] not in {
        "future_rejected",
        "stale_version_conflict",
        "day_complete_conflict",
        "entry_not_found",
        "idempotency_key_conflict",
    }:
        replays[replay_key] = {"request": request_identity, "response": deepcopy(result)}
    return result


def validate_document(document: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if document.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if not isinstance(document.get("seed"), int):
        failures.append("seed must be an integer")
    vectors = document.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        failures.append("vectors must be a non-empty list")
        return failures

    names: set[str] = set()
    for vector in vectors:
        name = vector.get("name", "<unnamed>")
        if name in names:
            failures.append(f"duplicate vector name: {name}")
        names.add(name)
        state = deepcopy(vector["initial"])
        replays: dict[tuple[str, str], dict[str, Any]] = {}
        for index, event in enumerate(vector["events"], start=1):
            actual = apply_event(state, event, replays)
            expected = event["expected"]
            if actual != expected:
                failures.append(
                    f"{name} event {index}: expected {expected!r}, got {actual!r}"
                )
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_w2_day_logging_status_vectors.py VECTORS.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        failures = validate_document(document)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"plan031: invalid vector document: {error}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"FAIL: {failure}")
    passed = len(document["vectors"]) - len(failures)
    print(f"plan031: {passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
