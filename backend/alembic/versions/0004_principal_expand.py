"""expand durable Principal ownership

Revision ID: 0004_principal_expand
Revises: 0003_diary_meal_type
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_principal_expand"
down_revision: str | None = "0003_diary_meal_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "principal",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_principal_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    for table in ("profile", "food", "diary_entry"):
        op.add_column(table, sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_principal_id_principal",
            table,
            "principal",
            ["principal_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_unique_constraint(
            f"uq_{table}_id_principal_id",
            table,
            ["id", "principal_id"],
        )


def downgrade() -> None:
    for table in ("diary_entry", "food", "profile"):
        op.drop_constraint(f"uq_{table}_id_principal_id", table, type_="unique")
        op.drop_constraint(f"fk_{table}_principal_id_principal", table, type_="foreignkey")
        op.drop_column(table, "principal_id")
    op.drop_table("principal")
