from __future__ import annotations

import json
import re
from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, delete, func, or_, text
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import (
    DiaryEntry,
    Food,
    FoodAnalyticalTrait,
    FoodGroupContribution,
    Principal,
    FoodStatus,
    utcnow,
)
from app.nutrition_rules.versions import VERSIONS
from app.schemas import (
    SOURCE_RELIABILITY_MAP,
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
    "food_category_key",
    "grain_type",
    "baked_good_type",
    "grain_starch_type",
    "food_kind",
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
        Food.status == FoodStatus.active
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
            .where(ranked.c.recent_rank == 1, Food.status == FoodStatus.active)
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


def _group_contributions(session: Session, food_id: UUID) -> list[FoodGroupContribution]:
    return list(
        session.exec(
            select(FoodGroupContribution)
            .where(FoodGroupContribution.food_id == food_id)
            .order_by(FoodGroupContribution.group_key)
        ).all()
    )


def _analytical_traits(session: Session, food_id: UUID) -> list[FoodAnalyticalTrait]:
    return list(
        session.exec(
            select(FoodAnalyticalTrait)
            .where(FoodAnalyticalTrait.food_id == food_id)
            .order_by(FoodAnalyticalTrait.trait_key)
        ).all()
    )


def _food_input_data(session: Session, principal: PrincipalContext, food: Food) -> dict[str, Any]:
    data = _food_data(food)
    data["nutrition_source"] = {
        "type": food.nutrition_source_type,
        "name": food.nutrition_source_name,
        "reference": food.nutrition_source_reference,
    }
    data["ingredients"] = {
        "text": food.ingredients_text,
        "source_type": food.ingredients_source_type,
        "source_name": food.ingredients_source_name,
        "source_reference": food.ingredients_source_reference,
    }
    data["group_contributions"] = [
        {
            "group_key": item.group_key,
            "subtype_key": item.subtype_key,
            "amount_per_100_basis": float(item.amount_per_100_basis),
            "data_status": item.data_status,
        }
        for item in _group_contributions(session, food.id)
    ]
    data["analytical_traits"] = [item.trait_key for item in _analytical_traits(session, food.id)]
    return data


def _build_food_response(
    food: Food,
    contributions: Sequence[FoodGroupContribution],
    traits: Sequence[FoodAnalyticalTrait],
) -> FoodResponse:
    derived_status = (
        "unknown"
        if not contributions
        else "estimated"
        if any(_enum_value(item.data_status) == "estimated" for item in contributions)
        else "known"
    )
    derived_completeness = (
        "unknown"
        if not contributions
        else "complete"
        if sum(float(item.amount_per_100_basis) for item in contributions) >= 100
        else "partial"
    )
    try:
        return FoodResponse(
            id=food.id,
            **_food_data(food),
            status=food.status,
            group_data_status=derived_status,
            group_data_completeness=derived_completeness,
            taxonomy_review_required=food.taxonomy_review_required,
            nutrition_source={
                "type": food.nutrition_source_type,
                "name": food.nutrition_source_name,
                "reference": food.nutrition_source_reference,
                "reliability": SOURCE_RELIABILITY_MAP[_enum_value(food.nutrition_source_type)],
                "reliability_rules_version": VERSIONS.source_reliability_rules_version,
            },
            ingredients={
                "text": food.ingredients_text,
                "source_type": food.ingredients_source_type,
                "source_name": food.ingredients_source_name,
                "source_reference": food.ingredients_source_reference,
            },
            group_contributions=[
                {
                    "group_key": item.group_key,
                    "subtype_key": item.subtype_key,
                    "amount_per_100_basis": float(item.amount_per_100_basis),
                    "data_status": item.data_status,
                    "food_group_rules_version": item.food_group_rules_version,
                }
                for item in contributions
            ],
            analytical_traits=[item.trait_key for item in traits],
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
    if not foods:
        return []

    food_ids = list(dict.fromkeys(food.id for food in foods))
    contributions_by_food_id: dict[UUID, list[FoodGroupContribution]] = defaultdict(list)
    traits_by_food_id: dict[UUID, list[FoodAnalyticalTrait]] = defaultdict(list)

    contributions = session.exec(
        select(FoodGroupContribution)
        .where(FoodGroupContribution.food_id.in_(food_ids))
        .order_by(FoodGroupContribution.food_id, FoodGroupContribution.group_key)
    ).all()
    for contribution in contributions:
        contributions_by_food_id[contribution.food_id].append(contribution)

    traits = session.exec(
        select(FoodAnalyticalTrait)
        .where(FoodAnalyticalTrait.food_id.in_(food_ids))
        .order_by(FoodAnalyticalTrait.food_id, FoodAnalyticalTrait.trait_key)
    ).all()
    for trait in traits:
        traits_by_food_id[trait.food_id].append(trait)

    return [
        _build_food_response(
            food,
            contributions_by_food_id[food.id],
            traits_by_food_id[food.id],
        )
        for food in foods
    ]


def to_food_response(session: Session, principal: PrincipalContext, food: Food) -> FoodResponse:
    return to_food_responses(session, principal, [food])[0]


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
    current = _food_input_data(session, principal, food)
    updates = payload.model_dump(exclude_unset=True)
    for key in (
        "nutrition_source",
        "ingredients",
        "group_contributions",
        "analytical_traits",
    ):
        if updates.get(key) is None:
            updates.pop(key, None)
    current.update(updates)
    try:
        return FoodCreate.model_validate(current)
    except ValidationError as error:
        raise food_validation_http_exception(error) from error


def _persistence_data(payload: FoodCreate) -> dict[str, Any]:
    data = payload.model_dump(
        exclude={
            "id",
            "nutrition_source",
            "ingredients",
            "group_contributions",
            "analytical_traits",
        }
    )
    source = payload.nutrition_source
    contributions = payload.group_contributions
    derived_status = (
        "unknown"
        if not contributions
        else "estimated"
        if any(_enum_value(item.data_status) == "estimated" for item in contributions)
        else "known"
    )
    derived_completeness = (
        "unknown"
        if not contributions
        else "complete"
        if sum(item.amount_per_100_basis for item in contributions) >= 100
        else "partial"
    )
    data.update(
        normalized_name=normalize_text(payload.name),
        group_data_status=derived_status,
        group_data_completeness=derived_completeness,
        nutrition_source_type=source.type,
        nutrition_source_name=source.name,
        nutrition_source_reference=source.reference,
        ingredients_text=payload.ingredients.text,
        ingredients_source_type=payload.ingredients.source_type,
        ingredients_source_name=payload.ingredients.source_name,
        ingredients_source_reference=payload.ingredients.source_reference,
        nova_classification=None,
        nova_review_status=None,
    )
    return data


def _replace_classification(
    session: Session, principal: PrincipalContext, food: Food, payload: FoodCreate
) -> None:
    session.exec(
        delete(FoodGroupContribution).where(
            FoodGroupContribution.food_id == food.id,
        )
    )
    session.exec(
        delete(FoodAnalyticalTrait).where(
            FoodAnalyticalTrait.food_id == food.id,
        )
    )
    session.flush()
    for item in payload.group_contributions:
        session.add(
            FoodGroupContribution(
                created_by_principal_id=principal.principal_id,
                food_id=food.id,
                group_key=item.group_key,
                subtype_key=item.subtype_key,
                amount_per_100_basis=item.amount_per_100_basis,
                data_status=item.data_status,
                food_group_rules_version=VERSIONS.food_group_rules_version,
            )
        )
    for trait_key in payload.analytical_traits:
        session.add(
            FoodAnalyticalTrait(
                created_by_principal_id=principal.principal_id,
                food_id=food.id,
                trait_key=trait_key,
                food_group_rules_version=VERSIONS.food_group_rules_version,
            )
        )


def list_foods(
    session: Session, principal: PrincipalContext, query: str | None = None
) -> list[Food]:
    statement = select(Food).where(Food.status == FoodStatus.active).order_by(Food.name)
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
    status: FoodStatus | None = FoodStatus.active,
) -> FoodPage:
    conditions = [Food.status == status] if status is not None else []
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        conditions.append(or_(Food.name.ilike(pattern), Food.brand.ilike(pattern)))

    if category and category != UNCATEGORIZED_CATEGORY:
        conditions.append(Food.food_category_key == category)

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

    category_statement = select(Food.food_category_key).distinct()
    if status is not None:
        category_statement = category_statement.where(Food.status == status)
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
        statement = statement.where(Food.status == FoodStatus.active)
    food = session.exec(statement).first()
    if food is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    return food


def get_active_food_for_logging(
    session: Session, principal: PrincipalContext, food_id: UUID
) -> Food:
    """Load an active, visible Food while holding a shared row lock.

    The lock is the synchronization point for immutable Diary snapshot capture
    and must be held until the Diary transaction commits or rolls back.
    """
    food = session.exec(
        select(Food)
        .where(Food.id == food_id, Food.status == FoodStatus.active)
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
        statement = statement.where(Food.status == FoodStatus.active)
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
    _replace_classification(session, principal, food, payload)
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
    ensure_not_duplicate(session, data, food_id=food.id)
    for key, value in data.items():
        setattr(food, key, value)
    food.updated_at = utcnow()
    food.updated_by_principal_id = principal.principal_id
    session.add(food)
    session.flush()
    _replace_classification(session, principal, food, validated)
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
    if _enum_value(food.status) == FoodStatus.archived.value:
        return
    food.status = FoodStatus.archived
    food.archived_at = utcnow()
    food.archived_by_principal_id = principal.principal_id
    food.updated_by_principal_id = principal.principal_id
    food.updated_at = utcnow()


def _restore_food_uncommitted(session: Session, principal: PrincipalContext, food_id: UUID) -> Food:
    _lock_food_namespace(session, principal)
    food = get_food_for_update(session, principal, food_id, include_archived=True)
    if _enum_value(food.status) == FoodStatus.active.value:
        return food
    food.status = FoodStatus.active
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
    session.exec(delete(FoodGroupContribution).where(FoodGroupContribution.food_id == food.id))
    session.exec(delete(FoodAnalyticalTrait).where(FoodAnalyticalTrait.food_id == food.id))
    session.delete(food)
    session.commit()
    return True
