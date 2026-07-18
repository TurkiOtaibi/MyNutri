"""Add Supabase identity and two-role account metadata.

Revision ID: 0012_v2_principal_auth_expand
Revises: 0011_diary_snapshot_v2_expand
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_v2_principal_auth_expand"
down_revision: str | None = "0011_diary_snapshot_v2_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "principal",
        sa.Column("auth_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("principal", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("principal", sa.Column("display_name", sa.String(length=120), nullable=True))
    op.add_column(
        "principal",
        sa.Column("role", sa.Text(), server_default="user", nullable=False),
    )
    op.create_unique_constraint(
        "uq_principal_auth_user_id", "principal", ["auth_user_id"]
    )
    op.create_check_constraint(
        "ck_principal_role", "principal", "role IN ('user','admin')"
    )
    op.create_index(
        "uq_principal_lower_email",
        "principal",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM principal WHERE auth_user_id IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Lossy V2 identity downgrade prohibited.'; END IF; END $$;"
    )
    op.drop_index("uq_principal_lower_email", table_name="principal")
    op.drop_constraint("ck_principal_role", "principal", type_="check")
    op.drop_constraint("uq_principal_auth_user_id", "principal", type_="unique")
    op.drop_column("principal", "role")
    op.drop_column("principal", "display_name")
    op.drop_column("principal", "email")
    op.drop_column("principal", "auth_user_id")

