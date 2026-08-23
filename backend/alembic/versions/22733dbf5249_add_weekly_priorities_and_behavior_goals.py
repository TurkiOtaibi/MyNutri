"""add weekly priorities and behavior goals

Revision ID: 22733dbf5249
Revises: c3a7e6d5f210
Create Date: 2026-08-23
"""

import sqlalchemy as sa
from alembic import context, op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql

revision = "22733dbf5249"
down_revision = "c3a7e6d5f210"
branch_labels = None
depends_on = None


def _uuid() -> postgresql.UUID:
    return postgresql.UUID(as_uuid=True)


def _json() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "weekly_priority_recommendation",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("source_analysis_revision_id", _uuid(), nullable=False),
        sa.Column("source_analysis_id", _uuid(), nullable=False),
        sa.Column("source_analysis_revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("as_of_diary_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rules_version", sa.String(64), nullable=False),
        sa.Column("copy_version", sa.String(64), nullable=False),
        sa.Column("analysis_rules_version", sa.String(64), nullable=False),
        sa.Column("source_versions", _json(), nullable=False),
        sa.Column("result_document", _json(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("superseded_by_id", _uuid()),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_analysis_id"], ["nutrition_analysis.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_analysis_revision_id", "principal_id"], ["nutrition_analysis_revision.id", "nutrition_analysis_revision.principal_id"], name="fk_weekly_priority_analysis_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["weekly_priority_recommendation.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "principal_id", name="uq_weekly_priority_id_owner"),
        sa.UniqueConstraint("principal_id", "source_analysis_revision_id", "rules_version", name="uq_weekly_priority_source_rules"),
        sa.CheckConstraint("schema_version = 1", name="ck_weekly_priority_schema"),
        sa.CheckConstraint("status IN ('selected','none','stale','superseded','safety_suppressed')", name="ck_weekly_priority_status"),
        sa.CheckConstraint("period_end - period_start = 6", name="ck_weekly_priority_period"),
        sa.CheckConstraint("length(input_digest) = 64 AND length(content_hash) = 64", name="ck_weekly_priority_hash"),
        sa.CheckConstraint("(superseded_by_id IS NULL AND superseded_at IS NULL) OR (superseded_by_id IS NOT NULL AND superseded_at IS NOT NULL)", name="ck_weekly_priority_supersession"),
    )
    op.create_index("uq_weekly_priority_one_selected", "weekly_priority_recommendation", ["principal_id"], unique=True, postgresql_where=sa.text("superseded_at IS NULL AND status='selected'"))
    op.create_index("ix_weekly_priority_current", "weekly_priority_recommendation", ["principal_id", sa.text("period_end DESC"), sa.text("created_at DESC"), sa.text("id DESC")])

    op.create_table(
        "weekly_priority_evidence_ref",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recommendation_id", _uuid(), nullable=False),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("metric_key", sa.String(96), nullable=False),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column("opaque_source_id", _uuid(), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(24, 6)),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("coverage_percent", sa.Numeric(6, 3)),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recommendation_id", "principal_id"], ["weekly_priority_recommendation.id", "weekly_priority_recommendation.principal_id"], name="fk_weekly_priority_evidence_owner", ondelete="RESTRICT"),
        sa.UniqueConstraint("recommendation_id", "metric_key", "evidence_kind", "opaque_source_id", "diary_date", name="uq_weekly_priority_evidence_identity"),
        sa.CheckConstraint("coverage_percent IS NULL OR coverage_percent BETWEEN 0 AND 100", name="ck_weekly_priority_evidence_coverage"),
        sa.CheckConstraint("evidence_kind = 'analysis_fact'", name="ck_weekly_priority_evidence_kind"),
        sa.CheckConstraint("value IS NULL OR value NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)", name="ck_weekly_priority_evidence_finite"),
    )
    op.create_index("ix_weekly_priority_evidence_principal_date", "weekly_priority_evidence_ref", ["principal_id", sa.text("diary_date DESC")])

    op.create_table(
        "behavior_goal",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("recommendation_id", _uuid(), nullable=False),
        sa.Column("root_goal_id", _uuid(), nullable=False),
        sa.Column("previous_goal_id", _uuid()),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rule_key", sa.String(64), nullable=False),
        sa.Column("action_key", sa.String(96), nullable=False),
        sa.Column("weekly_target_count", sa.SmallInteger(), nullable=False),
        sa.Column("day_mask", _json(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("rules_version", sa.String(64), nullable=False),
        sa.Column("copy_version", sa.String(64), nullable=False),
        sa.Column("progress_document", _json(), nullable=False),
        sa.Column("progress_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reminder_preference", sa.String(16), nullable=False, server_default="disabled"),
        sa.Column("external_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("private_note", sa.String(280)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("deferred_at", sa.DateTime(timezone=True)),
        sa.Column("deferred_until", sa.Date()),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("changed_at", sa.DateTime(timezone=True)),
        sa.Column("resumed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recommendation_id", "principal_id"], ["weekly_priority_recommendation.id", "weekly_priority_recommendation.principal_id"], name="fk_behavior_goal_recommendation_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["root_goal_id", "principal_id"], ["behavior_goal.id", "behavior_goal.principal_id"], name="fk_behavior_goal_root_owner", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        sa.ForeignKeyConstraint(["previous_goal_id", "principal_id"], ["behavior_goal.id", "behavior_goal.principal_id"], name="fk_behavior_goal_previous_owner", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        sa.UniqueConstraint("id", "principal_id", name="uq_behavior_goal_id_owner"),
        sa.UniqueConstraint("principal_id", "root_goal_id", "sequence_number", name="uq_behavior_goal_sequence"),
        sa.UniqueConstraint("principal_id", "previous_goal_id", name="uq_behavior_goal_successor"),
        sa.CheckConstraint("sequence_number >= 1 AND version >= 1", name="ck_behavior_goal_versions"),
        sa.CheckConstraint("weekly_target_count BETWEEN 1 AND 7", name="ck_behavior_goal_target"),
        sa.CheckConstraint("window_end - window_start = 6", name="ck_behavior_goal_window"),
        sa.CheckConstraint("state IN ('offered','deferred','active','paused','completed','incomplete','rejected','ended','archived')", name="ck_behavior_goal_state"),
        sa.CheckConstraint("private_note IS NULL OR length(private_note) <= 280", name="ck_behavior_goal_note"),
        sa.CheckConstraint("jsonb_typeof(day_mask)='array' AND jsonb_array_length(day_mask) <= 7", name="ck_behavior_goal_day_mask"),
        sa.CheckConstraint("reminder_preference IN ('enabled','disabled')", name="ck_behavior_goal_reminder_preference"),
        sa.CheckConstraint("(state <> 'deferred' OR (deferred_at IS NOT NULL AND deferred_until IS NOT NULL)) AND (state <> 'paused' OR paused_at IS NOT NULL) AND (state <> 'completed' OR completed_at IS NOT NULL) AND (state <> 'incomplete' OR reviewed_at IS NOT NULL) AND (state <> 'rejected' OR rejected_at IS NOT NULL) AND (state <> 'ended' OR ended_at IS NOT NULL)", name="ck_behavior_goal_state_timestamps"),
    )
    op.create_index("uq_behavior_goal_one_primary", "behavior_goal", ["principal_id"], unique=True, postgresql_where=sa.text("state IN ('active','paused')"))
    op.create_index("ix_behavior_goal_history", "behavior_goal", ["principal_id", sa.text("window_end DESC"), sa.text("created_at DESC"), sa.text("id DESC")])

    op.create_table(
        "behavior_goal_history",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("goal_id", _uuid(), nullable=False), sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("root_goal_id", _uuid(), nullable=False), sa.Column("previous_goal_id", _uuid()),
        sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("goal_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False), sa.Column("from_state", sa.String(24)),
        sa.Column("to_state", sa.String(24), nullable=False), sa.Column("request_digest", sa.String(64)),
        sa.Column("actor_type", sa.String(16), nullable=False), sa.Column("reason", sa.String(64)),
        sa.Column("terms_progress_snapshot", _json(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_id", sa.String(64)),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["goal_id", "principal_id"], ["behavior_goal.id", "behavior_goal.principal_id"], name="fk_behavior_goal_history_owner", ondelete="RESTRICT"),
        sa.UniqueConstraint("goal_id", "goal_version", name="uq_behavior_goal_history_version"),
        sa.CheckConstraint("actor_type IN ('owner','system')", name="ck_behavior_goal_history_actor"),
        sa.CheckConstraint("event_type IN ('offered','accept','edit','defer','reject','change','changed','pause','resume','end','completed','evidence_reopened','progress_updated','finalized_incomplete','repeated_from_previous_window')", name="ck_behavior_goal_history_event"),
        sa.CheckConstraint("reason IS NULL OR reason IN ('not_relevant','too_difficult','prefer_other','pause_tracking','other','owner_requested','evidence_superseded')", name="ck_behavior_goal_history_reason"),
    )
    op.create_index("ix_behavior_goal_history_goal_time", "behavior_goal_history", ["goal_id", sa.text("occurred_at DESC")])

    op.create_table(
        "behavior_goal_command_idempotency",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", _uuid(), nullable=False), sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("source_goal_id", _uuid(), nullable=False), sa.Column("key_digest", sa.String(64), nullable=False),
        sa.Column("command_hash", sa.String(64), nullable=False), sa.Column("captured_diary_date", sa.Date(), nullable=False),
        sa.Column("recommendation_id", _uuid()), sa.Column("allocated_goal_id", _uuid()),
        sa.Column("response_status", sa.SmallInteger(), nullable=False), sa.Column("response_headers", _json(), nullable=False),
        sa.Column("response_document", _json(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_goal_id", "principal_id"], ["behavior_goal.id", "behavior_goal.principal_id"], name="fk_behavior_goal_command_source_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["weekly_priority_recommendation.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["allocated_goal_id"], ["behavior_goal.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("principal_id", "operation", "source_goal_id", "key_digest", name="uq_behavior_goal_command_scope"),
        sa.CheckConstraint("length(key_digest) = 64 AND length(command_hash) = 64", name="ck_behavior_goal_command_hashes"),
        sa.CheckConstraint("response_status BETWEEN 200 AND 599", name="ck_behavior_goal_command_status"),
    )
    op.create_index("ix_behavior_goal_command_completed", "behavior_goal_command_idempotency", ["principal_id", sa.text("completed_at DESC")])

    op.create_table(
        "behavior_goal_reminder_delivery",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("goal_id", _uuid(), nullable=False), sa.Column("principal_id", _uuid(), nullable=False),
        sa.Column("goal_revision", sa.Integer(), nullable=False), sa.Column("reminder_type", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False), sa.Column("eligibility_diary_date", sa.Date(), nullable=False),
        sa.Column("deferred_until", sa.DateTime(timezone=True)), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("provider_receipt_digest", sa.String(64)), sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["goal_id", "principal_id"], ["behavior_goal.id", "behavior_goal.principal_id"], name="fk_behavior_goal_reminder_owner", ondelete="RESTRICT"),
        sa.UniqueConstraint("goal_id", "goal_revision", "reminder_type", name="uq_behavior_goal_reminder_cap"),
        sa.CheckConstraint("attempts IN (0,1)", name="ck_behavior_goal_reminder_attempts"),
        sa.CheckConstraint("reminder_type IN ('midweek','endweek_review')", name="ck_behavior_goal_reminder_type"),
        sa.CheckConstraint("channel IN ('in_app','external')", name="ck_behavior_goal_reminder_channel"),
        sa.CheckConstraint("status IN ('eligible','deferred','sent','failed','suppressed')", name="ck_behavior_goal_reminder_status"),
    )
    op.create_index("ix_behavior_goal_reminder_due", "behavior_goal_reminder_delivery", ["status", "deferred_until"])


def downgrade() -> None:
    if context.is_offline_mode():
        raise CommandError("PLAN033 downgrade requires an online empty-table preflight")
    connection = op.get_bind()
    tables = (
        "behavior_goal_reminder_delivery", "behavior_goal_command_idempotency",
        "behavior_goal_history", "behavior_goal", "weekly_priority_evidence_ref",
        "weekly_priority_recommendation",
    )
    counts = {table: int(connection.scalar(sa.text(f"SELECT count(*) FROM {table}")) or 0) for table in tables}
    if any(counts.values()):
        summary = ", ".join(f"{name}={count}" for name, count in counts.items())
        raise CommandError(f"PLAN033 downgrade blocked: {summary}; preserve immutable goal history")
    op.drop_index("ix_behavior_goal_reminder_due", table_name="behavior_goal_reminder_delivery")
    op.drop_table("behavior_goal_reminder_delivery")
    op.drop_index("ix_behavior_goal_command_completed", table_name="behavior_goal_command_idempotency")
    op.drop_table("behavior_goal_command_idempotency")
    op.drop_index("ix_behavior_goal_history_goal_time", table_name="behavior_goal_history")
    op.drop_table("behavior_goal_history")
    op.drop_index("ix_behavior_goal_history", table_name="behavior_goal")
    op.drop_index("uq_behavior_goal_one_primary", table_name="behavior_goal")
    op.drop_table("behavior_goal")
    op.drop_index("ix_weekly_priority_evidence_principal_date", table_name="weekly_priority_evidence_ref")
    op.drop_table("weekly_priority_evidence_ref")
    op.drop_index("ix_weekly_priority_current", table_name="weekly_priority_recommendation")
    op.drop_index("uq_weekly_priority_one_selected", table_name="weekly_priority_recommendation")
    op.drop_table("weekly_priority_recommendation")
