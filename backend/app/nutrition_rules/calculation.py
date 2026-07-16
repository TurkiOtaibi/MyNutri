from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any
from zoneinfo import ZoneInfo

from app.models import ActivityLevel, Goal, Sex
from app.nutrition_rules.registry import NUTRIENTS
from app.nutrition_rules.versions import VERSIONS

D0 = Decimal("0")
D1 = Decimal("0.1")
ACTIVITY_FACTORS: dict[ActivityLevel, Decimal] = {
    ActivityLevel.sedentary: Decimal("1.2"),
    ActivityLevel.light: Decimal("1.375"),
    ActivityLevel.moderate: Decimal("1.55"),
    ActivityLevel.active: Decimal("1.725"),
    ActivityLevel.very_active: Decimal("1.9"),
}
GOAL_FACTORS: dict[Goal, Decimal] = {
    Goal.cut: Decimal("0.8"),
    Goal.maintain: Decimal("1.0"),
    Goal.bulk: Decimal("1.1"),
}


class CalculationError(ValueError):
    def __init__(self, code: str, message_ar: str, dimension: str) -> None:
        super().__init__(code)
        self.code = code
        self.message_ar = message_ar
        self.dimension = dimension


@dataclass(frozen=True, slots=True)
class ProteinCalculation:
    basis: str
    bmi_used: float
    actual_weight_kg: float
    reference_weight_kg: float | None
    calculation_weight_kg: float
    protein_per_kg: float
    target_g: float
    explanation_ar: str
    reference_weight_label_ar: str = "وزن مرجعي للحساب"
    calculation_engine_version: str = VERSIONS.calculation_engine_version


@dataclass(frozen=True, slots=True)
class CalculationWarning:
    code: str
    severity: str
    dimension: str
    value: float
    reference_value: float
    message_ar: str


@dataclass(frozen=True, slots=True)
class TargetResult:
    bmr: float
    tdee: float
    target_calories: int
    calories: int
    selected_cut_intensity: float
    requested_deficit_kcal: float
    applied_deficit_kcal: float
    deficit_cap_applied: bool
    final_target_calories: int
    safety_outcome: str
    can_activate: bool
    protein_g: float
    protein_calculation: ProteinCalculation
    fat_g: float
    carb_g: float
    carb_clamped: bool
    calculation_warnings: tuple[CalculationWarning, ...]
    additional_targets: tuple[dict[str, Any], ...]
    calculation_engine_version: str = VERSIONS.calculation_engine_version
    nutrition_registry_version: str = VERSIONS.nutrition_registry_version


def decimal(value: object) -> Decimal:
    return Decimal(str(value))


def age_on(birth_date: date, today: date | None = None) -> int:
    current = today or datetime.now(ZoneInfo("Asia/Riyadh")).date()
    years = current.year - birth_date.year
    if (current.month, current.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)


def calculate_bmr(sex: Sex, weight_kg: object, height_cm: object, age: int) -> Decimal:
    base = (
        Decimal(10) * decimal(weight_kg) + Decimal("6.25") * decimal(height_cm) - Decimal(5) * age
    )
    return base + Decimal(5) if sex == Sex.male else base - Decimal(161)


def _one_decimal(value: Decimal) -> float:
    return float(value.quantize(D1, rounding=ROUND_HALF_EVEN))


