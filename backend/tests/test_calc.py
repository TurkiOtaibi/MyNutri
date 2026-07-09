from datetime import date

import pytest

from app.models import ActivityLevel, Goal, Profile, Sex
from app.services.calc import age_on, calculate_bmr, calculate_targets


def test_age_on_accounts_for_birthday() -> None:
    assert age_on(date(1995, 7, 9), today=date(2026, 7, 8)) == 30
    assert age_on(date(1995, 7, 8), today=date(2026, 7, 8)) == 31


def test_mifflin_st_jeor_example_from_plan() -> None:
    profile = Profile(
        sex=Sex.male,
        birth_date=date(1995, 1, 1),
        height_cm=175,
        weight_kg=80,
        activity_level=ActivityLevel.moderate,
        goal=Goal.cut,
        protein_per_kg=1.8,
        fat_pct=0.25,
    )

    assert calculate_bmr(Sex.male, 80, 175, 30) == 1748.75

    targets = calculate_targets(profile, today=date(2025, 1, 1))

    assert targets.bmr == 1748.75
    assert targets.tdee == pytest.approx(2710.56)
    assert targets.target_calories in (2168, 2169)
    assert targets.protein_g == 144
    assert targets.fat_g == pytest.approx(60.2)
    assert targets.carb_g == pytest.approx(262.6)
    assert targets.carb_clamped is False


def test_negative_carb_calories_are_clamped() -> None:
    profile = Profile(
        sex=Sex.female,
        birth_date=date(2000, 1, 1),
        height_cm=150,
        weight_kg=45,
        activity_level=ActivityLevel.sedentary,
        goal=Goal.cut,
        protein_per_kg=2.2,
        fat_pct=0.3,
    )

    targets = calculate_targets(profile, today=date(2026, 1, 1))

    assert targets.carb_g >= 0
