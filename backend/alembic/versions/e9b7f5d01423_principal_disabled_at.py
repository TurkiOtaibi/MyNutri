"""Record the time of an account disable transition.

Revision ID: e9b7f5d01423
Revises: d8a6e4c90312
"""
from alembic import op
import sqlalchemy as sa

revision = "e9b7f5d01423"
down_revision = "d8a6e4c90312"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing disabled accounts intentionally retain an unknown disable date.
    op.add_column("principal", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Rollback removes only the display timestamp; account status is preserved.
    op.drop_column("principal", "disabled_at")
