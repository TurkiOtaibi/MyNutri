"""retire NOVA from active product contracts

Revision ID: 8a91c4e7d2f6
Revises: 22733dbf5249
Create Date: 2026-09-04
"""

from alembic import op


revision = "8a91c4e7d2f6"
down_revision = "22733dbf5249"
branch_labels = None
depends_on = None


PHASE1_SQL = r"""
CREATE SCHEMA IF NOT EXISTS nova_retirement;
REVOKE ALL ON SCHEMA nova_retirement FROM PUBLIC;
CREATE TABLE nova_retirement.contract_generation (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  generation smallint NOT NULL,
  state text NOT NULL,
  activated_at timestamptz NULL,
  CHECK ((generation = 1 AND state = 'LEGACY_COMPAT' AND activated_at IS NULL)
      OR (generation = 2 AND state = 'NOVA_RETIRED' AND activated_at IS NOT NULL))
);
REVOKE ALL ON TABLE nova_retirement.contract_generation FROM PUBLIC;
INSERT INTO nova_retirement.contract_generation(singleton, generation, state, activated_at)
VALUES (true, 1, 'LEGACY_COMPAT', NULL);

CREATE OR REPLACE FUNCTION nova_retirement.generation_lock_key()
RETURNS bigint LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path = pg_catalog AS $$
  SELECT 74219360427180316::bigint
$$;
CREATE OR REPLACE FUNCTION nova_retirement.lock_generation_shared()
RETURNS void LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  PERFORM pg_catalog.pg_advisory_xact_lock_shared(nova_retirement.generation_lock_key());
END;
$$;
CREATE OR REPLACE FUNCTION nova_retirement.guard_contract_generation()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  PERFORM pg_catalog.pg_advisory_xact_lock(nova_retirement.generation_lock_key());
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_GENERATION_DELETE_FORBIDDEN' USING ERRCODE = '23514';
  ELSIF TG_OP = 'INSERT' THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_GENERATION_SINGLETON' USING ERRCODE = '23514';
  END IF;
  IF NEW.singleton IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_GENERATION_SINGLETON' USING ERRCODE = '23514';
  END IF;
  IF OLD.state = 'NOVA_RETIRED'
     AND (NEW.state IS DISTINCT FROM 'NOVA_RETIRED' OR NEW.generation IS DISTINCT FROM 2) THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_LEGACY_RETURN_FORBIDDEN' USING ERRCODE = '23514';
  END IF;
  IF NEW.state = 'LEGACY_COMPAT'
     AND (NEW.generation <> 1 OR NEW.activated_at IS NOT NULL) THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_INVALID_GENERATION' USING ERRCODE = '23514';
  END IF;
  IF NEW.state = 'NOVA_RETIRED'
     AND (NEW.generation <> 2 OR NEW.activated_at IS NULL) THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_INVALID_GENERATION' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_generation_guard
BEFORE INSERT OR UPDATE OR DELETE ON nova_retirement.contract_generation
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_contract_generation();
CREATE OR REPLACE FUNCTION nova_retirement.current_contract_state()
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
DECLARE result text;
BEGIN
  PERFORM nova_retirement.lock_generation_shared();
  SELECT state INTO result FROM nova_retirement.contract_generation WHERE singleton = true;
  IF result IS NULL THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_GENERATION_MISSING' USING ERRCODE = '23514';
  END IF;
  RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION nova_retirement.snapshot_contains_retired_fields(value jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
  SELECT COALESCE(value ? 'nova', false)
      OR COALESCE(value->'versions' ? 'nova_rules_version', false)
$$;
CREATE OR REPLACE FUNCTION nova_retirement.canonical_snapshot_versions(value jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
  SELECT COALESCE(value = '[3]'::jsonb OR value = '[4]'::jsonb
      OR value = '[3,4]'::jsonb, false)
$$;
CREATE OR REPLACE FUNCTION nova_retirement.analysis_contains_retired_fields(
  analysis_document jsonb, source_versions jsonb
)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  IF pg_catalog.jsonb_typeof(analysis_document) IS DISTINCT FROM 'object'
     OR pg_catalog.jsonb_typeof(source_versions) IS DISTINCT FROM 'object' THEN
    RETURN true;
  END IF;
  IF analysis_document ? 'nova_rules_version'
     OR analysis_document ? 'unsupported_nova_rules'
     OR source_versions ? 'nova_rules_version'
     OR source_versions ? 'nova_rules_versions'
     OR COALESCE(analysis_document->'safety_flags' ? 'unsupported_nova_rules', false) THEN
    RETURN true;
  END IF;
  IF pg_catalog.jsonb_typeof(analysis_document->'metric_facts') IS DISTINCT FROM 'array' THEN
    RETURN true;
  END IF;
  RETURN EXISTS (
    SELECT 1 FROM pg_catalog.jsonb_array_elements(analysis_document->'metric_facts') AS fact
    WHERE fact->>'metric_key' IN (
      'nova:nova4_calorie_share_percent', 'nova:nova4_occurrence_days'
    )
  );
END;
$$;

ALTER TABLE public.food
  ALTER COLUMN nova_classification DROP DEFAULT,
  ALTER COLUMN nova_classification DROP NOT NULL,
  ALTER COLUMN nova_review_status DROP DEFAULT,
  ALTER COLUMN nova_review_status DROP NOT NULL;
ALTER TABLE public.diary_entry DROP CONSTRAINT IF EXISTS ck_diary_entry_snapshot_version;
ALTER TABLE public.diary_entry ADD CONSTRAINT ck_diary_entry_snapshot_version
  CHECK (snapshot_schema_version IS NULL OR snapshot_schema_version IN (2,3,4));
ALTER TABLE public.nutrition_analysis DROP CONSTRAINT IF EXISTS ck_nutrition_analysis_interface;
ALTER TABLE public.nutrition_analysis ADD CONSTRAINT ck_nutrition_analysis_interface
  CHECK (interface_version IN (1,2));
ALTER TABLE public.nutrition_analysis_evidence_ref
  DROP CONSTRAINT IF EXISTS ck_nutrition_analysis_evidence_snapshot_version;
ALTER TABLE public.nutrition_analysis_evidence_ref
  ADD CONSTRAINT ck_nutrition_analysis_evidence_snapshot_version
  CHECK (snapshot_schema_version IN (2,3,4));
ALTER TABLE public.behavior_goal_history DROP CONSTRAINT IF EXISTS ck_behavior_goal_history_event;
ALTER TABLE public.behavior_goal_history ADD CONSTRAINT ck_behavior_goal_history_event CHECK (
  event_type IN (
    'offered','accept','edit','defer','reject','change','changed','pause','resume','end',
    'completed','archive','evidence_reopened','progress_updated','historical_evidence_changed',
    'finalized_completed','finalized_incomplete','repeated_from_previous_window'
  )
);

CREATE OR REPLACE FUNCTION nova_retirement.guard_food_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' AND NEW.status = 'active' THEN
    IF TG_OP = 'INSERT' THEN
      IF NEW.nova_classification IS NOT NULL OR NEW.nova_review_status IS NOT NULL THEN
        RAISE EXCEPTION 'NOVA_RETIREMENT_ACTIVE_FOOD_NOVA_FORBIDDEN' USING ERRCODE = '23514';
      END IF;
    ELSIF (OLD.status IS DISTINCT FROM 'active'
      OR NEW.nova_classification IS DISTINCT FROM OLD.nova_classification
      OR NEW.nova_review_status IS DISTINCT FROM OLD.nova_review_status)
      AND (NEW.nova_classification IS NOT NULL OR NEW.nova_review_status IS NOT NULL) THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_ACTIVE_FOOD_NOVA_FORBIDDEN' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_food_guard BEFORE INSERT OR UPDATE ON public.food
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_food_row();

CREATE OR REPLACE FUNCTION nova_retirement.guard_diary_snapshot_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
DECLARE changed boolean;
BEGIN
  changed := TG_OP = 'INSERT';
  IF TG_OP = 'UPDATE' THEN
    changed := NEW.nutrition_snapshot IS DISTINCT FROM OLD.nutrition_snapshot
      OR NEW.snapshot_schema_version IS DISTINCT FROM OLD.snapshot_schema_version;
  END IF;
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' AND changed THEN
    IF NEW.snapshot_schema_version IS DISTINCT FROM 4
       OR pg_catalog.jsonb_typeof(NEW.nutrition_snapshot) IS DISTINCT FROM 'object'
       OR NEW.nutrition_snapshot->>'schema_version' IS DISTINCT FROM '4'
       OR NEW.nutrition_snapshot->'versions'->>'nutrition_registry_version' IS DISTINCT FROM '3.0.0'
       OR NEW.nutrition_snapshot->'versions'->>'snapshot_schema_version' IS DISTINCT FROM '4'
       OR nova_retirement.snapshot_contains_retired_fields(NEW.nutrition_snapshot) THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_SNAPSHOT_V4_REQUIRED' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_diary_snapshot_guard BEFORE INSERT OR UPDATE ON public.diary_entry
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_diary_snapshot_row();

CREATE OR REPLACE FUNCTION nova_retirement.guard_analysis_series_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' THEN
    IF TG_OP = 'INSERT' AND NEW.interface_version IS DISTINCT FROM 2 THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_ANALYSIS_V2_REQUIRED' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE'
       AND (OLD.interface_version IS DISTINCT FROM 2 OR NEW.interface_version IS DISTINCT FROM 2) THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_ANALYSIS_V1_FROZEN' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_analysis_series_guard
BEFORE INSERT OR UPDATE ON public.nutrition_analysis
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_analysis_series_row();

CREATE OR REPLACE FUNCTION nova_retirement.guard_analysis_revision_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
DECLARE parent_interface smallint;
BEGIN
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' THEN
    SELECT interface_version INTO parent_interface FROM public.nutrition_analysis
    WHERE id = NEW.analysis_id AND principal_id = NEW.principal_id;
    IF parent_interface IS DISTINCT FROM 2
       OR NEW.analysis_rules_version IS DISTINCT FROM 'w3-analysis-2.0.0'
       OR NEW.analysis_document->>'interface_version' IS DISTINCT FROM '2'
       OR NEW.analysis_document->>'analysis_rules_version' IS DISTINCT FROM 'w3-analysis-2.0.0'
       OR NEW.analysis_document->>'nutrition_registry_version' IS DISTINCT FROM '3.0.0'
       OR NOT nova_retirement.canonical_snapshot_versions(NEW.analysis_document->'snapshot_schema_versions')
       OR NEW.source_versions->>'analysis_rules_version' IS DISTINCT FROM 'w3-analysis-2.0.0'
       OR NEW.source_versions->'nutrition_registry_versions' IS DISTINCT FROM '["3.0.0"]'::jsonb
       OR NOT nova_retirement.canonical_snapshot_versions(NEW.source_versions->'snapshot_schema_versions')
       OR nova_retirement.analysis_contains_retired_fields(
            NEW.analysis_document, NEW.source_versions
          ) THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_ANALYSIS_V2_SHAPE_REQUIRED' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_analysis_revision_guard BEFORE INSERT ON public.nutrition_analysis_revision
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_analysis_revision_row();

CREATE OR REPLACE FUNCTION nova_retirement.guard_analysis_evidence_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
DECLARE parent_interface smallint;
DECLARE parent_rules text;
BEGIN
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' THEN
    SELECT a.interface_version, r.analysis_rules_version INTO parent_interface, parent_rules
    FROM public.nutrition_analysis_revision r
    JOIN public.nutrition_analysis a ON a.id = r.analysis_id AND a.principal_id = r.principal_id
    WHERE r.id = NEW.revision_id AND r.principal_id = NEW.principal_id;
    IF parent_interface IS DISTINCT FROM 2
       OR parent_rules IS DISTINCT FROM 'w3-analysis-2.0.0'
       OR NEW.snapshot_schema_version NOT IN (3,4)
       OR NEW.metric_key IN ('nova:nova4_calorie_share_percent','nova:nova4_occurrence_days') THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_ANALYSIS_EVIDENCE_V2_REQUIRED' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_analysis_evidence_guard
BEFORE INSERT ON public.nutrition_analysis_evidence_ref
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_analysis_evidence_row();

CREATE OR REPLACE FUNCTION nova_retirement.guard_target_plan_row()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
DECLARE changed boolean;
BEGIN
  changed := TG_OP = 'INSERT';
  IF TG_OP = 'UPDATE' THEN
    changed := NEW.nutrition_registry_version IS DISTINCT FROM OLD.nutrition_registry_version
      OR NEW.calculation_document IS DISTINCT FROM OLD.calculation_document
      OR NEW.calculation_document_schema_version IS DISTINCT FROM OLD.calculation_document_schema_version;
  END IF;
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' AND changed THEN
    IF NEW.nutrition_registry_version IS DISTINCT FROM '3.0.0'
       OR NEW.calculation_document->>'nutrition_registry_version' IS DISTINCT FROM '3.0.0' THEN
      RAISE EXCEPTION 'NOVA_RETIREMENT_TARGET_PLAN_REGISTRY_V3_REQUIRED' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_target_plan_guard BEFORE INSERT OR UPDATE ON public.target_plan
FOR EACH ROW EXECUTE FUNCTION nova_retirement.guard_target_plan_row();

CREATE OR REPLACE FUNCTION nova_retirement.reject_new_plan033_state()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  IF nova_retirement.current_contract_state() = 'NOVA_RETIRED' THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_PLAN033_INACTIVE' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER nova_retirement_weekly_priority_insert_guard
BEFORE INSERT ON public.weekly_priority_recommendation
FOR EACH ROW EXECUTE FUNCTION nova_retirement.reject_new_plan033_state();
CREATE TRIGGER nova_retirement_behavior_goal_insert_guard
BEFORE INSERT ON public.behavior_goal
FOR EACH ROW EXECUTE FUNCTION nova_retirement.reject_new_plan033_state();
CREATE TRIGGER nova_retirement_behavior_goal_reminder_insert_guard
BEFORE INSERT OR UPDATE ON public.behavior_goal_reminder_delivery
FOR EACH ROW EXECUTE FUNCTION nova_retirement.reject_new_plan033_state();

CREATE OR REPLACE FUNCTION nova_retirement.assert_phase1_downgrade_safe()
RETURNS void LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, nova_retirement AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM nova_retirement.contract_generation WHERE state = 'NOVA_RETIRED')
     OR EXISTS (SELECT 1 FROM public.diary_entry WHERE snapshot_schema_version = 4)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis WHERE interface_version = 2)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis_evidence_ref WHERE snapshot_schema_version = 4)
     OR EXISTS (SELECT 1 FROM public.target_plan WHERE nutrition_registry_version = '3.0.0')
     OR EXISTS (SELECT 1 FROM public.food WHERE nova_classification IS NULL OR nova_review_status IS NULL)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis_command_idempotency)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis_revision_event)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis_evidence_ref)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis_revision)
     OR EXISTS (SELECT 1 FROM public.nutrition_analysis)
     OR EXISTS (SELECT 1 FROM public.behavior_goal_reminder_delivery)
     OR EXISTS (SELECT 1 FROM public.behavior_goal_command_idempotency)
     OR EXISTS (SELECT 1 FROM public.behavior_goal_history)
     OR EXISTS (SELECT 1 FROM public.behavior_goal)
     OR EXISTS (SELECT 1 FROM public.weekly_priority_evidence_ref)
     OR EXISTS (SELECT 1 FROM public.weekly_priority_evaluation)
     OR EXISTS (SELECT 1 FROM public.weekly_priority_recommendation) THEN
    RAISE EXCEPTION 'NOVA_RETIREMENT_READER_FLOOR_REQUIRED' USING ERRCODE = '23514';
  END IF;
END;
$$;
"""


