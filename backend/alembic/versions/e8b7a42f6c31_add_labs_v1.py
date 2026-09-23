"""Add private Labs facts and durable create receipts.

Revision ID: e8b7a42f6c31
Revises: d9f64a1c3e58
"""

from alembic import context, op
from alembic.util import CommandError
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e8b7a42f6c31"
down_revision = "d9f64a1c3e58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_key", sa.String(64), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("entered_value", sa.Numeric(), nullable=False),
        sa.Column("entered_unit", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["principal.id"], ondelete="RESTRICT"),
        # This unique B-tree also covers owner/test/date reads in either date order.
        sa.UniqueConstraint(
            "principal_id", "test_key", "test_date", name="uq_lab_result_principal_test_date"
        ),
        sa.CheckConstraint(
            "entered_value >= 0 AND entered_value NOT IN "
            "('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_lab_result_value_finite_nonnegative",
        ),
        sa.CheckConstraint("length(entered_value::text) <= 128", name="ck_lab_result_value_length"),
        sa.CheckConstraint("length(test_key) > 0", name="ck_lab_result_test_key_nonempty"),
        sa.CheckConstraint("length(entered_unit) > 0", name="ck_lab_result_entered_unit_nonempty"),
    )
    op.alter_column(
        "idempotency_record", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=True
    )
    op.create_check_constraint(
        "ck_idempotency_operation_expiry",
        "idempotency_record",
        "(operation = 'lab_results.create.v1' AND expires_at IS NULL) OR "
        "(operation <> 'lab_results.create.v1' AND expires_at IS NOT NULL)",
    )
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.lab_result FROM PUBLIC")
    op.execute("""
        DO $$
        DECLARE data_api_role text;
        BEGIN
          FOREACH data_api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = data_api_role) THEN
              EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.lab_result FROM %I', data_api_role);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    if context.is_offline_mode():
        raise CommandError("Labs V1 downgrade requires an online empty-table preflight")
    connection = op.get_bind()
    # Keep writers out between the census and DDL; never discard facts or receipts.
    connection.execute(
        sa.text("LOCK TABLE lab_result, idempotency_record IN ACCESS EXCLUSIVE MODE")
    )
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM lab_result) OR EXISTS "
            "(SELECT 1 FROM idempotency_record WHERE operation='lab_results.create.v1')"
        )
    ):
        raise CommandError("LABS_V1_DOWNGRADE_BLOCKED: preserve LabResult facts and Labs receipts")
    op.drop_table("lab_result")
    op.drop_constraint("ck_idempotency_operation_expiry", "idempotency_record", type_="check")
    op.alter_column(
        "idempotency_record", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False
    )
