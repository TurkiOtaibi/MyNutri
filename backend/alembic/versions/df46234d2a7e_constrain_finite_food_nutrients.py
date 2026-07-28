"""Constrain Food nutrition values to finite numerics.

Revision ID: df46234d2a7e
Revises: 0014_v2_food_taxonomy
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "df46234d2a7e"
down_revision: str | None = "0014_v2_food_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
SPECIAL_VALUES = "('NaN', 'Infinity', '-Infinity')"


def _finite_check(columns: tuple[str, ...]) -> str:
    return " AND ".join(f"{column} NOT IN {SPECIAL_VALUES}" for column in columns)


def _preflight_sql() -> str:
    checks = [
        (
            f"SELECT 'food.{column}' AS field_name, count(*) AS invalid_count "
            f"FROM food WHERE {column} IN {SPECIAL_VALUES}"
        )
        for column in FOOD_NUMERIC_COLUMNS
    ]
    checks.append(
        "SELECT 'food_group_contribution.amount_per_100_basis' AS field_name, "
        "count(*) AS invalid_count FROM food_group_contribution "
        f"WHERE amount_per_100_basis IN {SPECIAL_VALUES}"
    )
    union = "\nUNION ALL\n".join(checks)
    return f"""
DO $$
DECLARE
    invalid_counts jsonb;
BEGIN
    SELECT jsonb_object_agg(field_name, invalid_count)
      INTO invalid_counts
      FROM (
{union}
      ) AS checks
     WHERE invalid_count > 0;

    IF invalid_counts IS NOT NULL THEN
        RAISE EXCEPTION
            'Plan 009 cannot add finite Food constraints; special-value counts: %',
            invalid_counts
            USING ERRCODE = 'check_violation';
    END IF;
END
$$
"""


def upgrade() -> None:
    op.execute(_preflight_sql())
    op.create_check_constraint(
        "ck_food_numeric_values_finite",
        "food",
        _finite_check(FOOD_NUMERIC_COLUMNS),
    )
    op.create_check_constraint(
        "ck_food_group_contribution_amount_finite",
        "food_group_contribution",
        f"amount_per_100_basis NOT IN {SPECIAL_VALUES}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_food_group_contribution_amount_finite",
        "food_group_contribution",
        type_="check",
    )
    op.drop_constraint("ck_food_numeric_values_finite", "food", type_="check")
