"""add bounded Admin Diary ordering index

Revision ID: 9f2a1b6c3d05
Revises: 7c4a9d2e1f06
Create Date: 2026-08-05
"""

from alembic import op


revision = "9f2a1b6c3d05"
down_revision = "7c4a9d2e1f06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_diary_entry_principal_date_created_id_desc "
        "ON diary_entry (principal_id, entry_date DESC, created_at DESC, id DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_diary_entry_principal_date_created_id_desc", table_name="diary_entry")
