from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import current_diary_date, next_diary_date
from app.models import (
    IdempotencyRecord,
    IdempotencyState,
    LegacyTargetTransitionSnapshot,
    Principal,
    Profile,
    TargetPlan,
    TargetPlanStatus,
    utcnow,
)
from app.nutrition_rules.versions import VERSIONS
from app.schemas import (
    ProfilePreview,
    TargetPlanActivationRequest,
    TargetPlanActivationResponse,
    TargetPlanHistoryResponse,
    TargetPlanReplacementRequest,
    TargetPlanSummary,
    TargetResponse,
    TargetSourceResponse,
)
from app.services.profile import to_target_response


class TargetPlanError(RuntimeError):
    def __init__(self, code: str, status_code: int, message_ar: str) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.message_ar = message_ar


def _canonical_hash(payload: Any) -> str:
    data = payload.model_dump(mode="json", exclude={"expected_preview_hash"})
    return sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _profile_data(payload: ProfilePreview) -> dict[str, Any]:
    data = payload.model_dump(exclude={"confirmed", "replace_confirmed", "expected_preview_hash"})
    data["cut_intensity"] = data.pop("selected_cut_intensity")
    return data


def _target_document(payload: ProfilePreview, targets: TargetResponse) -> dict[str, Any]:
    target_data = targets.model_dump(mode="json", exclude={"preview_hash"})
    return {
        "schema_version": 1,
        "profile_inputs": payload.model_dump(
            mode="json", exclude={"confirmed", "replace_confirmed", "expected_preview_hash"}
        ),
        "selected_cut_intensity": targets.selected_cut_intensity,
        "requested_deficit_kcal": targets.requested_deficit_kcal,
        "applied_deficit_kcal": targets.applied_deficit_kcal,
        "deficit_cap_applied": targets.deficit_cap_applied,
        "calorie_safety_outcome": targets.safety_outcome,
        "protein_calculation": targets.protein_calculation.model_dump(mode="json"),
        "target_result": target_data,
        "carbohydrate_warning_codes": [item.code for item in targets.calculation_warnings],
        "calculation_engine_version": VERSIONS.calculation_engine_version,
        "nutrition_registry_version": VERSIONS.nutrition_registry_version,
        "calendar_timezone": "Asia/Riyadh",
    }


def _legacy_document(profile: Profile, targets: TargetResponse) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "legacy_unversioned_transition",
        "captured_profile_inputs": {
            "sex": profile.sex.value,
            "birth_date": profile.birth_date.isoformat(),
            "height_cm": float(profile.height_cm),
            "weight_kg": float(profile.weight_kg),
            "activity_level": profile.activity_level.value,
            "goal": profile.goal.value,
            "protein_per_kg": float(profile.protein_per_kg),
            "fat_pct": float(profile.fat_pct),
            "cut_intensity": float(profile.cut_intensity),
        },
        "resolved_targets": targets.model_dump(mode="json", exclude={"preview_hash"}),
    }


def _targets_from_plan(plan: TargetPlan) -> TargetResponse:
    return TargetResponse.model_validate(plan.calculation_document["target_result"])


def to_plan_summary(plan: TargetPlan) -> TargetPlanSummary:
    return TargetPlanSummary(
        id=plan.id,
        status=plan.status.value if hasattr(plan.status, "value") else plan.status,
        effective_from=plan.effective_from,
        effective_to=plan.effective_to,
        calendar_timezone=plan.calendar_timezone,
        predecessor_plan_id=plan.predecessor_plan_id,
        superseded_by_plan_id=plan.superseded_by_plan_id,
        targets=_targets_from_plan(plan),
        created_at=plan.created_at,
        activated_at=plan.activated_at,
        closed_at=plan.closed_at,
        superseded_at=plan.superseded_at,
    )


def _replay(record: IdempotencyRecord, request_hash: str) -> TargetPlanActivationResponse | None:
    if record.request_hash != request_hash:
        raise TargetPlanError("IDEMPOTENCY_KEY_REUSED", 409, "استُخدم مفتاح الطلب مع محتوى مختلف.")
    if record.state == IdempotencyState.completed and record.response_document:
        return TargetPlanActivationResponse.model_validate(record.response_document)
    raise TargetPlanError("IDEMPOTENCY_REQUEST_IN_PROGRESS", 409, "الطلب نفسه قيد التنفيذ.")


def _advance_lifecycle(session: Session, principal_id, today: date) -> None:
    due = session.exec(
        select(TargetPlan).where(
            TargetPlan.principal_id == principal_id,
            TargetPlan.status == TargetPlanStatus.scheduled,
            TargetPlan.effective_from <= today,
        ).with_for_update()
    ).first()
    if due is None:
        return
    now = utcnow()
    active = session.exec(
        select(TargetPlan).where(
            TargetPlan.principal_id == principal_id,
            TargetPlan.status == TargetPlanStatus.active,
            TargetPlan.effective_to.is_(None),
        ).with_for_update()
    ).first()
    if active:
        active.status = TargetPlanStatus.closed
        active.effective_to = due.effective_from
        active.closed_at = now
        session.add(active)
        session.flush()
    due.status = TargetPlanStatus.active
    due.activated_at = now
    session.add(due)
    session.flush()