def calculate_energy_target(
    tdee: Decimal, goal: Goal, selected_cut_intensity: Decimal
) -> tuple[Decimal, Decimal, bool, int]:
    requested = tdee * selected_cut_intensity if goal == Goal.cut else D0
    applied = min(requested, Decimal(750)) if goal == Goal.cut else D0
    cap_applied = goal == Goal.cut and requested > Decimal(750)
    if goal == Goal.cut:
        raw_target = tdee - applied
    elif goal == Goal.bulk:
        raw_target = tdee * Decimal("1.1")
    else:
        raw_target = tdee
    final_target = int(raw_target.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    return requested, applied, cap_applied, final_target


def classify_calorie_safety(final_calories: int) -> tuple[str, bool]:
    if final_calories > 1200:
        return "normal", True
    if final_calories >= 800:
        return "specialist_review_required", False
    return "very_low_energy_blocked", False


def calculate_protein(
    actual_weight_kg: Decimal, height_cm: Decimal, protein_per_kg: Decimal
) -> tuple[ProteinCalculation, Decimal]:
    height_m = height_cm / 100
    bmi = actual_weight_kg / (height_m * height_m)
    if bmi < Decimal(30):
        basis = "actual_weight"
        reference_weight = None
        calculation_weight = actual_weight_kg
    else:
        basis = "adjusted_weight"
        reference_weight = Decimal(25) * height_m * height_m
        calculation_weight = reference_weight + Decimal("0.33") * (
            actual_weight_kg - reference_weight
        )
    raw_target = calculation_weight * protein_per_kg
    return (
        ProteinCalculation(
            basis=basis,
            bmi_used=float(bmi),
            actual_weight_kg=float(actual_weight_kg),
            reference_weight_kg=None if reference_weight is None else float(reference_weight),
            calculation_weight_kg=float(calculation_weight),
            protein_per_kg=float(protein_per_kg),
            target_g=_one_decimal(raw_target),
            explanation_ar=(
                "تم حساب البروتين باستخدام وزنك الحالي لأن مؤشر كتلة الجسم أقل من 30."
                if basis == "actual_weight"
                else "تم حساب البروتين باستخدام وزن حسابي معدل لأن مؤشر كتلة الجسم يساوي 30 أو أكثر."
            ),
        ),
        raw_target,
    )


def calculate_carbohydrate(
    final_calories: int, raw_protein_g: Decimal, fat_pct: Decimal
) -> tuple[float, tuple[CalculationWarning, ...]]:
    raw_carb_calories = (
        Decimal(final_calories) - raw_protein_g * 4 - Decimal(final_calories) * fat_pct
    )
    carb_g = _one_decimal(raw_carb_calories / 4)
    if raw_carb_calories <= 0 or decimal(carb_g) <= 0:
        raise CalculationError(
            "NON_POSITIVE_CARBOHYDRATE_ALLOCATION",
            "إعدادات السعرات والمغذيات الكبرى المختارة لا تترك كمية صالحة للكربوهيدرات. عدّل السعرات أو إعدادات المغذيات الكبرى.",
            "macro_allocation",
        )

    warnings: list[CalculationWarning] = []
    if carb_g < 100:
        warnings.append(
            CalculationWarning(
                "CARBOHYDRATE_VERY_LOW",
                "warning",
                "carbohydrate",
                carb_g,
                100.0,
                "كمية الكربوهيدرات المحسوبة منخفضة جدًا. راجع إعدادات السعرات والمغذيات الكبرى.",
            )
        )
    elif carb_g < 130:
        warnings.append(
            CalculationWarning(
                "CARBOHYDRATE_BELOW_GENERAL_REFERENCE",
                "info",
                "carbohydrate",
                carb_g,
                130.0,
                "كمية الكربوهيدرات المحسوبة أقل من المرجع العام البالغ 130 جم.",
            )
        )
    return carb_g, tuple(warnings)


def calculate_fat(final_calories: int, fat_pct: Decimal) -> float:
    return _one_decimal(Decimal(final_calories) * fat_pct / 9)


def resolved_nutrient_targets(
    final_calories: int, sex: Sex, age: int
) -> tuple[dict[str, Any], ...]:
    calories = Decimal(final_calories)
    values: dict[str, Decimal | None] = {
        "fiber_g": Decimal(30),
        "added_sugar_g": calories * Decimal("0.10") / 4,
        "saturated_fat_g": calories * Decimal("0.10") / 9,
        "trans_fat_g": calories * Decimal("0.01") / 9,
        "sodium_mg": Decimal(2000),
        "potassium_mg": Decimal(3400 if sex == Sex.male else 2600),
        "cholesterol_mg": None,
        "calcium_mg": Decimal(1200 if age > 70 or (sex == Sex.female and age >= 51) else 1000),
        "iron_mg": Decimal(18 if sex == Sex.female and age <= 50 else 8),
        "magnesium_mg": Decimal(
            400
            if sex == Sex.male and age <= 30
            else 420
            if sex == Sex.male
            else 310
            if age <= 30
            else 320
        ),
        "zinc_mg": Decimal(11 if sex == Sex.male else 8),
        "selenium_mcg": Decimal(55),
        "vitamin_b12_mcg": Decimal("2.4"),
        "folate_dfe_mcg": Decimal(400),
        "vitamin_a_rae_mcg": Decimal(900 if sex == Sex.male else 700),
        "iodine_mcg": Decimal(150),
    }
    result: list[dict[str, Any]] = []
    for item in NUTRIENTS:
        value = values[item.key]
        rounded = (
            None
            if value is None
            else float(
                value.quantize(Decimal(1).scaleb(-item.display_precision), rounding=ROUND_HALF_EVEN)
            )
        )
        result.append(
            {
                "key": item.key,
                "label_ar": item.label_ar,
                "unit": item.unit,
                "precision": item.display_precision,
                "order": item.display_order,
                "target_type": item.target_type,
                "target_source": item.target_source,
                "target_value": rounded,
                "target_rule": item.target_rule,
            }
        )
    return tuple(result)


def calculate_targets(profile: Any, today: date | None = None) -> TargetResult:
    age = age_on(profile.birth_date, today)
    weight = decimal(profile.weight_kg)
    height_cm = decimal(profile.height_cm)
    bmr = calculate_bmr(profile.sex, weight, height_cm, age)
    tdee = bmr * ACTIVITY_FACTORS[profile.activity_level]
    intensity = decimal(getattr(profile, "selected_cut_intensity", Decimal("0.20")))
    requested, applied, cap_applied, final_calories = calculate_energy_target(
        tdee, profile.goal, intensity
    )
    safety_outcome, can_activate = classify_calorie_safety(final_calories)

    protein, raw_protein = calculate_protein(weight, height_cm, decimal(profile.protein_per_kg))
    fat_pct = decimal(profile.fat_pct)
    fat_g = calculate_fat(final_calories, fat_pct)
    carb_g, warnings = calculate_carbohydrate(final_calories, raw_protein, fat_pct)

    return TargetResult(
        bmr=float(bmr.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)),
        tdee=float(tdee.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)),
        target_calories=final_calories,
        calories=final_calories,
        selected_cut_intensity=float(intensity),
        requested_deficit_kcal=float(requested),
        applied_deficit_kcal=float(applied),
        deficit_cap_applied=cap_applied,
        final_target_calories=final_calories,
        safety_outcome=safety_outcome,
        can_activate=can_activate,
        protein_g=protein.target_g,
        protein_calculation=protein,
        fat_g=fat_g,
        carb_g=carb_g,
        carb_clamped=False,
        calculation_warnings=warnings,
        additional_targets=resolved_nutrient_targets(final_calories, profile.sex, age),
    )
