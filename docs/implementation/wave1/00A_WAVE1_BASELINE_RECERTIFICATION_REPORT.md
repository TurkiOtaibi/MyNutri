# Wave 1 Baseline Recertification Report

## 1. Identity and Scope

| Field | Value |
|---|---|
| Report ID | `W1-BASELINE-00A` |
| Audited branch | `impl/wave1-00-baseline-and-execution-plan` |
| Audited base / main | `c9c12eb6922636833945308055597aaed55cc971` |
| Origin main at audit | `c9c12eb6922636833945308055597aaed55cc971` |
| Freeze package commit | `47265cd42138a9daca762a2c7cf6175065d5328b` |
| Audit date | `2026-07-16` |
| Product code changed | No |

The Freeze Index was present at `Frozen - Ready to Build`, authorized Wave 1 only, and kept later waves unauthorized. Artifacts 13-23 were present. No frozen contradiction or new Product Owner decision was found during repository inspection.

## 2. Brownfield Evidence Inspected

- FastAPI application, routes, services, Pydantic schemas, SQLModel models, database session/startup, and bearer-token dependency.
- Alembic configuration and immutable `0001_initial -> 0002_foods_v1_per_basis -> 0003_diary_meal_type` chain.
- Current Profile, Food, Diary, snapshot, aggregation, duplicate detection, and hard-delete behavior.
- Next.js Frontend, Arabic/RTL layout, API client, responsive components, service worker/PWA shell, Playwright suites, and package scripts.
- Backend tests and GitHub Actions workflow.

Confirmed implementation deltas, not baseline blockers: no durable Principal; bearer token is only a pass/fail credential; runtime startup still invokes `SQLModel.metadata.create_all`; no Target Plan, Snapshot v2, or frozen Registry/rules package exists. These are explicitly assigned to implementation stages 01-06.

## 3. Environment

| Component | Evidence |
|---|---|
| OS | Windows development host |
| PostgreSQL | Disposable PostgreSQL 16.14 cluster, trust-authenticated on loopback port 55432 |
| Database | `mynutri_wave1_00`; no production/shared database |
| Backend | Local FastAPI/Uvicorn on `127.0.0.1:8000` |
| Frontend | Local production Next.js server on `127.0.0.1:3000` |
| Browser | Playwright Chromium, one worker, `ar-SA`, `Asia/Riyadh` |

The disposable database was created through `initdb`, migrated with Alembic, and received only local test fixtures. E2E prerequisites were a valid Profile with a 2000 kcal target and one non-E2E Food used by the existing recent-food/visual expectations. No fixture was committed.

## 4. Validation Results

| Command / gate | Result | Counts / notes |
|---|---|---|
| `python -m ruff check .` | Passed | Exit 0 |
| `python -m pytest -q -rs` | Passed | 42 passed, 1 expected skip, 1 deprecation warning |
| Expected skip | Accepted | `tests/test_sync.py`: sync push/pull is disabled Future Scope for online-only v1 |
| `python -m alembic heads` | Passed | One head: `0003_diary_meal_type` |
| `python -m alembic upgrade head --sql` | Passed | Offline SQL renders 0001-0003 |
| Disposable PostgreSQL `alembic upgrade head` | Passed | Ledger at `0003_diary_meal_type`; tables `profile`, `food`, `diary_entry` |
| `npm ci` | Passed | 61 packages; 0 vulnerabilities; two dependency rename notices |
| `npm run typecheck` | Passed | Exit 0 |
| `npm run build` | Passed | Production build; 8 routes |
| `npm audit --omit=dev` | Passed | 0 vulnerabilities |
| `npm run test:e2e` | Passed | 245 passed, 0 failed, 0 skipped in 8.6 minutes |
| `git diff --check` before documentation | Passed | Clean |

The repository has no Frontend lint or unit/component script. Artifact 20's example `pnpm` commands do not match the current npm toolchain and are implementation targets, not silently claimed baseline passes. Existing GitHub CI likewise does not run real PostgreSQL or Playwright; stages 01 and 08 must add the required exact-head gates.

## 5. E2E Diagnostic History

The first run on a completely empty database produced 222 passes and 23 failures because Profile-dependent tests require an existing Profile. After adding a valid Profile, 243 passed and two tests failed because their fixtures assume a target below 2500 kcal and at least one persistent recent Food. Both failures reproduced with the incomplete fixture and both passed after the documented local prerequisites were supplied. The final full run passed 245/245.

This is classified as a baseline test-environment prerequisite, not a Product defect. Stage 08 must make fixture provisioning deterministic so a fresh-database E2E run cannot depend on undocumented retained data.

## 6. Generated Evidence Handling

Visual tests regenerated tracked screenshots under `docs/ui-ux/screenshots`. Those test-created changes were restored to the audited baseline and were not staged. Playwright `test-results`, reports, logs, the disposable database, and process files remain excluded. `frontend/debug-diary.png` was not present in this isolated worktree and was not read, changed, staged, or committed in the main worktree.

## 7. Findings and Risks

| Severity | Finding | Disposition |
|---|---|---|
| Critical | None | N/A |
| High | None | N/A |
| Medium | E2E setup depends on retained Profile/Food data | Resolve with deterministic fixtures by Stage 08; does not alter product behavior |
| Medium | Current CI lacks real PostgreSQL, E2E, accessibility, and migration rehearsal gates | Implement incrementally; mandatory before completion |
| Low | Starlette TestClient deprecation warning | Track during dependency/test maintenance |
| Low | Two Base UI package rename notices during npm install | Track; no audit vulnerability |

No baseline finding invalidates the frozen implementation plan. Physical iPhone/Android/PWA evidence remains a production-release gate, not an implementation-start gate, exactly as Artifact 20 specifies.

## 8. Verdict

```text
Frozen baseline verified: Yes
Critical baseline blockers: 0
High baseline blockers: 0
Required executable baseline gates passed: Yes
PostgreSQL migration baseline: Passed
Existing E2E regression: 245/245 passed
Product Owner decisions required: 0
Phase 0 verdict: Ready for documentation PR
```
