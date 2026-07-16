from datetime import date

from app.models import (
    ActivityLevel,
    DefaultUnitType,
    Food,
    Goal,
    NutritionBasis,
    Sex,
    UnitBasis,
)
from app.nutrition_rules.calculation import resolved_nutrient_targets
from app.nutrition_rules.registry import NUTRIENTS
from app.schemas import ProfilePreview, ProfileUpsert
from app.services.diary import make_snapshot, totals_from_snapshot
from app.services.profile import preview_targets


def test_new_profile_defaults_are_sex_compatible() -> None:
    common = dict(
        birth_date=date(1990, 1, 1),
        height_cm=170,
        weight_kg=80,
        activity_level=ActivityLevel.moderate,
        goal=Goal.maintain,
    )
    male = ProfileUpsert(sex=Sex.male, **common)
    female = ProfileUpsert(sex=Sex.female, **common)
    assert male.protein_per_kg == female.protein_per_kg == 1.2
    assert male.fat_pct == 0.25
    assert female.fat_pct == 0.30


def test_w1_gc_005_female_high_bmi_regression() -> None:
    payload = ProfilePreview(
        sex=Sex.female,
        birth_date=date(1991, 1, 1),
        height_cm=170,
        weight_kg=115,
        activity_level=ActivityLevel.sedentary,
        goal=Goal.maintain,
        protein_per_kg=1.2,
        fat_pct=0.30,
    )
    preview = preview_targets(payload)
    protein = preview.protein_calculation
    assert protein.basis == "adjusted_weight"
    assert protein.reference_weight_kg == 72.25
    assert protein.calculation_weight_kg == 86.3575
    assert preview.protein_g == 103.6
    assert protein.target_g == preview.protein_g


def test_registry_contains_exactly_sixteen_wave1_nutrients_and_seven_target_types() -> None:
    assert len(NUTRIENTS) == 16
    assert {item.key for item in NUTRIENTS} == {
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
    }
    approved_types = {
        "minimum",
        "maximum",
        "adequate",
        "recommended",
        "range",
        "monitor_only",
        "minimize",
    }
    assert {item.target_type for item in NUTRIENTS} <= approved_types


def test_w1_gc_008_through_015_resolved_nutrient_targets() -> None:
    male = {
        item["key"]: item["target_value"] for item in resolved_nutrient_targets(2000, Sex.male, 30)
    }
    female_51 = {
        item["key"]: item["target_value"]
        for item in resolved_nutrient_targets(2000, Sex.female, 51)
    }
    assert male == {
        "fiber_g": 30.0,
        "added_sugar_g": 50.0,
        "saturated_fat_g": 22.2,
        "trans_fat_g": 2.2,
        "sodium_mg": 2000.0,
        "potassium_mg": 3400.0,
        "cholesterol_mg": None,
        "calcium_mg": 1000.0,
        "iron_mg": 8.0,
        "magnesium_mg": 400.0,
        "zinc_mg": 11.0,
        "selenium_mcg": 55.0,
        "vitamin_b12_mcg": 2.4,
        "folate_dfe_mcg": 400.0,
        "vitamin_a_rae_mcg": 900.0,
        "iodine_mcg": 150.0,
    }
    assert female_51["potassium_mg"] == 2600
    assert female_51["calcium_mg"] == 1200
    assert female_51["iron_mg"] == 8
    assert female_51["magnesium_mg"] == 320
    assert female_51["zinc_mg"] == 8
    assert female_51["vitamin_a_rae_mcg"] == 700


def test_snapshot_preserves_known_zero_unknown_and_scales_known_values() -> None:
    food = Food(
        name="Nutrient snapshot",
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.serving,
        unit_amount=50,
        unit_basis=UnitBasis.g,
        calories=100,
        protein_g=10,
        carb_g=20,
        fat_g=5,
        fiber_g=0,
        sodium_mg=None,
        potassium_mg=400,
    )
    snapshot = make_snapshot(food, 1)
    assert snapshot["fiber_g"] == 0
    assert snapshot["sodium_mg"] is None
    totals = totals_from_snapshot(snapshot, 2)
    assert totals.fiber_g == 0
    assert totals.sodium_mg is None
    assert totals.potassium_mg == 400
