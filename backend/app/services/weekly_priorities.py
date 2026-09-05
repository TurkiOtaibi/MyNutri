from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from typing import Any, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, exists, func, or_, tuple_, update
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
    NutritionAnalysis,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
    WeeklyPriorityEvidenceRef,
    WeeklyPriorityEvaluation,
    WeeklyPriorityRecommendation,
    utcnow,
)
from app.nutrition_rules.weekly_priority import (
    COPY_CATALOG,
    INFORMATIONAL_COPY_AR,
    METRIC_RULES,
    RULE_META,
    TRACKABLE_ACTIONS,
    WEEKLY_PRIORITY_COPY_VERSION,
    WEEKLY_PRIORITY_RULES_VERSION,
    action_day_qualifies,
    action_trackability,
    apply_goal_event,
    select as select_priority,
    validate_producer,
)
from app.schemas import (
    BehaviorGoalCommandResponseV1,
    BehaviorGoalCommandV1,
    BehaviorGoalCurrentResponseV1,
    BehaviorGoalHistoryPageV1,
    BehaviorGoalHistoryItemV1,
    BehaviorGoalHistorySnapshotV1,
    BehaviorGoalProgressV1,
    BehaviorGoalResponseV1,
    PriorityV1,
    WeeklyPriorityAnalysisInputV1,
    WeeklyPriorityExcludedV1,
    WeeklyPriorityFactV1,
    WeeklyPriorityResultV1,
)
from app.services.pattern_analysis import (
    PatternAnalysisError,
    contract_generation_state,
    current_analysis,
    refresh_historical_analysis,
)

_KEY_RE = re.compile(r"^[\x21-\x7e]{1,128}$")
_RIYADH = ZoneInfo("Asia/Riyadh")
_PRIMARY_STATES = {"active", "paused"}
_PRODUCER_INVALIDATION_EVENTS = (
    "day_reopened",
    "day_version_changed",
    "target_source_changed",
    "source_snapshot_corrected",
    "source_version_unsupported",
)
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


RecommendationSourceState = Literal[
    "VALID",
    "STALE",
    "SUPERSEDED",
    "UNSUPPORTED_VERSION",
    "UNSAFE",
    "TRACKABILITY_NOT_AVAILABLE",
]


@dataclass(frozen=True)
class RecommendationSourceValidation:
    state: RecommendationSourceState
    series: NutritionAnalysis | None = None
    revision: NutritionAnalysisRevision | None = None
    source: WeeklyPriorityAnalysisInputV1 | None = None


@dataclass(frozen=True)
class RecommendationSourceAuthority:
    bound_by_id: dict[UUID, NutritionAnalysis]
    latest_by_principal: dict[UUID, NutritionAnalysis]
    revision_by_id: dict[UUID, NutritionAnalysisRevision]
    events_by_revision: dict[UUID, set[str]]


_STALE_SOURCE_EVENTS = {
    "day_reopened",
    "day_version_changed",
    "target_source_changed",
    "source_snapshot_corrected",
    "source_version_unsupported",
}


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


def _is_expired(expires_at: datetime, *, now: datetime | None = None) -> bool:
    observed = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    return observed <= (now or utcnow())


def _finalization_boundary(period_end: date) -> datetime:
    """Return the governed 36-hour boundary from Riyadh diary midnight."""
    local_midnight = datetime.combine(period_end + timedelta(days=1), datetime.min.time(), _RIYADH)
    return (local_midnight + timedelta(hours=36)).astimezone(timezone.utc)


