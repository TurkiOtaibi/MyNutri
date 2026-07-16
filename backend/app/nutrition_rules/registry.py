from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NutrientDefinition:
    key: str
    storage_field: str
    label_ar: str
    unit: str
    display_precision: int
    display_order: int
    target_type: str
    target_source: str
    target_rule: dict[str, Any]
    completeness_participation: bool = True
    diary_coverage_participation: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


NUTRIENTS: tuple[NutrientDefinition, ...] = (
    NutrientDefinition(
        "fiber_g",
        "fiber_g",
        "الألياف",
        "g",
        1,
        1,
        "minimum",
        "product_rule",
        {"kind": "fixed", "value": 30},
    ),
    NutrientDefinition(
        "added_sugar_g",
        "added_sugar_g",
        "السكر المضاف",
        "g",
        1,
        2,
        "maximum",
        "calorie_derived",
        {"kind": "percent_of_calories", "percent": 10, "kcal_per_unit": 4},
    ),
    NutrientDefinition(
        "saturated_fat_g",
        "saturated_fat_g",
        "الدهون المشبعة",
        "g",
        1,
        3,
        "maximum",
        "calorie_derived",
        {"kind": "percent_of_calories", "percent": 10, "kcal_per_unit": 9},
    ),
    NutrientDefinition(
        "trans_fat_g",
        "trans_fat_g",
        "الدهون المتحولة",
        "g",
        1,
        4,
        "maximum",
        "calorie_derived",
        {"kind": "strict_percent_of_calories", "percent": 1, "kcal_per_unit": 9},
    ),
    NutrientDefinition(
        "sodium_mg",
        "sodium_mg",
        "الصوديوم",
        "mg",
        0,
        5,
        "maximum",
        "reference",
        {"kind": "strict_upper_bound", "value": 2000},
    ),
    NutrientDefinition(
        "potassium_mg",
        "potassium_mg",
        "البوتاسيوم",
        "mg",
        0,
        6,
        "adequate",
        "sex_derived",
        {"male": 3400, "female": 2600},
    ),
    NutrientDefinition(
        "cholesterol_mg",
        "cholesterol_mg",
        "الكوليسترول",
        "mg",
        0,
        7,
        "monitor_only",
        "reference",
        {"kind": "no_numeric_target"},
    ),
    NutrientDefinition(
        "calcium_mg",
        "calcium_mg",
        "الكالسيوم",
        "mg",
        0,
        8,
        "recommended",
        "age_sex_derived",
        {"age_19_50": 1000, "male_51_70": 1000, "female_51_70": 1200, "over_70": 1200},
    ),
    NutrientDefinition(
        "iron_mg",
        "iron_mg",
        "الحديد",
        "mg",
        0,
        9,
        "recommended",
        "age_sex_derived",
        {"male_adult": 8, "female_19_50": 18, "female_51_plus": 8},
    ),
    NutrientDefinition(
        "magnesium_mg",
        "magnesium_mg",
        "المغنيسيوم",
        "mg",
        0,
        10,
        "recommended",
        "age_sex_derived",
        {"male_19_30": 400, "male_31_plus": 420, "female_19_30": 310, "female_31_plus": 320},
    ),
    NutrientDefinition(
        "zinc_mg",
        "zinc_mg",
        "الزنك",
        "mg",
        0,
        11,
        "recommended",
        "sex_derived",
        {"male": 11, "female": 8},
    ),
    NutrientDefinition(
        "selenium_mcg",
        "selenium_mcg",
        "السيلينيوم",
        "mcg",
        0,
        12,
        "recommended",
        "reference",
        {"kind": "fixed", "value": 55},
    ),
    NutrientDefinition(
        "vitamin_b12_mcg",
        "vitamin_b12_mcg",
        "فيتامين ب12",
        "mcg",
        1,
        13,
        "recommended",
        "reference",
        {"kind": "fixed", "value": 2.4},
    ),
    NutrientDefinition(
        "folate_dfe_mcg",
        "folate_dfe_mcg",
        "الفولات (DFE)",
        "mcg_dfe",
        0,
        14,
        "recommended",
        "reference",
        {"kind": "fixed", "value": 400},
    ),
    NutrientDefinition(
        "vitamin_a_rae_mcg",
        "vitamin_a_rae_mcg",
        "فيتامين أ (RAE)",
        "mcg_rae",
        0,
        15,
        "recommended",
        "sex_derived",
        {"male": 900, "female": 700},
    ),
    NutrientDefinition(
        "iodine_mcg",
        "iodine_mcg",
        "اليود",
        "mcg",
        0,
        16,
        "recommended",
        "reference",
        {"kind": "fixed", "value": 150},
    ),
)

