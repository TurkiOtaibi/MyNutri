"""Block lossy Food Taxonomy V2 downgrades.

Revision ID: 5294eff9a956
Revises: df46234d2a7e
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
from alembic.util.exc import CommandError

revision: str = "5294eff9a956"
down_revision: str | None = "df46234d2a7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOWNGRADE_BLOCK_MESSAGE = (
    "PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED "
    "[plan012_lossy_taxonomy_downgrade_guard]: Food Taxonomy V2 is intentionally "
    "irreversible because frozen revision 0014 cannot restore the exact prior "
    "category type and primary_category_key nullability; retain the current schema "
    "and roll forward or restore an approved pre-migration backup"
)


def upgrade() -> None:
    pass


def downgrade() -> None:
    if op.get_context().as_sql:
        raise CommandError(
            f"{DOWNGRADE_BLOCK_MESSAGE}; offline downgrade SQL is intentionally unavailable"
        )

    op.execute(
        f"""
        DO $$
        BEGIN
            RAISE EXCEPTION '{DOWNGRADE_BLOCK_MESSAGE}'
                USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'plan012_lossy_taxonomy_downgrade_guard';
        END
        $$;
        """
    )
