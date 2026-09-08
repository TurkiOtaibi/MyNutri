from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime, timezone
import binascii
import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import DiaryCalendarAuthority, diary_calendar_authority
from app.models import DiaryDayStatusEvent, DiaryEntry, Food
from app.schemas import (
    DiaryEntryCreate,
    DiaryFoodReference,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    AdminDiaryItem,
    AdminDiaryPage,
    NutritionTotals,
)
from app.services.food import get_active_food_for_logging, lock_food_namespace_for_logging
from app.services.target_plans import resolve_target_binding
from app.services.day_logging_status import (
    entry_count_for_day,
    lock_day_for_entry,
    lock_owner,
    record_entry_mutation,
)

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
    "vitamin_a_rae_mcg",
    "folate_mcg",
    "folate_dfe_mcg",
    "vitamin_k_mcg",
    "iodine_mcg",
)


class AdminDiaryCursorError(ValueError):
    pass


def _diary_integrity_error(code: str, message_ar: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message_ar": message_ar})


def get_food_for_entry(session: Session, entry: DiaryEntry) -> Food:
    food = session.get(Food, entry.food_id)
    if food is None:
        raise _diary_integrity_error(
            "DIARY_FOOD_REFERENCE_BROKEN",
            "تعذر قراءة اليومية لأن مرجع الطعام غير صالح.",
        )
    return food


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def totals_for_entry(entry: DiaryEntry, food: Food) -> NutritionTotals:
    expected_basis = "g" if _enum_value(food.nutrition_basis) == "per_100g" else "ml"
    if _enum_value(entry.recorded_unit_basis) != expected_basis:
        raise _diary_integrity_error(
            "DIARY_MEASUREMENT_DIMENSION_MISMATCH",
            "تعذر حساب اليومية لاختلاف وحدة القياس المسجلة عن أساس الطعام الحالي.",
        )

    multiplier = float(entry.quantity) * float(entry.recorded_unit_amount) / 100
    fiber_g = food.fiber_g
    sugar_g = food.sugar_g
    totals: dict[str, Any] = {
        "calories": round(float(food.calories) * multiplier, 2),
        "protein_g": round(float(food.protein_g) * multiplier, 2),
        "carb_g": round(float(food.carb_g) * multiplier, 2),
        "fat_g": round(float(food.fat_g) * multiplier, 2),
        "net_carbs_g": round(
            max(float(food.carb_g) - float(fiber_g or 0), 0) * multiplier, 2
        ),
        "total_sugars_g": None if sugar_g is None else round(float(sugar_g) * multiplier, 2),
        "sugar_g": None if sugar_g is None else round(float(sugar_g) * multiplier, 2),
    }
    for field in DETAIL_FIELDS:
        value = getattr(food, field)
        totals[field] = None if value is None else round(float(value) * multiplier, 2)
    return NutritionTotals.model_validate(totals)


def to_entry_response(entry: DiaryEntry, food: Food) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        id=entry.id,
        entry_date=entry.entry_date,
        food_id=entry.food_id,
        target_plan_id=entry.target_plan_id,
        target_provenance=entry.target_provenance,
        quantity=float(entry.quantity),
        recorded_unit_type=entry.recorded_unit_type,
        recorded_unit_amount=float(entry.recorded_unit_amount),
        recorded_unit_basis=entry.recorded_unit_basis,
        recorded_unit_label=entry.recorded_unit_label,
        meal_type=entry.meal_type,
        food=DiaryFoodReference(id=food.id, name=food.name, brand=food.brand),
        totals=totals_for_entry(entry, food),
        created_at=entry.created_at,
    )


def list_entries(
    session: Session, principal: PrincipalContext, entry_date: date | None = None
) -> list[tuple[DiaryEntry, Food]]:
    statement = (
        select(DiaryEntry, Food)
        .join(Food, Food.id == DiaryEntry.food_id)
        .where(DiaryEntry.principal_id == principal.principal_id)
        .order_by(DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc())
    )
    if entry_date is not None:
        statement = statement.where(DiaryEntry.entry_date == entry_date)
    return list(session.exec(statement).all())