def _accepted_goal_window(
    recommendation: WeeklyPriorityRecommendation | WeeklyPriorityResultV1,
    start: date,
) -> tuple[date, date]:
    """Cap a seven-date execution window at the source period's next review end."""
    review_end = recommendation.period_end + timedelta(days=7)
    return start, min(start + timedelta(days=6), review_end)


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
        if tier == 1 and metric.direction == "minimize":
            qualifying = metric.current.status == "observed" and (metric.current.value or 0) > 0
        else:
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
    if not later_revision or not any(
        day.analysis_eligible
        and day.completed_at is not None
        and day.completed_at > rejected_goal.rejected_at
        for day in source.days
    ):
        return True
    prior_revision = session.get(
        NutritionAnalysisRevision, rejected_recommendation.source_analysis_revision_id
    )
    if prior_revision is None:
        return True
    try:
        prior_source = WeeklyPriorityAnalysisInputV1.model_validate(
            prior_revision.analysis_document
        )
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
    action_key = actions[mode]
    trackability, unavailable_reason = action_trackability(action_key)
    return PriorityV1(
        rule_key=rule_key,
        rank=rank,
        category={1: "limit", 2: "positive", 3: "micronutrient"}[tier],
        title_ar=title,
        reason_ar=reason,
        coverage_percent=metric.current.coverage_percent,
        complete_day_count=metric.current.complete_day_count,
        action_key=action_key,
        action_ar=action,
        action_mode=mode,
        goal_trackability=trackability,
        goal_unavailable_reason=unavailable_reason,
        goal_unavailable_copy_ar=(
            INFORMATIONAL_COPY_AR if trackability == "informational_only" else None
        ),
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
    elif _is_expired(row.expires_at) and document.get("status") == "selected":
        document.update(status="stale", main=None, secondary=None, none_reason="stale_analysis")
    document["etag"] = _recommendation_etag(row.id)
    return WeeklyPriorityResultV1.model_validate(document)


def _load_recommendation_source_authority(
    session: Session,
    recommendations: list[WeeklyPriorityRecommendation],
) -> RecommendationSourceAuthority:
    """Load the bounded PLAN 032 authority needed for recommendation validation.

    Bound historical series are loaded directly. Latest current series are
    selected once per Principal in the database through an indexed correlated
    top-one probe, so lifetime date-keyed history is never materialized here.
    """
    if not recommendations:
        return RecommendationSourceAuthority({}, {}, {}, {})
    principal_ids = {row.principal_id for row in recommendations}
    source_analysis_ids = {row.source_analysis_id for row in recommendations}

    bound_rows = list(
        session.exec(
            select(NutritionAnalysis).where(NutritionAnalysis.id.in_(source_analysis_ids))
        ).all()
    )
    bound_by_id = {row.id: row for row in bound_rows}

    latest_series_id = (
        select(NutritionAnalysis.id)
        .where(
            NutritionAnalysis.principal_id == Principal.id,
            NutritionAnalysis.current_revision_id.is_not(None),
        )
        .order_by(
            NutritionAnalysis.as_of_diary_date.desc(),
            NutritionAnalysis.id.desc(),
        )
        .limit(1)
        .correlate(Principal)
        .scalar_subquery()
    )
    latest_ids_by_principal = (
        select(
            Principal.id.label("principal_id"),
            latest_series_id.label("series_id"),
        )
        .where(Principal.id.in_(principal_ids))
        .subquery()
    )
    latest_rows = list(
        session.exec(
            select(NutritionAnalysis)
            .join(
                latest_ids_by_principal,
                latest_ids_by_principal.c.series_id == NutritionAnalysis.id,
            )
            .where(latest_ids_by_principal.c.series_id.is_not(None))
        ).all()
    )
    latest_by_principal = {row.principal_id: row for row in latest_rows}

    revision_ids = {row.source_analysis_revision_id for row in recommendations}
    revision_ids.update(
        series.current_revision_id
        for series in bound_by_id.values()
        if series.current_revision_id is not None
    )
    revisions = list(
        session.exec(
            select(NutritionAnalysisRevision).where(NutritionAnalysisRevision.id.in_(revision_ids))
        ).all()
    )
    revision_by_id = {row.id: row for row in revisions}
    events = list(
        session.exec(
            select(NutritionAnalysisRevisionEvent).where(
                NutritionAnalysisRevisionEvent.revision_id.in_(revision_ids)
            )
        ).all()
    )
    events_by_revision: dict[UUID, set[str]] = {}
    for event in events:
        events_by_revision.setdefault(event.revision_id, set()).add(event.event_type)

    return RecommendationSourceAuthority(
        bound_by_id=bound_by_id,
        latest_by_principal=latest_by_principal,
        revision_by_id=revision_by_id,
        events_by_revision=events_by_revision,
    )


def _validate_recommendation_sources(
    recommendations: list[WeeklyPriorityRecommendation],
    authority: RecommendationSourceAuthority,
    *,
    allow_newer_revision: bool = False,
    allow_insufficient_progress_evidence: bool = False,
    require_trackable: bool = False,
) -> dict[UUID, RecommendationSourceValidation]:
    """Apply one centralized policy to an immutable loaded source authority."""
    bound_by_id = authority.bound_by_id
    latest_by_principal = authority.latest_by_principal
    revision_by_id = authority.revision_by_id
    events_by_revision = authority.events_by_revision

    validations: dict[UUID, RecommendationSourceValidation] = {}
    for recommendation in recommendations:
        bound_series = bound_by_id.get(recommendation.source_analysis_id)
        latest_series = latest_by_principal.get(recommendation.principal_id)
        current_revision = (
            revision_by_id.get(bound_series.current_revision_id)
            if bound_series is not None
            else None
        )
        bound_revision = revision_by_id.get(recommendation.source_analysis_revision_id)
        if (
            recommendation.schema_version != 1
            or recommendation.rules_version != WEEKLY_PRIORITY_RULES_VERSION
            or recommendation.copy_version != WEEKLY_PRIORITY_COPY_VERSION
        ):
            validations[recommendation.id] = RecommendationSourceValidation(
                "UNSUPPORTED_VERSION", bound_series, current_revision
            )
            continue
        if recommendation.superseded_by_id is not None:
            validations[recommendation.id] = RecommendationSourceValidation(
                "SUPERSEDED", bound_series, current_revision
            )
            continue
        if bound_series is None or latest_series is None:
            validations[recommendation.id] = RecommendationSourceValidation("STALE")
            continue
        if bound_series.principal_id != recommendation.principal_id:
            validations[recommendation.id] = RecommendationSourceValidation(
                "STALE", bound_series, current_revision
            )
            continue
        if latest_series.id != bound_series.id and not allow_newer_revision:
            validations[recommendation.id] = RecommendationSourceValidation(
                "SUPERSEDED", bound_series, current_revision
            )
            continue
        if current_revision is None or bound_revision is None:
            validations[recommendation.id] = RecommendationSourceValidation(
                "STALE", bound_series, current_revision
            )
            continue
        if (
            bound_revision.analysis_id != recommendation.source_analysis_id
            or bound_revision.principal_id != recommendation.principal_id
            or bound_revision.revision != recommendation.source_analysis_revision
        ):
            validations[recommendation.id] = RecommendationSourceValidation(
                "UNSUPPORTED_VERSION", bound_series, current_revision
            )
            continue
        revision_advanced = current_revision.id != bound_revision.id
        if revision_advanced and not (
            allow_newer_revision
            and current_revision.analysis_id == recommendation.source_analysis_id
            and current_revision.revision > recommendation.source_analysis_revision
        ):
            validations[recommendation.id] = RecommendationSourceValidation(
                "SUPERSEDED", bound_series, current_revision
            )
            continue
        source_revision = current_revision if revision_advanced else bound_revision
        event_types = events_by_revision.get(source_revision.id, set())
        if "superseded_by_revision" in event_types:
            validations[recommendation.id] = RecommendationSourceValidation(
                "SUPERSEDED", bound_series, source_revision
            )
            continue
        try:
            source = WeeklyPriorityAnalysisInputV1.model_validate(source_revision.analysis_document)
        except ValueError:
            validations[recommendation.id] = RecommendationSourceValidation(
                "UNSUPPORTED_VERSION", bound_series, source_revision
            )
            continue
        if (
            source.source_analysis_id != source_revision.analysis_id
            or source.source_analysis_revision != source_revision.revision
            or source.interface_version != bound_series.interface_version
            or recommendation.analysis_rules_version != bound_revision.analysis_rules_version
        ):
            validations[recommendation.id] = RecommendationSourceValidation(
                "UNSUPPORTED_VERSION", bound_series, source_revision
            )
            continue
        producer_state = validate_producer(
            source,
            stale=bool(event_types & _STALE_SOURCE_EVENTS)
            or source.generated_at < utcnow() - timedelta(hours=36)
            or (not allow_newer_revision and _is_expired(recommendation.expires_at)),
            superseded=False,
            require_selector_eligibility=not allow_insufficient_progress_evidence,
        )
        if producer_state == "unsupported_version":
            state: RecommendationSourceState = "UNSUPPORTED_VERSION"
        elif producer_state == "superseded_analysis":
            state = "SUPERSEDED"
        elif producer_state == "stale_analysis":
            state = "STALE"
        elif producer_state != "eligible":
            state = "UNSAFE"
        else:
            state = "VALID"
        if state == "VALID" and require_trackable:
            try:
                projected = WeeklyPriorityResultV1.model_validate(recommendation.result_document)
            except ValueError:
                state = "UNSUPPORTED_VERSION"
            else:
                if (
                    projected.status != "selected"
                    or projected.main is None
                    or projected.main.goal_trackability != "trackable"
                ):
                    state = "TRACKABILITY_NOT_AVAILABLE"
        validations[recommendation.id] = RecommendationSourceValidation(
            state, bound_series, source_revision, source
        )
    return validations


def _recommendation_source_validations(
    session: Session,
    recommendations: list[WeeklyPriorityRecommendation],
    *,
    allow_newer_revision: bool = False,
    allow_insufficient_progress_evidence: bool = False,
    require_trackable: bool = False,
) -> dict[UUID, RecommendationSourceValidation]:
    """Convenience validator for non-batch callers using one bounded DB load."""
    authority = _load_recommendation_source_authority(session, recommendations)
    return _validate_recommendation_sources(
        recommendations,
        authority,
        allow_newer_revision=allow_newer_revision,
        allow_insufficient_progress_evidence=allow_insufficient_progress_evidence,
        require_trackable=require_trackable,
    )


def _validate_recommendation_source(
    session: Session,
    recommendation: WeeklyPriorityRecommendation,
    *,
    allow_newer_revision: bool = False,
    allow_insufficient_progress_evidence: bool = False,
    require_trackable: bool = False,
) -> RecommendationSourceValidation:
    return _recommendation_source_validations(
        session,
        [recommendation],
        allow_newer_revision=allow_newer_revision,
        allow_insufficient_progress_evidence=allow_insufficient_progress_evidence,
        require_trackable=require_trackable,
    )[recommendation.id]


def _raise_for_source_state(validation: RecommendationSourceValidation) -> None:
    if validation.state == "VALID":
        return
    code, status, message = {
        "STALE": (
            "PRIORITY_SOURCE_STALE",
            409,
            "انتهت صلاحية مصدر الأولوية. حدّث التحليل ثم حاول مجددًا.",
        ),
        "SUPERSEDED": (
            "PRIORITY_SOURCE_SUPERSEDED",
            409,
            "استُبدل مصدر الأولوية بتحليل أحدث. حدّث الصفحة ثم حاول مجددًا.",
        ),
        "UNSUPPORTED_VERSION": (
            "UNSUPPORTED_PRIORITY_VERSION",
            422,
            "إصدار مصدر الأولوية غير مدعوم.",
        ),
        "UNSAFE": (
            "PRIORITY_EVIDENCE_UNAVAILABLE",
            503,
            "لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.",
        ),
        "TRACKABILITY_NOT_AVAILABLE": (
            "GOAL_STATE_CONFLICT",
            409,
            "لا تتاح متابعة تلقائية لهذه الأولوية حاليًا.",
        ),
    }[validation.state]
    raise WeeklyPriorityError(code, status, message)


def _record_evaluation(
    session: Session,
    row: WeeklyPriorityRecommendation,
    result: WeeklyPriorityResultV1,
    evaluation_mode: str,
    evaluation_diary_date: date,
) -> None:
    existing = session.exec(
        select(WeeklyPriorityEvaluation).where(
            WeeklyPriorityEvaluation.principal_id == row.principal_id,
            WeeklyPriorityEvaluation.recommendation_id == row.id,
            WeeklyPriorityEvaluation.evaluation_mode == evaluation_mode,
            WeeklyPriorityEvaluation.evaluation_diary_date == evaluation_diary_date,
        )
    ).first()
    if existing is not None:
        return
    session.add(
        WeeklyPriorityEvaluation(
            principal_id=row.principal_id,
            recommendation_id=row.id,
            evaluation_mode=evaluation_mode,
            evaluation_diary_date=evaluation_diary_date,
            selector_eligible=result.none_reason
            not in {"invalid_analysis_input", "unsupported_version", "safety_exclusion"},
            recommendation_selected=result.status == "selected",
            main_trackability=result.main.goal_trackability if result.main else None,
            goal_offer_created=False,
        )
    )


def evaluate_recommendation(
    session: Session, principal: PrincipalContext, *, evaluation_mode: str = "live"
) -> WeeklyPriorityResultV1:
    if evaluation_mode not in {"live", "shadow"}:
        raise ValueError("evaluation_mode must be live or shadow")
    session.exec(
        select(Principal).where(Principal.id == principal.principal_id).with_for_update()
    ).one()
    v2_series_exists = session.exec(
        select(NutritionAnalysis.id).where(
            NutritionAnalysis.principal_id == principal.principal_id,
            NutritionAnalysis.interface_version == 2,
        )
    ).first()
    if contract_generation_state(session) == "NOVA_RETIRED" or v2_series_exists is not None:
        raise WeeklyPriorityError(
            "WEEKLY_PRIORITY_INACTIVE_FOR_ANALYSIS_V2",
            409,
            "التوصيات الأسبوعية غير مفعلة لهذا الإصدار من التحليل.",
        )
    analysis = current_analysis(session, principal)
    source = analysis.priority_input
    if source.interface_version != 1:
        raise WeeklyPriorityError(
            "WEEKLY_PRIORITY_INACTIVE_FOR_ANALYSIS_V2",
            409,
            "التوصيات الأسبوعية غير مفعلة لهذا الإصدار من التحليل.",
        )
    existing = session.exec(
        select(WeeklyPriorityRecommendation).where(
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
            WeeklyPriorityRecommendation.source_analysis_id == source.source_analysis_id,
            WeeklyPriorityRecommendation.source_analysis_revision
            == source.source_analysis_revision,
            WeeklyPriorityRecommendation.rules_version == WEEKLY_PRIORITY_RULES_VERSION,
        )
    ).first()
    evaluation_diary_date = diary_calendar_authority().current_diary_date
    if existing:
        projected = _project_recommendation(existing)
        _record_evaluation(session, existing, projected, evaluation_mode, evaluation_diary_date)
        session.commit()
        return projected
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
        expires_at=_finalization_boundary(source.period_end),
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
        evaluation_diary_date=evaluation_diary_date,
        evaluation_mode=evaluation_mode,
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
    _record_evaluation(session, row, result, evaluation_mode, evaluation_diary_date)
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
            "FEATURE_DISABLED",
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
    _raise_for_source_state(_validate_recommendation_source(session, row))
    return _project_recommendation(row)


def _empty_progress(goal: BehaviorGoal, as_of: date, now: datetime) -> BehaviorGoalProgressV1:
    window_day_count = sum(
        not goal.day_mask or (goal.window_start + timedelta(days=offset)).weekday() in goal.day_mask
        for offset in range((goal.window_end - goal.window_start).days + 1)
    )
    return BehaviorGoalProgressV1(
        window_start=goal.window_start,
        window_end=goal.window_end,
        progress_count=0,
        target_count=goal.weekly_target_count,
        progress_percent=0,
        complete_day_count=0,
        partial_day_count=0,
        unregistered_day_count=window_day_count,
        status="unknown",
        as_of_diary_date=as_of,
        source_day_versions={},
        calculation_rules_version=goal.rules_version,
        last_recomputed_at=now,
    )


def _goal_snapshot(
    goal: BehaviorGoal, recommendation: WeeklyPriorityRecommendation
) -> dict[str, Any]:
    """Immutable governed terms and derived state for historical reconstruction."""
    recommendation_document = WeeklyPriorityResultV1.model_validate(recommendation.result_document)
    priority = recommendation_document.main
    if priority is None or priority.action_key != goal.action_key:
        raise ValueError("goal snapshot requires its persisted source action")
    return {
        "goal_id": str(goal.id),
        "recommendation_id": str(goal.recommendation_id),
        "root_goal_id": str(goal.root_goal_id),
        "previous_goal_id": str(goal.previous_goal_id) if goal.previous_goal_id else None,
        "sequence_number": goal.sequence_number,
        "state": goal.state,
        "version": goal.version,
        "rule_key": goal.rule_key,
        "action_key": goal.action_key,
        "action_copy_ar": priority.action_ar,
        "goal_trackability": priority.goal_trackability,
        "goal_unavailable_reason": priority.goal_unavailable_reason,
        "informational_copy_ar": priority.goal_unavailable_copy_ar,
        "weekly_target_count": goal.weekly_target_count,
        "scheduled_day_mask": list(goal.day_mask),
        "owner_note": goal.private_note,
        "reminder_preference": goal.reminder_preference,
        "window_start": goal.window_start.isoformat(),
        "window_end": goal.window_end.isoformat(),
        "rules_version": goal.rules_version,
        "copy_version": goal.copy_version,
        "source_analysis_id": str(recommendation.source_analysis_id),
        "source_analysis_revision_id": str(recommendation.source_analysis_revision_id),
        "source_analysis_revision": recommendation.source_analysis_revision,
        "analysis_rules_version": recommendation.analysis_rules_version,
        "source_versions": dict(recommendation.source_versions),
        "last_progress_analysis_id": (
            str(goal.last_progress_analysis_id) if goal.last_progress_analysis_id else None
        ),
        "last_progress_analysis_revision_id": (
            str(goal.last_progress_analysis_revision_id)
            if goal.last_progress_analysis_revision_id
            else None
        ),
        "last_progress_analysis_revision": goal.last_progress_analysis_revision,
        "progress_revision": goal.progress_revision,
        "progress": dict(goal.progress_document),
        "offered_at": goal.created_at.isoformat(),
        "accepted_at": goal.accepted_at.isoformat() if goal.accepted_at else None,
        "deferred_at": goal.deferred_at.isoformat() if goal.deferred_at else None,
        "deferred_until": goal.deferred_until.isoformat() if goal.deferred_until else None,
        "changed_at": goal.changed_at.isoformat() if goal.changed_at else None,
        "paused_at": goal.paused_at.isoformat() if goal.paused_at else None,
        "resumed_at": goal.resumed_at.isoformat() if goal.resumed_at else None,
        "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        "reviewed_at": goal.reviewed_at.isoformat() if goal.reviewed_at else None,
        "rejected_at": goal.rejected_at.isoformat() if goal.rejected_at else None,
        "ended_at": goal.ended_at.isoformat() if goal.ended_at else None,
        "archived_at": goal.archived_at.isoformat() if goal.archived_at else None,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }


def _goal_response(goal: BehaviorGoal, authority=None) -> BehaviorGoalResponseV1:
    authority = authority or diary_calendar_authority()
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
        or recommendation.main.goal_trackability != "trackable"
        or _is_expired(recommendation.expires_at)
    ):
        return None
    recommendation_row = session.exec(
        select(WeeklyPriorityRecommendation).where(
            WeeklyPriorityRecommendation.id == recommendation.recommendation_id,
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
        )
    ).first()
    if recommendation_row is None:
        return None
    source_validation = _validate_recommendation_source(
        session, recommendation_row, require_trackable=True
    )
    if source_validation.state != "VALID":
        return None
    existing = session.exec(
        select(BehaviorGoal).where(
            BehaviorGoal.principal_id == principal.principal_id,
            BehaviorGoal.recommendation_id == recommendation.recommendation_id,
            BehaviorGoal.sequence_number == 1,
        )
    ).first()
    if existing:
        evaluation = session.exec(
            select(WeeklyPriorityEvaluation).where(
                WeeklyPriorityEvaluation.principal_id == principal.principal_id,
                WeeklyPriorityEvaluation.recommendation_id == recommendation.recommendation_id,
                WeeklyPriorityEvaluation.evaluation_mode == "live",
                WeeklyPriorityEvaluation.evaluation_diary_date
                == diary_calendar_authority().current_diary_date,
            )
        ).first()
        if evaluation is not None and not evaluation.goal_offer_created:
            evaluation.goal_offer_created = True
            session.add(evaluation)
            session.commit()
        return existing
    authority, now, goal_id = diary_calendar_authority(), utcnow(), uuid4()
    window_start, window_end = _accepted_goal_window(recommendation, authority.current_diary_date)
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
        window_start=window_start,
        window_end=window_end,
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
            terms_progress_snapshot=_goal_snapshot(goal, recommendation_row),
        )
    )
    evaluation = session.exec(
        select(WeeklyPriorityEvaluation).where(
            WeeklyPriorityEvaluation.principal_id == principal.principal_id,
            WeeklyPriorityEvaluation.recommendation_id == recommendation.recommendation_id,
            WeeklyPriorityEvaluation.evaluation_mode == "live",
            WeeklyPriorityEvaluation.evaluation_diary_date == authority.current_diary_date,
        )
    ).first()
    if evaluation is not None:
        evaluation.goal_offer_created = True
        session.add(evaluation)
    session.commit()
    session.refresh(goal)
    return goal


