from __future__ import annotations

import json
import re
from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, text
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import (
    DiaryEntry,
    Food,
    Principal,
    utcnow,
)
from app.schemas import (
    FoodCreate,
    FoodPickerItem,
    FoodPickerResponse,
    FoodResponse,
    FoodSort,
    FoodUpdate,
)
from app.services.food_validation_errors import (
    duplicate_food_detail,
    food_validation_http_exception,
)

FOOD_FIELDS = (
    "name",
    "brand",
    "primary_category",
    "subcategory",
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
    "selenium_mcg",
    "vitamin_d_mcg",
    "vitamin_b12_mcg",
    "vitamin_c_mg",
    "vitamin_a_mcg",
    "vitamin_a_rae_mcg",
    "folate_mcg",
    "folate_dfe_mcg",
    "vitamin_k_mcg",
    "iodine_mcg",
    "notes",
    "nutrition_data_source",
    "ingredients",
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


PICKER_COLUMNS = (
    Food.id,
    Food.name,
    Food.brand,
    Food.nutrition_basis,
    Food.default_unit_type,
    Food.unit_amount,
    Food.unit_basis,
    Food.calories,
    Food.protein_g,
    Food.carb_g,
    Food.fat_g,
)


def _picker_item(row: Any) -> FoodPickerItem:
    return FoodPickerItem.model_validate(dict(zip(FoodPickerItem.model_fields, row, strict=True)))


def _encode_picker_cursor(sort_name: str, item_id: UUID) -> str:
    payload = json.dumps(
        {"name": sort_name, "id": str(item_id)},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_picker_cursor(cursor: str) -> tuple[str, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(b64decode(cursor + padding, altchars=b"-_", validate=True))
        if set(payload) != {"name", "id"} or not isinstance(payload["name"], str):
            raise ValueError
        return payload["name"], UUID(payload["id"])
    except (
        Base64Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_CURSOR", "message_ar": "مؤشر التصفح غير صالح."},
        ) from error


def list_food_picker(
    session: Session,
    principal: PrincipalContext,
    *,
    search: str = "",
    limit: int = 30,
    cursor: str | None = None,
) -> FoodPickerResponse:
    normalized_search = search.strip()
    normalized_name = func.lower(Food.name)
    catalog = select(normalized_name.label("sort_name"), *PICKER_COLUMNS).where(
        Food.archived_at.is_(None)
    )
    if normalized_search:
        pattern = f"%{normalized_search}%"
        catalog = catalog.where(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))
    if cursor:
        cursor_name, cursor_id = _decode_picker_cursor(cursor)
        catalog = catalog.where(
            or_(
                normalized_name > cursor_name,
                and_(normalized_name == cursor_name, Food.id > cursor_id),
            )
        )
    rows = session.exec(catalog.order_by(normalized_name, Food.id).limit(limit + 1)).all()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [_picker_item(row[1:]) for row in page_rows]

    recent_items: list[FoodPickerItem] = []
    if not normalized_search:
        ranked = (
            select(
                DiaryEntry.food_id.label("food_id"),
                DiaryEntry.created_at.label("created_at"),
                DiaryEntry.id.label("entry_id"),
                func.row_number()
                .over(
                    partition_by=DiaryEntry.food_id,
                    order_by=(DiaryEntry.created_at.desc(), DiaryEntry.id.desc()),
                )
                .label("recent_rank"),
            )
            .where(
                DiaryEntry.principal_id == principal.principal_id,
                DiaryEntry.food_id.is_not(None),
            )
            .subquery()
        )
        recent_rows = session.exec(
            select(*PICKER_COLUMNS)
            .join(ranked, ranked.c.food_id == Food.id)
            .where(ranked.c.recent_rank == 1, Food.archived_at.is_(None))
            .order_by(ranked.c.created_at.desc(), ranked.c.entry_id.desc())
            .limit(5)
        ).all()
        recent_items = [_picker_item(row) for row in recent_rows]

    return FoodPickerResponse(
        items=items,
        recent_items=recent_items,
        next_cursor=(
            _encode_picker_cursor(page_rows[-1][0], page_rows[-1][1]) if has_more else None
        ),
    )


def net_carbs(food: Food) -> float | None:
    if food.fiber_g is None:
        return None
    return round(max(float(food.carb_g) - float(food.fiber_g), 0), 2)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _food_data(food: Food) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in FOOD_FIELDS:
        value = getattr(food, field)
        if hasattr(value, "value"):
            data[field] = _enum_value(value)
        elif (
            isinstance(value, (int, float))
            or value is not None
            and field.endswith(("_g", "_mg", "_mcg"))
        ):
            data[field] = _float_or_none(value)
        elif field in {"unit_amount", "calories", "protein_g", "carb_g", "fat_g"}:
            data[field] = float(value)
        else:
            data[field] = value
    return data


def _build_food_response(food: Food) -> FoodResponse:
    try:
        return FoodResponse(
            id=food.id,
            **_food_data(food),
            legacy_nutrition={
                "folate_mcg": _float_or_none(food.folate_mcg),
                "vitamin_a_mcg": _float_or_none(food.vitamin_a_mcg),
            },
            net_carbs_g=net_carbs(food),
            created_at=food.created_at,
            updated_at=food.updated_at,
            archived_at=food.archived_at,
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_FOOD_DATA",
                "message_ar": "تعذر قراءة بيانات الطعام بسبب عدم توافقها.",
            },
        ) from error


def to_food_responses(
    session: Session, principal: PrincipalContext, foods: Sequence[Food]
) -> list[FoodResponse]:
    del session, principal
    return [_build_food_response(food) for food in foods]


def to_food_response(session: Session, principal: PrincipalContext, food: Food) -> FoodResponse:
    del session, principal
    return _build_food_response(food)


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
    session: Session, data: dict[str, Any], food_id: UUID | None = None
) -> None:
    target_key = duplicate_key(data)
    foods = session.exec(select(Food)).all()
    for food in foods:
        if food_id is not None and food.id == food_id:
            continue
        if duplicate_key(_food_data(food)) == target_key:
            raise HTTPException(status_code=422, detail=_duplicate_detail())


