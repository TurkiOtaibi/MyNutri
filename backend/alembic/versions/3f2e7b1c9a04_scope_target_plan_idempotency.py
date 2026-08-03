"""Scope Target Plan idempotency uniqueness to the operation ledger.

Revision ID: 3f2e7b1c9a04
Revises: 5294eff9a956
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
from alembic.util.exc import CommandError

revision: str = "3f2e7b1c9a04"
down_revision: str | None = "5294eff9a956"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOWNGRADE_BLOCK_MESSAGE = (
    "PLAN021_TARGET_PLAN_IDEMPOTENCY_DOWNGRADE_BLOCKED "
    "[plan021_target_plan_idempotency_downgrade_guard]: legitimate cross-operation "
    "Target Plan key reuse prevents restoring principal-wide key uniqueness"
)


def upgrade() -> None:
    op.drop_constraint(
        "uq_target_plan_principal_key",
        "target_plan",
        type_="unique",
    )


def downgrade() -> None:
    if op.get_context().as_sql:
        raise CommandError(
            f"{DOWNGRADE_BLOCK_MESSAGE}; offline downgrade SQL is intentionally unavailable"
        )

    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM target_plan
                 GROUP BY principal_id, activation_idempotency_key
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION '{DOWNGRADE_BLOCK_MESSAGE}'
                    USING
                        ERRCODE = 'unique_violation',
                        CONSTRAINT = 'plan021_target_plan_idempotency_downgrade_guard';
            END IF;
        END
        $$;
        """
    )
    op.create_unique_constraint(
        "uq_target_plan_principal_key",
        "target_plan",
        ["principal_id", "activation_idempotency_key"],
    )
