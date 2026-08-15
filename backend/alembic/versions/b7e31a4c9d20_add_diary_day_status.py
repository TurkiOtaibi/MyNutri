"""add owner-bound Diary day logging status and immutable history

Revision ID: b7e31a4c9d20
Revises: 9f2a1b6c3d05
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import context, op
from alembic.util import CommandError
from sqlalchemy.dialects import postgresql

revision = "b7e31a4c9d20"
down_revision = "9f2a1b6c3d05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE invalid_future bigint; orphaned bigint;
        BEGIN
          SELECT count(*) INTO invalid_future FROM diary_entry
           WHERE entry_date > (now() AT TIME ZONE 'Asia/Riyadh')::date;
          SELECT count(*) INTO orphaned FROM diary_entry d
           LEFT JOIN principal p ON p.id=d.principal_id WHERE p.id IS NULL;
          IF invalid_future > 0 OR orphaned > 0 THEN
            RAISE EXCEPTION 'PLAN031_PREFLIGHT_BLOCKED future=%, orphaned=%',
              invalid_future, orphaned USING ERRCODE='check_violation';
          END IF;
        END $$;
        """
    )
    op.create_table(
        "diary_day_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("reopened_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "principal_id", name="uq_diary_day_status_id_principal"),
        sa.UniqueConstraint("principal_id", "diary_date", name="uq_diary_day_status_principal_date"),
        sa.CheckConstraint("status IN ('partial','complete')", name="ck_diary_day_status_value"),
        sa.CheckConstraint("version >= 1", name="ck_diary_day_status_version"),
        sa.CheckConstraint("entry_count >= 0", name="ck_diary_day_status_entry_count"),
        sa.CheckConstraint(
            "(status='complete' AND completed_at IS NOT NULL) OR "
            "(status='partial' AND completed_at IS NULL)",
            name="ck_diary_day_status_completion",
        ),
    )
    op.create_index(
        "ix_diary_day_status_principal_date_desc",
        "diary_day_status",
        ["principal_id", sa.text("diary_date DESC")],
    )
    op.create_table(
        "diary_day_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("day_status_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("from_status", sa.Text()),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("day_version", sa.BigInteger(), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_id", sa.Text()),
        sa.ForeignKeyConstraint(
            ["day_status_id", "principal_id"],
            ["diary_day_status.id", "diary_day_status.principal_id"],
            name="fk_diary_day_status_history_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_principal_id"], ["principal.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("day_status_id", "day_version", name="uq_diary_day_status_history_version"),
        sa.CheckConstraint("from_status IS NULL OR from_status IN ('partial','complete')", name="ck_diary_day_status_history_from"),
        sa.CheckConstraint("to_status IN ('partial','complete')", name="ck_diary_day_status_history_to"),
        sa.CheckConstraint("event_type IN ('entry_created','entry_edited','entry_deleted','completed','reopened')", name="ck_diary_day_status_history_event"),
        sa.CheckConstraint("day_version >= 1", name="ck_diary_day_status_history_version"),
        sa.CheckConstraint("actor_principal_id = principal_id", name="ck_diary_day_status_history_actor"),
    )
    op.create_index(
        "ix_diary_day_status_history_principal_date_version",
        "diary_day_status_history",
        ["principal_id", "diary_date", "day_version"],
    )
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM diary_day_status)
             OR EXISTS (SELECT 1 FROM diary_day_status_history) THEN
            RAISE EXCEPTION 'PLAN031_BACKFILL_MUST_REMAIN_EMPTY';
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    if context.is_offline_mode():
        raise CommandError("PLAN031 downgrade requires an online empty-table preflight")
    connection = op.get_bind()
    status_count = connection.scalar(sa.text("SELECT count(*) FROM diary_day_status"))
    history_count = connection.scalar(sa.text("SELECT count(*) FROM diary_day_status_history"))
    if status_count or history_count:
        raise CommandError(
            "PLAN031 downgrade blocked: "
            f"status_count={status_count}, history_count={history_count}; "
            "restore the compatible application"
        )
    op.drop_index(
        "ix_diary_day_status_history_principal_date_version",
        table_name="diary_day_status_history",
    )
    op.drop_table("diary_day_status_history")
    op.drop_index("ix_diary_day_status_principal_date_desc", table_name="diary_day_status")
    op.drop_table("diary_day_status")
