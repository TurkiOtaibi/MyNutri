from datetime import date, datetime
import math
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.labs.numbers import normalize_decimal_text

from app.models import (
    ActivityLevel,
    DefaultUnitType,
    Goal,
    MealType,
    NutritionBasis,
    NutritionDataSource,
    PrincipalRole,
    PrincipalStatus,
    Sex,
    UnitBasis,
)

from app.core.calendar import age_on
from app.nutrition_rules.registry import PRIMARY_CATEGORIES, SUBCATEGORIES_BY_PRIMARY
from app.services.food_validation_errors import (
    ABOVE_MAX_MESSAGE,
    ADDED_SUGAR_GT_SUGAR_MESSAGE,
    FIBER_GT_CARBS_MESSAGE,
    FOOD_NAME_REQUIRED_MESSAGE,
    NUTRITION_UNIT_BASIS_MESSAGE,
    OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE,
    OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE,
    SATURATED_FAT_GT_FAT_MESSAGE,
    SATURATED_TRANS_GT_FAT_MESSAGE,
    TRANS_FAT_GT_FAT_MESSAGE,
)


class RegistryNutrientDefinition(BaseModel):
    key: str
    storage_field: str
    label_ar: str
    unit: str
    display_precision: int
    display_order: int
    target_type: Literal[
        "minimum", "maximum", "adequate", "recommended", "range", "monitor_only", "minimize"
    ]
    target_source: str
    target_rule: dict[str, Any]
    completeness_participation: bool
    diary_coverage_participation: bool


class RegistryLabelDefinition(BaseModel):
    key: str
    label_ar: str


class RegistryPrimaryCategoryDefinition(RegistryLabelDefinition):
    subcategories: list[RegistryLabelDefinition]


class NutritionRegistryResponse(BaseModel):
    rules_manifest_hash: str
    calculation_policy: dict[str, Any]
    nutrients: list[RegistryNutrientDefinition]
    target_types: list[str]
    primary_categories: list[str]
    food_taxonomy: list[RegistryPrimaryCategoryDefinition]
    nutrition_data_sources: list[RegistryLabelDefinition]


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
    preview_hash: str | None = None


PROFILE_HEIGHT_MIN_CM = 100.0
PROFILE_HEIGHT_MAX_CM = 250.0
PROFILE_WEIGHT_MIN_KG = 20.0
PROFILE_WEIGHT_MAX_KG = 300.0
PROFILE_PROTEIN_MIN_PER_KG = 1.0
PROFILE_PROTEIN_MAX_PER_KG = 3.0
PROFILE_FAT_MIN_PCT = 0.15
PROFILE_FAT_MAX_PCT = 0.40
PROFILE_MIN_AGE = 10
PROFILE_MAX_AGE = 100


class ProfileDomainValidationError(ValueError):
    def __init__(self, field: str, code: str, message: str, value: Any) -> None:
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message
        self.value = value


class ProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sex: Sex
    birth_date: date
    height_cm: float = Field(
        ge=PROFILE_HEIGHT_MIN_CM, le=PROFILE_HEIGHT_MAX_CM, allow_inf_nan=False
    )
    weight_kg: float = Field(
        ge=PROFILE_WEIGHT_MIN_KG, le=PROFILE_WEIGHT_MAX_KG, allow_inf_nan=False
    )
    activity_level: ActivityLevel
    goal: Goal
    protein_per_kg: float = Field(
        default=1.2,
        ge=PROFILE_PROTEIN_MIN_PER_KG,
        le=PROFILE_PROTEIN_MAX_PER_KG,
        allow_inf_nan=False,
    )
    fat_pct: float = Field(
        default=0.25,
        ge=PROFILE_FAT_MIN_PCT,
        le=PROFILE_FAT_MAX_PCT,
        allow_inf_nan=False,
    )
    selected_cut_intensity: Literal[0.15, 0.2, 0.25] = 0.2

    @field_validator("height_cm", "weight_kg", "protein_per_kg", "fat_pct", mode="before")
    @classmethod
    def make_non_finite_validation_input_json_safe(cls, value: Any) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            if math.isnan(value):
                return "NaN"
            return "Infinity" if value > 0 else "-Infinity"
        return value

    @model_validator(mode="before")
    @classmethod
    def apply_sex_aware_fat_default(cls, value: Any) -> Any:
        if isinstance(value, dict) and "fat_pct" not in value:
            value = dict(value)
            value["fat_pct"] = 0.30 if value.get("sex") in {Sex.female, "female"} else 0.25
        return value


class ProfilePreview(ProfileUpsert):
    pass


