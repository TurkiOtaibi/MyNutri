"""replace Target Plan lifecycle state with immutable date-effective revisions

Revision ID: b7d42e9a1c36
Revises: a6c81e4f2d90
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from alembic.util import CommandError

revision: str = "b7d42e9a1c36"
down_revision: str | None = "a6c81e4f2d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM target_plan tp
            LEFT JOIN profile p
              ON p.id = tp.profile_id AND p.principal_id = tp.principal_id
            WHERE p.id IS NULL
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: invalid Profile ownership';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM diary_entry de
            LEFT JOIN target_plan tp
              ON tp.id = de.target_plan_id AND tp.principal_id = de.principal_id
            WHERE de.target_plan_id IS NOT NULL
              AND (tp.id IS NULL OR tp.effective_from > de.entry_date)
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: invalid Diary ownership, applicability, or orphan binding';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM diary_entry
            WHERE (target_provenance = 'versioned_plan' AND target_plan_id IS NULL)
               OR (target_provenance IN ('legacy_unversioned','no_target_source')
                   AND target_plan_id IS NOT NULL)
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: invalid Diary binding invariant';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM target_plan
            WHERE calculation_document IS NULL
               OR jsonb_typeof(calculation_document) <> 'object'
               OR calculation_document_schema_version IS NULL
               OR calculation_document_schema_version <= 0
               OR calculation_engine_version IS NULL
               OR nutrition_registry_version IS NULL
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: invalid calculation or version metadata';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM target_plan child
            JOIN target_plan parent ON parent.id = child.predecessor_plan_id
            WHERE parent.principal_id <> child.principal_id
               OR parent.effective_from <> child.effective_from
               OR parent.superseded_by_plan_id IS DISTINCT FROM child.id
          ) OR EXISTS (
            SELECT 1
            FROM target_plan parent
            JOIN target_plan child ON child.id = parent.superseded_by_plan_id
            WHERE parent.principal_id <> child.principal_id
               OR parent.effective_from <> child.effective_from
               OR child.predecessor_plan_id IS DISTINCT FROM parent.id
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: invalid replacement link';
          END IF;

          IF EXISTS (
            SELECT predecessor_plan_id
            FROM target_plan
            WHERE predecessor_plan_id IS NOT NULL
            GROUP BY predecessor_plan_id
            HAVING count(*) > 1
          ) OR EXISTS (
            SELECT superseded_by_plan_id
            FROM target_plan
            WHERE superseded_by_plan_id IS NOT NULL
            GROUP BY superseded_by_plan_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: branching replacement chain';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM (
              SELECT principal_id, effective_from,
                     count(*) FILTER (WHERE predecessor_plan_id IS NULL) AS roots,
                     count(*) FILTER (WHERE superseded_by_plan_id IS NULL) AS finals
              FROM target_plan
              GROUP BY principal_id, effective_from
            ) grouped
            WHERE roots <> 1 OR finals <> 1
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: ambiguous replacement chain';
          END IF;

          IF EXISTS (
            WITH RECURSIVE walk AS (
              SELECT id AS start_id, id, superseded_by_plan_id, ARRAY[id] AS path, false AS cycle
              FROM target_plan
              UNION ALL
              SELECT walk.start_id, next.id, next.superseded_by_plan_id,
                     walk.path || next.id, next.id = ANY(walk.path)
              FROM walk
              JOIN target_plan next ON next.id = walk.superseded_by_plan_id
              WHERE NOT walk.cycle
            )
            SELECT 1 FROM walk WHERE cycle
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: replacement cycle';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM idempotency_record ir
            LEFT JOIN target_plan tp
              ON tp.id = ir.resource_id AND tp.principal_id = ir.principal_id
            WHERE ir.operation IN ('target_plan.activate','target_plan.replace')
              AND (
                ir.state <> 'completed'
                OR ir.resource_id IS NULL
                OR tp.id IS NULL
                OR ir.response_document IS NULL
                OR jsonb_typeof(ir.response_document) <> 'object'
                OR jsonb_typeof(ir.response_document->'plan') <> 'object'
                OR ir.response_document->'plan'->>'id' <> tp.id::text
                OR ir.response_document->'plan'->>'effective_from' <> tp.effective_from::text
                OR (
                  ir.response_document ? 'replaced_plan'
                  AND jsonb_typeof(ir.response_document->'replaced_plan')
                      NOT IN ('null','object')
                )
                OR (
                  jsonb_typeof(ir.response_document->'replaced_plan') = 'object'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM target_plan replaced
                    WHERE replaced.id::text = ir.response_document->'replaced_plan'->>'id'
                      AND replaced.principal_id = ir.principal_id
                      AND replaced.effective_from = tp.effective_from
                  )
                )
              )
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: incompatible legacy idempotency record';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM idempotency_record
            WHERE operation IN ('target_plan.activate','target_plan.replace')
            GROUP BY principal_id, idempotency_key
            HAVING bool_or(operation='target_plan.activate')
               AND bool_or(operation='target_plan.replace')
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: ambiguous legacy idempotency key';
          END IF;
        END $$
        """
    )

    op.add_column("target_plan", sa.Column("revision", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH RECURSIVE revision_chain AS (
          SELECT id, principal_id, effective_from, 1 AS revision
          FROM target_plan
          WHERE predecessor_plan_id IS NULL
          UNION ALL
          SELECT child.id, child.principal_id, child.effective_from,
                 revision_chain.revision + 1
          FROM target_plan child
          JOIN revision_chain ON child.predecessor_plan_id = revision_chain.id
          WHERE child.principal_id = revision_chain.principal_id
            AND child.effective_from = revision_chain.effective_from
        )
        UPDATE target_plan tp
        SET revision = revision_chain.revision
        FROM revision_chain
        WHERE tp.id = revision_chain.id
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM target_plan WHERE revision IS NULL) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_BACKFILL: incomplete revision chain';
          END IF;
          IF EXISTS (
            SELECT 1 FROM target_plan
            GROUP BY principal_id, effective_from, revision
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_BACKFILL: duplicate revision';
          END IF;
        END $$
        """
    )
    op.alter_column("target_plan", "revision", nullable=False)
    op.create_check_constraint(
        "ck_target_plan_revision_positive", "target_plan", "revision >= 1"
    )
    op.create_unique_constraint(
        "uq_target_plan_principal_effective_revision",
        "target_plan",
        ["principal_id", "effective_from", "revision"],
    )
    op.execute(
        """
        CREATE INDEX ix_target_plan_principal_effective_revision
        ON target_plan (principal_id, effective_from DESC, revision DESC, id DESC)
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_diary_event_binding()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          canonical_plan_id uuid;
          riyadh_today date := (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date;
          validate_canonical_binding boolean := false;
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            IF NEW.entry_date IS DISTINCT FROM OLD.entry_date
               OR NEW.food_id IS DISTINCT FROM OLD.food_id
               OR NEW.principal_id IS DISTINCT FROM OLD.principal_id
               OR NEW.recorded_unit_type IS DISTINCT FROM OLD.recorded_unit_type
               OR NEW.recorded_unit_amount IS DISTINCT FROM OLD.recorded_unit_amount
               OR NEW.recorded_unit_basis IS DISTINCT FROM OLD.recorded_unit_basis
               OR NEW.recorded_unit_label IS DISTINCT FROM OLD.recorded_unit_label
            THEN
              RAISE EXCEPTION 'Diary event identity and measurement are immutable'
                USING ERRCODE='23514';
            END IF;

            IF NEW.target_plan_id IS DISTINCT FROM OLD.target_plan_id
               OR NEW.target_provenance IS DISTINCT FROM OLD.target_provenance
            THEN
              validate_canonical_binding := true;
              IF OLD.entry_date < riyadh_today THEN
                RAISE EXCEPTION 'Historical Diary target binding is immutable'
                  USING ERRCODE='23514';
              END IF;
              IF NEW.target_plan_id IS NULL OR NEW.target_provenance <> 'versioned_plan' THEN
                RAISE EXCEPTION 'Diary target binding must use the canonical Target Plan'
                  USING ERRCODE='23514';
              END IF;
            END IF;
          ELSE
            validate_canonical_binding := true;
          END IF;

          IF validate_canonical_binding THEN
            SELECT tp.id INTO canonical_plan_id
            FROM target_plan tp
            WHERE tp.principal_id = NEW.principal_id
              AND tp.effective_from <= NEW.entry_date
            ORDER BY tp.effective_from DESC, tp.revision DESC, tp.id DESC
            LIMIT 1;

            IF canonical_plan_id IS NOT NULL
               AND (
                 NEW.target_plan_id IS DISTINCT FROM canonical_plan_id
                 OR NEW.target_provenance <> 'versioned_plan'
               )
            THEN
              RAISE EXCEPTION 'Diary target binding must use the canonical Target Plan'
                USING ERRCODE='23514';
            END IF;

            IF canonical_plan_id IS NULL
               AND (
                 NEW.target_plan_id IS NOT NULL
                 OR NEW.target_provenance = 'versioned_plan'
               )
            THEN
              RAISE EXCEPTION 'Diary target binding has no applicable Target Plan'
                USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END $$
        """
    )
    op.execute("DROP TRIGGER diary_event_binding_immutable_trigger ON diary_entry")
    op.execute(
        """
        CREATE TRIGGER diary_event_binding_immutable_trigger
        BEFORE INSERT OR UPDATE ON diary_entry
        FOR EACH ROW EXECUTE FUNCTION protect_diary_event_binding()
        """
    )

    op.execute(
        """
        WITH boundary AS (
          SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date AS today
        ), resolved AS (
          SELECT de.id,
                 (
                   SELECT tp.id
                   FROM target_plan tp
                   WHERE tp.principal_id = de.principal_id
                     AND tp.effective_from <= de.entry_date
                   ORDER BY tp.effective_from DESC, tp.revision DESC, tp.id DESC
                   LIMIT 1
                 ) AS canonical_plan_id
          FROM diary_entry de
          CROSS JOIN boundary
          WHERE de.entry_date >= boundary.today
        )
        UPDATE diary_entry de
        SET target_plan_id = resolved.canonical_plan_id,
            target_provenance = 'versioned_plan'
        FROM resolved
        WHERE de.id = resolved.id
          AND resolved.canonical_plan_id IS NOT NULL
          AND (
            de.target_plan_id IS DISTINCT FROM resolved.canonical_plan_id
            OR de.target_provenance <> 'versioned_plan'
          )
        """
    )

    op.execute("DROP TRIGGER target_plan_immutable_content_trigger ON target_plan")
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
    op.execute(
        """
        CREATE TRIGGER target_plan_immutable_content_trigger
        BEFORE UPDATE OR DELETE ON target_plan
        FOR EACH ROW EXECUTE FUNCTION protect_target_plan_content()
        """
    )

    op.execute("ALTER TABLE target_plan DROP CONSTRAINT ex_target_plan_effective_period")
    op.drop_index("uq_target_plan_one_active", table_name="target_plan")
    op.drop_index("uq_target_plan_one_scheduled", table_name="target_plan")
    op.drop_index("ix_target_plan_principal_effective", table_name="target_plan")
    op.drop_constraint("fk_target_plan_predecessor_owner", "target_plan", type_="foreignkey")
    op.drop_constraint("fk_target_plan_superseding_owner", "target_plan", type_="foreignkey")
    op.drop_constraint("ck_target_plan_status", "target_plan", type_="check")
    op.drop_constraint("ck_target_plan_period", "target_plan", type_="check")
    op.drop_constraint("ck_target_plan_timezone", "target_plan", type_="check")
    op.drop_constraint("ck_target_plan_activation_state", "target_plan", type_="check")
    op.drop_constraint("ck_target_plan_supersession_state", "target_plan", type_="check")

    for column_name in (
        "status",
        "effective_to",
        "calendar_timezone",
        "predecessor_plan_id",
        "superseded_by_plan_id",
        "activation_idempotency_key",
        "activated_at",
        "closed_at",
        "superseded_at",
    ):
        op.drop_column("target_plan", column_name)

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            WITH extension_info AS (
              SELECT oid AS extension_oid
              FROM pg_extension
              WHERE extname='btree_gist'
            ), extension_members AS (
              SELECT d.classid, d.objid, d.objsubid
              FROM pg_depend d
              CROSS JOIN extension_info e
              WHERE d.refclassid='pg_extension'::regclass
                AND d.refobjid=e.extension_oid
                AND d.deptype='e'
            ), direct_dependents AS (
              SELECT DISTINCT d.classid, d.objid, d.objsubid
              FROM pg_depend d
              JOIN extension_members m
                ON d.refclassid=m.classid
               AND d.refobjid=m.objid
               AND d.refobjsubid=m.objsubid
              WHERE d.classid IN (
                'pg_class'::regclass,
                'pg_constraint'::regclass,
                'pg_proc'::regclass
              )
                AND NOT EXISTS (
                  SELECT 1 FROM extension_members own
                  WHERE own.classid=d.classid
                    AND own.objid=d.objid
                    AND own.objsubid=d.objsubid
                )
            )
            SELECT 1
            FROM direct_dependents d
            WHERE (
              d.classid='pg_class'::regclass
              AND EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE c.oid=d.objid
                  AND n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%'
              )
            ) OR (
              d.classid='pg_constraint'::regclass
              AND EXISTS (
                SELECT 1 FROM pg_constraint con
                JOIN pg_class c ON c.oid=con.conrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE con.oid=d.objid
                  AND n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%'
              )
            ) OR (
              d.classid='pg_proc'::regclass
              AND EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE p.oid=d.objid
                  AND n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%'
              )
            )
          ) THEN
            RAISE EXCEPTION 'TARGET_PLAN_DATE_MODEL_PREFLIGHT: btree_gist still has application dependencies';
          END IF;
        END $$
        """
    )
    op.execute("DROP EXTENSION IF EXISTS btree_gist")


def downgrade() -> None:
    message = (
        "TARGET_PLAN_DATE_MODEL_DOWNGRADE_BLOCKED: lifecycle state and mutable transition "
        "history cannot be faithfully reconstructed; restore the approved pre-cutover "
        "backup with the matching application revision"
    )
    if context.is_offline_mode():
        raise CommandError(f"{message}; offline downgrade SQL is intentionally unavailable")
    raise CommandError(message)
