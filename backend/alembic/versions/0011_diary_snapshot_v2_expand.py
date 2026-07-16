"""expand Diary target binding and Snapshot v2 support

Revision ID: 0011_diary_snapshot_v2_expand
Revises: 0010_target_plan_expand
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_diary_snapshot_v2_expand"
down_revision: str | None = "0010_target_plan_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diary_entry",
        sa.Column("target_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("diary_entry", sa.Column("target_provenance", sa.Text(), nullable=True))
    op.add_column(
        "diary_entry", sa.Column("snapshot_schema_version", sa.SmallInteger(), nullable=True)
    )
    op.execute("UPDATE diary_entry SET target_provenance='legacy_unversioned'")
    op.alter_column("diary_entry", "target_provenance", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(
        "ck_diary_entry_target_provenance",
        "diary_entry",
        "target_provenance IN ('versioned_plan','legacy_unversioned','no_target_source')",
    )
    op.create_check_constraint(
        "ck_diary_entry_target_binding",
        "diary_entry",
        "(target_provenance = 'versioned_plan' AND target_plan_id IS NOT NULL) OR "
        "(target_provenance IN ('legacy_unversioned','no_target_source') AND target_plan_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_diary_entry_snapshot_version",
        "diary_entry",
        "snapshot_schema_version IS NULL OR snapshot_schema_version = 2",
    )
    op.create_foreign_key(
        "fk_diary_entry_target_plan_owner",
        "diary_entry",
        "target_plan",
        ["target_plan_id", "principal_id"],
        ["id", "principal_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_diary_entry_principal_date_meal_created",
        "diary_entry",
        ["principal_id", "entry_date", "meal_type", "created_at"],
    )
    op.create_index(
        "ix_diary_entry_principal_target_plan",
        "diary_entry",
        ["principal_id", "target_plan_id"],
    )
    op.execute(
        """
        ALTER TABLE diary_entry ADD CONSTRAINT ck_diary_entry_v2_shape CHECK (
          snapshot_schema_version IS NULL OR (
            jsonb_typeof(nutrition_snapshot) = 'object'
            AND nutrition_snapshot->>'schema_version' = '2'
          )
        )
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_diary_snapshot_binding() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.nutrition_snapshot IS DISTINCT FROM OLD.nutrition_snapshot
             OR NEW.snapshot_schema_version IS DISTINCT FROM OLD.snapshot_schema_version
             OR NEW.entry_date IS DISTINCT FROM OLD.entry_date
             OR (NEW.food_id IS DISTINCT FROM OLD.food_id AND NOT (OLD.food_id IS NOT NULL AND NEW.food_id IS NULL))
             OR NEW.principal_id IS DISTINCT FROM OLD.principal_id
          THEN RAISE EXCEPTION 'Diary captured content is immutable' USING ERRCODE='23514'; END IF;
          IF (NEW.target_plan_id IS DISTINCT FROM OLD.target_plan_id
              OR NEW.target_provenance IS DISTINCT FROM OLD.target_provenance)
             AND NOT (
               OLD.target_plan_id IS NULL
               AND OLD.target_provenance = 'no_target_source'
               AND NEW.target_plan_id IS NOT NULL
               AND NEW.target_provenance = 'versioned_plan'
             )
          THEN RAISE EXCEPTION 'Diary target binding is immutable' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER diary_snapshot_binding_immutable_trigger BEFORE UPDATE ON diary_entry
          FOR EACH ROW EXECUTE FUNCTION protect_diary_snapshot_binding();
        """
    )


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM diary_entry WHERE snapshot_schema_version=2 "
        "OR target_plan_id IS NOT NULL) THEN RAISE EXCEPTION 'Lossy Snapshot v2 downgrade prohibited.'; "
        "END IF; END $$;"
    )
    op.execute("DROP TRIGGER diary_snapshot_binding_immutable_trigger ON diary_entry")
    op.execute("DROP FUNCTION protect_diary_snapshot_binding()")
    op.drop_constraint("ck_diary_entry_v2_shape", "diary_entry", type_="check")
    op.drop_index("ix_diary_entry_principal_target_plan", table_name="diary_entry")
    op.drop_index("ix_diary_entry_principal_date_meal_created", table_name="diary_entry")
    op.drop_constraint("fk_diary_entry_target_plan_owner", "diary_entry", type_="foreignkey")
    op.drop_constraint("ck_diary_entry_snapshot_version", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_target_binding", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_target_provenance", "diary_entry", type_="check")
    op.drop_column("diary_entry", "snapshot_schema_version")
    op.drop_column("diary_entry", "target_provenance")
    op.drop_column("diary_entry", "target_plan_id")
