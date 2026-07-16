"""contract durable Principal ownership

Revision ID: 0006_principal_contract
Revises: 0005_principal_backfill
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_principal_contract"
down_revision: str | None = "0005_principal_backfill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM profile WHERE principal_id IS NULL)
             OR EXISTS (SELECT 1 FROM food WHERE principal_id IS NULL)
             OR EXISTS (SELECT 1 FROM diary_entry WHERE principal_id IS NULL) THEN
            RAISE EXCEPTION 'Cannot enforce ownership while user-data rows have null owners.';
          END IF;
        END
        $$;
        """
    )

    for table in ("profile", "food", "diary_entry"):
        op.alter_column(table, "principal_id", existing_type=sa.Uuid(), nullable=False)
        op.create_index(f"ix_{table}_principal_id", table, ["principal_id"], unique=False)
    op.create_unique_constraint("uq_profile_principal_id", "profile", ["principal_id"])
    op.create_foreign_key(
        "fk_diary_entry_food_owner",
        "diary_entry",
        "food",
        ["food_id", "principal_id"],
        ["id", "principal_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_diary_entry_food_owner", "diary_entry", type_="foreignkey")
    op.drop_constraint("uq_profile_principal_id", "profile", type_="unique")
    for table in ("diary_entry", "food", "profile"):
        op.drop_index(f"ix_{table}_principal_id", table_name=table)
        op.alter_column(table, "principal_id", existing_type=sa.Uuid(), nullable=True)