DOWNGRADE_SQL = r"""
SELECT nova_retirement.assert_phase1_downgrade_safe();
DROP TRIGGER nova_retirement_behavior_goal_reminder_insert_guard ON public.behavior_goal_reminder_delivery;
DROP TRIGGER nova_retirement_behavior_goal_insert_guard ON public.behavior_goal;
DROP TRIGGER nova_retirement_weekly_priority_insert_guard ON public.weekly_priority_recommendation;
DROP TRIGGER nova_retirement_target_plan_guard ON public.target_plan;
DROP TRIGGER nova_retirement_analysis_evidence_guard ON public.nutrition_analysis_evidence_ref;
DROP TRIGGER nova_retirement_analysis_revision_guard ON public.nutrition_analysis_revision;
DROP TRIGGER nova_retirement_analysis_series_guard ON public.nutrition_analysis;
DROP TRIGGER nova_retirement_diary_snapshot_guard ON public.diary_entry;
DROP TRIGGER nova_retirement_food_guard ON public.food;
ALTER TABLE public.behavior_goal_history DROP CONSTRAINT ck_behavior_goal_history_event;
ALTER TABLE public.behavior_goal_history ADD CONSTRAINT ck_behavior_goal_history_event CHECK (
  event_type IN (
    'offered','accept','edit','defer','reject','change','changed','pause','resume','end',
    'completed','evidence_reopened','progress_updated','historical_evidence_changed',
    'finalized_completed','finalized_incomplete','repeated_from_previous_window'
  )
);
ALTER TABLE public.nutrition_analysis_evidence_ref DROP CONSTRAINT ck_nutrition_analysis_evidence_snapshot_version;
ALTER TABLE public.nutrition_analysis_evidence_ref ADD CONSTRAINT ck_nutrition_analysis_evidence_snapshot_version
  CHECK (snapshot_schema_version IN (2,3));
ALTER TABLE public.nutrition_analysis DROP CONSTRAINT ck_nutrition_analysis_interface;
ALTER TABLE public.nutrition_analysis ADD CONSTRAINT ck_nutrition_analysis_interface CHECK (interface_version = 1);
ALTER TABLE public.diary_entry DROP CONSTRAINT ck_diary_entry_snapshot_version;
ALTER TABLE public.diary_entry ADD CONSTRAINT ck_diary_entry_snapshot_version
  CHECK (snapshot_schema_version IS NULL OR snapshot_schema_version IN (2,3));
ALTER TABLE public.food
  ALTER COLUMN nova_classification SET DEFAULT 'unknown',
  ALTER COLUMN nova_classification SET NOT NULL,
  ALTER COLUMN nova_review_status SET DEFAULT 'unreviewed',
  ALTER COLUMN nova_review_status SET NOT NULL;
DROP SCHEMA nova_retirement CASCADE;
"""


def upgrade() -> None:
    """Apply the frozen NOVA Retirement Design 1.8 Phase-1 contract."""
    op.execute(PHASE1_SQL)


def downgrade() -> None:
    """Refuse unsafe downgrade before restoring predecessor constraints."""
    op.execute(DOWNGRADE_SQL)
