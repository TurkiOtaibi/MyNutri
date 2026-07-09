from dataclasses import dataclass
from datetime import date

from app.models import ActivityLevel, Goal, Profile, Sex

ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}

GOAL_FACTORS: dict[Goal, float] = {
    Goal.cut: 0.8,
    Goal.maintain: 1.0,
    Goal.bulk: 1.1,
}


@dataclass(frozen=True)
class TargetResult:
    bmr: float
    tdee: float
    target_calories: int
    protein_g: float
    fat_g: float
    carb_g: float
    carb_clamped: bool = False


def age_on(birth_date: date, today: date | None = None) -> int:
    current = today or date.today()
    years = current.year - birth_date.year
    if (current.month, current.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)


def calculate_bmr(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * float(weight_kg) + 6.25 * float(height_cm) - 5 * age
    if sex == Sex.male:
        return base + 5
    return base - 161


def calculate_targets(profile: Profile, today: date | None = None) -> TargetResult:
    age = age_on(profile.birth_date, today)
    bmr = calculate_bmr(profile.sex, profile.weight_kg, profile.height_cm, age)
    tdee = bmr * ACTIVITY_FACTORS[profile.activity_level]
    raw_target = tdee * GOAL_FACTORS[profile.goal]
    target_calories = int(round(raw_target))

    protein_g = float(profile.protein_per_kg) * float(profile.weight_kg)
    protein_cal = protein_g * 4
    fat_cal = raw_target * float(profile.fat_pct)
    fat_g = fat_cal / 9
    carb_cal = raw_target - protein_cal - fat_cal
    carb_clamped = carb_cal < 0
    carb_g = max(carb_cal, 0) / 4

    return TargetResult(
        bmr=round(bmr, 2),
        tdee=round(tdee, 2),
        target_calories=target_calories,
        protein_g=round(protein_g, 1),
        fat_g=round(fat_g, 1),
        carb_g=round(carb_g, 1),
        carb_clamped=carb_clamped,
    )
