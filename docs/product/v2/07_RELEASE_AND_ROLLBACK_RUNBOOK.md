# V2 Release and Rollback Runbook

Status: Operational authority. This document does not authorize a deployment or
production mutation.

## Admin-managed account lifecycle release gates (pending implementation)

The approved account lifecycle requires a separate release review and does not
change the current deployed revision by this documentation update. Before
cutover, verify exactly one bootstrap Admin, the partial unique Admin-role
index, existing Principal/Auth-link integrity, full private-FK inventory, and
Food attribution to Principals. A count above one Admin, unresolved ownership,
or an unsafe migration stops rollout. Establish the single Admin before making
Admin-created accounts the only admission path.

Release backend admission and all Principal-owned writer status/lock checks
together with the lifecycle schema. Configure the Service Role credential only
for FastAPI Admin create/reset/delete and bootstrap; verify it is absent from
frontend/public variables, responses, and logs. Disable public Supabase signup
and remove the sign-up UI in the coordinated cutover. Direct signup, unknown
Auth identities, and all non-active statuses must fail application admission.
Keep the current Admin's ability to read selected Profile/Diary/Labs without
write access to those resources.

In an explicitly authorized disposable environment, verify interrupted create
resumes with the same idempotency key; interrupted deletion remains `deleting`,
rejects even pre-existing access tokens, is visible to Admin as incomplete,
and resumes to a scrubbed `deleted` tombstone. Verify the locked purge removes
all private dependents while global Foods and their attribution survive. A
missing Supabase identity counts as a successful deletion retry. Validate
concurrent writers cannot insert private data after the purge and that no API
can create or disable/delete the single Admin.

Do not treat a partially completed saga as a successful deletion or re-enable
an account in `deleting`. Rollback across irreversible Auth/private-data
deletion cannot reconstruct those records from code or a reverse migration;
pause new lifecycle operations and use an explicitly authorized matching
database/Auth recovery procedure or roll forward to complete the saga.
New UI/error Arabic copy remains pending Product Owner approval in the BA field
dictionary and cannot ship before approval.

## Release identity

The current migration head is private Labs persistence revision `e8b7a42f6c31`,
with parent Food catalog unification revision `d9f64a1c3e58`. Confirm the intended application
commit, generated contract, single Alembic head, and approved environment before
any rollout action.

## Required pre-release validation

- Backend Ruff/static checks and the complete pytest suite pass.
- A disposable PostgreSQL database upgrades cleanly from base to head.
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
- Diary create, update, and delete accept future dates without `If-Match` and
  do not read or write Day Logging Status state or history.
- Target Plan and unrelated idempotency rows survive the selective cleanup.
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
  Linux visual, PWA, development StrictMode and seven provider cases plus cleanup.
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
- Create, update, and delete a future-dated Diary entry without `If-Match`.
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
