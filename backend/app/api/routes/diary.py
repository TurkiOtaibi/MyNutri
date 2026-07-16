from datetime import date
from uuid import UUID

from typing import Any

from fastapi import APIRouter, Body, Depends, Response, status
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.schemas import DiaryEntryCreate, DiaryEntryResponse, DiaryEntryUpdate, WeekSummary
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

router = APIRouter(prefix="/diary", tags=["diary"])


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


@router.post("/entries", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def add_entry(
    payload: dict[str, Any] = Body(...),
    principal: PrincipalContext = Depends(get_principal_context),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return to_entry_response(
        create_entry(
            session,
            principal,
            validate_diary_payload(DiaryEntryCreate, payload),
            snapshot_v2_writer_enabled=settings.snapshot_v2_writer_enabled,
        )
    )


@router.get("/entries/{entry_id}", response_model=DiaryEntryResponse)
@router.get("/{entry_id}", response_model=DiaryEntryResponse, include_in_schema=False)
def read_entry(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return to_entry_response(get_entry(session, principal, entry_id))


@router.patch("/entries/{entry_id}", response_model=DiaryEntryResponse)
@router.put("/{entry_id}", response_model=DiaryEntryResponse, include_in_schema=False)
def edit_entry(
    entry_id: UUID,
    payload: dict[str, Any] = Body(...),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return to_entry_response(
        update_entry(
            session,
            principal,
            entry_id,
            validate_diary_payload(DiaryEntryUpdate, payload),
        )
    )


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def remove_entry(
    entry_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    delete_entry(session, principal, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
