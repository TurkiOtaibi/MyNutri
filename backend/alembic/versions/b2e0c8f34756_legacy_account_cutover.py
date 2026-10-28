"""Irreversibly tombstone legacy users while preserving internal accounts and Foods.

Revision ID: b2e0c8f34756
Revises: a1d9b7f23645

Product Owner decision: 28 October 2026, issue #114.
Production execution requires the separately approved release and backup procedure.
"""

from alembic import op


revision = "b2e0c8f34756"
down_revision = "a1d9b7f23645"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
          affected bigint;
        BEGIN
          -- Freeze eligibility and credentials before checking or changing rows.
          -- Follow the application's Principal-before-private-data locking order.
          -- EXCLUSIVE also drains SELECT FOR UPDATE writers before private locks.
          -- Plain admission reads remain possible while the cutover is running.
          LOCK TABLE public.principal IN EXCLUSIVE MODE;
          IF (SELECT count(*) FROM public.principal WHERE role = 'admin') <> 1
             OR (SELECT count(*) FROM public.principal
                 WHERE role = 'admin' AND status = 'active'
                   AND password_hash IS NOT NULL) <> 1 THEN
            RAISE EXCEPTION 'LEGACY_CUTOVER_REQUIRES_SINGLE_ACTIVE_INTERNAL_ADMIN';
          END IF;

          LOCK TABLE public.auth_session, public.diary_entry, public.lab_result,
                     public.idempotency_record, public.target_plan, public.profile
            IN SHARE ROW EXCLUSIVE MODE;
          CREATE TEMP TABLE mynutri_legacy_cutover_targets ON COMMIT DROP AS
            SELECT id FROM public.principal
            WHERE role = 'user' AND password_hash IS NULL AND status <> 'deleted';

          UPDATE public.principal SET status = 'deleting'
            WHERE id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover accounts=%', affected;

          DELETE FROM public.auth_session
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover auth_session=%', affected;
          DELETE FROM public.diary_entry
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover diary_entry=%', affected;
          DELETE FROM public.lab_result
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover lab_result=%', affected;
          DELETE FROM public.idempotency_record
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover idempotency_record=%', affected;
          DELETE FROM public.target_plan
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover target_plan=%', affected;
          DELETE FROM public.profile
            WHERE principal_id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover profile=%', affected;

          UPDATE public.principal
            SET auth_user_id = NULL, retired_auth_user_id = NULL,
                email = NULL, display_name = NULL, username = NULL,
                normalized_username = NULL, password_hash = NULL,
                must_change_password = false, failed_login_count = 0,
                locked_at = NULL, last_login_at = NULL, status = 'deleted',
                deletion_started_at = coalesce(deletion_started_at, now()),
                deleted_at = now(), updated_at = now()
            WHERE id IN (SELECT id FROM mynutri_legacy_cutover_targets);
          GET DIAGNOSTICS affected = ROW_COUNT;
          RAISE NOTICE 'legacy_cutover tombstones=%', affected;
          DROP TABLE mynutri_legacy_cutover_targets;
        END $$
    """)


def downgrade() -> None:
    # Intentionally no-op: deleted personal data cannot be reconstructed.
    # Recovery requires an approved pre-cutover backup and matching application.
    pass
