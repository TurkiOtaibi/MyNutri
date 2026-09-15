# V2 Release and Rollback Runbook

Status: Operational authority. This document does not authorize a deployment or
production mutation.

## Release identity

The current migration head is Target Plan date-effective revision
`b7d42e9a1c36`, with parent `a6c81e4f2d90`. Confirm the intended application
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
- Diary quantity, recorded measurement, archived-Food resolution, hard-delete
  restriction, and mass/volume dimension safety tests pass.
- Target Plan date resolution selects the greatest applicable effective date and
  highest revision without a read-triggered write.
- Target Plan same-date writes insert immutable revisions, reject backdated
  dates, preserve legacy replay, and atomically rebind only today/future Diary
  rows in the affected interval.
- Diary create, update, and delete accept future dates without `If-Match` and
  do not read or write Day Logging Status state or history.
- Target Plan and unrelated idempotency rows survive the selective cleanup.
- Retired endpoints, navigation, schema fields, tables, flags, and generated
  contracts are absent.
- Historical Alembic revision hashes remain unchanged.
- `git diff --check` and exact-path scope verification pass.

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

Any non-zero blocking count stops the rollout. Do not delete, rewrite, or infer
production data during preflight.

## Deployment order

Only after a separately approved release window:

1. Verify backups and restore procedure.
2. Stop all incompatible Day Logging Status and Diary writers; there is no
   compatibility window.
3. Stop Target Plan lifecycle writers and other incompatible application
   instances; the Target Plan schema cutover also has no compatibility window.
4. Apply the reviewed migration to the explicitly identified environment.
5. Deploy backend and frontend artifacts built from the same approved revision.
6. Verify health, authentication, Food reads, Diary reads, and Target Plan history.
7. Confirm archived Foods referenced by Diary history remain resolvable.
8. Confirm generated-contract and migration-head identities from runtime evidence.

## Smoke checks

- Create and edit a Food with a valid two-level taxonomy.
- Confirm only `official` and `estimated` are accepted for nutrition provenance.
- Record a Diary amount, edit current Food nutrition, and verify the old date
  recalculates while its consumed amount remains unchanged.
- Archive a referenced Food and verify the Diary still reads and calculates it.
- Verify an unreferenced Food can be deleted and a referenced Food cannot be
  hard-deleted.
- Verify an incompatible mass/volume basis edit is rejected for a referenced Food.
- Verify historical/current/future Target Plan reads select the canonical plan by
  date and revision without writing lifecycle state.
- Write plans for today and two distinct future dates; revise one future date and
  verify history retains both revisions.
- Verify a future Diary row follows the revised canonical plan while a past Diary
  binding remains unchanged.
- Confirm the final Target Plan API contains only POST/list/current and exposes no
  lifecycle status, pending plan, or lifecycle timestamps.
- Create, update, and delete a future-dated Diary entry without `If-Match`.
- Confirm all four retired status routes return `404` and week summaries contain
  no status, version, completion timestamp, or entry-count presence field.

## Rollback

Do not downgrade below `b7d42e9a1c36`. The Target Plan lifecycle cannot be
faithfully synthesized from immutable revisions, and the preceding Day Logging
Status and Food cutovers also removed data/schema. Stop writes and either roll
forward with an approved corrective revision or restore the pre-migration
database backup together with the matching application release.

Rollback is not permission to delete production data, rewrite historical
migrations, revive retired features, or deploy without a separate authorization.
