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

FOOD_TAXONOMY: tuple[dict[str, Any], ...] = (
    {"key": "grains_and_starches", "label_ar": "الحبوب والنشويات", "subcategories": (("rice", "الأرز"), ("oats", "الشوفان"), ("pasta", "المعكرونة"), ("bulgur", "البرغل"), ("jareesh", "الجريش"), ("wheat", "القمح"), ("barley", "الشعير"), ("corn", "الذرة"), ("potatoes", "البطاطس"), ("sweet_potatoes", "البطاطا الحلوة"), ("other", "أخرى"))},
    {"key": "bakery", "label_ar": "المخبوزات", "subcategories": (("bread", "الخبز"), ("toast", "التوست"), ("samoli", "الصامولي"), ("croissant", "الكرواسون"), ("pastries", "المعجنات"), ("tortilla_and_wraps", "التورتيلا واللفائف"), ("biscuits_and_crackers", "البسكويت والمقرمشات"), ("other", "أخرى"))},
    {"key": "meat_and_poultry", "label_ar": "اللحوم والدواجن", "subcategories": (("chicken", "الدجاج"), ("turkey", "الديك الرومي"), ("beef", "اللحم البقري"), ("lamb", "لحم الغنم"), ("camel", "لحم الإبل"), ("eggs", "البيض"), ("processed_meat", "اللحوم المصنعة"), ("other", "أخرى"))},
    {"key": "fish_and_seafood", "label_ar": "الأسماك والمأكولات البحرية", "subcategories": (("fish", "الأسماك"), ("tuna", "التونة"), ("shrimp", "الروبيان"), ("crustaceans", "القشريات"), ("mollusks", "الرخويات"), ("other", "أخرى"))},
    {"key": "dairy_products", "label_ar": "الألبان ومنتجاتها", "subcategories": (("milk", "الحليب"), ("laban", "اللبن"), ("yogurt", "الزبادي"), ("labneh", "اللبنة"), ("cheese", "الأجبان"), ("cream_and_qishta", "القشطة والكريمة"), ("other", "منتجات ألبان أخرى"))},
    {"key": "legumes", "label_ar": "البقوليات", "subcategories": (("lentils", "العدس"), ("chickpeas", "الحمص"), ("beans", "الفاصوليا"), ("fava_beans", "الفول"), ("peas", "البازلاء"), ("cowpeas", "اللوبيا"), ("lupin", "الترمس"), ("other", "أخرى"))},
    {"key": "vegetables", "label_ar": "الخضروات", "subcategories": (("leafy_vegetables", "الخضروات الورقية"), ("cruciferous_vegetables", "الخضروات الصليبية"), ("root_vegetables", "الخضروات الجذرية"), ("tomatoes", "الطماطم"), ("cucumber", "الخيار"), ("peppers", "الفلفل"), ("onion_and_garlic", "البصل والثوم"), ("zucchini_and_squash", "الكوسا والقرع"), ("eggplant", "الباذنجان"), ("mushrooms", "الفطر"), ("other", "خضروات أخرى"))},
    {"key": "fruits", "label_ar": "الفواكه", "subcategories": (("citrus", "الحمضيات"), ("apples_and_pears", "التفاح والكمثرى"), ("bananas", "الموز"), ("grapes", "العنب"), ("berries", "التوت"), ("stone_fruits", "الفواكه ذات النواة"), ("tropical_fruits", "الفواكه الاستوائية"), ("watermelon_and_melon", "البطيخ والشمام"), ("dates", "التمر"), ("pomegranate", "الرمان"), ("figs", "التين"), ("dried_fruits", "الفواكه المجففة"), ("other", "فواكه أخرى"))},
    {"key": "nuts_and_seeds", "label_ar": "المكسرات والبذور", "subcategories": (("almonds", "اللوز"), ("walnuts", "الجوز"), ("cashews", "الكاجو"), ("pistachios", "الفستق"), ("hazelnuts", "البندق"), ("peanuts", "الفول السوداني"), ("sesame_seeds", "بذور السمسم"), ("chia_seeds", "بذور الشيا"), ("flax_seeds", "بذور الكتان"), ("sunflower_seeds", "بذور دوار الشمس"), ("pumpkin_seeds", "بذور اليقطين"), ("other", "مكسرات وبذور أخرى"))},
    {"key": "fats_and_oils", "label_ar": "الدهون والزيوت", "subcategories": (("olive_oil", "زيت الزيتون"), ("vegetable_oils", "الزيوت النباتية"), ("coconut_oil", "زيت جوز الهند"), ("butter", "الزبدة"), ("ghee", "السمن"), ("margarine", "السمن النباتي"), ("other", "دهون وزيوت أخرى"))},
    {"key": "sweets_and_sugars", "label_ar": "الحلويات والسكريات", "subcategories": (("cake", "الكيك"), ("chocolate", "الشوكولاتة"), ("sweet_biscuits", "البسكويت الحلو"), ("middle_eastern_sweets", "الحلويات الشرقية"), ("western_desserts", "الحلويات الغربية"), ("ice_cream_and_frozen_desserts", "الآيس كريم والحلويات المجمدة"), ("candy", "الحلوى والسكاكر"), ("sugar_and_sweeteners", "السكر والمحليات"), ("jam_and_sweet_spreads", "المربى والدهن الحلو"), ("other", "حلويات وسكريات أخرى"))},
    {"key": "beverages", "label_ar": "المشروبات", "subcategories": (("water", "الماء"), ("coffee", "القهوة"), ("tea", "الشاي"), ("juices", "العصائر"), ("carbonated_drinks", "المشروبات الغازية"), ("energy_drinks", "مشروبات الطاقة"), ("sports_drinks", "المشروبات الرياضية"), ("plant_based_drinks", "المشروبات النباتية"), ("shakes_and_smoothies", "المشروبات المخفوقة"), ("other", "مشروبات أخرى"))},
    {"key": "meals", "label_ar": "الوجبات", "subcategories": (("rice_dishes", "أطباق الأرز"), ("pasta_dishes", "أطباق المعكرونة"), ("burgers_and_sandwiches", "البرغر والسندويتشات"), ("shawarma", "الشاورما"), ("pizza", "البيتزا"), ("salads", "السلطات"), ("soups", "الشوربات"), ("main_dishes", "الأطباق الرئيسية"), ("breakfast_meals", "وجبات الإفطار"), ("other", "وجبات أخرى"))},
    {"key": "sauces_spices_and_additions", "label_ar": "الصلصات والتوابل والإضافات", "subcategories": (("sauces", "الصلصات"), ("mayonnaise", "المايونيز"), ("dressings", "التتبيلات"), ("tahini", "الطحينة"), ("spices_and_seasonings", "التوابل والبهارات"), ("herbs", "الأعشاب"), ("salt", "الملح"), ("vinegar", "الخل"), ("additions", "الإضافات"), ("other", "أخرى"))},
    {"key": "other", "label_ar": "أخرى", "subcategories": (("other", "أخرى"),)},
)

PRIMARY_CATEGORIES: tuple[str, ...] = tuple(item["key"] for item in FOOD_TAXONOMY)
SUBCATEGORIES_BY_PRIMARY: dict[str, frozenset[str]] = {
    item["key"]: frozenset(key for key, _label in item["subcategories"])
    for item in FOOD_TAXONOMY
}

NUTRITION_DATA_SOURCES: tuple[dict[str, str], ...] = (
    {"key": "official", "label_ar": "رسمي"},
    {"key": "estimated", "label_ar": "تقديري"},
)
