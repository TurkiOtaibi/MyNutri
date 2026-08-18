from datetime import date, datetime, timedelta
from contextvars import ContextVar, Token
from enum import Enum
import math
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    ActivityLevel,
    BakedGoodType,
    ContributionDataStatus,
    DefaultUnitType,
    FoodKind,
    FoodStatus,
    Goal,
    GrainStarchType,
    GrainType,
    GroupDataCompleteness,
    GroupDataStatus,
    IngredientsSourceType,
    MealType,
    NovaClassification,
    NovaReviewStatus,
    NutritionBasis,
    NutritionSourceType,
    PrincipalRole,
    PrincipalStatus,
    Sex,
    UnitBasis,
)

from app.nutrition_rules.calculation import age_on
from app.nutrition_rules.registry import FOOD_CATEGORIES, FOOD_GROUPS, SOURCE_RELIABILITY, TRAITS
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

_diary_validation_date: ContextVar[date | None] = ContextVar(
    "diary_validation_date", default=None
)


def set_diary_validation_date(value: date) -> Token[date | None]:
    return _diary_validation_date.set(value)


def reset_diary_validation_date(token: Token[date | None]) -> None:
    _diary_validation_date.reset(token)


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


class RegistryFoodGroupDefinition(RegistryLabelDefinition):
    model_config = ConfigDict(extra="allow")
    subtype_labels_ar: dict[str, str]
    subtypes: dict[str, Any] | list[str] | None = None


class RegistrySourceTypeDefinition(BaseModel):
    type: NutritionSourceType
    label_ar: str
    reliability: Literal["high", "medium", "low", "mixed", "unknown"]


class RegistryIngredientSourceDefinition(BaseModel):
    type: IngredientsSourceType
    label_ar: str


class RegistryNovaDefinition(BaseModel):
    classifications: list[int | Literal["unknown"]]
    labels_ar: dict[str, str]
    review_statuses: list[Literal["unreviewed", "reviewed"]]
    automated_suggestions: Literal[False]


class NutritionRegistryResponse(BaseModel):
    nutrition_registry_version: str
    calculation_engine_version: str
    food_group_rules_version: str
    source_reliability_rules_version: str
    nova_rules_version: str
    registry_schema_version: Literal[2]
    snapshot_schema_version: Literal[3]
    analysis_rules_version: Literal["w3-analysis-1.0.0"]
    analysis_rules_status: Literal["active"]
    rules_manifest_hash: str
    calculation_policy: dict[str, Any]
    nutrients: list[RegistryNutrientDefinition]
    target_types: list[str]
    food_categories: list[str]
    food_category_definitions: list[RegistryLabelDefinition]
    grain_type_definitions: list[RegistryLabelDefinition]
    baked_good_type_definitions: list[RegistryLabelDefinition]
    grain_starch_type_definitions: list[RegistryLabelDefinition]
    food_groups: list[dict[str, Any]]
    food_group_definitions: list[RegistryFoodGroupDefinition]
    traits: list[RegistryLabelDefinition]
    source_types: list[RegistrySourceTypeDefinition]
    ingredient_source_types: list[IngredientsSourceType]
    ingredient_source_definitions: list[RegistryIngredientSourceDefinition]
    reliability_levels: list[RegistryLabelDefinition]
    nova: RegistryNovaDefinition
    analysis_metrics: list[dict[str, str]]


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

    @field_validator(
        "height_cm", "weight_kg", "protein_per_kg", "fat_pct", mode="before"
    )
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


def validate_profile_domain(
    profile: ProfileUpsert, effective_date: date
) -> ProfileUpsert:
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

FOOD_CORE_NUMERIC_FIELDS = (
    "unit_amount",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
)
FOOD_NUMERIC_FIELDS = FOOD_CORE_NUMERIC_FIELDS + tuple(OPTIONAL_NUTRIENT_MAX)
FOOD_GROUP_NUMERIC_FIELDS = ("amount_per_100_basis",)
FOOD_RESPONSE_DERIVED_NUMERIC_FIELDS = ("net_carbs_g",)

