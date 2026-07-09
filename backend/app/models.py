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
    protein_per_kg: float = Field(default=1.8, sa_column=Column(Numeric(4, 2), nullable=False))
    fat_pct: float = Field(default=0.25, sa_column=Column(Numeric(4, 2), nullable=False))
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Food(SQLModel, table=True):
    __tablename__ = "food"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    serving_label: str
    serving_grams: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    calories: float = Field(sa_column=Column(Numeric(8, 2), nullable=False))
    protein_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    carb_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    fat_g: float = Field(sa_column=Column(Numeric(7, 2), nullable=False))
    saturated_fat_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    trans_fat_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    cholesterol_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    sodium_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    fiber_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    total_sugars_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    added_sugar_g: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
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
    nutrition_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
