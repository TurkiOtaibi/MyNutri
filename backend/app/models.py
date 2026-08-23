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
    BigInteger,
    Integer,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    desc,
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


class DiaryDayStatusValue(str, Enum):
    partial = "partial"
    complete = "complete"


class DiaryDayStatusEvent(str, Enum):
    entry_created = "entry_created"
    entry_edited = "entry_edited"
    entry_deleted = "entry_deleted"
    completed = "completed"
    reopened = "reopened"


class PrincipalStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class PrincipalRole(str, Enum):
    user = "user"
    admin = "admin"


class FoodStatus(str, Enum):
    active = "active"
    archived = "archived"


class GrainType(str, Enum):
    whole = "whole"
    refined = "refined"
    mixed = "mixed"
    grain_free = "grain_free"
    unknown = "unknown"


class BakedGoodType(str, Enum):
    arabic_bread = "arabic_bread"
    toast = "toast"
    rolls_wraps = "rolls_wraps"
    burger_bun = "burger_bun"
    flatbread = "flatbread"
    pastries = "pastries"
    cake = "cake"
    biscuits_cookies = "biscuits_cookies"
    other = "other"


class GrainStarchType(str, Enum):
    rice = "rice"
    pasta = "pasta"
    oats = "oats"
    breakfast_cereal = "breakfast_cereal"
    bulgur = "bulgur"
    quinoa = "quinoa"
    flour = "flour"
    other = "other"


