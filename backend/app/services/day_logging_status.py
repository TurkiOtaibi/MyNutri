from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import DiaryCalendarAuthority
from app.models import (
    DiaryDayStatus,
    DiaryDayStatusEvent,
    DiaryDayStatusHistory,
    DiaryDayStatusValue,
    DiaryEntry,
    IdempotencyRecord,
    IdempotencyState,
    Principal,
    utcnow,
)
from app.schemas import CalendarAuthorityResponse, DiaryDayStatusResponse

_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _error(status_code: int, code: str, message_ar: str, **extra: object) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message_ar": message_ar, **extra},
    )


def lock_owner(session: Session, principal: PrincipalContext) -> None:
    session.exec(
        select(Principal)
        .where(Principal.id == principal.principal_id)
        .with_for_update()
    ).one()


def entry_count_for_day(session: Session, principal_id: UUID, diary_date: date) -> int:
    return len(
        session.exec(
            select(DiaryEntry.id).where(
                DiaryEntry.principal_id == principal_id,
                DiaryEntry.entry_date == diary_date,
            )
        ).all()
    )


def _status_row(
    session: Session, principal_id: UUID, diary_date: date, *, lock: bool = False
) -> DiaryDayStatus | None:
    statement = select(DiaryDayStatus).where(
        DiaryDayStatus.principal_id == principal_id,
        DiaryDayStatus.diary_date == diary_date,
    )
    if lock:
        statement = statement.with_for_update()
    return session.exec(statement).first()


def _calendar_response(authority: DiaryCalendarAuthority) -> CalendarAuthorityResponse:
    return CalendarAuthorityResponse(
        current_diary_date=authority.current_diary_date,
        calendar_timezone=authority.calendar_timezone,
        next_rollover_at=authority.next_rollover_at,
    )


def _project(
    row: DiaryDayStatus | None,
    diary_date: date,
    entry_count: int,
    authority: DiaryCalendarAuthority,
) -> DiaryDayStatusResponse:
    if diary_date > authority.current_diary_date:
        row = None
        entry_count = 0
    if row is not None:
        status = row.status.value if isinstance(row.status, DiaryDayStatusValue) else row.status
    else:
        status = "partial" if entry_count else "unregistered"
    return DiaryDayStatusResponse(
        date=diary_date,
        logging_status=status,
        logging_status_version=row.version if row else 0,
        entry_count=entry_count,
        analysis_eligible=status == "complete",
        completed_at=row.completed_at if row else None,
        calendar=_calendar_response(authority),
    )


def project_day_status(
    session: Session,
    principal: PrincipalContext,
    diary_date: date,
    authority: DiaryCalendarAuthority,
) -> DiaryDayStatusResponse:
    row = _status_row(session, principal.principal_id, diary_date)
    return _project(
        row,
        diary_date,
        row.entry_count if row else entry_count_for_day(session, principal.principal_id, diary_date),
        authority,
    )


def project_status_range(
    session: Session,
    principal: PrincipalContext,
    start: date,
    end: date,
    authority: DiaryCalendarAuthority,
) -> list[DiaryDayStatusResponse]:
    rows = session.exec(
        select(DiaryDayStatus).where(
            DiaryDayStatus.principal_id == principal.principal_id,
            DiaryDayStatus.diary_date >= start,
            DiaryDayStatus.diary_date <= end,
        )
    ).all()
    entries = session.exec(
        select(DiaryEntry.entry_date).where(
            DiaryEntry.principal_id == principal.principal_id,
            DiaryEntry.entry_date >= start,
            DiaryEntry.entry_date <= end,
        )
    ).all()
    counts: dict[date, int] = {}
    for item in entries:
        counts[item] = counts.get(item, 0) + 1
    by_date = {row.diary_date: row for row in rows}
    result = []
    current = start
    while current <= end:
        row = by_date.get(current)
        result.append(_project(row, current, row.entry_count if row else counts.get(current, 0), authority))
        current += timedelta(days=1)
    return result


