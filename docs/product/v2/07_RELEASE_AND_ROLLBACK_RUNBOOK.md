# V2 Release and Rollback Runbook

## CURRENT internal-auth gates versus APPROVED TARGET release

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility, not an authentication path; #114 clears them only on selected legacy-user tombstones. New users are created atomically by immutable username. The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043). Internal-auth acceptance replaces the retired provider gate with real session-revocation and Principal-isolation proof; the removed recovery UI has no recovery gate (BR-AUT-012). No deployment is implied.

The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. (17/27 October 2026 AUT/USM/FOD decisions; BR-USM-027/043, BR-FOD-021; #110.)


Status: Operational authority. This document does not authorize a deployment or
production mutation.

## Admin-managed account lifecycle release gates

Before release, verify exactly one Admin, the partial unique Admin-role index,
private ownership integrity and unchanged Food attribution to Principals. Verify
that the intended Admin already has internal credentials, or separately authorize
the existing attach command before removing legacy admission. Legacy-only accounts
cannot log in. #114 executes only the selective purge described below when its
release is explicitly authorized.

In an explicitly disposable loopback environment, exercise atomic/idempotent user
creation, session expiry, password-change revocation of other sessions, Admin reset
revocation of all sessions, disable/delete invalidation, and Principal isolation.
Prove failed local deletion remains locked out and retryable, locked purge removes
all private dependents, and scrubbed tombstones preserve Food attribution IDs.
No external Auth creation/deletion/absence-check/reconciliation step remains.

After a separately authorized deployment of the approved #113 revision, obsolete
Render Auth variables may be removed with separate authorization for that exact
configuration change: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`SUPABASE_ADMIN_HTTP_TIMEOUT_SECONDS`, `SUPABASE_JWT_AUDIENCE`,
`SUPABASE_JWKS_URL`, `SUPABASE_JWKS_TIMEOUT_SECONDS`, `SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS`,
`SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS`, `SUPABASE_JWKS_NEGATIVE_CACHE_TTL_SECONDS`,
`SUPABASE_JWKS_NEGATIVE_CACHE_MAX_ENTRIES`, `SUPABASE_JWKS_MAX_KEYS`,
`SUPABASE_JWT_KID_MAX_LENGTH`, `NEXT_PUBLIC_SUPABASE_URL`, and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. These names are removal notes only;
no values belong in documentation or logs. Supabase PostgreSQL hosting and the
existing `DATABASE_URL` and database configuration stay unchanged. This repository
change performs no deployment, environment edit, restart or production mutation.

Rollback after private-data deletion requires a separately authorized matching
backup/application recovery or an approved roll-forward; code cannot restore data.
Use the exact approved Arabic account-management copy in the BA field dictionary.

## Release identity

The current repository migration head is `b2e0c8f34756`, parent `a1d9b7f23645`.
The 28 October 2026 decision selects only non-deleted normal users without an
internal password hash. V2 06 defines exact purge, preservation and guard rules.
No production deployment or migration has been performed by this change.

## #114 backup-first release and recovery

1. Before authorizing merge, identify the exact revision and environment, take a
   pre-cutover database backup, and verify restoration into an explicitly
   disposable isolated database. Record backup identity and restore evidence
   without credentials or private data. A backup without verified recovery is
   insufficient.
2. Confirm the single active Admin has internal credentials and login readiness.
   Preserve that Admin and every internal account with all their data. If needed,
   separately authorize attach/reset before release using the commands below;
   do not delete or recreate the existing Admin. Login itself changes session
   state, so any production login check needs explicit authorization.
3. Review aggregate eligibility/private-table counts and Food counts/attribution
   integrity, confirm complete required CI, and approve the exact merge/release
   only after backup and Admin readiness. A merge to the configured Render branch
   triggers deployment; startup runs `alembic upgrade head`, executing the purge.
   Merge is therefore the execution boundary, not a harmless preparation step.
4. After authorized execution, verify the actual Render running revision and
   Alembic head, aggregate notices, zero remaining eligible users, unchanged
   Admin/internal-account data and unchanged Foods/attribution. Use safe
   non-mutating checks; do not log identities, hashes, tokens or connection URLs.
5. On failure, stop and inspect the rollback outcome. Do not bypass the Admin
   guard. Repeating the SQL after success selects zero with a valid Admin.
   `downgrade` is a no-op and restores no data; recovery requires the verified
   pre-cutover database backup plus compatible application, or an approved
   corrective release, each separately authorized.

Optional manual removal of obsolete Supabase Auth users in the Dashboard may
occur after release only with separate authorization. It is not a migration step
or application dependency. Keep Supabase PostgreSQL and database configuration.
These instructions imply no further authorization for merge, deployment, restart,
configuration changes, production migration or production data mutation.

## Fresh disposable database bootstrap and Admin password recovery

An empty database deliberately fails the head guard. From `backend`, with the
exact target confirmed as disposable loopback PostgreSQL and its `DATABASE_URL`
kept local, use the existing command in this order (documentation only; not
executed by this change):

```console
python -m alembic upgrade a1d9b7f23645
python -m app.ops.internal_admin create --username <admin_username>
python -m alembic upgrade head
```

If the parent database already has an active legacy Admin, replace `create` with
`python -m app.ops.internal_admin attach --username <admin_username>`; this attaches
to the same Principal and preserves its data. If internal credentials already
exist, use neither create nor attach. Never create a replacement Admin to bypass
the guard. Production bootstrap/attach requires separate exact authorization.

For a forgotten Admin password, use the existing command:

```console
python -m app.ops.internal_admin reset --username <admin_username>
```

Enter the password at the hidden prompt. Automation may append `--password-stdin`
and supply it through protected stdin; never put a password in command arguments,
examples, logs or shell history. Reset requires the active Admin's matching
username, clears its lock and revokes sessions. Authorize production reset
separately; this runbook does not execute it.

## Required pre-release validation

- Backend Ruff/static checks and the complete pytest suite pass.
- A disposable PostgreSQL database upgrades to the parent, bootstraps the internal
  Admin as above, then upgrades to head; a direct empty-database upgrade fails
  the guard and rolls back as designed.
- `alembic heads`, `alembic check`, and offline upgrade SQL pass.
- Migration preflights reject orphan Diary rows, ambiguous measurements, and
  populated retired-feature tables without partial schema changes.
- Frontend TypeScript, ESLint, Vitest/architecture tests, production build, and
  the applicable Playwright projects pass.
- OpenAPI and generated TypeScript reproduce deterministically with no drift.
- Current Food correction tests prove historical Diary nutrition recalculates.
- Diary quantity, recorded measurement, Food cascade deletion, hard-delete
  restriction, and mass/volume dimension safety tests pass.
- Target Plan date resolution selects the greatest applicable effective date and
  highest revision without a read-triggered write.
- Target Plan same-date writes insert immutable revisions, reject backdated
  dates, preserve legacy replay, and atomically rebind only today/future Diary
  rows in the affected interval.
- Nutrition Registry payloads are structurally validated; rules-manifest drift
  changes preview hashes even when calculated numbers do not change.
- New calculation documents and public contracts contain no semantic nutrition
  versions, while historical calculation JSON remains readable and unchanged.
- No-plan dates return null plan/targets, Diary null bindings remain valid, and
  transition snapshots/Profile target fallback/target provenance are absent.
- New Diary entries allow past dates without limit and future dates through
  Asia/Riyadh today + 7 days, per BR-DRY-028 and the Product Owner decision of
  17 October 2026, reconfirmed on 25 October 2026. Existing entries retain their
  update/delete rules. Diary writes require no `If-Match` and do not read or
  write Day Logging Status state or history.
- Earlier retired-feature cleanup preserves Target Plan and unrelated idempotency
  rows; #114 deliberately purges all six private tables for selected users only.
- Retired endpoints, navigation, schema fields, tables, flags, and generated
  contracts are absent.
- Historical Alembic revision hashes remain unchanged.
- `git diff --check` and exact-path scope verification pass.
- Labs catalog integrity/package resource, migration/model/privilege/preflight and
  offline SQL gates pass. Sex/DOB guards, exact arithmetic/current-rule history,
  atomic/idempotent owner CRUD, admin read-only/404 privacy and nutrition independence
  pass, together with generated-contract drift and complete UI/session/PWA gates.
- Preserve locked dependency reproduction and both backend/frontend audits; execute
  every backend partition, all four functional shards and aggregate collectors,
  Linux visual, PWA, development StrictMode, real internal-auth browser and backend acceptance against disposable loopback PostgreSQL, including Principal isolation, session revocation, expiry and complete cleanup. The seven obsolete browser recovery cases remain removed with that UI (BR-AUT-012).
  An unavailable or failing gate remains a blocker, not inferred success.

## Production preflight

Production access and mutation require separate explicit authorization. When it
is granted, perform read-only counts first for:

- populated retired analysis/group/trait/priority tables;
- Diary rows with null or missing Food references;
- Diary rows whose recorded measurement cannot be derived;
- Diary rows whose derived recorded mass/volume basis conflicts with the current
  referenced Food nutrition basis;
- Food rows whose legacy taxonomy/source cannot follow the approved fallback.
- Day Logging Status and history row counts, and status-command idempotency row
  counts, as destructive-cutover evidence rather than blockers.
- Target Plans by lifecycle status; duplicate Principal/effective-date groups;
  replacement-chain integrity; Diary binding invariants; legacy transition
  snapshots; legacy Target Plan idempotency response shapes; and `btree_gist`
  application dependencies.
- Target Plan semantic-version column validity and document shape; transition
  snapshot count; legacy Diary provenance count; deterministic target-plan-only
  bindings; and legacy Target Plan idempotency resource integrity for the
  combined retirement.

Any non-zero blocking count stops the rollout. Do not delete, rewrite, or infer
production data during preflight.
For the Labs revision, after exact production access authorization, inspect the
running revision/head and presence of facts and create receipts before deciding
rollback eligibility. Their presence forbids downgrade, not forward deployment.
Never print connection secrets or delete facts/receipts to permit a downgrade.

## Deployment order

Only after a separately approved release window:

1. Verify backups and restore procedure.
2. Stop all incompatible Day Logging Status and Diary writers; there is no
   compatibility window.
3. Stop Target Plan lifecycle writers and other incompatible application
   instances; the Target Plan schema cutover also has no compatibility window.
4. Stop application instances that write semantic Target Plan versions,
   transition snapshots, or Diary provenance; the combined cutover has no
   compatibility window.
5. Apply the reviewed migration to the explicitly identified environment.
6. Deploy backend and frontend artifacts built from the same approved revision.
7. Verify health, authentication, Food reads, Diary reads, and Target Plan history.
8. Confirm the Food archive schema is absent and the Diary Food FK is `ON DELETE CASCADE`.
9. Confirm generated-contract and migration-head identities from runtime evidence.

For Labs, separately authorize the exact revision and each production migration
and deployment action: schema `e8b7a42f6c31` precedes its compatible backend,
generated contract and frontend artifacts. A local commit, CI result or migration
file does not prove any production action or running revision.

## Smoke checks

The following mutation checks run in an explicitly disposable release environment.
Production checks remain safe and non-mutating unless the exact broader action
is separately authorized. Production-safe Labs checks inspect running revision,
authenticated catalog/reads, `no-store` and admin read-only presentation. Disposable
Labs checks cover owner create/edit/delete, retained receipt replay, DOB/sex guards,
and unchanged Profile/TargetPlan/Diary/Food facts across Labs CRUD.

- Create and edit a Food with a valid two-level taxonomy.
- Confirm only `official` and `estimated` are accepted for nutrition provenance.
- Record a Diary amount, edit current Food nutrition, and verify the old date
  recalculates while its consumed amount remains unchanged.
- In a disposable environment, delete a referenced Food and verify all of its
  cross-Principal Diary entries are deleted while unrelated Diary entries and
  Target Plans remain.
- Verify an incompatible mass/volume basis edit is rejected for a referenced Food.
- Verify historical/current/future Target Plan reads select the canonical plan by
  date and revision without writing lifecycle state.
- Write plans for today and two distinct future dates; revise one future date and
  verify history retains both revisions.
- Verify a future Diary row follows the revised canonical plan while a past Diary
  binding remains unchanged.
- Confirm the final Target Plan API contains only POST/list/current and exposes no
  lifecycle status, pending plan, or lifecycle timestamps.
- Confirm Registry responses pass structural validation and manifest/ETag
  integrity without numeric schema/version fields.
- Confirm a date before the first applicable plan returns null plan/targets and a
  Diary entry for that date stores a null target-plan binding.
- Create a Diary entry through Asia/Riyadh today + 7 days and reject a new entry
  at today + 8 days. Verify unrestricted past creation and unchanged update/delete
  of existing entries, including later future dates, without `If-Match`.
- Confirm all four retired status routes return `404` and week summaries contain
  no status, version, completion timestamp, or entry-count presence field.

## Rollback

Labs revision `e8b7a42f6c31` refuses downgrade if any LabResult or
`lab_results.create.v1` receipt exists. Only an online empty-Labs preflight permits
removing its table/check and restoring receipt expiry to NOT NULL. Never delete
facts or receipts to make rollback pass; production rollback remains separately
authorized and subject to the matching backup/application restore policy.

Do not downgrade below `d9f64a1c3e58`. Food archive state cannot be reconstructed,
and permanent Food deletion may have cascaded Diary history. Earlier semantic-version,
provenance, transition, Target Plan lifecycle, Day Logging Status, and Food cutovers
also removed data/schema. Stop writes and either roll forward with an approved
corrective revision or restore the matching pre-cutover database backup together
with its compatible application release.

Rollback is not permission to delete production data, rewrite historical
migrations, revive retired features, or deploy without a separate authorization.

Issue #111 adds `python -m app.ops.internal_admin attach --username <username>` for the existing active legacy Admin only. It refuses any existing internal username/normalized username/hash, attaches internal credentials to the same Principal with `must_change_password=false`, and preserves legacy identity/email, role/status, private data and Food attribution. It makes no external call or session revocation; #113 rejects all legacy JWT admission. Password input is hidden or supplied through `--password-stdin`, never an argument or log. This is a user-run release step requiring authorization for the exact production action and revision; it has not been executed by this change. Admin creation/reset and destructive cutover retain their separate authorization boundaries. (Product Owner #111 authorization, 27 October 2026; BR-AUT-017, BR-USM-027.)
