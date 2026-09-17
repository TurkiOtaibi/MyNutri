from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, date, timedelta
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import current_diary_date
from app.models import (
    DiaryEntry,
    IdempotencyRecord,
    IdempotencyState,
    Principal,
    Profile,
    TargetPlan,
    utcnow,
)
from app.schemas import (
    ProfilePreview,
    TargetPlanHistoryResponse,
    TargetPlanSummary,
    TargetPlanWriteRequest,
    TargetPlanWriteResponse,
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


@dataclass(frozen=True, slots=True)
class WeekTargetContext:
    plans: tuple[TargetPlan, ...]


def _canonical_hash(payload: TargetPlanWriteRequest) -> str:
    data = payload.model_dump(mode="json", exclude={"expected_preview_hash"})
    return sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _legacy_hash(payload: TargetPlanWriteRequest, operation: str) -> str:
    data = payload.model_dump(
        mode="json",
        exclude={"effective_from", "expected_preview_hash", "confirmed"},
    )
    if operation == "target_plan.activate":
        data["confirmed"] = True
    elif operation == "target_plan.replace":
        data["replace_confirmed"] = True
    else:
        raise ValueError("Unsupported legacy Target Plan operation")
    return sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _profile_data(payload: ProfilePreview) -> dict[str, Any]:
    data = payload.model_dump(exclude={"confirmed", "expected_preview_hash", "effective_from"})
    data["cut_intensity"] = data.pop("selected_cut_intensity")
    return data


def _target_document(payload: TargetPlanWriteRequest, targets: TargetResponse) -> dict[str, Any]:
    target_data = targets.model_dump(mode="json", exclude={"preview_hash"})
    return {
        "effective_from": payload.effective_from.isoformat(),
        "profile_inputs": payload.model_dump(
            mode="json",
            exclude={"confirmed", "expected_preview_hash", "effective_from"},
        ),
        "selected_cut_intensity": targets.selected_cut_intensity,
        "requested_deficit_kcal": targets.requested_deficit_kcal,
        "applied_deficit_kcal": targets.applied_deficit_kcal,
        "deficit_cap_applied": targets.deficit_cap_applied,
        "calorie_safety_outcome": targets.safety_outcome,
        "protein_calculation": targets.protein_calculation.model_dump(mode="json"),
        "target_result": target_data,
        "carbohydrate_warning_codes": [item.code for item in targets.calculation_warnings],
        "calendar_timezone": "Asia/Riyadh",
    }


def _targets_from_plan(plan: TargetPlan) -> TargetResponse:
    return TargetResponse.model_validate(plan.calculation_document["target_result"])


def to_plan_summary(plan: TargetPlan) -> TargetPlanSummary:
    created_at = plan.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return TargetPlanSummary(
        id=plan.id,
        effective_from=plan.effective_from,
        revision=plan.revision,
        targets=_targets_from_plan(plan),
        created_at=created_at,
    )


def _database_riyadh_date(session: Session) -> date:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return current_diary_date()
    return (
        session.connection()
        .execute(text("SELECT (clock_timestamp() AT TIME ZONE 'Asia/Riyadh')::date"))
        .scalar_one()
    )


def _load_owned_plan(
    session: Session, principal_id: UUID, plan_id: UUID | None
) -> TargetPlan | None:
    if plan_id is None:
        return None
    return session.exec(
        select(TargetPlan).where(
            TargetPlan.id == plan_id,
            TargetPlan.principal_id == principal_id,
        )
    ).first()


def _response_from_record(
    session: Session,
    principal_id: UUID,
    record: IdempotencyRecord,
    expected_effective_from: date,
) -> TargetPlanWriteResponse:
    plan = _load_owned_plan(session, principal_id, record.resource_id)
    if plan is None or plan.effective_from != expected_effective_from:
        raise TargetPlanError(
            "IDEMPOTENCY_REPLAY_INVALID",
            409,
            "استُخدم مفتاح الطلب مع محتوى مختلف.",
        )
    document = record.response_document
    if not isinstance(document, dict):
        raise TargetPlanError(
            "IDEMPOTENCY_REPLAY_INVALID",
            409,
            "استُخدم مفتاح الطلب مع محتوى مختلف.",
        )
    replaced_document = document.get("replaced_plan")
    replaced_plan = None
    if replaced_document is not None:
        if not isinstance(replaced_document, dict) or not isinstance(
            replaced_document.get("id"), str
        ):
            raise TargetPlanError(
                "IDEMPOTENCY_REPLAY_INVALID",
                409,
                "استُخدم مفتاح الطلب مع محتوى مختلف.",
            )
        try:
            replaced_id = UUID(replaced_document["id"])
        except ValueError as error:
            raise TargetPlanError(
                "IDEMPOTENCY_REPLAY_INVALID",
                409,
                "استُخدم مفتاح الطلب مع محتوى مختلف.",
            ) from error
        replaced_plan = _load_owned_plan(session, principal_id, replaced_id)
        if replaced_plan is None or replaced_plan.effective_from != plan.effective_from:
            raise TargetPlanError(
                "IDEMPOTENCY_REPLAY_INVALID",
                409,
                "استُخدم مفتاح الطلب مع محتوى مختلف.",
            )
    return TargetPlanWriteResponse(
        plan=to_plan_summary(plan),
        replaced_plan=to_plan_summary(replaced_plan) if replaced_plan else None,
    )


def _replay_new_record(
    session: Session,
    principal_id: UUID,
    record: IdempotencyRecord,
    request_hash: str,
    effective_from: date,
) -> TargetPlanWriteResponse:
    if record.request_hash != request_hash:
        raise TargetPlanError("IDEMPOTENCY_KEY_REUSED", 409, "استُخدم مفتاح الطلب مع محتوى مختلف.")
    if record.state != IdempotencyState.completed:
        raise TargetPlanError("IDEMPOTENCY_REQUEST_IN_PROGRESS", 409, "الطلب نفسه قيد التنفيذ.")
    return _response_from_record(session, principal_id, record, effective_from)


def _replay_legacy_record(
    session: Session,
    principal_id: UUID,
    payload: TargetPlanWriteRequest,
    idempotency_key: str,
) -> TargetPlanWriteResponse | None:
    records = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == principal_id,
            IdempotencyRecord.operation.in_(["target_plan.activate", "target_plan.replace"]),
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    ).all()
    if not records:
        return None
    matching = [
        record
        for record in records
        if record.request_hash == _legacy_hash(payload, record.operation)
    ]
    if len(matching) > 1:
        raise TargetPlanError(
            "IDEMPOTENCY_REPLAY_AMBIGUOUS",
            409,
            "استُخدم مفتاح الطلب مع محتوى مختلف.",
        )
    if not matching:
        raise TargetPlanError("IDEMPOTENCY_KEY_REUSED", 409, "استُخدم مفتاح الطلب مع محتوى مختلف.")
    record = matching[0]
    if record.state != IdempotencyState.completed:
        raise TargetPlanError("IDEMPOTENCY_REQUEST_IN_PROGRESS", 409, "الطلب نفسه قيد التنفيذ.")
    return _response_from_record(session, principal_id, record, payload.effective_from)


