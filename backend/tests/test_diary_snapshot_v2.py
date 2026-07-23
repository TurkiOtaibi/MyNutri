from copy import deepcopy
from datetime import date
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import PrincipalContext
from app.models import (
    ContributionDataStatus,
    DefaultUnitType,
    DiaryEntry,
    Food,
    FoodAnalyticalTrait,
    FoodGroupContribution,
    FoodKind,
    GroupDataCompleteness,
    GroupDataStatus,
    MealType,
    NovaClassification,
    NovaReviewStatus,
    NutritionBasis,
    NutritionSourceType,
    Principal,
    TargetProvenance,
    UnitBasis,
)
from app.schemas import DiaryEntryCreate, DiaryEntryUpdate
from app.services.diary import create_entry, make_snapshot, to_entry_response, update_entry
from app.services.snapshot import read_snapshot_v2

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)


@pytest.fixture
def snapshot_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
        yield session


def _food() -> Food:
    return Food(
        principal_id=PRINCIPAL_ID,
        name="Captured food",
        brand="Brand",
        food_category_key="grains_starches",
        grain_type="whole",
        grain_starch_type="oats",
        food_kind=FoodKind.simple,
        group_data_status=GroupDataStatus.known,
        group_data_completeness=GroupDataCompleteness.partial,
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.serving,
        unit_amount=50,
        unit_basis=UnitBasis.g,
        calories=200,
        protein_g=10,
        carb_g=20,
        fat_g=5,
        fiber_g=5,
        trans_fat_g=0,
        sodium_mg=None,
        nutrition_source_type=NutritionSourceType.official_product_label,
        nutrition_source_name="Label",
        nova_classification=NovaClassification.three,
        nova_review_status=NovaReviewStatus.reviewed,
    )


def test_v2_captures_one_unit_and_quantity_never_mutates_snapshot(snapshot_session) -> None:
    food = _food()
    snapshot_session.add(food)
    snapshot_session.flush()
    snapshot_session.add(
        FoodGroupContribution(
            principal_id=PRINCIPAL_ID,
            food_id=food.id,
            group_key="whole_grains",
            amount_per_100_basis=80,
            data_status=ContributionDataStatus.known,
            food_group_rules_version="1.0.0",
        )
    )
    snapshot_session.add(
        FoodAnalyticalTrait(
            principal_id=PRINCIPAL_ID,
            food_id=food.id,
            trait_key="processed",
            food_group_rules_version="1.0.0",
        )
    )
    snapshot_session.commit()

    entry = create_entry(
        snapshot_session,
        PRINCIPAL,
        DiaryEntryCreate(
            entry_date=date(2026, 7, 16),
            food_id=food.id,
            quantity=3,
            meal_type=MealType.breakfast,
        ),
        snapshot_v3_writer_enabled=True,
    )
    original = deepcopy(entry.nutrition_snapshot)
    response = to_entry_response(entry)

    assert entry.snapshot_schema_version == 3
    assert entry.target_provenance == TargetProvenance.no_target_source
    assert entry.target_plan_id is None
    assert original["nutrition"]["fiber_g"] == 2.5
    assert original["food"]["name"] == "Captured food"
    assert original["food"]["food_category_key"] == "grains_starches"
    assert original["nutrition"]["calories"] == 100
    assert original["nutrition"]["trans_fat_g"] == 0
    assert original["nutrition"]["sodium_mg"] is None
    assert original["food_groups"]["contributions"][0]["amount_per_captured_unit"] == 40
    assert original["food_groups"]["traits"] == ["processed"]
    assert original["source"]["reliability"] == "high"
    assert original["nova"]["classification"] == "3"
    assert response.totals.fiber_g == 7.5
    assert response.totals.trans_fat_g == 0
    assert response.totals.sodium_mg is None

    invalid_registry_value = deepcopy(original)
    invalid_registry_value["source"]["type"] = "invented_source"
    with pytest.raises(HTTPException) as invalid_source:
        read_snapshot_v2(invalid_registry_value)
    assert invalid_source.value.detail["code"] == "INVALID_DIARY_SNAPSHOT_DATA"

    updated = update_entry(
        snapshot_session,
        PRINCIPAL,
        entry.id,
        DiaryEntryUpdate(quantity=2, meal_type=MealType.dinner),
    )
    assert updated.nutrition_snapshot == original
    updated_response = to_entry_response(updated)
    assert updated_response.totals.fiber_g == 5
    assert updated_response.meal_type == MealType.dinner

    food.name = "Changed later"
    food.fiber_g = 99
    snapshot_session.add(food)
    snapshot_session.commit()
    assert to_entry_response(updated).nutrition_snapshot.name == "Captured food"
    assert to_entry_response(updated).totals.fiber_g == 5


def test_snapshot_readers_reject_unknown_or_malformed_data() -> None:
    food = _food()
    legacy = DiaryEntry(
        principal_id=PRINCIPAL_ID,
        entry_date=date(2026, 7, 16),
        quantity=1,
        nutrition_snapshot=make_snapshot(food),
        snapshot_schema_version=None,
    )
    assert to_entry_response(legacy).nutrition_snapshot.name == "Captured food"

    unsupported = DiaryEntry(
        principal_id=PRINCIPAL_ID,
        entry_date=date(2026, 7, 16),
        quantity=1,
        nutrition_snapshot={"schema_version": 4},
        snapshot_schema_version=4,
    )
    with pytest.raises(HTTPException) as unsupported_error:
        to_entry_response(unsupported)
    assert unsupported_error.value.detail["code"] == "UNSUPPORTED_DIARY_SNAPSHOT_VERSION"

    malformed = DiaryEntry(
        principal_id=PRINCIPAL_ID,
        entry_date=date(2026, 7, 16),
        quantity=1,
        nutrition_snapshot={"schema_version": 2},
        snapshot_schema_version=2,
    )
    with pytest.raises(HTTPException) as malformed_error:
        to_entry_response(malformed)
    assert malformed_error.value.detail["code"] == "INVALID_DIARY_SNAPSHOT_DATA"
