from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    ActivityLevel,
    ContributionDataStatus,
    DefaultUnitType,
    FoodKind,
    Goal,
    GroupDataCompleteness,
    GroupDataStatus,
    IngredientsSourceType,
    MealType,
    NovaClassification,
    NovaReviewStatus,
    NutritionBasis,
    NutritionSourceType,
    Sex,
    UnitBasis,
)
from app.nutrition_rules.registry import FOOD_GROUPS, PRIMARY_CATEGORIES, SOURCE_RELIABILITY, TRAITS
from app.services.food_validation_errors import (
    ABOVE_MAX_MESSAGE,
    ADDED_SUGAR_GT_SUGAR_MESSAGE,
    FIBER_GT_CARBS_MESSAGE,
    FOOD_NAME_REQUIRED_MESSAGE,
    OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE,
    OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE,
    SATURATED_FAT_GT_FAT_MESSAGE,
    SATURATED_TRANS_GT_FAT_MESSAGE,
    TRANS_FAT_GT_FAT_MESSAGE,
)


class AdditionalNutrientTarget(BaseModel):
    key: str
    label_ar: str
    unit: str
    precision: int
    order: int
    target_type: Literal[
        "minimum", "maximum", "adequate", "recommended", "range", "monitor_only", "minimize"
    ]
    target_source: str
    target_value: float | None = None
    target_rule: dict[str, Any] = Field(default_factory=dict)


class ProteinCalculationResponse(BaseModel):
    basis: Literal["actual_weight", "adjusted_weight"]
    bmi_used: float
    actual_weight_kg: float
    reference_weight_kg: float | None
    calculation_weight_kg: float
    protein_per_kg: float
    target_g: float
    explanation_ar: str
    reference_weight_label_ar: str
    calculation_engine_version: str


class CalculationWarningResponse(BaseModel):
    code: Literal["CARBOHYDRATE_BELOW_GENERAL_REFERENCE", "CARBOHYDRATE_VERY_LOW"]
    severity: Literal["info", "warning"]
    dimension: Literal["carbohydrate"]
    value: float
    reference_value: float
    message_ar: str


class TargetResponse(BaseModel):
    bmr: float
    tdee: float
    target_calories: int
    calories: int
    selected_cut_intensity: float
    requested_deficit_kcal: float
    applied_deficit_kcal: float
    deficit_cap_applied: bool
    final_target_calories: int
    safety_outcome: Literal["normal", "specialist_review_required", "very_low_energy_blocked"]
    can_activate: bool
    protein_g: float
    protein_calculation: ProteinCalculationResponse
    fat_g: float
    carb_g: float
    carb_clamped: bool = False
    calculation_warnings: list[CalculationWarningResponse] = Field(default_factory=list)
    additional_targets: list[AdditionalNutrientTarget] = Field(default_factory=list)
    calculation_engine_version: str
    nutrition_registry_version: str
    preview_hash: str | None = None


class ProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sex: Sex
    birth_date: date
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    activity_level: ActivityLevel
    goal: Goal
    protein_per_kg: float = Field(default=1.2, ge=1.0, le=3.0)
    fat_pct: float = Field(default=0.25, ge=0.2, le=0.3)
    selected_cut_intensity: Literal[0.15, 0.2, 0.25] = 0.2

    @model_validator(mode="before")
    @classmethod
    def apply_sex_aware_fat_default(cls, value: Any) -> Any:
        if isinstance(value, dict) and "fat_pct" not in value:
            value = dict(value)
            value["fat_pct"] = 0.30 if value.get("sex") in {Sex.female, "female"} else 0.25
        return value


class ProfilePreview(ProfileUpsert):
    pass


class TargetPlanSummary(BaseModel):
    id: UUID
    status: Literal["active", "scheduled", "closed", "superseded_before_effective"]
    effective_from: date
    effective_to: date | None
    calendar_timezone: str
    predecessor_plan_id: UUID | None
    superseded_by_plan_id: UUID | None
    targets: TargetResponse
    created_at: datetime
    activated_at: datetime | None
    closed_at: datetime | None
    superseded_at: datetime | None