def _validate_idempotency_key(idempotency_key: str) -> None:
    if (
        not idempotency_key
        or len(idempotency_key) > 128
        or not all(0x21 <= ord(character) <= 0x7E for character in idempotency_key)
    ):
        raise TargetPlanError("INVALID_IDEMPOTENCY_KEY", 422, "مفتاح الطلب غير صالح.")


def _date_conflict(code: str) -> TargetPlanError:
    return TargetPlanError(
        code,
        409,
        "تغيّرت نتيجة المعاينة؛ راجعها ثم أكد مجددًا.",
    )


def write_target_plan(
    session: Session,
    principal: PrincipalContext,
    payload: TargetPlanWriteRequest,
    idempotency_key: str,
) -> tuple[TargetPlanWriteResponse, bool]:
    _validate_idempotency_key(idempotency_key)
    request_hash = _canonical_hash(payload)
    try:
        session.exec(
            select(Principal).where(Principal.id == principal.principal_id).with_for_update()
        ).one()
        profile = session.exec(
            select(Profile).where(Profile.principal_id == principal.principal_id).with_for_update()
        ).first()
        captured_date = _database_riyadh_date(session)

        existing_record = session.exec(
            select(IdempotencyRecord).where(
                IdempotencyRecord.principal_id == principal.principal_id,
                IdempotencyRecord.operation == "target_plan.write",
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        ).first()
        if existing_record is not None:
            replay = _replay_new_record(
                session,
                principal.principal_id,
                existing_record,
                request_hash,
                payload.effective_from,
            )
            session.rollback()
            return replay, True

        legacy_replay = _replay_legacy_record(
            session, principal.principal_id, payload, idempotency_key
        )
        if legacy_replay is not None:
            session.rollback()
            return legacy_replay, True

        if payload.effective_from < captured_date:
            raise _date_conflict("TARGET_PLAN_EFFECTIVE_DATE_PAST")

        previous_plan = session.exec(
            select(TargetPlan)
            .where(
                TargetPlan.principal_id == principal.principal_id,
                TargetPlan.effective_from == payload.effective_from,
            )
            .order_by(TargetPlan.revision.desc(), TargetPlan.id.desc())
            .with_for_update()
        ).first()

        targets = to_target_response(payload, payload.effective_from)
        if targets.preview_hash != payload.expected_preview_hash:
            raise TargetPlanError(
                "PREVIEW_RESULT_CHANGED",
                409,
                "تغيّرت نتيجة المعاينة؛ راجعها ثم أكد مجددًا.",
            )
        if not targets.can_activate:
            code = (
                "VERY_LOW_ENERGY_TARGET_BLOCKED"
                if targets.safety_outcome == "very_low_energy_blocked"
                else "SPECIALIST_REVIEW_REQUIRED"
            )
            raise TargetPlanError(code, 422, "لا يمكن حفظ هذه النتيجة وفق سياسة السلامة.")

        if profile is None:
            profile = Profile(
                principal_id=principal.principal_id,
                **_profile_data(payload),
            )
            session.add(profile)
            session.flush()

        for key, value in _profile_data(payload).items():
            setattr(profile, key, value)
        now = utcnow()
        profile.updated_at = now
        session.add(profile)

        new_plan = TargetPlan(
            principal_id=principal.principal_id,
            profile_id=profile.id,
            effective_from=payload.effective_from,
            revision=(previous_plan.revision + 1) if previous_plan else 1,
            calculation_document=_target_document(payload, targets),
            created_at=now,
        )
        session.add(new_plan)
        session.flush()

        next_effective_from = session.exec(
            select(func.min(TargetPlan.effective_from)).where(
                TargetPlan.principal_id == principal.principal_id,
                TargetPlan.effective_from > payload.effective_from,
            )
        ).one()
        entries_statement = select(DiaryEntry).where(
            DiaryEntry.principal_id == principal.principal_id,
            DiaryEntry.entry_date >= payload.effective_from,
        )
        if next_effective_from is not None:
            entries_statement = entries_statement.where(DiaryEntry.entry_date < next_effective_from)
        entries = session.exec(entries_statement.with_for_update()).all()
        for entry in entries:
            if entry.target_plan_id != new_plan.id:
                entry.target_plan_id = new_plan.id
                session.add(entry)

        response = TargetPlanWriteResponse(
            plan=to_plan_summary(new_plan),
            replaced_plan=to_plan_summary(previous_plan) if previous_plan else None,
        )
        session.add(
            IdempotencyRecord(
                principal_id=principal.principal_id,
                operation="target_plan.write",
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
        )

        final_date = _database_riyadh_date(session)
        if payload.effective_from < final_date:
            raise _date_conflict("TARGET_PLAN_DATE_BOUNDARY_CHANGED")
        session.commit()
        return response, False
    except TargetPlanError:
        session.rollback()
        raise
    except IntegrityError as error:
        session.rollback()
        raise TargetPlanError(
            "TARGET_PLAN_CONFLICT",
            409,
            "تغيّرت نتيجة المعاينة؛ راجعها ثم أكد مجددًا.",
        ) from error
    except Exception:
        session.rollback()
        raise


def resolve_target_plan(
    session: Session,
    principal: PrincipalContext,
    requested_date: date,
) -> TargetPlan | None:
    return session.exec(
        select(TargetPlan)
        .where(
            TargetPlan.principal_id == principal.principal_id,
            TargetPlan.effective_from <= requested_date,
        )
        .order_by(
            TargetPlan.effective_from.desc(),
            TargetPlan.revision.desc(),
            TargetPlan.id.desc(),
        )
        .limit(1)
    ).first()
def _target_source_response(
    plan: TargetPlan | None,
) -> TargetSourceResponse:
    if plan is not None:
        return TargetSourceResponse(
            plan=to_plan_summary(plan),
            targets=_targets_from_plan(plan),
        )
    return TargetSourceResponse(
        plan=None,
        targets=None,
    )


def resolve_week_target_context(
    session: Session,
    principal: PrincipalContext,
    week_start: date,
    week_end: date,
) -> WeekTargetContext:
    canonical_revisions = (
        select(
            TargetPlan.principal_id.label("principal_id"),
            TargetPlan.effective_from.label("effective_from"),
            func.max(TargetPlan.revision).label("revision"),
        )
        .where(
            TargetPlan.principal_id == principal.principal_id,
            TargetPlan.effective_from <= week_end,
        )
        .group_by(TargetPlan.principal_id, TargetPlan.effective_from)
        .subquery()
    )
    latest_before_week = (
        select(func.max(TargetPlan.effective_from))
        .where(
            TargetPlan.principal_id == principal.principal_id,
            TargetPlan.effective_from < week_start,
        )
        .scalar_subquery()
    )
    plans = session.exec(
        select(TargetPlan)
        .join(
            canonical_revisions,
            and_(
                TargetPlan.principal_id == canonical_revisions.c.principal_id,
                TargetPlan.effective_from == canonical_revisions.c.effective_from,
                TargetPlan.revision == canonical_revisions.c.revision,
            ),
        )
        .where(
            or_(
                TargetPlan.effective_from >= week_start,
                TargetPlan.effective_from == latest_before_week,
            )
        )
        .order_by(
            TargetPlan.effective_from.desc(),
            TargetPlan.revision.desc(),
            TargetPlan.id.desc(),
        )
    ).all()
    return WeekTargetContext(plans=tuple(plans))


def target_for_date(context: WeekTargetContext, requested_date: date) -> TargetSourceResponse:
    plan = next(
        (item for item in context.plans if item.effective_from <= requested_date),
        None,
    )
    return _target_source_response(plan)
def resolve_targets(
    session: Session,
    principal: PrincipalContext,
    requested_date: date,
) -> TargetSourceResponse:
    return _target_source_response(resolve_target_plan(session, principal, requested_date))


def _encode_history_cursor(plan: TargetPlan) -> str:
    payload = json.dumps(
        {
            "effective_from": plan.effective_from.isoformat(),
            "revision": plan.revision,
            "id": str(plan.id),
        },
        separators=(",", ":"),
    ).encode()
    return urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_history_cursor(cursor: str) -> tuple[date, int, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(urlsafe_b64decode(cursor + padding))
        if set(payload) != {"effective_from", "revision", "id"}:
            raise ValueError
        return (
            date.fromisoformat(payload["effective_from"]),
            int(payload["revision"]),
            UUID(payload["id"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TargetPlanError("INVALID_CURSOR", 422, "مؤشر التصفح غير صالح.") from error


def plan_history(
    session: Session,
    principal: PrincipalContext,
    limit: int,
    cursor: str | None = None,
) -> TargetPlanHistoryResponse:
    statement = select(TargetPlan).where(TargetPlan.principal_id == principal.principal_id)
    if cursor:
        effective_from, revision, plan_id = _decode_history_cursor(cursor)
        statement = statement.where(
            or_(
                TargetPlan.effective_from < effective_from,
                and_(
                    TargetPlan.effective_from == effective_from,
                    TargetPlan.revision < revision,
                ),
                and_(
                    TargetPlan.effective_from == effective_from,
                    TargetPlan.revision == revision,
                    TargetPlan.id < plan_id,
                ),
            )
        )
    plans = session.exec(
        statement.order_by(
            TargetPlan.effective_from.desc(),
            TargetPlan.revision.desc(),
            TargetPlan.id.desc(),
        ).limit(limit + 1)
    ).all()
    has_more = len(plans) > limit
    items = plans[:limit]
    next_cursor = _encode_history_cursor(items[-1]) if has_more else None
    return TargetPlanHistoryResponse(
        items=[to_plan_summary(item) for item in items],
        next_cursor=next_cursor,
    )
