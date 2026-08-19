#!/usr/bin/env python3
"""Standard-library oracle for the frozen PLAN 032 design corpus."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any


TIMEZONE = "Asia/Riyadh"
ANALYSIS_VERSION = "w3-analysis-1.1.0"
MIN_COMPLETE_DAYS = 4
LIMITED_COVERAGE = 50.0
STRONG_COVERAGE = 75.0
MAX_COMPARISON_COVERAGE_GAP = 10.0
MATERIAL_TARGET_DELTA = 0.10
CONTRIBUTOR_CAP = 5
REQUIRED_MUTATIONS = {
    "wrong_riyadh_window",
    "sunday_aligned",
    "unknown_as_zero",
    "wrong_coverage_denominator",
    "swap_periods",
    "material_threshold_20",
    "one_period_persistence",
    "reverse_tie_order",
    "accept_version_mismatch",
    "mutate_finalized_history",
    "scalar_minimum_for_range",
    "invent_range_tolerance",
    "choose_incompatible_target",
    "nonnull_incompatible_target",
    "duplicate_stale_count",
    "coverage_boundary_shift",
    "latency_boundary_shift",
}


def round6(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def iso(value: date) -> str:
    return value.isoformat()


def windows(as_of: str, mutation: str | None) -> dict[str, str]:
    end = date.fromisoformat(as_of)
    if mutation == "wrong_riyadh_window":
        end -= timedelta(days=1)
    if mutation == "sunday_aligned":
        start = end - timedelta(days=(end.weekday() + 1) % 7)
        end = start + timedelta(days=6)
    else:
        start = end - timedelta(days=6)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    return {
        "period_start": iso(start),
        "period_end": iso(end),
        "previous_period_start": iso(previous_start),
        "previous_period_end": iso(previous_end),
    }


def coverage(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    complete_days = [day for day in payload["days"] if day["status"] == "complete"]
    total = sum(len(day["values"]) for day in complete_days)
    known = sum(value is not None for day in complete_days for value in day["values"])
    if mutation == "unknown_as_zero":
        known = total
    numeric_values: list[float] = []
    for day in complete_days:
        values = day["values"]
        finite = [float(value) for value in values if value is not None]
        if mutation == "unknown_as_zero" and values:
            finite = [0.0 if value is None else float(value) for value in values]
        if not values:
            numeric_values.append(0.0)
        elif finite:
            numeric_values.append(sum(finite))
    if not complete_days:
        percent = None
    elif mutation == "wrong_coverage_denominator":
        percent = round6(known / len(complete_days) * 100)
    elif total == 0:
        percent = 100.0
    else:
        percent = round6(known / total * 100)
    average = round6(sum(numeric_values) / len(numeric_values)) if numeric_values else None
    if len(complete_days) < MIN_COMPLETE_DAYS or percent is None or percent < LIMITED_COVERAGE:
        confidence = "unavailable"
    elif percent < STRONG_COVERAGE:
        confidence = "limited"
    else:
        confidence = "strong"
    if average is None:
        qualifier = "unavailable"
    elif total == 0 or known == total:
        qualifier = "exact"
    else:
        qualifier = "at_least"
    return {
        "complete_day_count": len(complete_days),
        "total_entry_count": total,
        "known_entry_count": known,
        "numeric_day_count": len(numeric_values),
        "coverage_percent": percent,
        "value": average,
        "amount_qualifier": qualifier,
        "confidence": confidence,
    }


def period_aggregate(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    observations = payload["observations"]
    known = [float(value) for value in observations if value is not None]
    if mutation == "unknown_as_zero":
        known = [0.0 if value is None else float(value) for value in observations]
    if not known:
        return {"value": None, "value_state": "unknown", "known_count": 0, "amount_qualifier": "unavailable"}
    value = round6(sum(known))
    state = "explicit_zero" if value == 0 and any(value == 0 for value in known) else "numeric"
    qualifier = "exact" if len(known) == len(observations) else "at_least"
    return {"value": value, "value_state": state, "known_count": len(known), "amount_qualifier": qualifier}


def target_projection(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    value = payload.get("scalar")
    if value is None or not math.isfinite(float(value)) or float(value) <= 0:
        return {"target": None, "valid": False, "reason": "invalid_target"}
    numeric = float(value)
    if mutation == "scalar_minimum_for_range":
        target = {"type": "minimum", "unit": payload["unit"], "value": numeric, "source_plan_ids": [payload["plan_id"]]}
    elif mutation == "invent_range_tolerance":
        target = {"type": "range", "unit": payload["unit"], "lower": round6(numeric * 0.9), "upper": round6(numeric * 1.1), "source_plan_ids": [payload["plan_id"]]}
    else:
        target = {"type": "range", "unit": payload["unit"], "lower": numeric, "upper": numeric, "source_plan_ids": [payload["plan_id"]]}
    return {"target": target, "valid": True, "reason": "authoritative_scalar"}


def range_status(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    value = float(payload["value"])
    lower = float(payload["lower"])
    upper = float(payload["upper"])
    if value < lower:
        status = "below_target"
        distance = (lower - value) / lower
    elif value > upper:
        status = "above_target"
        distance = (value - upper) / upper
    elif lower == upper and value == lower:
        status = "at_target"
        distance = 0.0
    else:
        status = "within_target"
        distance = 0.0
    return {"status": status, "adverse_distance": round6(distance)}


def target_compatibility(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    targets = payload.get("targets", [])
    numeric = payload.get("current_numeric", False) or payload.get("previous_numeric", False)
    if not targets:
        return {
            "target": None,
            "current_status": "observed" if payload.get("current_numeric", False) else "unavailable",
            "previous_status": "observed" if payload.get("previous_numeric", False) else "unavailable",
            "comparison": {"status": "not_comparable", "reason": "unavailable_value"},
            "persistence": {"qualifies": False, "reason": "current_not_qualifying"},
            "safety_flags": ["missing_target"] if numeric else [],
        }
    semantic = lambda item: tuple(item.get(key) for key in ("type", "unit", "value", "lower", "upper"))
    compatible = len({semantic(item) for item in targets}) == 1
    if mutation == "choose_incompatible_target":
        compatible = True
    if not compatible:
        target = None
        if mutation == "nonnull_incompatible_target":
            target = {key: value for key, value in targets[0].items() if key != "plan_id"}
        return {
            "target": target,
            "current_status": "target_incompatible" if payload.get("current_numeric", False) else "unavailable",
            "previous_status": "target_incompatible" if payload.get("previous_numeric", False) else "unavailable",
            "comparison": {"status": "not_comparable", "reason": "target_incompatible"},
            "persistence": {"qualifies": False, "reason": "target_changed"},
            "safety_flags": ["incompatible_target"],
        }
    target = {key: value for key, value in targets[0].items() if key != "plan_id"}
    target["source_plan_ids"] = sorted({item["plan_id"] for item in targets})
    return {"target": target, "compatible": True, "safety_flags": []}


def metric_schema(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    direction = payload["direction"]
    target = payload.get("target")
    null_reason = payload.get("null_reason")
    errors: list[str] = []
    expected_type = {"minimum": "minimum", "maximum": "maximum", "range": "range"}.get(direction)
    if direction in {"minimize", "monitor_only"} and target is not None:
        errors.append("target_forbidden")
    elif expected_type and target is not None and target.get("type") != expected_type:
        errors.append("target_type_mismatch")
    elif expected_type and target is None and null_reason not in {"missing", "legacy", "unsafe", "incompatible"}:
        errors.append("target_required")
    return {"valid": not errors, "errors": errors}


def monitoring_coverage(payload: dict[str, Any], mutation: str | None) -> dict[str, int]:
    result = {"unknown": 0, "0_to_lt_50": 0, "50_to_lt_75": 0, "75_to_100": 0}
    for value in payload["current_coverages"]:
        if value is None:
            result["unknown"] += 1
        elif value < (49.999 if mutation == "coverage_boundary_shift" else 50):
            result["0_to_lt_50"] += 1
        elif value < (74.999 if mutation == "coverage_boundary_shift" else 75):
            result["50_to_lt_75"] += 1
        else:
            result["75_to_100"] += 1
    return result


def monitoring_stale(payload: dict[str, Any], mutation: str | None) -> dict[str, int]:
    keys = ["day_reopened", "day_version_changed", "target_source_changed", "source_snapshot_corrected", "source_version_unsupported"]
    result = {key: 0 for key in keys}
    seen: set[tuple[str, str]] = set()
    for event in payload["events"]:
        pair = (event["revision"], event["reason"])
        if mutation != "duplicate_stale_count" and pair in seen:
            continue
        seen.add(pair)
        result[event["reason"]] += 1
    return result


def monitoring_latency(payload: dict[str, Any], mutation: str | None) -> dict[str, int]:
    result = {"unknown": 0, "lt_250_ms": 0, "250_to_lt_500_ms": 0, "500_to_lt_1000_ms": 0, "gte_1000_ms": 0}
    values = [] if payload.get("replay", False) else payload.get("durations_ms", [])
    for value in values:
        if value is None or value < 0:
            result["unknown"] += 1
        elif value < (249.999 if mutation == "latency_boundary_shift" else 250):
            result["lt_250_ms"] += 1
        elif value < (499.999 if mutation == "latency_boundary_shift" else 500):
            result["250_to_lt_500_ms"] += 1
        elif value < (999.999 if mutation == "latency_boundary_shift" else 1000):
            result["500_to_lt_1000_ms"] += 1
        else:
            result["gte_1000_ms"] += 1
    return result


def monitoring_cohort(payload: dict[str, Any], mutation: str | None) -> dict[str, int]:
    monday = date.fromisoformat(payload["week_monday"])
    start = datetime.combine(monday, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    count = 0
    for value in payload["finalized_at"]:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if start <= instant < end:
            count += 1
    return {"total_count": count}


def adverse_distance(value: float, target: float, direction: str) -> float:
    if target <= 0 or not math.isfinite(value) or not math.isfinite(target):
        raise ValueError("invalid target/value")
    ratio = value / target
    if direction == "minimum":
        return max(1.0 - ratio, 0.0)
    if direction == "maximum":
        return max(ratio - 1.0, 0.0)
    raise ValueError("invalid direction")


def comparison(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    current = dict(payload["current"])
    previous = dict(payload["previous"])
    if mutation == "swap_periods":
        current, previous = previous, current
    if not payload.get("version_compatible", True):
        return {"status": "not_comparable", "reason": "version_incompatible"}
    if not payload.get("target_compatible", True):
        return {"status": "not_comparable", "reason": "target_incompatible"}
    target = float(payload["target"])
    if target <= 0:
        return {"status": "invalid", "reason": "invalid_target"}
    if current["complete_days"] < 4 or previous["complete_days"] < 4:
        return {"status": "not_comparable", "reason": "insufficient_complete_days"}
    if current["coverage"] < 50 or previous["coverage"] < 50:
        return {"status": "not_comparable", "reason": "insufficient_coverage"}
    if abs(current["coverage"] - previous["coverage"]) > 10:
        return {"status": "not_comparable", "reason": "coverage_mismatch"}
    if current["coverage"] < 75 or previous["coverage"] < 75:
        return {"status": "descriptive_only", "reason": "limited_coverage"}
    current_adverse = adverse_distance(float(current["value"]), target, payload["direction"])
    previous_adverse = adverse_distance(float(previous["value"]), target, payload["direction"])
    delta = round6(current_adverse - previous_adverse)
    threshold = 0.20 if mutation == "material_threshold_20" else 0.10
    if abs(delta) < threshold:
        status = "no_material_change"
    elif delta < 0:
        status = "improved"
    else:
        status = "worsened"
    return {"status": status, "reason": "comparable", "normalized_adverse_delta": delta}


def descriptive_comparison(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    current = float(payload["current"])
    previous = float(payload["previous"])
    if mutation == "swap_periods":
        current, previous = previous, current
    delta = round6(current - previous)
    threshold = float(payload["material_threshold"])
    if abs(delta) < threshold:
        status = "no_material_change"
    elif delta > 0:
        status = "descriptive_increase"
    else:
        status = "descriptive_decrease"
    return {"status": status, "difference": delta}


def persistence(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    if not payload.get("version_compatible", True):
        return {"qualifies": False, "reason": "version_incompatible"}
    if not payload.get("target_compatible", True):
        return {"qualifies": False, "reason": "target_changed"}
    current = payload["current"]
    previous = payload.get("previous")
    if previous is None:
        return {"qualifies": False, "reason": "missing_previous"}
    periods = [current] if mutation == "one_period_persistence" else [current, previous]
    if any(item["complete_days"] < 4 for item in periods):
        return {"qualifies": False, "reason": "insufficient_complete_days"}
    if any(item["coverage"] < 75 for item in periods):
        return {"qualifies": False, "reason": "insufficient_coverage"}
    direction = payload["direction"]
    target = float(payload["target"])
    if direction == "minimum":
        qualifying = [float(item["value"]) / target <= 0.80 for item in periods]
    elif direction == "maximum":
        qualifying = [float(item["value"]) > target for item in periods]
    elif direction == "frequency":
        qualifying = [float(item["value"]) >= float(payload["predicate_min"]) for item in periods]
    else:
        raise ValueError("invalid persistence direction")
    if all(qualifying):
        return {"qualifies": True, "reason": "qualified"}
    if not qualifying[0]:
        return {"qualifies": False, "reason": "current_not_qualifying"}
    return {"qualifies": False, "reason": "previous_not_qualifying"}


def contributors(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    rows = [row for row in payload["items"] if row.get("known", True)]
    rows.sort(key=lambda item: (-abs(float(item["value"])), item["date"], item["ref"].lower()))
    if mutation == "reverse_tie_order":
        rows.sort(key=lambda item: (-abs(float(item["value"])), item["date"], item["ref"].lower()), reverse=True)
    return {"refs": [item["ref"] for item in rows[:5]], "count": min(len(rows), 5)}


def revision(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    action = payload["action"]
    if action == "first":
        return {"result": "created", "revision": 1, "historical_mutated": False}
    if action == "same_hash":
        return {"result": "no_change", "revision": payload["current_revision"], "historical_mutated": False}
    if action == "changed_hash":
        if mutation == "mutate_finalized_history":
            return {"result": "overwritten", "revision": payload["current_revision"], "historical_mutated": True}
        return {"result": "created", "revision": payload["current_revision"] + 1, "historical_mutated": False}
    if action == "new_date":
        return {"result": "created_new_series", "revision": 1, "historical_mutated": False}
    if action == "unsupported_replay":
        return {"result": "error", "code": "UNSUPPORTED_HISTORICAL_VERSION", "historical_mutated": False}
    if action == "stale":
        return {"result": "stale_event_appended", "revision": payload["current_revision"], "historical_mutated": False}
    raise ValueError("invalid revision action")


def projection(payload: dict[str, Any], mutation: str | None) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("interface_version", 1) != 1:
        errors.append("unsupported_interface_version")
    version_supported = payload.get("analysis_version") == ANALYSIS_VERSION
    if mutation == "accept_version_mismatch":
        version_supported = True
    if not version_supported:
        errors.append("unsupported_analysis_rules")
    if payload.get("timezone") != TIMEZONE:
        errors.append("invalid_timezone")
    days = payload.get("days", [])
    if len(days) != 7 or days != sorted(days) or len(set(days)) != 7:
        errors.append("invalid_current_days")
    previous = payload.get("previous_days", [])
    if len(previous) != 7 or previous != sorted(previous) or len(set(previous)) != 7:
        errors.append("invalid_previous_days")
    if days and previous:
        day_dates = [date.fromisoformat(item) for item in days]
        previous_dates = [date.fromisoformat(item) for item in previous]
        if any(b - a != timedelta(days=1) for a, b in zip(day_dates, day_dates[1:])):
            errors.append("non_contiguous_current")
        if any(b - a != timedelta(days=1) for a, b in zip(previous_dates, previous_dates[1:])):
            errors.append("non_contiguous_previous")
        if previous_dates[-1] + timedelta(days=1) != day_dates[0]:
            errors.append("windows_not_contiguous")
    metrics = payload.get("metric_keys", [])
    if metrics != sorted(metrics) or len(metrics) != len(set(metrics)):
        errors.append("invalid_metric_order")
    flags = payload.get("safety_flags", [])
    if flags != sorted(flags) or len(flags) != len(set(flags)):
        errors.append("invalid_safety_order")
    for fact in payload.get("metric_facts", []):
        if fact.get("status") == "target_incompatible" and fact.get("target") is not None:
            errors.append("contradictory_incompatible_target")
        if fact.get("status") == "target_incompatible" and "incompatible_target" not in flags:
            errors.append("missing_incompatible_target_flag")
    return {"valid": not errors, "errors": sorted(errors)}


def evaluate(vector: dict[str, Any], mutation: str | None = None) -> dict[str, Any]:
    kind = vector["kind"]
    payload = vector["input"]
    if kind == "window":
        return windows(payload["as_of_diary_date"], mutation)
    if kind == "coverage":
        return coverage(payload, mutation)
    if kind == "period_aggregate":
        return period_aggregate(payload, mutation)
    if kind == "target_projection":
        return target_projection(payload, mutation)
    if kind == "range_status":
        return range_status(payload, mutation)
    if kind == "target_compatibility":
        return target_compatibility(payload, mutation)
    if kind == "metric_schema":
        return metric_schema(payload, mutation)
    if kind == "monitoring_coverage":
        return monitoring_coverage(payload, mutation)
    if kind == "monitoring_stale":
        return monitoring_stale(payload, mutation)
    if kind == "monitoring_latency":
        return monitoring_latency(payload, mutation)
    if kind == "monitoring_cohort":
        return monitoring_cohort(payload, mutation)
    if kind == "comparison":
        return comparison(payload, mutation)
    if kind == "descriptive_comparison":
        return descriptive_comparison(payload, mutation)
    if kind == "persistence":
        return persistence(payload, mutation)
    if kind == "contributors":
        return contributors(payload, mutation)
    if kind == "revision":
        return revision(payload, mutation)
    if kind == "projection":
        return projection(payload, mutation)
    raise ValueError(f"unsupported kind: {kind}")


def check_artifacts(vector_path: Path) -> list[str]:
    root = vector_path.parent
    design = root / "27_W3_VERSIONED_PATTERN_ANALYSIS_DESIGN.md"
    approval = root / "27B_W3_PATTERN_ANALYSIS_APPROVAL_REPORT.md"
    errors: list[str] = []
    if not design.is_file():
        return ["missing design artifact"]
    if not approval.is_file():
        return ["missing approval artifact"]
    design_text = design.read_text(encoding="utf-8")
    approval_text = approval.read_text(encoding="utf-8")
    required_design = [
        "NO UNIFIED NUTRITION SCORE",
        "w3-analysis-1.1.0",
        "withdrawn pre-release",
        "0_to_lt_50",
        "gte_1000_ms",
        "WeeklyPriorityAnalysisInputV1",
        "Asia/Riyadh",
        "previous_period_start",
        "known_entry_count",
        "source_input_hash",
        "UNSUPPORTED_HISTORICAL_VERSION",
        "PLAN 031 → PLAN 032: PASS",
        "PLAN 032 → PLAN 033: PASS",
        "Implementation remains unauthorized",
    ]
    for token in required_design:
        if token not in design_text:
            errors.append(f"design missing decision token: {token}")
    forbidden = ["T" + "BD", "implementation" + "-defined", "to be decided during implementation"]
    for token in forbidden:
        if token.lower() in design_text.lower():
            errors.append(f"design contains unresolved term: {token}")
    required_approval = [
        "Product Owner | APPROVED",
        "Nutrition / Safety | APPROVED",
        "Data / Analysis | APPROVED",
        "Architecture / API | APPROVED",
        "Security / Privacy | APPROVED",
        "UX / Arabic / Accessibility | APPROVED",
        "Notifications / Operations | APPROVED",
        "QA | APPROVED",
        "Decision status: Design 1.1 refrozen for implementation remediation",
        "Implementation authorized: NO",
    ]
    for token in required_approval:
        if token not in approval_text:
            errors.append(f"approval missing decision token: {token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vectors", type=Path)
    parser.add_argument("--skip-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.vectors.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"plan032: invalid corpus: {error}")
        return 2
    errors: list[str] = []
    if document.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if document.get("design_version") != "1.1":
        errors.append("design_version must equal 1.1")
    if document.get("analysis_rules_version") != ANALYSIS_VERSION:
        errors.append(f"analysis_rules_version must equal {ANALYSIS_VERSION}")
    vectors = document.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        errors.append("vectors must be a non-empty list")
        vectors = []
    ids = [item.get("id") for item in vectors]
    if len(ids) != len(set(ids)) or any(not isinstance(item, str) or not item for item in ids):
        errors.append("vector IDs must be non-empty and unique")
    required_coverage = set(document.get("required_coverage", []))
    actual_coverage = {tag for item in vectors for tag in item.get("covers", [])}
    missing_coverage = sorted(required_coverage - actual_coverage)
    if missing_coverage:
        errors.append(f"missing coverage tags: {missing_coverage}")
    passed = 0
    for vector in vectors:
        try:
            actual = evaluate(vector)
        except Exception as error:  # deterministic failure report, not a bypass
            errors.append(f"{vector.get('id')}: evaluator error: {error}")
            continue
        if actual != vector.get("expected"):
            errors.append(
                f"{vector.get('id')}: expected {json.dumps(vector.get('expected'), sort_keys=True)} "
                f"got {json.dumps(actual, sort_keys=True)}"
            )
        else:
            passed += 1
    mutations = document.get("negative_mutations", [])
    mutation_names = {item.get("name") for item in mutations}
    missing_mutations = sorted(REQUIRED_MUTATIONS - mutation_names)
    if missing_mutations:
        errors.append(f"missing required negative mutations: {missing_mutations}")
    mutation_passed = 0
    for mutation in mutations:
        name = mutation.get("name")
        detected_by = mutation.get("detected_by", [])
        selected = [item for item in vectors if item.get("id") in detected_by]
        if not selected:
            errors.append(f"mutation {name}: no detector vectors")
            continue
        changed = False
        for vector in selected:
            try:
                if evaluate(vector, name) != vector.get("expected"):
                    changed = True
                    break
            except Exception:
                changed = True
                break
        if changed:
            mutation_passed += 1
        else:
            errors.append(f"mutation {name}: not detected")
    if len(mutations) < 17:
        errors.append("at least 17 independent negative mutations are required")
    if not args.skip_artifacts:
        errors.extend(check_artifacts(args.vectors))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(
            f"plan032: {passed} passed, {len(vectors) - passed} failed; "
            f"negative mutations: {mutation_passed}/{len(mutations)} rejected"
        )
        return 1
    print(f"plan032: {passed} passed, 0 failed")
    print(f"negative mutations: {mutation_passed}/{len(mutations)} correctly rejected")
    print("decision completeness: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
