from collections.abc import Callable
from datetime import date, timedelta

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import DiaryEntry
from app.nutrition_rules.registry import NUTRIENTS, NutrientDefinition
from app.schemas import (
    DaySummary,
    DiaryNutrientAggregate,
    DiaryNutrientTarget,
    TargetResponse,
    TargetSourceResponse,
    WeekSummary,
)
from app.services.diary import add_totals, empty_totals, totals_for_entry
from app.services.profile import get_profile, to_target_response
from app.services.target_plans import project_targets, resolve_targets


TargetResolver = Callable[[Session, PrincipalContext, date], TargetSourceResponse]


def sunday_start(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _rounded(value: float) -> float:
    return round(value, 6)


def _target_for(
    definition: NutrientDefinition,
    targets: TargetResponse | None,
    provenance: str,
) -> DiaryNutrientTarget | None:
    if targets is None or provenance == "no_target_source":
        return None
    resolved = next(
        (item for item in targets.additional_targets if item.key == definition.key),
        None,
    )
    if resolved is None:
        return None
    rule = resolved.target_rule
    return DiaryNutrientTarget(
        type=resolved.target_type,
        value=resolved.target_value,
        lower=rule.get("lower") if isinstance(rule, dict) else None,
        upper=rule.get("upper") if isinstance(rule, dict) else None,
        unit=resolved.unit,
        source=provenance,
    )


def _complete_evaluation(
    amount: float, target: DiaryNutrientTarget
) -> tuple[str | None, float | None, float | None, float | None]:
    value = target.value
    if target.type in {"minimum", "recommended", "adequate"} and value is not None:
        return (
            "met" if amount >= value else "below_target",
            _rounded(amount / value * 100) if value > 0 else None,
            _rounded(max(value - amount, 0)),
            None,
        )
    if target.type == "maximum" and value is not None:
        evaluation = "exceeded" if amount > value else "at_limit" if amount == value else "within_limit"
        return (
            evaluation,
            _rounded(amount / value * 100) if value > 0 else None,
            None,
            _rounded(max(value - amount, 0)),
        )
    if target.type == "range" and target.lower is not None and target.upper is not None:
        evaluation = (
            "below_range"
            if amount < target.lower
            else "above_range"
            if amount > target.upper
            else "within_range"
        )
        return evaluation, None, None, None
    return None, None, None, None


def aggregate_nutrient(
    definition: NutrientDefinition,
    values: list[float | None],
    target: DiaryNutrientTarget | None,
) -> DiaryNutrientAggregate:
    total = len(values)
    known_values = [value for value in values if value is not None]
    known = len(known_values)
    if total == 0:
        return DiaryNutrientAggregate(
            key=definition.key,
            amount=None,
            known_entry_count=0,
            total_entry_count=0,
            coverage_percent=None,
            coverage_state="no_entries",
            amount_qualifier="unavailable",
            target=target,
        )
    if known == 0:
        return DiaryNutrientAggregate(
            key=definition.key,
            amount=None,
            known_entry_count=0,
            total_entry_count=total,
            coverage_percent=0,
            coverage_state="all_unknown",
            amount_qualifier="unavailable",
            target=target,
        )

    amount = _rounded(sum(known_values))
    coverage = _rounded(known / total * 100)
    if known < total:
        evaluation = None
        if target is not None:
            if target.type in {"minimum", "recommended", "adequate"} and target.value is not None:
                evaluation = "met_at_least" if amount >= target.value else "indeterminate_partial_coverage"
            elif target.type == "maximum" and target.value is not None:
                evaluation = "exceeded_at_least" if amount > target.value else "indeterminate_partial_coverage"
            elif target.type == "range" and target.upper is not None:
                evaluation = "above_range_at_least" if amount > target.upper else "indeterminate_partial_coverage"
        return DiaryNutrientAggregate(
            key=definition.key,
            amount=amount,
            known_entry_count=known,
            total_entry_count=total,
            coverage_percent=coverage,
            coverage_state="partial",
            amount_qualifier="at_least",
            target=target,
            evaluation=evaluation,
        )

    evaluation = progress = remaining = available = None
    if target is not None:
        evaluation, progress, remaining, available = _complete_evaluation(amount, target)
    return DiaryNutrientAggregate(
        key=definition.key,
        amount=amount,
        known_entry_count=known,
        total_entry_count=total,
        coverage_percent=100,
        coverage_state="complete",
        amount_qualifier="exact",
        target=target,
        evaluation=evaluation,
        progress_percent=progress,
        remaining=remaining,
        available=available,
    )


def _summary_integrity_error(entry: DiaryEntry, error: HTTPException) -> HTTPException:
    cause = error.detail.get("code") if isinstance(error.detail, dict) else "INVALID_DIARY_SNAPSHOT_DATA"
    return HTTPException(
        status_code=409,
        detail={
            "code": "DIARY_SUMMARY_DATA_INTEGRITY_ERROR",
            "message_ar": "تعذر حساب ملخص اليوم بسبب مشكلة في بيانات يومية محفوظة.",
            "entries": [{"entry_id": str(entry.id), "cause": cause}],
        },
    )


def _day_summary(
    session: Session,
    principal: PrincipalContext,
    current: date,
    entries: list[DiaryEntry],
    target_resolver: TargetResolver,
) -> DaySummary:
    totals = empty_totals()
    entry_totals = []
    for entry in entries:
        try:
            resolved = totals_for_entry(entry)
        except HTTPException as error:
            raise _summary_integrity_error(entry, error) from error
        entry_totals.append(resolved)
        totals = add_totals(totals, resolved)

    source = target_resolver(session, principal, current)
    aggregates = []
    for definition in NUTRIENTS:
        if not definition.diary_coverage_participation:
            continue
        values = [getattr(item, definition.storage_field) for item in entry_totals]
        target = _target_for(definition, source.targets, source.target_provenance)
        aggregates.append(aggregate_nutrient(definition, values, target))
    overall = (
        None
        if not entries
        else _rounded(sum(item.coverage_percent or 0 for item in aggregates) / len(aggregates))
    )
    return DaySummary(
        date=current,
        totals=totals,
        targets=source.targets,
        target_provenance=source.target_provenance,
        nutrient_aggregates=aggregates,
        overall_nutrient_coverage_percent=overall,
    )


def _weekly_summary(
    session: Session,
    principal: PrincipalContext,
    start: date,
    target_resolver: TargetResolver,
) -> WeekSummary:
    week_start = sunday_start(start)
    week_end = week_start + timedelta(days=6)
    entries = session.exec(
        select(DiaryEntry).where(
            DiaryEntry.principal_id == principal.principal_id,
            DiaryEntry.entry_date >= week_start,
            DiaryEntry.entry_date <= week_end,
        )
    ).all()

    targets = None
    profile = get_profile(session, principal)
    if profile is not None:
        targets = to_target_response(profile)

    days: list[DaySummary] = []
    weekly_totals = empty_totals()
    for offset in range(7):
        current = week_start + timedelta(days=offset)
        day = _day_summary(
            session,
            principal,
            current,
            [entry for entry in entries if entry.entry_date == current],
            target_resolver,
        )
        weekly_totals = add_totals(weekly_totals, day.totals)
        days.append(day)

    return WeekSummary(start=week_start, end=week_end, days=days, weekly_totals=weekly_totals, targets=targets)


def weekly_summary(session: Session, principal: PrincipalContext, start: date) -> WeekSummary:
    return _weekly_summary(session, principal, start, resolve_targets)


def weekly_summary_read_only(
    session: Session, principal: PrincipalContext, start: date
) -> WeekSummary:
    return _weekly_summary(session, principal, start, project_targets)
