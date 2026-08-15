from datetime import date
from uuid import UUID, uuid4

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response, status
from pydantic import SkipValidation
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.core.calendar import diary_calendar_authority
from app.schemas import (
    DiaryDayStatusCommand,
    DiaryDayStatusResponse,
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    WeekSummary,
    reset_diary_validation_date,
    set_diary_validation_date,
)
from app.services.aggregation import weekly_summary
from app.services.diary import (
    create_entry,
    delete_entry,
    get_entry,
    list_entries,
    to_entry_response,
    update_entry,
)
from app.services.diary_validation_errors import validate_diary_payload
from app.services.day_logging_status import command_day_status, project_day_status

router = APIRouter(prefix="/diary", tags=["diary"])


def _expected_version(if_match: str | None) -> int | None:
    if if_match is None:
        return None
    value = if_match.strip().strip('"')
    if not value.startswith("day-") or not value[4:].isdigit():
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message_ar": "صيغة إصدار اليوم غير صالحة."},
        )
    return int(value[4:])


@router.get("/entries", response_model=list[DiaryEntryResponse])
@router.get("", response_model=list[DiaryEntryResponse], include_in_schema=False)
def read_entries(
    entry_date: date | None = None,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> list[DiaryEntryResponse]:
    return [to_entry_response(entry) for entry in list_entries(session, principal, entry_date)]


@router.get("/week", response_model=WeekSummary)
def read_week(
    start: date,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> WeekSummary:
    return weekly_summary(session, principal, start)


def _add_entry(
    payload: Annotated[SkipValidation[DiaryEntryCreate], Body()],
    response: Response,
    if_match: str | None,
    principal: PrincipalContext,
    settings: Settings,
    session: Session,
) -> DiaryEntryResponse:
    authority = diary_calendar_authority()
    validation_token = set_diary_validation_date(authority.current_diary_date)
    try:
        validated_payload = validate_diary_payload(DiaryEntryCreate, payload)
    finally:
        reset_diary_validation_date(validation_token)
    entry = create_entry(
        session,
        principal,
        validated_payload,
        snapshot_v3_writer_enabled=settings.snapshot_v3_writer_enabled,
        expected_day_version=_expected_version(if_match),
        calendar_authority=authority,
    )
    day = project_day_status(session, principal, entry.entry_date, authority)
    response.headers["ETag"] = f'"day-{day.logging_status_version}"'
    return to_entry_response(entry)


@router.post("/entries", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
def add_entry(
    payload: Annotated[SkipValidation[DiaryEntryCreate], Body()],
    response: Response,
    if_match: str = Header(alias="If-Match"),
    principal: PrincipalContext = Depends(get_principal_context),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _add_entry(payload, response, if_match, principal, settings, session)


@router.post(
    "", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
def add_entry_legacy(
    payload: Annotated[SkipValidation[DiaryEntryCreate], Body()],
    response: Response,
    principal: PrincipalContext = Depends(get_principal_context),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _add_entry(payload, response, None, principal, settings, session)


@router.get("/entries/{entry_id}", response_model=DiaryEntryResponse)
@router.get("/{entry_id}", response_model=DiaryEntryResponse, include_in_schema=False)
def read_entry(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return to_entry_response(get_entry(session, principal, entry_id))


def _edit_entry(
    entry_id: UUID,
    payload: Annotated[SkipValidation[DiaryEntryUpdate], Body()],
    response: Response,
    if_match: str | None,
    principal: PrincipalContext,
    session: Session,
) -> DiaryEntryResponse:
    authority = diary_calendar_authority()
    entry = update_entry(
        session,
        principal,
        entry_id,
        validate_diary_payload(DiaryEntryUpdate, payload),
        expected_day_version=_expected_version(if_match),
        calendar_authority=authority,
    )
    day = project_day_status(session, principal, entry.entry_date, authority)
    response.headers["ETag"] = f'"day-{day.logging_status_version}"'
    return to_entry_response(entry)


@router.patch("/entries/{entry_id}", response_model=DiaryEntryResponse)
def edit_entry(
    entry_id: UUID,
    payload: Annotated[SkipValidation[DiaryEntryUpdate], Body()],
    response: Response,
    if_match: str = Header(alias="If-Match"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _edit_entry(entry_id, payload, response, if_match, principal, session)


@router.put("/{entry_id}", response_model=DiaryEntryResponse, include_in_schema=False)
def edit_entry_legacy(
    entry_id: UUID,
    payload: Annotated[SkipValidation[DiaryEntryUpdate], Body()],
    response: Response,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _edit_entry(entry_id, payload, response, None, principal, session)


def remove_entry(
    entry_id: UUID,
    if_match: str | None,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    delete_entry(
        session,
        principal,
        entry_id,
        expected_day_version=_expected_version(if_match),
        calendar_authority=diary_calendar_authority(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry_documented(
    entry_id: UUID,
    if_match: str = Header(alias="If-Match"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    return remove_entry(entry_id, if_match, principal, session)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def remove_entry_legacy(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    return remove_entry(entry_id, None, principal, session)


@router.get("/days/{diary_date}/status", response_model=DiaryDayStatusResponse)
def read_day_status(
    diary_date: date,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryDayStatusResponse:
    authority = diary_calendar_authority()
    return project_day_status(session, principal, diary_date, authority)


def _day_command(
    diary_date: date,
    operation: str,
    payload: DiaryDayStatusCommand,
    idempotency_key: str,
    principal: PrincipalContext,
    session: Session,
    response: Response,
) -> DiaryDayStatusResponse:
    try:
        result, replayed = command_day_status(
            session,
            principal,
            diary_date,
            operation,
            payload.expected_version,
            idempotency_key,
            diary_calendar_authority(),
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as error:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DAY_STATUS_WRITE_FAILED",
                "message_ar": "تعذر حفظ حالة اليوم. لم تُفقد بياناتك؛ حاول مجددًا.",
                "request_id": str(uuid4()),
            },
        ) from error
    response.headers["ETag"] = f'"day-{result.logging_status_version}"'
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return result


@router.put("/days/{diary_date}/complete", response_model=DiaryDayStatusResponse)
def complete_day(
    diary_date: date,
    payload: DiaryDayStatusCommand,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryDayStatusResponse:
    return _day_command(
        diary_date, "complete", payload, idempotency_key, principal, session, response
    )


@router.put("/days/{diary_date}/reopen", response_model=DiaryDayStatusResponse)
def reopen_day(
    diary_date: date,
    payload: DiaryDayStatusCommand,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryDayStatusResponse:
    return _day_command(
        diary_date, "reopen", payload, idempotency_key, principal, session, response
    )
