from datetime import date
from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status
from pydantic import SkipValidation
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.schemas import (
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    WeekSummary,
)
from app.services.aggregation import weekly_summary
from app.services.diary import (
    create_entry_response,
    delete_entry,
    list_entries,
    to_entry_response,
    update_entry_response,
)
from app.services.diary_validation_errors import validate_diary_payload

router = APIRouter(prefix="/diary", tags=["diary"])


@router.get("/entries", response_model=list[DiaryEntryResponse])
def read_entries(
    entry_date: date | None = None,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> list[DiaryEntryResponse]:
    return [
        to_entry_response(entry, food)
        for entry, food in list_entries(session, principal, entry_date)
    ]


@router.get("/week", response_model=WeekSummary)
def read_week(
    start: date,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> WeekSummary:
    return weekly_summary(session, principal, start)


def _add_entry(
    payload: Annotated[SkipValidation[DiaryEntryCreate], Body()],
    principal: PrincipalContext,
    session: Session,
) -> DiaryEntryResponse:
    validated_payload = validate_diary_payload(DiaryEntryCreate, payload)
    return create_entry_response(session, principal, validated_payload)


@router.post("/entries", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
def add_entry(
    payload: Annotated[SkipValidation[DiaryEntryCreate], Body()],
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _add_entry(payload, principal, session)


def _edit_entry(
    entry_id: UUID,
    payload: Annotated[SkipValidation[DiaryEntryUpdate], Body()],
    principal: PrincipalContext,
    session: Session,
) -> DiaryEntryResponse:
    return update_entry_response(
        session,
        principal,
        entry_id,
        validate_diary_payload(DiaryEntryUpdate, payload),
    )


@router.patch("/entries/{entry_id}", response_model=DiaryEntryResponse)
def edit_entry(
    entry_id: UUID,
    payload: Annotated[SkipValidation[DiaryEntryUpdate], Body()],
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return _edit_entry(entry_id, payload, principal, session)


def remove_entry(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    delete_entry(session, principal, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry_documented(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    return remove_entry(entry_id, principal, session)
