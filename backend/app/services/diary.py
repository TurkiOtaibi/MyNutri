from datetime import date
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import DiaryEntry, Food
from app.schemas import (
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    NutritionTotals,
)
from app.services.food import get_active_food_for_logging, lock_food_namespace_for_logging
from app.services.snapshot import (
    _create_snapshot_v3_from_locked_food,
    normalized_snapshot,
    totals_from_versioned,
)
from app.services.target_plans import resolve_target_binding

DETAIL_FIELDS = (
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
)


def make_snapshot(food: Food, quantity: float | None = None) -> dict[str, Any]:
    snapshot = {
        "food_id": str(food.id),
        "name": food.name,
        "brand": food.brand,
        "category": food.food_category_key,
        "nutrition_basis": food.nutrition_basis.value,
        "default_unit_type": food.default_unit_type.value,
        "unit_amount": float(food.unit_amount),
        "unit_basis": food.unit_basis.value,
        "calories": float(food.calories),
        "protein_g": float(food.protein_g),
        "carb_g": float(food.carb_g),
        "fat_g": float(food.fat_g),
        "notes": food.notes,
        "data_source": food.data_source,
        "log_mode": "servings",
    }
    for field in DETAIL_FIELDS:
        value = getattr(food, field)
        snapshot[field] = None if value is None else float(value)
    if quantity is not None:
        snapshot["logged_quantity"] = float(quantity)
        snapshot["calculated_totals"] = totals_from_snapshot(snapshot, quantity).model_dump()
    return snapshot


def totals_from_snapshot(snapshot: dict[str, Any], quantity: float) -> NutritionTotals:
    calculated = snapshot.get("calculated_totals")
    logged_quantity = snapshot.get("logged_quantity")
    if (
        calculated is not None
        and logged_quantity is not None
        and float(logged_quantity) == float(quantity)
    ):
        return NutritionTotals.model_validate(calculated)

    if snapshot.get("nutrition_basis") in {"per_100g", "per_100ml"}:
        log_mode = snapshot.get("log_mode") or "servings"
        if log_mode == "grams":
            multiplier = float(quantity) / 100
        else:
            multiplier = (float(quantity) * float(snapshot.get("unit_amount") or 0)) / 100
    else:
        multiplier = float(quantity)

    carb_g = float(snapshot.get("carb_g") or 0) * multiplier
    fiber_g = snapshot.get("fiber_g")
    sugar_g = snapshot.get("sugar_g", snapshot.get("total_sugars_g"))
    totals: dict[str, Any] = {
        "calories": round(float(snapshot.get("calories") or 0) * multiplier, 2),
        "protein_g": round(float(snapshot.get("protein_g") or 0) * multiplier, 2),
        "carb_g": round(carb_g, 2),
        "fat_g": round(float(snapshot.get("fat_g") or 0) * multiplier, 2),
        "net_carbs_g": round(
            max(float(snapshot.get("carb_g") or 0) - float(fiber_g or 0), 0) * multiplier, 2
        ),
        "total_sugars_g": None if sugar_g is None else round(float(sugar_g) * multiplier, 2),
        "sugar_g": None if sugar_g is None else round(float(sugar_g) * multiplier, 2),
    }
    for field in DETAIL_FIELDS:
        value = snapshot.get(field)
        totals[field] = None if value is None else round(float(value) * multiplier, 2)
    return NutritionTotals.model_validate(totals)


def to_entry_response(entry: DiaryEntry) -> DiaryEntryResponse:
    snapshot = normalized_snapshot(entry.nutrition_snapshot, entry.snapshot_schema_version)
    return DiaryEntryResponse(
        id=entry.id,
        entry_date=entry.entry_date,
        food_id=entry.food_id,
        target_plan_id=entry.target_plan_id,
        target_provenance=entry.target_provenance,
        snapshot_schema_version=entry.snapshot_schema_version,
        quantity=float(entry.quantity),
        meal_type=entry.meal_type,
        nutrition_snapshot=snapshot,
        totals=totals_for_entry(entry),
        created_at=entry.created_at,
    )


def totals_for_entry(entry: DiaryEntry) -> NutritionTotals:
    if entry.snapshot_schema_version is None:
        normalized_snapshot(entry.nutrition_snapshot, None)
        return totals_from_snapshot(entry.nutrition_snapshot, float(entry.quantity))
    if entry.snapshot_schema_version in {2, 3}:
        return totals_from_versioned(
            entry.nutrition_snapshot,
            entry.snapshot_schema_version,
            float(entry.quantity),
        )
    normalized_snapshot(entry.nutrition_snapshot, entry.snapshot_schema_version)
    raise AssertionError("unreachable")


def list_entries(
    session: Session, principal: PrincipalContext, entry_date: date | None = None
) -> list[DiaryEntry]:
    statement = (
        select(DiaryEntry)
        .where(DiaryEntry.principal_id == principal.principal_id)
        .order_by(DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc())
    )
    if entry_date is not None:
        statement = statement.where(DiaryEntry.entry_date == entry_date)
    return list(session.exec(statement).all())


def get_entry(session: Session, principal: PrincipalContext, entry_id: UUID) -> DiaryEntry:
    entry = session.exec(
        select(DiaryEntry).where(
            DiaryEntry.id == entry_id,
            DiaryEntry.principal_id == principal.principal_id,
        )
    ).first()
    if entry is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return entry


def create_entry(
    session: Session,
    principal: PrincipalContext,
    payload: DiaryEntryCreate,
    *,
    snapshot_v3_writer_enabled: bool = True,
) -> DiaryEntry:
    lock_food_namespace_for_logging(session)
    binding = resolve_target_binding(session, principal, payload.entry_date)
    food = get_active_food_for_logging(session, principal, payload.food_id)
    if payload.id is not None:
        existing = session.get(DiaryEntry, payload.id)
        if existing is not None:
            if existing.principal_id != principal.principal_id:
                from app.services.errors import resource_not_found

                raise resource_not_found()
            if (
                existing.entry_date == payload.entry_date
                and existing.food_id == food.id
                and float(existing.quantity) == float(payload.quantity)
                and existing.meal_type == payload.meal_type
            ):
                session.rollback()
                return existing
            from fastapi import HTTPException

            session.rollback()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "DIARY_ENTRY_ID_CONFLICT",
                    "message_ar": "معرف اليومية مستخدم لمدخل مختلف.",
                },
            )

    entry_data = {
        "principal_id": principal.principal_id,
        "entry_date": payload.entry_date,
        "food_id": food.id,
        "quantity": payload.quantity,
        "meal_type": payload.meal_type,
        "target_plan_id": binding.plan.id if binding.plan else None,
        "target_provenance": binding.provenance,
        "snapshot_schema_version": 3 if snapshot_v3_writer_enabled else None,
        "nutrition_snapshot": (
            _create_snapshot_v3_from_locked_food(session, food)
            if snapshot_v3_writer_enabled
            else make_snapshot(food, payload.quantity)
        ),
    }
    if payload.id is not None:
        entry_data["id"] = payload.id
    entry = DiaryEntry(**entry_data)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def update_entry(
    session: Session,
    principal: PrincipalContext,
    entry_id: UUID,
    payload: DiaryEntryUpdate,
) -> DiaryEntry:
    entry = get_entry(session, principal, entry_id)
    if payload.quantity is not None:
        entry.quantity = payload.quantity
    if payload.meal_type is not None:
        entry.meal_type = payload.meal_type
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(session: Session, principal: PrincipalContext, entry_id: UUID) -> None:
    entry = get_entry(session, principal, entry_id)
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
