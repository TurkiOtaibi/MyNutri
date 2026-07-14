"""add Diary meal type

Revision ID: 0003_diary_meal_type
Revises: 0002_foods_v1_per_basis
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_diary_meal_type"
down_revision: str | None = "0002_foods_v1_per_basis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

meal_type_enum = sa.Enum(
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "unspecified",
    name="meal_type_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    meal_type_enum.create(bind, checkfirst=True)
    op.add_column(
        "diary_entry",
        sa.Column(
            "meal_type",
            meal_type_enum,
            nullable=False,
            server_default="unspecified",
        ),
    )
    op.alter_column("diary_entry", "meal_type", server_default=None)


def downgrade() -> None:
    op.drop_column("diary_entry", "meal_type")
    meal_type_enum.drop(op.get_bind(), checkfirst=True)