class TargetSourceResponse(BaseModel):
    target_provenance: Literal["versioned_plan", "legacy_unversioned", "no_target_source"]
    target_source_detail: Literal[
        "effective_target_plan", "legacy_transition_snapshot", "no_preserved_target_source"
    ]
    plan: TargetPlanSummary | None
    targets: TargetResponse | None


class TargetPlanActivationRequest(ProfilePreview):
    confirmed: Literal[True]
    expected_preview_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class TargetPlanReplacementRequest(ProfilePreview):
    replace_confirmed: Literal[True]
    expected_preview_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class TargetPlanActivationResponse(BaseModel):
    plan: TargetPlanSummary
    replaced_plan: TargetPlanSummary | None = None


class TargetPlanHistoryResponse(BaseModel):
    items: list[TargetPlanSummary]
    next_cursor: str | None = None


class ProfileResponse(ProfileUpsert):
    id: UUID
    updated_at: datetime
    targets: TargetResponse
    target_provenance: Literal["versioned_plan", "legacy_unversioned"] = "legacy_unversioned"
    effective_plan: TargetPlanSummary | None = None
    pending_plan: TargetPlanSummary | None = None

    model_config = ConfigDict(from_attributes=True)


OPTIONAL_NUTRIENT_MAX: dict[str, float] = {
    "fiber_g": 100,
    "sugar_g": 100,
    "added_sugar_g": 100,
    "saturated_fat_g": 100,
    "trans_fat_g": 100,
    "cholesterol_mg": 2000,
    "sodium_mg": 50000,
    "potassium_mg": 10000,
    "calcium_mg": 5000,
    "iron_mg": 100,
    "magnesium_mg": 1000,
    "zinc_mg": 100,
    "selenium_mcg": 9999999.999,
    "vitamin_d_mcg": 250,
    "vitamin_b12_mcg": 1000,
    "vitamin_c_mg": 5000,
    "vitamin_a_mcg": 3000,
    "vitamin_a_rae_mcg": 9999999.999,
    "folate_mcg": 2000,
    "folate_dfe_mcg": 9999999.999,
    "vitamin_k_mcg": 2000,
    "iodine_mcg": 9999999.999,
}

FOOD_TEXT_MAX: dict[str, int] = {
    "name": 120,
    "brand": 80,
    "category": 80,
    "notes": 500,
    "data_source": 120,
}


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


SOURCE_RELIABILITY_MAP = {item["type"]: item["reliability"] for item in SOURCE_RELIABILITY}
GROUP_KEYS = {item["key"] for item in FOOD_GROUPS}
TRAIT_KEYS = {item["key"] for item in TRAITS}
SUBTYPE_KEYS = {
    "dairy_fortified_alternatives": {
        "milk_laban_kefir",
        "yogurt",
        "hard_cheese",
        "cottage_ricotta",
        "fortified_plant_alternative",
    },
    "eggs": {"whole_egg", "egg_white", "mixed_egg_product"},
}


class NutritionSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: NutritionSourceType = NutritionSourceType.unknown
    name: str | None = None
    reference: str | None = None

    @model_validator(mode="after")
    def validate_name(self):
        self.name = _clean_optional_text(self.name)
        self.reference = _clean_optional_text(self.reference)
        if self.type != NutritionSourceType.unknown and self.name is None:
            raise ValueError("اسم مصدر البيانات الغذائية مطلوب لنوع المصدر المحدد.")
        return self


class NutritionSourceResponse(NutritionSourceInput):
    reliability: Literal["high", "medium", "low", "mixed", "unknown"]
    reliability_rules_version: str


class IngredientsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = None
    source_type: IngredientsSourceType | None = None
    source_name: str | None = None
    source_reference: str | None = None

    @model_validator(mode="after")
    def validate_source(self):
        self.text = _clean_optional_text(self.text)
        self.source_name = _clean_optional_text(self.source_name)
        self.source_reference = _clean_optional_text(self.source_reference)
        if self.text is not None and self.source_type is None:
            raise ValueError("نوع مصدر المكونات مطلوب عند إدخال المكونات.")
        if (
            self.source_type not in {None, IngredientsSourceType.unknown}
            and self.source_name is None
        ):
            raise ValueError("اسم مصدر المكونات مطلوب لنوع المصدر المحدد.")
        return self


class NovaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classification: NovaClassification


class NovaResponse(BaseModel):
    classification: NovaClassification
    review_status: NovaReviewStatus
    rules_version: str


class FoodGroupContributionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_key: str
    subtype_key: str | None = None
    amount_per_100_basis: float = Field(gt=0, le=100)
    data_status: ContributionDataStatus

    @model_validator(mode="after")
    def validate_registry_key(self):
        if self.group_key not in GROUP_KEYS:
            raise ValueError("مجموعة غذائية غير معتمدة.")
        allowed = SUBTYPE_KEYS.get(self.group_key)
        if allowed is not None and self.subtype_key not in allowed:
            raise ValueError("النوع الفرعي مطلوب وغير متوافق مع المجموعة الغذائية.")
        if allowed is None and self.subtype_key is not None:
            raise ValueError("هذه المجموعة لا تقبل نوعًا فرعيًا.")
        return self


class FoodGroupContributionResponse(FoodGroupContributionInput):
    food_group_rules_version: str


class FoodBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    brand: str | None = None
    category: str | None = None
    primary_category_key: str | None = None
    food_kind: FoodKind = FoodKind.unknown
    group_data_status: GroupDataStatus = GroupDataStatus.unknown
    group_data_completeness: GroupDataCompleteness = GroupDataCompleteness.unknown
    nutrition_basis: NutritionBasis
    default_unit_type: DefaultUnitType
    unit_amount: float = Field(gt=0, le=2000)
    unit_basis: UnitBasis
    calories: float = Field(ge=0, le=3000)
    protein_g: float = Field(ge=0, le=300)
    carb_g: float = Field(ge=0, le=500)
    fat_g: float = Field(ge=0, le=300)
    fiber_g: float | None = None
    sugar_g: float | None = None
    added_sugar_g: float | None = None
    saturated_fat_g: float | None = None
    trans_fat_g: float | None = None
    sodium_mg: float | None = None
    cholesterol_mg: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    magnesium_mg: float | None = None
    zinc_mg: float | None = None
    selenium_mcg: float | None = None
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    vitamin_a_rae_mcg: float | None = None
    folate_mcg: float | None = None
    folate_dfe_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    iodine_mcg: float | None = None
    notes: str | None = None
    data_source: str | None = None
    nutrition_source: NutritionSourceInput = Field(default_factory=NutritionSourceInput)
    ingredients: IngredientsInput = Field(default_factory=IngredientsInput)
    nova: NovaInput | None = None
    group_contributions: list[FoodGroupContributionInput] = Field(default_factory=list)
    analytical_traits: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError(FOOD_NAME_REQUIRED_MESSAGE)
        if len(cleaned) > FOOD_TEXT_MAX["name"]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator("brand", "category", "notes", "data_source", mode="before")
    @classmethod
    def clean_optional_text(cls, value: str | None, info) -> str | None:
        cleaned = _clean_optional_text(value)
        if cleaned is not None and len(cleaned) > FOOD_TEXT_MAX[info.field_name]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator(*OPTIONAL_NUTRIENT_MAX.keys())
    @classmethod
    def validate_optional_nutrient(cls, value: float | None, info) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError(OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE)
        maximum = OPTIONAL_NUTRIENT_MAX[info.field_name]
        if value > maximum:
            raise ValueError(OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE)
        return value

    @field_validator("fiber_g")
    @classmethod
    def validate_fiber_against_carbs(cls, value: float | None, info) -> float | None:
        carb_g = info.data.get("carb_g")
        if value is not None and carb_g is not None and value > carb_g:
            raise ValueError(FIBER_GT_CARBS_MESSAGE)
        return value

    @field_validator("added_sugar_g")
    @classmethod
    def validate_added_sugar_against_sugar(cls, value: float | None, info) -> float | None:
        sugar_g = info.data.get("sugar_g")
        if value is not None and sugar_g is not None and value > sugar_g:
            raise ValueError(ADDED_SUGAR_GT_SUGAR_MESSAGE)
        return value

    @field_validator("saturated_fat_g")
    @classmethod
    def validate_saturated_fat_against_fat(cls, value: float | None, info) -> float | None:
        fat_g = info.data.get("fat_g")
        if value is not None and fat_g is not None and value > fat_g:
            raise ValueError(SATURATED_FAT_GT_FAT_MESSAGE)
        return value

    @field_validator("trans_fat_g")
    @classmethod
    def validate_trans_fat_against_fat(cls, value: float | None, info) -> float | None:
        fat_g = info.data.get("fat_g")
        if value is not None and fat_g is not None and value > fat_g:
            raise ValueError(TRANS_FAT_GT_FAT_MESSAGE)
        saturated_fat_g = info.data.get("saturated_fat_g")
        if (
            value is not None
            and saturated_fat_g is not None
            and fat_g is not None
            and value + saturated_fat_g > fat_g
        ):
            raise ValueError(SATURATED_TRANS_GT_FAT_MESSAGE)
        return value

    @model_validator(mode="after")
    def validate_controlled_food_data(self):
        if (
            self.primary_category_key is not None
            and self.primary_category_key not in PRIMARY_CATEGORIES
        ):
            raise ValueError("التصنيف الأساسي غير معتمد.")
        groups = [item.group_key for item in self.group_contributions]
        if len(groups) != len(set(groups)):
            raise ValueError("لا يمكن تكرار المجموعة الغذائية للطعام نفسه.")
        if sum(item.amount_per_100_basis for item in self.group_contributions) > 100:
            raise ValueError("مجموع مساهمات المجموعات الغذائية لا يمكن أن يتجاوز 100.")
        if len(self.analytical_traits) != len(set(self.analytical_traits)):
            raise ValueError("لا يمكن تكرار السمة التحليلية.")
        if any(item not in TRAIT_KEYS for item in self.analytical_traits):
            raise ValueError("سمة تحليلية غير معتمدة.")
        if self.group_data_status == GroupDataStatus.unknown and self.group_contributions:
            raise ValueError("الحالة غير المعروفة لا تقبل مساهمات غذائية.")
        if (
            self.group_data_completeness == GroupDataCompleteness.unknown
            and self.group_contributions
        ):
            raise ValueError("اكتمال التصنيف غير المعروف لا يقبل مساهمات غذائية.")
        if (
            self.group_data_completeness == GroupDataCompleteness.partial
            and not self.group_contributions
        ):
            raise ValueError("التصنيف الجزئي يتطلب مساهمة غذائية واحدة على الأقل.")
        if self.group_data_status == GroupDataStatus.known and any(
            item.data_status != ContributionDataStatus.known for item in self.group_contributions
        ):
            raise ValueError("الحالة المؤكدة لا تقبل مساهمة تقديرية.")
        if (
            self.group_data_status == GroupDataStatus.estimated
            and not any(
                item.data_status == ContributionDataStatus.estimated
                for item in self.group_contributions
            )
        ):
            raise ValueError("الحالة التقديرية تتطلب مساهمة تقديرية واحدة على الأقل.")
        return self


class FoodCreate(FoodBase):
    id: UUID | None = None


class FoodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    brand: str | None = None
    category: str | None = None
    primary_category_key: str | None = None
    food_kind: FoodKind | None = None
    group_data_status: GroupDataStatus | None = None
    group_data_completeness: GroupDataCompleteness | None = None
    nutrition_basis: NutritionBasis | None = None
    default_unit_type: DefaultUnitType | None = None
    unit_amount: float | None = Field(default=None, gt=0, le=2000)
    unit_basis: UnitBasis | None = None
    calories: float | None = Field(default=None, ge=0, le=3000)
    protein_g: float | None = Field(default=None, ge=0, le=300)
    carb_g: float | None = Field(default=None, ge=0, le=500)
    fat_g: float | None = Field(default=None, ge=0, le=300)
    fiber_g: float | None = None
    sugar_g: float | None = None
    added_sugar_g: float | None = None
    saturated_fat_g: float | None = None
    trans_fat_g: float | None = None
    sodium_mg: float | None = None
    cholesterol_mg: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    magnesium_mg: float | None = None
    zinc_mg: float | None = None
    selenium_mcg: float | None = None
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    vitamin_a_rae_mcg: float | None = None
    folate_mcg: float | None = None
    folate_dfe_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    iodine_mcg: float | None = None
    notes: str | None = None
    data_source: str | None = None
    nutrition_source: NutritionSourceInput | None = None
    ingredients: IngredientsInput | None = None
    nova: NovaInput | None = None
    group_contributions: list[FoodGroupContributionInput] | None = None
    analytical_traits: list[str] | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError(FOOD_NAME_REQUIRED_MESSAGE)
        if len(cleaned) > FOOD_TEXT_MAX["name"]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator("brand", "category", "notes", "data_source", mode="before")
    @classmethod
    def clean_optional_text(cls, value: str | None, info) -> str | None:
        cleaned = _clean_optional_text(value)
        if cleaned is not None and len(cleaned) > FOOD_TEXT_MAX[info.field_name]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator(*OPTIONAL_NUTRIENT_MAX.keys())
    @classmethod
    def validate_optional_nutrient(cls, value: float | None, info) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError(OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE)
        maximum = OPTIONAL_NUTRIENT_MAX[info.field_name]
        if value > maximum:
            raise ValueError(OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE)
        return value

    @field_validator("fiber_g")
    @classmethod
    def validate_present_fiber_against_carbs(cls, value: float | None, info) -> float | None:
        carb_g = info.data.get("carb_g")
        if value is not None and carb_g is not None and value > carb_g:
            raise ValueError(FIBER_GT_CARBS_MESSAGE)
        return value

    @field_validator("added_sugar_g")
    @classmethod
    def validate_present_added_sugar_against_sugar(cls, value: float | None, info) -> float | None:
        sugar_g = info.data.get("sugar_g")
        if value is not None and sugar_g is not None and value > sugar_g:
            raise ValueError(ADDED_SUGAR_GT_SUGAR_MESSAGE)
        return value

    @field_validator("saturated_fat_g")
    @classmethod
    def validate_present_saturated_fat_against_fat(cls, value: float | None, info) -> float | None:
        fat_g = info.data.get("fat_g")
        if value is not None and fat_g is not None and value > fat_g:
            raise ValueError(SATURATED_FAT_GT_FAT_MESSAGE)
        return value

    @field_validator("trans_fat_g")
    @classmethod
    def validate_present_trans_fat_against_fat(cls, value: float | None, info) -> float | None:
        fat_g = info.data.get("fat_g")
        if value is not None and fat_g is not None and value > fat_g:
            raise ValueError(TRANS_FAT_GT_FAT_MESSAGE)
        saturated_fat_g = info.data.get("saturated_fat_g")
        if (
            value is not None
            and saturated_fat_g is not None
            and fat_g is not None
            and value + saturated_fat_g > fat_g
        ):
            raise ValueError(SATURATED_TRANS_GT_FAT_MESSAGE)
        return value


class LegacyNutritionResponse(BaseModel):
    folate_mcg: float | None
    vitamin_a_mcg: float | None
    meaning_ar: str = "قيمة قديمة غير محددة المعيار"


