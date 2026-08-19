"""add immutable versioned nutrition pattern analysis

Revision ID: c3a7e6d5f210
Revises: b7e31a4c9d20
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import context, op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql

revision = "c3a7e6d5f210"
down_revision = "b7e31a4c9d20"
branch_labels = None
depends_on = None


def _uuid() -> postgresql.UUID:
    return postgresql.UUID(as_uuid=True)


def _json() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "nutrition_analysis",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("as_of_diary_date", sa.Date(), nullable=False),
        sa.Column("calendar_timezone", sa.String(64), nullable=False),
        sa.Column("interface_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("current_revision_id", _uuid()),
        sa.Column("current_revision_number", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "principal_id", name="uq_nutrition_analysis_id_principal"),
        sa.UniqueConstraint("principal_id", "as_of_diary_date", "interface_version", name="uq_nutrition_analysis_principal_date_interface"),
        sa.CheckConstraint("calendar_timezone = 'Asia/Riyadh'", name="ck_nutrition_analysis_timezone"),
        sa.CheckConstraint("interface_version = 1", name="ck_nutrition_analysis_interface"),
        sa.CheckConstraint("(current_revision_id IS NULL AND current_revision_number IS NULL) OR (current_revision_id IS NOT NULL AND current_revision_number >= 1)", name="ck_nutrition_analysis_current_pointer"),
    )
    op.create_index(
        "ix_nutrition_analysis_principal_date_desc",
        "nutrition_analysis",
        ["principal_id", sa.text("as_of_diary_date DESC"), sa.text("id DESC")],
    )
    op.create_table(
        "nutrition_analysis_revision",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("analysis_id", _uuid(), nullable=False),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("previous_period_start", sa.Date(), nullable=False),
        sa.Column("previous_period_end", sa.Date(), nullable=False),
        sa.Column("analysis_rules_version", sa.String(64), nullable=False),
        sa.Column("source_versions", _json(), nullable=False),
        sa.Column("source_input_hash", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("complete_day_count", sa.SmallInteger(), nullable=False),
        sa.Column("previous_complete_day_count", sa.SmallInteger(), nullable=False),
        sa.Column("result_status", sa.String(32), nullable=False),
        sa.Column("result_reason", sa.String(64)),
        sa.Column("analysis_document", _json(), nullable=False),
        sa.Column("supersedes_revision_id", _uuid()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_id", "principal_id"], ["nutrition_analysis.id", "nutrition_analysis.principal_id"], name="fk_nutrition_analysis_revision_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["nutrition_analysis_revision.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "principal_id", name="uq_nutrition_analysis_revision_id_principal"),
        sa.UniqueConstraint("analysis_id", "id", "principal_id", name="uq_nutrition_analysis_revision_series_id_owner"),
        sa.UniqueConstraint("analysis_id", "revision", name="uq_nutrition_analysis_revision_number"),
        sa.UniqueConstraint("analysis_id", "source_input_hash", "analysis_rules_version", name="uq_nutrition_analysis_revision_source"),
        sa.CheckConstraint("revision >= 1", name="ck_nutrition_analysis_revision_positive"),
        sa.CheckConstraint("period_end - period_start = 6 AND previous_period_end - previous_period_start = 6 AND previous_period_end + 1 = period_start", name="ck_nutrition_analysis_revision_windows"),
        sa.CheckConstraint("complete_day_count BETWEEN 0 AND 7 AND previous_complete_day_count BETWEEN 0 AND 7", name="ck_nutrition_analysis_revision_day_counts"),
        sa.CheckConstraint("length(source_input_hash) = 64 AND length(content_hash) = 64", name="ck_nutrition_analysis_revision_hashes"),
        sa.CheckConstraint("result_status IN ('available','insufficient','unavailable')", name="ck_nutrition_analysis_revision_result"),
    )
    op.create_index(
        "ix_nutrition_analysis_revision_history",
        "nutrition_analysis_revision",
        ["principal_id", sa.text("period_end DESC"), sa.text("analysis_id DESC"), sa.text("revision DESC")],
    )
    op.create_foreign_key(
        "fk_nutrition_analysis_current_revision_owner",
        "nutrition_analysis",
        "nutrition_analysis_revision",
        ["id", "current_revision_id", "principal_id"],
        ["analysis_id", "id", "principal_id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "nutrition_analysis_evidence_ref",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("revision_id", _uuid(), nullable=False),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("day_version", sa.BigInteger(), nullable=False),
        sa.Column("source_ref", _uuid(), nullable=False),
        sa.Column("snapshot_schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("metric_key", sa.String(96), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(24, 6)),
        sa.Column("value_state", sa.String(24), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revision_id", "principal_id"], ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"], name="fk_nutrition_analysis_evidence_owner", ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "period", "diary_date", "source_ref", "metric_key", name="uq_nutrition_analysis_evidence_identity"),
        sa.CheckConstraint("period IN ('current','previous')", name="ck_nutrition_analysis_evidence_period"),
        sa.CheckConstraint("day_version >= 0", name="ck_nutrition_analysis_evidence_day_version"),
        sa.CheckConstraint("snapshot_schema_version IN (2,3)", name="ck_nutrition_analysis_evidence_snapshot_version"),
        sa.CheckConstraint("value_state IN ('known','explicit_zero','unknown')", name="ck_nutrition_analysis_evidence_value_state"),
        sa.CheckConstraint("(value_state='unknown' AND value IS NULL) OR (value_state='explicit_zero' AND value=0) OR (value_state='known' AND value IS NOT NULL)", name="ck_nutrition_analysis_evidence_value"),
    )
    op.create_index("ix_nutrition_analysis_evidence_principal_date_desc", "nutrition_analysis_evidence_ref", ["principal_id", sa.text("diary_date DESC")])
    op.create_table(
        "nutrition_analysis_revision_event",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("revision_id", _uuid(), nullable=False),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("successor_revision_id", _uuid()),
        sa.Column("reason", sa.String(96), nullable=False),
        sa.Column("source_day_version", sa.BigInteger()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_id", sa.String(64)),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revision_id", "principal_id"], ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"], name="fk_nutrition_analysis_event_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["successor_revision_id"], ["nutrition_analysis_revision.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", "event_type", "reason", "source_day_version", "successor_revision_id", name="uq_nutrition_analysis_event_identity"),
        sa.CheckConstraint("event_type IN ('day_reopened','day_version_changed','target_source_changed','source_snapshot_corrected','source_version_unsupported','superseded_by_revision')", name="ck_nutrition_analysis_event_type"),
    )
    op.create_index("ix_nutrition_analysis_event_revision_time", "nutrition_analysis_revision_event", ["revision_id", "occurred_at"])
    op.create_table(
        "nutrition_analysis_command_idempotency",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("key_digest", sa.String(64), nullable=False),
        sa.Column("command_hash", sa.String(64), nullable=False),
        sa.Column("captured_date", sa.Date(), nullable=False),
        sa.Column("analysis_id", _uuid()),
        sa.Column("revision_id", _uuid()),
        sa.Column("response_status", sa.SmallInteger(), nullable=False),
        sa.Column("response_headers", _json(), nullable=False),
        sa.Column("response_document", _json(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_id"], ["nutrition_analysis.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revision_id"], ["nutrition_analysis_revision.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("principal_id", "operation", "key_digest", name="uq_nutrition_analysis_command_scope"),
        sa.CheckConstraint("length(key_digest) = 64 AND length(command_hash) = 64", name="ck_nutrition_analysis_command_hashes"),
        sa.CheckConstraint("response_status IN (200,201)", name="ck_nutrition_analysis_command_status"),
    )
    op.create_index("ix_nutrition_analysis_command_expiry", "nutrition_analysis_command_idempotency", ["expires_at"])


def downgrade() -> None:
    if context.is_offline_mode():
        raise CommandError("PLAN032 downgrade requires an online empty-table preflight")
    connection = op.get_bind()
    tables = (
        "nutrition_analysis_command_idempotency",
        "nutrition_analysis_revision_event",
        "nutrition_analysis_evidence_ref",
        "nutrition_analysis_revision",
        "nutrition_analysis",
    )
    counts = {table: int(connection.scalar(sa.text(f"SELECT count(*) FROM {table}")) or 0) for table in tables}
    if any(counts.values()):
        summary = ", ".join(f"{name}={count}" for name, count in counts.items())
        raise CommandError(f"PLAN032 downgrade blocked: {summary}; preserve immutable analysis history")
    op.drop_index("ix_nutrition_analysis_command_expiry", table_name="nutrition_analysis_command_idempotency")
    op.drop_table("nutrition_analysis_command_idempotency")
    op.drop_index("ix_nutrition_analysis_event_revision_time", table_name="nutrition_analysis_revision_event")
    op.drop_table("nutrition_analysis_revision_event")
    op.drop_index("ix_nutrition_analysis_evidence_principal_date_desc", table_name="nutrition_analysis_evidence_ref")
    op.drop_table("nutrition_analysis_evidence_ref")
    op.drop_constraint("fk_nutrition_analysis_current_revision_owner", "nutrition_analysis", type_="foreignkey")
    op.drop_index("ix_nutrition_analysis_revision_history", table_name="nutrition_analysis_revision")
    op.drop_table("nutrition_analysis_revision")
    op.drop_index("ix_nutrition_analysis_principal_date_desc", table_name="nutrition_analysis")
    op.drop_table("nutrition_analysis")
