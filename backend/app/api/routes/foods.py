from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session

from app.core.auth import require_single_user
from app.db.session import get_session
from app.schemas import FoodCreate, FoodResponse, FoodUpdate
from app.services.food import create_food, delete_food, get_food, list_foods, to_food_response, update_food

router = APIRouter(prefix="/foods", tags=["foods"], dependencies=[Depends(require_single_user)])


@router.get("", response_model=list[FoodResponse])
def read_foods(q: str | None = None, session: Session = Depends(get_session)) -> list[FoodResponse]:
    return [to_food_response(food) for food in list_foods(session, q)]


@router.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def add_food(payload: FoodCreate, session: Session = Depends(get_session)) -> FoodResponse:
    return to_food_response(create_food(session, payload))


@router.get("/{food_id}", response_model=FoodResponse)
def read_food(food_id: UUID, session: Session = Depends(get_session)) -> FoodResponse:
    return to_food_response(get_food(session, food_id))


@router.put("/{food_id}", response_model=FoodResponse)
def edit_food(food_id: UUID, payload: FoodUpdate, session: Session = Depends(get_session)) -> FoodResponse:
    return to_food_response(update_food(session, food_id, payload))


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_food(food_id: UUID, session: Session = Depends(get_session)) -> Response:
    delete_food(session, food_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
