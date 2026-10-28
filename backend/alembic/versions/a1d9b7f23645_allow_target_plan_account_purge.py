"""Allow immutable Target Plan deletion only inside account deletion.

Revision ID: a1d9b7f23645
Revises: f0c8a6e12534
"""

from alembic import op


revision = "a1d9b7f23645"
down_revision = "f0c8a6e12534"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_target_plan_content()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND EXISTS (
            SELECT 1 FROM principal
            WHERE id = OLD.principal_id AND status = 'deleting'
          ) THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'Target Plan revisions are immutable' USING ERRCODE='23514';
          RETURN OLD;
        END $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_target_plan_content()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Target Plan revisions are immutable' USING ERRCODE='23514';
          RETURN OLD;
        END $$
        """
    )