TARGET_TYPES: tuple[str, ...] = (
    "minimum",
    "maximum",
    "adequate",
    "recommended",
    "range",
    "monitor_only",
    "minimize",
)

PRIMARY_CATEGORIES: tuple[str, ...] = (
    "vegetables",
    "fruits",
    "legumes",
    "whole_grains",
    "refined_grains",
    "nuts_seeds",
    "seafood",
    "dairy_fortified_alternatives",
    "eggs",
    "poultry",
    "red_meat",
    "processed_meat",
    "added_oils_fats",
    "sweets",
    "sugar_sweetened_beverages",
    "unsweetened_beverages",
    "herbs_spices",
    "mixed_dish",
    "other",
)

PRIMARY_CATEGORY_LABELS_AR: dict[str, str] = dict(
    zip(
        PRIMARY_CATEGORIES,
        (
            "الخضروات",
            "الفواكه",
            "البقوليات",
            "الحبوب الكاملة",
            "الحبوب المكررة",
            "المكسرات والبذور",
            "المأكولات البحرية",
            "الألبان والبدائل المدعمة",
            "البيض",
            "الدواجن",
            "اللحوم الحمراء",
            "اللحوم المصنعة",
            "الزيوت والدهون المضافة",
            "الحلويات",
            "المشروبات المحلاة بالسكر",
            "المشروبات غير المحلاة",
            "الأعشاب والتوابل",
            "طبق مركب",
            "أخرى",
        ),
        strict=True,
    )
)

FOOD_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "key": "vegetables",
        "mutually_exclusive": True,
        "serving": {"amount": 80, "unit": "g"},
        "combined_target": {"fruit_and_vegetables_g_per_day": 400},
        "excludes_traits": ["starchy_root"],
    },
    {
        "key": "fruits",
        "mutually_exclusive": True,
        "servings": {
            "whole_fresh": {"amount": 80, "unit": "g"},
            "dried_fruit": {"amount": 30, "unit": "g"},
            "fruit_liquid_100_percent": {"amount": 150, "unit": "ml", "daily_cap": 1},
        },
        "combined_target": {"fruit_and_vegetables_g_per_day": 400},
    },
    {
        "key": "legumes",
        "mutually_exclusive": True,
        "serving": {"amount": 80, "unit": "g"},
        "target": {"minimum_servings": 3, "period": "week"},
    },
    {
        "key": "whole_grains",
        "mutually_exclusive": True,
        "basis": "per_100g",
        "share_target": {"minimum_percent_of_known_grains": 50},
    },
    {
        "key": "refined_grains",
        "mutually_exclusive": True,
        "basis": "per_100g",
        "share_denominator": "known_whole_plus_refined",
    },
    {
        "key": "nuts_seeds",
        "mutually_exclusive": True,
        "serving": {"amount": 30, "unit": "g"},
        "target": {"minimum_servings": 5, "period": "week"},
        "includes": ["peanuts"],
        "excludes": ["extracted_oils"],
    },
    {
        "key": "seafood",
        "mutually_exclusive": True,
        "serving": {"amount": 100, "unit": "g"},
        "target": {"minimum_servings": 2, "period": "week", "omega3_rich_minimum_servings": 1},
    },
    {
        "key": "dairy_fortified_alternatives",
        "mutually_exclusive": True,
        "target": {"servings": 2, "period": "day"},
        "subtypes": {
            "milk_laban_kefir": {"amount": 250, "unit": "ml"},
            "yogurt": {"amount": 200, "unit": "g"},
            "hard_cheese": {"amount": 30, "unit": "g"},
            "cottage_ricotta": {"amount": 120, "unit": "g"},
            "fortified_plant_alternative": {
                "amount": 250,
                "unit": "ml",
                "requires_trait": "calcium_fortified",
                "minimum_calcium_mg_per_100ml": 100,
            },
        },
        "excludes": ["butter", "ghee", "cream", "ice_cream"],
    },
    {
        "key": "eggs",
        "mutually_exclusive": True,
        "target_type": "monitor_only",
        "reference_serving": {"amount": 50, "unit": "g"},
        "subtypes": ["whole_egg", "egg_white", "mixed_egg_product"],
    },
    {
        "key": "poultry",
        "mutually_exclusive": True,
        "target_type": "monitor_only",
        "reference_serving": {"amount": 100, "unit": "g"},
        "processed_classification": "processed_meat",
    },
    {
        "key": "red_meat",
        "mutually_exclusive": True,
        "reference_serving": {"amount": 100, "unit": "g"},
        "target": {"maximum_amount": 500, "near_limit_from": 350, "unit": "g", "period": "week"},
    },
    {
        "key": "processed_meat",
        "mutually_exclusive": True,
        "target_type": "minimize",
        "display": ["grams", "occasions"],
    },
    {"key": "added_oils_fats", "mutually_exclusive": True, "target_type": "monitor_only"},
    {"key": "sweets", "mutually_exclusive": True, "target_type": "minimize"},
    {"key": "sugar_sweetened_beverages", "mutually_exclusive": True, "target_type": "minimize"},
    {"key": "unsweetened_beverages", "mutually_exclusive": True, "target_type": "monitor_only"},
    {"key": "herbs_spices", "mutually_exclusive": True, "target_type": "monitor_only"},
)