class Principal(SQLModel, table=True):
    __tablename__ = "principal"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_principal_status"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_principal_role"),
        UniqueConstraint("auth_user_id", name="uq_principal_auth_user_id"),
        Index(
            "uq_principal_lower_email",
            sa_text("lower(email)"),
            unique=True,
            postgresql_where=sa_text("email IS NOT NULL"),
            sqlite_where=sa_text("email IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    auth_user_id: uuid.UUID | None = Field(default=None)
    email: str | None = Field(default=None, sa_column=Column(String(320), nullable=True))
    display_name: str | None = Field(default=None, sa_column=Column(String(120), nullable=True))
    role: PrincipalRole = Field(
        default=PrincipalRole.user,
        sa_column=Column(Text(), nullable=False, server_default=PrincipalRole.user.value),
    )
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
        CheckConstraint(
            "cut_intensity IN (0.150,0.200,0.250)",
            name="ck_profile_cut_intensity",
        ),
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
        CheckConstraint(
            "jsonb_typeof(legacy_target_document)='object' AND "
            "legacy_target_document->>'schema_version'='1' AND "
            "legacy_target_document->>'source'='legacy_unversioned_transition' AND "
            "jsonb_typeof(legacy_target_document->'captured_profile_inputs')='object' AND "
            "jsonb_typeof(legacy_target_document->'resolved_targets')='object'",
            name="ck_legacy_transition_document_shape",
        ).ddl_if(dialect="postgresql"),
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
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="ck_target_plan_period"
        ),
        CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_target_plan_timezone"),
        CheckConstraint(
            "calculation_document_schema_version > 0", name="ck_target_plan_document_version"
        ),
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
            "uq_target_plan_one_active",
            "principal_id",
            unique=True,
            postgresql_where=sa_text("status = 'active' AND effective_to IS NULL"),
            sqlite_where=sa_text("status = 'active' AND effective_to IS NULL"),
        ),
        Index(
            "uq_target_plan_one_scheduled",
            "principal_id",
            unique=True,
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
    calculation_document_schema_version: int = Field(
        sa_column=Column(SmallInteger(), nullable=False)
    )
    calculation_engine_version: str = Field(sa_column=Column(String(32), nullable=False))
    nutrition_registry_version: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    activated_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    closed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    superseded_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency_record"
    __table_args__ = (
        UniqueConstraint(
            "principal_id", "operation", "idempotency_key", name="uq_idempotency_scope"
        ),
        CheckConstraint("state IN ('in_progress','completed')", name="ck_idempotency_state"),
        CheckConstraint(
            "(state='in_progress' AND response_status IS NULL AND response_document IS NULL AND completed_at IS NULL) OR "
            "(state='completed' AND response_status IS NOT NULL AND response_document IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_idempotency_completion",
        ),
        Index("ix_idempotency_expiry", "expires_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    operation: str = Field(sa_column=Column(String(64), nullable=False))
    idempotency_key: str = Field(sa_column=Column(String(128), nullable=False))
    request_hash: str = Field(sa_column=Column(String(64), nullable=False))
    state: IdempotencyState = Field(sa_column=Column(Text(), nullable=False))
    response_status: int | None = Field(default=None, sa_column=Column(SmallInteger()))
    response_document: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON().with_variant(JSONB, "postgresql"))
    )
    resource_type: str | None = Field(default=None, sa_column=Column(String(64)))
    resource_id: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


FOOD_NUMERIC_COLUMNS = (
    "unit_amount",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "added_sugar_g",
    "saturated_fat_g",
    "trans_fat_g",
    "sodium_mg",
    "cholesterol_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "selenium_mcg",
    "vitamin_d_mcg",
    "vitamin_b12_mcg",
    "vitamin_c_mg",
    "vitamin_a_mcg",
    "vitamin_a_rae_mcg",
    "folate_mcg",
    "folate_dfe_mcg",
    "vitamin_k_mcg",
    "iodine_mcg",
)
FOOD_GROUP_NUMERIC_COLUMNS = ("amount_per_100_basis",)


def _finite_numeric_check(columns: tuple[str, ...]) -> str:
    special_values = "('NaN', 'Infinity', '-Infinity')"
    return " AND ".join(f"{column} NOT IN {special_values}" for column in columns)


class Food(SQLModel, table=True):
    __tablename__ = "food"
    __table_args__ = (
        CheckConstraint(
            "food_category_key IN ('vegetables','fruits','legumes','grains_starches','baked_goods','nuts_seeds','seafood','dairy_fortified_alternatives','eggs','poultry','red_meat','processed_meat','added_oils_fats','sweets','sugar_sweetened_beverages','unsweetened_beverages','herbs_spices','mixed_dish','other')",
            name="ck_food_category_v2",
        ),
        CheckConstraint("status IN ('active','archived')", name="ck_food_status"),
        CheckConstraint(
            "grain_type IS NULL OR grain_type IN ('whole','refined','mixed','grain_free','unknown')",
            name="ck_food_grain_type",
        ),
        CheckConstraint(
            "baked_good_type IS NULL OR baked_good_type IN ('arabic_bread','toast','rolls_wraps','burger_bun','flatbread','pastries','cake','biscuits_cookies','other')",
            name="ck_food_baked_good_type",
        ),
        CheckConstraint(
            "grain_starch_type IS NULL OR grain_starch_type IN ('rice','pasta','oats','breakfast_cereal','bulgur','quinoa','flour','other')",
            name="ck_food_grain_starch_type",
        ),
        CheckConstraint(
            "(food_category_key='baked_goods' AND baked_good_type IS NOT NULL AND grain_type IS NOT NULL AND grain_starch_type IS NULL) OR "
            "(food_category_key='grains_starches' AND grain_starch_type IS NOT NULL AND grain_type IS NOT NULL AND baked_good_type IS NULL) OR "
            "(food_category_key NOT IN ('baked_goods','grains_starches') AND baked_good_type IS NULL AND grain_starch_type IS NULL AND grain_type IS NULL)",
            name="ck_food_category_details_v2",
        ),
        CheckConstraint(
            "(status='active' AND archived_at IS NULL AND archived_by_principal_id IS NULL) OR "
            "(status='archived' AND archived_at IS NOT NULL AND archived_by_principal_id IS NOT NULL)",
            name="ck_food_archive_state",
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
            _finite_numeric_check(FOOD_NUMERIC_COLUMNS),
            name="ck_food_numeric_values_finite",
        ),
        CheckConstraint(
            "(CAST(nutrition_basis AS TEXT) = 'per_100g' AND CAST(unit_basis AS TEXT) = 'g') OR (CAST(nutrition_basis AS TEXT) = 'per_100ml' AND CAST(unit_basis AS TEXT) = 'ml')",
            name="ck_food_nutrition_unit_basis",
        ),
        Index("ix_food_catalog_lower_name", sa_text("lower(name)")),
        Index("ix_food_catalog_created_desc", sa_text("created_at DESC")),
        Index("ix_food_catalog_category_status", "food_category_key", "status"),
        UniqueConstraint(
            "normalized_name",
            "nutrition_basis",
            "default_unit_type",
            "unit_amount",
            "unit_basis",
            name="uq_food_catalog_duplicate",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by_principal_id: uuid.UUID = Field(
        alias="principal_id",
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        ),
    )
    updated_by_principal_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=True),
    )
    archived_by_principal_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=True),
    )
    name: str = Field(index=True)
    normalized_name: str = Field(default="", sa_column=Column(String(512), nullable=False))
    brand: str | None = None
    food_category_key: str = Field(default="other", sa_column=Column(Text(), nullable=False))
    grain_type: GrainType | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    baked_good_type: BakedGoodType | None = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    grain_starch_type: GrainStarchType | None = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    taxonomy_review_required: bool = Field(default=False, nullable=False)
    status: FoodStatus = Field(
        default=FoodStatus.active,
        sa_column=Column(Text(), nullable=False, server_default=FoodStatus.active.value),
    )
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
    archived_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class FoodTaxonomyV2MigrationAudit(SQLModel, table=True):
    __tablename__ = "food_taxonomy_v2_migration_audit"

    food_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("food.id", ondelete="CASCADE"), primary_key=True, nullable=False
        )
    )
    legacy_category: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    legacy_primary_category_key: str | None = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    recorded_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()")),
    )


