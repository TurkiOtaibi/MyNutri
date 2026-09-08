# V2 Release and Rollback Runbook

Status: Operational authority. This document does not authorize a deployment or
production mutation.

## Release identity

The Food simplification migration has revision `f47a2c9d6e13` and parent
`8a91c4e7d2f6`. Confirm the intended application commit, generated contract,
single Alembic head, and approved environment before any rollout action.

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
- Historical Target Plan effective-date behavior remains unchanged.
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
- Food rows whose legacy taxonomy/source cannot follow the approved fallback.

Any non-zero blocking count stops the rollout. Do not delete, rewrite, or infer
production data during preflight.

## Deployment order

Only after a separately approved release window:

1. Verify backups and restore procedure.
2. Stop incompatible writers.
3. Apply the reviewed migration to the explicitly identified environment.
4. Deploy backend and frontend artifacts built from the same approved revision.
5. Verify health, authentication, Food reads, Diary reads, and Target Plan history.
6. Confirm archived Foods referenced by Diary history remain resolvable.
7. Confirm generated-contract and migration-head identities from runtime evidence.

## Smoke checks

- Create and edit a Food with a valid two-level taxonomy.
- Confirm only `official` and `estimated` are accepted for nutrition provenance.
- Record a Diary amount, edit current Food nutrition, and verify the old date
  recalculates while its consumed amount remains unchanged.
- Archive a referenced Food and verify the Diary still reads and calculates it.
- Verify an unreferenced Food can be deleted and a referenced Food cannot be
  hard-deleted.
- Verify an incompatible mass/volume basis edit is rejected for a referenced Food.
- Verify an older date continues to use its effective historical Target Plan.

## Rollback

Do not attempt an Alembic downgrade below `f47a2c9d6e13`; it fails closed by
design because removed product schemas and Food snapshots cannot be faithfully
reconstructed. Stop writes and either roll forward with an approved corrective
revision or restore the pre-migration database backup together with the matching
application release.

Rollback is not permission to delete production data, rewrite historical
migrations, revive retired features, or deploy without a separate authorization.