def validate_profile_domain(profile: ProfileUpsert, effective_date: date) -> ProfileUpsert:
    if profile.birth_date > effective_date:
        raise ProfileDomainValidationError(
            "birth_date",
            "profile_birth_date_future",
            "Birth date cannot be later than the authoritative effective date.",
            profile.birth_date,
        )

    age = age_on(profile.birth_date, effective_date)
    if age < PROFILE_MIN_AGE:
        raise ProfileDomainValidationError(
            "birth_date",
            "profile_age_below_minimum",
            f"Age must be at least {PROFILE_MIN_AGE} on the authoritative effective date.",
            profile.birth_date,
        )
    if age > PROFILE_MAX_AGE:
        raise ProfileDomainValidationError(
            "birth_date",
            "profile_age_above_maximum",
            f"Age must be at most {PROFILE_MAX_AGE} on the authoritative effective date.",
            profile.birth_date,
        )
    return profile


class TargetPlanSummary(BaseModel):
    id: UUID
    effective_from: date
    revision: int
    targets: TargetResponse
    created_at: datetime


class TargetSourceResponse(BaseModel):
    plan: TargetPlanSummary | None
    targets: TargetResponse | None

    @model_validator(mode="after")
    def require_consistent_target_source(self):
        if (self.plan is None) != (self.targets is None):
            raise ValueError("plan and targets must both be present or both be null")
        return self


class TargetPlanPreviewRequest(ProfilePreview):
    effective_from: date


class TargetPlanWriteRequest(TargetPlanPreviewRequest):
    confirmed: Literal[True]
    expected_preview_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class TargetPlanWriteResponse(BaseModel):
    plan: TargetPlanSummary
    replaced_plan: TargetPlanSummary | None = None


class TargetPlanHistoryResponse(BaseModel):
    items: list[TargetPlanSummary]
    next_cursor: str | None = None


class ProfileResponse(ProfileUpsert):
    id: UUID
    updated_at: datetime
    targets: TargetResponse | None = None
    effective_plan: TargetPlanSummary | None = None

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

FOOD_CORE_NUMERIC_FIELDS = (
    "unit_amount",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
)
FOOD_NUMERIC_FIELDS = FOOD_CORE_NUMERIC_FIELDS + tuple(OPTIONAL_NUTRIENT_MAX)
FOOD_RESPONSE_DERIVED_NUMERIC_FIELDS = ("net_carbs_g",)

FOOD_TEXT_MAX: dict[str, int] = {
    "name": 120,
    "brand": 80,
    "notes": 500,
}


