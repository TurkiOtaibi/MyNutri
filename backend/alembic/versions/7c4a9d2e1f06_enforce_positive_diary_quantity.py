"""Enforce positive finite Diary quantities.

Revision ID: 7c4a9d2e1f06
Revises: 3f2e7b1c9a04
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "7c4a9d2e1f06"
down_revision: str | None = "3f2e7b1c9a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_diary_entry_quantity_positive_finite"
PREFLIGHT_GUARD = "plan023_diary_quantity_positive_finite_preflight"
PREFLIGHT_PREDICATE = (
    "quantity <= 0 OR quantity::text IN ('NaN', 'Infinity', '-Infinity')"
)
CHECK_EXPRESSION = (
    "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')"
)


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
            invalid_count bigint;
            bounded_ids text;
        BEGIN
            SELECT count(*)
              INTO invalid_count
              FROM diary_entry
             WHERE {PREFLIGHT_PREDICATE};

            SELECT string_agg(id::text, ', ' ORDER BY id)
              INTO bounded_ids
              FROM (
                    SELECT id
                      FROM diary_entry
                     WHERE {PREFLIGHT_PREDICATE}
                     ORDER BY id
                     LIMIT 10
                   ) AS invalid_rows;

            IF invalid_count > 0 THEN
                RAISE EXCEPTION
                    'PLAN023_DIARY_QUANTITY_PREFLIGHT_BLOCKED [{PREFLIGHT_GUARD}]: invalid_count=%, bounded_ids=%',
                    invalid_count,
                    coalesce(bounded_ids, '')
                    USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = '{PREFLIGHT_GUARD}';
            END IF;
        END
        $$;
        """
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "diary_entry",
        CHECK_EXPRESSION,
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "diary_entry", type_="check")