TRAITS: tuple[dict[str, str], ...] = tuple(
    {"key": key, "label_ar": label}
    for key, label in (
        ("sweetened", "محلى"),
        ("non_nutritive_sweetened", "محلى بمُحلٍ غير مغذٍ"),
        ("processed", "مصنع"),
        ("omega3_rich_seafood", "مأكولات بحرية غنية بأوميغا 3"),
        ("calcium_fortified", "مدعم بالكالسيوم"),
        ("unsaturated_fat_source", "مصدر للدهون غير المشبعة"),
        ("smoked", "مدخن"),
        ("salted", "مملح"),
        ("fruit_liquid_100_percent", "عصير أو سموذي فواكه 100%"),
        ("dried_fruit", "فاكهة مجففة"),
        ("starchy_root", "جذر نشوي"),
    )
)

FOOD_GROUP_LABELS_AR: dict[str, str] = {
    key: PRIMARY_CATEGORY_LABELS_AR[key] for key in (item["key"] for item in FOOD_GROUPS)
}

FOOD_GROUP_SUBTYPE_LABELS_AR: dict[str, dict[str, str]] = {
    "dairy_fortified_alternatives": {
        "milk_laban_kefir": "حليب أو لبن أو كفير",
        "yogurt": "زبادي",
        "hard_cheese": "جبن صلب",
        "cottage_ricotta": "جبن قريش أو ريكوتا",
        "fortified_plant_alternative": "بديل نباتي مدعم",
    },
    "eggs": {
        "whole_egg": "بيضة كاملة",
        "egg_white": "بياض بيض",
        "mixed_egg_product": "منتج بيض مختلط",
    },
}

SOURCE_RELIABILITY: tuple[dict[str, str], ...] = (
    {"type": "laboratory_analysis", "label_ar": "تحليل مخبري", "reliability": "high"},
    {
        "type": "official_food_database",
        "label_ar": "قاعدة بيانات غذائية رسمية",
        "reliability": "high",
    },
    {"type": "official_product_label", "label_ar": "بطاقة منتج رسمية", "reliability": "high"},
    {"type": "manufacturer_website", "label_ar": "موقع الشركة المصنعة", "reliability": "high"},
    {"type": "official_restaurant", "label_ar": "بيانات مطعم رسمية", "reliability": "medium"},
    {"type": "calculated_recipe", "label_ar": "وصفة محسوبة", "reliability": "medium"},
    {"type": "manual_estimate", "label_ar": "تقدير يدوي", "reliability": "low"},
    {"type": "multiple_sources", "label_ar": "مصادر متعددة", "reliability": "mixed"},
    {"type": "unknown", "label_ar": "مصدر غير معروف", "reliability": "unknown"},
)

INGREDIENT_SOURCE_TYPES: tuple[str, ...] = (
    "official_product_label",
    "manufacturer_website",
    "official_food_database",
    "official_restaurant",
    "calculated_recipe",
    "manual_entry",
    "multiple_sources",
    "unknown",
)

INGREDIENT_SOURCE_LABELS_AR: dict[str, str] = {
    "official_product_label": "بطاقة منتج رسمية",
    "manufacturer_website": "موقع الشركة المصنعة",
    "official_food_database": "قاعدة بيانات غذائية رسمية",
    "official_restaurant": "بيانات مطعم رسمية",
    "calculated_recipe": "وصفة محسوبة",
    "manual_entry": "إدخال يدوي",
    "multiple_sources": "مصادر متعددة",
    "unknown": "مصدر غير معروف",
}

RELIABILITY_LEVELS: tuple[dict[str, str], ...] = (
    {"key": "high", "label_ar": "مرتفعة"},
    {"key": "medium", "label_ar": "متوسطة"},
    {"key": "low", "label_ar": "محدودة"},
    {"key": "mixed", "label_ar": "متفاوتة"},
    {"key": "unknown", "label_ar": "غير معروفة"},
)

NOVA = {
    "classifications": [1, 2, 3, 4, "unknown"],
    "labels_ar": {
        "1": "NOVA 1",
        "2": "NOVA 2",
        "3": "NOVA 3",
        "4": "NOVA 4",
        "unknown": "غير معروف",
    },
    "review_statuses": ["unreviewed", "reviewed"],
    "automated_suggestions": False,
}
