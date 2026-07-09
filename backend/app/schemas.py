from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import ActivityLevel, Goal, Sex


class TargetResponse(BaseModel):
    bmr: float
    tdee: float
    target_calories: int
    protein_g: float
    fat_g: float
    carb_g: float
    carb_clamped: bool = False


class ProfileUpsert(BaseModel):
    sex: Sex
    birth_date: date
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    activity_level: ActivityLevel
    goal: Goal
    protein_per_kg: float = Field(default=1.8, ge=1.6, le=2.2)
    fat_pct: float = Field(default=0.25, ge=0.2, le=0.3)


class ProfileResponse(ProfileUpsert):
    id: UUID
    updated_at: datetime
    targets: TargetResponse

    model_config = ConfigDict(from_attributes=True)


class FoodBase(BaseModel):
    name: str = Field(min_length=1)
    serving_label: str = Field(min_length=1)
    serving_grams: float | None = Field(default=None, gt=0)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carb_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    trans_fat_g: float | None = Field(default=None, ge=0)
    cholesterol_mg: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    total_sugars_g: float | None = Field(default=None, ge=0)
    added_sugar_g: float | None = Field(default=None, ge=0)


class FoodCreate(FoodBase):
    id: UUID | None = None


class FoodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    serving_label: str | None = Field(default=None, min_length=1)
    serving_grams: float | None = Field(default=None, gt=0)
    calories: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carb_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    saturated_fat_g: float | None = Field(default=None, ge=0)
    trans_fat_g: float | None = Field(default=None, ge=0)
    cholesterol_mg: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    total_sugars_g: float | None = Field(default=None, ge=0)
    added_sugar_g: float | None = Field(default=None, ge=0)


class FoodResponse(FoodBase):
    id: UUID
    net_carbs_g: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NutritionSnapshot(FoodBase):
    food_id: UUID


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
    total_sugars_g: float | None = None
    added_sugar_g: float | None = None
    net_carbs_g: float = 0


class DiaryEntryCreate(BaseModel):
    id: UUID | None = None
    entry_date: date
    food_id: UUID
    quantity: float = Field(gt=0)


class DiaryEntryUpdate(BaseModel):
    entry_date: date | None = None
    food_id: UUID | None = None
    quantity: float | None = Field(default=None, gt=0)


class DiaryEntryResponse(BaseModel):
    id: UUID
    entry_date: date
    food_id: UUID | None
    quantity: float
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