def _encode_admin_diary_cursor(entry_date: date, created_at: datetime, entry_id: UUID) -> str:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = json.dumps(
        {
            "entry_date": entry_date.isoformat(),
            "created_at": created_at.isoformat(),
            "id": str(entry_id),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_admin_diary_cursor(cursor: str) -> tuple[date, datetime, UUID]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not cursor or any(character not in alphabet for character in cursor):
        raise AdminDiaryCursorError("invalid cursor")
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(urlsafe_b64decode(cursor + padding).decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"entry_date", "created_at", "id"}:
            raise ValueError("unexpected cursor shape")
        if not all(isinstance(payload[key], str) for key in ("entry_date", "created_at", "id")):
            raise ValueError("invalid cursor types")
        entry_date = date.fromisoformat(payload["entry_date"])
        created_at = datetime.fromisoformat(payload["created_at"])
        entry_id = UUID(payload["id"])
        if (
            entry_date.isoformat() != payload["entry_date"]
            or created_at.isoformat() != payload["created_at"]
            or created_at.tzinfo is None
            or created_at.utcoffset() is None
            or str(entry_id) != payload["id"]
        ):
            raise ValueError("non-canonical cursor")
        return entry_date, created_at, entry_id
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        raise AdminDiaryCursorError("invalid cursor") from error


def admin_diary_page(
    session: Session,
    principal: PrincipalContext,
    limit: int,
    cursor: str | None = None,
    entry_date: date | None = None,
) -> AdminDiaryPage:
    statement = select(
        DiaryEntry.id,
        DiaryEntry.entry_date,
        DiaryEntry.meal_type,
        DiaryEntry.quantity,
        Food.name.label("food_name"),
        DiaryEntry.created_at,
    ).join(Food, Food.id == DiaryEntry.food_id).where(
        DiaryEntry.principal_id == principal.principal_id
    )
    if entry_date is not None:
        statement = statement.where(DiaryEntry.entry_date == entry_date)
    if cursor is not None:
        cursor_entry_date, cursor_created_at, cursor_entry_id = _decode_admin_diary_cursor(cursor)
        statement = statement.where(
            tuple_(DiaryEntry.entry_date, DiaryEntry.created_at, DiaryEntry.id)
            < tuple_(
                cursor_entry_date,
                cursor_created_at,
                cursor_entry_id,
            )
        )
    rows = session.exec(
        statement.order_by(
            DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc(), DiaryEntry.id.desc()
        ).limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return AdminDiaryPage(
        items=[
            AdminDiaryItem(
                id=row.id,
                entry_date=row.entry_date,
                meal_type=row.meal_type,
                quantity=float(row.quantity),
                food_name=row.food_name,
            )
            for row in items
        ],
        next_cursor=(
            _encode_admin_diary_cursor(items[-1].entry_date, items[-1].created_at, items[-1].id)
            if has_more
            else None
        ),
    )


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
    expected_day_version: int | None = None,
    calendar_authority: DiaryCalendarAuthority | None = None,
) -> DiaryEntry:
    if payload.id is not None:
        existing = session.get(DiaryEntry, payload.id)
        if existing is not None:
            if existing.principal_id != principal.principal_id:
                from app.services.errors import resource_not_found

                raise resource_not_found()
            if (
                existing.entry_date == payload.entry_date
                and existing.food_id == payload.food_id
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
    authority = calendar_authority or diary_calendar_authority()
    lock_owner(session, principal)
    binding = resolve_target_binding(
        session,
        principal,
        payload.entry_date,
        authoritative_current_date=authority.current_diary_date,
    )
    day = lock_day_for_entry(
        session, principal, payload.entry_date, expected_day_version, authority
    )
    lock_food_namespace_for_logging(session)
    food = get_active_food_for_logging(session, principal, payload.food_id)
    entry_data = {
        "principal_id": principal.principal_id,
        "entry_date": payload.entry_date,
        "food_id": food.id,
        "quantity": payload.quantity,
        "recorded_unit_type": food.default_unit_type,
        "recorded_unit_amount": food.unit_amount,
        "recorded_unit_basis": food.unit_basis,
        "recorded_unit_label": None,
        "meal_type": payload.meal_type,
        "target_plan_id": binding.plan.id if binding.plan else None,
        "target_provenance": binding.provenance,
    }
    if payload.id is not None:
        entry_data["id"] = payload.id
    entry = DiaryEntry(**entry_data)
    session.add(entry)
    session.flush()
    previous_count = (
        day.entry_count
        if day
        else entry_count_for_day(session, principal.principal_id, payload.entry_date) - 1
    )
    record_entry_mutation(
        session,
        principal,
        payload.entry_date,
        day,
        DiaryDayStatusEvent.entry_created,
        entry.id,
        previous_count + 1,
    )
    session.commit()
    session.refresh(entry)
    return entry


def update_entry(
    session: Session,
    principal: PrincipalContext,
    entry_id: UUID,
    payload: DiaryEntryUpdate,
    *,
    expected_day_version: int | None = None,
    calendar_authority: DiaryCalendarAuthority | None = None,
) -> DiaryEntry:
    entry = get_entry(session, principal, entry_id)
    authority = calendar_authority or diary_calendar_authority()
    lock_owner(session, principal)
    day = lock_day_for_entry(session, principal, entry.entry_date, expected_day_version, authority)
    entry = session.exec(
        select(DiaryEntry)
        .where(
            DiaryEntry.id == entry_id,
            DiaryEntry.principal_id == principal.principal_id,
        )
        .with_for_update()
    ).one()
    current_count = (
        day.entry_count
        if day
        else entry_count_for_day(session, principal.principal_id, entry.entry_date)
    )
    if payload.quantity is not None:
        entry.quantity = payload.quantity
    if payload.meal_type is not None:
        entry.meal_type = payload.meal_type
    session.add(entry)
    record_entry_mutation(
        session,
        principal,
        entry.entry_date,
        day,
        DiaryDayStatusEvent.entry_edited,
        entry.id,
        current_count,
    )
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(
    session: Session,
    principal: PrincipalContext,
    entry_id: UUID,
    *,
    expected_day_version: int | None = None,
    calendar_authority: DiaryCalendarAuthority | None = None,
) -> None:
    entry = get_entry(session, principal, entry_id)
    authority = calendar_authority or diary_calendar_authority()
    lock_owner(session, principal)
    day = lock_day_for_entry(session, principal, entry.entry_date, expected_day_version, authority)
    entry = session.exec(
        select(DiaryEntry)
        .where(
            DiaryEntry.id == entry_id,
            DiaryEntry.principal_id == principal.principal_id,
        )
        .with_for_update()
    ).one()
    diary_date = entry.entry_date
    current_count = (
        day.entry_count if day else entry_count_for_day(session, principal.principal_id, diary_date)
    )
    remaining = max(current_count - 1, 0)
    session.delete(entry)
    record_entry_mutation(
        session,
        principal,
        diary_date,
        day,
        DiaryDayStatusEvent.entry_deleted,
        entry.id,
        remaining,
    )
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
