from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import DiaryEntry, Food
from app.schemas import (
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    NutritionSnapshot,
    NutritionTotals,
)
from app.services.food import get_food

DETAIL_FIELDS = (
    "saturated_fat_g",
    "trans_fat_g",
    "cholesterol_mg",
    "sodium_mg",
    "fiber_g",
    "total_sugars_g",
    "added_sugar_g",
)


def make_snapshot(food: Food) -> dict[str, Any]:
    snapshot = {
        "food_id": str(food.id),
        "name": food.name,
        "serving_label": food.serving_label,
        "serving_grams": None if food.serving_grams is None else float(food.serving_grams),
        "calories": float(food.calories),
        "protein_g": float(food.protein_g),
        "carb_g": float(food.carb_g),
        "fat_g": float(food.fat_g),
    }
    for field in DETAIL_FIELDS:
        value = getattr(food, field)
        snapshot[field] = None if value is None else float(value)
    return snapshot


def totals_from_snapshot(snapshot: dict[str, Any], quantity: float) -> NutritionTotals:
    multiplier = float(quantity)
    carb_g = float(snapshot.get("carb_g") or 0) * multiplier
    fiber_g = snapshot.get("fiber_g")
    totals: dict[str, Any] = {
        "calories": round(float(snapshot.get("calories") or 0) * multiplier, 2),
        "protein_g": round(float(snapshot.get("protein_g") or 0) * multiplier, 2),
        "carb_g": round(carb_g, 2),
        "fat_g": round(float(snapshot.get("fat_g") or 0) * multiplier, 2),
        "net_carbs_g": round((float(snapshot.get("carb_g") or 0) - float(fiber_g or 0)) * multiplier, 2),
    }
    for field in DETAIL_FIELDS:
        value = snapshot.get(field)
        totals[field] = None if value is None else round(float(value) * multiplier, 2)
    return NutritionTotals.model_validate(totals)


def to_entry_response(entry: DiaryEntry) -> DiaryEntryResponse:
    snapshot = NutritionSnapshot.model_validate(entry.nutrition_snapshot)
    return DiaryEntryResponse(
        id=entry.id,
        entry_date=entry.entry_date,
        food_id=entry.food_id,
        quantity=float(entry.quantity),
        nutrition_snapshot=snapshot,
        totals=totals_from_snapshot(entry.nutrition_snapshot, float(entry.quantity)),
        created_at=entry.created_at,
    )


def list_entries(session: Session, entry_date: date | None = None) -> list[DiaryEntry]:
    statement = select(DiaryEntry).order_by(DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc())
    if entry_date is not None:
        statement = statement.where(DiaryEntry.entry_date == entry_date)
    return list(session.exec(statement).all())


def get_entry(session: Session, entry_id: UUID) -> DiaryEntry:
    entry = session.get(DiaryEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found.")
    return entry


def create_entry(session: Session, payload: DiaryEntryCreate) -> DiaryEntry:
    food = get_food(session, payload.food_id)
    if payload.id is not None:
        existing = session.get(DiaryEntry, payload.id)
        if existing is not None:
            existing.entry_date = payload.entry_date
            existing.food_id = food.id
            existing.quantity = payload.quantity
            existing.nutrition_snapshot = make_snapshot(food)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

    entry_data = {
        "entry_date": payload.entry_date,
        "food_id": food.id,
        "quantity": payload.quantity,
        "nutrition_snapshot": make_snapshot(food),
    }
    if payload.id is not None:
        entry_data["id"] = payload.id
    entry = DiaryEntry(**entry_data)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def update_entry(session: Session, entry_id: UUID, payload: DiaryEntryUpdate) -> DiaryEntry:
    entry = get_entry(session, entry_id)
    updates = payload.model_dump(exclude_unset=True)
    if "food_id" in updates and updates["food_id"] is not None:
        food = get_food(session, updates["food_id"])
        entry.food_id = food.id
        entry.nutrition_snapshot = make_snapshot(food)
    if "entry_date" in updates and updates["entry_date"] is not None:
        entry.entry_date = updates["entry_date"]
    if "quantity" in updates and updates["quantity"] is not None:
        entry.quantity = updates["quantity"]

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(session: Session, entry_id: UUID) -> None:
    entry = get_entry(session, entry_id)
    session.delete(entry)
    session.commit()


def empty_totals() -> NutritionTotals:
    return NutritionTotals()


def add_totals(left: NutritionTotals, right: NutritionTotals) -> NutritionTotals:
    data = left.model_dump()
    other = right.model_dump()
    for key, value in other.items():
        if value is None:
            continue
        data[key] = round(float(data.get(key) or 0) + float(value), 2)
    return NutritionTotals.model_validate(data)
