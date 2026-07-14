from datetime import date
from uuid import UUID

from typing import Any

from fastapi import APIRouter, Body, Depends, Response, status
from sqlmodel import Session

from app.core.auth import require_single_user
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

router = APIRouter(prefix="/diary", tags=["diary"], dependencies=[Depends(require_single_user)])


@router.get("", response_model=list[DiaryEntryResponse])
def read_entries(
    entry_date: date | None = None,
    session: Session = Depends(get_session),
) -> list[DiaryEntryResponse]:
    return [to_entry_response(entry) for entry in list_entries(session, entry_date)]


@router.get("/week", response_model=WeekSummary)
def read_week(start: date, session: Session = Depends(get_session)) -> WeekSummary:
    return weekly_summary(session, start)


@router.post("", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
def add_entry(payload: dict[str, Any] = Body(...), session: Session = Depends(get_session)) -> DiaryEntryResponse:
    return to_entry_response(create_entry(session, validate_diary_payload(DiaryEntryCreate, payload)))


@router.get("/{entry_id}", response_model=DiaryEntryResponse)
def read_entry(entry_id: UUID, session: Session = Depends(get_session)) -> DiaryEntryResponse:
    return to_entry_response(get_entry(session, entry_id))


@router.put("/{entry_id}", response_model=DiaryEntryResponse)
def edit_entry(
    entry_id: UUID,
    payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> DiaryEntryResponse:
    return to_entry_response(update_entry(session, entry_id, validate_diary_payload(DiaryEntryUpdate, payload)))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(entry_id: UUID, session: Session = Depends(get_session)) -> Response:
    delete_entry(session, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
