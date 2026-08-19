"""Pure, version-dispatched PLAN 032 nutrition-pattern rules.

This module deliberately has no database or HTTP dependencies.  It owns the
deterministic arithmetic shared by evaluation, historical validation, and the
production golden-vector oracle.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Final

ANALYSIS_RULES_VERSION: Final = "w3-analysis-1.1.0"
CALENDAR_TIMEZONE: Final = "Asia/Riyadh"
MIN_COMPLETE_DAYS: Final = 4
LIMITED_COVERAGE_PERCENT: Final = Decimal("50")
STRONG_COVERAGE_PERCENT: Final = Decimal("75")
MAX_COMPARISON_COVERAGE_GAP: Final = Decimal("10")
MATERIAL_TARGET_DELTA: Final = Decimal("0.10")
CONTRIBUTOR_CAP: Final = 5

DAILY_METRICS: Final[dict[str, tuple[str, str]]] = {
    "energy:calories_kcal_per_day": ("kcal/day", "maximum"),
    "macro:protein_g_per_day": ("g/day", "minimum"),
    "macro:carb_g_per_day": ("g/day", "range"),
    "macro:fat_g_per_day": ("g/day", "range"),
    "nutrient:fiber_g": ("g/day", "minimum"),
    "nutrient:added_sugar_g": ("g/day", "maximum"),
    "nutrient:saturated_fat_g": ("g/day", "maximum"),
    "nutrient:trans_fat_g": ("g/day", "maximum"),
    "nutrient:sodium_mg": ("mg/day", "maximum"),
    "nutrient:potassium_mg": ("mg/day", "minimum"),
    "nutrient:cholesterol_mg": ("mg/day", "monitor_only"),
    "nutrient:calcium_mg": ("mg/day", "minimum"),
    "nutrient:iron_mg": ("mg/day", "minimum"),
    "nutrient:magnesium_mg": ("mg/day", "minimum"),
    "nutrient:zinc_mg": ("mg/day", "minimum"),
    "nutrient:selenium_mcg": ("mcg/day", "minimum"),
    "nutrient:vitamin_b12_mcg": ("mcg/day", "minimum"),
    "nutrient:folate_dfe_mcg": ("mcg/day", "minimum"),
    "nutrient:vitamin_a_rae_mcg": ("mcg/day", "minimum"),
    "nutrient:iodine_mcg": ("mcg/day", "minimum"),
}

PATTERN_METRICS: Final[dict[str, tuple[str, str]]] = {
    "group:fruit_vegetable_g_per_day": ("g/day", "minimum"),
    "group:legumes_servings_per_period": ("servings/7d", "minimum"),
    "group:whole_grain_share_percent": ("percent", "minimum"),
    "group:nuts_seeds_servings_per_period": ("servings/7d", "minimum"),
    "group:seafood_servings_per_period": ("servings/7d", "minimum"),
    "group:omega3_seafood_servings_per_period": ("servings/7d", "minimum"),
    "group:dairy_fortified_servings_per_day": ("servings/day", "minimum"),
    "group:red_meat_g_per_period": ("g/7d", "maximum"),
    "group:processed_meat_occurrence_days": ("days/7d", "minimize"),
    "group:sugar_sweetened_beverage_occurrence_days": ("days/7d", "minimize"),
    "group:sweets_occurrence_days": ("days/7d", "minimize"),
    "protein:source_diversity_count": ("sources/7d", "monitor_only"),
    "nova:nova4_calorie_share_percent": ("percent", "minimize"),
    "nova:nova4_occurrence_days": ("days/7d", "minimize"),
}

METRIC_REGISTRY: Final = {**DAILY_METRICS, **PATTERN_METRICS}


def decimal_value(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non_finite_source_fact")
    return result


def round6(value: Decimal | float | int) -> float:
    return float(decimal_value(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def analysis_windows(as_of_diary_date: date | str) -> dict[str, str]:
    end = (
        date.fromisoformat(as_of_diary_date)
        if isinstance(as_of_diary_date, str)
        else as_of_diary_date
    )
    start = end - timedelta(days=6)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "previous_period_start": previous_start.isoformat(),
        "previous_period_end": previous_end.isoformat(),
    }


def metric_coverage(days: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [day for day in days if day["status"] == "complete"]
    total = sum(len(day["values"]) for day in complete)
    known = sum(value is not None for day in complete for value in day["values"])
    numeric: list[Decimal] = []
    for day in complete:
        values = day["values"]
        finite = [decimal_value(value) for value in values if value is not None]
        if not values:
            numeric.append(Decimal(0))
        elif finite:
            numeric.append(sum(finite, Decimal(0)))
    if not complete:
        coverage = None
    elif total == 0:
        coverage = 100.0
    else:
        coverage = round6(Decimal(known) / Decimal(total) * 100)
    average = round6(sum(numeric, Decimal(0)) / len(numeric)) if numeric else None
    if len(complete) < MIN_COMPLETE_DAYS or coverage is None or coverage < 50:
        confidence = "unavailable"
    elif coverage < 75:
        confidence = "limited"
    else:
        confidence = "strong"
    qualifier = (
        "unavailable"
        if average is None
        else "exact"
        if total == 0 or known == total
        else "at_least"
    )
    return {
        "complete_day_count": len(complete),
        "total_entry_count": total,
        "known_entry_count": known,
        "numeric_day_count": len(numeric),
        "coverage_percent": coverage,
        "value": average,
        "amount_qualifier": qualifier,
        "confidence": confidence,
    }


def aggregate_period_values(observations: list[float | None]) -> dict[str, Any]:
    known = [decimal_value(value) for value in observations if value is not None]
    if not known:
        return {
            "value": None,
            "value_state": "unknown",
            "known_count": 0,
            "amount_qualifier": "unavailable",
        }
    value = round6(sum(known, Decimal(0)))
    return {
        "value": value,
        "value_state": "explicit_zero" if value == 0 else "numeric",
        "known_count": len(known),
        "amount_qualifier": "exact" if len(known) == len(observations) else "at_least",
    }


def scalar_range_target(value: Any, unit: str, plan_id: str) -> dict[str, Any]:
    numeric = decimal_value(value)
    if numeric <= 0:
        return {"target": None, "valid": False, "reason": "invalid_target"}
    published = float(numeric)
    return {
        "target": {
            "type": "range",
            "unit": unit,
            "lower": published,
            "upper": published,
            "source_plan_ids": [plan_id],
        },
        "valid": True,
        "reason": "authoritative_scalar",
    }


def range_metric_status(value: Any, lower: Any, upper: Any) -> dict[str, Any]:
    observed = decimal_value(value)
    minimum = decimal_value(lower)
    maximum = decimal_value(upper)
    if minimum <= 0 or maximum <= 0 or minimum > maximum:
        raise ValueError("invalid_target")
    if observed < minimum:
        status = "below_target"
        distance = (minimum - observed) / minimum
    elif observed > maximum:
        status = "above_target"
        distance = (observed - maximum) / maximum
    elif minimum == maximum and observed == minimum:
        status = "at_target"
        distance = Decimal(0)
    else:
        status = "within_target"
        distance = Decimal(0)
    return {"status": status, "adverse_distance": round6(distance)}


def project_target_compatibility(payload: dict[str, Any]) -> dict[str, Any]:
    targets = payload.get("targets", [])
    current_numeric = bool(payload.get("current_numeric"))
    previous_numeric = bool(payload.get("previous_numeric"))
    if not targets:
        return {
            "target": None,
            "current_status": "observed" if current_numeric else "unavailable",
            "previous_status": "observed" if previous_numeric else "unavailable",
            "comparison": {"status": "not_comparable", "reason": "unavailable_value"},
            "persistence": {"qualifies": False, "reason": "current_not_qualifying"},
            "safety_flags": ["missing_target"] if current_numeric or previous_numeric else [],
        }
    semantic_keys = ("type", "unit", "value", "lower", "upper")
    semantics = {tuple(item.get(key) for key in semantic_keys) for item in targets}
    if len(semantics) != 1:
        return {
            "target": None,
            "current_status": "target_incompatible" if current_numeric else "unavailable",
            "previous_status": "target_incompatible" if previous_numeric else "unavailable",
            "comparison": {"status": "not_comparable", "reason": "target_incompatible"},
            "persistence": {"qualifies": False, "reason": "target_changed"},
            "safety_flags": ["incompatible_target"],
        }
    target = {key: value for key, value in targets[0].items() if key != "plan_id"}
    target["source_plan_ids"] = sorted({item["plan_id"] for item in targets})
    return {"target": target, "compatible": True, "safety_flags": []}


def validate_metric_target_shape(payload: dict[str, Any]) -> dict[str, Any]:
    direction = payload["direction"]
    target = payload.get("target")
    null_reason = payload.get("null_reason")
    errors: list[str] = []
    expected_type = {"minimum": "minimum", "maximum": "maximum", "range": "range"}.get(direction)
    if direction in {"minimize", "monitor_only"} and target is not None:
        errors.append("target_forbidden")
    elif expected_type and target is not None and target.get("type") != expected_type:
        errors.append("target_type_mismatch")
    elif (
        expected_type
        and target is None
        and null_reason
        not in {
            "missing",
            "legacy",
            "unsafe",
            "incompatible",
        }
    ):
        errors.append("target_required")
    return {"valid": not errors, "errors": errors}


def coverage_band_counts(current_coverages: list[float | None]) -> dict[str, int]:
    result = {"unknown": 0, "0_to_lt_50": 0, "50_to_lt_75": 0, "75_to_100": 0}
    for value in current_coverages:
        if value is None:
            result["unknown"] += 1
        elif value < 50:
            result["0_to_lt_50"] += 1
        elif value < 75:
            result["50_to_lt_75"] += 1
        else:
            result["75_to_100"] += 1
    return result


def stale_reason_counts(events: list[dict[str, str]]) -> dict[str, int]:
    keys = (
        "day_reopened",
        "day_version_changed",
        "target_source_changed",
        "source_snapshot_corrected",
        "source_version_unsupported",
    )
    result = {key: 0 for key in keys}
    seen: set[tuple[str, str]] = set()
    for event in events:
        pair = (event["revision"], event["reason"])
        if event["reason"] not in result or pair in seen:
            continue
        seen.add(pair)
        result[event["reason"]] += 1
    return result


def latency_band_counts(durations_ms: list[float | None]) -> dict[str, int]:
    result = {
        "unknown": 0,
        "lt_250_ms": 0,
        "250_to_lt_500_ms": 0,
        "500_to_lt_1000_ms": 0,
        "gte_1000_ms": 0,
    }
    for value in durations_ms:
        if value is None or value < 0:
            result["unknown"] += 1
        elif value < 250:
            result["lt_250_ms"] += 1
        elif value < 500:
            result["250_to_lt_500_ms"] += 1
        elif value < 1000:
            result["500_to_lt_1000_ms"] += 1
        else:
            result["gte_1000_ms"] += 1
    return result


def monitoring_cohort_count(week_monday: str, finalized_at: list[str]) -> dict[str, int]:
    monday = date.fromisoformat(week_monday)
    start = datetime.combine(monday, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    count = sum(
        start <= datetime.fromisoformat(value.replace("Z", "+00:00")) < end
        for value in finalized_at
    )
    return {"total_count": count}


def _adverse_distance(value: float, target: float, direction: str) -> Decimal:
    observed = decimal_value(value)
    comparator = decimal_value(target)
    if comparator <= 0:
        raise ValueError("invalid_target")
    ratio = observed / comparator
    if direction == "minimum":
        return max(Decimal(1) - ratio, Decimal(0))
    if direction == "maximum":
        return max(ratio - Decimal(1), Decimal(0))
    raise ValueError("invalid_direction")


def compare_target_metric(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("version_compatible", True):
        return {"status": "not_comparable", "reason": "version_incompatible"}
    if not payload.get("target_compatible", True):
        return {"status": "not_comparable", "reason": "target_incompatible"}
    current, previous = payload["current"], payload["previous"]
    target = float(payload["target"])
    if target <= 0 or not math.isfinite(target):
        return {"status": "invalid", "reason": "invalid_target"}
    if current["complete_days"] < 4 or previous["complete_days"] < 4:
        return {"status": "not_comparable", "reason": "insufficient_complete_days"}
    if current["coverage"] < 50 or previous["coverage"] < 50:
        return {"status": "not_comparable", "reason": "insufficient_coverage"}
    if abs(current["coverage"] - previous["coverage"]) > 10:
        return {"status": "not_comparable", "reason": "coverage_mismatch"}
    if current["coverage"] < 75 or previous["coverage"] < 75:
        return {"status": "descriptive_only", "reason": "limited_coverage"}
    delta = round6(
        _adverse_distance(current["value"], target, payload["direction"])
        - _adverse_distance(previous["value"], target, payload["direction"])
    )
    status = "no_material_change" if abs(delta) < 0.10 else "improved" if delta < 0 else "worsened"
    return {"status": status, "reason": "comparable", "normalized_adverse_delta": delta}


def compare_descriptive_metric(payload: dict[str, Any]) -> dict[str, Any]:
    difference = round6(decimal_value(payload["current"]) - decimal_value(payload["previous"]))
    threshold = decimal_value(payload["material_threshold"])
    status = (
        "no_material_change"
        if abs(Decimal(str(difference))) < threshold
        else "descriptive_increase"
        if difference > 0
        else "descriptive_decrease"
    )
    return {"status": status, "difference": difference}


def persistence_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("version_compatible", True):
        return {"qualifies": False, "reason": "version_incompatible"}
    if not payload.get("target_compatible", True):
        return {"qualifies": False, "reason": "target_changed"}
    current, previous = payload["current"], payload.get("previous")
    if previous is None:
        return {"qualifies": False, "reason": "missing_previous"}
    periods = [current, previous]
    if any(item["complete_days"] < 4 for item in periods):
        return {"qualifies": False, "reason": "insufficient_complete_days"}
    if any(item["coverage"] < 75 for item in periods):
        return {"qualifies": False, "reason": "insufficient_coverage"}
    direction = payload["direction"]
    target = decimal_value(payload["target"])
    if target <= 0:
        return {"qualifies": False, "reason": "current_not_qualifying"}
    if direction == "minimum":
        qualified = [decimal_value(item["value"]) / target <= Decimal("0.80") for item in periods]
    elif direction == "maximum":
        qualified = [decimal_value(item["value"]) > target for item in periods]
    elif direction == "frequency":
        threshold = decimal_value(payload["predicate_min"])
        qualified = [decimal_value(item["value"]) >= threshold for item in periods]
    else:
        raise ValueError("invalid_persistence_direction")
    if all(qualified):
        return {"qualifies": True, "reason": "qualified"}
    return {
        "qualifies": False,
        "reason": "current_not_qualifying" if not qualified[0] else "previous_not_qualifying",
    }


def rank_contributors(items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item for item in items if item.get("known", True)]
    rows.sort(
        key=lambda item: (-abs(decimal_value(item["value"])), item["date"], item["ref"].lower())
    )
    return {
        "refs": [item["ref"] for item in rows[:CONTRIBUTOR_CAP]],
        "count": min(len(rows), CONTRIBUTOR_CAP),
    }


def revision_transition(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if action == "first":
        return {"result": "created", "revision": 1, "historical_mutated": False}
    if action == "same_hash":
        return {
            "result": "no_change",
            "revision": payload["current_revision"],
            "historical_mutated": False,
        }
    if action == "changed_hash":
        return {
            "result": "created",
            "revision": payload["current_revision"] + 1,
            "historical_mutated": False,
        }
    if action == "new_date":
        return {"result": "created_new_series", "revision": 1, "historical_mutated": False}
    if action == "unsupported_replay":
        return {
            "result": "error",
            "code": "UNSUPPORTED_HISTORICAL_VERSION",
            "historical_mutated": False,
        }
    if action == "stale":
        return {
            "result": "stale_event_appended",
            "revision": payload["current_revision"],
            "historical_mutated": False,
        }
    raise ValueError("invalid_revision_action")


def validate_priority_projection(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("interface_version", 1) != 1:
        errors.append("unsupported_interface_version")
    if payload.get("analysis_version") != ANALYSIS_RULES_VERSION:
        errors.append("unsupported_analysis_rules")
    if payload.get("timezone") != CALENDAR_TIMEZONE:
        errors.append("invalid_timezone")
    current = payload.get("days", [])
    previous = payload.get("previous_days", [])
    if len(current) != 7 or current != sorted(current) or len(set(current)) != 7:
        errors.append("invalid_current_days")
    if len(previous) != 7 or previous != sorted(previous) or len(set(previous)) != 7:
        errors.append("invalid_previous_days")
    if current and previous:
        current_dates = [date.fromisoformat(value) for value in current]
        previous_dates = [date.fromisoformat(value) for value in previous]
        if any(
            right - left != timedelta(days=1)
            for left, right in zip(current_dates, current_dates[1:])
        ):
            errors.append("non_contiguous_current")
        if any(
            right - left != timedelta(days=1)
            for left, right in zip(previous_dates, previous_dates[1:])
        ):
            errors.append("non_contiguous_previous")
        if previous_dates[-1] + timedelta(days=1) != current_dates[0]:
            errors.append("windows_not_contiguous")
    metrics = payload.get("metric_keys", [])
    if metrics != sorted(metrics) or len(metrics) != len(set(metrics)):
        errors.append("invalid_metric_order")
    flags = payload.get("safety_flags", [])
    if flags != sorted(flags) or len(flags) != len(set(flags)):
        errors.append("invalid_safety_order")
    incompatible = any(
        metric.get("status") == "target_incompatible" for metric in payload.get("metric_facts", [])
    )
    if incompatible and "incompatible_target" not in flags:
        errors.append("missing_incompatible_target_flag")
    return {"valid": not errors, "errors": sorted(errors)}


def evaluate_contract_case(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise the same production rules used by orchestration for design cases."""
    if kind == "window":
        return analysis_windows(payload["as_of_diary_date"])
    if kind == "coverage":
        return metric_coverage(payload["days"])
    if kind == "comparison":
        return compare_target_metric(payload)
    if kind == "descriptive_comparison":
        return compare_descriptive_metric(payload)
    if kind == "persistence":
        return persistence_evidence(payload)
    if kind == "contributors":
        return rank_contributors(payload["items"])
    if kind == "revision":
        return revision_transition(payload)
    if kind == "projection":
        return validate_priority_projection(payload)
    if kind == "period_aggregate":
        return aggregate_period_values(payload["observations"])
    if kind == "target_projection":
        return scalar_range_target(payload["scalar"], payload["unit"], payload["plan_id"])
    if kind == "range_status":
        return range_metric_status(payload["value"], payload["lower"], payload["upper"])
    if kind == "target_compatibility":
        return project_target_compatibility(payload)
    if kind == "metric_schema":
        return validate_metric_target_shape(payload)
    if kind == "monitoring_coverage":
        return coverage_band_counts(payload["current_coverages"])
    if kind == "monitoring_stale":
        return stale_reason_counts(payload["events"])
    if kind == "monitoring_latency":
        durations = [] if payload.get("replay") else payload["durations_ms"]
        return latency_band_counts(durations)
    if kind == "monitoring_cohort":
        return monitoring_cohort_count(payload["week_monday"], payload["finalized_at"])
    raise ValueError(f"unsupported contract case: {kind}")


def require_analysis_rules(version: str) -> None:
    if version != ANALYSIS_RULES_VERSION:
        raise ValueError("UNSUPPORTED_ANALYSIS_RULE_VERSION")