_FOOD_NAMESPACE_ADVISORY_KEY = 4_666_663_031


def _food_namespace_lock(session: Session, *, shared: bool) -> None:
    """Use one transaction-scoped namespace lock without taking an owner row.

    Keeping this sentinel outside the Principal/Food row namespaces lets Diary
    writers follow the frozen owner -> target -> day -> namespace -> Food order,
    while Food writers serialize before locking Food rows.
    """
    if session.get_bind().dialect.name != "postgresql":
        return
    function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    session.execute(
        text(f"SELECT {function}(:lock_key)"),
        {"lock_key": _FOOD_NAMESPACE_ADVISORY_KEY},
    )


def _lock_food_namespace(session: Session, principal: PrincipalContext) -> None:
    """Lock the actor before serializing Food writers and locking Food rows."""
    session.exec(
        select(Principal).where(Principal.id == principal.principal_id).with_for_update()
    ).one()
    _food_namespace_lock(session, shared=False)


def lock_food_namespace_for_logging(session: Session) -> None:
    """Join the Food lock order with a reader-compatible namespace lock.

    Diary capture takes this only after owner/target/day locks and before Food.
    Food writers first lock their Principal, then take the exclusive advisory
    lock before Food. This matches Diary's Principal -> namespace -> Food
    ordering and prevents an implicit Principal foreign-key lock from creating
    an inversion after the namespace lock is held.
    """
    _food_namespace_lock(session, shared=True)


def _validated_update_data(
    session: Session, principal: PrincipalContext, food: Food, payload: FoodUpdate
) -> FoodCreate:
    del session, principal
    current = _food_data(food)
    updates = payload.model_dump(exclude_unset=True)
    current.update(updates)
    try:
        return FoodCreate.model_validate(current)
    except ValidationError as error:
        raise food_validation_http_exception(error) from error


