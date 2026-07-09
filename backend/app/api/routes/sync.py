from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import require_single_user
from app.db.session import get_session
from app.schemas import (
    DiaryEntryCreate,
    DiaryEntryUpdate,
    FoodCreate,
    FoodUpdate,
    ProfileUpsert,
    SyncOperation,
    SyncPushRequest,
    SyncPushResponse,
)
from app.services.diary import create_entry, delete_entry, list_entries, to_entry_response, update_entry
from app.services.food import create_food, delete_food, list_foods, to_food_response, update_food
from app.services.profile import get_profile, to_profile_response, upsert_profile

router = APIRouter(prefix="/sync", tags=["sync"], dependencies=[Depends(require_single_user)])


@router.get("/pull")
def pull(session: Session = Depends(get_session)) -> dict[str, object]:
    profile = get_profile(session)
    return {
        "profile": None if profile is None else to_profile_response(profile),
        "foods": [to_food_response(food) for food in list_foods(session)],
        "diary_entries": [to_entry_response(entry) for entry in list_entries(session)],
    }


@router.post("/push", response_model=SyncPushResponse)
def push(payload: SyncPushRequest, session: Session = Depends(get_session)) -> SyncPushResponse:
    accepted = 0
    accepted_client_ids: list[str] = []
    rejected: list[dict[str, object]] = []

    for operation in payload.operations:
        try:
            apply_operation(session, operation)
            accepted += 1
            if operation.client_id is not None:
                accepted_client_ids.append(operation.client_id)
        except Exception as exc:
            session.rollback()
            rejected.append(
                {
                    "method": operation.method,
                    "path": operation.path,
                    "client_id": operation.client_id,
                    "error": str(exc),
                }
            )

    return SyncPushResponse(
        accepted=accepted,
        accepted_client_ids=accepted_client_ids,
        rejected=rejected,
    )


def apply_operation(session: Session, operation: SyncOperation) -> None:
    method = operation.method.upper()
    path = operation.path.rstrip("/") or "/"
    body = operation.body or {}

    if method == "PUT" and path == "/profile":
        upsert_profile(session, ProfileUpsert.model_validate(body))
        return

    if method == "POST" and path == "/foods":
        create_food(session, FoodCreate.model_validate(body))
        return

    if path.startswith("/foods/"):
        food_id = UUID(path.removeprefix("/foods/"))
        if method == "PUT":
            update_food(session, food_id, FoodUpdate.model_validate(body))
            return
        if method == "DELETE":
            delete_food_if_present(session, food_id)
            return

    if method == "POST" and path == "/diary":
        create_entry(session, DiaryEntryCreate.model_validate(body))
        return

    if path.startswith("/diary/"):
        entry_id = UUID(path.removeprefix("/diary/"))
        if method == "PUT":
            update_entry(session, entry_id, DiaryEntryUpdate.model_validate(body))
            return
        if method == "DELETE":
            delete_entry_if_present(session, entry_id)
            return

    raise ValueError(f"Unsupported sync operation: {method} {path}")


def delete_food_if_present(session: Session, food_id: UUID) -> None:
    try:
        delete_food(session, food_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise


def delete_entry_if_present(session: Session, entry_id: UUID) -> None:
    try:
        delete_entry(session, entry_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
