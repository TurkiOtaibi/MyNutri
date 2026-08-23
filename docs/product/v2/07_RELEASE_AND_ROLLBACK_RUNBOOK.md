# V2 Release and Rollback Runbook

## Pre-release Gates

- One Alembic head and zero model drift.
- Fresh and populated PostgreSQL rehearsals pass.
- Admin bootstrap and taxonomy tools pass dry-run.
- User A/User B/Admin isolation suite passes.
- Backend, Frontend, Playwright, accessibility, audit, and build gates pass.
- Built browser assets contain no shared token or service-role secret.

## Deployment Order

1. Configure Supabase email/password, redirect URLs, and asymmetric signing key.
2. Configure Backend Supabase URL/issuer/audience and trusted CORS origins.
3. Apply migrations and run preflight.
4. Link/bootstrap the preserved production Principal as admin.
5. Deploy Backend and verify health/auth/isolation.
6. Configure and deploy Frontend Supabase public values.
7. Verify signup, login, logout, reset, shared catalog, and admin read views.

No production command is executed as part of repository implementation.

### Diary quantity reconciliation before Plan 023

Before applying revision `7c4a9d2e1f06`, run the following read-only query in
the explicitly approved target environment. It uses the migration's exact
predicate and returns only the total count plus at most ten Diary entry IDs:

```sql
WITH invalid_rows AS (
    SELECT id
      FROM diary_entry
     WHERE quantity <= 0
        OR quantity::text IN ('NaN', 'Infinity', '-Infinity')
),
bounded_rows AS (
    SELECT id
      FROM invalid_rows
     ORDER BY id
     LIMIT 10
)
SELECT (SELECT count(*) FROM invalid_rows) AS invalid_count,
       coalesce(
           (SELECT array_agg(id ORDER BY id) FROM bounded_rows),
           ARRAY[]::uuid[]
       ) AS bounded_ids;
```

If `invalid_count` is nonzero, STOP before migration. Escalate a separately
reviewed data-remediation decision for the identified environment. Never
delete the rows automatically, take an absolute value, clamp a quantity, or
otherwise rewrite historical Diary data merely to pass the migration. The
migration repeats this predicate and fails closed before adding
`ck_diary_entry_quantity_positive_finite`.

If the preflight blocks the upgrade, revision `3f2e7b1c9a04`, the schema, and
all Diary rows remain unchanged; the new constraint is absent. Do not retry
blindly or delete, clamp, normalize, or replace a quantity (including with
`1`, `0.001`, or another placeholder). Resolve the data-governance decision
under separate explicit authorization before retrying.

### Plan 023 disposable upgrade and rollback rehearsal

Revision `3f2e7b1c9a04` is the predecessor and `7c4a9d2e1f06` is the Plan 023
head. Rehearse only in a PostgreSQL database created specifically for this
test and bound to loopback. Do not use shared staging, hosted Supabase,
Render, production credentials, or copied production secrets. The placeholder
below must resolve only to that disposable loopback database:

```powershell
Set-Location backend
$env:DATABASE_URL = "<disposable-loopback-postgresql-url>"
$env:TEST_DATABASE_URL = $env:DATABASE_URL

python -m alembic current
python -m alembic upgrade 7c4a9d2e1f06
python -m alembic current
python -m alembic heads
python -m pytest -q tests/test_principal_migrations.py -k plan023

Remove-Item Env:TEST_DATABASE_URL
Remove-Item Env:DATABASE_URL
```

After upgrade, both `alembic current` and `alembic heads` must report
`7c4a9d2e1f06`. Verify the column and named constraint without dumping Diary
content:

```sql
SELECT data_type, numeric_precision, numeric_scale, is_nullable
  FROM information_schema.columns
 WHERE table_schema = current_schema()
   AND table_name = 'diary_entry'
   AND column_name = 'quantity';

SELECT count(*)
  FROM pg_constraint
 WHERE conrelid = 'diary_entry'::regclass
   AND conname = 'ck_diary_entry_quantity_positive_finite';
```

The column must remain `numeric(8,3)` with unchanged nullability, and the
constraint count must be exactly one. The approved Plan 023 PostgreSQL test
performs direct writes and exact `quantity::text` reads: `0.001`, `1.250`, and
`50.000` must persist with scale 3. Zero, a negative finite value, `NaN`,
`Infinity`, and `-Infinity` must not persist. Record only SQLSTATE, the named
constraint when PostgreSQL supplies it, and whether rejection occurred at the
check or numeric typmod/cast boundary. Never record a database URL,
credentials, or Diary content. After each expected error, roll back and use a
clean transaction; the test must then prove a valid write still succeeds.

