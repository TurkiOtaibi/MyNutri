"""foods v1 per-basis schema

Revision ID: 0002_foods_v1_per_basis
Revises: 0001_initial
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_foods_v1_per_basis"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


nutrition_basis_enum = sa.Enum("per_100g", "per_100ml", name="nutrition_basis_enum")
default_unit_type_enum = sa.Enum(
    "g",
    "ml",
    "cup",
    "slice",
    "piece",
    "scoop",
    "serving",
    "tablespoon",
    "teaspoon",
    name="default_unit_type_enum",
)
unit_basis_enum = sa.Enum("g", "ml", name="unit_basis_enum")


def upgrade() -> None:
    bind = op.get_bind()
    nutrition_basis_enum.create(bind, checkfirst=True)
    default_unit_type_enum.create(bind, checkfirst=True)
    unit_basis_enum.create(bind, checkfirst=True)

    op.add_column("food", sa.Column("brand", sa.String(), nullable=True))
    op.add_column("food", sa.Column("category", sa.String(), nullable=True))
    op.add_column(
        "food",
        sa.Column(
            "nutrition_basis",
            nutrition_basis_enum,
            nullable=False,
            server_default="per_100g",
        ),
    )
    op.add_column(
        "food",
        sa.Column(
            "default_unit_type",
            default_unit_type_enum,
            nullable=False,
            server_default="serving",
        ),
    )
    op.add_column(
        "food",
        sa.Column("unit_amount", sa.Numeric(8, 2), nullable=False, server_default="100"),
    )
    op.add_column(
        "food",
        sa.Column("unit_basis", unit_basis_enum, nullable=False, server_default="g"),
    )
    op.add_column("food", sa.Column("sugar_g", sa.Numeric(7, 2), nullable=True))
    op.add_column("food", sa.Column("potassium_mg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("calcium_mg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("iron_mg", sa.Numeric(7, 2), nullable=True))
    op.add_column("food", sa.Column("magnesium_mg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("zinc_mg", sa.Numeric(7, 2), nullable=True))
    op.add_column("food", sa.Column("vitamin_d_mcg", sa.Numeric(7, 2), nullable=True))
    op.add_column("food", sa.Column("vitamin_b12_mcg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("vitamin_c_mg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("vitamin_a_mcg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("folate_mcg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("vitamin_k_mcg", sa.Numeric(8, 2), nullable=True))
    op.add_column("food", sa.Column("notes", sa.String(), nullable=True))
    op.add_column("food", sa.Column("data_source", sa.String(), nullable=True))

    op.execute("UPDATE food SET unit_amount = COALESCE(serving_grams, 100)")
    op.execute("UPDATE food SET sugar_g = total_sugars_g")
    op.execute(
        """
        UPDATE food
        SET
          calories = ROUND(calories * 100 / serving_grams, 2),
          protein_g = ROUND(protein_g * 100 / serving_grams, 2),
          carb_g = ROUND(carb_g * 100 / serving_grams, 2),
          fat_g = ROUND(fat_g * 100 / serving_grams, 2),
          saturated_fat_g = CASE WHEN saturated_fat_g IS NULL THEN NULL ELSE ROUND(saturated_fat_g * 100 / serving_grams, 2) END,
          trans_fat_g = CASE WHEN trans_fat_g IS NULL THEN NULL ELSE ROUND(trans_fat_g * 100 / serving_grams, 2) END,
          cholesterol_mg = CASE WHEN cholesterol_mg IS NULL THEN NULL ELSE ROUND(cholesterol_mg * 100 / serving_grams, 2) END,
          sodium_mg = CASE WHEN sodium_mg IS NULL THEN NULL ELSE ROUND(sodium_mg * 100 / serving_grams, 2) END,
          fiber_g = CASE WHEN fiber_g IS NULL THEN NULL ELSE ROUND(fiber_g * 100 / serving_grams, 2) END,
          sugar_g = CASE WHEN sugar_g IS NULL THEN NULL ELSE ROUND(sugar_g * 100 / serving_grams, 2) END,
          added_sugar_g = CASE WHEN added_sugar_g IS NULL THEN NULL ELSE ROUND(added_sugar_g * 100 / serving_grams, 2) END
        WHERE serving_grams IS NOT NULL AND serving_grams > 0
        """
    )

    op.drop_column("food", "serving_label")
    op.drop_column("food", "serving_grams")
    op.drop_column("food", "total_sugars_g")
    op.alter_column("food", "nutrition_basis", server_default=None)
    op.alter_column("food", "default_unit_type", server_default=None)
    op.alter_column("food", "unit_amount", server_default=None)
    op.alter_column("food", "unit_basis", server_default=None)


def downgrade() -> None:
    op.add_column("food", sa.Column("serving_label", sa.String(), nullable=True))
    op.add_column("food", sa.Column("serving_grams", sa.Numeric(7, 2), nullable=True))
    op.add_column("food", sa.Column("total_sugars_g", sa.Numeric(7, 2), nullable=True))
    op.execute("UPDATE food SET serving_label = default_unit_type")
    op.execute("UPDATE food SET serving_grams = unit_amount")
    op.execute("UPDATE food SET total_sugars_g = sugar_g")
    op.alter_column("food", "serving_label", nullable=False)

    for column in (
        "data_source",
        "notes",
        "vitamin_k_mcg",
        "folate_mcg",
        "vitamin_a_mcg",
        "vitamin_c_mg",
        "vitamin_b12_mcg",
        "vitamin_d_mcg",
        "zinc_mg",
        "magnesium_mg",
        "iron_mg",
        "calcium_mg",
        "potassium_mg",
        "sugar_g",
        "unit_basis",
        "unit_amount",
        "default_unit_type",
        "nutrition_basis",
        "category",
        "brand",
    ):
        op.drop_column("food", column)

    bind = op.get_bind()
    unit_basis_enum.drop(bind, checkfirst=True)
    default_unit_type_enum.drop(bind, checkfirst=True)
    nutrition_basis_enum.drop(bind, checkfirst=True)
