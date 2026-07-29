"""Block lossy Food Taxonomy V2 downgrades.

Revision ID: 5294eff9a956
Revises: df46234d2a7e
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5294eff9a956"
down_revision: str | None = "df46234d2a7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM food_taxonomy_v2_migration_audit
                WHERE legacy_primary_category_key IS NULL
            ) THEN
                RAISE EXCEPTION
                    'PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED [plan012_lossy_taxonomy_downgrade_guard]: legacy NULL-origin taxonomy cannot be restored safely through frozen revision 0014'
                    USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = 'plan012_lossy_taxonomy_downgrade_guard';
            ELSIF EXISTS (
                SELECT 1
                FROM diary_entry
                WHERE snapshot_schema_version = 3
            ) OR EXISTS (
                SELECT 1
                FROM food AS current_food
                LEFT JOIN food_taxonomy_v2_migration_audit AS audit
                  ON audit.food_id = current_food.id
                WHERE audit.food_id IS NULL
                   OR current_food.food_category_key IS DISTINCT FROM
                      CASE
                          WHEN audit.legacy_primary_category_key IN (
                              'whole_grains', 'refined_grains'
                          ) THEN 'grains_starches'
                          WHEN audit.legacy_primary_category_key IS NULL THEN 'other'
                          ELSE audit.legacy_primary_category_key
                      END
                   OR current_food.grain_type IS DISTINCT FROM
                      CASE audit.legacy_primary_category_key
                          WHEN 'whole_grains' THEN 'whole'
                          WHEN 'refined_grains' THEN 'refined'
                          ELSE NULL
                      END
                   OR current_food.baked_good_type IS DISTINCT FROM NULL
                   OR current_food.grain_starch_type IS DISTINCT FROM
                      CASE
                          WHEN audit.legacy_primary_category_key IN (
                              'whole_grains', 'refined_grains'
                          ) THEN 'other'
                          ELSE NULL
                      END
                   OR current_food.taxonomy_review_required IS DISTINCT FROM
                      (
                          audit.legacy_primary_category_key IN (
                              'whole_grains', 'refined_grains'
                          )
                          OR audit.legacy_primary_category_key IS NULL
                      )
            ) THEN
                RAISE EXCEPTION
                    'PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED [plan012_lossy_taxonomy_downgrade_guard]: current Food Taxonomy V2 state is not the untouched 0014 mapping'
                    USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = 'plan012_lossy_taxonomy_downgrade_guard';
            END IF;
        END
        $$;
        """
    )
