from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Food, utcnow
from app.schemas import FoodCreate, FoodResponse, FoodUpdate


def net_carbs(food: Food) -> float:
    fiber = float(food.fiber_g or 0)
    return round(float(food.carb_g) - fiber, 2)


def to_food_response(food: Food) -> FoodResponse:
    return FoodResponse(
        id=food.id,
        name=food.name,
        serving_label=food.serving_label,
        serving_grams=None if food.serving_grams is None else float(food.serving_grams),
        calories=float(food.calories),
        protein_g=float(food.protein_g),
        carb_g=float(food.carb_g),
        fat_g=float(food.fat_g),
        saturated_fat_g=None if food.saturated_fat_g is None else float(food.saturated_fat_g),
        trans_fat_g=None if food.trans_fat_g is None else float(food.trans_fat_g),
        cholesterol_mg=None if food.cholesterol_mg is None else float(food.cholesterol_mg),
        sodium_mg=None if food.sodium_mg is None else float(food.sodium_mg),
        fiber_g=None if food.fiber_g is None else float(food.fiber_g),
        total_sugars_g=None if food.total_sugars_g is None else float(food.total_sugars_g),
        added_sugar_g=None if food.added_sugar_g is None else float(food.added_sugar_g),
        net_carbs_g=net_carbs(food),
        created_at=food.created_at,
        updated_at=food.updated_at,
    )


def list_foods(session: Session, query: str | None = None) -> list[Food]:
    statement = select(Food).order_by(Food.name)
    if query:
        statement = statement.where(Food.name.ilike(f"%{query.strip()}%"))
    return list(session.exec(statement).all())


def get_food(session: Session, food_id: UUID) -> Food:
    food = session.get(Food, food_id)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found.")
    return food


def create_food(session: Session, payload: FoodCreate) -> Food:
    data = payload.model_dump()
    if payload.id is None:
        data.pop("id")
    else:
        existing = session.get(Food, payload.id)
        if existing is not None:
            for key, value in data.items():
                if key != "id":
                    setattr(existing, key, value)
            existing.updated_at = utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

    food = Food(**data)
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def update_food(session: Session, food_id: UUID, payload: FoodUpdate) -> Food:
    food = get_food(session, food_id)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(food, key, value)
    food.updated_at = utcnow()
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def delete_food(session: Session, food_id: UUID) -> None:
    food = get_food(session, food_id)
    session.delete(food)
    session.commit()
