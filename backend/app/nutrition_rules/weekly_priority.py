from __future__ import annotations

import math
from copy import deepcopy
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.schemas import WeeklyPriorityAnalysisInputV1

WEEKLY_PRIORITY_RULES_VERSION: Final = "w3-priority-1.0.0"
WEEKLY_PRIORITY_COPY_VERSION: Final = "w3-priority-ar-1.0.0"
SUPPORTED_INTERFACE_VERSIONS: Final = frozenset({1})
SUPPORTED_ANALYSIS_RULES_VERSIONS: Final = frozenset({"w3-analysis-1.1.0"})
SUPPORTED_NUTRITION_REGISTRY_VERSIONS: Final = frozenset({"2.0.0"})
SUPPORTED_FOOD_GROUP_RULES_VERSIONS: Final = frozenset({"1.0.0"})
SUPPORTED_NOVA_RULES_VERSIONS: Final = frozenset({"1.0.0"})
SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS: Final = frozenset({3})

RULE_META: Final[dict[str, tuple[int, int, dict[str, str]]]] = {
    "sodium_overage": (1, 10, {"replace": "replace_high_sodium_choice"}),
    "added_sugar_overage": (1, 20, {"replace": "replace_added_sugar_choice"}),
    "saturated_fat_overage": (1, 30, {"replace": "replace_saturated_fat_choice"}),
    "trans_fat_overage": (1, 40, {"replace": "replace_trans_fat_choice"}),
    "processed_meat_frequency": (1, 50, {"replace": "replace_processed_meat_choice"}),
    "sugary_drink_frequency": (1, 60, {"replace": "replace_sugary_drink_choice"}),
    "fruit_vegetable_gap": (
        2,
        110,
        {"add": "add_fruit_or_vegetable", "replace": "replace_with_fruit_or_vegetable"},
    ),
    "legumes_gap": (2, 120, {"add": "add_legumes", "replace": "replace_with_legumes"}),
    "whole_grain_share_gap": (2, 130, {"replace": "replace_with_whole_grain"}),
    "nuts_seeds_gap": (
        2,
        140,
        {"add": "add_nuts_or_seeds", "replace": "replace_with_nuts_or_seeds"},
    ),
    "seafood_gap": (2, 150, {"replace": "replace_with_seafood"}),
    "dairy_alternative_gap": (
        2,
        160,
        {
            "add": "add_dairy_or_fortified_alternative",
            "replace": "replace_with_dairy_or_fortified_alternative",
        },
    ),
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

METRIC_RULES: Final[dict[str, str]] = {
    "nutrient:sodium_mg": "sodium_overage",
    "nutrient:added_sugar_g": "added_sugar_overage",
    "nutrient:saturated_fat_g": "saturated_fat_overage",
    "nutrient:trans_fat_g": "trans_fat_overage",
    "group:processed_meat_occurrence_days": "processed_meat_frequency",
    "group:sugar_sweetened_beverage_occurrence_days": "sugary_drink_frequency",
    "group:fruit_vegetable_g_per_day": "fruit_vegetable_gap",
    "group:legumes_servings_per_period": "legumes_gap",
    "group:whole_grain_share_percent": "whole_grain_share_gap",
    "group:nuts_seeds_servings_per_period": "nuts_seeds_gap",
    "group:seafood_servings_per_period": "seafood_gap",
    "group:dairy_fortified_servings_per_day": "dairy_alternative_gap",
    "nutrient:fiber_g": "fiber_gap",
    "nutrient:potassium_mg": "potassium_gap",
    "nutrient:calcium_mg": "calcium_gap",
    "nutrient:iron_mg": "iron_gap",
    "nutrient:magnesium_mg": "magnesium_gap",
    "nutrient:zinc_mg": "zinc_gap",
    "nutrient:selenium_mcg": "selenium_gap",
    "nutrient:vitamin_b12_mcg": "vitamin_b12_gap",
    "nutrient:folate_dfe_mcg": "folate_dfe_gap",
    "nutrient:vitamin_a_rae_mcg": "vitamin_a_rae_gap",
    "nutrient:iodine_mcg": "iodine_gap",
}

COPY_CATALOG: Final[dict[str, tuple[str, str, str]]] = {
    "sodium_overage": (
        "تقليل الصوديوم",
        "تجاوز متوسط الصوديوم الحد المرجعي في يومين مكتملين أو أكثر.",
        "استبدل خيارًا مرتفع الصوديوم بخيار أقل صوديومًا هذا الأسبوع.",
    ),
    "added_sugar_overage": (
        "تقليل السكر المضاف",
        "تجاوز متوسط السكر المضاف الحد المحدد في يومين مكتملين أو أكثر.",
        "استبدل خيارًا يحتوي على سكر مضاف بخيار غير محلى.",
    ),
    "saturated_fat_overage": (
        "تقليل الدهون المشبعة",
        "تجاوز متوسط الدهون المشبعة الحد المحدد في يومين مكتملين أو أكثر.",
        "استبدل مصدرًا مرتفع الدهون المشبعة بمصدر دهون غير مشبعة.",
    ),
    "trans_fat_overage": (
        "تقليل الدهون المتحولة",
        "تجاوزت الدهون المتحولة الحد المحدد في يومين مكتملين أو أكثر.",
        "استبدل الخيار المحتوي على دهون متحولة بخيار لا يحتوي عليها.",
    ),
    "processed_meat_frequency": (
        "تقليل تكرار اللحوم المصنعة",
        "ظهرت اللحوم المصنعة في يومين مكتملين أو أكثر خلال الفترة.",
        "استبدل إحدى مرات تناول اللحوم المصنعة بمصدر بروتين آخر.",
    ),
    "sugary_drink_frequency": (
        "تقليل المشروبات المحلاة",
        "ظهرت المشروبات المحلاة بالسكر في يومين مكتملين أو أكثر خلال الفترة.",
        "استبدل مشروبًا محلى بالماء أو مشروب غير محلى.",
    ),
    "fruit_vegetable_gap": (
        "زيادة الخضروات والفواكه",
        "كان المتوسط المسجل أقل من 80٪ من الهدف.",
        "أضف أو استبدل خيارًا في وجبة واحدة بخضروات أو فاكهة.",
    ),
    "legumes_gap": (
        "زيادة البقوليات",
        "كان عدد حصص البقوليات أقل من 80٪ من الهدف الأسبوعي.",
        "أضف أو استبدل مصدر بروتين في وجبة واحدة بالبقوليات.",
    ),
    "whole_grain_share_gap": (
        "زيادة الحبوب الكاملة",
        "كانت حصة الحبوب الكاملة أقل من 80٪ من الهدف ضمن الحبوب المعروفة.",
        "استبدل خيارًا من الحبوب المكررة بخيار من الحبوب الكاملة.",
    ),
    "nuts_seeds_gap": (
        "زيادة المكسرات والبذور",
        "كان عدد الحصص المسجلة أقل من 80٪ من الهدف الأسبوعي.",
        "أضف حصة مناسبة أو استبدل وجبة خفيفة بمكسرات أو بذور غير مملحة.",
    ),
    "seafood_gap": (
        "زيادة المأكولات البحرية",
        "كان عدد حصص المأكولات البحرية أقل من 80٪ من الهدف الأسبوعي.",
        "استبدل مصدر بروتين في وجبة واحدة بمأكولات بحرية.",
    ),
    "dairy_alternative_gap": (
        "زيادة الألبان أو البدائل المدعمة",
        "كان المتوسط المسجل أقل من 80٪ من الهدف اليومي.",
        "أضف أو استبدل خيارًا بمنتج ألبان أو بديل مدعم مناسب.",
    ),
    "fiber_gap": (
        "زيادة الألياف",
        "كان متوسط الألياف أقل من 80٪ من الهدف.",
        "أضف أو استبدل خيارًا بمصدر غني بالألياف.",
    ),
}

_MICRONUTRIENT_NAMES: Final = {
    "potassium_gap": "البوتاسيوم",
    "calcium_gap": "الكالسيوم",
    "iron_gap": "الحديد",
    "magnesium_gap": "المغنيسيوم",
    "zinc_gap": "الزنك",
    "selenium_gap": "السيلينيوم",
    "vitamin_b12_gap": "فيتامين ب12",
    "folate_dfe_gap": "الفولات (DFE)",
    "vitamin_a_rae_gap": "فيتامين أ (RAE)",
    "iodine_gap": "اليود",
}
for _rule, _label in _MICRONUTRIENT_NAMES.items():
    COPY_CATALOG[_rule] = (
        f"مراجعة مصادر {_label}",
        f"ظل متوسط {_label} أقل من 80٪ من الهدف خلال فترتين مع تغطية قوية.",
        f"راجع الأطعمة المسجلة الغنية بـ{_label} واختر مصدرًا مناسبًا؛ لا تبدأ مكملاً بناءً على هذه النتيجة.",
    )

ALLOWED_INPUT_STATES: Final = {
    "eligible",
    "invalid_analysis_input",
    "stale_analysis",
    "superseded_analysis",
    "safety_exclusion",
    "unsupported_version",
}
DAY_STATUSES: Final = {"complete", "partial", "unregistered"}
STABLE_REPEAT_IDENTITY_FIELDS: Final = (
    "principal_ref",
    "operation",
    "source_goal_id",
    "event",
    "repeat_mode",
    "expected_version",
    "weekly_target_count",
)


def complete_days(vector: dict[str, Any]) -> int:
    days = vector.get("days")
    if days is None:
        value = vector.get("complete_days", 4)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("complete_days must be a non-negative integer")
        return value
    if len(days) != 7:
        raise ValueError("structured days must contain exactly seven records")
    parsed: list[date] = []
    complete = 0
    for day in days:
        parsed.append(date.fromisoformat(day["date"]))
        status = day.get("logging_status")
        if status not in DAY_STATUSES:
            raise ValueError(f"unknown logging_status: {status!r}")
        if day.get("analysis_eligible") is not (status == "complete"):
            raise ValueError("analysis_eligible must be true exactly for complete days")
        count = day.get("entry_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("entry_count must be a non-negative integer")
        complete += status == "complete"
    if parsed != sorted(set(parsed)) or any(
        b - a != timedelta(days=1) for a, b in zip(parsed, parsed[1:])
    ):
        raise ValueError("structured day dates must be unique, sorted, and consecutive")
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
    mode = normalized.get("action_mode", "review" if tier == 3 else "replace")
    if mode not in actions:
        raise ValueError(f"{key}: action_mode does not match closed vocabulary")
    if normalized.get("action_key", actions[mode]) != actions[mode]:
        raise ValueError(f"{key}: action_key does not match closed vocabulary")
    normalized.update(
        tier=tier,
        taxonomy_order=order,
        action_mode=mode,
        action_key=actions[mode],
        evidence_dimension=normalized.get("evidence_dimension", key),
        complete_days=day_count,
    )
    if normalized.get("derive_from_days"):
        days = [d for d in vector.get("days", []) if d["logging_status"] == "complete"]
        target = normalized["target"]
        if (
            not isinstance(target, (int, float))
            or isinstance(target, bool)
            or not math.isfinite(target)
            or target <= 0
        ):
            raise ValueError(f"{key}: target must be finite and positive")
        values: list[float] = []
        known_entries = total_entries = 0
        for day in days:
            total_entries += day["entry_count"]
            known = day.get("known_metric_entry_count")
            if (
                not isinstance(known, int)
                or isinstance(known, bool)
                or not 0 <= known <= day["entry_count"]
            ):
                raise ValueError(
                    f"{key}: known_metric_entry_count must be between zero and entry_count"
                )
            known_entries += known
            if day["entry_count"] == 0:
                values.append(0.0)
            elif normalized["metric_key"] in day.get("metrics", {}):
                value = day["metrics"][normalized["metric_key"]]
                if (
                    known == 0
                    or not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                ):
                    raise ValueError(f"{key}: known metric value must be finite")
                values.append(float(value))
            elif known != 0:
                raise ValueError(f"{key}: known metric count requires a metric value")
        if not values:
            raise ValueError(f"{key}: no complete-day metric evidence")
        normalized["coverage"] = (
            100.0 if total_entries == 0 else 100.0 * known_entries / total_entries
        )
        normalized["severity"] = round((target - sum(values) / len(values)) / target, 6)
    if not math.isfinite(normalized.get("severity", math.nan)):
        raise ValueError(f"{key}: severity must be finite")
    return normalized


def rejection_is_suppressed(context: dict[str, Any], candidates: list[dict[str, Any]]) -> bool:
    required = (
        "rejected_principal_ref",
        "current_principal_ref",
        "rejected_rule_key",
        "current_rule_key",
        "rejected_rules_version",
        "current_rules_version",
        "rejected_action_key",
    )
    if any(not isinstance(context.get(field), str) or not context[field] for field in required):
        raise ValueError("rejection context requires explicit non-empty identity fields")
    for field in (
        "rejected_analysis_revision",
        "current_analysis_revision",
        "new_complete_dates_after_rejection",
    ):
        value = context.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                "rejection context revisions and day count must be non-negative integers"
            )
    severity = context.get("rejected_severity")
    if (
        not isinstance(severity, (int, float))
        or isinstance(severity, bool)
        or not math.isfinite(severity)
    ):
        raise ValueError("rejected_severity must be finite")
    same = (
        context["rejected_principal_ref"] == context["current_principal_ref"]
        and context["rejected_rule_key"] == context["current_rule_key"]
        and context["rejected_rules_version"] == context["current_rules_version"]
    )
    if not same:
        return False
    matches = [c for c in candidates if c["key"] == context["current_rule_key"]]
    if len(matches) != 1:
        raise ValueError("rejection context must resolve exactly one current rule candidate")
    current = matches[0]
    changed = (
        round(current["severity"] - severity, 6) >= 0.10
        or current["action_key"] != context["rejected_action_key"]
    )
    return not (
        context["current_analysis_revision"] > context["rejected_analysis_revision"]
        and context["new_complete_dates_after_rejection"] >= 1
        and changed
    )


def eligible_candidate(candidate: dict[str, Any]) -> bool:
    if not (
        candidate.get("actionable") is True
        and candidate.get("coverage", 0) >= 75
        and candidate.get("complete_days", 4) >= 4
        and candidate.get("excluded") is not True
    ):
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
    count = complete_days(vector)
    if count < 4:
        return {"main": None, "secondary": None, "reason": "insufficient_complete_days"}
    normalized = [normalize_candidate(c, vector, count) for c in vector.get("candidates", [])]
    if vector.get("rejection_context") and rejection_is_suppressed(
        vector["rejection_context"], normalized
    ):
        return {"main": None, "secondary": None, "reason": "rejected_goal_suppression"}
    candidates = [
        c
        for c in normalized
        if eligible_candidate(c)
        and not (
            vector.get("calories_relation") == "above_target" and c.get("action_mode") == "add"
        )
    ]
    candidates.sort(key=rank_key)
    if not candidates:
        return {"main": None, "secondary": None, "reason": "no_eligible_priority"}
    main, secondary = candidates[0], None
    for candidate in candidates[1:]:
        if (
            candidate["severity"] < 0.25
            or candidate.get("conflict_group") == main.get("conflict_group")
            or candidate["evidence_dimension"] == main["evidence_dimension"]
            or candidate["action_key"] == main["action_key"]
            or candidate.get("conflicts_with") == main["key"]
            or main.get("conflicts_with") == candidate["key"]
            or (
                vector.get("calories_relation") == "above_target"
                and candidate.get("action_mode") == "add"
            )
        ):
            continue
        secondary = candidate
        break
    return {
        "main": main["key"],
        "secondary": secondary["key"] if secondary else None,
        "reason": "selected",
    }


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
    kind, current = event["type"], state["state"]
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
        state["progress"], state["version"] = event.get("derived_progress"), state["version"] + 1
        return goal_response(state, "progress_updated")
    if kind == "midweek_reminder":
        if (
            current != "active"
            or not event.get("midweek_eligible")
            or state.get("progress") not in {0, 0.0}
            or state.get("midweek_reminders", 0) >= 1
            or event.get("opted_out")
        ):
            return goal_response(state, "suppressed")
        state["midweek_reminders"], state["version"] = 1, state["version"] + 1
        return goal_response(state, "sent")
    if kind == "endweek_review":
        if (
            current not in {"active", "paused"}
            or not event.get("endweek_eligible")
            or state.get("endweek_reviews", 0) >= 1
        ):
            return goal_response(state, "suppressed")
        state["endweek_reviews"], state["version"] = 1, state["version"] + 1
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
    state["state"], state["version"] = next_state, state["version"] + 1
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


def evaluate_progress(vector: dict[str, Any]) -> dict[str, Any]:
    target = vector.get("target_count")
    if not isinstance(target, int) or isinstance(target, bool) or not 1 <= target <= 7:
        raise ValueError("progress target_count must be an integer from 1 to 7")
    complete = progress = 0
    for day in vector.get("days", []):
        status = day.get("logging_status")
        if status not in DAY_STATUSES:
            raise ValueError(f"unknown logging_status: {status!r}")
        if status == "complete":
            complete += 1
            progress += day.get("qualifies") is True
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


def repeat_response(
    state: dict[str, Any], result: str, new_goal: dict[str, Any] | None = None
) -> dict[str, Any]:
    source, priority = state["source_goal"], state["current_priority"]
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


def repeat_request_identity(
    state: dict[str, Any], event: dict[str, Any], fields: tuple[str, ...] | list[str]
) -> dict[str, Any]:
    values = {
        "principal_ref": state.get("principal_ref"),
        "operation": "behavior_goal_repeat",
        "source_goal_id": state["source_goal"]["goal_id"],
        "event": event.get("type"),
        "repeat_mode": event.get("repeat_mode"),
        "expected_version": event.get("expected_version"),
        "weekly_target_count": event.get("weekly_target_count"),
        "captured_diary_date": state.get("captured_diary_date"),
        "current_recommendation_id": state.get("current_priority", {}).get("recommendation_id"),
    }
    if not isinstance(state.get("principal_ref"), str) or not state["principal_ref"]:
        raise ValueError("repeat requires a non-empty Principal reference")
    unknown = [field for field in fields if field not in values]
    if unknown:
        raise ValueError(f"unknown repeat request identity field: {unknown[0]}")
    return {field: values[field] for field in fields}


def apply_repeat_event(
    state: dict[str, Any],
    event: dict[str, Any],
    replays: dict[str, dict[str, Any]],
    identity_fields: tuple[str, ...] | list[str] = STABLE_REPEAT_IDENTITY_FIELDS,
) -> dict[str, Any]:
    fixture = event.get("_server_state_before")
    if fixture is not None:
        if not isinstance(fixture, dict):
            raise ValueError("server-state fixture must be an object")
        if "captured_diary_date" in fixture:
            state["captured_diary_date"] = fixture["captured_diary_date"]
        if "current_priority" in fixture:
            state["current_priority"] = deepcopy(fixture["current_priority"])
    if event.get("type") != "repeat":
        return repeat_response(state, "goal_state_conflict")
    key = event.get("idempotency_key")
    if not isinstance(key, str) or not key:
        raise ValueError("repeat requires a non-empty idempotency key")
    identity = repeat_request_identity(state, event, identity_fields)
    if key in replays:
        recorded = replays[key]
        return (
            deepcopy(recorded["response"])
            if recorded["request"] == identity
            else repeat_response(state, "idempotency_key_conflict")
        )
    source = state["source_goal"]
    if event.get("expected_version") != source["version"]:
        return repeat_response(state, "goal_version_conflict")
    if source["state"] != "incomplete":
        return repeat_response(state, "goal_state_conflict")
    captured = date.fromisoformat(state["captured_diary_date"])
    old_start, old_end = (
        date.fromisoformat(source["window_start"]),
        date.fromisoformat(source["window_end"]),
    )
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
        new_target, result = source["weekly_target_count"], "repeated"
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
    new_id = event.get("_server_generated_goal_id")
    if (
        not isinstance(new_id, str)
        or not new_id
        or new_id == source["goal_id"]
        or new_id in state.get("created_goal_ids", [])
    ):
        raise ValueError("repeat server-generated goal ID must be unique and distinct")
    new_start = max(captured, old_end + timedelta(days=1))
    new_goal = {
        "goal_id": new_id,
        "root_goal_id": source.get("root_goal_id", source["goal_id"]),
        "previous_goal_id": source["goal_id"],
        "sequence_number": source.get("sequence_number", 1) + 1,
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
    state.setdefault("created_goal_ids", []).append(new_id)
    state["new_goal"] = deepcopy(new_goal)
    response = repeat_response(state, result, new_goal)
    replays[key] = {"request": identity, "response": deepcopy(response)}
    return response


def validate_producer(
    source: WeeklyPriorityAnalysisInputV1, *, stale: bool = False, superseded: bool = False
) -> str:
    if (
        source.interface_version not in SUPPORTED_INTERFACE_VERSIONS
        or source.analysis_rules_version not in SUPPORTED_ANALYSIS_RULES_VERSIONS
        or source.nutrition_registry_version not in SUPPORTED_NUTRITION_REGISTRY_VERSIONS
        or source.food_group_rules_version not in SUPPORTED_FOOD_GROUP_RULES_VERSIONS
        or source.nova_rules_version not in SUPPORTED_NOVA_RULES_VERSIONS
        or not set(source.snapshot_schema_versions).issubset(SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS)
    ):
        return "unsupported_version"
    if superseded:
        return "superseded_analysis"
    if stale or "stale_evidence" in source.safety_flags:
        return "stale_analysis"
    if source.safety_flags:
        return "safety_exclusion"
    if sum(day.analysis_eligible for day in source.days) < 4:
        return "invalid_analysis_input"
    return "eligible"


def priority_registry() -> list[dict[str, Any]]:
    metric_by_rule = {rule_key: metric_key for metric_key, rule_key in METRIC_RULES.items()}
    return [
        {
            "rule_key": key,
            "metric_key": metric_by_rule[key],
            "tier": tier,
            "taxonomy_order": order,
            "actions": actions,
            "title_ar": COPY_CATALOG[key][0],
            "reason_ar": COPY_CATALOG[key][1],
            "action_ar": COPY_CATALOG[key][2],
        }
        for key, (tier, order, actions) in sorted(RULE_META.items(), key=lambda item: item[1][1])
    ]
