from datetime import date
from decimal import Decimal

import pytest

from app.models import ActivityLevel, Goal, Profile, Sex
from app.nutrition_rules.calculation import (
    CalculationError,
    age_on,
    calculate_bmr,
    calculate_carbohydrate,
    calculate_energy_target,
    calculate_fat,
    calculate_protein,
    calculate_targets,
    classify_calorie_safety,
)


def test_age_on_accounts_for_birthday() -> None:
    assert age_on(date(1995, 7, 9), today=date(2026, 7, 8)) == 30
    assert age_on(date(1995, 7, 8), today=date(2026, 7, 8)) == 31


def test_w1_gc_001_mifflin_maintain_baseline() -> None:
    profile = Profile(
        sex=Sex.male,
        birth_date=date(1996, 1, 1),
        height_cm=180,
        weight_kg=80,
        activity_level=ActivityLevel.moderate,
        goal=Goal.maintain,
        protein_per_kg=1.2,
        fat_pct=0.25,
    )
    result = calculate_targets(profile, today=date(2026, 1, 1))
    assert calculate_bmr(Sex.male, 80, 180, 30) == Decimal(1780)
    assert result.bmr == 1780
    assert result.tdee == 2759
    assert result.final_target_calories == 2759
    assert result.protein_g == 96.0
    assert result.fat_g == 76.6
    assert result.carb_g == 421.3
    assert result.safety_outcome == "normal"
    assert result.calculation_warnings == ()


@pytest.mark.parametrize(
    ("intensity", "requested", "target"),
    [("0.15", "375", 2125), ("0.20", "500", 2000), ("0.25", "625", 1875)],
)
def test_w1_gc_002_cut_intensities(intensity: str, requested: str, target: int) -> None:
    result = calculate_energy_target(Decimal(2500), Goal.cut, Decimal(intensity))
    assert result == (Decimal(requested), Decimal(requested), False, target)


def test_w1_gc_002_deficit_cap_and_non_cut() -> None:
    assert calculate_energy_target(Decimal(4000), Goal.cut, Decimal("0.25")) == (
        Decimal(1000),
        Decimal(750),
        True,
        3250,
    )
    assert calculate_energy_target(Decimal(2500), Goal.maintain, Decimal("0.25")) == (
        Decimal(0),
        Decimal(0),
        False,
        2500,
    )


@pytest.mark.parametrize(
    ("calories", "outcome", "can_activate"),
    [
        (1201, "normal", True),
        (1200, "specialist_review_required", False),
        (800, "specialist_review_required", False),
        (799, "very_low_energy_blocked", False),
    ],
)
def test_w1_gc_003_safety_boundaries(calories: int, outcome: str, can_activate: bool) -> None:
    assert classify_calorie_safety(calories) == (outcome, can_activate)


@pytest.mark.parametrize(
    ("raw", "rounded"), [("1200.49", 1200), ("1200.50", 1200), ("1200.51", 1201)]
)
def test_w1_gc_003_half_even_rounding_precedes_safety(raw: str, rounded: int) -> None:
    assert calculate_energy_target(Decimal(raw), Goal.maintain, Decimal("0.20"))[3] == rounded


@pytest.mark.parametrize(
    ("weight", "basis", "calculation_weight", "target"),
    [
        ("97.199", "actual_weight", "97.199", 116.6),
        ("97.200", "adjusted_weight", "86.346", 103.6),
        ("100", "adjusted_weight", "87.27", 104.7),
    ],
)
def test_w1_gc_004_unrounded_bmi_boundary(
    weight: str, basis: str, calculation_weight: str, target: float
) -> None:
    result, raw = calculate_protein(Decimal(weight), Decimal(180), Decimal("1.2"))
    assert result.basis == basis
    assert Decimal(str(result.calculation_weight_kg)) == Decimal(calculation_weight)
    assert result.target_g == target
    assert raw == Decimal(calculation_weight) * Decimal("1.2")


def test_w1_gc_005_and_006_female_regression_and_fat_options() -> None:
    protein, raw_protein = calculate_protein(Decimal(115), Decimal(170), Decimal("1.2"))
    carbs, warnings = calculate_carbohydrate(1655, raw_protein, Decimal("0.30"))
    assert protein.calculation_weight_kg == 86.3575
    assert protein.target_g == 103.6
    assert calculate_fat(1655, Decimal("0.30")) == 55.2
    assert carbs == 186.0
    assert warnings == ()
    assert calculate_fat(2000, Decimal("0.25")) == 55.6
    assert calculate_fat(2000, Decimal("0.30")) == 66.7
    assert calculate_fat(2000, Decimal("0.27")) == 60.0


def _carbohydrate_for_raw_grams(raw_grams: str) -> tuple[float, tuple[str, ...]]:
    final_calories = 2000
    fat_pct = Decimal("0.25")
    raw_protein = (
        Decimal(final_calories) - Decimal(raw_grams) * 4 - Decimal(final_calories) * fat_pct
    ) / 4
    value, warnings = calculate_carbohydrate(final_calories, raw_protein, fat_pct)
    return value, tuple(item.code for item in warnings)


@pytest.mark.parametrize(
    ("raw", "rounded", "warnings"),
    [
        ("130.04", 130.0, ()),
        ("129.95", 130.0, ()),
        ("129.94", 129.9, ("CARBOHYDRATE_BELOW_GENERAL_REFERENCE",)),
        ("100.00", 100.0, ("CARBOHYDRATE_BELOW_GENERAL_REFERENCE",)),
        ("99.95", 100.0, ("CARBOHYDRATE_BELOW_GENERAL_REFERENCE",)),
        ("99.94", 99.9, ("CARBOHYDRATE_VERY_LOW",)),
    ],
)
def test_w1_gc_007_carbohydrate_warning_boundaries(
    raw: str, rounded: float, warnings: tuple[str, ...]
) -> None:
    assert _carbohydrate_for_raw_grams(raw) == (rounded, warnings)


@pytest.mark.parametrize("raw", ["0.01", "0", "-1"])
def test_w1_gc_007_non_positive_carbohydrate_is_rejected(raw: str) -> None:
    with pytest.raises(CalculationError, match="NON_POSITIVE_CARBOHYDRATE_ALLOCATION"):
        _carbohydrate_for_raw_grams(raw)
