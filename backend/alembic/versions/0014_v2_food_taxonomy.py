"""Install Food Taxonomy V2 and Snapshot v3 compatibility.

Revision ID: 0014_v2_food_taxonomy
Revises: 0013_v2_shared_food_catalog
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_v2_food_taxonomy"
down_revision: str | None = "0013_v2_shared_food_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_taxonomy_v2_migration_audit",
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legacy_category", sa.Text(), nullable=True),
        sa.Column("legacy_primary_category_key", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["food.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("food_id"),
    )
    op.execute(
        "INSERT INTO food_taxonomy_v2_migration_audit "
        "(food_id,legacy_category,legacy_primary_category_key) "
        "SELECT id,category,primary_category_key FROM food"
    )
    op.drop_constraint("ck_food_primary_category", "food", type_="check")
    op.alter_column("food", "primary_category_key", new_column_name="food_category_key")
    op.add_column("food", sa.Column("grain_type", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("baked_good_type", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("grain_starch_type", sa.Text(), nullable=True))
    op.add_column(
        "food",
        sa.Column(
            "taxonomy_review_required", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.execute(
        "UPDATE food SET grain_type='whole', food_category_key='grains_starches', "
        "grain_starch_type='other', taxonomy_review_required=true "
        "WHERE food_category_key='whole_grains'"
    )
    op.execute(
        "UPDATE food SET grain_type='refined', food_category_key='grains_starches', "
        "grain_starch_type='other', taxonomy_review_required=true "
        "WHERE food_category_key='refined_grains'"
    )
    op.execute(
        "UPDATE food SET food_category_key='other', taxonomy_review_required=true "
        "WHERE food_category_key IS NULL"
    )
    op.drop_column("food", "category")
    op.alter_column("food", "food_category_key", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(
        "ck_food_category_v2",
        "food",
        "food_category_key IN ('vegetables','fruits','legumes','grains_starches',"
        "'baked_goods','nuts_seeds','seafood','dairy_fortified_alternatives','eggs',"
        "'poultry','red_meat','processed_meat','added_oils_fats','sweets',"
        "'sugar_sweetened_beverages','unsweetened_beverages','herbs_spices','mixed_dish','other')",
    )
    op.create_check_constraint(
        "ck_food_grain_type",
        "food",
        "grain_type IS NULL OR grain_type IN ('whole','refined','mixed','grain_free','unknown')",
    )
    op.create_check_constraint(
        "ck_food_baked_good_type",
        "food",
        "baked_good_type IS NULL OR baked_good_type IN ('arabic_bread','toast','rolls_wraps',"
        "'burger_bun','flatbread','pastries','cake','biscuits_cookies','other')",
    )
    op.create_check_constraint(
        "ck_food_grain_starch_type",
        "food",
        "grain_starch_type IS NULL OR grain_starch_type IN ('rice','pasta','oats',"
        "'breakfast_cereal','bulgur','quinoa','flour','other')",
    )
    op.create_check_constraint(
        "ck_food_category_details_v2",
        "food",
        "(food_category_key='baked_goods' AND baked_good_type IS NOT NULL AND grain_type IS NOT NULL AND grain_starch_type IS NULL) OR "
        "(food_category_key='grains_starches' AND grain_starch_type IS NOT NULL AND grain_type IS NOT NULL AND baked_good_type IS NULL) OR "
        "(food_category_key NOT IN ('baked_goods','grains_starches') AND baked_good_type IS NULL AND grain_starch_type IS NULL AND grain_type IS NULL)",
    )
    op.create_index(
        "ix_food_catalog_category_status", "food", ["food_category_key", "status"]
    )

    op.drop_constraint("ck_diary_entry_snapshot_version", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_v2_shape", "diary_entry", type_="check")
    op.create_check_constraint(
        "ck_diary_entry_snapshot_version",
        "diary_entry",
        "snapshot_schema_version IS NULL OR snapshot_schema_version IN (2,3)",
    )
    op.execute(
        "ALTER TABLE diary_entry ADD CONSTRAINT ck_diary_entry_versioned_shape CHECK ("
        "snapshot_schema_version IS NULL OR (jsonb_typeof(nutrition_snapshot)='object' AND "
        "nutrition_snapshot->>'schema_version'=snapshot_schema_version::text))"
    )


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM diary_entry WHERE snapshot_schema_version=3) OR "
        "EXISTS (SELECT 1 FROM food f LEFT JOIN food_taxonomy_v2_migration_audit a "
        "ON a.food_id=f.id WHERE a.food_id IS NULL) "
        "THEN RAISE EXCEPTION 'Lossy Food Taxonomy V2 downgrade prohibited.'; END IF; END $$;"
    )
    op.drop_constraint("ck_diary_entry_versioned_shape", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_snapshot_version", "diary_entry", type_="check")
    op.create_check_constraint(
        "ck_diary_entry_snapshot_version",
        "diary_entry",
        "snapshot_schema_version IS NULL OR snapshot_schema_version=2",
    )
    op.execute(
        "ALTER TABLE diary_entry ADD CONSTRAINT ck_diary_entry_v2_shape CHECK ("
        "snapshot_schema_version IS NULL OR (jsonb_typeof(nutrition_snapshot)='object' "
        "AND nutrition_snapshot->>'schema_version'='2'))"
    )
    op.drop_index("ix_food_catalog_category_status", table_name="food")
    op.drop_constraint("ck_food_category_details_v2", "food", type_="check")
    op.drop_constraint("ck_food_grain_starch_type", "food", type_="check")
    op.drop_constraint("ck_food_baked_good_type", "food", type_="check")
    op.drop_constraint("ck_food_grain_type", "food", type_="check")
    op.drop_constraint("ck_food_category_v2", "food", type_="check")
    op.add_column("food", sa.Column("category", sa.Text(), nullable=True))
    op.execute(
        "UPDATE food f SET category=a.legacy_category, "
        "food_category_key=a.legacy_primary_category_key "
        "FROM food_taxonomy_v2_migration_audit a WHERE a.food_id=f.id"
    )
    op.alter_column("food", "food_category_key", new_column_name="primary_category_key")
    op.drop_column("food", "taxonomy_review_required")
    op.drop_column("food", "grain_starch_type")
    op.drop_column("food", "baked_good_type")
    op.drop_column("food", "grain_type")
    op.create_check_constraint(
        "ck_food_primary_category",
        "food",
        "primary_category_key IS NULL OR primary_category_key IN ('vegetables','fruits',"
        "'legumes','whole_grains','refined_grains','nuts_seeds','seafood',"
        "'dairy_fortified_alternatives','eggs','poultry','red_meat','processed_meat',"
        "'added_oils_fats','sweets','sugar_sweetened_beverages','unsweetened_beverages',"
        "'herbs_spices','mixed_dish','other')",
    )
    op.drop_table("food_taxonomy_v2_migration_audit")
