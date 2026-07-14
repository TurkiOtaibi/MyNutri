from dataclasses import dataclass
from typing import Literal

NutrientTargetType = Literal["minimum", "maximum", "range", "monitor_only"]
NutrientTargetSource = Literal["fixed", "calculated", "reference", "manual", "clinical"]


@dataclass(frozen=True)
class NutrientDefinition:
    key: str
    label_ar: str
    unit: str
    precision: int
    order: int
    target_type: NutrientTargetType
    target_source: NutrientTargetSource
    target_value: float | None
    food_completeness: bool = True
    profile_targets: bool = True
    diary_details: bool = True


ADDITIONAL_NUTRIENTS: tuple[NutrientDefinition, ...] = (
    NutrientDefinition("fiber_g", "الألياف", "جم", 1, 1, "minimum", "fixed", 30),
    NutrientDefinition("sodium_mg", "الصوديوم", "ملجم", 0, 2, "maximum", "reference", None),
    NutrientDefinition("saturated_fat_g", "الدهون المشبعة", "جم", 1, 3, "maximum", "reference", None),
    NutrientDefinition("added_sugar_g", "السكر المضاف", "جم", 1, 4, "maximum", "reference", None),
    NutrientDefinition("potassium_mg", "البوتاسيوم", "ملجم", 0, 5, "minimum", "reference", None),
    NutrientDefinition("cholesterol_mg", "الكوليسترول", "ملجم", 0, 6, "monitor_only", "reference", None),
)


def nutrient_target_payloads() -> list[dict[str, object]]:
    return [
        {
            "key": item.key,
            "label_ar": item.label_ar,
            "unit": item.unit,
            "precision": item.precision,
            "order": item.order,
            "target_type": item.target_type,
            "target_source": item.target_source,
            "target_value": item.target_value,
        }
        for item in ADDITIONAL_NUTRIENTS
        if item.profile_targets
    ]
