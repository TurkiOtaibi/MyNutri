from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
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
    Integer,
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


FOOD_TAXONOMY_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "grains_and_starches",
        (
            "rice",
            "oats",
            "pasta",
            "bulgur",
            "jareesh",
            "wheat",
            "barley",
            "corn",
            "potatoes",
            "sweet_potatoes",
            "other",
        ),
    ),
    (
        "bakery",
        (
            "bread",
            "toast",
            "samoli",
            "croissant",
            "pastries",
            "tortilla_and_wraps",
            "biscuits_and_crackers",
            "other",
        ),
    ),
    (
        "meat_and_poultry",
        ("chicken", "turkey", "beef", "lamb", "camel", "eggs", "processed_meat", "other"),
    ),
    ("fish_and_seafood", ("fish", "tuna", "shrimp", "crustaceans", "mollusks", "other")),
    (
        "dairy_products",
        ("milk", "laban", "yogurt", "labneh", "cheese", "cream_and_qishta", "other"),
    ),
    (
        "legumes",
        ("lentils", "chickpeas", "beans", "fava_beans", "peas", "cowpeas", "lupin", "other"),
    ),
    (
        "vegetables",
        (
            "leafy_vegetables",
            "cruciferous_vegetables",
            "root_vegetables",
            "tomatoes",
            "cucumber",
            "peppers",
            "onion_and_garlic",
            "zucchini_and_squash",
            "eggplant",
            "mushrooms",
            "other",
        ),
    ),
    (
        "fruits",
        (
            "citrus",
            "apples_and_pears",
            "bananas",
            "grapes",
            "berries",
            "stone_fruits",
            "tropical_fruits",
            "watermelon_and_melon",
            "dates",
            "pomegranate",
            "figs",
            "dried_fruits",
            "other",
        ),
    ),
    (
        "nuts_and_seeds",
        (
            "almonds",
            "walnuts",
            "cashews",
            "pistachios",
            "hazelnuts",
            "peanuts",
            "sesame_seeds",
            "chia_seeds",
            "flax_seeds",
            "sunflower_seeds",
            "pumpkin_seeds",
            "other",
        ),
    ),
    (
        "fats_and_oils",
        ("olive_oil", "vegetable_oils", "coconut_oil", "butter", "ghee", "margarine", "other"),
    ),
    (
        "sweets_and_sugars",
        (
            "cake",
            "chocolate",
            "sweet_biscuits",
            "middle_eastern_sweets",
            "western_desserts",
            "ice_cream_and_frozen_desserts",
            "candy",
            "sugar_and_sweeteners",
            "jam_and_sweet_spreads",
            "other",
        ),
    ),
    (
        "beverages",
        (
            "water",
            "coffee",
            "tea",
            "juices",
            "carbonated_drinks",
            "energy_drinks",
            "sports_drinks",
            "plant_based_drinks",
            "shakes_and_smoothies",
            "other",
        ),
    ),
    (
        "meals",
        (
            "rice_dishes",
            "pasta_dishes",
            "burgers_and_sandwiches",
            "shawarma",
            "pizza",
            "salads",
            "soups",
            "main_dishes",
            "breakfast_meals",
            "other",
        ),
    ),
    (
        "sauces_spices_and_additions",
        (
            "sauces",
            "mayonnaise",
            "dressings",
            "tahini",
            "spices_and_seasonings",
            "herbs",
            "salt",
            "vinegar",
            "additions",
            "other",
        ),
    ),
    ("other", ("other",)),
)


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


class NutritionDataSource(str, Enum):
    official = "official"
    estimated = "estimated"


class IdempotencyState(str, Enum):
    in_progress = "in_progress"
    completed = "completed"


class PrincipalStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class PrincipalRole(str, Enum):
    user = "user"
    admin = "admin"


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
        CheckConstraint(
            "jsonb_typeof(calculation_document)='object' AND "
            "jsonb_typeof(calculation_document->'target_result')='object'",
            name="ck_target_plan_calculation_document_shape",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("revision >= 1", name="ck_target_plan_revision_positive"),
        UniqueConstraint(
            "principal_id",
            "effective_from",
            "revision",
            name="uq_target_plan_principal_effective_revision",
        ),
        Index(
            "ix_target_plan_principal_effective_revision",
            "principal_id",
            desc("effective_from"),
            desc("revision"),
            desc("id"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    profile_id: uuid.UUID = Field(nullable=False)
    effective_from: date = Field(nullable=False)
    revision: int = Field(sa_column=Column(Integer(), nullable=False))
    calculation_document: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


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
        CheckConstraint(
            "(operation = 'lab_results.create.v1' AND expires_at IS NULL) OR "
            "(operation <> 'lab_results.create.v1' AND expires_at IS NOT NULL)",
            name="ck_idempotency_operation_expiry",
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
    expires_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class LabResult(SQLModel, table=True):
    __tablename__ = "lab_result"
    __table_args__ = (
        # The unique B-tree supports owner/test/date reads, including reverse date scans.
        UniqueConstraint(
            "principal_id", "test_key", "test_date", name="uq_lab_result_principal_test_date"
        ),
        CheckConstraint(
            "entered_value >= 0 AND entered_value NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_lab_result_value_finite_nonnegative",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "length(entered_value::text) <= 128", name="ck_lab_result_value_length"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("length(test_key) > 0", name="ck_lab_result_test_key_nonempty"),
        CheckConstraint("length(entered_unit) > 0", name="ck_lab_result_entered_unit_nonempty"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    principal_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("principal.id", ondelete="RESTRICT"), nullable=False)
    )
    test_key: str = Field(sa_column=Column(String(64), nullable=False))
    test_date: date = Field(nullable=False)
    entered_value: Decimal = Field(sa_column=Column(Numeric(), nullable=False))
    entered_unit: str = Field(sa_column=Column(String(64), nullable=False))
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


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


def _finite_numeric_check(columns: tuple[str, ...]) -> str:
    special_values = "('NaN', 'Infinity', '-Infinity')"
    return " AND ".join(f"{column} NOT IN {special_values}" for column in columns)


class Food(SQLModel, table=True):
    __tablename__ = "food"
    __table_args__ = (
        CheckConstraint(
            "primary_category IN ("
            + ",".join(f"'{primary}'" for primary, _children in FOOD_TAXONOMY_KEYS)
            + ")",
            name="ck_food_primary_category",
        ),
        CheckConstraint(
            " OR ".join(
                "(primary_category='{}' AND subcategory IN ({}))".format(
                    primary,
                    ",".join(f"'{key}'" for key in children),
                )
                for primary, children in FOOD_TAXONOMY_KEYS
            ),
            name="ck_food_taxonomy_pair",
        ),
        CheckConstraint(
            "nutrition_data_source IN ('official','estimated')",
            name="ck_food_nutrition_data_source",
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
        Index("ix_food_catalog_primary_category", "primary_category"),
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
    name: str = Field(index=True)
    normalized_name: str = Field(default="", sa_column=Column(String(512), nullable=False))
    brand: str | None = None
    primary_category: str = Field(default="other", sa_column=Column(Text(), nullable=False))
    subcategory: str = Field(default="other", sa_column=Column(Text(), nullable=False))
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
    nutrition_data_source: NutritionDataSource = Field(
        default=NutritionDataSource.estimated,
        sa_column=Column(
            Text(), nullable=False, server_default=NutritionDataSource.estimated.value
        ),
    )
    ingredients: str | None = Field(default=None, sa_column=Column(Text()))
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
    __table_args__ = (
        UniqueConstraint("id", "principal_id", name="uq_diary_entry_id_principal_id"),
        ForeignKeyConstraint(
            ["target_plan_id", "principal_id"],
            ["target_plan.id", "target_plan.principal_id"],
            name="fk_diary_entry_target_plan_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_diary_entry_quantity_positive_finite",
        ),
        CheckConstraint(
            "recorded_unit_amount > 0 AND "
            "recorded_unit_amount NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_diary_entry_recorded_unit_amount_positive_finite",
        ),
        CheckConstraint(
            "recorded_unit_type IN "
            "('g','ml','cup','slice','piece','scoop','serving','tablespoon','teaspoon')",
            name="ck_diary_entry_recorded_unit_type",
        ),
        CheckConstraint(
            "recorded_unit_basis IN ('g','ml')",
            name="ck_diary_entry_recorded_unit_basis",
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
    food_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("food.id", ondelete="CASCADE"), index=True, nullable=False),
    )
    target_plan_id: uuid.UUID | None = Field(default=None, nullable=True)
    quantity: float = Field(sa_column=Column(Numeric(8, 3), nullable=False))
    recorded_unit_type: DefaultUnitType = Field(sa_column=Column(Text(), nullable=False))
    recorded_unit_amount: float = Field(sa_column=Column(Numeric(10, 4), nullable=False))
    recorded_unit_basis: UnitBasis = Field(sa_column=Column(Text(), nullable=False))
    recorded_unit_label: str | None = Field(
        default=None, sa_column=Column(String(80), nullable=True)
    )
    meal_type: MealType = Field(
        default=MealType.unspecified,
        sa_column=Column(SAEnum(MealType, name="meal_type_enum"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
