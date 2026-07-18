"""Convert owner-scoped Foods into a global admin-managed catalog.

Revision ID: 0013_v2_shared_food_catalog
Revises: 0012_v2_principal_auth_expand
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_v2_shared_food_catalog"
down_revision: str | None = "0012_v2_principal_auth_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("fk_diary_entry_food_owner", "diary_entry", type_="foreignkey")
    op.drop_constraint(
        "fk_food_group_contribution_food_owner",
        "food_group_contribution",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_food_analytical_trait_food_owner",
        "food_analytical_trait",
        type_="foreignkey",
    )

    op.drop_constraint("uq_food_id_principal_id", "food", type_="unique")
    op.drop_constraint(
        "uq_food_group_contribution_id_principal",
        "food_group_contribution",
        type_="unique",
    )
    op.drop_constraint(
        "uq_food_analytical_trait_id_principal",
        "food_analytical_trait",
        type_="unique",
    )

    op.drop_index("ix_food_principal_lower_name", table_name="food")
    op.drop_index("ix_food_principal_created_desc", table_name="food")
    op.drop_index("ix_food_principal_primary_category", table_name="food")
    op.drop_index("ix_food_principal_id", table_name="food")
    op.drop_index(
        "ix_food_group_contribution_principal_id",
        table_name="food_group_contribution",
    )
    op.drop_index(
        "ix_food_analytical_trait_principal_id",
        table_name="food_analytical_trait",
    )

    op.alter_column("food", "principal_id", new_column_name="created_by_principal_id")
    op.alter_column(
        "food_group_contribution",
        "principal_id",
        new_column_name="created_by_principal_id",
    )
    op.alter_column(
        "food_analytical_trait",
        "principal_id",
        new_column_name="created_by_principal_id",
    )

    op.add_column(
        "food",
        sa.Column("updated_by_principal_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "food",
        sa.Column("archived_by_principal_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "food", sa.Column("status", sa.Text(), server_default="active", nullable=False)
    )
    op.add_column(
        "food", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("food", sa.Column("normalized_name", sa.String(length=512), nullable=True))
    op.execute("UPDATE food SET updated_by_principal_id=created_by_principal_id")
    op.execute(
        "UPDATE food SET normalized_name="
        "lower(regexp_replace(trim(name), '\\s+', ' ', 'g'))"
    )
    op.alter_column("food", "normalized_name", nullable=False)

    op.create_foreign_key(
        "fk_food_updated_by_principal",
        "food",
        "principal",
        ["updated_by_principal_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_food_archived_by_principal",
        "food",
        "principal",
        ["archived_by_principal_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_food_group_contribution_food",
        "food_group_contribution",
        "food",
        ["food_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_food_analytical_trait_food",
        "food_analytical_trait",
        "food",
        ["food_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint("ck_food_status", "food", "status IN ('active','archived')")
    op.create_check_constraint(
        "ck_food_archive_state",
        "food",
        "(status='active' AND archived_at IS NULL AND archived_by_principal_id IS NULL) OR "
        "(status='archived' AND archived_at IS NOT NULL AND archived_by_principal_id IS NOT NULL)",
    )
    op.create_index("ix_food_catalog_lower_name", "food", [sa.text("lower(name)")])
    op.create_index(
        "ix_food_catalog_created_desc", "food", [sa.text("created_at DESC")]
    )
    op.create_index(
        "ix_food_created_by_principal_id", "food", ["created_by_principal_id"]
    )
    op.create_index(
        "ix_food_group_contribution_created_by",
        "food_group_contribution",
        ["created_by_principal_id"],
    )
    op.create_index(
        "ix_food_analytical_trait_created_by",
        "food_analytical_trait",
        ["created_by_principal_id"],
    )
    op.create_unique_constraint(
        "uq_food_catalog_duplicate",
        "food",
        [
            "normalized_name",
            "nutrition_basis",
            "default_unit_type",
            "unit_amount",
            "unit_basis",
        ],
    )


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM food WHERE status='archived') OR "
        "EXISTS (SELECT 1 FROM diary_entry d JOIN food f ON f.id=d.food_id "
        "WHERE d.principal_id<>f.created_by_principal_id) OR "
        "EXISTS (SELECT 1 FROM food_group_contribution c JOIN food f ON f.id=c.food_id "
        "WHERE c.created_by_principal_id<>f.created_by_principal_id) OR "
        "EXISTS (SELECT 1 FROM food_analytical_trait t JOIN food f ON f.id=t.food_id "
        "WHERE t.created_by_principal_id<>f.created_by_principal_id) "
        "THEN RAISE EXCEPTION 'Lossy shared catalog downgrade prohibited.'; END IF; END $$;"
    )
    op.drop_constraint("uq_food_catalog_duplicate", "food", type_="unique")
    op.drop_index("ix_food_analytical_trait_created_by", table_name="food_analytical_trait")
    op.drop_index("ix_food_group_contribution_created_by", table_name="food_group_contribution")
    op.drop_index("ix_food_created_by_principal_id", table_name="food")
    op.drop_index("ix_food_catalog_created_desc", table_name="food")
    op.drop_index("ix_food_catalog_lower_name", table_name="food")
    op.drop_constraint("ck_food_archive_state", "food", type_="check")
    op.drop_constraint("ck_food_status", "food", type_="check")
    op.drop_constraint(
        "fk_food_analytical_trait_food", "food_analytical_trait", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_food_group_contribution_food", "food_group_contribution", type_="foreignkey"
    )
    op.drop_constraint("fk_food_archived_by_principal", "food", type_="foreignkey")
    op.drop_constraint("fk_food_updated_by_principal", "food", type_="foreignkey")
    op.drop_column("food", "archived_at")
    op.drop_column("food", "status")
    op.drop_column("food", "archived_by_principal_id")
    op.drop_column("food", "updated_by_principal_id")
    op.drop_column("food", "normalized_name")
    op.alter_column(
        "food_analytical_trait",
        "created_by_principal_id",
        new_column_name="principal_id",
    )
    op.alter_column(
        "food_group_contribution",
        "created_by_principal_id",
        new_column_name="principal_id",
    )
    op.alter_column("food", "created_by_principal_id", new_column_name="principal_id")
    op.create_unique_constraint("uq_food_id_principal_id", "food", ["id", "principal_id"])
    op.create_unique_constraint(
        "uq_food_group_contribution_id_principal",
        "food_group_contribution",
        ["id", "principal_id"],
    )
    op.create_unique_constraint(
        "uq_food_analytical_trait_id_principal",
        "food_analytical_trait",
        ["id", "principal_id"],
    )
    op.create_foreign_key(
        "fk_food_group_contribution_food_owner",
        "food_group_contribution",
        "food",
        ["food_id", "principal_id"],
        ["id", "principal_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_food_analytical_trait_food_owner",
        "food_analytical_trait",
        "food",
        ["food_id", "principal_id"],
        ["id", "principal_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_diary_entry_food_owner",
        "diary_entry",
        "food",
        ["food_id", "principal_id"],
        ["id", "principal_id"],
    )
    op.create_index("ix_food_principal_id", "food", ["principal_id"])
    op.execute("CREATE INDEX ix_food_principal_lower_name ON food (principal_id, lower(name))")
    op.execute(
        "CREATE INDEX ix_food_principal_created_desc ON food (principal_id, created_at DESC)"
    )
    op.create_index(
        "ix_food_principal_primary_category", "food", ["principal_id", "primary_category_key"]
    )
    op.create_index(
        "ix_food_group_contribution_principal_id",
        "food_group_contribution",
        ["principal_id"],
    )
    op.create_index(
        "ix_food_analytical_trait_principal_id",
        "food_analytical_trait",
        ["principal_id"],
    )
