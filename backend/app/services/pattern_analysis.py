from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import re
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    DiaryDayStatus,
    DiaryDayStatusValue,
    DiaryEntry,
    NutritionAnalysis,
    NutritionAnalysisCommandIdempotency,
    NutritionAnalysisEvidenceRef,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
    utcnow,
)
from app.nutrition_rules.analysis import (
    ANALYSIS_RULES_VERSION,
    DAILY_METRICS,
    METRIC_REGISTRY,
    analysis_windows,
    compare_descriptive_metric,
    compare_target_metric,
    coverage_band_counts,
    latency_band_counts,
    metric_coverage,
    persistence_evidence,
    range_metric_status,
    rank_contributors,
    round6,
    stale_reason_counts,
)
from app.nutrition_rules.manifest import rules_manifest_hash
from app.nutrition_rules.versions import VERSIONS
from app.schemas import (
    AnalysisComparisonV1,
    AnalysisContributorV1,
    AnalysisContributorsV1,
    AnalysisDayFactV1,
    AnalysisDayMetricValueV1,
    AnalysisEvaluateCommandV1,
    AnalysisMetricFactV1,
    AnalysisMetricTargetV1,
    AnalysisPersistenceV1,
    AnalysisSourceVersionBundleV1,
    NutritionAnalysisMonitoringResponseV1,
    NutritionPatternAnalysisHistoryItemV1,
    NutritionPatternAnalysisHistoryPageV1,
    NutritionPatternAnalysisResponseV1,
    OpaqueEvidenceRefV1,
    PeriodMetricEvidenceV1,
    TargetPlanAnalysisRefV1,
    WeeklyPriorityAnalysisInputV1,
)
from app.services.diary import totals_for_entry
from app.services.snapshot import read_snapshot_v2, read_snapshot_v3
from app.services.target_plans import project_week_target_context, target_for_date


_KEY_RE = re.compile(r"^[\x21-\x7e]{1,128}$")
_ETAG_RE = re.compile(r'^"analysis-(?P<analysis_id>[0-9a-fA-F-]{36})-r(?P<revision>[1-9][0-9]*)"$')
_STALE_EVENTS = {
    "day_reopened",
    "day_version_changed",
    "target_source_changed",
    "source_snapshot_corrected",
    "source_version_unsupported",
}


class PatternAnalysisError(RuntimeError):
    def __init__(self, code: str, status_code: int, message_ar: str) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.message_ar = message_ar


@dataclass(frozen=True, slots=True)
class _EntryFact:
    entry: DiaryEntry
    nutrition: dict[str, float | None]
    groups: dict[str, float]
    group_known: bool
    traits: frozenset[str]
    nova: str | None
    nova_calories: float | None
    registry_version: str
    group_version: str
    nova_version: str
    source_version: str


@dataclass(frozen=True, slots=True)
class _TargetResolution:
    target: AnalysisMetricTargetV1 | None
    state: str


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _content_hash(document: dict[str, Any]) -> str:
    deterministic = dict(document)
    deterministic.pop("generated_at", None)
    return _hash(deterministic)


def _etag(analysis_id: UUID, revision: int) -> str:
    return f'"analysis-{analysis_id}-r{revision}"'


def _key_digest(principal_id: UUID, key: str) -> str:
    return hmac.new(principal_id.bytes, key.encode(), hashlib.sha256).hexdigest()


def _command_hash(principal_id: UUID, command: AnalysisEvaluateCommandV1) -> str:
    return _hash(
        {
            "operation": "nutrition_analysis.evaluate",
            "principal_id": str(principal_id),
            **command.model_dump(mode="json"),
        }
    )


def _unexpired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > utcnow()


