from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.core.config import get_settings
from app.models import (
    BehaviorGoal,
    BehaviorGoalCommandIdempotency,
    BehaviorGoalHistory,
    BehaviorGoalReminderDelivery,
    NutritionAnalysisRevision,
    Principal,
    WeeklyPriorityEvidenceRef,
    WeeklyPriorityRecommendation,
    utcnow,
)
from app.nutrition_rules.weekly_priority import (
    COPY_CATALOG,
    METRIC_RULES,
    RULE_META,
    WEEKLY_PRIORITY_COPY_VERSION,
    WEEKLY_PRIORITY_RULES_VERSION,
    select as select_priority,
    validate_producer,
)
from app.schemas import (
    BehaviorGoalCommandResponseV1,
    BehaviorGoalCommandV1,
    BehaviorGoalCurrentResponseV1,
    BehaviorGoalHistoryPageV1,
    BehaviorGoalProgressV1,
    BehaviorGoalResponseV1,
    PriorityV1,
    WeeklyPriorityAnalysisInputV1,
    WeeklyPriorityExcludedV1,
    WeeklyPriorityFactV1,
    WeeklyPriorityResultV1,
)
from app.services.pattern_analysis import current_analysis

_KEY_RE = re.compile(r"^[\x21-\x7e]{1,128}$")
_PRIMARY_STATES = {"active", "paused"}
_ALLOWED_ACTIONS: dict[str, list[str]] = {
    "offered": ["accept", "edit", "defer", "reject"],
    "deferred": ["accept", "reject"],
    "active": ["edit", "change", "pause", "end"],
    "paused": ["resume", "end"],
    "incomplete": ["repeat", "reduce", "change", "end"],
    "rejected": [],
    "completed": [],
    "ended": [],
    "archived": [],
}


class WeeklyPriorityError(RuntimeError):
    def __init__(self, code: str, status_code: int, message_ar: str) -> None:
        super().__init__(code)
        self.code, self.status_code, self.message_ar = code, status_code, message_ar


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key_digest(principal_id: UUID, key: str) -> str:
    secret = get_settings().weekly_priority_idempotency_hmac_secret.encode()
    scoped_key = principal_id.bytes + b"\x00" + key.encode()
    return hmac.new(secret, scoped_key, hashlib.sha256).hexdigest()


def _etag(goal_id: UUID, version: int) -> str:
    del goal_id
    return f'"goal-{version}"'


def _recommendation_etag(recommendation_id: UUID) -> str:
    return f'"weekly-priority-{recommendation_id}"'


def _target_value(metric) -> float | None:
    if metric.target is None:
        return None
    if metric.target.type in {"minimum", "maximum"}:
        return metric.target.value
    if metric.target.type == "range":
        return metric.target.lower
    return None


def _candidate_severity(metric) -> float:
    value, target = metric.current.value, _target_value(metric)
    if value is None:
        return 0.0
    if metric.direction == "minimize":
        return min(1.0, max(0.0, value / max(1, metric.current.complete_day_count)))
    if target is None or target <= 0:
        return 0.0
    if metric.direction == "maximum":
        return max(0.0, (value - target) / target)
    return max(0.0, (target - value) / target)


def _repeat_events(source: WeeklyPriorityAnalysisInputV1, metric) -> int:
    target = _target_value(metric)
    count = 0
    for day in source.days:
        if not day.analysis_eligible:
            continue
        value = next(
            (item.value for item in day.metric_values if item.metric_key == metric.metric_key), None
        )
        if value is None:
            continue
        if metric.direction == "maximum" and target is not None and value > target:
            count += 1
        elif metric.direction == "minimize" and value > 0:
            count += 1
    return count


