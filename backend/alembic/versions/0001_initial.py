"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


sex_enum = postgresql.ENUM("male", "female", name="sex_enum")
activity_enum = postgresql.ENUM(
    "sedentary", "light", "moderate", "active", "very_active", name="activity_level_enum"
)
goal_enum = postgresql.ENUM("cut", "maintain", "bulk", name="goal_enum")


def upgrade() -> None:
    op.create_table(
        "profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sex", sex_enum, nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("height_cm", sa.Numeric(6, 2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=False),
        sa.Column("activity_level", activity_enum, nullable=False),
        sa.Column("goal", goal_enum, nullable=False),
        sa.Column("protein_per_kg", sa.Numeric(4, 2), nullable=False),
        sa.Column("fat_pct", sa.Numeric(4, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "food",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("serving_label", sa.String(), nullable=False),
        sa.Column("serving_grams", sa.Numeric(7, 2), nullable=True),
        sa.Column("calories", sa.Numeric(8, 2), nullable=False),
        sa.Column("protein_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("carb_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("fat_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("saturated_fat_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("trans_fat_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("cholesterol_mg", sa.Numeric(8, 2), nullable=True),
        sa.Column("sodium_mg", sa.Numeric(8, 2), nullable=True),
        sa.Column("fiber_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("total_sugars_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("added_sugar_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_food_name"), "food", ["name"], unique=False)

    op.create_table(
        "diary_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(8, 3), nullable=False),
        sa.Column("nutrition_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diary_entry_entry_date"), "diary_entry", ["entry_date"], unique=False)
    op.create_index(op.f("ix_diary_entry_food_id"), "diary_entry", ["food_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_diary_entry_food_id"), table_name="diary_entry")
    op.drop_index(op.f("ix_diary_entry_entry_date"), table_name="diary_entry")
    op.drop_table("diary_entry")
    op.drop_index(op.f("ix_food_name"), table_name="food")
    op.drop_table("food")
    op.drop_table("profile")
    goal_enum.drop(op.get_bind(), checkfirst=True)
    activity_enum.drop(op.get_bind(), checkfirst=True)
    sex_enum.drop(op.get_bind(), checkfirst=True)