def _persistence_data(payload: FoodCreate) -> dict[str, Any]:
    data = payload.model_dump(exclude={"id"})
    data["normalized_name"] = normalize_text(payload.name)
    return data


def list_foods(
    session: Session, principal: PrincipalContext, query: str | None = None
) -> list[Food]:
    statement = select(Food).where(Food.archived_at.is_(None)).order_by(Food.name)
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
    archived: bool | None = False,
) -> FoodPage:
    conditions = (
        [Food.archived_at.is_not(None)]
        if archived is True
        else [Food.archived_at.is_(None)]
        if archived is False
        else []
    )
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        conditions.append(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))

    if category and category != UNCATEGORIZED_CATEGORY:
        conditions.append(Food.primary_category == category)

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

    category_statement = select(Food.primary_category).distinct()
    if archived is True:
        category_statement = category_statement.where(Food.archived_at.is_not(None))
    elif archived is False:
        category_statement = category_statement.where(Food.archived_at.is_(None))
    category_rows = session.exec(category_statement).all()
    categories = sorted(
        {value.strip() for value in category_rows if value and value.strip()}, key=str.casefold
    )
    uncategorized_count = 0

    return FoodPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
        categories=categories,
        uncategorized_count=uncategorized_count,
    )


def get_food(
    session: Session,
    principal: PrincipalContext,
    food_id: UUID,
    *,
    include_archived: bool = False,
) -> Food:
    statement = select(Food).where(Food.id == food_id)
    if not include_archived:
        statement = statement.where(Food.archived_at.is_(None))
    food = session.exec(statement).first()
    if food is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return food


def get_active_food_for_logging(
    session: Session, principal: PrincipalContext, food_id: UUID
) -> Food:
    """Load an active Food and preserve its measurement definition for the entry."""
    food = session.exec(
        select(Food)
        .where(Food.id == food_id, Food.archived_at.is_(None))
        .execution_options(populate_existing=True)
        .with_for_update(read=True)
    ).first()
    if food is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return food


def get_food_for_update(
    session: Session,
    principal: PrincipalContext,
    food_id: UUID,
    *,
    include_archived: bool = False,
) -> Food:
    """Load a visible Food while holding its exclusive writer lock."""
    statement = (
        select(Food)
        .where(Food.id == food_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if not include_archived:
        statement = statement.where(Food.archived_at.is_(None))
    food = session.exec(statement).first()
    if food is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return food


def _create_food_uncommitted(
    session: Session, principal: PrincipalContext, payload: FoodCreate
) -> Food:
    _lock_food_namespace(session, principal)
    data = _persistence_data(payload)
    if payload.id is not None:
        existing = session.exec(
            select(Food)
            .where(Food.id == payload.id)
            .execution_options(populate_existing=True)
            .with_for_update()
        ).first()
        if existing is not None:
            ensure_not_duplicate(session, data, food_id=existing.id)
            return _update_food_uncommitted(
                session,
                principal,
                existing.id,
                FoodUpdate.model_validate(payload.model_dump(exclude={"id"})),
                food=existing,
            )
        data["id"] = payload.id

    ensure_not_duplicate(session, data)
    food = Food(
        created_by_principal_id=principal.principal_id,
        updated_by_principal_id=principal.principal_id,
        **data,
    )
    session.add(food)
    session.flush()
    return food


def create_food(session: Session, principal: PrincipalContext, payload: FoodCreate) -> Food:
    try:
        food = _create_food_uncommitted(session, principal, payload)
        session.commit()
        session.refresh(food)
        return food
    except Exception:
        session.rollback()
        raise


def create_food_response(
    session: Session, principal: PrincipalContext, payload: FoodCreate
) -> FoodResponse:
    try:
        food = _create_food_uncommitted(session, principal, payload)
        response = to_food_response(session, principal, food)
        response.model_dump_json()
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise


def _update_food_uncommitted(
    session: Session,
    principal: PrincipalContext,
    food_id: UUID,
    payload: FoodUpdate,
    *,
    food: Food | None = None,
) -> Food:
    if food is None:
        _lock_food_namespace(session, principal)
        food = get_food_for_update(session, principal, food_id, include_archived=True)
    validated = _validated_update_data(session, principal, food, payload)
    data = _persistence_data(validated)
    if validated.nutrition_basis != food.nutrition_basis:
        referenced = session.exec(
            select(DiaryEntry.id).where(DiaryEntry.food_id == food.id).limit(1)
        ).first()
        if referenced is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "FOOD_MEASUREMENT_DIMENSION_IN_USE",
                    "message_ar": (
                        "لا يمكن تغيير أساس القياس بين الوزن والحجم بعد تسجيل الطعام في اليومية."
                    ),
                },
            )
    ensure_not_duplicate(session, data, food_id=food.id)
    for key, value in data.items():
        setattr(food, key, value)
    food.updated_at = utcnow()
    food.updated_by_principal_id = principal.principal_id
    session.add(food)
    session.flush()
    return food