def activate_plan(
    session: Session,
    principal: PrincipalContext,
    payload: TargetPlanActivationRequest | TargetPlanReplacementRequest,
    idempotency_key: str,
    *,
    replace_pending: bool = False,
) -> tuple[TargetPlanActivationResponse, bool]:
    if (
        not idempotency_key
        or len(idempotency_key) > 128
        or not all(0x21 <= ord(character) <= 0x7E for character in idempotency_key)
    ):
        raise TargetPlanError("INVALID_IDEMPOTENCY_KEY", 422, "مفتاح الطلب غير صالح.")

    operation = "target_plan.replace" if replace_pending else "target_plan.activate"
    request_hash = _canonical_hash(payload)
    try:
        session.exec(
            select(Principal)
            .where(Principal.id == principal.principal_id)
            .with_for_update()
        ).one()
        profile = session.exec(
            select(Profile)
            .where(Profile.principal_id == principal.principal_id)
            .with_for_update()
        ).first()
        existing_record = session.exec(
            select(IdempotencyRecord).where(
                IdempotencyRecord.principal_id == principal.principal_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        ).first()
        if existing_record:
            replay = _replay(existing_record, request_hash)
            session.rollback()
            return replay, True

        today = current_diary_date()
        _advance_lifecycle(session, principal.principal_id, today)
        plans = session.exec(
            select(TargetPlan).where(TargetPlan.principal_id == principal.principal_id)
        ).all()
        pending = next((item for item in plans if item.status == TargetPlanStatus.scheduled), None)
        if replace_pending and pending is None:
            raise TargetPlanError("NO_PENDING_TARGET_PLAN", 409, "لا توجد خطة مجدولة لاستبدالها.")
        if not replace_pending and pending is not None:
            raise TargetPlanError("TARGET_PLAN_PENDING_EXISTS", 409, "توجد خطة مجدولة بالفعل.")

        was_new_profile = profile is None
        if profile is None:
            profile = Profile(principal_id=principal.principal_id, **_profile_data(payload))
            session.add(profile)
            session.flush()

        effective_from = today if was_new_profile and not plans else next_diary_date()
        targets = to_target_response(payload, effective_from)
        if targets.preview_hash != payload.expected_preview_hash:
            raise TargetPlanError("PREVIEW_RESULT_CHANGED", 409, "تغيّرت نتيجة المعاينة؛ راجعها ثم أكد مجددًا.")
        if not targets.can_activate:
            code = (
                "VERY_LOW_ENERGY_TARGET_BLOCKED"
                if targets.safety_outcome == "very_low_energy_blocked"
                else "SPECIALIST_REVIEW_REQUIRED"
            )
            raise TargetPlanError(code, 422, "لا يمكن تفعيل هذه النتيجة وفق سياسة السلامة.")

        transition = session.exec(
            select(LegacyTargetTransitionSnapshot).where(
                LegacyTargetTransitionSnapshot.profile_id == profile.id
            )
        ).first()
        first_legacy_transition = not was_new_profile and not plans and transition is None
        if first_legacy_transition:
            legacy_targets = to_target_response(profile, today)
            transition = LegacyTargetTransitionSnapshot(
                principal_id=principal.principal_id,
                profile_id=profile.id,
                transition_date=today,
                calendar_timezone="Asia/Riyadh",
                target_document_schema_version=1,
                legacy_target_document=_legacy_document(profile, legacy_targets),
            )
            session.add(transition)

        for key, value in _profile_data(payload).items():
            setattr(profile, key, value)
        profile.updated_at = utcnow()
        session.add(profile)

        status = TargetPlanStatus.active if effective_from == today else TargetPlanStatus.scheduled
        now = utcnow()
        new_plan = TargetPlan(
            principal_id=principal.principal_id,
            profile_id=profile.id,
            status=status,
            effective_from=effective_from,
            effective_to=None,
            calendar_timezone="Asia/Riyadh",
            predecessor_plan_id=pending.id if pending else None,
            activation_idempotency_key=idempotency_key,
            calculation_document=_target_document(payload, targets),
            calculation_document_schema_version=1,
            calculation_engine_version=VERSIONS.calculation_engine_version,
            nutrition_registry_version=VERSIONS.nutrition_registry_version,
            activated_at=now if status == TargetPlanStatus.active else None,
        )
        replaced_summary = None
        if pending:
            pending.status = TargetPlanStatus.superseded_before_effective
            pending.superseded_at = now
            pending.superseded_by_plan_id = new_plan.id
            session.add(pending)
            session.flush()
            replaced_summary = to_plan_summary(pending)
        session.add(new_plan)
        session.flush()

        response = TargetPlanActivationResponse(
            plan=to_plan_summary(new_plan), replaced_plan=replaced_summary
        )
        record = IdempotencyRecord(
            principal_id=principal.principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            state=IdempotencyState.completed,
            response_status=201,
            response_document=response.model_dump(mode="json"),
            resource_type="target_plan",
            resource_id=new_plan.id,
            completed_at=now,
            expires_at=now + timedelta(days=3650),
        )
        session.add(record)
        session.commit()
        return response, False
    except TargetPlanError:
        session.rollback()
        raise
    except IntegrityError as error:
        session.rollback()
        raise TargetPlanError("TARGET_PLAN_CONFLICT", 409, "تعارض طلب التفعيل مع طلب آخر.") from error
    except Exception:
        session.rollback()
        raise


def resolve_targets(
    session: Session, principal: PrincipalContext, requested_date: date
) -> TargetSourceResponse:
    _advance_lifecycle(session, principal.principal_id, current_diary_date())
    session.commit()
    plan = session.exec(
        select(TargetPlan)
        .where(
            TargetPlan.principal_id == principal.principal_id,
            TargetPlan.effective_from <= requested_date,
            (TargetPlan.effective_to.is_(None) | (TargetPlan.effective_to > requested_date)),
            TargetPlan.status.in_([TargetPlanStatus.active, TargetPlanStatus.closed, TargetPlanStatus.scheduled]),
        )
        .order_by(TargetPlan.effective_from.desc())
    ).first()
    if plan:
        return TargetSourceResponse(
            target_provenance="versioned_plan",
            target_source_detail="effective_target_plan",
            plan=to_plan_summary(plan),
            targets=_targets_from_plan(plan),
        )
    transition = session.exec(
        select(LegacyTargetTransitionSnapshot).where(
            LegacyTargetTransitionSnapshot.principal_id == principal.principal_id,
            LegacyTargetTransitionSnapshot.transition_date == requested_date,
        )
    ).first()
    if transition:
        return TargetSourceResponse(
            target_provenance="legacy_unversioned",
            target_source_detail="legacy_transition_snapshot",
            plan=None,
            targets=TargetResponse.model_validate(
                transition.legacy_target_document["resolved_targets"]
            ),
        )
    profile = session.exec(
        select(Profile).where(Profile.principal_id == principal.principal_id)
    ).first()
    any_transition = session.exec(
        select(LegacyTargetTransitionSnapshot.id).where(
            LegacyTargetTransitionSnapshot.principal_id == principal.principal_id
        )
    ).first()
    if profile and any_transition is None and requested_date == current_diary_date():
        return TargetSourceResponse(
            target_provenance="legacy_unversioned",
            target_source_detail="no_preserved_target_source",
            plan=None,
            targets=to_target_response(profile, requested_date),
        )
    return TargetSourceResponse(
        target_provenance="no_target_source",
        target_source_detail="no_preserved_target_source",
        plan=None,
        targets=None,
    )


def pending_plan(session: Session, principal: PrincipalContext) -> TargetPlanSummary | None:
    plan = session.exec(
        select(TargetPlan).where(
            TargetPlan.principal_id == principal.principal_id,
            TargetPlan.status == TargetPlanStatus.scheduled,
            TargetPlan.effective_from > current_diary_date(),
        )
    ).first()
    return to_plan_summary(plan) if plan else None


def _encode_history_cursor(plan: TargetPlan) -> str:
    payload = json.dumps(
        {"created_at": plan.created_at.isoformat(), "id": str(plan.id)},
        separators=(",", ":"),
    ).encode()
    return urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_history_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(urlsafe_b64decode(cursor + padding))
        return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TargetPlanError("INVALID_CURSOR", 422, "مؤشر التصفح غير صالح.") from error


def plan_history(
    session: Session, principal: PrincipalContext, limit: int, cursor: str | None = None
) -> TargetPlanHistoryResponse:
    statement = select(TargetPlan).where(TargetPlan.principal_id == principal.principal_id)
    if cursor:
        created_at, plan_id = _decode_history_cursor(cursor)
        statement = statement.where(
            or_(
                TargetPlan.created_at < created_at,
                and_(TargetPlan.created_at == created_at, TargetPlan.id < plan_id),
            )
        )
    plans = session.exec(
        statement.order_by(TargetPlan.created_at.desc(), TargetPlan.id.desc()).limit(limit + 1)
    ).all()
    has_more = len(plans) > limit
    items = plans[:limit]
    next_cursor = _encode_history_cursor(items[-1]) if has_more else None
    return TargetPlanHistoryResponse(
        items=[to_plan_summary(item) for item in items], next_cursor=next_cursor
    )
