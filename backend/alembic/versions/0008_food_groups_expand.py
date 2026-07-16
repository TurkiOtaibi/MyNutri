"""expand normalized Food groups and analytical traits

Revision ID: 0008_food_groups_expand
Revises: 0007_food_quality_expand
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_food_groups_expand"
down_revision: str | None = "0007_food_quality_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GROUP_KEYS = (
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
)
TRAIT_KEYS = (
    "sweetened",
    "non_nutritive_sweetened",
    "processed",
    "omega3_rich_seafood",
    "calcium_fortified",
    "unsaturated_fat_source",
    "smoked",
    "salted",
    "fruit_liquid_100_percent",
    "dried_fruit",
    "starchy_root",
)


def quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "food_group_contribution",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_key", sa.Text(), nullable=False),
        sa.Column("subtype_key", sa.Text(), nullable=True),
        sa.Column("amount_per_100_basis", sa.Numeric(6, 3), nullable=False),
        sa.Column("data_status", sa.Text(), nullable=False),
        sa.Column("food_group_rules_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"group_key IN ({quoted(GROUP_KEYS)})", name="ck_food_group_contribution_key"
        ),
        sa.CheckConstraint(
            "amount_per_100_basis > 0 AND amount_per_100_basis <= 100",
            name="ck_food_group_contribution_amount",
        ),
        sa.CheckConstraint(
            "data_status IN ('known','estimated')", name="ck_food_group_contribution_status"
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["food_id", "principal_id"],
            ["food.id", "food.principal_id"],
            name="fk_food_group_contribution_food_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("food_id", "group_key", name="uq_food_group_contribution_food_group"),
        sa.UniqueConstraint("id", "principal_id", name="uq_food_group_contribution_id_principal"),
    )
    op.create_index(
        "ix_food_group_contribution_principal_id", "food_group_contribution", ["principal_id"]
    )
    op.create_index("ix_food_group_contribution_food_id", "food_group_contribution", ["food_id"])

    op.create_table(
        "food_analytical_trait",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trait_key", sa.Text(), nullable=False),
        sa.Column("food_group_rules_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"trait_key IN ({quoted(TRAIT_KEYS)})", name="ck_food_analytical_trait_key"
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["food_id", "principal_id"],
            ["food.id", "food.principal_id"],
            name="fk_food_analytical_trait_food_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("food_id", "trait_key", name="uq_food_analytical_trait_food_trait"),
        sa.UniqueConstraint("id", "principal_id", name="uq_food_analytical_trait_id_principal"),
    )
    op.create_index(
        "ix_food_analytical_trait_principal_id", "food_analytical_trait", ["principal_id"]
    )
    op.create_index("ix_food_analytical_trait_food_id", "food_analytical_trait", ["food_id"])

    op.execute(
        """
        CREATE FUNCTION enforce_food_group_contribution_total() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_food uuid := COALESCE(NEW.food_id, OLD.food_id); total numeric;
        BEGIN
          PERFORM pg_advisory_xact_lock(hashtextextended(target_food::text, 0));
          SELECT COALESCE(sum(amount_per_100_basis), 0) INTO total
            FROM food_group_contribution WHERE food_id = target_food;
          IF total > 100.000 THEN
            RAISE EXCEPTION 'Food group contribution total exceeds 100' USING ERRCODE = '23514';
          END IF;
          RETURN COALESCE(NEW, OLD);
        END $$;
        CREATE CONSTRAINT TRIGGER food_group_contribution_total_trigger
          AFTER INSERT OR UPDATE OR DELETE ON food_group_contribution
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
          EXECUTE FUNCTION enforce_food_group_contribution_total();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM food_group_contribution) OR EXISTS (SELECT 1 FROM food_analytical_trait)
          THEN RAISE EXCEPTION 'Lossy downgrade of Food classification data is prohibited.'; END IF;
        END $$;
        """
    )
    op.execute("DROP TRIGGER food_group_contribution_total_trigger ON food_group_contribution")
    op.execute("DROP FUNCTION enforce_food_group_contribution_total()")
    op.drop_table("food_analytical_trait")
    op.drop_table("food_group_contribution")