def _future_guard(diary_date: date, authority: DiaryCalendarAuthority) -> None:
    if diary_date > authority.current_diary_date:
        raise _error(
            422,
            "FUTURE_DIARY_DATE",
            "لا يمكن تغيير حالة يوم مستقبلي.",
            current_diary_date=authority.current_diary_date.isoformat(),
            calendar_timezone=authority.calendar_timezone,
        )


def lock_day_for_entry(
    session: Session,
    principal: PrincipalContext,
    diary_date: date,
    expected_version: int | None,
    authority: DiaryCalendarAuthority,
) -> DiaryDayStatus | None:
    _future_guard(diary_date, authority)
    row = _status_row(session, principal.principal_id, diary_date, lock=True)
    version = row.version if row else 0
    if expected_version is not None and expected_version != version:
        current = _project(
            row,
            diary_date,
            row.entry_count if row else entry_count_for_day(session, principal.principal_id, diary_date),
            authority,
        )
        raise _error(
            409,
            "DAY_VERSION_CONFLICT",
            "تغيّرت بيانات اليوم. حدّث الصفحة ثم حاول مجددًا.",
            current=current.model_dump(mode="json", exclude={"calendar"}),
        )
    if row is not None and row.status == DiaryDayStatusValue.complete:
        raise _error(409, "DAY_ALREADY_COMPLETE", "أعد فتح اليوم قبل تعديل الوجبات.")
    return row


