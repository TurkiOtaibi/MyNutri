from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import Food, FoodAnalyticalTrait, FoodGroupContribution
from app.nutrition_rules.versions import VERSIONS
from app.schemas import NutritionSnapshot, NutritionTotals, SOURCE_RELIABILITY_MAP

WAVE1_NUTRIENTS = (
    "fiber_g",
    "added_sugar_g",
    "saturated_fat_g",
    "trans_fat_g",
    "sodium_mg",
    "potassium_mg",
    "cholesterol_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "selenium_mcg",
    "vitamin_b12_mcg",
    "folate_dfe_mcg",
    "vitamin_a_rae_mcg",
    "iodine_mcg",
)

PrimaryCategory = Literal[
    "vegetables", "fruits", "legumes", "whole_grains", "refined_grains",
    "nuts_seeds", "seafood", "dairy_fortified_alternatives", "eggs", "poultry",
    "red_meat", "processed_meat", "added_oils_fats", "sweets",
    "sugar_sweetened_beverages", "unsweetened_beverages", "herbs_spices",
    "mixed_dish", "other",
]
GroupKey = Literal[
    "vegetables", "fruits", "legumes", "whole_grains", "refined_grains",
    "nuts_seeds", "seafood", "dairy_fortified_alternatives", "eggs", "poultry",
    "red_meat", "processed_meat", "added_oils_fats", "sweets",
    "sugar_sweetened_beverages", "unsweetened_beverages", "herbs_spices",
]
TraitKey = Literal[
    "sweetened", "non_nutritive_sweetened", "processed", "omega3_rich_seafood",
    "calcium_fortified", "unsaturated_fat_source", "smoked", "salted",
    "fruit_liquid_100_percent", "dried_fruit", "starchy_root",
]
SourceType = Literal[
    "laboratory_analysis", "official_food_database", "official_product_label",
    "manufacturer_website", "official_restaurant", "calculated_recipe",
    "manual_estimate", "multiple_sources", "unknown",
]


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotFood(_ClosedModel):
    food_id: str | None
    name: str
    brand: str | None
    primary_category_key: PrimaryCategory | None
    food_kind: Literal["simple", "composite", "unknown"]


class SnapshotUnit(_ClosedModel):
    nutrition_basis: Literal["per_100g", "per_100ml"]
    default_unit_type: Literal[
        "g", "ml", "cup", "slice", "piece", "scoop", "serving", "tablespoon", "teaspoon"
    ]
    unit_amount: float
    unit_basis: Literal["g", "ml"]


class SnapshotNutrition(_ClosedModel):
    calories: float
    protein_g: float
    carb_g: float
    fat_g: float
    fiber_g: float | None
    added_sugar_g: float | None
    saturated_fat_g: float | None
    trans_fat_g: float | None
    sodium_mg: float | None
    potassium_mg: float | None
    cholesterol_mg: float | None
    calcium_mg: float | None
    iron_mg: float | None
    magnesium_mg: float | None
    zinc_mg: float | None
    selenium_mcg: float | None
    vitamin_b12_mcg: float | None
    folate_dfe_mcg: float | None
    vitamin_a_rae_mcg: float | None
    iodine_mcg: float | None


class SnapshotCompleteness(_ClosedModel):
    known_nutrient_count: int
    total_nutrient_count: Literal[16]
    state: Literal["all_unknown", "partial", "complete"]

    @model_validator(mode="after")
    def validate_state(self):
        expected = (
            "complete"
            if self.known_nutrient_count == 16
            else "all_unknown"
            if self.known_nutrient_count == 0
            else "partial"
        )
        if not 0 <= self.known_nutrient_count <= 16 or self.state != expected:
            raise ValueError("Snapshot nutrient completeness is inconsistent.")
        return self


class SnapshotGroupContribution(_ClosedModel):
    group_key: GroupKey
    subtype_key: str | None
    amount_per_captured_unit: float
    data_status: Literal["known", "estimated"]


class SnapshotFoodGroups(_ClosedModel):
    status: Literal["known", "estimated", "unknown"]
    completeness: Literal["complete", "partial", "unknown"]
    contributions: list[SnapshotGroupContribution]
    traits: list[TraitKey]
    food_group_rules_version: Literal["1.0.0"]


class SnapshotSource(_ClosedModel):
    type: SourceType
    name: str | None
    reference: str | None
    reliability: Literal["high", "medium", "low", "mixed", "unknown"]
    source_reliability_rules_version: Literal["1.0.0"]


class SnapshotNova(_ClosedModel):
    classification: Literal["1", "2", "3", "4", "unknown"]
    review_status: Literal["unreviewed", "reviewed"]
    nova_rules_version: Literal["1.0.0"]


class SnapshotVersions(_ClosedModel):
    nutrition_registry_version: Literal["1.0.0"]
    food_group_rules_version: Literal["1.0.0"]
    source_reliability_rules_version: Literal["1.0.0"]
    nova_rules_version: Literal["1.0.0"]
    snapshot_schema_version: Literal[2]


class SnapshotV2(_ClosedModel):
    schema_version: Literal[2]
    food: SnapshotFood
    captured_unit: SnapshotUnit
    nutrition: SnapshotNutrition
    completeness: SnapshotCompleteness
    food_groups: SnapshotFoodGroups
    source: SnapshotSource
    nova: SnapshotNova
    versions: SnapshotVersions


def _scaled(value: Any, factor: float) -> float | None:
    if value is None:
        return None
    return round(float(value) * factor, 6)


