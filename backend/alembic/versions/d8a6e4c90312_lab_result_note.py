"""Add private per-result batch notes.

Revision ID: d8a6e4c90312
Revises: c7f5d3b89201
"""

from alembic import op
import sqlalchemy as sa

revision = "d8a6e4c90312"
down_revision = "c7f5d3b89201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_result", sa.Column("note", sa.String(500), nullable=True))


def downgrade() -> None:
    # Fail closed rather than silently destroy private notes during rollback.
    # SQL form works identically in online and offline migration execution.
    op.execute("LOCK TABLE lab_result IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM lab_result WHERE note IS NOT NULL) THEN
                RAISE EXCEPTION 'LAB_NOTE_DOWNGRADE_BLOCKED';
            END IF;
        END $$;
    """)
    op.drop_column("lab_result", "note")