FOOD_TEXT_MAX: dict[str, int] = {
    "name": 120,
    "brand": 80,
    "notes": 500,
    "data_source": 120,
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
    amount_per_100_basis: float = Field(gt=0, le=100, allow_inf_nan=False)
    data_status: ContributionDataStatus

    @field_validator("amount_per_100_basis", mode="before")
    @classmethod
    def make_non_finite_validation_input_json_safe(cls, value: Any) -> Any:
        return _finite_number_input(value)

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
    food_category_key: str
    grain_type: GrainType | None = None
    baked_good_type: BakedGoodType | None = None
    grain_starch_type: GrainStarchType | None = None
    food_kind: FoodKind = FoodKind.unknown
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
    data_source: str | None = None
    nutrition_source: NutritionSourceInput = Field(default_factory=NutritionSourceInput)
    ingredients: IngredientsInput = Field(default_factory=IngredientsInput)
    nova: NovaInput | None = None
    group_contributions: list[FoodGroupContributionInput] = Field(default_factory=list)
    analytical_traits: list[str] = Field(default_factory=list)

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

    @field_validator("brand", "notes", "data_source", mode="before")
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
    def validate_controlled_food_data(self):
        if self.food_category_key not in FOOD_CATEGORIES:
            raise ValueError("فئة الطعام غير معتمدة.")
        if self.food_category_key == "baked_goods":
            if self.baked_good_type is None:
                raise ValueError("نوع المخبوزات مطلوب لفئة المخبوزات.")
            if self.grain_type is None:
                raise ValueError("نوع الحبوب مطلوب لفئة المخبوزات.")
            if self.grain_starch_type is not None:
                raise ValueError("نوع الحبوب والنشويات غير متاح لفئة المخبوزات.")
        elif self.food_category_key == "grains_starches":
            if self.grain_starch_type is None:
                raise ValueError("نوع الحبوب أو النشويات مطلوب لهذه الفئة.")
            if self.grain_type is None:
                raise ValueError("نوع الحبوب مطلوب لفئة الحبوب والنشويات.")
            if self.baked_good_type is not None:
                raise ValueError("نوع المخبوزات غير متاح لفئة الحبوب والنشويات.")
        elif any(
            value is not None
            for value in (self.grain_type, self.baked_good_type, self.grain_starch_type)
        ):
            raise ValueError("تفاصيل الحبوب والمخبوزات غير متاحة لفئة الطعام المحددة.")
        groups = [item.group_key for item in self.group_contributions]
        if len(groups) != len(set(groups)):
            raise ValueError("لا يمكن تكرار المجموعة الغذائية للطعام نفسه.")
        if sum(item.amount_per_100_basis for item in self.group_contributions) > 100:
            raise ValueError("مجموع مساهمات المجموعات الغذائية لا يمكن أن يتجاوز 100.")
        if len(self.analytical_traits) != len(set(self.analytical_traits)):
            raise ValueError("لا يمكن تكرار السمة التحليلية.")
        if any(item not in TRAIT_KEYS for item in self.analytical_traits):
            raise ValueError("سمة تحليلية غير معتمدة.")
        return self


class FoodCreate(FoodBase):
    id: UUID | None = None


class FoodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    brand: str | None = None
    food_category_key: str | None = None
    grain_type: GrainType | None = None
    baked_good_type: BakedGoodType | None = None
    grain_starch_type: GrainStarchType | None = None
    food_kind: FoodKind | None = None
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
    data_source: str | None = None
    nutrition_source: NutritionSourceInput | None = None
    ingredients: IngredientsInput | None = None
    nova: NovaInput | None = None
    group_contributions: list[FoodGroupContributionInput] | None = None
    analytical_traits: list[str] | None = None

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

    @field_validator("brand", "notes", "data_source", mode="before")
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
    status: FoodStatus
    group_data_status: GroupDataStatus
    group_data_completeness: GroupDataCompleteness
    taxonomy_review_required: bool
    nutrition_source: NutritionSourceResponse
    nova: NovaResponse
    group_contributions: list[FoodGroupContributionResponse]
    analytical_traits: list[str]
    legacy_nutrition: LegacyNutritionResponse
    net_carbs_g: float
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

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
    uncategorized_count: int


class FoodDeleteResponse(BaseModel):
    disposition: Literal["deleted", "archived"]


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


class DiaryLoggingStatus(str, Enum):
    unregistered = "unregistered"
    partial = "partial"
    complete = "complete"


class DiaryDayStatusCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)


class DiaryDayStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    logging_status: DiaryLoggingStatus
    logging_status_version: int = Field(ge=0)
    entry_count: int = Field(ge=0)
    analysis_eligible: bool
    completed_at: datetime | None
    calendar: CalendarAuthorityResponse


class AdminDiaryDayStatusPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DiaryDayStatusResponse]


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
    pending_plan: TargetPlanSummary | None
    plan_history: TargetPlanHistoryResponse


class NutritionSnapshot(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

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

        authoritative_date = _diary_validation_date.get() or current_diary_date()
        if value > authoritative_date:
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


class _AnalysisClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


AnalysisSafetyFlag = Literal[
    "incompatible_target",
    "incompatible_source_versions",
    "invalid_day_evidence",
    "missing_target",
    "non_finite_source_fact",
    "profile_specialist_review_required",
    "stale_evidence",
    "unsupported_analysis_rules",
    "unsupported_food_group_rules",
    "unsupported_nova_rules",
    "unsupported_registry",
    "unsupported_snapshot_schema",
    "very_low_energy_blocked",
]

AnalysisStaleReason = Literal[
    "day_reopened",
    "day_version_changed",
    "target_source_changed",
    "source_snapshot_corrected",
    "source_version_unsupported",
]


class TargetPlanAnalysisRefV1(_AnalysisClosedModel):
    id: UUID
    effective_from: date
    effective_to: date | None
    calculation_document_schema_version: int = Field(ge=1)
    calculation_engine_version: str = Field(min_length=1)
    nutrition_registry_version: str = Field(min_length=1)
    safety_outcome: Literal[
        "normal", "specialist_review_required", "very_low_energy_blocked"
    ]
    target_document_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class OpaqueEvidenceRefV1(_AnalysisClosedModel):
    source_ref: UUID
    diary_date: date
    source_version: str = Field(min_length=1)


class AnalysisContributorV1(OpaqueEvidenceRefV1):
    contribution_value: float = Field(ge=0)
    unit: str = Field(min_length=1)
    relation: Literal["supports_observed_value"] = "supports_observed_value"


class AnalysisDayMetricValueV1(_AnalysisClosedModel):
    metric_key: str = Field(min_length=1)
    value: float | None
    value_state: Literal["known", "explicit_zero", "unknown"]
    known_entry_count: int = Field(ge=0)
    total_entry_count: int = Field(ge=0)
    amount_qualifier: Literal["exact", "at_least", "unavailable"]
    unit: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_value_state(self):
        if self.known_entry_count > self.total_entry_count:
            raise ValueError("known entry count exceeds total")
        if self.value_state == "unknown" and self.value is not None:
            raise ValueError("unknown value must be null")
        if self.value_state == "explicit_zero" and self.value != 0:
            raise ValueError("explicit zero must equal zero")
        if self.value_state == "known" and self.value is None:
            raise ValueError("known value is required")
        return self


class AnalysisDayFactV1(_AnalysisClosedModel):
    date: date
    logging_status: Literal["unregistered", "partial", "complete"]
    logging_status_version: int = Field(ge=0)
    entry_count: int = Field(ge=0)
    analysis_eligible: bool
    completed_at: datetime | None
    snapshot_schema_versions: list[int]
    metric_values: list[AnalysisDayMetricValueV1]

    @model_validator(mode="after")
    def validate_day(self):
        if self.analysis_eligible != (self.logging_status == "complete"):
            raise ValueError("analysis eligibility contradicts logging status")
        if self.logging_status != "complete" and self.metric_values:
            raise ValueError("ineligible day cannot expose metric values")
        if self.snapshot_schema_versions != sorted(set(self.snapshot_schema_versions)):
            raise ValueError("snapshot schema versions must be sorted and unique")
        keys = [item.metric_key for item in self.metric_values]
        if keys != sorted(set(keys)):
            raise ValueError("metric values must be sorted and unique")
        return self


class AnalysisMetricTargetV1(_AnalysisClosedModel):
    type: Literal["minimum", "maximum", "range"]
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    source_plan_ids: list[UUID]

    @model_validator(mode="after")
    def validate_target(self):
        if self.source_plan_ids != sorted(set(self.source_plan_ids), key=str):
            raise ValueError("target plan IDs must be sorted and unique")
        if self.type == "range":
            if self.value is not None or self.lower is None or self.upper is None or self.lower > self.upper:
                raise ValueError("range requires ordered lower and upper")
        elif self.value is None or self.lower is not None or self.upper is not None:
            raise ValueError("minimum/maximum requires value only")
        return self


class PeriodMetricEvidenceV1(_AnalysisClosedModel):
    value: float | None
    value_state: Literal["known", "explicit_zero", "unknown"]
    amount_qualifier: Literal["exact", "at_least", "unavailable"]
    complete_day_count: int = Field(ge=0, le=7)
    numeric_day_count: int = Field(ge=0, le=7)
    known_entry_count: int = Field(ge=0)
    total_entry_count: int = Field(ge=0)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    confidence: Literal["strong", "limited", "unavailable"]
    status: Literal[
        "below_target",
        "at_target",
        "within_target",
        "above_target",
        "observed",
        "target_incompatible",
        "unavailable",
    ]
    evidence_refs: list[OpaqueEvidenceRefV1]

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.numeric_day_count > self.complete_day_count:
            raise ValueError("numeric days exceed complete days")
        if self.known_entry_count > self.total_entry_count:
            raise ValueError("known entries exceed total")
        if self.value_state == "unknown" and self.value is not None:
            raise ValueError("unknown value must be null")
        if self.value_state == "explicit_zero" and self.value != 0:
            raise ValueError("explicit zero must equal zero")
        keys = [(item.diary_date, str(item.source_ref)) for item in self.evidence_refs]
        if keys != sorted(set(keys)):
            raise ValueError("evidence references must be sorted and unique")
        return self


class AnalysisComparisonV1(_AnalysisClosedModel):
    status: Literal[
        "improved",
        "worsened",
        "no_material_change",
        "descriptive_increase",
        "descriptive_decrease",
        "descriptive_change",
        "not_comparable",
    ]
    reason: Literal[
        "comparable",
        "insufficient_complete_days",
        "insufficient_coverage",
        "limited_coverage",
        "coverage_mismatch",
        "target_incompatible",
        "version_incompatible",
        "invalid_target",
        "stale_evidence",
        "unavailable_value",
    ]
    difference: float | None
    normalized_adverse_delta: float | None


class AnalysisPersistenceV1(_AnalysisClosedModel):
    kind: Literal["same_direction_two_period"] = "same_direction_two_period"
    qualifies: bool
    reason: Literal[
        "qualified",
        "current_not_qualifying",
        "previous_not_qualifying",
        "insufficient_complete_days",
        "insufficient_coverage",
        "target_changed",
        "version_incompatible",
        "stale_evidence",
        "missing_previous",
    ]


class AnalysisContributorsV1(_AnalysisClosedModel):
    current: list[AnalysisContributorV1] = Field(max_length=5)
    previous: list[AnalysisContributorV1] = Field(max_length=5)


class AnalysisMetricFactV1(_AnalysisClosedModel):
    metric_key: str = Field(min_length=1)
    metric_kind: Literal[
        "daily_average",
        "period_total",
        "occurrence_days",
        "share_percent",
        "diversity_count",
        "calorie_share",
    ]
    unit: str = Field(min_length=1)
    aggregation: Literal[
        "average_numeric_days",
        "sum_period",
        "distinct_positive_dates",
        "ratio_percent",
        "distinct_source_count",
    ]
    direction: Literal["minimum", "maximum", "range", "minimize", "monitor_only"]
    target: AnalysisMetricTargetV1 | None
    current: PeriodMetricEvidenceV1
    previous: PeriodMetricEvidenceV1
    comparison: AnalysisComparisonV1
    persistence: AnalysisPersistenceV1
    contributors: AnalysisContributorsV1


class WeeklyPriorityAnalysisInputV1(_AnalysisClosedModel):
    interface_version: Literal[1] = 1
    principal_ref: UUID
    source_analysis_id: UUID
    source_analysis_revision: int = Field(ge=1)
    generated_at: datetime
    as_of_diary_date: date
    calendar_timezone: Literal["Asia/Riyadh"]
    period_start: date
    period_end: date
    previous_period_start: date
    previous_period_end: date
    analysis_rules_version: str = Field(min_length=1)
    nutrition_registry_version: str = Field(min_length=1)
    food_group_rules_version: str = Field(min_length=1)
    nova_rules_version: str = Field(min_length=1)
    snapshot_schema_versions: list[int]
    target_plan_refs: list[TargetPlanAnalysisRefV1]
    days: list[AnalysisDayFactV1] = Field(min_length=7, max_length=7)
    previous_period: list[AnalysisDayFactV1] = Field(min_length=7, max_length=7)
    metric_facts: list[AnalysisMetricFactV1]
    safety_flags: list[AnalysisSafetyFlag]

    @model_validator(mode="after")
    def validate_projection(self):
        if self.snapshot_schema_versions != sorted(set(self.snapshot_schema_versions)):
            raise ValueError("snapshot schema versions must be sorted and unique")
        if self.safety_flags != sorted(set(self.safety_flags)):
            raise ValueError("safety flags must be sorted and unique")
        if [item.date for item in self.days] != sorted(item.date for item in self.days):
            raise ValueError("current days must be sorted")
        if [item.date for item in self.previous_period] != sorted(item.date for item in self.previous_period):
            raise ValueError("previous days must be sorted")
        if [item.metric_key for item in self.metric_facts] != sorted({item.metric_key for item in self.metric_facts}):
            raise ValueError("metric facts must be sorted and unique")
        if self.period_end - self.period_start != timedelta(days=6):
            raise ValueError("current period must contain seven days")
        if self.previous_period_end - self.previous_period_start != timedelta(days=6):
            raise ValueError("previous period must contain seven days")
        if self.previous_period_end + timedelta(days=1) != self.period_start:
            raise ValueError("periods must be contiguous")
        return self


class AnalysisSourceVersionBundleV1(_AnalysisClosedModel):
    analysis_rules_version: str
    nutrition_registry_version: str
    calculation_engine_version: str
    food_group_rules_version: str
    source_reliability_rules_version: str
    nova_rules_version: str
    snapshot_schema_versions: list[int]
    status_evidence_version: int = Field(ge=1)
    rules_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class NutritionPatternAnalysisResponseV1(_AnalysisClosedModel):
    source_analysis_id: UUID
    source_analysis_revision: int = Field(ge=1)
    lifecycle_status: Literal["current", "stale", "superseded"]
    stale_reasons: list[AnalysisStaleReason]
    as_of_diary_date: date
    period_start: date
    period_end: date
    previous_period_start: date
    previous_period_end: date
    complete_day_count: int = Field(ge=0, le=7)
    previous_complete_day_count: int = Field(ge=0, le=7)
    metric_summaries: list[AnalysisMetricFactV1]
    source_versions: AnalysisSourceVersionBundleV1
    priority_input: WeeklyPriorityAnalysisInputV1
    generated_at: datetime
    finalized_at: datetime
    etag: str


class AnalysisEvaluateCommandV1(_AnalysisClosedModel):
    expected_current_revision: int | None = Field(default=None, ge=1)


class NutritionPatternAnalysisHistoryItemV1(_AnalysisClosedModel):
    source_analysis_id: UUID
    source_analysis_revision: int = Field(ge=1)
    lifecycle_status: Literal["current", "stale", "superseded"]
    as_of_diary_date: date
    period_start: date
    period_end: date
    previous_period_start: date
    previous_period_end: date
    analysis_rules_version: str
    complete_day_count: int = Field(ge=0, le=7)
    previous_complete_day_count: int = Field(ge=0, le=7)
    generated_at: datetime
    finalized_at: datetime
    etag: str


class NutritionPatternAnalysisHistoryPageV1(_AnalysisClosedModel):
    items: list[NutritionPatternAnalysisHistoryItemV1]
    next_cursor: str | None


class NutritionAnalysisMonitoringResponseV1(_AnalysisClosedModel):
    iso_week: str
    total_count: int = Field(ge=0)
    status_counts: dict[str, int]
    version_counts: dict[str, int]
    complete_day_band_counts: dict[str, int]
    coverage_band_counts: dict[str, int]
    stale_reason_counts: dict[str, int]
    latency_band_counts: dict[str, int]
    model_config = ConfigDict(from_attributes=True)


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
    target_provenance: Literal["versioned_plan", "legacy_unversioned", "no_target_source"]
    nutrient_aggregates: list["DiaryNutrientAggregate"]
    overall_nutrient_coverage_percent: float | None
    logging_status: DiaryLoggingStatus
    logging_status_version: int = Field(ge=0)
    entry_count: int = Field(ge=0)
    analysis_eligible: bool
    completed_at: datetime | None


class DiaryNutrientTarget(BaseModel):
    type: Literal[
        "minimum", "maximum", "adequate", "recommended", "range", "monitor_only", "minimize"
    ]
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    unit: str
    source: Literal["versioned_plan", "legacy_unversioned"]


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