def _selection_input(
    source: WeeklyPriorityAnalysisInputV1, state: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    calories = next(
        (item for item in source.metric_facts if item.metric_key == "energy:calories_kcal_per_day"),
        None,
    )
    calories_relation = calories.current.status if calories else "unavailable"
    candidates: list[dict[str, Any]] = []
    by_rule: dict[str, Any] = {}
    for metric in source.metric_facts:
        rule_key = METRIC_RULES.get(metric.metric_key)
        if rule_key is None:
            continue
        tier, _, actions = RULE_META[rule_key]
        mode = "review" if tier == 3 else "replace"
        if tier == 2 and calories_relation != "above_target" and "add" in actions:
            mode = "add"
        qualifying = metric.current.status == ("above_target" if tier == 1 else "below_target")
        coverage = metric.current.coverage_percent or 0.0
        candidate = {
            "key": rule_key,
            "actionable": qualifying,
            "coverage": coverage,
            "severity": round(_candidate_severity(metric), 6),
            "repeat_events": _repeat_events(source, metric),
            "persistent_weeks": 2 if metric.persistence.qualifies else 0,
            "action_mode": mode,
            "evidence_dimension": metric.metric_key,
            "conflict_group": {
                "added_sugar_overage": "sugar",
                "sugary_drink_frequency": "sugar",
                "saturated_fat_overage": "fat",
                "dairy_alternative_gap": "fat",
                "fruit_vegetable_gap": "plant",
                "fiber_gap": "plant",
            }.get(rule_key, rule_key),
        }
        candidates.append(candidate)
        by_rule[rule_key] = metric
    return {
        "input_state": state,
        "calories_relation": calories_relation,
        "complete_days": sum(day.analysis_eligible for day in source.days),
        "candidates": candidates,
    }, by_rule


def _rejection_suppressed(
    session: Session,
    principal_id: UUID,
    source: WeeklyPriorityAnalysisInputV1,
    selected_rule: str | None,
    candidate_by_rule: dict[str, dict[str, Any]],
) -> bool:
    if selected_rule is None:
        return False
    rejected_goal = session.exec(
        select(BehaviorGoal)
        .where(
            BehaviorGoal.principal_id == principal_id,
            BehaviorGoal.state == "rejected",
            BehaviorGoal.rule_key == selected_rule,
            BehaviorGoal.rules_version == WEEKLY_PRIORITY_RULES_VERSION,
        )
        .order_by(BehaviorGoal.rejected_at.desc(), BehaviorGoal.id.desc())
        .limit(1)
    ).first()
    if rejected_goal is None or rejected_goal.rejected_at is None:
        return False
    rejected_recommendation = session.exec(
        select(WeeklyPriorityRecommendation).where(
            WeeklyPriorityRecommendation.id == rejected_goal.recommendation_id,
            WeeklyPriorityRecommendation.principal_id == principal_id,
        )
    ).first()
    if rejected_recommendation is None:
        return True
    later_revision = (
        source.source_analysis_id == rejected_recommendation.source_analysis_id
        and source.source_analysis_revision > rejected_recommendation.source_analysis_revision
    ) or source.as_of_diary_date > rejected_recommendation.as_of_diary_date
    if (
        not later_revision
        or not any(
            day.analysis_eligible
            and day.completed_at is not None
            and day.completed_at > rejected_goal.rejected_at
            for day in source.days
        )
    ):
        return True
    prior_revision = session.get(
        NutritionAnalysisRevision, rejected_recommendation.source_analysis_revision_id
    )
    if prior_revision is None:
        return True
    try:
        prior_source = WeeklyPriorityAnalysisInputV1.model_validate(prior_revision.analysis_document)
        prior_vector, _ = _selection_input(prior_source, "eligible")
        prior_candidate = next(
            item for item in prior_vector["candidates"] if item["key"] == selected_rule
        )
    except (ValueError, StopIteration):
        return True
    current = candidate_by_rule[selected_rule]
    return not (
        current["action_mode"] != prior_candidate["action_mode"]
        or current["severity"] >= prior_candidate["severity"] + 0.10
    )


def _priority(rule_key: str, rank: str, candidate: dict[str, Any], metric) -> PriorityV1:
    tier, _, actions = RULE_META[rule_key]
    mode = candidate["action_mode"]
    title, reason, action = COPY_CATALOG[rule_key]
    refs = sorted(
        metric.current.evidence_refs, key=lambda item: (item.diary_date, str(item.source_ref))
    )
    return PriorityV1(
        rule_key=rule_key,
        rank=rank,
        category={1: "limit", 2: "positive", 3: "micronutrient"}[tier],
        title_ar=title,
        reason_ar=reason,
        coverage_percent=metric.current.coverage_percent,
        complete_day_count=metric.current.complete_day_count,
        action_key=actions[mode],
        action_ar=action,
        action_mode=mode,
        rules_version=WEEKLY_PRIORITY_RULES_VERSION,
        copy_version=WEEKLY_PRIORITY_COPY_VERSION,
        facts_used=[
            WeeklyPriorityFactV1(
                metric_key=metric.metric_key,
                value=metric.current.value,
                unit=metric.unit,
                target=metric.target,
                comparison=metric.comparison.status,
                period="current",
            )
        ],
        evidence_refs=refs,
        conflict_decisions=[],
    )


def _project_recommendation(row: WeeklyPriorityRecommendation) -> WeeklyPriorityResultV1:
    document = dict(row.result_document)
    if row.superseded_by_id is not None:
        document.update(
            status="superseded", main=None, secondary=None, none_reason="superseded_analysis"
        )
    document["etag"] = _recommendation_etag(row.id)
    return WeeklyPriorityResultV1.model_validate(document)


def evaluate_recommendation(
    session: Session, principal: PrincipalContext
) -> WeeklyPriorityResultV1:
    session.exec(
        select(Principal).where(Principal.id == principal.principal_id).with_for_update()
    ).one()
    analysis = current_analysis(session, principal)
    source = analysis.priority_input
    existing = session.exec(
        select(WeeklyPriorityRecommendation).where(
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
            WeeklyPriorityRecommendation.source_analysis_id == source.source_analysis_id,
            WeeklyPriorityRecommendation.source_analysis_revision
            == source.source_analysis_revision,
            WeeklyPriorityRecommendation.rules_version == WEEKLY_PRIORITY_RULES_VERSION,
        )
    ).first()
    if existing:
        return _project_recommendation(existing)
    state = validate_producer(
        source,
        stale=(
            analysis.lifecycle_status == "stale"
            or source.generated_at < utcnow() - timedelta(hours=36)
        ),
        superseded=analysis.lifecycle_status == "superseded",
    )
    vector, metric_by_rule = _selection_input(source, state)
    selected = select_priority(vector)
    candidate_by_rule = {item["key"]: item for item in vector["candidates"]}
    if _rejection_suppressed(
        session,
        principal.principal_id,
        source,
        selected["main"],
        candidate_by_rule,
    ):
        selected = {"main": None, "secondary": None, "reason": "rejected_goal_suppression"}
    rec_id, now = uuid4(), utcnow()
    status = (
        "selected"
        if selected["reason"] == "selected"
        else (
            "stale"
            if selected["reason"] == "stale_analysis"
            else "superseded"
            if selected["reason"] == "superseded_analysis"
            else "safety_suppressed"
            if selected["reason"] == "safety_exclusion"
            else "none"
        )
    )
    main = (
        _priority(
            selected["main"],
            "main",
            candidate_by_rule[selected["main"]],
            metric_by_rule[selected["main"]],
        )
        if selected["main"]
        else None
    )
    secondary = (
        _priority(
            selected["secondary"],
            "secondary",
            candidate_by_rule[selected["secondary"]],
            metric_by_rule[selected["secondary"]],
        )
        if selected["secondary"]
        else None
    )
    chosen = {key for key in (selected["main"], selected["secondary"]) if key}
    excluded = [
        WeeklyPriorityExcludedV1(rule_key=item["key"], reason_code="lower_rank")
        for item in sorted(vector["candidates"], key=lambda value: value["key"])
        if item["key"] not in chosen and item.get("actionable")
    ]
    result = WeeklyPriorityResultV1(
        recommendation_id=rec_id,
        source_analysis_id=source.source_analysis_id,
        source_analysis_revision=source.source_analysis_revision,
        period_start=source.period_start,
        period_end=source.period_end,
        generated_at=now,
        expires_at=datetime.combine(
            source.period_end + timedelta(days=2), datetime.min.time(), timezone.utc
        )
        + timedelta(hours=12),
        status=status,
        rules_version=WEEKLY_PRIORITY_RULES_VERSION,
        copy_version=WEEKLY_PRIORITY_COPY_VERSION,
        analysis_rules_version=source.analysis_rules_version,
        nutrition_registry_version=source.nutrition_registry_version,
        food_group_rules_version=source.food_group_rules_version,
        nova_rules_version=source.nova_rules_version,
        snapshot_schema_versions=source.snapshot_schema_versions,
        target_plan_refs=source.target_plan_refs,
        main=main,
        secondary=secondary,
        excluded_alternatives=excluded,
        none_reason=None if status == "selected" else selected["reason"],
        etag=_recommendation_etag(rec_id),
    )
    revision = session.exec(
        select(NutritionAnalysisRevision).where(
            NutritionAnalysisRevision.analysis_id == source.source_analysis_id,
            NutritionAnalysisRevision.revision == source.source_analysis_revision,
            NutritionAnalysisRevision.principal_id == principal.principal_id,
        )
    ).one()
    previous = session.exec(
        select(WeeklyPriorityRecommendation)
        .where(
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
            WeeklyPriorityRecommendation.superseded_by_id.is_(None),
        )
        .order_by(WeeklyPriorityRecommendation.created_at.desc())
        .with_for_update()
    ).first()
    persisted_status = "none" if previous is not None and status == "selected" else status
    row = WeeklyPriorityRecommendation(
        id=rec_id,
        principal_id=principal.principal_id,
        source_analysis_revision_id=revision.id,
        source_analysis_id=source.source_analysis_id,
        source_analysis_revision=source.source_analysis_revision,
        period_start=source.period_start,
        period_end=source.period_end,
        as_of_diary_date=source.as_of_diary_date,
        status=persisted_status,
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
        input_digest=_hash(source.model_dump(mode="json")),
        content_hash=_hash(result.model_dump(mode="json")),
        generated_at=now,
        expires_at=result.expires_at,
    )
    session.add(row)
    session.flush()
    if previous and previous.id != row.id:
        previous.superseded_by_id = row.id
        previous.superseded_at = now
        session.add(previous)
        session.flush()
        row.status = status
        session.add(row)
        session.flush()
    for priority in (main, secondary):
        if priority:
            for ref in priority.evidence_refs:
                fact = priority.facts_used[0]
                session.add(
                    WeeklyPriorityEvidenceRef(
                        recommendation_id=rec_id,
                        principal_id=principal.principal_id,
                        metric_key=fact.metric_key,
                        evidence_kind="analysis_fact",
                        opaque_source_id=ref.source_ref,
                        source_version=ref.source_version,
                        diary_date=ref.diary_date,
                        value=fact.value,
                        unit=fact.unit,
                        coverage_percent=priority.coverage_percent,
                    )
                )
    session.commit()
    session.refresh(row)
    return _project_recommendation(row)


def current_recommendation(session: Session, principal: PrincipalContext) -> WeeklyPriorityResultV1:
    if not get_settings().weekly_priorities_display_enabled:
        raise WeeklyPriorityError(
            "PRIORITY_EVIDENCE_UNAVAILABLE",
            503,
            "لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.",
        )
    row = session.exec(
        select(WeeklyPriorityRecommendation)
        .where(
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
            WeeklyPriorityRecommendation.superseded_by_id.is_(None),
        )
        .order_by(
            WeeklyPriorityRecommendation.period_end.desc(),
            WeeklyPriorityRecommendation.created_at.desc(),
            WeeklyPriorityRecommendation.id.desc(),
        )
    ).first()
    if row is None:
        raise WeeklyPriorityError(
            "PRIORITY_EVIDENCE_UNAVAILABLE",
            503,
            "لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.",
        )
    return _project_recommendation(row)


def _empty_progress(goal: BehaviorGoal, as_of: date, now: datetime) -> BehaviorGoalProgressV1:
    return BehaviorGoalProgressV1(
        window_start=goal.window_start,
        window_end=goal.window_end,
        progress_count=0,
        target_count=goal.weekly_target_count,
        progress_percent=0,
        complete_day_count=0,
        partial_day_count=0,
        unregistered_day_count=7,
        status="unknown",
        as_of_diary_date=as_of,
        source_day_versions={},
        calculation_rules_version=goal.rules_version,
        last_recomputed_at=now,
    )


def _goal_response(goal: BehaviorGoal) -> BehaviorGoalResponseV1:
    authority = diary_calendar_authority()
    return BehaviorGoalResponseV1(
        goal_id=goal.id,
        root_goal_id=goal.root_goal_id,
        previous_goal_id=goal.previous_goal_id,
        sequence_number=goal.sequence_number,
        state=goal.state,
        version=goal.version,
        rule_key=goal.rule_key,
        action_key=goal.action_key,
        weekly_target_count=goal.weekly_target_count,
        scheduled_day_mask=goal.day_mask,
        owner_note=goal.private_note,
        window_start=goal.window_start,
        window_end=goal.window_end,
        source_recommendation_id=goal.recommendation_id,
        source_rules_version=goal.rules_version,
        source_copy_version=goal.copy_version,
        progress=BehaviorGoalProgressV1.model_validate(goal.progress_document),
        allowed_actions=_ALLOWED_ACTIONS[goal.state],
        reminder_preference=goal.reminder_preference,
        offered_at=goal.created_at,
        accepted_at=goal.accepted_at,
        deferred_at=goal.deferred_at,
        deferred_until=goal.deferred_until,
        changed_at=goal.changed_at,
        paused_at=goal.paused_at,
        resumed_at=goal.resumed_at,
        completed_at=goal.completed_at,
        reviewed_at=goal.reviewed_at,
        rejected_at=goal.rejected_at,
        ended_at=goal.ended_at,
        archived_at=goal.archived_at,
        calendar={
            "current_diary_date": authority.current_diary_date,
            "calendar_timezone": authority.calendar_timezone,
            "next_rollover_at": authority.next_rollover_at,
        },
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        etag=_etag(goal.id, goal.version),
    )


def ensure_offer(
    session: Session, principal: PrincipalContext, recommendation: WeeklyPriorityResultV1
) -> BehaviorGoal | None:
    if (
        not get_settings().behavior_goal_offers_enabled
        or recommendation.status != "selected"
        or recommendation.main is None
    ):
        return None
    existing = session.exec(
        select(BehaviorGoal).where(
            BehaviorGoal.principal_id == principal.principal_id,
            BehaviorGoal.recommendation_id == recommendation.recommendation_id,
            BehaviorGoal.sequence_number == 1,
        )
    ).first()
    if existing:
        return existing
    authority, now, goal_id = diary_calendar_authority(), utcnow(), uuid4()
    goal = BehaviorGoal(
        id=goal_id,
        principal_id=principal.principal_id,
        recommendation_id=recommendation.recommendation_id,
        root_goal_id=goal_id,
        sequence_number=1,
        state="offered",
        version=1,
        rule_key=recommendation.main.rule_key,
        action_key=recommendation.main.action_key,
        weekly_target_count=3,
        day_mask=[],
        window_start=authority.current_diary_date,
        window_end=authority.current_diary_date + timedelta(days=6),
        rules_version=recommendation.rules_version,
        copy_version=recommendation.copy_version,
        progress_document={},
        progress_revision=1,
        reminder_preference="disabled",
    )
    goal.progress_document = _empty_progress(goal, authority.current_diary_date, now).model_dump(
        mode="json"
    )
    session.add(goal)
    session.add(
        BehaviorGoalHistory(
            goal_id=goal.id,
            principal_id=principal.principal_id,
            root_goal_id=goal.id,
            sequence_number=1,
            goal_version=1,
            event_type="offered",
            from_state=None,
            to_state="offered",
            actor_type="system",
            terms_progress_snapshot=goal.progress_document,
        )
    )
    session.commit()
    session.refresh(goal)
    return goal


def current_goal(session: Session, principal: PrincipalContext) -> BehaviorGoalCurrentResponseV1:
    recommendation = None
    try:
        recommendation = current_recommendation(session, principal)
    except WeeklyPriorityError:
        pass
    goal = session.exec(
        select(BehaviorGoal)
        .where(
            BehaviorGoal.principal_id == principal.principal_id,
            BehaviorGoal.state.in_(["offered", "deferred", "active", "paused", "incomplete"]),
        )
        .order_by(BehaviorGoal.updated_at.desc(), BehaviorGoal.id.desc())
    ).first()
    return BehaviorGoalCurrentResponseV1(
        recommendation=recommendation, goal=_goal_response(goal) if goal else None
    )


def _encode_cursor(goal: BehaviorGoal) -> str:
    return (
        urlsafe_b64encode(_canonical({"date": goal.window_end.isoformat(), "id": str(goal.id)}))
        .decode()
        .rstrip("=")
    )


def _decode_cursor(cursor: str) -> tuple[date, UUID]:
    try:
        value = json.loads(urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return date.fromisoformat(value["date"]), UUID(value["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise WeeklyPriorityError("VALIDATION_ERROR", 422, "تحقق من بيانات الطلب.") from error


def goal_history(
    session: Session, principal: PrincipalContext, limit: int, cursor: str | None
) -> BehaviorGoalHistoryPageV1:
    statement = select(BehaviorGoal).where(
        BehaviorGoal.principal_id == principal.principal_id,
        BehaviorGoal.state.in_(["completed", "incomplete", "rejected", "ended", "archived"]),
    )
    if cursor:
        end, goal_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                BehaviorGoal.window_end < end,
                and_(BehaviorGoal.window_end == end, BehaviorGoal.id < goal_id),
            )
        )
    rows = list(
        session.exec(
            statement.order_by(BehaviorGoal.window_end.desc(), BehaviorGoal.id.desc()).limit(
                limit + 1
            )
        ).all()
    )
    return BehaviorGoalHistoryPageV1(
        items=[_goal_response(item) for item in rows[:limit]],
        next_cursor=_encode_cursor(rows[limit - 1]) if len(rows) > limit else None,
    )


def _command_hash(principal_id: UUID, goal_id: UUID, command: BehaviorGoalCommandV1) -> str:
    return _hash(
        {
            "principal_ref": str(principal_id),
            "goal_id": str(goal_id),
            **command.model_dump(mode="json"),
        }
    )


def _command_replay(
    session: Session,
    principal_id: UUID,
    operation: str,
    goal_id: UUID,
    digest: str,
    command_hash: str,
) -> tuple[BehaviorGoalCommandResponseV1, int, bool] | None:
    row = session.exec(
        select(BehaviorGoalCommandIdempotency)
        .where(
            BehaviorGoalCommandIdempotency.principal_id == principal_id,
            BehaviorGoalCommandIdempotency.operation == operation,
            BehaviorGoalCommandIdempotency.source_goal_id == goal_id,
            BehaviorGoalCommandIdempotency.key_digest == digest,
        )
        .with_for_update()
    ).first()
    if row is None:
        return None
    if row.command_hash != command_hash:
        raise WeeklyPriorityError("IDEMPOTENCY_KEY_REUSED", 409, "تعارض الطلب مع محاولة سابقة.")
    return BehaviorGoalCommandResponseV1.model_validate(row.response_document), row.response_status, True


def command_goal(
    session: Session,
    principal: PrincipalContext,
    goal_id: UUID,
    command: BehaviorGoalCommandV1,
    idempotency_key: str,
) -> tuple[BehaviorGoalCommandResponseV1, int, bool]:
    if not _KEY_RE.fullmatch(idempotency_key):
        raise WeeklyPriorityError(
            "INVALID_IDEMPOTENCY_KEY", 400, "تعذر التحقق من الطلب. أعد المحاولة."
        )
    operation = (
        "behavior_goal_repeat" if command.event == "repeat" else f"behavior_goal.{command.event}"
    )
    digest, command_hash = (
        _key_digest(principal.principal_id, idempotency_key),
        _command_hash(principal.principal_id, goal_id, command),
    )
    replay = _command_replay(
        session, principal.principal_id, operation, goal_id, digest, command_hash
    )
    if replay:
        session.rollback()
        return replay
    session.exec(
        select(Principal).where(Principal.id == principal.principal_id).with_for_update()
    ).one()
    # A same-key transaction may have committed while this request waited for
    # the Principal lock. Re-read the ledger before any calendar or mutable
    # goal state so the second caller receives the exact original response.
    replay = _command_replay(
        session, principal.principal_id, operation, goal_id, digest, command_hash
    )
    if replay:
        session.rollback()
        return replay
    goal = session.exec(
        select(BehaviorGoal)
        .where(BehaviorGoal.id == goal_id, BehaviorGoal.principal_id == principal.principal_id)
        .with_for_update()
    ).first()
    if goal is None:
        raise WeeklyPriorityError("RESOURCE_NOT_FOUND", 404, "تعذر العثور على السجل المطلوب.")
    if goal.version != command.expected_version:
        raise WeeklyPriorityError(
            "GOAL_VERSION_CONFLICT", 409, "تغيّر الهدف. حدّث الصفحة ثم حاول مجددًا."
        )
    recommendation = session.exec(
        select(WeeklyPriorityRecommendation)
        .where(
            WeeklyPriorityRecommendation.id == goal.recommendation_id,
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
        )
        .with_for_update()
    ).one()
    previous = _goal_response(goal)
    created: BehaviorGoal | None = None
    now, authority = utcnow(), diary_calendar_authority()
    allowed = _ALLOWED_ACTIONS.get(goal.state, [])
    event_name = (
        "reduce" if command.event == "repeat" and command.repeat_mode == "reduce" else command.event
    )
    if event_name not in allowed:
        raise WeeklyPriorityError(
            "GOAL_STATE_CONFLICT", 409, "لا يتاح هذا الإجراء في حالة الهدف الحالية."
        )
    from_state = goal.state
    if command.event == "repeat":
        if goal.state != "incomplete":
            raise WeeklyPriorityError(
                "GOAL_STATE_CONFLICT", 409, "لا يتاح هذا الإجراء في حالة الهدف الحالية."
            )
        current = session.exec(
            select(WeeklyPriorityRecommendation)
            .where(
                WeeklyPriorityRecommendation.principal_id == principal.principal_id,
                WeeklyPriorityRecommendation.superseded_by_id.is_(None),
            )
            .order_by(WeeklyPriorityRecommendation.created_at.desc())
            .with_for_update()
        ).first()
        projected = _project_recommendation(current) if current else None
        if (
            not projected
            or not projected.main
            or projected.main.rule_key != goal.rule_key
            or projected.main.action_key != goal.action_key
            or projected.rules_version != goal.rules_version
        ):
            raise WeeklyPriorityError(
                "GOAL_REPEAT_PRIORITY_CONFLICT",
                409,
                "لا تتوافق أولوية الأسبوع الحالية مع تكرار هذا الهدف.",
            )
        target = (
            goal.weekly_target_count
            if command.repeat_mode == "same"
            else command.weekly_target_count
        )
        if (
            target is None
            or target < 1
            or target >= goal.weekly_target_count
            and command.repeat_mode == "reduce"
        ):
            raise WeeklyPriorityError(
                "GOAL_STATE_CONFLICT", 409, "لا يتاح هذا الإجراء في حالة الهدف الحالية."
            )
        existing_primary = session.exec(
            select(BehaviorGoal)
            .where(
                BehaviorGoal.principal_id == principal.principal_id,
                BehaviorGoal.state.in_(list(_PRIMARY_STATES)),
            )
            .with_for_update()
        ).first()
        if existing_primary:
            raise WeeklyPriorityError(
                "PRIMARY_GOAL_EXISTS", 409, "لديك هدف أساسي حالي. غيّره أو أنهه أولًا."
            )
        new_id, start = (
            uuid4(),
            max(authority.current_diary_date, goal.window_end + timedelta(days=1)),
        )
        created = BehaviorGoal(
            id=new_id,
            principal_id=principal.principal_id,
            recommendation_id=current.id,
            root_goal_id=goal.root_goal_id,
            previous_goal_id=goal.id,
            sequence_number=goal.sequence_number + 1,
            state="active",
            version=1,
            rule_key=goal.rule_key,
            action_key=goal.action_key,
            weekly_target_count=target,
            day_mask=[],
            window_start=start,
            window_end=start + timedelta(days=6),
            rules_version=goal.rules_version,
            copy_version=goal.copy_version,
            progress_document={},
            progress_revision=1,
            reminder_preference=goal.reminder_preference,
            accepted_at=now,
        )
        created.progress_document = _empty_progress(
            created, authority.current_diary_date, now
        ).model_dump(mode="json")
        session.add(created)
        session.add(
            BehaviorGoalHistory(
                goal_id=created.id,
                principal_id=principal.principal_id,
                root_goal_id=created.root_goal_id,
                previous_goal_id=goal.id,
                sequence_number=created.sequence_number,
                goal_version=1,
                event_type="repeated_from_previous_window",
                from_state=None,
                to_state="active",
                request_digest=command_hash,
                actor_type="owner",
                terms_progress_snapshot=created.progress_document,
            )
        )
        result, response_goal = (
            "reduced_and_repeated" if command.repeat_mode == "reduce" else "repeated",
            created,
        )
    elif command.event == "change":
        current = session.exec(
            select(WeeklyPriorityRecommendation)
            .where(
                WeeklyPriorityRecommendation.principal_id == principal.principal_id,
                WeeklyPriorityRecommendation.superseded_by_id.is_(None),
            )
            .order_by(WeeklyPriorityRecommendation.created_at.desc())
            .with_for_update()
        ).first()
        projected = _project_recommendation(current) if current else None
        if not projected or not projected.main:
            raise WeeklyPriorityError(
                "PRIORITY_EVIDENCE_UNAVAILABLE",
                503,
                "لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.",
            )
        if goal.state == "incomplete":
            result, response_goal = "change_available", goal
        else:
            goal.recommendation_id = current.id
            goal.rule_key, goal.action_key = projected.main.rule_key, projected.main.action_key
            goal.window_start, goal.window_end = (
                authority.current_diary_date,
                authority.current_diary_date + timedelta(days=6),
            )
            goal.weekly_target_count = command.weekly_target_count or goal.weekly_target_count
            goal.version += 1
            goal.progress_revision += 1
            goal.changed_at = now
            goal.updated_at = now
            goal.progress_document = _empty_progress(
                goal, authority.current_diary_date, now
            ).model_dump(mode="json")
            session.add(goal)
            session.add(
                BehaviorGoalHistory(
                    goal_id=goal.id,
                    principal_id=principal.principal_id,
                    root_goal_id=goal.root_goal_id,
                    previous_goal_id=goal.previous_goal_id,
                    sequence_number=goal.sequence_number,
                    goal_version=goal.version,
                    event_type="changed",
                    from_state=from_state,
                    to_state="active",
                    request_digest=command_hash,
                    actor_type="owner",
                    reason=command.change_reason or "owner_requested",
                    terms_progress_snapshot=goal.progress_document,
                )
            )
            result, response_goal = "changed", goal
        recommendation = current
    else:
        if command.event in {"accept", "edit"}:
            primary = session.exec(
                select(BehaviorGoal)
                .where(
                    BehaviorGoal.principal_id == principal.principal_id,
                    BehaviorGoal.id != goal.id,
                    BehaviorGoal.state.in_(list(_PRIMARY_STATES)),
                )
                .with_for_update()
            ).first()
            if primary:
                raise WeeklyPriorityError(
                    "PRIMARY_GOAL_EXISTS", 409, "لديك هدف أساسي حالي. غيّره أو أنهه أولًا."
                )
        transitions = {
            "accept": "active",
            "edit": "active",
            "defer": "deferred",
            "reject": "rejected",
            "pause": "paused",
            "resume": "active",
            "end": "ended",
        }
        goal.state = transitions[command.event]
        goal.version += 1
        goal.updated_at = now
        if command.weekly_target_count is not None:
            goal.weekly_target_count = command.weekly_target_count
        if command.scheduled_day_mask is not None:
            goal.day_mask = command.scheduled_day_mask
        if command.note is not None:
            goal.private_note = command.note
        if command.reminder_preference is not None:
            goal.reminder_preference = command.reminder_preference
        setattr(
            goal,
            {
                "accept": "accepted_at",
                "defer": "deferred_at",
                "reject": "rejected_at",
                "pause": "paused_at",
                "resume": "resumed_at",
                "end": "ended_at",
            }.get(command.event, "updated_at"),
            now,
        )
        if command.event == "defer":
            goal.deferred_until = min(
                authority.current_diary_date + timedelta(days=1), goal.window_end
            )
        session.add(goal)
        session.add(
            BehaviorGoalHistory(
                goal_id=goal.id,
                principal_id=principal.principal_id,
                root_goal_id=goal.root_goal_id,
                previous_goal_id=goal.previous_goal_id,
                sequence_number=goal.sequence_number,
                goal_version=goal.version,
                event_type=command.event,
                from_state=from_state,
                to_state=goal.state,
                request_digest=command_hash,
                actor_type="owner",
                reason=command.change_reason if command.event == "change" else command.reason,
                terms_progress_snapshot=goal.progress_document,
            )
        )
        result, response_goal = (
            {
                "accept": "accepted",
                "edit": "edited",
                "defer": "deferred",
                "reject": "rejected",
                "pause": "paused",
                "resume": "resumed",
                "end": "ended",
            }[command.event],
            goal,
        )
    response = BehaviorGoalCommandResponseV1(
        result=result,
        previous_goal=previous if created else None,
        goal=_goal_response(response_goal),
        recommendation=_project_recommendation(recommendation),
    )
    ledger = BehaviorGoalCommandIdempotency(
        principal_id=principal.principal_id,
        operation=operation,
        source_goal_id=goal_id,
        key_digest=digest,
        command_hash=command_hash,
        captured_diary_date=authority.current_diary_date,
        recommendation_id=recommendation.id,
        allocated_goal_id=created.id if created else goal.id,
        response_status=200,
        response_headers={"ETag": response.goal.etag},
        response_document=response.model_dump(mode="json"),
    )
    session.add(ledger)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise WeeklyPriorityError(
            "GOAL_VERSION_CONFLICT", 409, "تغيّر الهدف. حدّث الصفحة ثم حاول مجددًا."
        ) from error
    return response, 200, False


_ACTION_METRIC: dict[str, str] = {
    "replace_high_sodium_choice": "nutrient:sodium_mg",
    "replace_added_sugar_choice": "nutrient:added_sugar_g",
    "replace_saturated_fat_choice": "nutrient:saturated_fat_g",
    "replace_trans_fat_choice": "nutrient:trans_fat_g",
    "replace_processed_meat_choice": "group:processed_meat_occurrence_days",
    "replace_sugary_drink_choice": "group:sugar_sweetened_beverage_occurrence_days",
    "add_fruit_or_vegetable": "group:fruit_vegetable_g_per_day",
    "replace_with_fruit_or_vegetable": "group:fruit_vegetable_g_per_day",
    "add_legumes": "group:legumes_servings_per_period",
    "replace_with_legumes": "group:legumes_servings_per_period",
    "replace_with_whole_grain": "group:whole_grain_share_percent",
    "add_nuts_or_seeds": "group:nuts_seeds_servings_per_period",
    "replace_with_nuts_or_seeds": "group:nuts_seeds_servings_per_period",
    "replace_with_seafood": "group:seafood_servings_per_period",
    "add_dairy_or_fortified_alternative": "group:dairy_fortified_servings_per_day",
    "replace_with_dairy_or_fortified_alternative": "group:dairy_fortified_servings_per_day",
    "add_fiber_source": "nutrient:fiber_g",
    "replace_with_fiber_source": "nutrient:fiber_g",
}


def recompute_goal_progress(session: Session, goal: BehaviorGoal) -> bool:
    """Recompute from the persisted PLAN 032 contract; never read Diary rows."""
    try:
        analysis = current_analysis(session, PrincipalContext(principal_id=goal.principal_id))
    except Exception:
        return False
    source = analysis.priority_input
    if (
        validate_producer(
            source,
            stale=analysis.lifecycle_status == "stale",
            superseded=analysis.lifecycle_status == "superseded",
        )
        != "eligible"
    ):
        return False
    metric_key = _ACTION_METRIC.get(goal.action_key)
    if metric_key is None and goal.action_key.startswith("review_food_sources_"):
        metric_key = "nutrient:" + goal.action_key.removeprefix("review_food_sources_")
        metric_key += (
            "_mg"
            if metric_key.split(":", 1)[1] in {"potassium", "calcium", "iron", "magnesium", "zinc"}
            else "_mcg"
        )
    days = [item for item in source.days if goal.window_start <= item.date <= goal.window_end]
    complete = partial = unregistered = progress = 0
    versions: dict[str, int] = {}
    for day in days:
        versions[day.date.isoformat()] = day.logging_status_version
        if day.logging_status == "complete":
            complete += 1
            value = next(
                (fact.value for fact in day.metric_values if fact.metric_key == metric_key), None
            )
            if value is not None and value > 0:
                progress += 1
        elif day.logging_status == "partial":
            partial += 1
        else:
            unregistered += 1
    unregistered += 7 - len(days)
    ended = source.as_of_diary_date > goal.window_end
    if progress >= goal.weekly_target_count:
        status = "achieved"
    elif ended and complete < 4:
        status = "insufficient_evidence"
    elif complete:
        status = "not_yet_reached" if ended else "in_progress"
    else:
        status = "unknown"
    percent = min(100, round(100 * progress / goal.weekly_target_count))
    now = utcnow()
    document = BehaviorGoalProgressV1(
        window_start=goal.window_start,
        window_end=goal.window_end,
        progress_count=progress,
        target_count=goal.weekly_target_count,
        progress_percent=percent,
        complete_day_count=complete,
        partial_day_count=partial,
        unregistered_day_count=unregistered,
        status=status,
        as_of_diary_date=source.as_of_diary_date,
        source_day_versions=versions,
        calculation_rules_version=goal.rules_version,
        last_recomputed_at=now,
    ).model_dump(mode="json")
    if document == goal.progress_document:
        return False
    old_state = goal.state
    if status == "achieved" and goal.state == "active":
        goal.state, goal.completed_at = "completed", now
    elif (
        status != "achieved"
        and goal.state == "completed"
        and source.as_of_diary_date <= goal.window_end + timedelta(days=1)
    ):
        goal.state, goal.completed_at = "active", None
    goal.progress_document, goal.progress_revision = document, goal.progress_revision + 1
    goal.version, goal.updated_at = goal.version + 1, now
    session.add(goal)
    session.add(
        BehaviorGoalHistory(
            goal_id=goal.id,
            principal_id=goal.principal_id,
            root_goal_id=goal.root_goal_id,
            previous_goal_id=goal.previous_goal_id,
            sequence_number=goal.sequence_number,
            goal_version=goal.version,
            event_type="completed"
            if goal.state == "completed"
            else "evidence_reopened"
            if old_state == "completed"
            else "progress_updated",
            from_state=old_state,
            to_state=goal.state,
            actor_type="system",
            terms_progress_snapshot=document,
        )
    )
    return True


def process_due_goals(session: Session, *, limit: int = 100) -> dict[str, int]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    today, now = diary_calendar_authority().current_diary_date, utcnow()
    rows = list(
        session.exec(
            select(BehaviorGoal)
            .where(
                BehaviorGoal.state.in_(["active", "paused"]),
                or_(
                    BehaviorGoal.window_end < today,
                    and_(
                        BehaviorGoal.state == "active",
                        BehaviorGoal.window_start <= today - timedelta(days=3),
                    ),
                ),
            )
            .order_by(BehaviorGoal.window_end, BehaviorGoal.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    finalized = reminders = recomputed = 0
    delivery_enabled = get_settings().behavior_goal_reminder_delivery_enabled
    for goal in rows:
        recomputed += recompute_goal_progress(session, goal)
        progress = BehaviorGoalProgressV1.model_validate(goal.progress_document)
        ended = goal.window_end < today
        previous_state = goal.state
        if ended and progress.status != "achieved":
            goal.state, goal.version, goal.reviewed_at, goal.updated_at = (
                "incomplete",
                goal.version + 1,
                now,
                now,
            )
            session.add(goal)
            finalized += 1
            session.add(
                BehaviorGoalHistory(
                    goal_id=goal.id,
                    principal_id=goal.principal_id,
                    root_goal_id=goal.root_goal_id,
                    previous_goal_id=goal.previous_goal_id,
                    sequence_number=goal.sequence_number,
                    goal_version=goal.version,
                    event_type="finalized_incomplete",
                    from_state=previous_state,
                    to_state="incomplete",
                    actor_type="system",
                    terms_progress_snapshot=goal.progress_document,
                )
            )
        reminder_type = (
            "endweek_review"
            if ended
            else "midweek"
            if goal.state == "active"
            and progress.progress_count == 0
            and progress.complete_day_count >= 2
            else None
        )
        if (
            not delivery_enabled
            or goal.reminder_preference != "enabled"
            or reminder_type is None
            or progress.status in {"unknown", "achieved"}
        ):
            continue
        existing = session.exec(
            select(BehaviorGoalReminderDelivery).where(
                BehaviorGoalReminderDelivery.goal_id == goal.id,
                BehaviorGoalReminderDelivery.goal_revision == goal.version,
                BehaviorGoalReminderDelivery.reminder_type == reminder_type,
            )
        ).first()
        if existing is None:
            session.add(
                BehaviorGoalReminderDelivery(
                    goal_id=goal.id,
                    principal_id=goal.principal_id,
                    goal_revision=goal.version,
                    reminder_type=reminder_type,
                    channel="in_app",
                    eligibility_diary_date=today,
                    status="eligible",
                    attempts=0,
                )
            )
            reminders += 1
    session.commit()
    return {
        "processed": len(rows),
        "recomputed": recomputed,
        "finalized": finalized,
        "reminders": reminders,
    }
