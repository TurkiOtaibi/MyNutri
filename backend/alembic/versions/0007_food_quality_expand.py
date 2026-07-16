"""expand Food quality, source, ingredients, and NOVA fields

Revision ID: 0007_food_quality_expand
Revises: 0006_principal_contract
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_food_quality_expand"
down_revision: str | None = "0006_principal_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRIMARY_CATEGORIES = (
    "vegetables",
    "fruits",
    "legumes",
    "whole_grains",
    "refined_grains",
    "nuts_seeds",
    "seafood",
    "dairy_fortified_alternatives",
    "eggs",
    "poultry",
    "red_meat",
    "processed_meat",
    "added_oils_fats",
    "sweets",
    "sugar_sweetened_beverages",
    "unsweetened_beverages",
    "herbs_spices",
    "mixed_dish",
    "other",
)
SOURCE_TYPES = (
    "laboratory_analysis",
    "official_food_database",
    "official_product_label",
    "manufacturer_website",
    "official_restaurant",
    "calculated_recipe",
    "manual_estimate",
    "multiple_sources",
    "unknown",
)
INGREDIENT_SOURCE_TYPES = (
    "official_product_label",
    "manufacturer_website",
    "official_food_database",
    "official_restaurant",
    "calculated_recipe",
    "manual_entry",
    "multiple_sources",
    "unknown",
)


def quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.add_column("food", sa.Column("primary_category_key", sa.Text(), nullable=True))
    op.add_column(
        "food", sa.Column("food_kind", sa.Text(), server_default="unknown", nullable=False)
    )
    op.add_column(
        "food", sa.Column("group_data_status", sa.Text(), server_default="unknown", nullable=False)
    )
    op.add_column(
        "food",
        sa.Column("group_data_completeness", sa.Text(), server_default="unknown", nullable=False),
    )
    op.add_column(
        "food",
        sa.Column("nutrition_source_type", sa.Text(), server_default="unknown", nullable=False),
    )
    op.add_column("food", sa.Column("nutrition_source_name", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("nutrition_source_reference", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("ingredients_text", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("ingredients_source_type", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("ingredients_source_name", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("ingredients_source_reference", sa.Text(), nullable=True))
    op.add_column(
        "food",
        sa.Column("nova_classification", sa.Text(), server_default="unknown", nullable=False),
    )
    op.add_column(
        "food",
        sa.Column("nova_review_status", sa.Text(), server_default="unreviewed", nullable=False),
    )
    for column in ("selenium_mcg", "iodine_mcg", "folate_dfe_mcg", "vitamin_a_rae_mcg"):
        op.add_column("food", sa.Column(column, sa.Numeric(10, 3), nullable=True))

    op.create_check_constraint(
        "ck_food_primary_category",
        "food",
        f"primary_category_key IS NULL OR primary_category_key IN ({quoted(PRIMARY_CATEGORIES)})",
    )
    op.create_check_constraint(
        "ck_food_kind", "food", "food_kind IN ('simple','composite','unknown')"
    )
    op.create_check_constraint(
        "ck_food_group_data_status", "food", "group_data_status IN ('known','estimated','unknown')"
    )
    op.create_check_constraint(
        "ck_food_group_data_completeness",
        "food",
        "group_data_completeness IN ('complete','partial','unknown')",
    )
    op.create_check_constraint(
        "ck_food_nutrition_source_type",
        "food",
        f"nutrition_source_type IN ({quoted(SOURCE_TYPES)})",
    )
    op.create_check_constraint(
        "ck_food_ingredients_source_type",
        "food",
        f"ingredients_source_type IS NULL OR ingredients_source_type IN ({quoted(INGREDIENT_SOURCE_TYPES)})",
    )
    op.create_check_constraint(
        "ck_food_nova_classification", "food", "nova_classification IN ('1','2','3','4','unknown')"
    )
    op.create_check_constraint(
        "ck_food_nova_review_status", "food", "nova_review_status IN ('unreviewed','reviewed')"
    )
    op.create_check_constraint(
        "ck_food_wave1_exact_nutrients_nonnegative",
        "food",
        " AND ".join(
            f"({column} IS NULL OR {column} >= 0)"
            for column in (
                "fiber_g",
                "added_sugar_g",
                "saturated_fat_g",
                "trans_fat_g",
                "sodium_mg",
                "potassium_mg",
                "cholesterol_mg",
                "calcium_mg",
                "iron_mg",
                "magnesium_mg",
                "zinc_mg",
                "selenium_mcg",
                "vitamin_b12_mcg",
                "folate_dfe_mcg",
                "vitamin_a_rae_mcg",
                "iodine_mcg",
            )
        ),
    )
    op.create_check_constraint(
        "ck_food_core_nonnegative",
        "food",
        "calories >= 0 AND protein_g >= 0 AND carb_g >= 0 AND fat_g >= 0",
    )
    op.create_check_constraint(
        "ck_food_nutrition_unit_basis",
        "food",
        "(nutrition_basis::text = 'per_100g' AND unit_basis::text = 'g') OR (nutrition_basis::text = 'per_100ml' AND unit_basis::text = 'ml')",
    )
    op.execute("CREATE INDEX ix_food_principal_lower_name ON food (principal_id, lower(name))")
    op.execute(
        "CREATE INDEX ix_food_principal_created_desc ON food (principal_id, created_at DESC)"
    )
    op.create_index(
        "ix_food_principal_primary_category", "food", ["principal_id", "primary_category_key"]
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM food WHERE primary_category_key IS NOT NULL OR food_kind <> 'unknown'
              OR group_data_status <> 'unknown' OR group_data_completeness <> 'unknown'
              OR nutrition_source_type <> 'unknown' OR nutrition_source_name IS NOT NULL
              OR nutrition_source_reference IS NOT NULL OR ingredients_text IS NOT NULL
              OR ingredients_source_type IS NOT NULL OR ingredients_source_name IS NOT NULL
              OR ingredients_source_reference IS NOT NULL OR nova_classification <> 'unknown'
              OR nova_review_status <> 'unreviewed' OR selenium_mcg IS NOT NULL OR iodine_mcg IS NOT NULL
              OR folate_dfe_mcg IS NOT NULL OR vitamin_a_rae_mcg IS NOT NULL
          ) THEN RAISE EXCEPTION 'Lossy downgrade of Food quality data is prohibited.'; END IF;
        END $$;
        """
    )
    op.drop_index("ix_food_principal_primary_category", table_name="food")
    op.execute("DROP INDEX ix_food_principal_created_desc")
    op.execute("DROP INDEX ix_food_principal_lower_name")
    for name in (
        "ck_food_nutrition_unit_basis",
        "ck_food_core_nonnegative",
        "ck_food_wave1_exact_nutrients_nonnegative",
        "ck_food_nova_review_status",
        "ck_food_nova_classification",
        "ck_food_ingredients_source_type",
        "ck_food_nutrition_source_type",
        "ck_food_group_data_completeness",
        "ck_food_group_data_status",
        "ck_food_kind",
        "ck_food_primary_category",
    ):
        op.drop_constraint(name, "food", type_="check")
    for column in (
        "vitamin_a_rae_mcg",
        "folate_dfe_mcg",
        "iodine_mcg",
        "selenium_mcg",
        "nova_review_status",
        "nova_classification",
        "ingredients_source_reference",
        "ingredients_source_name",
        "ingredients_source_type",
        "ingredients_text",
        "nutrition_source_reference",
        "nutrition_source_name",
        "nutrition_source_type",
        "group_data_completeness",
        "group_data_status",
        "food_kind",
        "primary_category_key",
    ):
        op.drop_column("food", column)
