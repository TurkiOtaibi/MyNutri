"""Pure, version-dispatched PLAN 032 nutrition-pattern rules.

This module deliberately has no database or HTTP dependencies.  It owns the
deterministic arithmetic shared by evaluation, historical validation, and the
production golden-vector oracle.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Final

ANALYSIS_RULES_VERSION: Final = "w3-analysis-1.0.0"
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
    end = date.fromisoformat(as_of_diary_date) if isinstance(as_of_diary_date, str) else as_of_diary_date
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
    rows.sort(key=lambda item: (-abs(decimal_value(item["value"])), item["date"], item["ref"].lower()))
    return {"refs": [item["ref"] for item in rows[:CONTRIBUTOR_CAP]], "count": min(len(rows), CONTRIBUTOR_CAP)}


def revision_transition(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if action == "first":
        return {"result": "created", "revision": 1, "historical_mutated": False}
    if action == "same_hash":
        return {"result": "no_change", "revision": payload["current_revision"], "historical_mutated": False}
    if action == "changed_hash":
        return {"result": "created", "revision": payload["current_revision"] + 1, "historical_mutated": False}
    if action == "new_date":
        return {"result": "created_new_series", "revision": 1, "historical_mutated": False}
    if action == "unsupported_replay":
        return {"result": "error", "code": "UNSUPPORTED_HISTORICAL_VERSION", "historical_mutated": False}
    if action == "stale":
        return {"result": "stale_event_appended", "revision": payload["current_revision"], "historical_mutated": False}
    raise ValueError("invalid_revision_action")


def validate_priority_projection(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
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
        if any(right - left != timedelta(days=1) for left, right in zip(current_dates, current_dates[1:])):
            errors.append("non_contiguous_current")
        if any(right - left != timedelta(days=1) for left, right in zip(previous_dates, previous_dates[1:])):
            errors.append("non_contiguous_previous")
        if previous_dates[-1] + timedelta(days=1) != current_dates[0]:
            errors.append("windows_not_contiguous")
    metrics = payload.get("metric_keys", [])
    if metrics != sorted(metrics) or len(metrics) != len(set(metrics)):
        errors.append("invalid_metric_order")
    flags = payload.get("safety_flags", [])
    if flags != sorted(flags) or len(flags) != len(set(flags)):
        errors.append("invalid_safety_order")
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
    raise ValueError(f"unsupported contract case: {kind}")


def require_analysis_rules(version: str) -> None:
    if version != ANALYSIS_RULES_VERSION:
        raise ValueError("UNSUPPORTED_ANALYSIS_RULE_VERSION")
