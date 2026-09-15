"""retire nutrition semantic versioning and legacy target compatibility

Revision ID: c8e53f0b2d47
Revises: b7d42e9a1c36
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import context, op
from alembic.util import CommandError

revision: str = "c8e53f0b2d47"
down_revision: str | None = "b7d42e9a1c36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('target_plan') IS NULL
             OR to_regclass('diary_entry') IS NULL
             OR to_regclass('profile') IS NULL
             OR to_regclass('principal') IS NULL
             OR to_regclass('idempotency_record') IS NULL
             OR to_regclass('legacy_target_transition_snapshots') IS NULL
          THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: expected schema is missing';
          END IF;

          IF EXISTS (
            SELECT required.column_name
            FROM (VALUES
              ('target_plan', 'calculation_document_schema_version'),
              ('target_plan', 'calculation_engine_version'),
              ('target_plan', 'nutrition_registry_version'),
              ('diary_entry', 'target_provenance')
            ) AS required(table_name, column_name)
            LEFT JOIN information_schema.columns actual
              ON actual.table_schema = current_schema()
             AND actual.table_name = required.table_name
             AND actual.column_name = required.column_name
            WHERE actual.column_name IS NULL
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: expected retirement column is missing';
          END IF;

          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'target_plan'::regclass
              AND conname = 'ck_target_plan_document_version'
          ) OR NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'diary_entry'::regclass
              AND conname = 'ck_diary_entry_target_provenance'
          ) OR NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'diary_entry'::regclass
              AND conname = 'ck_diary_entry_target_binding'
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: expected constraint is missing';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM target_plan
            WHERE calculation_document_schema_version IS NULL
               OR calculation_document_schema_version <= 0
               OR calculation_engine_version IS NULL
               OR btrim(calculation_engine_version) = ''
               OR nutrition_registry_version IS NULL
               OR btrim(nutrition_registry_version) = ''
               OR calculation_document IS NULL
               OR jsonb_typeof(calculation_document) <> 'object'
               OR jsonb_typeof(calculation_document->'target_result') <> 'object'
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: invalid calculation document or semantic version metadata';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM target_plan tp
            LEFT JOIN principal pr ON pr.id = tp.principal_id
            LEFT JOIN profile p
              ON p.id = tp.profile_id AND p.principal_id = tp.principal_id
            WHERE pr.id IS NULL
               OR p.id IS NULL
               OR tp.revision IS NULL
               OR tp.revision < 1
          ) OR EXISTS (
            SELECT 1
            FROM target_plan
            GROUP BY principal_id, effective_from, revision
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: invalid Target Plan ownership or revision';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM legacy_target_transition_snapshots
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: legacy transition data exists';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM diary_entry
            WHERE target_provenance = 'legacy_unversioned'
               OR target_provenance NOT IN ('versioned_plan', 'no_target_source')
               OR (target_plan_id IS NULL AND target_provenance <> 'no_target_source')
               OR (target_plan_id IS NOT NULL AND target_provenance <> 'versioned_plan')
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: Diary provenance cannot be represented by target_plan_id alone';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM diary_entry de
            LEFT JOIN target_plan tp
              ON tp.id = de.target_plan_id AND tp.principal_id = de.principal_id
            WHERE de.target_plan_id IS NOT NULL
              AND (tp.id IS NULL OR tp.effective_from > de.entry_date)
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: invalid Diary Target Plan ownership, applicability, or FK';
          END IF;

          IF EXISTS (
            WITH boundary AS (
              SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date AS today
            )
            SELECT 1
            FROM diary_entry de
            CROSS JOIN boundary
            LEFT JOIN LATERAL (
              SELECT tp.id
              FROM target_plan tp
              WHERE tp.principal_id = de.principal_id
                AND tp.effective_from <= de.entry_date
              ORDER BY tp.effective_from DESC, tp.revision DESC, tp.id DESC
              LIMIT 1
            ) canonical ON true
            WHERE de.entry_date >= boundary.today
              AND de.target_plan_id IS DISTINCT FROM canonical.id
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: editable Diary binding is not canonical';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM idempotency_record ir
            LEFT JOIN target_plan tp
              ON tp.id = ir.resource_id AND tp.principal_id = ir.principal_id
            WHERE ir.operation IN (
              'target_plan.write', 'target_plan.activate', 'target_plan.replace'
            )
              AND (
                ir.state <> 'completed'
                OR ir.resource_type IS DISTINCT FROM 'target_plan'
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
                      NOT IN ('null', 'object')
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
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: incompatible Target Plan idempotency record';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM idempotency_record
            WHERE operation IN ('target_plan.activate', 'target_plan.replace')
            GROUP BY principal_id, idempotency_key
            HAVING bool_or(operation = 'target_plan.activate')
               AND bool_or(operation = 'target_plan.replace')
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_PREFLIGHT: ambiguous legacy idempotency key';
          END IF;
        END $$
        """
    )

    op.execute(
        """
        ALTER TABLE target_plan
        ADD CONSTRAINT ck_target_plan_calculation_document_shape
        CHECK (
          jsonb_typeof(calculation_document) = 'object'
          AND jsonb_typeof(calculation_document->'target_result') = 'object'
        ) NOT VALID
        """
    )
    op.execute(
        "ALTER TABLE target_plan VALIDATE CONSTRAINT ck_target_plan_calculation_document_shape"
    )
    op.drop_constraint("ck_target_plan_document_version", "target_plan", type_="check")
    for column_name in (
        "calculation_document_schema_version",
        "calculation_engine_version",
        "nutrition_registry_version",
    ):
        # No CASCADE is intentional: an unexpected dependent object aborts the migration.
        op.drop_column("target_plan", column_name)

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

            IF NEW.target_plan_id IS DISTINCT FROM OLD.target_plan_id THEN
              validate_canonical_binding := true;
              IF OLD.entry_date < riyadh_today THEN
                RAISE EXCEPTION 'Historical Diary target binding is immutable'
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

            IF NEW.target_plan_id IS DISTINCT FROM canonical_plan_id THEN
              RAISE EXCEPTION 'Diary target binding must match the canonical Target Plan'
                USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END $$
        """
    )
    op.drop_constraint("ck_diary_entry_target_binding", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_target_provenance", "diary_entry", type_="check")
    op.drop_column("diary_entry", "target_provenance")

    op.execute(
        "DROP TRIGGER legacy_transition_immutable_trigger ON legacy_target_transition_snapshots"
    )
    # RESTRICT/no CASCADE is intentional so an unexpected live dependency fails closed.
    op.drop_table("legacy_target_transition_snapshots")
    op.execute("DROP FUNCTION reject_legacy_transition_mutation()")

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('legacy_target_transition_snapshots') IS NOT NULL THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_POSTFLIGHT: transition table remains';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND (
                (table_name = 'target_plan' AND column_name IN (
                  'calculation_document_schema_version',
                  'calculation_engine_version',
                  'nutrition_registry_version'
                ))
                OR (table_name = 'diary_entry' AND column_name = 'target_provenance')
              )
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_POSTFLIGHT: retired column remains';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM target_plan tp
            LEFT JOIN profile p
              ON p.id = tp.profile_id AND p.principal_id = tp.principal_id
            WHERE p.id IS NULL
               OR tp.revision < 1
               OR jsonb_typeof(tp.calculation_document) <> 'object'
               OR jsonb_typeof(tp.calculation_document->'target_result') <> 'object'
          ) OR EXISTS (
            SELECT 1
            FROM target_plan
            GROUP BY principal_id, effective_from, revision
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_POSTFLIGHT: invalid Target Plan';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM diary_entry de
            LEFT JOIN target_plan tp
              ON tp.id = de.target_plan_id AND tp.principal_id = de.principal_id
            WHERE de.target_plan_id IS NOT NULL
              AND (tp.id IS NULL OR tp.effective_from > de.entry_date)
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_POSTFLIGHT: invalid Diary binding';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM idempotency_record ir
            LEFT JOIN target_plan tp
              ON tp.id = ir.resource_id AND tp.principal_id = ir.principal_id
            WHERE ir.operation IN (
              'target_plan.write', 'target_plan.activate', 'target_plan.replace'
            )
              AND (ir.resource_id IS NULL OR tp.id IS NULL)
          ) THEN
            RAISE EXCEPTION 'TARGET_INTEGRITY_RETIREMENT_POSTFLIGHT: Target Plan idempotency resource is invalid';
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    message = (
        "TARGET_INTEGRITY_RETIREMENT_DOWNGRADE_BLOCKED: semantic version columns, "
        "legacy target snapshots, and Diary provenance cannot be faithfully reconstructed; "
        "restore the approved pre-cutover backup with the matching application revision"
    )
    if context.is_offline_mode():
        raise CommandError(f"{message}; offline downgrade SQL is intentionally unavailable")
    raise CommandError(message)