def update_food(
    session: Session, principal: PrincipalContext, food_id: UUID, payload: FoodUpdate
) -> Food:
    try:
        food = _update_food_uncommitted(session, principal, food_id, payload)
        session.commit()
        session.refresh(food)
        return food
    except Exception:
        session.rollback()
        raise


def update_food_response(
    session: Session, principal: PrincipalContext, food_id: UUID, payload: FoodUpdate
) -> FoodResponse:
    try:
        food = _update_food_uncommitted(session, principal, food_id, payload)
        response = to_food_response(session, principal, food)
        response.model_dump_json()
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise


def _archive_food_uncommitted(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    _lock_food_namespace(session, principal)
    food = get_food_for_update(session, principal, food_id, include_archived=True)
    _archive_locked_food(principal, food)
    session.add(food)
    session.flush()
    return food


def archive_food(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    try:
        food = _archive_food_uncommitted(session, principal, food_id)
        session.commit()
        session.refresh(food)
        return food
    except Exception:
        session.rollback()
        raise


def archive_food_response(
    session: Session, principal: PrincipalContext, food_id: UUID
) -> FoodResponse:
    try:
        food = _archive_food_uncommitted(session, principal, food_id)
        response = to_food_response(session, principal, food)
        response.model_dump_json()
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise


def _archive_locked_food(principal: PrincipalContext, food: Food) -> None:
    """Mutate a Food whose exclusive row lock is held; never commit here."""
    if food.archived_at is not None:
        return
    food.archived_at = utcnow()
    food.archived_by_principal_id = principal.principal_id
    food.updated_by_principal_id = principal.principal_id
    food.updated_at = utcnow()


def _restore_food_uncommitted(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    _lock_food_namespace(session, principal)
    food = get_food_for_update(session, principal, food_id, include_archived=True)
    if food.archived_at is None:
        return food
    food.archived_at = None
    food.archived_by_principal_id = None
    food.updated_by_principal_id = principal.principal_id
    food.updated_at = utcnow()
    session.add(food)
    session.flush()
    return food


def restore_food(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    try:
        food = _restore_food_uncommitted(session, principal, food_id)
        session.commit()
        session.refresh(food)
        return food
    except Exception:
        session.rollback()
        raise


def restore_food_response(
    session: Session, principal: PrincipalContext, food_id: UUID
) -> FoodResponse:
    try:
        food = _restore_food_uncommitted(session, principal, food_id)
        response = to_food_response(session, principal, food)
        response.model_dump_json()
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise


def delete_food(session: Session, principal: PrincipalContext, food_id: UUID) -> bool:
    _lock_food_namespace(session, principal)
    food = get_food_for_update(session, principal, food_id, include_archived=True)
    used = session.exec(select(DiaryEntry.id).where(DiaryEntry.food_id == food.id).limit(1)).first()
    if used is not None:
        _archive_locked_food(principal, food)
        session.add(food)
        session.commit()
        session.refresh(food)
        return False
    session.delete(food)
    session.commit()
    return True
