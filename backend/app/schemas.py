from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ActivityLevel, DefaultUnitType, Goal, MealType, NutritionBasis, Sex, UnitBasis
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
    target_type: Literal["minimum", "maximum", "range", "monitor_only"]
    target_source: Literal["fixed", "calculated", "reference", "manual", "clinical"]
    target_value: float | None = None


class TargetResponse(BaseModel):
    bmr: float
    tdee: float
    target_calories: int
    protein_g: float
    fat_g: float
    carb_g: float
    carb_clamped: bool = False
    additional_targets: list[AdditionalNutrientTarget] = Field(default_factory=list)


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

    @model_validator(mode="before")
    @classmethod
    def apply_sex_aware_fat_default(cls, value: Any) -> Any:
        if isinstance(value, dict) and "fat_pct" not in value:
            value = dict(value)
            value["fat_pct"] = 0.30 if value.get("sex") in {Sex.female, "female"} else 0.25
        return value


class ProfileResponse(ProfileUpsert):
    id: UUID
    updated_at: datetime
    targets: TargetResponse

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
    "vitamin_d_mcg": 250,
    "vitamin_b12_mcg": 1000,
    "vitamin_c_mg": 5000,
    "vitamin_a_mcg": 3000,
    "folate_mcg": 2000,
    "vitamin_k_mcg": 2000,
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


class FoodBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    brand: str | None = None
    category: str | None = None
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
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    notes: str | None = None
    data_source: str | None = None

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
        if value is not None and saturated_fat_g is not None and fat_g is not None and value + saturated_fat_g > fat_g:
            raise ValueError(SATURATED_TRANS_GT_FAT_MESSAGE)
        return value


class FoodCreate(FoodBase):
    id: UUID | None = None


class FoodUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    category: str | None = None
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
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    vitamin_k_mcg: float | None = None
    notes: str | None = None
    data_source: str | None = None

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
        if value is not None and saturated_fat_g is not None and fat_g is not None and value + saturated_fat_g > fat_g:
            raise ValueError(SATURATED_TRANS_GT_FAT_MESSAGE)
        return value


class FoodResponse(FoodBase):
    id: UUID
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
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    vitamin_k_mcg: float | None = None
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
    vitamin_d_mcg: float | None = None
    vitamin_b12_mcg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_a_mcg: float | None = None
    folate_mcg: float | None = None
    vitamin_k_mcg: float | None = None
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
        if value > date.today():
            raise ValueError("لا يمكن تسجيل يوميات بتاريخ مستقبلي.")
        return value


class DiaryEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: float = Field(gt=0, le=50)
    meal_type: MealType | None = None


class DiaryEntryResponse(BaseModel):
    id: UUID
    entry_date: date
    food_id: UUID | None
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
