"""unify Food catalog and cascade Diary deletion

Revision ID: d9f64a1c3e58
Revises: c8e53f0b2d47
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import context, op
from alembic.util import CommandError

revision: str = "d9f64a1c3e58"
down_revision: str | None = "c8e53f0b2d47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("LOCK TABLE food IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE diary_entry IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $$
        DECLARE
          incoming_food_fks integer;
          food_owner name;
        BEGIN
          IF to_regclass('public.food') IS NULL
             OR to_regclass('public.diary_entry') IS NULL
             OR to_regclass('public.principal') IS NULL
             OR to_regclass('public.target_plan') IS NULL
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: expected schema is missing';
          END IF;

          IF EXISTS (
            SELECT required.column_name
            FROM (VALUES ('archived_at'), ('archived_by_principal_id'))
              AS required(column_name)
            LEFT JOIN information_schema.columns actual
              ON actual.table_schema = 'public'
             AND actual.table_name = 'food'
             AND actual.column_name = required.column_name
            WHERE actual.column_name IS NULL
          ) OR NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'public.food'::regclass
              AND conname = 'ck_food_archive_state'
          ) OR NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'public.food'::regclass
              AND conname = 'fk_food_archived_by_principal'
          ) OR to_regclass('public.ix_food_catalog_primary_archived') IS NULL
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: expected archive schema is missing';
          END IF;

          IF EXISTS (
            SELECT 1 FROM food
            WHERE archived_at IS NOT NULL OR archived_by_principal_id IS NOT NULL
          ) THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: archived Food data exists';
          END IF;

          SELECT count(*) INTO incoming_food_fks
          FROM pg_constraint
          WHERE contype = 'f' AND confrelid = 'public.food'::regclass;
          IF incoming_food_fks <> 1 OR NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = 'public.diary_entry'::regclass
              AND confrelid = 'public.food'::regclass
              AND conname = 'fk_diary_entry_food'
              AND confdeltype = 'r'
          ) THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: unexpected Food foreign-key graph';
          END IF;

          IF EXISTS (
            SELECT 1 FROM diary_entry de
            LEFT JOIN food f ON f.id = de.food_id
            WHERE de.food_id IS NULL OR f.id IS NULL
          ) OR EXISTS (
            SELECT 1 FROM food f
            LEFT JOIN principal creator ON creator.id = f.created_by_principal_id
            LEFT JOIN principal updater ON updater.id = f.updated_by_principal_id
            WHERE creator.id IS NULL
               OR (f.updated_by_principal_id IS NOT NULL AND updater.id IS NULL)
          ) OR EXISTS (
            SELECT 1 FROM diary_entry de
            LEFT JOIN principal p ON p.id = de.principal_id
            LEFT JOIN target_plan tp
              ON tp.id = de.target_plan_id AND tp.principal_id = de.principal_id
            WHERE p.id IS NULL
               OR (de.target_plan_id IS NOT NULL AND tp.id IS NULL)
          ) THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: ownership or binding integrity failed';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM pg_depend d
            JOIN pg_class dependent ON dependent.oid = d.objid
            WHERE d.refobjid = 'public.food'::regclass
              AND dependent.relkind IN ('v', 'm')
          ) THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: unexpected Food view dependency';
          END IF;

          SELECT owner_role.rolname INTO food_owner
          FROM pg_class relation
          JOIN pg_roles owner_role ON owner_role.oid = relation.relowner
          WHERE relation.oid = 'public.food'::regclass;
          IF food_owner IS NULL
             OR NOT has_table_privilege(current_user, 'public.food', 'SELECT,INSERT,UPDATE,DELETE')
             OR current_user IN ('anon', 'authenticated')
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: backend Food access cannot be preserved safely';
          END IF;
        END $$
        """
    )

    op.drop_constraint("fk_diary_entry_food", "diary_entry", type_="foreignkey")
    op.create_foreign_key(
        "fk_diary_entry_food",
        "diary_entry",
        "food",
        ["food_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("ck_food_archive_state", "food", type_="check")
    op.drop_constraint("fk_food_archived_by_principal", "food", type_="foreignkey")
    op.drop_index("ix_food_catalog_primary_archived", table_name="food")
    op.create_index("ix_food_catalog_primary_category", "food", ["primary_category"])
    op.drop_column("food", "archived_by_principal_id")
    op.drop_column("food", "archived_at")

    op.execute(
        """
        DO $$
        DECLARE data_api_role text;
        BEGIN
          REVOKE ALL PRIVILEGES ON TABLE public.food FROM PUBLIC;
          FOREACH data_api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = data_api_role) THEN
              EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.food FROM %I',
                data_api_role
              );
            END IF;
          END LOOP;
        END $$
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'food'
              AND column_name IN ('archived_at', 'archived_by_principal_id')
          ) OR to_regclass('public.ix_food_catalog_primary_archived') IS NOT NULL
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_POSTFLIGHT: archive schema remains';
          END IF;

          IF to_regclass('public.ix_food_catalog_primary_category') IS NULL
             OR NOT EXISTS (
               SELECT 1 FROM pg_constraint
               WHERE conrelid = 'public.diary_entry'::regclass
                 AND confrelid = 'public.food'::regclass
                 AND conname = 'fk_diary_entry_food'
                 AND confdeltype = 'c'
             )
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_POSTFLIGHT: final index or cascade FK is invalid';
          END IF;

          IF EXISTS (
            SELECT 1 FROM diary_entry de
            LEFT JOIN food f ON f.id = de.food_id
            LEFT JOIN principal p ON p.id = de.principal_id
            LEFT JOIN target_plan tp
              ON tp.id = de.target_plan_id AND tp.principal_id = de.principal_id
            WHERE de.food_id IS NULL OR f.id IS NULL OR p.id IS NULL
               OR (de.target_plan_id IS NOT NULL AND tp.id IS NULL)
          ) OR NOT has_table_privilege(current_user, 'public.food', 'SELECT,INSERT,UPDATE,DELETE')
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_POSTFLIGHT: data integrity or backend access failed';
          END IF;

          IF EXISTS (
               SELECT 1 FROM information_schema.role_table_grants
               WHERE table_schema = 'public' AND table_name = 'food'
                 AND grantee = 'PUBLIC'
                 AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
             ) OR (
               EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
               AND has_table_privilege('anon', 'public.food', 'INSERT,UPDATE,DELETE')
             ) OR (
               EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated')
               AND has_table_privilege('authenticated', 'public.food', 'INSERT,UPDATE,DELETE')
             )
          THEN
            RAISE EXCEPTION 'FOOD_CATALOG_SIMPLIFICATION_POSTFLIGHT: public Food mutation privilege remains';
          END IF;

        END $$
        """
    )


def downgrade() -> None:
    message = (
        "FOOD_CATALOG_SIMPLIFICATION_DOWNGRADE_BLOCKED: archive state and deleted Food/Diary "
        "history cannot be faithfully reconstructed; restore the approved pre-cutover backup "
        "with the matching application revision"
    )
    if context.is_offline_mode():
        raise CommandError(f"{message}; offline downgrade SQL is intentionally unavailable")
    raise CommandError(message)