def record_entry_mutation(
    session: Session,
    principal: PrincipalContext,
    diary_date: date,
    row: DiaryDayStatus | None,
    event: DiaryDayStatusEvent,
    entry_id: UUID,
    resulting_entry_count: int,
) -> DiaryDayStatus:
    previous = row.status if row else None
    now = utcnow()
    if row is None:
        row = DiaryDayStatus(
            principal_id=principal.principal_id,
            diary_date=diary_date,
            status=DiaryDayStatusValue.partial,
            version=1,
            entry_count=resulting_entry_count,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
    else:
        row.version += 1
        row.entry_count = resulting_entry_count
        row.updated_at = now
        session.add(row)
    session.add(
        DiaryDayStatusHistory(
            day_status_id=row.id,
            principal_id=principal.principal_id,
            diary_date=diary_date,
            from_status=previous,
            to_status=DiaryDayStatusValue.partial,
            event_type=event,
            day_version=row.version,
            entry_id=entry_id,
            actor_principal_id=principal.principal_id,
            occurred_at=now,
        )
    )
    # PLAN 032 owns historical source invalidation. Entry mutations are only
    # possible while a day is non-complete, but they still need a distinct,
    # owner-bound day-version identity so an older analysis window can be
    # refreshed after a previous reopen was already attempted.
    from app.services.pattern_analysis import append_stale_events_for_date

    append_stale_events_for_date(
        session,
        principal.principal_id,
        diary_date,
        "day_version_changed",
        "diary_entry_changed",
        row.version,
    )
    return row


def _request_hash(
    operation: str, diary_date: date, expected_version: int, principal_id: UUID
) -> str:
    canonical = json.dumps(
        {
            "date": diary_date.isoformat(),
            "expected_version": expected_version,
            "operation": operation,
            "principal_id": str(principal_id),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def command_day_status(
    session: Session,
    principal: PrincipalContext,
    diary_date: date,
    operation: str,
    expected_version: int,
    idempotency_key: str,
    authority: DiaryCalendarAuthority,
) -> tuple[DiaryDayStatusResponse, bool]:
    if not _KEY_RE.fullmatch(idempotency_key):
        raise _error(400, "INVALID_IDEMPOTENCY_KEY", "تعذر التحقق من الطلب. أعد المحاولة.")
    _future_guard(diary_date, authority)
    lock_owner(session, principal)
    row = _status_row(session, principal.principal_id, diary_date, lock=True)
    request_hash = _request_hash(
        operation, diary_date, expected_version, principal.principal_id
    )
    replay = session.exec(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == principal.principal_id,
            IdempotencyRecord.operation == f"diary_day_{operation}",
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    ).first()
    if replay is not None:
        if replay.request_hash != request_hash:
            raise _error(409, "IDEMPOTENCY_KEY_REUSED", "تعارض الطلب مع محاولة سابقة.")
        if replay.state == IdempotencyState.completed and replay.response_document:
            return DiaryDayStatusResponse.model_validate(replay.response_document), True
    version = row.version if row else 0
    if version != expected_version:
        current = _project(
            row,
            diary_date,
            row.entry_count if row else entry_count_for_day(session, principal.principal_id, diary_date),
            authority,
        )
        raise _error(
            409,
            "DAY_VERSION_CONFLICT",
            "تغيّرت بيانات اليوم. حدّث الصفحة ثم حاول مجددًا.",
            current=current.model_dump(mode="json", exclude={"calendar"}),
        )
    now = utcnow()
    count = row.entry_count if row else entry_count_for_day(session, principal.principal_id, diary_date)
    previous = row.status if row else None
    target = DiaryDayStatusValue.complete if operation == "complete" else DiaryDayStatusValue.partial
    current_status = (
        previous.value if isinstance(previous, DiaryDayStatusValue) else previous
    ) or ("partial" if count else "unregistered")
    if (operation == "complete" and current_status == "complete") or (
        operation == "reopen" and current_status != "complete"
    ):
        response = _project(row, diary_date, count, authority)
        session.add(
            IdempotencyRecord(
                principal_id=principal.principal_id,
                operation=f"diary_day_{operation}",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                state=IdempotencyState.completed,
                response_status=200,
                response_document=response.model_dump(mode="json"),
                resource_type="diary_day_status",
                resource_id=row.id if row else None,
                completed_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        session.commit()
        return response, False
    if row is None:
        row = DiaryDayStatus(
            principal_id=principal.principal_id,
            diary_date=diary_date,
            status=target,
            version=1,
            entry_count=count,
            completed_at=now if target == DiaryDayStatusValue.complete else None,
            reopened_at=now if operation == "reopen" else None,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
    else:
        row.status = target
        row.version += 1
        row.completed_at = now if target == DiaryDayStatusValue.complete else None
        if operation == "reopen":
            row.reopened_at = now
        row.updated_at = now
        session.add(row)
    session.add(
        DiaryDayStatusHistory(
            day_status_id=row.id,
            principal_id=principal.principal_id,
            diary_date=diary_date,
            from_status=previous,
            to_status=target,
            event_type=(DiaryDayStatusEvent.completed if operation == "complete" else DiaryDayStatusEvent.reopened),
            day_version=row.version,
            actor_principal_id=principal.principal_id,
            occurred_at=now,
        )
    )
    if operation == "reopen":
        # PLAN 032 consumes PLAN 031's owner/day lock order and appends lifecycle
        # evidence without changing the immutable analysis document.
        from app.services.pattern_analysis import append_stale_events_for_date

        append_stale_events_for_date(
            session,
            principal.principal_id,
            diary_date,
            "day_reopened",
            "completed_day_reopened",
            row.version,
        )
    else:
        from app.services.pattern_analysis import append_stale_events_for_date

        append_stale_events_for_date(
            session,
            principal.principal_id,
            diary_date,
            "day_version_changed",
            "day_completed",
            row.version,
        )
    response = _project(row, diary_date, count, authority)
    record = IdempotencyRecord(
        principal_id=principal.principal_id,
        operation=f"diary_day_{operation}",
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        state=IdempotencyState.completed,
        response_status=200,
        response_document=response.model_dump(mode="json"),
        resource_type="diary_day_status",
        resource_id=row.id,
        completed_at=now,
        expires_at=now + timedelta(days=7),
    )
    session.add(record)
    session.commit()
    return response, False
