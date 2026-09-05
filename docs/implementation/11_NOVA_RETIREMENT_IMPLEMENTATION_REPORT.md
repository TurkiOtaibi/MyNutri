# NOVA Retirement Phase-1 Implementation Report

## Status

The frozen NOVA Retirement Design 1.8 has been implemented on branch
`nova-retirement-implementation-1.8` from pinned base
`3db21b45efba1c533abd72d14a169f62ca2ac438`. The Project Owner authorized
publication of this implementation branch and a Draft PR for canonical GitHub
CI on the published source commit. Merge and deployment remain unauthorized.
Production databases, credentials, Render, and Supabase production were not
accessed or changed.

## Implemented contract

- Registry schema 3 / Registry `3.0.0` removes only active NOVA definitions.
- SnapshotV4 removes `nova` and `versions.nova_rules_version`; V1-V3 readers
  remain available for historical data and new captures use V4.
- PLAN 032 exposes the frozen V2 request, response, history, revision, and
  evaluation contracts with interface version 2 and rules version
  `w3-analysis-2.0.0`.
- Active Food request/response and UI contracts no longer expose or write NOVA.
- PLAN 033 remains V1 and inactive for new recommendations, offers, goals, and
  reminders; existing historical reads and terminal archive behavior remain.
- Phase 1 retains nullable physical Food NOVA columns and installs only the
  frozen row-shape, cutover-lock, canonical-version-array, and downgrade guards.
  Physical column deletion remains deferred to a separately authorized Phase 2.

## Migration

Exactly one additive revision was created:

- `backend/alembic/versions/8a91c4e7d2f6_nova_retirement_phase1.py`
- revision: `8a91c4e7d2f6`
- down revision: `22733dbf5249`

The complete pinned Alembic chain upgrades a fresh PostgreSQL 16 database to
this sole head. `alembic check`, production-style preflight, offline SQL
generation, downgrade refusal, model drift, row-shape enforcement, and the
shared/exclusive cutover concurrency cases pass against disposable databases.

## Frozen design integrity

The four frozen design artifacts were not changed. Their SHA-256 hashes remain:

- `29_NOVA_RETIREMENT_AND_HISTORICAL_COMPATIBILITY_DESIGN.md`:
  `C5BBFA214F290FCC2801396E46681186B3578A426F35998C011A41775D69EB01`
- `29A_NOVA_RETIREMENT_GOLDEN_VECTORS.json`:
  `20B830945DB6486F8C4F5A8B6E0693E87D1CC74EBB567CADE7884614459B26AD`
- `tools/verify_nova_retirement_vectors.py`:
  `C361202F3E04166092D1878427AF385B62FFE1F0882C7EF44AA462DF8ECA2A56`
- `29B_NOVA_RETIREMENT_APPROVAL_REPORT.md`:
  `E7B8608FAC19FDC52D5D9BC354C75C068FFE885ACC1818F8D3BAA41186D476F4`

## Validation evidence

- Frozen verifier: pure validation PASS; PostgreSQL 16 row-shape oracle PASS;
  zero verifier crashes.
- Ruff: PASS.
- Backend without PostgreSQL: 720 passed, 85 skipped.
- Complete PostgreSQL-enabled Backend suite: 804 passed, 1 skipped; zero setup
  failures or errors attributable to disposable database state.
- Sole Alembic head: `8a91c4e7d2f6`; upgrade, model drift, preflight, and offline
  SQL PASS.
- OpenAPI export and generated TypeScript: byte-reproducible after regeneration.
- TypeScript: PASS.
- ESLint: PASS with 25 warnings and zero errors.
- Vitest and architecture tests: 33 passed.
- Production build: PASS, 16 routes generated.
- PWA isolation: 5 passed.
- Development StrictMode smoke: 1 passed.
- NOVA-focused Playwright cases: PASS.
- Linux critical visuals: the two owner-authorized NOVA snapshots regenerated
  and then passed comparison, 2/2.
- Complete host Playwright execution: 368 passed and 6 failed. A focused rerun
  produced 2 passes and 4 failures in unchanged Diary presentation tests.
  The subsequent attribution gate ran those exact four tests against fresh
  disposable PostgreSQL 16.14 databases and production builds using the same
  Playwright 1.61.1 environment: the NOVA worktree passed 4/4, and a clean
  checkout of the pinned baseline passed 4/4 on repeat (its initial run had one
  early page-readiness timeout). The earlier overflow failures did not reproduce
  in these isolated runs. The Project Owner accepted the attribution as
  `PRE_EXISTING_BASELINE`, with no NOVA regression and no additional Diary/CSS
  scope required. No out-of-scope Diary layout file was changed.
- `npm audit --omit=dev`: zero vulnerabilities.
- Full `npm audit`: one high-severity `fast-uri` advisory in the development-only
  OpenAPI generation chain. The lockfile blob is byte-identical to the approved
  baseline (`fc93c1cd2bd059a3749eec47c941be7ddfd75ea2`); dependency remediation was
  explicitly excluded from this task.
- `pip check`: PASS.
- `git diff --check`: PASS.

## Publication and remaining gate

The next gate is the canonical GitHub CI workflow for the exact published
source commit. Local validation results above do not substitute for that run.
The Draft PR remains a draft after CI. The separate Diary timing/shared-state
issue and pre-existing development-only `fast-uri` advisory are outside this
implementation scope; their tests and dependency gates are not bypassed.
The attribution databases, container, baseline worktree, and local services
were removed after validation. Merge, deployment, and production migration
require separate Project Owner authorization.
