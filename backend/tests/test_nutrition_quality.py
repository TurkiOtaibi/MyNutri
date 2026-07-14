from datetime import date

import pytest

from app.models import ActivityLevel, DefaultUnitType, Food, Goal, NutritionBasis, Profile, Sex, UnitBasis
from app.schemas import ProfileUpsert
from app.services.calc import ACTIVITY_FACTORS, GOAL_FACTORS, calculate_targets
from app.services.diary import make_snapshot, totals_from_snapshot
from app.services.nutrients import ADDITIONAL_NUTRIENTS
from app.services.profile import preview_targets, to_target_response


def profile(sex: Sex = Sex.male, **changes: object) -> Profile:
    data = dict(sex=sex, birth_date=date(1990, 1, 1), height_cm=170, weight_kg=80, activity_level=ActivityLevel.moderate, goal=Goal.maintain)
    data.update(changes)
    return Profile(**data)


def test_new_profile_defaults_are_sex_compatible() -> None:
    male = ProfileUpsert(sex=Sex.male, birth_date=date(1990, 1, 1), height_cm=170, weight_kg=80, activity_level=ActivityLevel.moderate, goal=Goal.maintain)
    female = ProfileUpsert(sex=Sex.female, birth_date=date(1990, 1, 1), height_cm=170, weight_kg=80, activity_level=ActivityLevel.moderate, goal=Goal.maintain)
    assert male.protein_per_kg == female.protein_per_kg == 1.2
    assert male.fat_pct == 0.25
    assert female.fat_pct == 0.30


def test_female_sanity_scenario_and_preview_match_calculator() -> None:
    payload = ProfileUpsert(sex=Sex.female, birth_date=date(1990, 1, 1), height_cm=165, weight_kg=115, activity_level=ActivityLevel.sedentary, goal=Goal.cut, protein_per_kg=1.2, fat_pct=0.30)
    preview = preview_targets(payload)
    direct = calculate_targets(Profile(**payload.model_dump()))
    assert preview.protein_g == 138
    assert preview.fat_g == direct.fat_g
    assert preview.carb_g == direct.carb_g
    assert preview.target_calories == direct.target_calories


def test_remaining_calories_feed_carbs_and_factors_are_unchanged() -> None:
    item = profile(protein_per_kg=1.2, fat_pct=0.25)
    result = calculate_targets(item, today=date(2026, 1, 1))
    raw_target = result.tdee * GOAL_FACTORS[item.goal]
    expected = (raw_target - result.protein_g * 4 - raw_target * float(item.fat_pct)) / 4
    assert result.carb_g == pytest.approx(round(max(expected, 0), 1))
    assert ACTIVITY_FACTORS[ActivityLevel.moderate] == 1.55
    assert GOAL_FACTORS[Goal.cut] == 0.8


def test_registry_only_fiber_has_new_numeric_target() -> None:
    indexed = {item.key: item for item in ADDITIONAL_NUTRIENTS}
    assert indexed["fiber_g"].target_value == 30
    assert indexed["fiber_g"].target_type == "minimum"
    assert indexed["cholesterol_mg"].target_type == "monitor_only"
    assert all(item.target_value is None for key, item in indexed.items() if key != "fiber_g")
    assert len(to_target_response(profile()).additional_targets) == 6


def test_snapshot_preserves_known_zero_unknown_and_scales_known_values() -> None:
    food = Food(name="Nutrient snapshot", nutrition_basis=NutritionBasis.per_100g, default_unit_type=DefaultUnitType.serving, unit_amount=50, unit_basis=UnitBasis.g, calories=100, protein_g=10, carb_g=20, fat_g=5, fiber_g=0, sodium_mg=None, potassium_mg=400)
    snapshot = make_snapshot(food, 1)
    assert snapshot["fiber_g"] == 0
    assert snapshot["sodium_mg"] is None
    totals = totals_from_snapshot(snapshot, 2)
    assert totals.fiber_g == 0
    assert totals.sodium_mg is None
    assert totals.potassium_mg == 400
