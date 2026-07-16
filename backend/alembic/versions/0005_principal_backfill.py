"""backfill explicitly provisioned Principal ownership

Revision ID: 0005_principal_backfill
Revises: 0004_principal_expand
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_principal_backfill"
down_revision: str | None = "0004_principal_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
          deployment_principal uuid;
          active_principals bigint;
          profile_before bigint;
          food_before bigint;
          diary_before bigint;
        BEGIN
          SELECT count(*) INTO profile_before FROM profile;
          SELECT count(*) INTO food_before FROM food;
          SELECT count(*) INTO diary_before FROM diary_entry;

          IF profile_before + food_before + diary_before = 0 THEN
            RETURN;
          END IF;

          SELECT count(*) INTO active_principals FROM principal WHERE status = 'active';
          IF active_principals <> 1 THEN
            RAISE EXCEPTION 'Ownership backfill requires exactly one explicitly provisioned active Principal.';
          END IF;
          SELECT id INTO deployment_principal FROM principal WHERE status = 'active';

          IF EXISTS (SELECT 1 FROM profile WHERE principal_id IS NOT NULL AND principal_id <> deployment_principal)
             OR EXISTS (SELECT 1 FROM food WHERE principal_id IS NOT NULL AND principal_id <> deployment_principal)
             OR EXISTS (SELECT 1 FROM diary_entry WHERE principal_id IS NOT NULL AND principal_id <> deployment_principal) THEN
            RAISE EXCEPTION 'Ownership backfill found conflicting owner assignments.';
          END IF;

          UPDATE profile SET principal_id = deployment_principal WHERE principal_id IS NULL;
          UPDATE food SET principal_id = deployment_principal WHERE principal_id IS NULL;
          UPDATE diary_entry SET principal_id = deployment_principal WHERE principal_id IS NULL;

          IF (SELECT count(*) FROM profile) <> profile_before
             OR (SELECT count(*) FROM food) <> food_before
             OR (SELECT count(*) FROM diary_entry) <> diary_before
             OR EXISTS (SELECT 1 FROM profile WHERE principal_id IS NULL)
             OR EXISTS (SELECT 1 FROM food WHERE principal_id IS NULL)
             OR EXISTS (SELECT 1 FROM diary_entry WHERE principal_id IS NULL) THEN
            RAISE EXCEPTION 'Ownership row-count or null-owner reconciliation failed.';
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM profile)
             OR EXISTS (SELECT 1 FROM food)
             OR EXISTS (SELECT 1 FROM diary_entry) THEN
            RAISE EXCEPTION 'Downgrading ownership backfill with data is intentionally unsupported.';
          END IF;
        END
        $$;
        """
    )
