from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Response, status
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context, require_admin
from app.models import FoodStatus
from app.db.session import get_session
from app.schemas import FoodCreate, FoodDeleteResponse, FoodListResponse, FoodResponse, FoodSort, FoodUpdate
from app.services.food import (
    archive_food,
    create_food,
    delete_food,
    get_food,
    list_foods,
    list_foods_page,
    restore_food,
    to_food_response,
    update_food,
)
from app.services.food_validation_errors import validate_food_payload

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=list[FoodResponse] | FoodListResponse)
def read_foods(
    q: str | None = None,
    search: str | None = None,
    category: str | None = None,
    sort: FoodSort = "name",
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> list[FoodResponse] | FoodListResponse:
    # Preserve the original list response for Diary and existing API consumers.
    if page is None and search is None and category is None and sort == "name":
        return [
            to_food_response(session, principal, food) for food in list_foods(session, principal, q)
        ]

    result = list_foods_page(
        session,
        principal,
        search=search if search is not None else q,
        category=category,
        sort=sort,
        page=page or 1,
        page_size=page_size,
    )
    return FoodListResponse(
        items=[to_food_response(session, principal, food) for food in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        categories=result.categories,
        uncategorized_count=result.uncategorized_count,
    )


@router.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def add_food(
    payload: dict[str, Any] = Body(...),
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodResponse:
    food_payload = validate_food_payload(FoodCreate, payload)
    return to_food_response(session, principal, create_food(session, principal, food_payload))


@router.get("/{food_id}", response_model=FoodResponse)
def read_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> FoodResponse:
    return to_food_response(session, principal, get_food(session, principal, food_id))


@router.put("/{food_id}", response_model=FoodResponse)
def edit_food(
    food_id: UUID,
    payload: dict[str, Any] = Body(...),
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodResponse:
    food_payload = validate_food_payload(FoodUpdate, payload)
    return to_food_response(
        session, principal, update_food(session, principal, food_id, food_payload)
    )


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Response:
    delete_food(session, principal, food_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


admin_router = APIRouter(prefix="/admin/foods", tags=["admin-foods"])


@admin_router.get("", response_model=FoodListResponse)
def read_admin_foods(
    search: str | None = None,
    category: str | None = None,
    food_status: FoodStatus | None = Query(default=None, alias="status"),
    sort: FoodSort = "name",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodListResponse:
    result = list_foods_page(
        session,
        principal,
        search=search,
        category=category,
        status=food_status,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return FoodListResponse(
        items=[to_food_response(session, principal, food) for food in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        categories=result.categories,
        uncategorized_count=result.uncategorized_count,
    )


@admin_router.get("/{food_id}", response_model=FoodResponse)
def read_admin_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodResponse:
    return to_food_response(
        session, principal, get_food(session, principal, food_id, include_archived=True)
    )


@admin_router.delete("/{food_id}", response_model=FoodDeleteResponse)
def delete_admin_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodDeleteResponse:
    deleted = delete_food(session, principal, food_id)
    return FoodDeleteResponse(disposition="deleted" if deleted else "archived")


@admin_router.post("/{food_id}/archive", response_model=FoodResponse)
def archive_admin_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodResponse:
    return to_food_response(session, principal, archive_food(session, principal, food_id))


@admin_router.post("/{food_id}/restore", response_model=FoodResponse)
def restore_admin_food(
    food_id: UUID,
    principal: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> FoodResponse:
    return to_food_response(session, principal, restore_food(session, principal, food_id))