def create_snapshot_v2(
    session: Session, principal: PrincipalContext, food: Food
) -> dict[str, Any]:
    factor = float(food.unit_amount) / 100
    nutrition = {
        "calories": _scaled(food.calories, factor),
        "protein_g": _scaled(food.protein_g, factor),
        "carb_g": _scaled(food.carb_g, factor),
        "fat_g": _scaled(food.fat_g, factor),
        **{field: _scaled(getattr(food, field), factor) for field in WAVE1_NUTRIENTS},
    }
    known = sum(nutrition[field] is not None for field in WAVE1_NUTRIENTS)
    completeness_state = "complete" if known == 16 else "all_unknown" if known == 0 else "partial"
    contributions = session.exec(
        select(FoodGroupContribution)
        .where(
            FoodGroupContribution.food_id == food.id,
            FoodGroupContribution.principal_id == principal.principal_id,
        )
        .order_by(FoodGroupContribution.group_key)
    ).all()
    traits = session.exec(
        select(FoodAnalyticalTrait)
        .where(
            FoodAnalyticalTrait.food_id == food.id,
            FoodAnalyticalTrait.principal_id == principal.principal_id,
        )
        .order_by(FoodAnalyticalTrait.trait_key)
    ).all()
    source_type = _value(food.nutrition_source_type)
    document = SnapshotV2(
        schema_version=2,
        food={
            "food_id": str(food.id),
            "name": food.name,
            "brand": food.brand,
            "primary_category_key": food.primary_category_key,
            "food_kind": _value(food.food_kind),
        },
        captured_unit={
            "nutrition_basis": _value(food.nutrition_basis),
            "default_unit_type": _value(food.default_unit_type),
            "unit_amount": float(food.unit_amount),
            "unit_basis": _value(food.unit_basis),
        },
        nutrition=nutrition,
        completeness={
            "known_nutrient_count": known,
            "total_nutrient_count": 16,
            "state": completeness_state,
        },
        food_groups={
            "status": _value(food.group_data_status),
            "completeness": _value(food.group_data_completeness),
            "contributions": [
                {
                    "group_key": item.group_key,
                    "subtype_key": item.subtype_key,
                    "amount_per_captured_unit": _scaled(item.amount_per_100_basis, factor),
                    "data_status": _value(item.data_status),
                }
                for item in contributions
            ],
            "traits": [item.trait_key for item in traits],
            "food_group_rules_version": VERSIONS.food_group_rules_version,
        },
        source={
            "type": source_type,
            "name": food.nutrition_source_name,
            "reference": food.nutrition_source_reference,
            "reliability": SOURCE_RELIABILITY_MAP[source_type],
            "source_reliability_rules_version": VERSIONS.source_reliability_rules_version,
        },
        nova={
            "classification": _value(food.nova_classification),
            "review_status": _value(food.nova_review_status),
            "nova_rules_version": VERSIONS.nova_rules_version,
        },
        versions={
            "nutrition_registry_version": VERSIONS.nutrition_registry_version,
            "food_group_rules_version": VERSIONS.food_group_rules_version,
            "source_reliability_rules_version": VERSIONS.source_reliability_rules_version,
            "nova_rules_version": VERSIONS.nova_rules_version,
            "snapshot_schema_version": VERSIONS.snapshot_schema_version,
        },
    )
    return document.model_dump(mode="json")


def _integrity_error(code: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": code,
            "message_ar": "تعذر قراءة بيانات يومية محفوظة بسبب عدم توافقها.",
        },
    )


def read_snapshot_v2(document: dict[str, Any]) -> SnapshotV2:
    try:
        return SnapshotV2.model_validate(document)
    except ValidationError as error:
        raise _integrity_error("INVALID_DIARY_SNAPSHOT_DATA") from error


def read_snapshot_v1(document: dict[str, Any]) -> NutritionSnapshot:
    if "schema_version" in document:
        raise _integrity_error("UNSUPPORTED_DIARY_SNAPSHOT_VERSION")
    required = {"name", "calories", "protein_g", "carb_g", "fat_g"}
    if not required.issubset(document):
        raise _integrity_error("INVALID_DIARY_SNAPSHOT_DATA")
    try:
        return NutritionSnapshot.model_validate(document)
    except ValidationError as error:
        raise _integrity_error("INVALID_DIARY_SNAPSHOT_DATA") from error


def normalized_snapshot(
    document: dict[str, Any], schema_version: int | None
) -> NutritionSnapshot:
    if schema_version is None:
        return read_snapshot_v1(document)
    if schema_version != 2:
        raise _integrity_error("UNSUPPORTED_DIARY_SNAPSHOT_VERSION")
    snapshot = read_snapshot_v2(document)
    nutrition = snapshot.nutrition.model_dump()
    return NutritionSnapshot(
        food_id=snapshot.food.food_id,
        name=snapshot.food.name,
        brand=snapshot.food.brand,
        category=snapshot.food.primary_category_key,
        nutrition_basis=snapshot.captured_unit.nutrition_basis,
        default_unit_type=snapshot.captured_unit.default_unit_type,
        unit_amount=snapshot.captured_unit.unit_amount,
        unit_basis=snapshot.captured_unit.unit_basis,
        **nutrition,
    )


def totals_from_v2(document: dict[str, Any], quantity: float) -> NutritionTotals:
    snapshot = read_snapshot_v2(document)
    values = snapshot.nutrition.model_dump()
    totals = {
        field: None if value is None else round(float(value) * quantity, 2)
        for field, value in values.items()
    }
    fiber = totals.get("fiber_g")
    totals.update(
        {
            "sugar_g": None,
            "total_sugars_g": None,
            "net_carbs_g": round(max(float(totals["carb_g"]) - float(fiber or 0), 0), 2),
        }
    )
    return NutritionTotals.model_validate(totals)