Downgrade is a separate, explicitly authorized release decision. Before a
disposable rehearsal downgrade, capture synthetic row signatures containing
only Diary-entry ID, quantity, and the relevant immutable synthetic
identifiers. Then run:

```powershell
python -m alembic downgrade 3f2e7b1c9a04
python -m alembic current
```

Revision `3f2e7b1c9a04` must be current. Only
`ck_diary_entry_quantity_positive_finite` is removed: the quantity column
remains non-null `numeric(8,3)`, every signature remains value-identical, no
Diary row is inserted, updated, deleted, clamped, or normalized, no Snapshot
is recalculated, and no other constraint is removed. **Plan 023 downgrade
removes only the new named constraint. It does not rewrite Diary quantities.**

Re-upgrade the same disposable database and rerun current-head verification:

```powershell
python -m alembic upgrade 7c4a9d2e1f06
python -m alembic current
python -m alembic heads
python -m pytest -q tests/test_principal_migrations.py -k plan023
```

The revision must return to `7c4a9d2e1f06`, the named constraint must exist
exactly once, valid signatures must remain unchanged, exact positive-value
checks must pass, and invalid writes must remain blocked. The downgraded
schema intentionally does not match current model metadata; perform
application/model verification only after re-upgrading to the current head.
Neither this rehearsal nor Plan 023 performs a deployment. Any production
rollback requires normal release approval, compatibility assessment, and
separate deployment coordination; rollback does not remediate invalid legacy
data.

## Render and Supabase Configuration

Backend values:

```text
DATABASE_URL=<Supabase PostgreSQL pooler connection URL used by this project>
ENVIRONMENT=production
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWKS_TIMEOUT_SECONDS=5
SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS=600
SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS=30
SUPABASE_JWKS_NEGATIVE_CACHE_TTL_SECONDS=30
SUPABASE_JWKS_NEGATIVE_CACHE_MAX_ENTRIES=256
SUPABASE_JWKS_MAX_KEYS=32
SUPABASE_JWT_KID_MAX_LENGTH=256
ALLOWED_ORIGINS=["https://<frontend-host>"]
CALENDAR_TIMEZONE=Asia/Riyadh
SNAPSHOT_V3_WRITER_ENABLED=true
```

Frontend values:

```text
NEXT_PUBLIC_API_URL=https://<backend-host>
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<public-publishable-key>
```

Do not configure `NEXT_PUBLIC_API_TOKEN` or expose
`SUPABASE_SERVICE_ROLE_KEY` to the Frontend. In Supabase Auth, configure the
production Site URL and the exact login/reset redirect URLs before deploying.

The JWKS limits above bound refresh work per Backend process, not across the
whole cluster. `SUPABASE_JWKS_TIMEOUT_SECONDS` bounds both provider calls and
singleflight waits. `SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS` controls the
successful snapshot lifetime, while
`SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS` limits refresh attempts after misses
and failures. `SUPABASE_JWKS_NEGATIVE_CACHE_TTL_SECONDS` suppresses repeated
lookups for an absent `kid` while still allowing rotation recovery after a
bounded interval. `SUPABASE_JWKS_NEGATIVE_CACHE_MAX_ENTRIES` caps that
per-process cache at 256 entries by default. `SUPABASE_JWKS_MAX_KEYS` and
`SUPABASE_JWT_KID_MAX_LENGTH` bound
provider documents and token key IDs. The defaults are 5, 600, 30, 32, and 256
respectively for timeout, snapshot lifetime, refresh cooldown, JWKS keys, and
key-ID length. The negative-cache defaults are 30 seconds and 256 entries.
A newly published provider key can be rejected until both its negative entry
and refresh cooldown permit another lookup, at most 30 seconds with the default
policy.

Before rollout, inspect the real non-production provider JWKS and confirm its
key count and key-ID lengths fit these bounds. Do not record private tokens or
authorization headers while performing that check.

## Smoke Test Order