def current_goal(session: Session, principal: PrincipalContext) -> BehaviorGoalCurrentResponseV1:
    if not get_settings().weekly_priorities_display_enabled:
        return BehaviorGoalCurrentResponseV1(
            recommendation=None, goal=None, goal_unavailable_reason=None
        )
    goal = session.exec(
        select(BehaviorGoal)
        .where(
            BehaviorGoal.principal_id == principal.principal_id,
            BehaviorGoal.state.in_(["offered", "deferred", "active", "paused", "incomplete"]),
        )
        .order_by(
            case(
                (BehaviorGoal.state.in_(["active", "paused"]), 0),
                (BehaviorGoal.state == "incomplete", 1),
                else_=2,
            ),
            BehaviorGoal.updated_at.desc(),
            BehaviorGoal.id.desc(),
        )
    ).first()
    if goal is not None:
        source_row = session.exec(
            select(WeeklyPriorityRecommendation).where(
                WeeklyPriorityRecommendation.id == goal.recommendation_id,
                WeeklyPriorityRecommendation.principal_id == principal.principal_id,
            )
        ).first()
        if source_row is None:
            _raise_for_source_state(RecommendationSourceValidation("STALE"))
        source_validation = _validate_recommendation_source(
            session, source_row, require_trackable=True
        )
        if goal.state in {"offered", "deferred"} or source_validation.state != "SUPERSEDED":
            _raise_for_source_state(source_validation)
        recommendation = _project_recommendation(source_row)
        if recommendation.recommendation_id != goal.recommendation_id:
            _raise_for_source_state(RecommendationSourceValidation("UNSUPPORTED_VERSION"))
        return BehaviorGoalCurrentResponseV1(
            recommendation=recommendation,
            goal=_goal_response(goal),
            goal_unavailable_reason=None,
        )
    try:
        recommendation = current_recommendation(session, principal)
    except WeeklyPriorityError as error:
        if error.code != "PRIORITY_EVIDENCE_UNAVAILABLE":
            raise
        recommendation = None
    unavailable_reason = (
        recommendation.main.goal_unavailable_reason
        if recommendation and recommendation.main
        else None
    )
    return BehaviorGoalCurrentResponseV1(
        recommendation=recommendation,
        goal=None,
        goal_unavailable_reason=unavailable_reason,
    )


