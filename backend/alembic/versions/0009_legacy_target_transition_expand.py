"""expand legacy target transition snapshot reader boundary

Revision ID: 0009_legacy_target_transition_expand
Revises: 0008_food_groups_expand
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_legacy_target_transition_expand"
down_revision: str | None = "0008_food_groups_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
    op.create_table(
        "legacy_target_transition_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transition_date", sa.Date(), nullable=False),
        sa.Column("calendar_timezone", sa.String(64), nullable=False),
        sa.Column("target_document_schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("legacy_target_document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_legacy_transition_timezone"),
        sa.CheckConstraint("target_document_schema_version = 1", name="ck_legacy_transition_schema_version"),
        sa.CheckConstraint(
            "jsonb_typeof(legacy_target_document)='object' AND "
            "legacy_target_document->>'schema_version'='1' AND "
            "legacy_target_document->>'source'='legacy_unversioned_transition' AND "
            "jsonb_typeof(legacy_target_document->'captured_profile_inputs')='object' AND "
            "jsonb_typeof(legacy_target_document->'resolved_targets')='object'",
            name="ck_legacy_transition_document_shape",
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["profile_id", "principal_id"], ["profile.id", "profile.principal_id"],
            name="fk_legacy_transition_profile_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "principal_id", name="uq_legacy_transition_id_principal"),
        sa.UniqueConstraint("profile_id", name="uq_legacy_transition_profile"),
        sa.UniqueConstraint("principal_id", "transition_date", name="uq_legacy_transition_date"),
    )
    op.create_index(
        "ix_legacy_transition_principal_date",
        "legacy_target_transition_snapshots",
        ["principal_id", "transition_date"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_legacy_transition_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          RAISE EXCEPTION 'Legacy target transition snapshots are immutable' USING ERRCODE='23514';
        END $$;
        CREATE TRIGGER legacy_transition_immutable_trigger
          BEFORE UPDATE OR DELETE ON legacy_target_transition_snapshots
          FOR EACH ROW EXECUTE FUNCTION reject_legacy_transition_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM legacy_target_transition_snapshots)
          THEN RAISE EXCEPTION 'Lossy downgrade of transition snapshots is prohibited.'; END IF;
        END $$;
        """
    )
    op.execute("DROP TRIGGER legacy_transition_immutable_trigger ON legacy_target_transition_snapshots")
    op.execute("DROP FUNCTION reject_legacy_transition_mutation()")
    op.drop_table("legacy_target_transition_snapshots")
