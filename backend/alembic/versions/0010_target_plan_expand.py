"""expand immutable target plans and idempotency

Revision ID: 0010_target_plan_expand
Revises: 0009_legacy_target_transition_expand
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_target_plan_expand"
down_revision: str | None = "0009_legacy_target_transition_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.add_column("profile", sa.Column("cut_intensity", sa.Numeric(4, 3), server_default="0.200", nullable=False))
    op.create_check_constraint("ck_profile_cut_intensity", "profile", "cut_intensity IN (0.150,0.200,0.250)")
    op.create_table(
        "target_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("calendar_timezone", sa.String(64), nullable=False),
        sa.Column("predecessor_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("superseded_by_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activation_idempotency_key", sa.String(128), nullable=False),
        sa.Column("calculation_document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculation_document_schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("calculation_engine_version", sa.String(32), nullable=False),
        sa.Column("nutrition_registry_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active','scheduled','closed','superseded_before_effective')", name="ck_target_plan_status"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_target_plan_period"),
        sa.CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_target_plan_timezone"),
        sa.CheckConstraint("calculation_document_schema_version > 0", name="ck_target_plan_document_version"),
        sa.CheckConstraint("(status IN ('active','closed') AND activated_at IS NOT NULL) OR (status IN ('scheduled','superseded_before_effective') AND activated_at IS NULL)", name="ck_target_plan_activation_state"),
        sa.CheckConstraint("status <> 'superseded_before_effective' OR (superseded_at IS NOT NULL AND superseded_by_plan_id IS NOT NULL)", name="ck_target_plan_supersession_state"),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id", "principal_id"], ["profile.id", "profile.principal_id"], name="fk_target_plan_profile_owner", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "principal_id", name="uq_target_plan_id_principal"),
        sa.UniqueConstraint("principal_id", "activation_idempotency_key", name="uq_target_plan_principal_key"),
    )
    op.create_foreign_key("fk_target_plan_predecessor_owner", "target_plan", "target_plan", ["predecessor_plan_id", "principal_id"], ["id", "principal_id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_target_plan_superseding_owner", "target_plan", "target_plan", ["superseded_by_plan_id", "principal_id"], ["id", "principal_id"], ondelete="RESTRICT", deferrable=True, initially="DEFERRED")
    op.create_index("ix_target_plan_principal_effective", "target_plan", ["principal_id", "effective_from"])
    op.execute("CREATE UNIQUE INDEX uq_target_plan_one_active ON target_plan (principal_id) WHERE status='active' AND effective_to IS NULL")
    op.execute("CREATE UNIQUE INDEX uq_target_plan_one_scheduled ON target_plan (principal_id) WHERE status='scheduled'")
    op.execute("ALTER TABLE target_plan ADD CONSTRAINT ex_target_plan_effective_period EXCLUDE USING gist (principal_id WITH =, daterange(effective_from,effective_to,'[)') WITH &&) WHERE (status IN ('active','closed'))")
    op.execute(
        """
        CREATE FUNCTION protect_target_plan_content() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id OR NEW.principal_id IS DISTINCT FROM OLD.principal_id
             OR NEW.profile_id IS DISTINCT FROM OLD.profile_id OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
             OR NEW.calendar_timezone IS DISTINCT FROM OLD.calendar_timezone
             OR NEW.activation_idempotency_key IS DISTINCT FROM OLD.activation_idempotency_key
             OR NEW.calculation_document IS DISTINCT FROM OLD.calculation_document
             OR NEW.calculation_document_schema_version IS DISTINCT FROM OLD.calculation_document_schema_version
             OR NEW.calculation_engine_version IS DISTINCT FROM OLD.calculation_engine_version
             OR NEW.nutrition_registry_version IS DISTINCT FROM OLD.nutrition_registry_version
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
          THEN RAISE EXCEPTION 'Target Plan immutable content cannot be changed' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER target_plan_immutable_content_trigger BEFORE UPDATE ON target_plan
          FOR EACH ROW EXECUTE FUNCTION protect_target_plan_content();
        """
    )
    op.create_table(
        "idempotency_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("response_document", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('in_progress','completed')", name="ck_idempotency_state"),
        sa.CheckConstraint("(state='in_progress' AND response_status IS NULL AND response_document IS NULL AND completed_at IS NULL) OR (state='completed' AND response_status IS NOT NULL AND response_document IS NOT NULL AND completed_at IS NOT NULL)", name="ck_idempotency_completion"),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("principal_id", "operation", "idempotency_key", name="uq_idempotency_scope"),
    )
    op.create_index("ix_idempotency_expiry", "idempotency_record", ["expires_at"])


def downgrade() -> None:
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM target_plan) OR EXISTS (SELECT 1 FROM idempotency_record) THEN RAISE EXCEPTION 'Lossy Target Plan downgrade prohibited.'; END IF; END $$;")
    op.drop_table("idempotency_record")
    op.execute("DROP TRIGGER target_plan_immutable_content_trigger ON target_plan")
    op.execute("DROP FUNCTION protect_target_plan_content()")
    op.drop_table("target_plan")
    op.drop_constraint("ck_profile_cut_intensity", "profile", type_="check")
    op.drop_column("profile", "cut_intensity")
