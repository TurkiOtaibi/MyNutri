"""Include normalized brand in Food duplicate identity (BR-FOD-029).

Revision ID: c7f5d3b89201
Revises: b6e4c2a78190
"""

import json
import sys

from alembic import op
import sqlalchemy as sa

revision = "c7f5d3b89201"
down_revision = "b6e4c2a78190"
branch_labels = None
depends_on = None

OLD_KEY = ["normalized_name", "nutrition_basis", "default_unit_type", "unit_amount", "unit_basis"]
NEW_KEY = ["normalized_name", "normalized_brand", *OLD_KEY[1:]]


def _check_collisions(columns: list[str], code: str) -> None:
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM food GROUP BY "
        + ", ".join(columns)
        + " HAVING count(*) > 1) THEN RAISE EXCEPTION '"
        + code
        + "'; END IF; END $$"
    )


def upgrade() -> None:
    op.execute("LOCK TABLE food IN ACCESS EXCLUSIVE MODE")
    op.add_column("food", sa.Column("normalized_brand", sa.Text(), nullable=True))
    # PostgreSQL 16 lower() is not Python casefold() (e.g. sharp S). Emit a
    # character map so online and offline SQL backfill exactly the same Unicode
    # normalization as the application, without extensions or locale dependence.
    mapping = {}
    for codepoint in range(sys.maxunicode + 1):
        character = chr(codepoint)
        normalized = " " if character.isspace() else character.casefold()
        if normalized != character:
            mapping[character] = normalized
    literal = json.dumps(mapping, ensure_ascii=True).replace("'", "''")
    op.execute(sa.text(
        "UPDATE food SET normalized_brand = btrim(regexp_replace(COALESCE(("
        "SELECT string_agg(COALESCE('" + literal + "'::jsonb ->> ch, ch), '' ORDER BY ordinal) "
        "FROM regexp_split_to_table(COALESCE(food.brand, ''), '') WITH ORDINALITY AS chars(ch, ordinal)"
        "), ''), ' +', ' ', 'g'))"
    ))
    _check_collisions(NEW_KEY, "FOOD_BRAND_UPGRADE_COLLISION")
    op.alter_column("food", "normalized_brand", nullable=False)
    op.drop_constraint("uq_food_catalog_duplicate", "food", type_="unique")
    op.create_unique_constraint("uq_food_catalog_duplicate", "food", NEW_KEY)


def downgrade() -> None:
    op.execute("LOCK TABLE food IN ACCESS EXCLUSIVE MODE")
    # Never delete or rewrite Foods to force the older, narrower rule to fit.
    _check_collisions(OLD_KEY, "FOOD_BRAND_DOWNGRADE_COLLISION")
    op.drop_constraint("uq_food_catalog_duplicate", "food", type_="unique")
    op.create_unique_constraint("uq_food_catalog_duplicate", "food", OLD_KEY)
    op.drop_column("food", "normalized_brand")
