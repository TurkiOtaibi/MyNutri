"""Add fail-closed Admin-managed Principal lifecycle fields.

Revision ID: b6e4c2a78190
Revises: e8b7a42f6c31
"""

from alembic import context, op
from alembic.util import CommandError
import sqlalchemy as sa

revision = "b6e4c2a78190"
down_revision = "e8b7a42f6c31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Hold this lock through the index creation so another Admin cannot appear
    # between the census and the uniqueness constraint.
    op.execute("LOCK TABLE principal IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$
        BEGIN
          IF (SELECT count(*) FROM principal WHERE role = 'admin') > 1 THEN
            RAISE EXCEPTION 'ADMIN_LIFECYCLE_MULTIPLE_ADMINS';
          END IF;
        END $$;
    """)
    op.add_column("principal", sa.Column("creation_idempotency_key", sa.String(128)))
    op.add_column("principal", sa.Column("identity_requested_at", sa.DateTime(timezone=True)))
    op.add_column("principal", sa.Column("retired_auth_user_id", sa.Uuid()))
    op.create_check_constraint(
        "ck_principal_one_auth_identity_state",
        "principal",
        "auth_user_id IS NULL OR retired_auth_user_id IS NULL",
    )
    op.add_column("principal", sa.Column("deletion_started_at", sa.DateTime(timezone=True)))
    op.add_column("principal", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("principal", sa.Column("sessions_valid_after", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_principal_status", "principal", type_="check")
    op.create_check_constraint(
        "ck_principal_status",
        "principal",
        "status IN ('provisioning', 'active', 'disabled', 'deleting', 'deleted')",
    )
    op.create_index(
        "uq_principal_single_admin",
        "principal",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'admin'"),
    )
    op.create_index(
        "uq_principal_creation_idempotency_key",
        "principal",
        ["creation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("creation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_principal_retired_auth_user_id",
        "principal",
        ["retired_auth_user_id"],
        unique=True,
        postgresql_where=sa.text("retired_auth_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_principal_any_auth_user_id",
        "principal",
        [sa.text("coalesce(auth_user_id, retired_auth_user_id)")],
        unique=True,
        postgresql_where=sa.text(
            "auth_user_id IS NOT NULL OR retired_auth_user_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    if context.is_offline_mode():
        raise CommandError("Admin lifecycle downgrade requires an online preflight")
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE principal IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM principal
            WHERE status IN ('provisioning', 'deleting', 'deleted')
               OR sessions_valid_after IS NOT NULL
        )
    """)):
        raise CommandError("ADMIN_LIFECYCLE_DOWNGRADE_BLOCKED")
    op.drop_index("uq_principal_creation_idempotency_key", table_name="principal")
    op.drop_index("uq_principal_retired_auth_user_id", table_name="principal")
    op.drop_index("uq_principal_any_auth_user_id", table_name="principal")
    op.drop_constraint("ck_principal_one_auth_identity_state", "principal", type_="check")
    op.drop_index("uq_principal_single_admin", table_name="principal")
    op.drop_constraint("ck_principal_status", "principal", type_="check")
    op.create_check_constraint(
        "ck_principal_status", "principal", "status IN ('active', 'disabled')"
    )
    op.drop_column("principal", "sessions_valid_after")
    op.drop_column("principal", "deleted_at")
    op.drop_column("principal", "deletion_started_at")
    op.drop_column("principal", "creation_idempotency_key")
    op.drop_column("principal", "identity_requested_at")
    op.drop_column("principal", "retired_auth_user_id")
