from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text as sa_text,
)
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


class TargetProvenance(str, Enum):
    versioned_plan = "versioned_plan"
    legacy_unversioned = "legacy_unversioned"
    no_target_source = "no_target_source"


class FoodKind(str, Enum):
    simple = "simple"
    composite = "composite"
    unknown = "unknown"


class GroupDataStatus(str, Enum):
    known = "known"
    estimated = "estimated"
    unknown = "unknown"


class GroupDataCompleteness(str, Enum):
    complete = "complete"
    partial = "partial"
    unknown = "unknown"


class NutritionSourceType(str, Enum):
    laboratory_analysis = "laboratory_analysis"
    official_food_database = "official_food_database"
    official_product_label = "official_product_label"
    manufacturer_website = "manufacturer_website"
    official_restaurant = "official_restaurant"
    calculated_recipe = "calculated_recipe"
    manual_estimate = "manual_estimate"
    multiple_sources = "multiple_sources"
    unknown = "unknown"


class IngredientsSourceType(str, Enum):
    official_product_label = "official_product_label"
    manufacturer_website = "manufacturer_website"
    official_food_database = "official_food_database"
    official_restaurant = "official_restaurant"
    calculated_recipe = "calculated_recipe"
    manual_entry = "manual_entry"
    multiple_sources = "multiple_sources"
    unknown = "unknown"


class NovaClassification(str, Enum):
    one = "1"
    two = "2"
    three = "3"
    four = "4"
    unknown = "unknown"


class NovaReviewStatus(str, Enum):
    unreviewed = "unreviewed"
    reviewed = "reviewed"


class ContributionDataStatus(str, Enum):
    known = "known"
    estimated = "estimated"


class TargetPlanStatus(str, Enum):
    active = "active"
    scheduled = "scheduled"
    closed = "closed"
    superseded_before_effective = "superseded_before_effective"


class IdempotencyState(str, Enum):
    in_progress = "in_progress"
    completed = "completed"


class PrincipalStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class Principal(SQLModel, table=True):
    __tablename__ = "principal"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_principal_status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: PrincipalStatus = Field(
        default=PrincipalStatus.active,
        sa_column=Column(Text(), nullable=False, server_default=PrincipalStatus.active.value),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Profile(SQLModel, table=True):
    __tablename__ = "profile"
    __table_args__ = (
        UniqueConstraint("principal_id", name="uq_profile_principal_id"),
        UniqueConstraint("id", "principal_id", name="uq_profile_id_principal_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
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
    cut_intensity: float = Field(
        default=0.2,
        sa_column=Column(Numeric(4, 3), nullable=False, server_default="0.200"),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LegacyTargetTransitionSnapshot(SQLModel, table=True):
    __tablename__ = "legacy_target_transition_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "principal_id"],
            ["profile.id", "profile.principal_id"],
            name="fk_legacy_transition_profile_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("profile_id", name="uq_legacy_transition_profile"),
        UniqueConstraint("id", "principal_id", name="uq_legacy_transition_id_principal"),
        UniqueConstraint("principal_id", "transition_date", name="uq_legacy_transition_date"),
        CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_legacy_transition_timezone"),
        CheckConstraint(
            "target_document_schema_version = 1", name="ck_legacy_transition_schema_version"
        ),
        Index("ix_legacy_transition_principal_date", "principal_id", "transition_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    profile_id: uuid.UUID = Field(nullable=False)
    transition_date: date = Field(nullable=False)
    calendar_timezone: str = Field(sa_column=Column(String(64), nullable=False))
    target_document_schema_version: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    legacy_target_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class TargetPlan(SQLModel, table=True):
    __tablename__ = "target_plan"
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_target_plan_id_principal"),
        UniqueConstraint(
            "principal_id", "activation_idempotency_key", name="uq_target_plan_principal_key"
        ),
        ForeignKeyConstraint(
            ["profile_id", "principal_id"],
            ["profile.id", "profile.principal_id"],
            name="fk_target_plan_profile_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["predecessor_plan_id", "principal_id"],
            ["target_plan.id", "target_plan.principal_id"],
            name="fk_target_plan_predecessor_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["superseded_by_plan_id", "principal_id"],
            ["target_plan.id", "target_plan.principal_id"],
            name="fk_target_plan_superseding_owner",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "status IN ('active','scheduled','closed','superseded_before_effective')",
            name="ck_target_plan_status",
        ),
        CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_target_plan_period"),
        CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_target_plan_timezone"),
        CheckConstraint("calculation_document_schema_version > 0", name="ck_target_plan_document_version"),
        CheckConstraint(
            "(status IN ('active','closed') AND activated_at IS NOT NULL) OR "
            "(status IN ('scheduled','superseded_before_effective') AND activated_at IS NULL)",
            name="ck_target_plan_activation_state",
        ),
        CheckConstraint(
            "status <> 'superseded_before_effective' OR "
            "(superseded_at IS NOT NULL AND superseded_by_plan_id IS NOT NULL)",
            name="ck_target_plan_supersession_state",
        ),
        Index(
            "uq_target_plan_one_active", "principal_id", unique=True,
            postgresql_where=sa_text("status = 'active' AND effective_to IS NULL"),
            sqlite_where=sa_text("status = 'active' AND effective_to IS NULL"),
        ),
        Index(
            "uq_target_plan_one_scheduled", "principal_id", unique=True,
            postgresql_where=sa_text("status = 'scheduled'"),
            sqlite_where=sa_text("status = 'scheduled'"),
        ),
        Index("ix_target_plan_principal_effective", "principal_id", "effective_from"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    profile_id: uuid.UUID = Field(nullable=False)
    status: TargetPlanStatus = Field(sa_column=Column(Text(), nullable=False))
    effective_from: date = Field(nullable=False)
    effective_to: date | None = Field(default=None)
    calendar_timezone: str = Field(sa_column=Column(String(64), nullable=False))
    predecessor_plan_id: uuid.UUID | None = Field(default=None)
    superseded_by_plan_id: uuid.UUID | None = Field(default=None)
    activation_idempotency_key: str = Field(sa_column=Column(String(128), nullable=False))
    calculation_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    calculation_document_schema_version: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    calculation_engine_version: str = Field(sa_column=Column(String(32), nullable=False))
    nutrition_registry_version: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    activated_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    closed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    superseded_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency_record"
    __table_args__ = (
        UniqueConstraint("principal_id", "operation", "idempotency_key", name="uq_idempotency_scope"),
        CheckConstraint("state IN ('in_progress','completed')", name="ck_idempotency_state"),
        CheckConstraint(
            "(state='in_progress' AND response_status IS NULL AND response_document IS NULL AND completed_at IS NULL) OR "
            "(state='completed' AND response_status IS NOT NULL AND response_document IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_idempotency_completion",
        ),
        Index("ix_idempotency_expiry", "expires_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False))
    operation: str = Field(sa_column=Column(String(64), nullable=False))
    idempotency_key: str = Field(sa_column=Column(String(128), nullable=False))
    request_hash: str = Field(sa_column=Column(String(64), nullable=False))
    state: IdempotencyState = Field(sa_column=Column(Text(), nullable=False))
    response_status: int | None = Field(default=None, sa_column=Column(SmallInteger()))
    response_document: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON().with_variant(JSONB, "postgresql")))
    resource_type: str | None = Field(default=None, sa_column=Column(String(64)))
    resource_id: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Food(SQLModel, table=True):
    __tablename__ = "food"
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_food_id_principal_id"),
        CheckConstraint(
            "primary_category_key IS NULL OR primary_category_key IN ('vegetables','fruits','legumes','whole_grains','refined_grains','nuts_seeds','seafood','dairy_fortified_alternatives','eggs','poultry','red_meat','processed_meat','added_oils_fats','sweets','sugar_sweetened_beverages','unsweetened_beverages','herbs_spices','mixed_dish','other')",
            name="ck_food_primary_category",
        ),
        CheckConstraint("food_kind IN ('simple','composite','unknown')", name="ck_food_kind"),
        CheckConstraint(
            "group_data_status IN ('known','estimated','unknown')", name="ck_food_group_data_status"
        ),
        CheckConstraint(
            "group_data_completeness IN ('complete','partial','unknown')",
            name="ck_food_group_data_completeness",
        ),
        CheckConstraint(
            "nutrition_source_type IN ('laboratory_analysis','official_food_database','official_product_label','manufacturer_website','official_restaurant','calculated_recipe','manual_estimate','multiple_sources','unknown')",
            name="ck_food_nutrition_source_type",
        ),
        CheckConstraint(
            "ingredients_source_type IS NULL OR ingredients_source_type IN ('official_product_label','manufacturer_website','official_food_database','official_restaurant','calculated_recipe','manual_entry','multiple_sources','unknown')",
            name="ck_food_ingredients_source_type",
        ),
        CheckConstraint(
            "nova_classification IN ('1','2','3','4','unknown')", name="ck_food_nova_classification"
        ),
        CheckConstraint(
            "nova_review_status IN ('unreviewed','reviewed')", name="ck_food_nova_review_status"
        ),
        CheckConstraint(
            "(fiber_g IS NULL OR fiber_g >= 0) AND (added_sugar_g IS NULL OR added_sugar_g >= 0) AND (saturated_fat_g IS NULL OR saturated_fat_g >= 0) AND (trans_fat_g IS NULL OR trans_fat_g >= 0) AND (sodium_mg IS NULL OR sodium_mg >= 0) AND (potassium_mg IS NULL OR potassium_mg >= 0) AND (cholesterol_mg IS NULL OR cholesterol_mg >= 0) AND (calcium_mg IS NULL OR calcium_mg >= 0) AND (iron_mg IS NULL OR iron_mg >= 0) AND (magnesium_mg IS NULL OR magnesium_mg >= 0) AND (zinc_mg IS NULL OR zinc_mg >= 0) AND (selenium_mcg IS NULL OR selenium_mcg >= 0) AND (vitamin_b12_mcg IS NULL OR vitamin_b12_mcg >= 0) AND (folate_dfe_mcg IS NULL OR folate_dfe_mcg >= 0) AND (vitamin_a_rae_mcg IS NULL OR vitamin_a_rae_mcg >= 0) AND (iodine_mcg IS NULL OR iodine_mcg >= 0)",
            name="ck_food_wave1_exact_nutrients_nonnegative",
        ),
        CheckConstraint(
            "calories >= 0 AND protein_g >= 0 AND carb_g >= 0 AND fat_g >= 0",
            name="ck_food_core_nonnegative",
        ),
        CheckConstraint(
            "(CAST(nutrition_basis AS TEXT) = 'per_100g' AND CAST(unit_basis AS TEXT) = 'g') OR (CAST(nutrition_basis AS TEXT) = 'per_100ml' AND CAST(unit_basis AS TEXT) = 'ml')",
            name="ck_food_nutrition_unit_basis",
        ),
        Index("ix_food_principal_lower_name", "principal_id", sa_text("lower(name)")),
        Index("ix_food_principal_created_desc", "principal_id", sa_text("created_at DESC")),
        Index("ix_food_principal_primary_category", "principal_id", "primary_category_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    name: str = Field(index=True)
    brand: str | None = None
    category: str | None = None
    primary_category_key: str | None = Field(default=None, sa_column=Column(Text()))
    food_kind: FoodKind = Field(
        default=FoodKind.unknown,
        sa_column=Column(Text(), nullable=False, server_default=FoodKind.unknown.value),
    )
    group_data_status: GroupDataStatus = Field(
        default=GroupDataStatus.unknown,
        sa_column=Column(Text(), nullable=False, server_default=GroupDataStatus.unknown.value),
    )
    group_data_completeness: GroupDataCompleteness = Field(
        default=GroupDataCompleteness.unknown,
        sa_column=Column(
            Text(), nullable=False, server_default=GroupDataCompleteness.unknown.value
        ),
    )
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
    selenium_mcg: float | None = Field(default=None, sa_column=Column(Numeric(10, 3)))
    vitamin_d_mcg: float | None = Field(default=None, sa_column=Column(Numeric(7, 2)))
    vitamin_b12_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_c_mg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_a_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    vitamin_a_rae_mcg: float | None = Field(default=None, sa_column=Column(Numeric(10, 3)))
    folate_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    folate_dfe_mcg: float | None = Field(default=None, sa_column=Column(Numeric(10, 3)))
    vitamin_k_mcg: float | None = Field(default=None, sa_column=Column(Numeric(8, 2)))
    iodine_mcg: float | None = Field(default=None, sa_column=Column(Numeric(10, 3)))
    notes: str | None = None
    data_source: str | None = None
    nutrition_source_type: NutritionSourceType = Field(
        default=NutritionSourceType.unknown,
        sa_column=Column(Text(), nullable=False, server_default=NutritionSourceType.unknown.value),
    )
    nutrition_source_name: str | None = Field(default=None, sa_column=Column(Text()))
    nutrition_source_reference: str | None = Field(default=None, sa_column=Column(Text()))
    ingredients_text: str | None = Field(default=None, sa_column=Column(Text()))
    ingredients_source_type: IngredientsSourceType | None = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    ingredients_source_name: str | None = Field(default=None, sa_column=Column(Text()))
    ingredients_source_reference: str | None = Field(default=None, sa_column=Column(Text()))
    nova_classification: NovaClassification = Field(
        default=NovaClassification.unknown,
        sa_column=Column(Text(), nullable=False, server_default=NovaClassification.unknown.value),
    )
    nova_review_status: NovaReviewStatus = Field(
        default=NovaReviewStatus.unreviewed,
        sa_column=Column(Text(), nullable=False, server_default=NovaReviewStatus.unreviewed.value),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class FoodGroupContribution(SQLModel, table=True):
    __tablename__ = "food_group_contribution"
    __table_args__ = (
        ForeignKeyConstraint(
            ["food_id", "principal_id"],
            ["food.id", "food.principal_id"],
            name="fk_food_group_contribution_food_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint("food_id", "group_key", name="uq_food_group_contribution_food_group"),
        UniqueConstraint("id", "principal_id", name="uq_food_group_contribution_id_principal"),
        CheckConstraint(
            "amount_per_100_basis > 0 AND amount_per_100_basis <= 100",
            name="ck_food_group_contribution_amount",
        ),
        CheckConstraint(
            "data_status IN ('known', 'estimated')", name="ck_food_group_contribution_status"
        ),
        CheckConstraint(
            "group_key IN ('vegetables','fruits','legumes','whole_grains','refined_grains','nuts_seeds','seafood','dairy_fortified_alternatives','eggs','poultry','red_meat','processed_meat','added_oils_fats','sweets','sugar_sweetened_beverages','unsweetened_beverages','herbs_spices')",
            name="ck_food_group_contribution_key",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    food_id: uuid.UUID = Field(nullable=False, index=True)
    group_key: str = Field(sa_column=Column(Text(), nullable=False))
    subtype_key: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    amount_per_100_basis: float = Field(sa_column=Column(Numeric(6, 3), nullable=False))
    data_status: ContributionDataStatus = Field(sa_column=Column(Text(), nullable=False))
    food_group_rules_version: str = Field(max_length=32)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class FoodAnalyticalTrait(SQLModel, table=True):
    __tablename__ = "food_analytical_trait"
    __table_args__ = (
        ForeignKeyConstraint(
            ["food_id", "principal_id"],
            ["food.id", "food.principal_id"],
            name="fk_food_analytical_trait_food_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint("food_id", "trait_key", name="uq_food_analytical_trait_food_trait"),
        UniqueConstraint("id", "principal_id", name="uq_food_analytical_trait_id_principal"),
        CheckConstraint(
            "trait_key IN ('sweetened','non_nutritive_sweetened','processed','omega3_rich_seafood','calcium_fortified','unsaturated_fat_source','smoked','salted','fruit_liquid_100_percent','dried_fruit','starchy_root')",
            name="ck_food_analytical_trait_key",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    food_id: uuid.UUID = Field(nullable=False, index=True)
    trait_key: str = Field(sa_column=Column(Text(), nullable=False))
    food_group_rules_version: str = Field(max_length=32)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class DiaryEntry(SQLModel, table=True):
    __tablename__ = "diary_entry"
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_diary_entry_id_principal_id"),
        ForeignKeyConstraint(
            ["food_id", "principal_id"],
            ["food.id", "food.principal_id"],
            name="fk_diary_entry_food_owner",
        ),
        ForeignKeyConstraint(
            ["target_plan_id", "principal_id"],
            ["target_plan.id", "target_plan.principal_id"],
            name="fk_diary_entry_target_plan_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "target_provenance IN ('versioned_plan','legacy_unversioned','no_target_source')",
            name="ck_diary_entry_target_provenance",
        ),
        CheckConstraint(
            "(target_provenance = 'versioned_plan' AND target_plan_id IS NOT NULL) OR "
            "(target_provenance IN ('legacy_unversioned','no_target_source') AND target_plan_id IS NULL)",
            name="ck_diary_entry_target_binding",
        ),
        CheckConstraint(
            "snapshot_schema_version IS NULL OR snapshot_schema_version = 2",
            name="ck_diary_entry_snapshot_version",
        ),
        Index("ix_diary_entry_principal_date_meal_created", "principal_id", "entry_date", "meal_type", "created_at"),
        Index("ix_diary_entry_principal_target_plan", "principal_id", "target_plan_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        )
    )
    entry_date: date = Field(index=True)
    food_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("food.id", ondelete="SET NULL"), index=True, nullable=True),
    )
    target_plan_id: uuid.UUID | None = Field(default=None, nullable=True)
    target_provenance: TargetProvenance = Field(
        default=TargetProvenance.legacy_unversioned,
        sa_column=Column(Text(), nullable=False),
    )
    snapshot_schema_version: int | None = Field(
        default=None, sa_column=Column(SmallInteger(), nullable=True)
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