def _encode_cursor(history: BehaviorGoalHistory) -> str:
    return (
        urlsafe_b64encode(
            _canonical({"occurred_at": history.occurred_at.isoformat(), "id": str(history.id)})
        )
        .decode()
        .rstrip("=")
    )


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        value = json.loads(urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return datetime.fromisoformat(value["occurred_at"]), UUID(value["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise WeeklyPriorityError("VALIDATION_ERROR", 422, "تحقق من بيانات الطلب.") from error


def goal_history(
    session: Session, principal: PrincipalContext, limit: int, cursor: str | None
) -> BehaviorGoalHistoryPageV1:
    statement = select(BehaviorGoalHistory).where(
        BehaviorGoalHistory.principal_id == principal.principal_id
    )
    if cursor:
        occurred_at, history_id = _decode_cursor(cursor)
        statement = statement.where(
            tuple_(BehaviorGoalHistory.occurred_at, BehaviorGoalHistory.id)
            < tuple_(occurred_at, history_id)
        )
    rows = list(
        session.exec(
            statement.order_by(
                BehaviorGoalHistory.occurred_at.desc(), BehaviorGoalHistory.id.desc()
            ).limit(limit + 1)
        ).all()
    )
    return BehaviorGoalHistoryPageV1(
        items=[
            BehaviorGoalHistoryItemV1(
                history_id=item.id,
                goal_id=item.goal_id,
                root_goal_id=item.root_goal_id,
                previous_goal_id=item.previous_goal_id,
                sequence_number=item.sequence_number,
                goal_version=item.goal_version,
                event_type=item.event_type,
                from_state=item.from_state,
                to_state=item.to_state,
                occurred_at=item.occurred_at,
                reason=item.reason,
                snapshot=BehaviorGoalHistorySnapshotV1.model_validate(item.terms_progress_snapshot),
            )
            for item in rows[:limit]
        ],
        next_cursor=_encode_cursor(rows[limit - 1]) if len(rows) > limit else None,
    )


def archive_terminal_goal(
    session: Session,
    principal: PrincipalContext,
    goal_id: UUID,
    *,
    expected_version: int,
) -> BehaviorGoalResponseV1:
    """Retain only the frozen PLAN 033 terminal-to-archive operation."""
    goal = session.exec(
        select(BehaviorGoal).where(
            BehaviorGoal.id == goal_id,
            BehaviorGoal.principal_id == principal.principal_id,
        )
    ).first()
    if goal is None:
        raise WeeklyPriorityError("RESOURCE_NOT_FOUND", 404, "تعذر العثور على السجل المطلوب.")
    transition = apply_goal_event(
        {"state": goal.state, "version": goal.version},
        {"type": "archive", "expected_version": expected_version},
    )
    if transition["result"] == "stale_version_conflict":
        raise WeeklyPriorityError(
            "GOAL_VERSION_CONFLICT", 409, "تغيّر الهدف. حدّث الصفحة ثم حاول مجددًا."
        )
    if transition["result"] != "archived":
        raise WeeklyPriorityError("GOAL_STATE_CONFLICT", 409, "لا يمكن أرشفة هذه الحالة.")
    recommendation = session.exec(
        select(WeeklyPriorityRecommendation).where(
            WeeklyPriorityRecommendation.id == goal.recommendation_id,
            WeeklyPriorityRecommendation.principal_id == principal.principal_id,
        )
    ).one()
    previous_state = goal.state
    now = utcnow()
    result = session.exec(
        update(BehaviorGoal)
        .where(
            BehaviorGoal.id == goal.id,
            BehaviorGoal.principal_id == principal.principal_id,
            BehaviorGoal.state == previous_state,
            BehaviorGoal.version == expected_version,
        )
        .values(
            state="archived",
            version=expected_version + 1,
            archived_at=now,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        raise WeeklyPriorityError(
            "GOAL_VERSION_CONFLICT", 409, "تغيّر الهدف. حدّث الصفحة ثم حاول مجددًا."
        )
    session.expire(goal)
    session.refresh(goal)
    session.add(
        BehaviorGoalHistory(
            goal_id=goal.id,
            principal_id=principal.principal_id,
            root_goal_id=goal.root_goal_id,
            previous_goal_id=goal.previous_goal_id,
            sequence_number=goal.sequence_number,
            goal_version=goal.version,
            event_type="archive",
            from_state=previous_state,
            to_state="archived",
            actor_type="system",
            terms_progress_snapshot=_goal_snapshot(goal, recommendation),
            occurred_at=now,
        )
    )
    session.commit()
    session.refresh(goal)
    return _goal_response(goal)


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
    return (
        BehaviorGoalCommandResponseV1.model_validate(row.response_document),
        row.response_status,
        True,
    )


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
    if command.event in {"accept", "edit", "defer", "resume"}:
        _raise_for_source_state(
            _validate_recommendation_source(session, recommendation, require_trackable=True)
        )
    now, authority = utcnow(), diary_calendar_authority()
    previous = _goal_response(goal, authority)
    created: BehaviorGoal | None = None
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
        if current is not None:
            _raise_for_source_state(
                _validate_recommendation_source(session, current, require_trackable=True)
            )
        projected = _project_recommendation(current) if current else None
        if (
            not projected
            or not projected.main
            or projected.main.rule_key != goal.rule_key
            or projected.main.action_key != goal.action_key
            or projected.rules_version != goal.rules_version
            or projected.main.goal_trackability != "trackable"
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
                terms_progress_snapshot=_goal_snapshot(created, current),
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
        if current is not None:
            _raise_for_source_state(_validate_recommendation_source(session, current))
        projected = _project_recommendation(current) if current else None
        if not projected or not projected.main:
            raise WeeklyPriorityError(
                "PRIORITY_EVIDENCE_UNAVAILABLE",
                503,
                "لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.",
            )
        if projected.main.goal_trackability != "trackable":
            if goal.state != "incomplete":
                goal.state = "ended"
                goal.version += 1
                goal.ended_at = now
                goal.updated_at = now
                session.add(goal)
                session.add(
                    BehaviorGoalHistory(
                        goal_id=goal.id,
                        principal_id=principal.principal_id,
                        root_goal_id=goal.root_goal_id,
                        previous_goal_id=goal.previous_goal_id,
                        sequence_number=goal.sequence_number,
                        goal_version=goal.version,
                        event_type="end",
                        from_state=from_state,
                        to_state="ended",
                        request_digest=command_hash,
                        actor_type="owner",
                        reason=command.change_reason or "owner_requested",
                        terms_progress_snapshot=_goal_snapshot(goal, recommendation),
                    )
                )
            result, response_goal = "change_available", goal
        elif goal.state == "incomplete":
            result, response_goal = "change_available", goal
        else:
            goal.recommendation_id = current.id
            goal.rule_key, goal.action_key = projected.main.rule_key, projected.main.action_key
            goal.window_start, goal.window_end = _accepted_goal_window(
                current,
                authority.current_diary_date,
            )
            goal.weekly_target_count = command.weekly_target_count or goal.weekly_target_count
            if command.scheduled_day_mask is not None:
                goal.day_mask = command.scheduled_day_mask
            if command.note is not None:
                goal.private_note = command.note
            if command.reminder_preference is not None:
                goal.reminder_preference = command.reminder_preference
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
                    terms_progress_snapshot=_goal_snapshot(goal, current),
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
        if command.event in {"accept", "edit"}:
            goal.window_start, goal.window_end = _accepted_goal_window(
                recommendation,
                authority.current_diary_date,
            )
            goal.progress_revision += 1
            goal.progress_document = _empty_progress(
                goal, authority.current_diary_date, now
            ).model_dump(mode="json")
            if from_state in {"offered", "deferred"}:
                goal.accepted_at = now
            else:
                goal.changed_at = now
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
                terms_progress_snapshot=_goal_snapshot(goal, recommendation),
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
        goal=_goal_response(response_goal, authority),
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


def recompute_goal_progress(
    session: Session,
    goal: BehaviorGoal,
    *,
    source_override: WeeklyPriorityAnalysisInputV1 | None = None,
    recommendation: WeeklyPriorityRecommendation | None = None,
    source_validation: RecommendationSourceValidation | None = None,
) -> bool:
    """Recompute from the persisted PLAN 032 contract; never read Diary rows."""
    if recommendation is None:
        recommendation = session.exec(
            select(WeeklyPriorityRecommendation).where(
                WeeklyPriorityRecommendation.id == goal.recommendation_id,
                WeeklyPriorityRecommendation.principal_id == goal.principal_id,
            )
        ).first()
    if recommendation is None:
        return False
    validation = source_validation or _validate_recommendation_source(
        session,
        recommendation,
        allow_newer_revision=True,
        allow_insufficient_progress_evidence=True,
        require_trackable=True,
    )
    if validation.state != "VALID":
        return False
    source = source_override or validation.source
    if (
        source is None
        or validate_producer(source, require_selector_eligibility=False) != "eligible"
    ):
        return False
    if goal.action_key not in TRACKABLE_ACTIONS:
        return False
    days = [item for item in source.days if goal.window_start <= item.date <= goal.window_end]
    scheduled_dates = {
        goal.window_start + timedelta(days=offset)
        for offset in range((goal.window_end - goal.window_start).days + 1)
        if not goal.day_mask
        or (goal.window_start + timedelta(days=offset)).weekday() in goal.day_mask
    }
    complete = partial = unregistered = progress = 0
    versions: dict[str, int] = {}
    for day in days:
        if day.date not in scheduled_dates:
            continue
        versions[day.date.isoformat()] = day.logging_status_version
        if day.logging_status == "complete" and day.analysis_eligible:
            complete += 1
            if action_day_qualifies(goal.action_key, day.model_dump(mode="json")):
                progress += 1
        elif day.logging_status == "partial":
            partial += 1
        else:
            unregistered += 1
    represented_dates = {day.date for day in days if day.date in scheduled_dates}
    unregistered += len(scheduled_dates - represented_dates)
    finalization_boundary = _finalization_boundary(goal.window_end)
    ended = utcnow() >= finalization_boundary
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
    previous_evidence = {
        key: value for key, value in goal.progress_document.items() if key != "last_recomputed_at"
    }
    current_evidence = {
        key: value for key, value in document.items() if key != "last_recomputed_at"
    }
    source_cursor_changed = bool(
        validation.revision and goal.last_progress_analysis_revision_id != validation.revision.id
    )
    if validation.revision is not None:
        goal.last_progress_attempt_analysis_id = validation.revision.analysis_id
        goal.last_progress_attempt_analysis_revision_id = validation.revision.id
        goal.last_progress_attempt_analysis_revision = validation.revision.revision
        goal.last_progress_analysis_id = validation.revision.analysis_id
        goal.last_progress_analysis_revision_id = validation.revision.id
        goal.last_progress_analysis_revision = validation.revision.revision
    if current_evidence == previous_evidence:
        if source_cursor_changed:
            goal.updated_at = now
            session.add(goal)
        return False
    old_state = goal.state
    if status == "achieved" and goal.state == "active":
        goal.state, goal.completed_at = "completed", now
    elif status != "achieved" and goal.state == "completed" and now < finalization_boundary:
        goal.state, goal.completed_at = "active", None
    goal.progress_document, goal.progress_revision = document, goal.progress_revision + 1
    goal.version, goal.updated_at = goal.version + 1, now
    session.add(goal)
    if old_state == "completed" and goal.state == "active":
        event_type = "evidence_reopened"
    elif old_state == "completed" and now >= finalization_boundary:
        event_type = "historical_evidence_changed"
    elif old_state != "completed" and goal.state == "completed":
        event_type = "completed"
    else:
        event_type = "progress_updated"
    session.add(
        BehaviorGoalHistory(
            goal_id=goal.id,
            principal_id=goal.principal_id,
            root_goal_id=goal.root_goal_id,
            previous_goal_id=goal.previous_goal_id,
            sequence_number=goal.sequence_number,
            goal_version=goal.version,
            event_type=event_type,
            from_state=old_state,
            to_state=goal.state,
            actor_type="system",
            terms_progress_snapshot=_goal_snapshot(goal, recommendation),
        )
    )
    return True


def process_due_goals(session: Session, *, limit: int = 100) -> dict[str, int]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    today, now = diary_calendar_authority().current_diary_date, utcnow()
    normal_due = or_(
        and_(
            BehaviorGoal.state.in_(["active", "paused"]),
            or_(
                BehaviorGoal.window_end < today,
                and_(
                    BehaviorGoal.state == "active",
                    BehaviorGoal.window_start <= today - timedelta(days=3),
                ),
            ),
        ),
        and_(
            BehaviorGoal.state == "completed",
            BehaviorGoal.reviewed_at.is_(None),
            BehaviorGoal.window_end < today,
        ),
    )
    finalized_unattempted = and_(
        BehaviorGoal.state == "completed",
        BehaviorGoal.reviewed_at.is_not(None),
        BehaviorGoal.last_progress_attempt_analysis_revision_id.is_(None),
        exists(
            select(1)
            .select_from(WeeklyPriorityRecommendation)
            .join(
                NutritionAnalysis,
                and_(
                    NutritionAnalysis.id == WeeklyPriorityRecommendation.source_analysis_id,
                    NutritionAnalysis.principal_id == BehaviorGoal.principal_id,
                ),
            )
            .where(
                WeeklyPriorityRecommendation.id == BehaviorGoal.recommendation_id,
                WeeklyPriorityRecommendation.principal_id == BehaviorGoal.principal_id,
                NutritionAnalysis.current_revision_id.is_not(None),
                NutritionAnalysis.current_revision_number.is_not(None),
            )
        ),
    )
    finalized_revision_advanced = and_(
        BehaviorGoal.state == "completed",
        BehaviorGoal.reviewed_at.is_not(None),
        BehaviorGoal.last_progress_attempt_analysis_revision_id.is_not(None),
        exists(
            select(1)
            .select_from(WeeklyPriorityRecommendation)
            .join(
                NutritionAnalysis,
                and_(
                    NutritionAnalysis.id == WeeklyPriorityRecommendation.source_analysis_id,
                    NutritionAnalysis.principal_id == BehaviorGoal.principal_id,
                ),
            )
            .where(
                WeeklyPriorityRecommendation.id == BehaviorGoal.recommendation_id,
                WeeklyPriorityRecommendation.principal_id == BehaviorGoal.principal_id,
                BehaviorGoal.last_progress_attempt_analysis_id == NutritionAnalysis.id,
                NutritionAnalysis.current_revision_id.is_not(None),
                NutritionAnalysis.current_revision_number.is_not(None),
                BehaviorGoal.last_progress_attempt_analysis_revision
                < NutritionAnalysis.current_revision_number,
            )
        ),
    )
    finalized_event_pending = and_(
        BehaviorGoal.state == "completed",
        BehaviorGoal.reviewed_at.is_not(None),
        exists(
            select(1)
            .select_from(WeeklyPriorityRecommendation)
            .join(
                NutritionAnalysisRevision,
                and_(
                    NutritionAnalysisRevision.analysis_id
                    == WeeklyPriorityRecommendation.source_analysis_id,
                    NutritionAnalysisRevision.principal_id == BehaviorGoal.principal_id,
                ),
            )
            .join(
                NutritionAnalysisRevisionEvent,
                and_(
                    NutritionAnalysisRevisionEvent.revision_id == NutritionAnalysisRevision.id,
                    NutritionAnalysisRevisionEvent.principal_id == BehaviorGoal.principal_id,
                ),
            )
            .where(
                WeeklyPriorityRecommendation.id == BehaviorGoal.recommendation_id,
                WeeklyPriorityRecommendation.principal_id == BehaviorGoal.principal_id,
                NutritionAnalysisRevisionEvent.event_type.in_(_PRODUCER_INVALIDATION_EVENTS),
                or_(
                    BehaviorGoal.last_progress_attempt_event_id.is_(None),
                    NutritionAnalysisRevisionEvent.occurred_at
                    > BehaviorGoal.last_progress_attempt_event_occurred_at,
                    and_(
                        NutritionAnalysisRevisionEvent.occurred_at
                        == BehaviorGoal.last_progress_attempt_event_occurred_at,
                        NutritionAnalysisRevisionEvent.id
                        > BehaviorGoal.last_progress_attempt_event_id,
                    ),
                ),
            )
        ),
    )

    # Discover the exact bounded cohort without taking goal locks. The owner set
    # is derived from this work only, then locked in canonical Principal order.
    # Goal eligibility is re-checked after those owner locks are held; workers
    # never claim replacement work for an owner they did not lock.
    def discover_candidates(predicate, *, order_by, capacity, excluded_ids=frozenset()):
        if capacity <= 0:
            return []
        query = select(
            BehaviorGoal.id.label("goal_id"),
            BehaviorGoal.principal_id.label("principal_id"),
        ).where(predicate)
        if excluded_ids:
            query = query.where(BehaviorGoal.id.not_in(excluded_ids))
        return list(session.exec(query.order_by(*order_by).limit(capacity)).all())

    normal_candidates = discover_candidates(
        normal_due,
        order_by=(BehaviorGoal.window_end, BehaviorGoal.id),
        capacity=limit,
    )
    unattempted_candidates = discover_candidates(
        finalized_unattempted,
        order_by=(BehaviorGoal.window_end, BehaviorGoal.id),
        capacity=limit,
    )
    remaining_historical_capacity = limit - len(unattempted_candidates)
    advanced_candidates = discover_candidates(
        finalized_revision_advanced,
        order_by=(
            BehaviorGoal.last_progress_attempt_analysis_id,
            BehaviorGoal.last_progress_attempt_analysis_revision,
            BehaviorGoal.window_end,
            BehaviorGoal.id,
        ),
        capacity=remaining_historical_capacity,
    )
    selected_historical_candidate_ids = {
        row.goal_id for row in [*unattempted_candidates, *advanced_candidates]
    }
    remaining_historical_capacity -= len(advanced_candidates)
    event_candidates = discover_candidates(
        finalized_event_pending,
        order_by=(
            BehaviorGoal.last_progress_attempt_event_occurred_at,
            BehaviorGoal.last_progress_attempt_event_id,
            BehaviorGoal.window_end,
            BehaviorGoal.id,
        ),
        capacity=remaining_historical_capacity,
        excluded_ids=selected_historical_candidate_ids,
    )
    all_candidates = [
        *normal_candidates,
        *unattempted_candidates,
        *advanced_candidates,
        *event_candidates,
    ]
    principal_ids = sorted({row.principal_id for row in all_candidates})
    locked_principal_ids = set(
        session.exec(
            select(Principal.id)
            .where(Principal.id.in_(principal_ids))
            .order_by(Principal.id)
            .with_for_update()
        ).all()
        if principal_ids
        else []
    )

    def reclaim_candidates(candidates, predicate, *, order_by):
        candidate_ids = {row.goal_id for row in candidates}
        if not candidate_ids or not locked_principal_ids:
            return []
        return list(
            session.exec(
                select(BehaviorGoal)
                .where(
                    BehaviorGoal.id.in_(candidate_ids),
                    BehaviorGoal.principal_id.in_(locked_principal_ids),
                    predicate,
                )
                .order_by(*order_by)
                .with_for_update(skip_locked=True)
            ).all()
        )

    normal_rows = reclaim_candidates(
        normal_candidates,
        normal_due,
        order_by=(BehaviorGoal.window_end, BehaviorGoal.id),
    )
    unattempted_rows = reclaim_candidates(
        unattempted_candidates,
        finalized_unattempted,
        order_by=(BehaviorGoal.window_end, BehaviorGoal.id),
    )
    advanced_rows = reclaim_candidates(
        advanced_candidates,
        finalized_revision_advanced,
        order_by=(
            BehaviorGoal.last_progress_attempt_analysis_id,
            BehaviorGoal.last_progress_attempt_analysis_revision,
            BehaviorGoal.window_end,
            BehaviorGoal.id,
        ),
    )
    event_rows = reclaim_candidates(
        event_candidates,
        finalized_event_pending,
        order_by=(
            BehaviorGoal.last_progress_attempt_event_occurred_at,
            BehaviorGoal.last_progress_attempt_event_id,
            BehaviorGoal.window_end,
            BehaviorGoal.id,
        ),
    )
    historical_rows = [*unattempted_rows, *advanced_rows, *event_rows]
    rows = [*normal_rows, *historical_rows]
    historical_goal_ids = {goal.id for goal in historical_rows}
    existing_reminders = {
        (row.goal_id, row.goal_revision, row.reminder_type)
        for row in (
            session.exec(
                select(BehaviorGoalReminderDelivery).where(
                    BehaviorGoalReminderDelivery.goal_id.in_({goal.id for goal in rows})
                )
            ).all()
            if rows
            else []
        )
    }
    recommendation_rows = (
        list(
            session.exec(
                select(WeeklyPriorityRecommendation).where(
                    WeeklyPriorityRecommendation.id.in_({goal.recommendation_id for goal in rows})
                )
            ).all()
        )
        if rows
        else []
    )
    recommendation_by_id = {row.id: row for row in recommendation_rows}

    pending_event_by_goal: dict[UUID, NutritionAnalysisRevisionEvent] = {}
    event_recommendations = [
        recommendation_by_id[goal.recommendation_id]
        for goal in event_rows
        if goal.recommendation_id in recommendation_by_id
    ]
    if event_recommendations:
        source_keys = {(row.source_analysis_id, row.principal_id) for row in event_recommendations}
        ranked_events = (
            select(
                NutritionAnalysisRevisionEvent.id.label("event_id"),
                NutritionAnalysisRevisionEvent.principal_id.label("principal_id"),
                NutritionAnalysisRevisionEvent.occurred_at.label("occurred_at"),
                NutritionAnalysisRevision.analysis_id.label("analysis_id"),
                func.row_number()
                .over(
                    partition_by=(
                        NutritionAnalysisRevision.analysis_id,
                        NutritionAnalysisRevisionEvent.principal_id,
                    ),
                    order_by=(
                        NutritionAnalysisRevisionEvent.occurred_at.desc(),
                        NutritionAnalysisRevisionEvent.id.desc(),
                    ),
                )
                .label("event_rank"),
            )
            .join(
                NutritionAnalysisRevision,
                NutritionAnalysisRevision.id == NutritionAnalysisRevisionEvent.revision_id,
            )
            .where(
                tuple_(
                    NutritionAnalysisRevision.analysis_id,
                    NutritionAnalysisRevisionEvent.principal_id,
                ).in_(source_keys),
                NutritionAnalysisRevisionEvent.event_type.in_(_PRODUCER_INVALIDATION_EVENTS),
            )
            .subquery()
        )
        latest_event_rows = session.exec(
            select(
                ranked_events.c.event_id,
                ranked_events.c.principal_id,
                ranked_events.c.occurred_at,
                ranked_events.c.analysis_id,
            ).where(ranked_events.c.event_rank == 1)
        ).all()
        latest_event_ids = {row.event_id for row in latest_event_rows}
        event_by_id = {
            event.id: event
            for event in session.exec(
                select(NutritionAnalysisRevisionEvent).where(
                    NutritionAnalysisRevisionEvent.id.in_(latest_event_ids)
                )
            ).all()
        }
        latest_by_source = {
            (row.analysis_id, row.principal_id): event_by_id[row.event_id]
            for row in latest_event_rows
            if row.event_id in event_by_id
            and event_by_id[row.event_id].principal_id == row.principal_id
        }
        refreshed_sources: set[tuple[UUID, UUID, UUID]] = set()
        for goal in event_rows:
            recommendation = recommendation_by_id.get(goal.recommendation_id)
            if recommendation is None:
                continue
            event = latest_by_source.get((recommendation.source_analysis_id, goal.principal_id))
            if event is None:
                continue
            event_cursor = (event.occurred_at, event.id)
            goal_cursor = (
                goal.last_progress_attempt_event_occurred_at,
                goal.last_progress_attempt_event_id,
            )
            if goal_cursor[0] is not None and event_cursor <= goal_cursor:
                continue
            pending_event_by_goal[goal.id] = event
            refresh_key = (goal.principal_id, recommendation.source_analysis_id, event.id)
            if refresh_key in refreshed_sources:
                continue
            try:
                refresh_historical_analysis(
                    session,
                    PrincipalContext(goal.principal_id),
                    recommendation.source_analysis_id,
                    event.id,
                )
            except PatternAnalysisError:
                # The immutable event is still recorded as attempted below; a
                # later event remains independently eligible. Successful source
                # cursors are advanced only after persisted producer validation.
                pass
            refreshed_sources.add(refresh_key)

    source_authority = _load_recommendation_source_authority(session, recommendation_rows)
    progress_validations = _validate_recommendation_sources(
        recommendation_rows,
        source_authority,
        allow_newer_revision=True,
        allow_insufficient_progress_evidence=True,
        require_trackable=True,
    )
    action_validations = _validate_recommendation_sources(
        recommendation_rows,
        source_authority,
        require_trackable=True,
    )
    finalized = reminders = recomputed = 0
    delivery_enabled = get_settings().behavior_goal_reminder_delivery_enabled
    for goal in rows:
        recommendation = recommendation_by_id.get(goal.recommendation_id)
        if recommendation is None:
            continue
        pending_event = pending_event_by_goal.get(goal.id)
        if pending_event is not None:
            goal.last_progress_attempt_event_id = pending_event.id
            goal.last_progress_attempt_event_occurred_at = pending_event.occurred_at
            session.add(goal)
        progress_validation = progress_validations[recommendation.id]
        attempted_revision = progress_validation.revision
        attempted_cursor_changed = bool(
            attempted_revision is not None
            and goal.last_progress_attempt_analysis_revision_id != attempted_revision.id
        )
        if attempted_revision is not None:
            goal.last_progress_attempt_analysis_id = attempted_revision.analysis_id
            goal.last_progress_attempt_analysis_revision_id = attempted_revision.id
            goal.last_progress_attempt_analysis_revision = attempted_revision.revision
            if attempted_cursor_changed:
                session.add(goal)
        if (
            progress_validation.state == "VALID"
            and progress_validation.revision is not None
            and goal.last_progress_analysis_revision_id != progress_validation.revision.id
        ):
            recomputed += recompute_goal_progress(
                session,
                goal,
                recommendation=recommendation,
                source_validation=progress_validation,
            )
        elif goal.id in historical_goal_ids and attempted_cursor_changed:
            # A rejected current producer revision is recorded as attempted but
            # never as successfully processed, and cannot fabricate history.
            session.add(goal)
        progress = BehaviorGoalProgressV1.model_validate(goal.progress_document)
        source_actionable = action_validations[recommendation.id].state == "VALID"
        finalization_boundary = _finalization_boundary(goal.window_end)
        ended = now >= finalization_boundary
        previous_state = goal.state
        if ended and goal.state in {"active", "paused"} and progress.status != "achieved":
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
                    terms_progress_snapshot=_goal_snapshot(goal, recommendation),
                )
            )
        elif ended and goal.state == "completed" and goal.reviewed_at is None:
            goal.version += 1
            goal.reviewed_at = now
            goal.updated_at = now
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
                    event_type="finalized_completed",
                    from_state="completed",
                    to_state="completed",
                    actor_type="system",
                    terms_progress_snapshot=_goal_snapshot(goal, recommendation),
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
            or not source_actionable
            or goal.reminder_preference != "enabled"
            or reminder_type is None
            or progress.status in {"unknown", "achieved"}
        ):
            continue
        reminder_key = (goal.id, goal.version, reminder_type)
        if reminder_key not in existing_reminders:
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
            existing_reminders.add(reminder_key)
    session.commit()
    return {
        "processed": len(rows),
        "recomputed": recomputed,
        "finalized": finalized,
        "reminders": reminders,
    }