def _date_list(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _decode_cursor(cursor: str) -> tuple[date, UUID, int]:
    try:
        payload = json.loads(urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return date.fromisoformat(payload["date"]), UUID(payload["id"]), int(payload["revision"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise PatternAnalysisError("INVALID_CURSOR", 422, "مؤشر التصفح غير صالح.") from error


def _encode_cursor(item: NutritionAnalysisRevision) -> str:
    return (
        urlsafe_b64encode(
            _canonical(
                {
                    "date": item.period_end.isoformat(),
                    "id": str(item.analysis_id),
                    "revision": item.revision,
                }
            )
        )
        .decode()
        .rstrip("=")
    )


def _parse_snapshot(entry: DiaryEntry) -> _EntryFact:
    if entry.snapshot_schema_version not in {2, 3}:
        raise PatternAnalysisError(
            "UNSUPPORTED_HISTORICAL_VERSION", 422, "تعذر فتح هذه النسخة بإصدارها الأصلي"
        )
    snapshot = (
        read_snapshot_v2(entry.nutrition_snapshot)
        if entry.snapshot_schema_version == 2
        else read_snapshot_v3(entry.nutrition_snapshot)
    )
    totals = totals_for_entry(entry).model_dump()
    groups = {
        item.group_key: round6(item.amount_per_captured_unit * float(entry.quantity))
        for item in snapshot.food_groups.contributions
    }
    calories = totals.get("calories")
    nova = (
        snapshot.nova.classification
        if snapshot.nova.review_status == "reviewed"
        and snapshot.nova.classification in {"1", "2", "3", "4"}
        else None
    )
    return _EntryFact(
        entry=entry,
        nutrition={key: (None if value is None else float(value)) for key, value in totals.items()},
        groups=groups,
        group_known=snapshot.food_groups.status in {"known", "estimated"},
        traits=frozenset(snapshot.food_groups.traits),
        nova=nova,
        nova_calories=None if nova is None or calories is None else float(calories),
        registry_version=snapshot.versions.nutrition_registry_version,
        group_version=snapshot.versions.food_group_rules_version,
        nova_version=snapshot.versions.nova_rules_version,
        source_version=f"snapshot-{entry.snapshot_schema_version}",
    )


def _nutrition_field(metric_key: str) -> str:
    if metric_key == "energy:calories_kcal_per_day":
        return "calories"
    if metric_key.startswith("macro:"):
        return metric_key.split(":", 1)[1].replace("_per_day", "")
    return metric_key.split(":", 1)[1]


def _entry_metric_value(fact: _EntryFact, metric_key: str) -> float | None:
    if metric_key in DAILY_METRICS:
        return fact.nutrition.get(_nutrition_field(metric_key))
    if not fact.group_known and metric_key.startswith(("group:", "protein:")):
        return None
    group = fact.groups
    if metric_key == "group:fruit_vegetable_g_per_day":
        vegetables = 0.0 if "starchy_root" in fact.traits else group.get("vegetables", 0.0)
        fruit = group.get("fruits", 0.0)
        if "fruit_liquid_100_percent" in fact.traits:
            fruit = min(fruit, 150.0)
        return vegetables + fruit
    if metric_key == "group:legumes_servings_per_period":
        return group.get("legumes", 0.0) / 80
    if metric_key == "group:nuts_seeds_servings_per_period":
        return group.get("nuts_seeds", 0.0) / 30
    if metric_key == "group:seafood_servings_per_period":
        return group.get("seafood", 0.0) / 100
    if metric_key == "group:omega3_seafood_servings_per_period":
        return group.get("seafood", 0.0) / 100 if "omega3_rich_seafood" in fact.traits else 0.0
    if metric_key == "group:red_meat_g_per_period":
        return group.get("red_meat", 0.0)
    if metric_key in {
        "group:processed_meat_occurrence_days",
        "group:sugar_sweetened_beverage_occurrence_days",
        "group:sweets_occurrence_days",
    }:
        return group.get(metric_key.split(":", 1)[1].replace("_occurrence_days", ""), 0.0)
    if metric_key == "group:dairy_fortified_servings_per_day":
        amount = group.get("dairy_fortified_alternatives", 0.0)
        subtype = next(
            (
                item.subtype_key
                for item in (
                    read_snapshot_v2(fact.entry.nutrition_snapshot)
                    if fact.entry.snapshot_schema_version == 2
                    else read_snapshot_v3(fact.entry.nutrition_snapshot)
                ).food_groups.contributions
                if item.group_key == "dairy_fortified_alternatives"
            ),
            None,
        )
        serving = {
            "milk_laban_kefir": 250,
            "yogurt": 200,
            "hard_cheese": 30,
            "cottage_ricotta": 120,
            "fortified_plant_alternative": 250,
        }.get(subtype or "", 250)
        if subtype == "fortified_plant_alternative" and "calcium_fortified" not in fact.traits:
            return 0.0
        return amount / serving
    if metric_key == "protein:source_diversity_count":
        return float(
            sum(
                group.get(key, 0) > 0
                for key in (
                    "legumes",
                    "nuts_seeds",
                    "seafood",
                    "eggs",
                    "poultry",
                    "red_meat",
                    "dairy_fortified_alternatives",
                )
            )
        )
    if metric_key.startswith("nova:"):
        return fact.nova_calories
    if metric_key == "group:whole_grain_share_percent":
        return group.get("whole_grains", 0.0) + group.get("refined_grains", 0.0)
    raise ValueError(f"unsupported metric {metric_key}")


def _day_metric_value(facts: list[_EntryFact], metric_key: str) -> tuple[float | None, int, int]:
    if not facts:
        return 0.0, 0, 0
    if metric_key == "group:fruit_vegetable_g_per_day":
        known = [fact for fact in facts if fact.group_known]
        if not known:
            return None, 0, len(facts)
        vegetables = sum(
            fact.groups.get("vegetables", 0.0)
            for fact in known
            if "starchy_root" not in fact.traits
        )
        whole_fruit = sum(
            fact.groups.get("fruits", 0.0)
            for fact in known
            if "fruit_liquid_100_percent" not in fact.traits
        )
        liquid_fruit = min(
            150.0,
            sum(
                fact.groups.get("fruits", 0.0)
                for fact in known
                if "fruit_liquid_100_percent" in fact.traits
            ),
        )
        return round6(vegetables + whole_fruit + liquid_fruit), len(known), len(facts)
    values = [_entry_metric_value(item, metric_key) for item in facts]
    known = [value for value in values if value is not None]
    return (round6(sum(known)) if known else None, len(known), len(values))


def _day_fact(
    day: date, status: DiaryDayStatus | None, entries: list[_EntryFact]
) -> AnalysisDayFactV1:
    logging_status = (
        getattr(status.status, "value", status.status)
        if status
        else "partial"
        if entries
        else "unregistered"
    )
    eligible = logging_status == "complete"
    metrics: list[AnalysisDayMetricValueV1] = []
    if eligible:
        for key, (unit, _) in sorted(METRIC_REGISTRY.items()):
            value, known, total = _day_metric_value(entries, key)
            metrics.append(
                AnalysisDayMetricValueV1(
                    metric_key=key,
                    value=value,
                    value_state="unknown"
                    if value is None and entries
                    else "explicit_zero"
                    if value in {None, 0}
                    else "known",
                    known_entry_count=known,
                    total_entry_count=total,
                    amount_qualifier="exact"
                    if not entries or known == total
                    else "at_least"
                    if known
                    else "unavailable",
                    unit=unit,
                )
            )
    return AnalysisDayFactV1(
        date=day,
        logging_status=logging_status,
        logging_status_version=status.version if status else 0,
        entry_count=status.entry_count if status else len(entries),
        analysis_eligible=eligible,
        completed_at=status.completed_at if status else None,
        snapshot_schema_versions=sorted(
            {
                item.entry.snapshot_schema_version
                for item in entries
                if item.entry.snapshot_schema_version
            }
        ),
        metric_values=metrics,
    )


def _static_target(metric_key: str) -> AnalysisMetricTargetV1 | None:
    values: dict[str, tuple[str, float]] = {
        "group:fruit_vegetable_g_per_day": ("minimum", 400),
        "group:legumes_servings_per_period": ("minimum", 3),
        "group:whole_grain_share_percent": ("minimum", 50),
        "group:nuts_seeds_servings_per_period": ("minimum", 5),
        "group:seafood_servings_per_period": ("minimum", 2),
        "group:omega3_seafood_servings_per_period": ("minimum", 1),
        "group:dairy_fortified_servings_per_day": ("minimum", 2),
        "group:red_meat_g_per_period": ("maximum", 500),
    }
    value = values.get(metric_key)
    return (
        AnalysisMetricTargetV1(type=value[0], value=value[1], source_plan_ids=[]) if value else None
    )


def _plan_target(
    metric_key: str, targets_by_day: dict[date, Any], numeric_dates: list[date]
) -> _TargetResolution:
    candidates: list[tuple[str, float, float | None, UUID | None]] = []
    for day in numeric_dates:
        source = targets_by_day[day]
        target = source.targets
        if target is None or source.target_provenance != "versioned_plan" or source.plan is None:
            return _TargetResolution(None, "missing")
        if target.safety_outcome != "normal":
            return _TargetResolution(None, "unsafe")
        plan_id = source.plan.id if source.plan else None
        if metric_key == "energy:calories_kcal_per_day":
            candidates.append(("maximum", float(target.final_target_calories), None, plan_id))
        elif metric_key == "macro:protein_g_per_day":
            candidates.append(("minimum", float(target.protein_g), None, plan_id))
        elif metric_key in {"macro:carb_g_per_day", "macro:fat_g_per_day"}:
            scalar = float(target.carb_g if metric_key == "macro:carb_g_per_day" else target.fat_g)
            candidates.append(("range", scalar, scalar, plan_id))
        else:
            key = _nutrition_field(metric_key)
            found = next(
                (
                    item
                    for item in target.additional_targets
                    if item.key == key and item.target_value is not None
                ),
                None,
            )
            if found is None or found.target_type not in {
                "minimum",
                "maximum",
                "adequate",
                "recommended",
            }:
                return _TargetResolution(None, "missing")
            direction = "maximum" if found.target_type == "maximum" else "minimum"
            candidates.append((direction, float(found.target_value), None, plan_id))
    if not candidates:
        return _TargetResolution(None, "missing")
    if any(not math.isfinite(value) or value <= 0 for _, value, _, _ in candidates):
        raise PatternAnalysisError(
            "INVALID_ANALYSIS_SOURCE", 422, "تعذر إنشاء التحليل من بيانات هدف غير صالحة."
        )
    if len({(kind, value, upper) for kind, value, upper, _ in candidates}) != 1:
        return _TargetResolution(None, "incompatible")
    kind, value, upper = candidates[0][:3]
    plan_ids = sorted({pid for _, _, _, pid in candidates if pid}, key=str)
    if kind == "range":
        target_value = AnalysisMetricTargetV1(
            type=kind, lower=value, upper=upper, source_plan_ids=plan_ids
        )
    else:
        target_value = AnalysisMetricTargetV1(type=kind, value=value, source_plan_ids=plan_ids)
    return _TargetResolution(target_value, "compatible")


def _period_evidence(
    days: list[AnalysisDayFactV1],
    metric_key: str,
    target: AnalysisMetricTargetV1 | None,
    entry_map: dict[date, list[_EntryFact]],
    *,
    target_state: str = "compatible",
) -> PeriodMetricEvidenceV1:
    raw_days = []
    refs: list[OpaqueEvidenceRefV1] = []
    for day in days:
        values = []
        if day.logging_status == "complete":
            for fact in entry_map[day.date]:
                value = _entry_metric_value(fact, metric_key)
                values.append(value)
                if value is not None:
                    refs.append(
                        OpaqueEvidenceRefV1(
                            source_ref=fact.entry.id,
                            diary_date=day.date,
                            source_version=fact.source_version,
                        )
                    )
        raw_days.append({"status": day.logging_status, "values": values})
    coverage = metric_coverage(raw_days)
    value = coverage["value"]
    if metric_key == "group:fruit_vegetable_g_per_day":
        day_values = [
            _day_metric_value(entry_map[day.date], metric_key)[0]
            for day in days
            if day.logging_status == "complete"
        ]
        numeric = [item for item in day_values if item is not None]
        value = round6(sum(numeric) / len(numeric)) if numeric else None
    elif metric_key in {
        "group:legumes_servings_per_period",
        "group:nuts_seeds_servings_per_period",
        "group:seafood_servings_per_period",
        "group:omega3_seafood_servings_per_period",
        "group:red_meat_g_per_period",
    }:
        observations = [
            _day_metric_value(entry_map[day.date], metric_key)[0]
            for day in days
            if day.logging_status == "complete"
        ]
        known = [item for item in observations if item is not None]
        value = round6(sum(known)) if known else None
    elif metric_key.endswith("_occurrence_days"):
        observations = [
            _day_metric_value(entry_map[day.date], metric_key)[0]
            for day in days
            if day.logging_status == "complete"
        ]
        known = [item for item in observations if item is not None]
        value = float(sum(item > 0 for item in known)) if known else None
    elif metric_key == "protein:source_diversity_count":
        groups = set()
        known_evidence = False
        for day in days:
            if day.logging_status != "complete":
                continue
            if not entry_map[day.date]:
                known_evidence = True
            for fact in entry_map[day.date]:
                known_evidence = known_evidence or fact.group_known
                if not fact.group_known:
                    continue
                groups.update(
                    key
                    for key in (
                        "legumes",
                        "nuts_seeds",
                        "seafood",
                        "eggs",
                        "poultry",
                        "red_meat",
                        "dairy_fortified_alternatives",
                    )
                    if fact.groups.get(key, 0) > 0
                )
        value = float(len(groups)) if known_evidence else None
    elif metric_key == "group:whole_grain_share_percent":
        whole = sum(
            fact.groups.get("whole_grains", 0)
            for day in days
            if day.logging_status == "complete"
            for fact in entry_map[day.date]
            if fact.group_known
        )
        refined = sum(
            fact.groups.get("refined_grains", 0)
            for day in days
            if day.logging_status == "complete"
            for fact in entry_map[day.date]
            if fact.group_known
        )
        value = None if whole + refined == 0 else round6(whole / (whole + refined) * 100)
    elif metric_key == "nova:nova4_calorie_share_percent":
        known = [
            fact
            for day in days
            if day.logging_status == "complete"
            for fact in entry_map[day.date]
            if fact.nova_calories is not None
        ]
        denominator = sum(fact.nova_calories or 0 for fact in known)
        numerator = sum(fact.nova_calories or 0 for fact in known if fact.nova == "4")
        value = (
            0.0
            if known and denominator == 0
            else None
            if not known
            else round6(numerator / denominator * 100)
        )
    elif metric_key == "nova:nova4_occurrence_days":
        known_days: list[bool] = []
        for day in days:
            if day.logging_status != "complete":
                continue
            facts = entry_map[day.date]
            if not facts:
                known_days.append(False)
            elif any(fact.nova_calories is not None for fact in facts):
                known_days.append(
                    any(
                        fact.nova == "4"
                        and fact.nova_calories is not None
                        and fact.nova_calories > 0
                        for fact in facts
                    )
                )
        value = float(sum(known_days)) if known_days else None
    if value is None:
        status = "unavailable"
        value_state = "unknown"
    elif target_state == "incompatible":
        status = "target_incompatible"
        value_state = "explicit_zero" if value == 0 else "known"
    elif target is None:
        status = "observed"
        value_state = "explicit_zero" if value == 0 else "known"
    elif target.type == "range":
        status = range_metric_status(value, target.lower, target.upper)["status"]
        value_state = "explicit_zero" if value == 0 else "known"
    elif target.type == "minimum":
        status = (
            "at_target"
            if value == target.value
            else "within_target"
            if value > float(target.value)
            else "below_target"
        )
        value_state = "explicit_zero" if value == 0 else "known"
    else:
        status = (
            "at_target"
            if value == target.value
            else "within_target"
            if value < float(target.value)
            else "above_target"
        )
        value_state = "explicit_zero" if value == 0 else "known"
    return PeriodMetricEvidenceV1(
        value=value,
        value_state=value_state,
        amount_qualifier="unavailable" if value is None else coverage["amount_qualifier"],
        complete_day_count=coverage["complete_day_count"],
        numeric_day_count=coverage["numeric_day_count"],
        known_entry_count=coverage["known_entry_count"],
        total_entry_count=coverage["total_entry_count"],
        coverage_percent=coverage["coverage_percent"],
        confidence=coverage["confidence"],
        status=status,
        evidence_refs=sorted(refs, key=lambda item: (item.diary_date, str(item.source_ref))),
    )


def _metric_kind(metric_key: str) -> tuple[str, str]:
    if metric_key in DAILY_METRICS or metric_key in {
        "group:fruit_vegetable_g_per_day",
        "group:dairy_fortified_servings_per_day",
    }:
        return "daily_average", "average_numeric_days"
    if metric_key.endswith("_occurrence_days"):
        return "occurrence_days", "distinct_positive_dates"
    if metric_key == "group:whole_grain_share_percent":
        return "share_percent", "ratio_percent"
    if metric_key == "nova:nova4_calorie_share_percent":
        return "calorie_share", "ratio_percent"
    if metric_key == "protein:source_diversity_count":
        return "diversity_count", "distinct_source_count"
    return "period_total", "sum_period"


def _comparison(
    current: PeriodMetricEvidenceV1,
    previous: PeriodMetricEvidenceV1,
    target: AnalysisMetricTargetV1 | None,
    direction: str,
    metric_key: str,
    *,
    target_state: str = "compatible",
) -> AnalysisComparisonV1:
    if target_state == "incompatible":
        return AnalysisComparisonV1(
            status="not_comparable",
            reason="target_incompatible",
            difference=None,
            normalized_adverse_delta=None,
        )
    if target_state in {"missing", "unsafe"}:
        return AnalysisComparisonV1(
            status="not_comparable",
            reason="unavailable_value",
            difference=None,
            normalized_adverse_delta=None,
        )
    if current.value is None or previous.value is None:
        return AnalysisComparisonV1(
            status="not_comparable",
            reason="unavailable_value",
            difference=None,
            normalized_adverse_delta=None,
        )
    difference = round6(current.value - previous.value)
    if target and target.type in {"minimum", "maximum"}:
        result = compare_target_metric(
            {
                "direction": target.type,
                "target": target.value,
                "current": {
                    "value": current.value,
                    "coverage": current.coverage_percent or 0,
                    "complete_days": current.complete_day_count,
                },
                "previous": {
                    "value": previous.value,
                    "coverage": previous.coverage_percent or 0,
                    "complete_days": previous.complete_day_count,
                },
            }
        )
        if result["status"] == "descriptive_only":
            return AnalysisComparisonV1(
                status="not_comparable",
                reason="limited_coverage",
                difference=difference,
                normalized_adverse_delta=None,
            )
        return AnalysisComparisonV1(
            status=result["status"],
            reason=result["reason"],
            difference=difference,
            normalized_adverse_delta=result.get("normalized_adverse_delta"),
        )
    if target and target.type == "range":
        periods = (current, previous)
        if any(item.complete_day_count < 4 for item in periods):
            return AnalysisComparisonV1(
                status="not_comparable",
                reason="insufficient_complete_days",
                difference=difference,
                normalized_adverse_delta=None,
            )
        coverages = [item.coverage_percent for item in periods]
        if any(value is None or value < 50 for value in coverages):
            return AnalysisComparisonV1(
                status="not_comparable",
                reason="insufficient_coverage",
                difference=difference,
                normalized_adverse_delta=None,
            )
        if abs(float(coverages[0]) - float(coverages[1])) > 10:
            return AnalysisComparisonV1(
                status="not_comparable",
                reason="coverage_mismatch",
                difference=difference,
                normalized_adverse_delta=None,
            )
        if any(float(value) < 75 for value in coverages):
            return AnalysisComparisonV1(
                status="not_comparable",
                reason="limited_coverage",
                difference=difference,
                normalized_adverse_delta=None,
            )
        current_distance = range_metric_status(current.value, target.lower, target.upper)[
            "adverse_distance"
        ]
        previous_distance = range_metric_status(previous.value, target.lower, target.upper)[
            "adverse_distance"
        ]
        delta = round6(current_distance - previous_distance)
        status = (
            "no_material_change" if abs(delta) < 0.10 else "improved" if delta < 0 else "worsened"
        )
        return AnalysisComparisonV1(
            status=status,
            reason="comparable",
            difference=difference,
            normalized_adverse_delta=delta,
        )
    threshold = 5 if metric_key == "nova:nova4_calorie_share_percent" else 1
    result = compare_descriptive_metric(
        {"current": current.value, "previous": previous.value, "material_threshold": threshold}
    )
    return AnalysisComparisonV1(
        status=result["status"],
        reason="comparable",
        difference=result["difference"],
        normalized_adverse_delta=None,
    )


def _persistence(
    current: PeriodMetricEvidenceV1,
    previous: PeriodMetricEvidenceV1,
    target: AnalysisMetricTargetV1 | None,
    direction: str,
    *,
    target_state: str = "compatible",
) -> AnalysisPersistenceV1:
    if target_state == "incompatible":
        return AnalysisPersistenceV1(qualifies=False, reason="target_changed")
    if target is None:
        return AnalysisPersistenceV1(qualifies=False, reason="current_not_qualifying")
    if current.value is None:
        return AnalysisPersistenceV1(qualifies=False, reason="current_not_qualifying")
    if previous.value is None:
        return AnalysisPersistenceV1(qualifies=False, reason="previous_not_qualifying")
    if target.type == "range":
        periods = (current, previous)
        if any(item.complete_day_count < 4 for item in periods):
            return AnalysisPersistenceV1(qualifies=False, reason="insufficient_complete_days")
        if any(item.coverage_percent is None or item.coverage_percent < 75 for item in periods):
            return AnalysisPersistenceV1(qualifies=False, reason="insufficient_coverage")
        below = [float(item.value) / float(target.lower) <= 0.80 for item in periods]
        above = [float(item.value) > float(target.upper) for item in periods]
        qualifies = all(below) or all(above)
        if qualifies:
            return AnalysisPersistenceV1(qualifies=True, reason="qualified")
        current_qualifies = below[0] or above[0]
        return AnalysisPersistenceV1(
            qualifies=False,
            reason="previous_not_qualifying" if current_qualifies else "current_not_qualifying",
        )
    result = persistence_evidence(
        {
            "direction": target.type,
            "target": target.value,
            "current": {
                "value": current.value,
                "coverage": current.coverage_percent or 0,
                "complete_days": current.complete_day_count,
            },
            "previous": {
                "value": previous.value,
                "coverage": previous.coverage_percent or 0,
                "complete_days": previous.complete_day_count,
            },
        }
    )
    return AnalysisPersistenceV1(**result)


def _contributors(
    days: list[AnalysisDayFactV1],
    metric_key: str,
    entry_map: dict[date, list[_EntryFact]],
    unit: str,
) -> list[AnalysisContributorV1]:
    items = []
    by_ref: dict[str, _EntryFact] = {}
    for day in days:
        if day.logging_status != "complete":
            continue
        for fact in entry_map[day.date]:
            value = _entry_metric_value(fact, metric_key)
            if metric_key.startswith("nova:"):
                value = (
                    fact.nova_calories
                    if fact.nova == "4"
                    else 0.0
                    if fact.nova is not None
                    else None
                )
            elif metric_key == "group:whole_grain_share_percent":
                value = fact.groups.get("whole_grains", 0.0) if fact.group_known else None
            if value is not None and value != 0:
                ref = str(fact.entry.id)
                by_ref[ref] = fact
                items.append({"ref": ref, "date": day.date.isoformat(), "value": value})
    if metric_key.endswith("_occurrence_days"):
        per_date: dict[str, dict[str, Any]] = {}
        for item in items:
            if float(item["value"]) <= 0:
                continue
            existing = per_date.get(item["date"])
            if existing is None or (-float(item["value"]), item["ref"]) < (
                -float(existing["value"]),
                existing["ref"],
            ):
                per_date[item["date"]] = item
        items = list(per_date.values())
    ranked = rank_contributors(items)["refs"]
    return [
        AnalysisContributorV1(
            source_ref=by_ref[ref].entry.id,
            diary_date=by_ref[ref].entry.entry_date,
            source_version=by_ref[ref].source_version,
            contribution_value=abs(
                float(next(item["value"] for item in items if item["ref"] == ref))
            ),
            unit=unit,
        )
        for ref in ranked
    ]


def _target_refs(targets_by_day: dict[date, Any]) -> list[TargetPlanAnalysisRefV1]:
    refs: dict[UUID, TargetPlanAnalysisRefV1] = {}
    for source in targets_by_day.values():
        if source.plan is None:
            continue
        plan = source.plan
        refs[plan.id] = TargetPlanAnalysisRefV1(
            id=plan.id,
            effective_from=plan.effective_from,
            effective_to=plan.effective_to,
            calculation_document_schema_version=1,
            calculation_engine_version=plan.targets.calculation_engine_version,
            nutrition_registry_version=plan.targets.nutrition_registry_version,
            safety_outcome=plan.targets.safety_outcome,
            target_document_hash=_hash(plan.targets.model_dump(mode="json")),
        )
    return sorted(refs.values(), key=lambda item: (item.effective_from, str(item.id)))


def _build_source(
    session: Session, principal: PrincipalContext, as_of: date
) -> tuple[
    dict[str, Any],
    list[AnalysisDayFactV1],
    list[AnalysisDayFactV1],
    dict[date, list[_EntryFact]],
    dict[date, Any],
]:
    windows = analysis_windows(as_of)
    previous_start = date.fromisoformat(windows["previous_period_start"])
    period_end = date.fromisoformat(windows["period_end"])
    dates = _date_list(previous_start, period_end)
    status_rows = session.exec(
        select(DiaryDayStatus)
        .where(
            DiaryDayStatus.principal_id == principal.principal_id,
            DiaryDayStatus.diary_date >= previous_start,
            DiaryDayStatus.diary_date <= period_end,
        )
        .order_by(DiaryDayStatus.diary_date)
        .with_for_update()
    ).all()
    statuses = {row.diary_date: row for row in status_rows}
    entries = session.exec(
        select(DiaryEntry)
        .where(
            DiaryEntry.principal_id == principal.principal_id,
            DiaryEntry.entry_date >= previous_start,
            DiaryEntry.entry_date <= period_end,
        )
        .order_by(DiaryEntry.entry_date, DiaryEntry.id)
    ).all()
    entry_map: dict[date, list[_EntryFact]] = {day: [] for day in dates}
    for entry in entries:
        entry_map[entry.entry_date].append(_parse_snapshot(entry))
    for day, status in statuses.items():
        if (
            status.entry_count != len(entry_map[day])
            or status.status == DiaryDayStatusValue.complete
            and status.completed_at is None
        ):
            raise PatternAnalysisError(
                "INVALID_ANALYSIS_SOURCE", 422, "تعذر إنشاء التحليل من البيانات الحالية."
            )
    context = project_week_target_context(
        session, principal, previous_start, period_end, authoritative_current_date=as_of
    )
    targets = {day: target_for_date(context, day) for day in dates}
    day_facts = [_day_fact(day, statuses.get(day), entry_map[day]) for day in dates]
    previous_days, current_days = day_facts[:7], day_facts[7:]
    facts = [fact for values in entry_map.values() for fact in values]
    versions = {
        "analysis_rules_version": ANALYSIS_RULES_VERSION,
        "nutrition_registry_versions": sorted({fact.registry_version for fact in facts}),
        "calculation_engine_version": VERSIONS.calculation_engine_version,
        "food_group_rules_versions": sorted({fact.group_version for fact in facts}),
        "source_reliability_rules_version": VERSIONS.source_reliability_rules_version,
        "nova_rules_versions": sorted({fact.nova_version for fact in facts}),
        "snapshot_schema_versions": sorted(
            {
                fact.entry.snapshot_schema_version
                for fact in facts
                if fact.entry.snapshot_schema_version
            }
        ),
        "status_evidence_version": 1,
        "rules_manifest_hash": rules_manifest_hash(),
    }
    if any(
        len(versions[key]) > 1
        for key in (
            "nutrition_registry_versions",
            "food_group_rules_versions",
            "nova_rules_versions",
        )
    ):
        raise PatternAnalysisError(
            "INVALID_ANALYSIS_SOURCE", 422, "تعذر إنشاء التحليل بسبب عدم توافق إصدارات المصدر."
        )
    source = {
        "principal_ref": str(principal.principal_id),
        "as_of_diary_date": as_of.isoformat(),
        "windows": windows,
        "versions": versions,
        "days": [item.model_dump(mode="json") for item in day_facts],
        "entries": [
            {
                "source_ref": str(fact.entry.id),
                "diary_date": fact.entry.entry_date.isoformat(),
                "snapshot_schema_version": fact.entry.snapshot_schema_version,
                "snapshot_hash": _hash(fact.entry.nutrition_snapshot),
                "quantity": str(fact.entry.quantity),
            }
            for fact in sorted(facts, key=lambda item: (item.entry.entry_date, str(item.entry.id)))
        ],
        "targets": [item.model_dump(mode="json") for item in _target_refs(targets)],
    }
    return source, current_days, previous_days, entry_map, targets


def _build_document(
    principal: PrincipalContext,
    series: NutritionAnalysis,
    revision_number: int,
    generated_at: datetime,
    source: dict[str, Any],
    current_days: list[AnalysisDayFactV1],
    previous_days: list[AnalysisDayFactV1],
    entry_map: dict[date, list[_EntryFact]],
    targets: dict[date, Any],
    *,
    require_selector_evidence: bool = True,
) -> dict[str, Any]:
    complete_current = sum(day.logging_status == "complete" for day in current_days)
    if require_selector_evidence and complete_current < 4:
        raise PatternAnalysisError(
            "INSUFFICIENT_ANALYSIS_EVIDENCE", 422, "التحليل غير متاح لعدم كفاية الأيام المكتملة"
        )
    safety: set[str] = set()
    target_safety = {
        source.targets.safety_outcome
        for source in targets.values()
        if source.targets is not None and source.targets.safety_outcome != "normal"
    }
    if "very_low_energy_blocked" in target_safety:
        safety.add("very_low_energy_blocked")
    if "specialist_review_required" in target_safety:
        safety.add("profile_specialist_review_required")
    metric_facts: list[AnalysisMetricFactV1] = []
    for key, (unit, direction) in sorted(METRIC_REGISTRY.items()):
        numeric_dates = [
            day.date
            for day in current_days + previous_days
            if day.logging_status == "complete"
            and _day_metric_value(entry_map[day.date], key)[0] is not None
        ]
        static_target = _static_target(key)
        if static_target is not None:
            resolution = _TargetResolution(static_target, "compatible")
        elif key in DAILY_METRICS and direction != "monitor_only":
            resolution = _plan_target(key, targets, numeric_dates)
        else:
            resolution = _TargetResolution(None, "not_applicable")
        target = resolution.target
        if resolution.state == "missing" and numeric_dates:
            safety.add("missing_target")
        elif resolution.state == "incompatible":
            safety.add("incompatible_target")
        current = _period_evidence(
            current_days, key, target, entry_map, target_state=resolution.state
        )
        previous = _period_evidence(
            previous_days, key, target, entry_map, target_state=resolution.state
        )
        kind, aggregation = _metric_kind(key)
        metric_facts.append(
            AnalysisMetricFactV1(
                metric_key=key,
                metric_kind=kind,
                unit=unit,
                aggregation=aggregation,
                direction=direction,
                target=target,
                current=current,
                previous=previous,
                comparison=_comparison(
                    current, previous, target, direction, key, target_state=resolution.state
                ),
                persistence=_persistence(
                    current, previous, target, direction, target_state=resolution.state
                ),
                contributors=AnalysisContributorsV1(
                    current=_contributors(current_days, key, entry_map, unit),
                    previous=_contributors(previous_days, key, entry_map, unit),
                ),
            )
        )
    versions = source["versions"]
    registry_version = (
        versions["nutrition_registry_versions"] or [VERSIONS.nutrition_registry_version]
    )[0]
    group_version = (versions["food_group_rules_versions"] or [VERSIONS.food_group_rules_version])[
        0
    ]
    nova_version = (versions["nova_rules_versions"] or [VERSIONS.nova_rules_version])[0]
    snapshot_versions = versions["snapshot_schema_versions"]
    priority = WeeklyPriorityAnalysisInputV1(
        principal_ref=principal.principal_id,
        source_analysis_id=series.id,
        source_analysis_revision=revision_number,
        generated_at=generated_at,
        as_of_diary_date=series.as_of_diary_date,
        calendar_timezone="Asia/Riyadh",
        period_start=current_days[0].date,
        period_end=current_days[-1].date,
        previous_period_start=previous_days[0].date,
        previous_period_end=previous_days[-1].date,
        analysis_rules_version=ANALYSIS_RULES_VERSION,
        nutrition_registry_version=registry_version,
        food_group_rules_version=group_version,
        nova_rules_version=nova_version,
        snapshot_schema_versions=snapshot_versions,
        target_plan_refs=_target_refs(targets),
        days=current_days,
        previous_period=previous_days,
        metric_facts=metric_facts,
        safety_flags=sorted(safety),
    )
    return priority.model_dump(mode="json")


def _persist_analysis_revision(
    session: Session,
    principal: PrincipalContext,
    series: NutritionAnalysis,
    source: dict[str, Any],
    current_days: list[AnalysisDayFactV1],
    previous_days: list[AnalysisDayFactV1],
    entry_map: dict[date, list[_EntryFact]],
    targets: dict[date, Any],
    *,
    require_selector_evidence: bool,
) -> tuple[NutritionAnalysisRevision, bool]:
    """Persist one producer revision without committing the caller transaction."""
    source_hash = _hash(source)
    current_revision = (
        session.get(NutritionAnalysisRevision, series.current_revision_id)
        if series.current_revision_id
        else None
    )
    if (
        current_revision
        and current_revision.source_input_hash == source_hash
        and current_revision.analysis_rules_version == ANALYSIS_RULES_VERSION
    ):
        return current_revision, False

    revision_number = (series.current_revision_number or 0) + 1
    generated = utcnow()
    document = _build_document(
        principal,
        series,
        revision_number,
        generated,
        source,
        current_days,
        previous_days,
        entry_map,
        targets,
        require_selector_evidence=require_selector_evidence,
    )
    complete_current = sum(day.logging_status == "complete" for day in current_days)
    revision = NutritionAnalysisRevision(
        analysis_id=series.id,
        principal_id=principal.principal_id,
        revision=revision_number,
        period_start=current_days[0].date,
        period_end=current_days[-1].date,
        previous_period_start=previous_days[0].date,
        previous_period_end=previous_days[-1].date,
        analysis_rules_version=ANALYSIS_RULES_VERSION,
        source_versions=source["versions"],
        source_input_hash=source_hash,
        content_hash=_content_hash(document),
        complete_day_count=complete_current,
        previous_complete_day_count=sum(
            day.logging_status == "complete" for day in previous_days
        ),
        result_status="available" if complete_current >= 4 else "insufficient",
        result_reason=None if complete_current >= 4 else "insufficient_complete_days",
        analysis_document=document,
        supersedes_revision_id=current_revision.id if current_revision else None,
        generated_at=generated,
        finalized_at=generated,
    )
    session.add(revision)
    session.flush()
    for period_name, period_days in (("current", current_days), ("previous", previous_days)):
        for day in period_days:
            if day.logging_status != "complete":
                continue
            for fact in entry_map[day.date]:
                for metric_key, (unit, _) in sorted(METRIC_REGISTRY.items()):
                    value = _entry_metric_value(fact, metric_key)
                    session.add(
                        NutritionAnalysisEvidenceRef(
                            revision_id=revision.id,
                            principal_id=principal.principal_id,
                            period=period_name,
                            diary_date=day.date,
                            day_version=day.logging_status_version,
                            source_ref=fact.entry.id,
                            snapshot_schema_version=fact.entry.snapshot_schema_version,
                            metric_key=metric_key,
                            source_version=fact.source_version,
                            value=value,
                            value_state=(
                                "unknown"
                                if value is None
                                else "explicit_zero"
                                if value == 0
                                else "known"
                            ),
                            unit=unit,
                        )
                    )
    if current_revision:
        session.add(
            NutritionAnalysisRevisionEvent(
                revision_id=current_revision.id,
                principal_id=principal.principal_id,
                event_type="superseded_by_revision",
                successor_revision_id=revision.id,
                reason="source_input_changed",
                occurred_at=generated,
            )
        )
    revision.finalized_at = utcnow()
    series.current_revision_id = revision.id
    series.current_revision_number = revision_number
    series.updated_at = generated
    session.add(revision)
    session.add(series)
    session.flush()
    return revision, True


def refresh_historical_analysis(
    session: Session,
    principal: PrincipalContext,
    analysis_id: UUID,
    invalidation_event_id: UUID,
) -> tuple[NutritionAnalysisRevision, bool]:
    """Refresh an existing historical series from producer-owned raw sources.

    The caller owns the surrounding transaction and Principal lock. The series
    date, rather than today's Diary date, is the immutable window authority.
    """
    event = session.exec(
        select(NutritionAnalysisRevisionEvent)
        .join(
            NutritionAnalysisRevision,
            NutritionAnalysisRevision.id == NutritionAnalysisRevisionEvent.revision_id,
        )
        .where(
            NutritionAnalysisRevisionEvent.id == invalidation_event_id,
            NutritionAnalysisRevisionEvent.principal_id == principal.principal_id,
            NutritionAnalysisRevision.analysis_id == analysis_id,
            NutritionAnalysisRevisionEvent.event_type.in_(_STALE_EVENTS),
        )
        .with_for_update()
    ).first()
    if event is None:
        raise PatternAnalysisError(
            "ANALYSIS_SOURCE_CHANGED", 409, "تغيّرت بيانات المصدر. حاول مرة أخرى."
        )
    series = session.exec(
        select(NutritionAnalysis)
        .where(
            NutritionAnalysis.id == analysis_id,
            NutritionAnalysis.principal_id == principal.principal_id,
            NutritionAnalysis.interface_version == 1,
        )
        .with_for_update()
    ).first()
    if series is None:
        raise PatternAnalysisError(
            "ANALYSIS_SOURCE_CHANGED", 409, "تغيّرت بيانات المصدر. حاول مرة أخرى."
        )
    source, current_days, previous_days, entry_map, targets = _build_source(
        session, principal, series.as_of_diary_date
    )
    return _persist_analysis_revision(
        session,
        principal,
        series,
        source,
        current_days,
        previous_days,
        entry_map,
        targets,
        require_selector_evidence=False,
    )


def _events(
    session: Session, revision_id: UUID, principal_id: UUID
) -> list[NutritionAnalysisRevisionEvent]:
    return list(
        session.exec(
            select(NutritionAnalysisRevisionEvent)
            .where(
                NutritionAnalysisRevisionEvent.revision_id == revision_id,
                NutritionAnalysisRevisionEvent.principal_id == principal_id,
            )
            .order_by(NutritionAnalysisRevisionEvent.occurred_at, NutritionAnalysisRevisionEvent.id)
        ).all()
    )


def _lifecycle(events: list[NutritionAnalysisRevisionEvent]) -> tuple[str, list[str]]:
    stale_reasons = sorted(
        {event.event_type for event in events if event.event_type in _STALE_EVENTS}
    )
    status = (
        "superseded"
        if any(event.event_type == "superseded_by_revision" for event in events)
        else "stale"
        if stale_reasons
        else "current"
    )
    return status, stale_reasons


def _response(
    session: Session, series: NutritionAnalysis, revision: NutritionAnalysisRevision
) -> NutritionPatternAnalysisResponseV1:
    events = _events(session, revision.id, revision.principal_id)
    lifecycle, stale_reasons = _lifecycle(events)
    priority = WeeklyPriorityAnalysisInputV1.model_validate(revision.analysis_document)
    versions = revision.source_versions
    source_versions = AnalysisSourceVersionBundleV1(
        analysis_rules_version=revision.analysis_rules_version,
        nutrition_registry_version=priority.nutrition_registry_version,
        calculation_engine_version=versions["calculation_engine_version"],
        food_group_rules_version=priority.food_group_rules_version,
        source_reliability_rules_version=versions["source_reliability_rules_version"],
        nova_rules_version=priority.nova_rules_version,
        snapshot_schema_versions=priority.snapshot_schema_versions,
        status_evidence_version=versions["status_evidence_version"],
        rules_manifest_hash=versions["rules_manifest_hash"],
        source_input_hash=revision.source_input_hash,
        content_hash=revision.content_hash,
    )
    return NutritionPatternAnalysisResponseV1(
        source_analysis_id=series.id,
        source_analysis_revision=revision.revision,
        lifecycle_status=lifecycle,
        stale_reasons=stale_reasons,
        as_of_diary_date=series.as_of_diary_date,
        period_start=revision.period_start,
        period_end=revision.period_end,
        previous_period_start=revision.previous_period_start,
        previous_period_end=revision.previous_period_end,
        complete_day_count=revision.complete_day_count,
        previous_complete_day_count=revision.previous_complete_day_count,
        metric_summaries=priority.metric_facts,
        source_versions=source_versions,
        priority_input=priority,
        generated_at=revision.generated_at,
        finalized_at=revision.finalized_at,
        etag=_etag(series.id, revision.revision),
    )


def _series_current(
    session: Session, principal_id: UUID, *, lock: bool = False
) -> tuple[NutritionAnalysis, NutritionAnalysisRevision] | None:
    statement = (
        select(NutritionAnalysis)
        .where(
            NutritionAnalysis.principal_id == principal_id,
            NutritionAnalysis.current_revision_id.is_not(None),
        )
        .order_by(NutritionAnalysis.as_of_diary_date.desc(), NutritionAnalysis.id.desc())
    )
    if lock:
        statement = statement.with_for_update()
    series = session.exec(statement).first()
    if series is None or series.current_revision_id is None:
        return None
    revision = session.get(NutritionAnalysisRevision, series.current_revision_id)
    return (series, revision) if revision else None


def current_analysis(
    session: Session, principal: PrincipalContext
) -> NutritionPatternAnalysisResponseV1:
    current = _series_current(session, principal.principal_id)
    if current is None:
        raise PatternAnalysisError("ANALYSIS_NOT_FOUND", 404, "لا يوجد تحليل محفوظ بعد.")
    return _response(session, *current)


def exact_revision(
    session: Session, principal: PrincipalContext, analysis_id: UUID, revision_number: int
) -> NutritionPatternAnalysisResponseV1:
    series = session.exec(
        select(NutritionAnalysis).where(
            NutritionAnalysis.id == analysis_id,
            NutritionAnalysis.principal_id == principal.principal_id,
        )
    ).first()
    revision = session.exec(
        select(NutritionAnalysisRevision).where(
            NutritionAnalysisRevision.analysis_id == analysis_id,
            NutritionAnalysisRevision.principal_id == principal.principal_id,
            NutritionAnalysisRevision.revision == revision_number,
        )
    ).first()
    if series is None or revision is None:
        raise PatternAnalysisError("RESOURCE_NOT_FOUND", 404, "تعذر العثور على المورد.")
    if _content_hash(revision.analysis_document) != revision.content_hash:
        raise PatternAnalysisError(
            "UNSUPPORTED_HISTORICAL_VERSION", 422, "تعذر فتح هذه النسخة بإصدارها الأصلي"
        )
    return _response(session, series, revision)


def analysis_history(
    session: Session, principal: PrincipalContext, limit: int, cursor: str | None
) -> NutritionPatternAnalysisHistoryPageV1:
    statement = select(NutritionAnalysisRevision).where(
        NutritionAnalysisRevision.principal_id == principal.principal_id
    )
    if cursor:
        period_end, analysis_id, revision = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                NutritionAnalysisRevision.period_end < period_end,
                and_(
                    NutritionAnalysisRevision.period_end == period_end,
                    NutritionAnalysisRevision.analysis_id < analysis_id,
                ),
                and_(
                    NutritionAnalysisRevision.period_end == period_end,
                    NutritionAnalysisRevision.analysis_id == analysis_id,
                    NutritionAnalysisRevision.revision < revision,
                ),
            )
        )
    rows = list(
        session.exec(
            statement.order_by(
                NutritionAnalysisRevision.period_end.desc(),
                NutritionAnalysisRevision.analysis_id.desc(),
                NutritionAnalysisRevision.revision.desc(),
            ).limit(limit + 1)
        ).all()
    )
    page_rows = rows[:limit]
    analysis_ids = {row.analysis_id for row in page_rows}
    revision_ids = {row.id for row in page_rows}
    series_by_id = (
        {
            series.id: series
            for series in session.exec(
                select(NutritionAnalysis).where(NutritionAnalysis.id.in_(analysis_ids))
            ).all()
        }
        if analysis_ids
        else {}
    )
    events_by_revision: dict[UUID, list[NutritionAnalysisRevisionEvent]] = {
        revision_id: [] for revision_id in revision_ids
    }
    if revision_ids:
        for event in session.exec(
            select(NutritionAnalysisRevisionEvent)
            .where(
                NutritionAnalysisRevisionEvent.principal_id == principal.principal_id,
                NutritionAnalysisRevisionEvent.revision_id.in_(revision_ids),
            )
            .order_by(
                NutritionAnalysisRevisionEvent.revision_id,
                NutritionAnalysisRevisionEvent.occurred_at,
                NutritionAnalysisRevisionEvent.id,
            )
        ).all():
            events_by_revision[event.revision_id].append(event)
    items = []
    for row in page_rows:
        series = series_by_id[row.analysis_id]
        lifecycle, _ = _lifecycle(events_by_revision[row.id])
        items.append(
            NutritionPatternAnalysisHistoryItemV1(
                source_analysis_id=row.analysis_id,
                source_analysis_revision=row.revision,
                lifecycle_status=lifecycle,
                as_of_diary_date=series.as_of_diary_date,
                period_start=row.period_start,
                period_end=row.period_end,
                previous_period_start=row.previous_period_start,
                previous_period_end=row.previous_period_end,
                analysis_rules_version=row.analysis_rules_version,
                complete_day_count=row.complete_day_count,
                previous_complete_day_count=row.previous_complete_day_count,
                generated_at=row.generated_at,
                finalized_at=row.finalized_at,
                etag=_etag(row.analysis_id, row.revision),
            )
        )
    return NutritionPatternAnalysisHistoryPageV1(
        items=items, next_cursor=_encode_cursor(rows[limit - 1]) if len(rows) > limit else None
    )


def evaluate_analysis(
    session: Session,
    principal: PrincipalContext,
    command: AnalysisEvaluateCommandV1,
    idempotency_key: str,
    if_match: str,
) -> tuple[NutritionPatternAnalysisResponseV1, int, bool]:
    if not _KEY_RE.fullmatch(idempotency_key):
        raise PatternAnalysisError(
            "INVALID_IDEMPOTENCY_KEY", 400, "تعذر التحقق من الطلب. أعد المحاولة."
        )
    digest = _key_digest(principal.principal_id, idempotency_key)
    command_hash = _command_hash(principal.principal_id, command)
    replay = session.exec(
        select(NutritionAnalysisCommandIdempotency).where(
            NutritionAnalysisCommandIdempotency.principal_id == principal.principal_id,
            NutritionAnalysisCommandIdempotency.operation == "nutrition_analysis.evaluate",
            NutritionAnalysisCommandIdempotency.key_digest == digest,
        )
    ).first()
    if replay and _unexpired(replay.expires_at):
        if replay.command_hash != command_hash:
            raise PatternAnalysisError(
                "IDEMPOTENCY_KEY_REUSED", 409, "تعارض الطلب مع محاولة سابقة."
            )
        return (
            NutritionPatternAnalysisResponseV1.model_validate(replay.response_document),
            replay.response_status,
            True,
        )
    authority = diary_calendar_authority()
    as_of = authority.current_diary_date
    try:
        session.exec(
            select(Principal).where(Principal.id == principal.principal_id).with_for_update()
        ).one()
        replay = session.exec(
            select(NutritionAnalysisCommandIdempotency).where(
                NutritionAnalysisCommandIdempotency.principal_id == principal.principal_id,
                NutritionAnalysisCommandIdempotency.operation == "nutrition_analysis.evaluate",
                NutritionAnalysisCommandIdempotency.key_digest == digest,
            )
        ).first()
        if replay and _unexpired(replay.expires_at):
            if replay.command_hash != command_hash:
                raise PatternAnalysisError(
                    "IDEMPOTENCY_KEY_REUSED", 409, "تعارض الطلب مع محاولة سابقة."
                )
            response = NutritionPatternAnalysisResponseV1.model_validate(replay.response_document)
            session.rollback()
            return response, replay.response_status, True
        if replay:
            session.delete(replay)
            session.flush()
        series = session.exec(
            select(NutritionAnalysis)
            .where(
                NutritionAnalysis.principal_id == principal.principal_id,
                NutritionAnalysis.as_of_diary_date == as_of,
                NutritionAnalysis.interface_version == 1,
            )
            .with_for_update()
        ).first()
        if series is None:
            series = NutritionAnalysis(
                principal_id=principal.principal_id,
                as_of_diary_date=as_of,
                calendar_timezone="Asia/Riyadh",
                interface_version=1,
            )
            session.add(series)
            session.flush()
        if command.expected_current_revision is None:
            if if_match != '"analysis-none"':
                raise PatternAnalysisError(
                    "INVALID_ANALYSIS_PRECONDITION", 400, "تعذر التحقق من نسخة التحليل."
                )
        else:
            match = _ETAG_RE.fullmatch(if_match)
            if match is None or int(match.group("revision")) != command.expected_current_revision:
                raise PatternAnalysisError(
                    "INVALID_ANALYSIS_PRECONDITION", 400, "تعذر التحقق من نسخة التحليل."
                )
            if UUID(match.group("analysis_id")) != series.id:
                raise PatternAnalysisError(
                    "ANALYSIS_VERSION_CONFLICT",
                    409,
                    "تغيّرت نسخة التحليل. حدّث الصفحة ثم حاول مجددًا.",
                )
        if series.current_revision_number != command.expected_current_revision:
            raise PatternAnalysisError(
                "ANALYSIS_VERSION_CONFLICT", 409, "تغيّرت نسخة التحليل. حدّث الصفحة ثم حاول مجددًا."
            )
        source, current_days, previous_days, entry_map, targets = _build_source(
            session, principal, as_of
        )
        revision, created = _persist_analysis_revision(
            session,
            principal,
            series,
            source,
            current_days,
            previous_days,
            entry_map,
            targets,
            require_selector_evidence=True,
        )
        response = _response(session, series, revision)
        status_code = 201 if created else 200
        now = utcnow()
        session.add(
            NutritionAnalysisCommandIdempotency(
                principal_id=principal.principal_id,
                operation="nutrition_analysis.evaluate",
                key_digest=digest,
                command_hash=command_hash,
                captured_date=as_of,
                analysis_id=response.source_analysis_id,
                revision_id=series.current_revision_id,
                response_status=status_code,
                response_headers={"ETag": response.etag},
                response_document=response.model_dump(mode="json"),
                completed_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        session.commit()
        return response, status_code, False
    except PatternAnalysisError:
        session.rollback()
        raise
    except IntegrityError as error:
        session.rollback()
        raise PatternAnalysisError(
            "ANALYSIS_SOURCE_CHANGED", 409, "تغيّرت بيانات المصدر. حاول مرة أخرى."
        ) from error
    except DBAPIError as error:
        session.rollback()
        if getattr(error.orig, "sqlstate", None) in {"40001", "40P01"}:
            raise PatternAnalysisError(
                "ANALYSIS_RETRY_REQUIRED", 409, "تعذر تحديث التحليل. حاول مرة أخرى"
            ) from error
        raise


def append_stale_events_for_date(
    session: Session,
    principal_id: UUID,
    diary_date: date,
    event_type: str,
    reason: str,
    source_day_version: int | None = None,
) -> int:
    if event_type not in _STALE_EVENTS:
        raise ValueError("unsupported stale event")
    revisions = session.exec(
        select(NutritionAnalysisRevision)
        .join(NutritionAnalysis, NutritionAnalysis.id == NutritionAnalysisRevision.analysis_id)
        .where(
            NutritionAnalysisRevision.principal_id == principal_id,
            NutritionAnalysis.current_revision_id == NutritionAnalysisRevision.id,
            NutritionAnalysisRevision.previous_period_start <= diary_date,
            NutritionAnalysisRevision.period_end >= diary_date,
        )
        .order_by(NutritionAnalysisRevision.analysis_id)
        .with_for_update()
    ).all()
    inserted = 0
    for revision in revisions:
        existing = session.exec(
            select(NutritionAnalysisRevisionEvent).where(
                NutritionAnalysisRevisionEvent.revision_id == revision.id,
                NutritionAnalysisRevisionEvent.event_type == event_type,
                NutritionAnalysisRevisionEvent.reason == reason,
                NutritionAnalysisRevisionEvent.source_day_version == source_day_version,
            )
        ).first()
        if existing is None:
            session.add(
                NutritionAnalysisRevisionEvent(
                    revision_id=revision.id,
                    principal_id=principal_id,
                    event_type=event_type,
                    reason=reason,
                    source_day_version=source_day_version,
                )
            )
            inserted += 1
    return inserted


def admin_monitoring(session: Session, iso_week: str) -> NutritionAnalysisMonitoringResponseV1:
    try:
        year, week = (int(value) for value in iso_week.split("-W", 1))
        start = date.fromisocalendar(year, week, 1)
    except (ValueError, TypeError) as error:
        raise PatternAnalysisError("INVALID_ISO_WEEK", 422, "الأسبوع المطلوب غير صالح.") from error
    end = start + timedelta(days=7)
    rows = session.exec(
        select(NutritionAnalysisRevision).where(
            NutritionAnalysisRevision.finalized_at
            >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            NutritionAnalysisRevision.finalized_at
            < datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc),
        )
    ).all()
    versions: dict[str, int] = {}
    statuses: dict[str, int] = {}
    complete_bands = {"0-3": 0, "4-5": 0, "6-7": 0}
    coverages: list[float | None] = []
    durations: list[float | None] = []
    for row in rows:
        versions[row.analysis_rules_version] = versions.get(row.analysis_rules_version, 0) + 1
        statuses[row.result_status] = statuses.get(row.result_status, 0) + 1
        complete_bands[
            "0-3" if row.complete_day_count < 4 else "4-5" if row.complete_day_count < 6 else "6-7"
        ] += 1
        metric_facts = row.analysis_document.get("metric_facts", [])
        coverages.extend(item.get("current", {}).get("coverage_percent") for item in metric_facts)
        generated = row.generated_at
        finalized = row.finalized_at
        if generated is None or finalized is None:
            durations.append(None)
        else:
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
            if finalized.tzinfo is None:
                finalized = finalized.replace(tzinfo=timezone.utc)
            durations.append((finalized - generated).total_seconds() * 1000)
    revision_ids = {row.id for row in rows}
    stale_events: list[dict[str, str]] = []
    if revision_ids:
        events = session.exec(
            select(NutritionAnalysisRevisionEvent).where(
                NutritionAnalysisRevisionEvent.revision_id.in_(revision_ids),
                NutritionAnalysisRevisionEvent.event_type.in_(_STALE_EVENTS),
            )
        ).all()
        stale_events = [
            {"revision": str(event.revision_id), "reason": event.event_type} for event in events
        ]
    return NutritionAnalysisMonitoringResponseV1(
        iso_week=iso_week,
        total_count=len(rows),
        status_counts=statuses,
        version_counts=versions,
        complete_day_band_counts=complete_bands,
        coverage_band_counts=coverage_band_counts(coverages),
        stale_reason_counts=stale_reason_counts(stale_events),
        latency_band_counts=latency_band_counts(durations),
    )
