from __future__ import annotations

import re
from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import Food, utcnow
from app.schemas import FoodCreate, FoodResponse, FoodSort, FoodUpdate
from app.services.food_validation_errors import duplicate_food_detail, food_validation_http_exception

FOOD_FIELDS = (
    "name",
    "brand",
    "category",
    "nutrition_basis",
    "default_unit_type",
    "unit_amount",
    "unit_basis",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "added_sugar_g",
    "saturated_fat_g",
    "trans_fat_g",
    "sodium_mg",
    "cholesterol_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "vitamin_d_mcg",
    "vitamin_b12_mcg",
    "vitamin_c_mg",
    "vitamin_a_mcg",
    "folate_mcg",
    "vitamin_k_mcg",
    "notes",
    "data_source",
)

UNCATEGORIZED_CATEGORY = "__uncategorized__"


@dataclass(frozen=True)
class FoodPage:
    items: list[Food]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]
    uncategorized_count: int

def net_carbs(food: Food) -> float:
    fiber = float(food.fiber_g or 0)
    return round(max(float(food.carb_g) - fiber, 0), 2)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _food_data(food: Food) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in FOOD_FIELDS:
        value = getattr(food, field)
        if field in {"nutrition_basis", "default_unit_type", "unit_basis"}:
            data[field] = _enum_value(value)
        elif isinstance(value, (int, float)) or value is not None and field.endswith(("_g", "_mg", "_mcg")):
            data[field] = _float_or_none(value)
        elif field in {"unit_amount", "calories", "protein_g", "carb_g", "fat_g"}:
            data[field] = float(value)
        else:
            data[field] = value
    return data


def to_food_response(food: Food) -> FoodResponse:
    return FoodResponse(
        id=food.id,
        **_food_data(food),
        net_carbs_g=net_carbs(food),
        created_at=food.created_at,
        updated_at=food.updated_at,
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def duplicate_key(data: dict[str, Any]) -> tuple[str, str, str, float, str]:
    return (
        normalize_text(str(data["name"])),
        str(_enum_value(data["nutrition_basis"])),
        str(_enum_value(data["default_unit_type"])),
        round(float(data["unit_amount"]), 4),
        str(_enum_value(data["unit_basis"])),
    )


def _duplicate_detail() -> list[dict[str, Any]]:
    return duplicate_food_detail()


def ensure_not_duplicate(
    session: Session,
    principal: PrincipalContext,
    data: dict[str, Any],
    food_id: UUID | None = None,
) -> None:
    target_key = duplicate_key(data)
    foods = session.exec(select(Food).where(Food.principal_id == principal.principal_id)).all()
    for food in foods:
        if food_id is not None and food.id == food_id:
            continue
        if duplicate_key(_food_data(food)) == target_key:
            raise HTTPException(status_code=422, detail=_duplicate_detail())


def _validated_update_data(food: Food, payload: FoodUpdate) -> dict[str, Any]:
    current = _food_data(food)
    updates = payload.model_dump(exclude_unset=True)
    current.update(updates)
    try:
        return FoodCreate.model_validate(current).model_dump(exclude={"id"})
    except ValidationError as error:
        raise food_validation_http_exception(error) from error


def list_foods(session: Session, principal: PrincipalContext, query: str | None = None) -> list[Food]:
    statement = select(Food).where(Food.principal_id == principal.principal_id).order_by(Food.name)
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        statement = statement.where(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))
    return list(session.exec(statement).all())


def list_foods_page(
    session: Session,
    principal: PrincipalContext,
    *,
    search: str | None = None,
    category: str | None = None,
    sort: FoodSort = "name",
    page: int = 1,
    page_size: int = 20,
) -> FoodPage:
    conditions = [Food.principal_id == principal.principal_id]
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        conditions.append(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))

    if category == UNCATEGORIZED_CATEGORY:
        conditions.append((Food.category.is_(None)) | (func.trim(Food.category) == ""))
    elif category:
        conditions.append(Food.category == category)

    count_statement = select(func.count()).select_from(Food)
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = int(session.exec(count_statement).one())

    statement = select(Food)
    if conditions:
        statement = statement.where(*conditions)

    serving_factor = Food.unit_amount / 100
    if sort == "recent":
        statement = statement.order_by(Food.created_at.desc(), Food.name)
    elif sort == "calories":
        statement = statement.order_by((Food.calories * serving_factor).desc(), Food.name)
    elif sort == "protein":
        statement = statement.order_by((Food.protein_g * serving_factor).desc(), Food.name)
    else:
        statement = statement.order_by(Food.name)

    statement = statement.offset((page - 1) * page_size).limit(page_size)
    items = list(session.exec(statement).all())

    category_rows = session.exec(
        select(Food.category).where(Food.principal_id == principal.principal_id)
    ).all()
    categories = sorted({value.strip() for value in category_rows if value and value.strip()}, key=str.casefold)
    uncategorized_count = sum(1 for value in category_rows if value is None or not value.strip())

    return FoodPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
        categories=categories,
        uncategorized_count=uncategorized_count,
    )


def get_food(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    food = session.exec(
        select(Food).where(Food.id == food_id, Food.principal_id == principal.principal_id)
    ).first()
    if food is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return food


def create_food(session: Session, principal: PrincipalContext, payload: FoodCreate) -> Food:
    data = payload.model_dump(exclude={"id"})
    if payload.id is not None:
        existing = session.get(Food, payload.id)
        if existing is not None:
            if existing.principal_id != principal.principal_id:
                from app.services.errors import resource_not_found

                raise resource_not_found()
            ensure_not_duplicate(session, principal, data, food_id=existing.id)
            return update_food(session, principal, existing.id, FoodUpdate.model_validate(data))
        data["id"] = payload.id

    ensure_not_duplicate(session, principal, data)
    food = Food(principal_id=principal.principal_id, **data)
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def update_food(
    session: Session, principal: PrincipalContext, food_id: UUID, payload: FoodUpdate
) -> Food:
    food = get_food(session, principal, food_id)
    data = _validated_update_data(food, payload)
    ensure_not_duplicate(session, principal, data, food_id=food.id)
    for key, value in data.items():
        setattr(food, key, value)
    food.updated_at = utcnow()
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def delete_food(session: Session, principal: PrincipalContext, food_id: UUID) -> None:
    food = get_food(session, principal, food_id)
    session.delete(food)
    session.commit()