class FoodResponse(FoodBase):
    id: UUID
    nutrition_source: NutritionSourceResponse
    nova: NovaResponse
    group_contributions: list[FoodGroupContributionResponse]
    analytical_traits: list[str]
    legacy_nutrition: LegacyNutritionResponse
    net_carbs_g: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


FoodSort = Literal["name", "recent", "calories", "protein"]


class FoodListResponse(BaseModel):
    items: list[FoodResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]
    uncategorized_count: int


class NutritionSnapshot(BaseModel):
    food_id: UUID | None = None
    name: str
    brand: str | None = None
    category: str | None = None
    nutrition_basis: NutritionBasis | None = None
    default_unit_type: DefaultUnitType | None = None
    unit_amount: float | None = None
    unit_basis: UnitBasis | None = None
    calories: float
    protein_g: float
    carb_g: float
    fat_g: float
    fiber_g: float | None = None
    sugar_g: float | None = None
    added_sugar_g: float | None = None
    saturated_fat_g: float | None = None
    trans_fat_g: float | None = None
    sodium_mg: float | None = None
    cholesterol_mg: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    magnesium_mg: float | None = None
    zinc_mg: float | None = None
    selenium_mcg: float | None = None
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_a_rae_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    folate_dfe_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    iodine_mcg: float | None = None
    notes: str | None = None
    data_source: str | None = None
    log_mode: str | None = None
    logged_quantity: float | None = None
    calculated_totals: dict[str, Any] | None = None
    serving_label: str | None = None
    serving_grams: float | None = None
    total_sugars_g: float | None = None


class NutritionTotals(BaseModel):
    calories: float = 0
    protein_g: float = 0
    carb_g: float = 0
    fat_g: float = 0
    saturated_fat_g: float | None = None
    trans_fat_g: float | None = None
    cholesterol_mg: float | None = None
    sodium_mg: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    added_sugar_g: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    magnesium_mg: float | None = None
    zinc_mg: float | None = None
    selenium_mcg: float | None = None
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_a_rae_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    folate_dfe_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    iodine_mcg: float | None = None
    total_sugars_g: float | None = None
    net_carbs_g: float = 0


class DiaryEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    entry_date: date
    food_id: UUID
    quantity: float = Field(gt=0, le=50)
    meal_type: MealType = MealType.unspecified

    @field_validator("entry_date")
    @classmethod
    def prevent_future_entry_date(cls, value: date) -> date:
        from app.core.calendar import current_diary_date

        if value > current_diary_date():
            raise ValueError("لا يمكن تسجيل يوميات بتاريخ مستقبلي.")
        return value


class DiaryEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: float | None = Field(default=None, gt=0, le=50)
    meal_type: MealType | None = None

    @model_validator(mode="after")
    def require_one_change(self):
        if self.quantity is None and self.meal_type is None:
            raise ValueError("يجب إرسال الكمية أو قسم الوجبة.")
        return self


class DiaryEntryResponse(BaseModel):
    id: UUID
    entry_date: date
    food_id: UUID | None
    target_plan_id: UUID | None
    target_provenance: Literal["versioned_plan", "legacy_unversioned", "no_target_source"]
    snapshot_schema_version: int | None
    quantity: float
    meal_type: MealType
    nutrition_snapshot: NutritionSnapshot
    totals: NutritionTotals
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DaySummary(BaseModel):
    date: date
    totals: NutritionTotals
    targets: TargetResponse | None = None


class WeekSummary(BaseModel):
    start: date
    end: date
    days: list[DaySummary]
    weekly_totals: NutritionTotals
    targets: TargetResponse | None = None


class SyncOperation(BaseModel):
    method: str
    path: str
    body: dict[str, Any] | None = None
    client_id: str | None = None
    created_at: datetime | None = None


class SyncPushRequest(BaseModel):
    operations: list[SyncOperation] = Field(default_factory=list)


class SyncPushResponse(BaseModel):
    accepted: int
    accepted_client_ids: list[str] = Field(default_factory=list)
    rejected: list[dict[str, Any]] = Field(default_factory=list)
