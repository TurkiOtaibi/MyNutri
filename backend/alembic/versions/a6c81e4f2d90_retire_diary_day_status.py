"""retire diary day logging status

Revision ID: a6c81e4f2d90
Revises: f47a2c9d6e13
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import context, op
from alembic.util import CommandError

revision: str = "a6c81e4f2d90"
down_revision: str | None = "f47a2c9d6e13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM idempotency_record
        WHERE operation IN ('diary_day_complete', 'diary_day_reopen')
          AND resource_type = 'diary_day_status'
        """
    )
    op.drop_table("diary_day_status_history")
    op.drop_table("diary_day_status")


def downgrade() -> None:
    message = (
        "DIARY_DAY_STATUS_RETIREMENT_DOWNGRADE_BLOCKED: deleted status, history, and "
        "command-idempotency data cannot be faithfully reconstructed; roll forward or "
        "restore an approved backup with the matching application revision"
    )
    if context.is_offline_mode():
        raise CommandError(f"{message}; offline downgrade SQL is intentionally unavailable")
    raise CommandError(message)