def _finite_number_input(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return "__non_finite_number__"
    if isinstance(value, str) and value.strip().casefold() in {
        "nan",
        "infinity",
        "+infinity",
        "-infinity",
        "inf",
        "+inf",
        "-inf",
    }:
        return "__non_finite_number__"
    return value


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


class FoodBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    brand: str | None = None
    primary_category: str
    subcategory: str
    nutrition_basis: NutritionBasis
    default_unit_type: DefaultUnitType
    unit_amount: float = Field(gt=0, le=2000, allow_inf_nan=False)
    unit_basis: UnitBasis
    calories: float = Field(ge=0, le=3000, allow_inf_nan=False)
    protein_g: float = Field(ge=0, le=300, allow_inf_nan=False)
    carb_g: float = Field(ge=0, le=500, allow_inf_nan=False)
    fat_g: float = Field(ge=0, le=300, allow_inf_nan=False)
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
    nutrition_data_source: NutritionDataSource
    ingredients: str | None = None

    @field_validator(*FOOD_NUMERIC_FIELDS, mode="before")
    @classmethod
    def make_non_finite_validation_input_json_safe(cls, value: Any) -> Any:
        return _finite_number_input(value)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError(FOOD_NAME_REQUIRED_MESSAGE)
        if len(cleaned) > FOOD_TEXT_MAX["name"]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator("brand", "notes", mode="before")
    @classmethod
    def clean_bounded_optional_text(cls, value: str | None, info) -> str | None:
        cleaned = _clean_optional_text(value)
        if cleaned is not None and len(cleaned) > FOOD_TEXT_MAX[info.field_name]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator("ingredients", mode="before")
    @classmethod
    def clean_ingredients(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("unit_basis")
    @classmethod
    def validate_nutrition_unit_basis(cls, value: UnitBasis, info) -> UnitBasis:
        nutrition_basis = info.data.get("nutrition_basis")
        expected = UnitBasis.g if nutrition_basis == NutritionBasis.per_100g else UnitBasis.ml
        if nutrition_basis is not None and value != expected:
            raise ValueError(NUTRITION_UNIT_BASIS_MESSAGE)
        return value

    @field_validator(*OPTIONAL_NUTRIENT_MAX.keys())
    @classmethod
    def validate_optional_nutrient(cls, value: float | None, info) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("Input should be a finite number")
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
    def validate_taxonomy(self):
        if self.primary_category not in PRIMARY_CATEGORIES:
            raise ValueError("فئة الطعام الرئيسية غير معتمدة.")
        if self.subcategory not in SUBCATEGORIES_BY_PRIMARY[self.primary_category]:
            raise ValueError("الفئة الفرعية غير معتمدة للفئة الرئيسية المحددة.")
        return self


class FoodCreate(FoodBase):
    id: UUID | None = None


class FoodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    brand: str | None = None
    primary_category: str | None = None
    subcategory: str | None = None
    nutrition_basis: NutritionBasis | None = None
    default_unit_type: DefaultUnitType | None = None
    unit_amount: float | None = Field(default=None, gt=0, le=2000, allow_inf_nan=False)
    unit_basis: UnitBasis | None = None
    calories: float | None = Field(default=None, ge=0, le=3000, allow_inf_nan=False)
    protein_g: float | None = Field(default=None, ge=0, le=300, allow_inf_nan=False)
    carb_g: float | None = Field(default=None, ge=0, le=500, allow_inf_nan=False)
    fat_g: float | None = Field(default=None, ge=0, le=300, allow_inf_nan=False)
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
    nutrition_data_source: NutritionDataSource | None = None
    ingredients: str | None = None

    @field_validator(*FOOD_NUMERIC_FIELDS, mode="before")
    @classmethod
    def make_non_finite_validation_input_json_safe(cls, value: Any) -> Any:
        return _finite_number_input(value)

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

    @field_validator("brand", "notes", mode="before")
    @classmethod
    def clean_bounded_optional_text(cls, value: str | None, info) -> str | None:
        cleaned = _clean_optional_text(value)
        if cleaned is not None and len(cleaned) > FOOD_TEXT_MAX[info.field_name]:
            raise ValueError(ABOVE_MAX_MESSAGE)
        return cleaned

    @field_validator("ingredients", mode="before")
    @classmethod
    def clean_ingredients(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator(*OPTIONAL_NUTRIENT_MAX.keys())
    @classmethod
    def validate_optional_nutrient(cls, value: float | None, info) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("Input should be a finite number")
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
    legacy_nutrition: LegacyNutritionResponse
    net_carbs_g: float | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FoodPickerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    brand: str | None
    nutrition_basis: NutritionBasis
    default_unit_type: DefaultUnitType
    unit_amount: float
    unit_basis: UnitBasis
    calories: float
    protein_g: float
    carb_g: float
    fat_g: float


class FoodPickerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FoodPickerItem]
    recent_items: list[FoodPickerItem]
    next_cursor: str | None


FoodSort = Literal["name", "recent", "calories", "protein"]


class FoodListResponse(BaseModel):
    items: list[FoodResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]


class AccountResponse(BaseModel):
    principal_id: UUID
    auth_user_id: UUID
    email: str | None
    display_name: str | None
    role: PrincipalRole
    status: PrincipalStatus


class CalendarAuthorityResponse(BaseModel):
    current_diary_date: date
    calendar_timezone: str
    next_rollover_at: datetime


class AdminUserSummary(BaseModel):
    principal_id: UUID
    email: str | None
    display_name: str | None
    status: PrincipalStatus
    role: PrincipalRole
    created_at: datetime
    profile_complete: bool
    current_goal: Goal | None
    last_activity_at: datetime | None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserDetail(BaseModel):
    account: AdminUserSummary
    profile: ProfileResponse | None
    current_target: TargetSourceResponse | None
    plan_history: TargetPlanHistoryResponse


class DiaryFoodReference(BaseModel):
    id: UUID
    name: str
    brand: str | None = None


class NutritionTotals(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

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
    net_carbs_g: float | None = 0


class DiaryEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    entry_date: date
    food_id: UUID
    quantity: float = Field(gt=0, le=50)
    meal_type: MealType = MealType.unspecified


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
    food_id: UUID
    target_plan_id: UUID | None
    quantity: float
    recorded_unit_type: DefaultUnitType
    recorded_unit_amount: float
    recorded_unit_basis: UnitBasis
    recorded_unit_label: str | None
    meal_type: MealType
    food: DiaryFoodReference
    totals: NutritionTotals
    created_at: datetime


class AdminDiaryItem(BaseModel):
    id: UUID
    entry_date: date
    meal_type: MealType
    quantity: float
    food_name: str


class AdminDiaryPage(BaseModel):
    items: list[AdminDiaryItem]
    next_cursor: str | None


class DaySummary(BaseModel):
    date: date
    totals: NutritionTotals
    targets: TargetResponse | None = None
    nutrient_aggregates: list["DiaryNutrientAggregate"]
    overall_nutrient_coverage_percent: float | None


class DiaryNutrientTarget(BaseModel):
    type: Literal[
        "minimum", "maximum", "adequate", "recommended", "range", "monitor_only", "minimize"
    ]
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    unit: str


class DiaryNutrientAggregate(BaseModel):
    key: str
    amount: float | None
    known_entry_count: int
    total_entry_count: int
    coverage_percent: float | None
    coverage_state: Literal["no_entries", "all_unknown", "partial", "complete"]
    amount_qualifier: Literal["unavailable", "at_least", "exact"]
    target: DiaryNutrientTarget | None = None
    evaluation: str | None = None
    progress_percent: float | None = None
    remaining: float | None = None
    available: float | None = None


class WeekSummary(BaseModel):
    start: date
    end: date
    days: list[DaySummary]
    weekly_totals: NutritionTotals


class LabCreateRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_key: StrictStr
    entered_value: StrictStr
    entered_unit: StrictStr

    @field_validator("entered_value", mode="before")
    @classmethod
    def plain_decimal(cls, value: Any) -> str:
        try:
            return normalize_decimal_text(value)
        except ValueError as error:
            if str(error) == "The normalized decimal exceeds 128 characters":
                raise PydanticCustomError(
                    "LAB_VALUE_TOO_LONG", "تتجاوز القيمة حد التخزين المسموح."
                ) from error
            raise PydanticCustomError(
                "LAB_DECIMAL_INVALID", "أدخل قيمة رقمية صريحة غير سالبة."
            ) from error


class LabCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_date: date
    results: list[LabCreateRow] = Field(min_length=1, max_length=51)

    @field_validator("test_date", mode="before")
    @classmethod
    def iso_date_string(cls, value: Any) -> date:
        if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("A YYYY-MM-DD date string is required")
        return date.fromisoformat(value)

    @field_validator("results", mode="before")
    @classmethod
    def populated_batch(cls, value: Any) -> Any:
        if isinstance(value, list) and not value:
            raise PydanticCustomError("LAB_BATCH_EMPTY", "أدخل نتيجة واحدة على الأقل.")
        return value


class LabCreateReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_version: Literal[1] = 1
    result_ids: list[UUID]


class LabFieldError(BaseModel):
    loc: list[str | int]
    field: str | None = None
    test_key: str | None = None
    code: str | None = None
    msg: str
    type: str


class LabErrorResponse(BaseModel):
    detail: list[LabFieldError]


class LabStatus(BaseModel):
    code: str
    label_ar: str
    tone: str


class LabStatusZone(BaseModel):
    status: LabStatus
    low: str | None
    high: str | None
    low_inclusive: bool
    high_inclusive: bool


class LabEligibility(BaseModel):
    allowed: bool
    reason: Literal["profile_required", "adult_only", "read_only"] | None = None


class LabResultResponse(BaseModel):
    id: UUID
    test_key: str
    test_date: date
    entered_value: str
    entered_unit: str
    created_at: datetime
    updated_at: datetime
    display_value: str
    display_unit: str
    display_is_approximate: bool
    status: LabStatus
    age_years: int
    reference_zones: list[LabStatusZone]
    medical_rules_version: str


class LabCatalogTest(BaseModel):
    test_key: str
    name_ar: str
    name_en: str
    abbreviation: str | None
    primary_category: str
    measurement: str
    specimen_context: str
    default_input_unit: str
    canonical_unit: str
    supported_units: list[str]
    fasting_assumption: str
    panels: list[str]


class LabOverviewItem(BaseModel):
    test_key: str
    latest: LabResultResponse
    last_updated_at: datetime


class LabOverviewResponse(BaseModel):
    items: list[LabOverviewItem]
    eligibility: LabEligibility
    server_today: date
    medical_rules_version: str
    read_only: bool


class LabChartZoneSegment(BaseModel):
    from_date: date
    to_date_exclusive: date
    age_min: int
    zones: list[LabStatusZone]


class LabTestDetailResponse(BaseModel):
    test: LabCatalogTest
    results: list[LabResultResponse]
    chart_zones: list[LabChartZoneSegment]
    reference_at_date: date
    reference_zones: list[LabStatusZone]
    eligibility: LabEligibility
    server_today: date
    medical_rules_version: str
    read_only: bool