class FoodGroupContribution(SQLModel, table=True):
    __tablename__ = "food_group_contribution"
    __table_args__ = (
        ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="CASCADE"),
        UniqueConstraint("food_id", "group_key", name="uq_food_group_contribution_food_group"),
        CheckConstraint(
            "amount_per_100_basis > 0 AND amount_per_100_basis <= 100",
            name="ck_food_group_contribution_amount",
        ),
        CheckConstraint(
            _finite_numeric_check(FOOD_GROUP_NUMERIC_COLUMNS),
            name="ck_food_group_contribution_amount_finite",
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
    created_by_principal_id: uuid.UUID = Field(
        alias="principal_id",
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        ),
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
        ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="CASCADE"),
        UniqueConstraint("food_id", "trait_key", name="uq_food_analytical_trait_food_trait"),
        CheckConstraint(
            "trait_key IN ('sweetened','non_nutritive_sweetened','processed','omega3_rich_seafood','calcium_fortified','unsaturated_fat_source','smoked','salted','fruit_liquid_100_percent','dried_fruit','starchy_root')",
            name="ck_food_analytical_trait_key",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by_principal_id: uuid.UUID = Field(
        alias="principal_id",
        sa_column=Column(
            ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False, index=True
        ),
    )
    food_id: uuid.UUID = Field(nullable=False, index=True)
    trait_key: str = Field(sa_column=Column(Text(), nullable=False))
    food_group_rules_version: str = Field(max_length=32)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class DiaryDayStatus(SQLModel, table=True):
    __tablename__ = "diary_day_status"
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_diary_day_status_id_principal"),
        UniqueConstraint("principal_id", "diary_date", name="uq_diary_day_status_principal_date"),
        CheckConstraint("status IN ('partial','complete')", name="ck_diary_day_status_value"),
        CheckConstraint("version >= 1", name="ck_diary_day_status_version"),
        CheckConstraint("entry_count >= 0", name="ck_diary_day_status_entry_count"),
        CheckConstraint(
            "(status='complete' AND completed_at IS NOT NULL) OR "
            "(status='partial' AND completed_at IS NULL)",
            name="ck_diary_day_status_completion",
        ),
        Index(
            "ix_diary_day_status_principal_date_desc",
            "principal_id",
            desc("diary_date"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    diary_date: date = Field(nullable=False)
    status: DiaryDayStatusValue = Field(sa_column=Column(Text(), nullable=False))
    version: int = Field(sa_column=Column(BigInteger(), nullable=False))
    entry_count: int = Field(sa_column=Column(Integer(), nullable=False))
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    reopened_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class DiaryDayStatusHistory(SQLModel, table=True):
    __tablename__ = "diary_day_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["day_status_id", "principal_id"],
            ["diary_day_status.id", "diary_day_status.principal_id"],
            name="fk_diary_day_status_history_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "day_status_id", "day_version", name="uq_diary_day_status_history_version"
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('partial','complete')",
            name="ck_diary_day_status_history_from",
        ),
        CheckConstraint(
            "to_status IN ('partial','complete')", name="ck_diary_day_status_history_to"
        ),
        CheckConstraint(
            "event_type IN ('entry_created','entry_edited','entry_deleted','completed','reopened')",
            name="ck_diary_day_status_history_event",
        ),
        CheckConstraint("day_version >= 1", name="ck_diary_day_status_history_version"),
        CheckConstraint(
            "actor_principal_id = principal_id", name="ck_diary_day_status_history_actor"
        ),
        Index(
            "ix_diary_day_status_history_principal_date_version",
            "principal_id",
            "diary_date",
            "day_version",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    day_status_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    diary_date: date = Field(nullable=False)
    from_status: DiaryDayStatusValue | None = Field(
        default=None, sa_column=Column(Text(), nullable=True)
    )
    to_status: DiaryDayStatusValue = Field(sa_column=Column(Text(), nullable=False))
    event_type: DiaryDayStatusEvent = Field(sa_column=Column(Text(), nullable=False))
    day_version: int = Field(sa_column=Column(BigInteger(), nullable=False))
    entry_id: uuid.UUID | None = Field(default=None, nullable=True)
    actor_principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    occurred_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    request_id: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))


class DiaryEntry(SQLModel, table=True):
    __tablename__ = "diary_entry"
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_diary_entry_id_principal_id"),
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
            "snapshot_schema_version IS NULL OR snapshot_schema_version IN (2,3)",
            name="ck_diary_entry_snapshot_version",
        ),
        CheckConstraint(
            "snapshot_schema_version IS NULL OR "
            "(jsonb_typeof(nutrition_snapshot)='object' AND "
            "nutrition_snapshot->>'schema_version'=snapshot_schema_version::text)",
            name="ck_diary_entry_versioned_shape",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_diary_entry_quantity_positive_finite",
        ),
        Index(
            "ix_diary_entry_principal_date_meal_created",
            "principal_id",
            "entry_date",
            "meal_type",
            "created_at",
        ),
        Index(
            "ix_diary_entry_principal_date_created_id_desc",
            "principal_id",
            desc("entry_date"),
            desc("created_at"),
            desc("id"),
        ),
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