1. Confirm Backend health and schema preflight.
2. Sign in as the linked admin and verify `/account/me` returns `admin`.
3. Register two ordinary accounts and verify each returns role `user`.
4. Verify ordinary users share the active catalog but receive `403` on Food mutation.
5. Verify cross-user Profile, Diary, and Target Plan identifiers do not disclose data.
6. Verify admin users/details are read-only and Food archive/restore works.
7. Log a Food and confirm the historical Snapshot remains stable after catalog edit.

## Rollback

Roll the application back only to a release that understands V2 schema and
shared Foods after V2 writes begin. Do not restore owner-scoped Food visibility,
re-enable a browser shared token, or downgrade schema if doing so loses V2 data.
For a frontend-only fault, keep Backend/schema and roll back to a V2-compatible
frontend. For auth-provider outage, fail closed and restore service rather than
bypass authentication.

The Food Taxonomy V2 boundary at `5294eff9a956` is intentionally irreversible.
There is no clean-data exception. Frozen revision `0014` recreates the legacy
`category` column as `TEXT` instead of its original `VARCHAR` and does not
restore nullable semantics for `primary_category_key`. It therefore cannot
restore the exact prior schema even when the database has no Food rows or every
Food still matches the untouched migration ledger. Legacy NULL-origin rows also
cannot be restored without violating the frozen non-null operation order.

Any runtime downgrade through `5294eff9a956` fails before frozen revision
`0014` executes. The database remains at `5294eff9a956`, and its schema and data
remain unchanged. Confirm that invariant through the approved workflow:

```text
alembic current
alembic downgrade 0013_v2_shared_food_catalog  # expected to fail closed
alembic current
```

`PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED` with constraint
`plan012_lossy_taxonomy_downgrade_guard` means the transaction remained at the
current head because exact schema restoration is impossible through frozen
revision `0014`. Offline downgrade SQL generation is also intentionally
rejected before destructive statements are emitted; generated downgrade output
must never be executed.

Supported recovery is to keep the current schema and roll forward with a
verified V2-compatible release, or restore an approved pre-migration backup
under normal backup-restoration governance and post-restore verification.
Never edit frozen revision `0014`, bypass or drop the guard, relax nullability,
coerce taxonomy values, execute generated destructive downgrade SQL, apply
direct compensating DDL, use `alembic stamp`, or mutate the Alembic ledger.

Rolling back the JWKS policy removes the application-owned snapshot,
singleflight, cooldown, and input limits and restores the prior PyJWT client
behavior. Retain fail-closed authentication during rollback; do not accept
expired cached keys.

## PLAN 033 weekly priorities and behavior goals

PLAN 033 is shipped with four independent, fail-safe Backend switches. Keep
`WEEKLY_PRIORITIES_SHADOW_V1`, `WEEKLY_PRIORITIES_DISPLAY_ENABLED`,
`BEHAVIOR_GOAL_OFFERS_ENABLED`, and
`BEHAVIOR_GOAL_REMINDER_DELIVERY_ENABLED` disabled until the Project Owner
authorizes the corresponding rollout stage. Set a production-only
`WEEKLY_PRIORITY_IDEMPOTENCY_HMAC_SECRET` containing at least 32 random
characters; never expose or casually rotate it because stored command lookup
digests depend on it.

Run bounded jobs directly from the Backend working directory:

```text
python -m app.ops.weekly_priority_jobs shadow --limit 100
python -m app.ops.weekly_priority_jobs report
python -m app.ops.weekly_priority_jobs due --limit 100
```

Shadow mode requires the shadow switch on while display, offers, and reminder
delivery remain off. It persists governed recommendations but never creates a
goal or reminder. Launch review requires at least 28 consecutive shadow days
and at least 1,000 eligible evaluations, plus the frozen manual-review and
safety evidence. Provider scheduling, Render workers, activation, and traffic
percentages require separate authorization.

Apply additive revision `22733dbf5249` only after normal backup/recovery and
deployment approval. It descends from `c3a7e6d5f210`, creates six PLAN 033
entities, and performs no historical backfill. An older Backend can run against
the additive schema. Application rollback therefore disables display, offers,
and delivery and deploys compatible code while retaining immutable history.
Once any PLAN 033 row exists, the migration's populated downgrade refuses
destructive removal; schema downgrade is not the production rollback method.
Reminder eligibility is computed locally, but external provider delivery and
provider scheduling remain outside this release and need separate authority.
