from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Enum as SAEnum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Sex(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class Goal(str, Enum):
    cut = "cut"
    maintain = "maintain"
    bulk = "bulk"


class NutritionBasis(str, Enum):
    per_100g = "per_100g"
    per_100ml = "per_100ml"


class DefaultUnitType(str, Enum):
    g = "g"
    ml = "ml"
    cup = "cup"
    slice = "slice"
    piece = "piece"
    scoop = "scoop"
    serving = "serving"
    tablespoon = "tablespoon"
    teaspoon = "teaspoon"


class UnitBasis(str, Enum):
    g = "g"
    ml = "ml"


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    unspecified = "unspecified"


class Profile(SQLModel, table=True):
    __tablename__ = "profile"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sex: Sex = Field(sa_column=Column(SAEnum(Sex, name="sex_enum"), nullable=False))
    birth_date: date
    height_cm: float = Field(sa_column=Column(Numeric(6, 2), nullable=False))
    weight_kg: float = Field(sa_column=Column(Numeric(6, 2), nullable=False))
    activity_level: ActivityLevel = Field(
        sa_column=Column(SAEnum(ActivityLevel, name="activity_level_enum"), nullable=False)
    )
    goal: Goal = Field(sa_column=Column(SAEnum(Goal, name="goal_enum"), nullable=False))
    protein_per_kg: float = Field(default=1.2, sa_column=Column(Numeric(4, 2), nullable=False))
    fat_pct: float = Field(default=0.25, sa_column=Column(Numeric(4, 2), nullable=False))
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Food(SQLModel, table=True):
    __tablename__ = "food"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    brand: str | None = None
    category: str | None = None
    nutrition_basis: NutritionBasis = Field(
        sa_column=Column(SAEnum(NutritionBasis, name="nutrition_basis_enum"), nullable=False)
    )
    default_unit_type: DefaultUnitType = Field(
        sa_column=Column(SAEnum(DefaultUnitType, name="default_unit_type_enum"), nullable=False)
    )
    unit_amount: float = Field(sa_column=Column(Numeric(8, 2), nullable=False))
    unit_basis: UnitBasis = Field(
        sa_column=Column(SAEnum(UnitBasis, name="unit_basis_enum"), nullable=False)
    )
    calories: float = Field(sa_column=Column(Numeric(8, 2), nullable=False))
    protein_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    carb_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    fat_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    fiber_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    sugar_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    added_sugar_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    saturated_fat_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    trans_fat_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    sodium_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    cholesterol_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    potassium_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    calcium_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    iron_mg: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    magnesium_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    zinc_mg: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    vitamin_d_mcg: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    vitamin_b12_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_c_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_a_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    folate_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_k_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    notes: str | None = None
    data_source: str | None = None
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DiaryEntry(SQLModel, table=True):
    __tablename__ = "diary_entry"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entry_date: date = Field(index=True)
    food_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("food.id", ondelete="SET NULL"), index=True, nullable=True),
    )
    quantity: float = Field(sa_column=Column(Numeric(8, 3), nullable=False))
    meal_type: MealType = Field(
        default=MealType.unspecified,
        sa_column=Column(SAEnum(MealType, name="meal_type_enum"), nullable=False),
    )
    nutrition_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