class NutritionAnalysis(SQLModel, table=True):
    __tablename__ = "nutrition_analysis"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id", "current_revision_id", "principal_id"],
            [
                "nutrition_analysis_revision.analysis_id",
                "nutrition_analysis_revision.id",
                "nutrition_analysis_revision.principal_id",
            ],
            name="fk_nutrition_analysis_current_revision_owner",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        UniqueConstraint("id", "principal_id", name="uq_nutrition_analysis_id_principal"),
        UniqueConstraint(
            "principal_id",
            "as_of_diary_date",
            "interface_version",
            name="uq_nutrition_analysis_principal_date_interface",
        ),
        CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_nutrition_analysis_timezone"),
        CheckConstraint("interface_version = 1", name="ck_nutrition_analysis_interface"),
        CheckConstraint(
            "(current_revision_id IS NULL AND current_revision_number IS NULL) OR "
            "(current_revision_id IS NOT NULL AND current_revision_number >= 1)",
            name="ck_nutrition_analysis_current_pointer",
        ),
        Index(
            "ix_nutrition_analysis_principal_date_desc",
            "principal_id",
            desc("as_of_diary_date"),
            desc("id"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    as_of_diary_date: date = Field(nullable=False)
    calendar_timezone: str = Field(sa_column=Column(String(64), nullable=False))
    interface_version: int = Field(default=1, sa_column=Column(SmallInteger(), nullable=False))
    current_revision_id: uuid.UUID | None = Field(default=None, nullable=True)
    current_revision_number: int | None = Field(
        default=None, sa_column=Column(Integer(), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class NutritionAnalysisRevision(SQLModel, table=True):
    __tablename__ = "nutrition_analysis_revision"
    __table_args__ = (
        ForeignKeyConstraint(
            ["analysis_id", "principal_id"],
            ["nutrition_analysis.id", "nutrition_analysis.principal_id"],
            name="fk_nutrition_analysis_revision_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "principal_id", name="uq_nutrition_analysis_revision_id_principal"),
        UniqueConstraint(
            "analysis_id",
            "id",
            "principal_id",
            name="uq_nutrition_analysis_revision_series_id_owner",
        ),
        UniqueConstraint("analysis_id", "revision", name="uq_nutrition_analysis_revision_number"),
        UniqueConstraint(
            "analysis_id",
            "source_input_hash",
            "analysis_rules_version",
            name="uq_nutrition_analysis_revision_source",
        ),
        CheckConstraint("revision >= 1", name="ck_nutrition_analysis_revision_positive"),
        CheckConstraint(
            "period_end - period_start = 6 AND previous_period_end - previous_period_start = 6 "
            "AND previous_period_end + 1 = period_start",
            name="ck_nutrition_analysis_revision_windows",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "complete_day_count BETWEEN 0 AND 7 AND previous_complete_day_count BETWEEN 0 AND 7",
            name="ck_nutrition_analysis_revision_day_counts",
        ),
        CheckConstraint(
            "length(source_input_hash) = 64 AND length(content_hash) = 64",
            name="ck_nutrition_analysis_revision_hashes",
        ),
        CheckConstraint(
            "result_status IN ('available','insufficient','unavailable')",
            name="ck_nutrition_analysis_revision_result",
        ),
        Index(
            "ix_nutrition_analysis_revision_history",
            "principal_id",
            desc("period_end"),
            desc("analysis_id"),
            desc("revision"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    revision: int = Field(sa_column=Column(Integer(), nullable=False))
    period_start: date = Field(nullable=False)
    period_end: date = Field(nullable=False)
    previous_period_start: date = Field(nullable=False)
    previous_period_end: date = Field(nullable=False)
    analysis_rules_version: str = Field(sa_column=Column(String(64), nullable=False))
    source_versions: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    source_input_hash: str = Field(sa_column=Column(String(64), nullable=False))
    content_hash: str = Field(sa_column=Column(String(64), nullable=False))
    complete_day_count: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    previous_complete_day_count: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    result_status: str = Field(sa_column=Column(String(32), nullable=False))
    result_reason: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    analysis_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    supersedes_revision_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("nutrition_analysis_revision.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    generated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finalized_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class NutritionAnalysisEvidenceRef(SQLModel, table=True):
    __tablename__ = "nutrition_analysis_evidence_ref"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "principal_id"],
            ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"],
            name="fk_nutrition_analysis_evidence_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "revision_id",
            "period",
            "diary_date",
            "source_ref",
            "metric_key",
            name="uq_nutrition_analysis_evidence_identity",
        ),
        CheckConstraint(
            "period IN ('current','previous')", name="ck_nutrition_analysis_evidence_period"
        ),
        CheckConstraint("day_version >= 0", name="ck_nutrition_analysis_evidence_day_version"),
        CheckConstraint(
            "snapshot_schema_version IN (2,3)",
            name="ck_nutrition_analysis_evidence_snapshot_version",
        ),
        CheckConstraint(
            "value_state IN ('known','explicit_zero','unknown')",
            name="ck_nutrition_analysis_evidence_value_state",
        ),
        CheckConstraint(
            "(value_state='unknown' AND value IS NULL) OR "
            "(value_state='explicit_zero' AND value=0) OR "
            "(value_state='known' AND value IS NOT NULL)",
            name="ck_nutrition_analysis_evidence_value",
        ),
        Index(
            "ix_nutrition_analysis_evidence_principal_date_desc",
            "principal_id",
            desc("diary_date"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    revision_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    period: str = Field(sa_column=Column(String(16), nullable=False))
    diary_date: date = Field(nullable=False)
    day_version: int = Field(sa_column=Column(BigInteger(), nullable=False))
    source_ref: uuid.UUID = Field(nullable=False)
    snapshot_schema_version: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    metric_key: str = Field(sa_column=Column(String(96), nullable=False))
    source_version: str = Field(sa_column=Column(String(64), nullable=False))
    value: float | None = Field(default=None, sa_column=Column(Numeric(24, 6), nullable=True))
    value_state: str = Field(sa_column=Column(String(24), nullable=False))
    unit: str = Field(sa_column=Column(String(32), nullable=False))


class NutritionAnalysisRevisionEvent(SQLModel, table=True):
    __tablename__ = "nutrition_analysis_revision_event"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "principal_id"],
            ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"],
            name="fk_nutrition_analysis_event_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "event_type IN ('day_reopened','day_version_changed','target_source_changed',"
            "'source_snapshot_corrected','source_version_unsupported','superseded_by_revision')",
            name="ck_nutrition_analysis_event_type",
        ),
        UniqueConstraint(
            "revision_id",
            "event_type",
            "reason",
            "source_day_version",
            "successor_revision_id",
            name="uq_nutrition_analysis_event_identity",
        ),
        Index("ix_nutrition_analysis_event_revision_time", "revision_id", "occurred_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    revision_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    successor_revision_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("nutrition_analysis_revision.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    reason: str = Field(sa_column=Column(String(96), nullable=False))
    source_day_version: int | None = Field(
        default=None, sa_column=Column(BigInteger(), nullable=True)
    )
    occurred_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    request_id: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))


class NutritionAnalysisCommandIdempotency(SQLModel, table=True):
    __tablename__ = "nutrition_analysis_command_idempotency"
    __table_args__ = (
        UniqueConstraint(
            "principal_id", "operation", "key_digest", name="uq_nutrition_analysis_command_scope"
        ),
        CheckConstraint(
            "length(key_digest) = 64 AND length(command_hash) = 64",
            name="ck_nutrition_analysis_command_hashes",
        ),
        CheckConstraint(
            "response_status IN (200,201)", name="ck_nutrition_analysis_command_status"
        ),
        Index("ix_nutrition_analysis_command_expiry", "expires_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    operation: str = Field(sa_column=Column(String(64), nullable=False))
    key_digest: str = Field(sa_column=Column(String(64), nullable=False))
    command_hash: str = Field(sa_column=Column(String(64), nullable=False))
    captured_date: date = Field(nullable=False)
    analysis_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("nutrition_analysis.id", ondelete="RESTRICT"), nullable=True),
    )
    revision_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("nutrition_analysis_revision.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    response_status: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    response_headers: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False),
    )
    response_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    completed_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class WeeklyPriorityRecommendation(SQLModel, table=True):
    __tablename__ = "weekly_priority_recommendation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_analysis_revision_id", "principal_id"],
            ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"],
            name="fk_weekly_priority_analysis_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "principal_id", name="uq_weekly_priority_id_owner"),
        UniqueConstraint(
            "principal_id",
            "source_analysis_revision_id",
            "rules_version",
            name="uq_weekly_priority_source_rules",
        ),
        CheckConstraint("schema_version = 1", name="ck_weekly_priority_schema"),
        CheckConstraint(
            "status IN ('selected','none','stale','superseded','safety_suppressed')",
            name="ck_weekly_priority_status",
        ),
        CheckConstraint("period_end - period_start = 6", name="ck_weekly_priority_period").ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            "length(input_digest) = 64 AND length(content_hash) = 64",
            name="ck_weekly_priority_hash",
        ),
        CheckConstraint(
            "(superseded_by_id IS NULL AND superseded_at IS NULL) OR "
            "(superseded_by_id IS NOT NULL AND superseded_at IS NOT NULL)",
            name="ck_weekly_priority_supersession",
        ),
        Index(
            "uq_weekly_priority_one_selected",
            "principal_id",
            unique=True,
            postgresql_where=sa_text("superseded_at IS NULL AND status='selected'"),
            sqlite_where=sa_text("superseded_at IS NULL AND status='selected'"),
        ),
        Index(
            "ix_weekly_priority_current",
            "principal_id",
            desc("period_end"),
            desc("created_at"),
            desc("id"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    source_analysis_revision_id: uuid.UUID = Field(nullable=False)
    source_analysis_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("nutrition_analysis.id", ondelete="RESTRICT"), nullable=False)
    )
    source_analysis_revision: int = Field(sa_column=Column(Integer(), nullable=False))
    schema_version: int = Field(default=1, sa_column=Column(SmallInteger(), nullable=False))
    period_start: date = Field(nullable=False)
    period_end: date = Field(nullable=False)
    as_of_diary_date: date = Field(nullable=False)
    status: str = Field(sa_column=Column(String(32), nullable=False))
    rules_version: str = Field(sa_column=Column(String(64), nullable=False))
    copy_version: str = Field(sa_column=Column(String(64), nullable=False))
    analysis_rules_version: str = Field(sa_column=Column(String(64), nullable=False))
    source_versions: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    result_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    input_digest: str = Field(sa_column=Column(String(64), nullable=False))
    content_hash: str = Field(sa_column=Column(String(64), nullable=False))
    superseded_by_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("weekly_priority_recommendation.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    superseded_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    generated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class WeeklyPriorityEvidenceRef(SQLModel, table=True):
    __tablename__ = "weekly_priority_evidence_ref"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recommendation_id", "principal_id"],
            ["weekly_priority_recommendation.id", "weekly_priority_recommendation.principal_id"],
            name="fk_weekly_priority_evidence_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "recommendation_id",
            "metric_key",
            "evidence_kind",
            "opaque_source_id",
            "diary_date",
            name="uq_weekly_priority_evidence_identity",
        ),
        CheckConstraint(
            "coverage_percent IS NULL OR coverage_percent BETWEEN 0 AND 100",
            name="ck_weekly_priority_evidence_coverage",
        ),
        CheckConstraint("evidence_kind = 'analysis_fact'", name="ck_weekly_priority_evidence_kind"),
        CheckConstraint(
            "value IS NULL OR value NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_weekly_priority_evidence_finite",
        ).ddl_if(dialect="postgresql"),
        Index("ix_weekly_priority_evidence_principal_date", "principal_id", desc("diary_date")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recommendation_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    metric_key: str = Field(sa_column=Column(String(96), nullable=False))
    evidence_kind: str = Field(sa_column=Column(String(32), nullable=False))
    opaque_source_id: uuid.UUID = Field(nullable=False)
    source_version: str = Field(sa_column=Column(String(64), nullable=False))
    diary_date: date = Field(nullable=False)
    value: float | None = Field(default=None, sa_column=Column(Numeric(24, 6), nullable=True))
    unit: str = Field(sa_column=Column(String(32), nullable=False))
    coverage_percent: float | None = Field(
        default=None, sa_column=Column(Numeric(6, 3), nullable=True)
    )


class BehaviorGoal(SQLModel, table=True):
    __tablename__ = "behavior_goal"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recommendation_id", "principal_id"],
            ["weekly_priority_recommendation.id", "weekly_priority_recommendation.principal_id"],
            name="fk_behavior_goal_recommendation_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["root_goal_id", "principal_id"],
            ["behavior_goal.id", "behavior_goal.principal_id"],
            name="fk_behavior_goal_root_owner",
            ondelete="RESTRICT",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["previous_goal_id", "principal_id"],
            ["behavior_goal.id", "behavior_goal.principal_id"],
            name="fk_behavior_goal_previous_owner",
            ondelete="RESTRICT",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
        UniqueConstraint("id", "principal_id", name="uq_behavior_goal_id_owner"),
        UniqueConstraint(
            "principal_id", "root_goal_id", "sequence_number", name="uq_behavior_goal_sequence"
        ),
        UniqueConstraint("principal_id", "previous_goal_id", name="uq_behavior_goal_successor"),
        CheckConstraint("sequence_number >= 1 AND version >= 1", name="ck_behavior_goal_versions"),
        CheckConstraint("weekly_target_count BETWEEN 1 AND 7", name="ck_behavior_goal_target"),
        CheckConstraint("window_end - window_start = 6", name="ck_behavior_goal_window").ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            "state IN ('offered','deferred','active','paused','completed','incomplete','rejected','ended','archived')",
            name="ck_behavior_goal_state",
        ),
        CheckConstraint(
            "private_note IS NULL OR length(private_note) <= 280", name="ck_behavior_goal_note"
        ),
        CheckConstraint(
            "jsonb_typeof(day_mask)='array' AND jsonb_array_length(day_mask) <= 7",
            name="ck_behavior_goal_day_mask",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "reminder_preference IN ('enabled','disabled')",
            name="ck_behavior_goal_reminder_preference",
        ),
        CheckConstraint(
            "(state <> 'deferred' OR (deferred_at IS NOT NULL AND deferred_until IS NOT NULL)) "
            "AND (state <> 'paused' OR paused_at IS NOT NULL) "
            "AND (state <> 'completed' OR completed_at IS NOT NULL) "
            "AND (state <> 'incomplete' OR reviewed_at IS NOT NULL) "
            "AND (state <> 'rejected' OR rejected_at IS NOT NULL) "
            "AND (state <> 'ended' OR ended_at IS NOT NULL)",
            name="ck_behavior_goal_state_timestamps",
        ),
        Index(
            "uq_behavior_goal_one_primary",
            "principal_id",
            unique=True,
            postgresql_where=sa_text("state IN ('active','paused')"),
            sqlite_where=sa_text("state IN ('active','paused')"),
        ),
        Index(
            "ix_behavior_goal_history",
            "principal_id",
            desc("window_end"),
            desc("created_at"),
            desc("id"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    recommendation_id: uuid.UUID = Field(nullable=False)
    root_goal_id: uuid.UUID = Field(nullable=False)
    previous_goal_id: uuid.UUID | None = Field(default=None, nullable=True)
    sequence_number: int = Field(default=1, sa_column=Column(Integer(), nullable=False))
    state: str = Field(sa_column=Column(String(24), nullable=False))
    version: int = Field(default=1, sa_column=Column(Integer(), nullable=False))
    rule_key: str = Field(sa_column=Column(String(64), nullable=False))
    action_key: str = Field(sa_column=Column(String(96), nullable=False))
    weekly_target_count: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    day_mask: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False),
    )
    window_start: date = Field(nullable=False)
    window_end: date = Field(nullable=False)
    rules_version: str = Field(sa_column=Column(String(64), nullable=False))
    copy_version: str = Field(sa_column=Column(String(64), nullable=False))
    progress_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    progress_revision: int = Field(default=1, sa_column=Column(Integer(), nullable=False))
    reminder_preference: str = Field(
        default="disabled", sa_column=Column(String(16), nullable=False)
    )
    external_notifications_enabled: bool = Field(default=False, nullable=False)
    private_note: str | None = Field(default=None, sa_column=Column(String(280), nullable=True))
    accepted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    deferred_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    deferred_until: date | None = Field(default=None, nullable=True)
    paused_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    changed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    resumed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    reviewed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    rejected_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    ended_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    archived_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class BehaviorGoalHistory(SQLModel, table=True):
    __tablename__ = "behavior_goal_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["goal_id", "principal_id"],
            ["behavior_goal.id", "behavior_goal.principal_id"],
            name="fk_behavior_goal_history_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("goal_id", "goal_version", name="uq_behavior_goal_history_version"),
        CheckConstraint("actor_type IN ('owner','system')", name="ck_behavior_goal_history_actor"),
        CheckConstraint(
            "event_type IN ('offered','accept','edit','defer','reject','change','changed',"
            "'pause','resume','end','completed','evidence_reopened','progress_updated',"
            "'finalized_incomplete','repeated_from_previous_window')",
            name="ck_behavior_goal_history_event",
        ),
        CheckConstraint(
            "reason IS NULL OR reason IN ('not_relevant','too_difficult','prefer_other',"
            "'pause_tracking','other','owner_requested','evidence_superseded')",
            name="ck_behavior_goal_history_reason",
        ),
        Index("ix_behavior_goal_history_goal_time", "goal_id", desc("occurred_at")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    goal_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    root_goal_id: uuid.UUID = Field(nullable=False)
    previous_goal_id: uuid.UUID | None = Field(default=None, nullable=True)
    sequence_number: int = Field(nullable=False)
    goal_version: int = Field(nullable=False)
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    from_state: str | None = Field(default=None, sa_column=Column(String(24), nullable=True))
    to_state: str = Field(sa_column=Column(String(24), nullable=False))
    request_digest: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    actor_type: str = Field(sa_column=Column(String(16), nullable=False))
    reason: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    terms_progress_snapshot: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    occurred_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    request_id: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))


class BehaviorGoalCommandIdempotency(SQLModel, table=True):
    __tablename__ = "behavior_goal_command_idempotency"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_goal_id", "principal_id"],
            ["behavior_goal.id", "behavior_goal.principal_id"],
            name="fk_behavior_goal_command_source_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "principal_id",
            "operation",
            "source_goal_id",
            "key_digest",
            name="uq_behavior_goal_command_scope",
        ),
        CheckConstraint(
            "length(key_digest) = 64 AND length(command_hash) = 64",
            name="ck_behavior_goal_command_hashes",
        ),
        CheckConstraint(
            "response_status BETWEEN 200 AND 599",
            name="ck_behavior_goal_command_status",
        ),
        Index("ix_behavior_goal_command_completed", "principal_id", desc("completed_at")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    operation: str = Field(sa_column=Column(String(64), nullable=False))
    source_goal_id: uuid.UUID = Field(nullable=False)
    key_digest: str = Field(sa_column=Column(String(64), nullable=False))
    command_hash: str = Field(sa_column=Column(String(64), nullable=False))
    captured_diary_date: date = Field(nullable=False)
    recommendation_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("weekly_priority_recommendation.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    allocated_goal_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("behavior_goal.id", ondelete="RESTRICT"), nullable=True),
    )
    response_status: int = Field(sa_column=Column(SmallInteger(), nullable=False))
    response_headers: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    response_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    completed_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class BehaviorGoalReminderDelivery(SQLModel, table=True):
    __tablename__ = "behavior_goal_reminder_delivery"
    __table_args__ = (
        ForeignKeyConstraint(
            ["goal_id", "principal_id"],
            ["behavior_goal.id", "behavior_goal.principal_id"],
            name="fk_behavior_goal_reminder_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "goal_id", "goal_revision", "reminder_type", name="uq_behavior_goal_reminder_cap"
        ),
        CheckConstraint("attempts IN (0,1)", name="ck_behavior_goal_reminder_attempts"),
        CheckConstraint(
            "reminder_type IN ('midweek','endweek_review')",
            name="ck_behavior_goal_reminder_type",
        ),
        CheckConstraint(
            "channel IN ('in_app','external')",
            name="ck_behavior_goal_reminder_channel",
        ),
        CheckConstraint(
            "status IN ('eligible','deferred','sent','failed','suppressed')",
            name="ck_behavior_goal_reminder_status",
        ),
        Index("ix_behavior_goal_reminder_due", "status", "deferred_until"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    goal_id: uuid.UUID = Field(nullable=False)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    goal_revision: int = Field(nullable=False)
    reminder_type: str = Field(sa_column=Column(String(32), nullable=False))
    channel: str = Field(sa_column=Column(String(16), nullable=False))
    eligibility_diary_date: date = Field(nullable=False)
    deferred_until: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    status: str = Field(sa_column=Column(String(24), nullable=False))
    provider_receipt_digest: str | None = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )
    attempts: int = Field(default=0, sa_column=Column(SmallInteger(), nullable=False))
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
