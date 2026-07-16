from datetime import date, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import PrincipalContext
from app.models import DefaultUnitType, DiaryEntry, Food, MealType, NutritionBasis, Principal, UnitBasis
from app.schemas import DiaryEntryCreate, DiaryEntryUpdate
from app.services.diary import make_snapshot, to_entry_response, totals_from_snapshot, update_entry
from app.services.diary_validation_errors import validate_diary_payload

TEST_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_PRINCIPAL = PrincipalContext(TEST_PRINCIPAL_ID)


def test_diary_snapshot_freezes_food_values() -> None:
    food = Food(
        principal_id=TEST_PRINCIPAL_ID,
        name="Greek yogurt",
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.serving,
        unit_amount=170,
        unit_basis=UnitBasis.g,
        calories=120,
        protein_g=18,
        carb_g=7,
        fat_g=0,
        fiber_g=1,
    )

    snapshot = make_snapshot(food)
    food.calories = 200

    totals = totals_from_snapshot(snapshot, 2)

    assert snapshot["calories"] == 120
    assert totals.calories == 408
    assert totals.protein_g == 61.2
    assert totals.net_carbs_g == 20.4


def test_future_diary_date_is_rejected() -> None:
    with pytest.raises(ValidationError, match="لا يمكن تسجيل يوميات بتاريخ مستقبلي"):
        DiaryEntryCreate(
            entry_date=date.today() + timedelta(days=1),
            food_id="00000000-0000-0000-0000-000000000001",
            quantity=1,
        )


def test_quantity_only_update_recalculates_frozen_totals() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    food = Food(
        principal_id=TEST_PRINCIPAL_ID,
        name="Snapshot food",
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.serving,
        unit_amount=50,
        unit_basis=UnitBasis.g,
        calories=200,
        protein_g=10,
        carb_g=20,
        fat_g=5,
    )
    with Session(engine) as session:
        session.add(Principal(id=TEST_PRINCIPAL_ID))
        session.add(food)
        session.commit()
        session.refresh(food)
        entry = DiaryEntry(
            principal_id=TEST_PRINCIPAL_ID,
            entry_date=date.today(),
            food_id=food.id,
            quantity=1,
            nutrition_snapshot=make_snapshot(food, 1),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        updated = update_entry(session, TEST_PRINCIPAL, entry.id, DiaryEntryUpdate(quantity=2))
        response = to_entry_response(updated)

        assert response.quantity == 2
        assert response.totals.calories == 200
        assert response.nutrition_snapshot.logged_quantity == 1
        assert response.nutrition_snapshot.calculated_totals["calories"] == 100
        assert response.entry_date == date.today()
        assert response.food_id == food.id


def test_diary_meal_type_defaults_and_rejects_invalid_values() -> None:
    payload = DiaryEntryCreate(
        entry_date=date.today(),
        food_id="00000000-0000-0000-0000-000000000001",
        quantity=1,
    )
    assert payload.meal_type == MealType.unspecified

    with pytest.raises(ValidationError):
        DiaryEntryCreate(
            entry_date=date.today(),
            food_id="00000000-0000-0000-0000-000000000001",
            quantity=1,
            meal_type="brunch",
        )


def test_invalid_meal_type_has_structured_arabic_error() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as raised:
        validate_diary_payload(
            DiaryEntryCreate,
            {
                "entry_date": str(date.today()),
                "food_id": "00000000-0000-0000-0000-000000000001",
                "quantity": 1,
                "meal_type": "brunch",
            },
        )

    assert raised.value.status_code == 422
    assert raised.value.detail[0]["field"] == "meal_type"
    assert raised.value.detail[0]["code"] == "invalid_meal_type"
    assert raised.value.detail[0]["msg"] == "اختر قسم وجبة صحيحًا."


def test_update_changes_quantity_and_meal_without_mutating_snapshot_identity() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    food = Food(
        principal_id=TEST_PRINCIPAL_ID,
        name="Meal snapshot food",
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.piece,
        unit_amount=50,
        unit_basis=UnitBasis.g,
        calories=200,
        protein_g=10,
        carb_g=20,
        fat_g=5,
    )
    with Session(engine) as session:
        session.add(Principal(id=TEST_PRINCIPAL_ID))
        session.add(food)
        session.commit()
        session.refresh(food)
        original_snapshot = make_snapshot(food, 1)
        entry = DiaryEntry(
            principal_id=TEST_PRINCIPAL_ID,
            entry_date=date.today(),
            food_id=food.id,
            quantity=1,
            meal_type=MealType.breakfast,
            nutrition_snapshot=original_snapshot,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        updated = update_entry(
            session,
            TEST_PRINCIPAL,
            entry.id,
            DiaryEntryUpdate(quantity=1.5, meal_type=MealType.dinner),
        )
        response = to_entry_response(updated)

        assert response.meal_type == MealType.dinner
        assert response.quantity == 1.5
        assert response.entry_date == date.today()
        assert response.food_id == food.id
        assert response.nutrition_snapshot.name == original_snapshot["name"]
        assert response.nutrition_snapshot.calories == original_snapshot["calories"]
