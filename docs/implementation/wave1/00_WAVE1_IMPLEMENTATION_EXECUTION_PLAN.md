# Wave 1 Implementation Execution Plan

## Metadata

| Field | Value |
|---|---|
| Plan ID | `W1-IMPL-PLAN-00` |
| Status | Active |
| Frozen baseline | `c9c12eb6922636833945308055597aaed55cc971` |
| Final Freeze Package Commit | `47265cd42138a9daca762a2c7cf6175065d5328b` |
| Scope | Wave 1 - Nutrition and Data Foundation only |
| Later waves | Not authorized |
| Production deployment | Not authorized |

## 1. Authority and Change Control

Implementation follows, in order, the Freeze Index, Product Decision Register v1.1, pinned Artifacts 13-21, approved C01-C02 and H01-H11 records, and current brownfield evidence. Current code does not override frozen behavior. A required contract change, contradiction, unsafe ownership or migration path, unresolved Critical/High finding, or unavailable mandatory gate stops the workflow for the named approver.

The application remains a brownfield myNutri implementation. NutriPlan, a greenfield rewrite, and Wave 2-4 behavior are excluded. `frontend/debug-diary.png` and generated test/runtime artifacts are excluded from every stage.

## 2. Stage and Dependency Sequence

| Stage | Branch / PR purpose | Frozen authority | Primary deliverables | Required evidence | Rollback boundary |
|---|---|---|---|---|---|
| 00 | `impl/wave1-00-baseline-and-execution-plan` | Freeze Index; Artifacts 20-21 | Plan, baseline report, register | Existing Backend, Frontend, Alembic, build, E2E | Documentation-only revert |
| 01 | `impl/wave1-01-principal-ownership` | C01; ADR-001-003; Artifacts 14-16, 20 | Principal, typed auth context, ownership, revisions 0004-0006 | Two-Principal/IDOR, token rotation, fresh/populated PostgreSQL | Additive owner-aware reader; fail before contract if reconciliation fails |
| 02 | `impl/wave1-02-rules-registry-calculations` | H01-H03, H05, H10; ADR-004/007 | Backend rules package, Registry, engine 2.0.0, calculations | W1-GC-001-015 and version/manifest/API tests | Previous compatible reader; no persisted new format yet |
| 03 | `impl/wave1-03-food-nutrition-foundation` | H05-H07, H09-H10; Artifacts 14-20 | Revision 0007-0008, Food nutrients, groups, traits, source, ingredients, NOVA, UI | W1-US-008-012; W1-GC-008-024; Food/UI/security/migration tests | Additive fields retained; no lossy downgrade after new controlled data |
| 04 | `impl/wave1-04-target-plans` | H01-H04, H10; ADR-005/009/010 | Revision 0009, preview/activation/lifecycle/idempotency, Profile UI | W1-US-002-007; W1-GC-029-035; concurrency and Riyadh boundaries | Target-Plan-capable reader after first write |
| 05 | `impl/wave1-05-snapshot-v2-diary-binding` | H04-H10; ADR-006 | Revision 0010, dual readers, v2 writer, Diary binding | W1-US-013/014/016; W1-GC-025-028; mixed v1/v2 and rollback | v2-capable reader required after first v2 write |
| 06 | `impl/wave1-06-diary-aggregation` | H11; ADR-008 | Nullable authoritative day/week aggregation and nutrient UI | W1-US-015; W1-UI-032-036; aggregation goldens | API-compatible application rollback; no data rewrite |
| 07 | `impl/wave1-07-frontend-integration` | Artifacts 15, 17-20 | Remaining W1-UI-001-038 integration | Component/E2E, RTL, axe, 320/360/390/430, build | Compatible Frontend rollback only |
| 08 | `impl/wave1-08-verification-certification` | Artifacts 16, 20-21 | Objective fixes, certification and residual-risk reports | Full migration/security/backend/frontend/device gates | Determined by written formats and Artifact 16 matrix |
| 09 | `impl/wave1-09-completion-audit` | Artifacts 20-21 | Final traceability, completion audit, completed register | Zero Critical/High, zero unexplained gaps/deviations | Documentation-only unless a traced defect fix requires a split PR |

Stages 01-07 may be split only where PostgreSQL transaction boundaries, reader-before-writer deployment, or independent security review require a smaller PR. Any split retains the same stage ID with a suffix and is recorded before merge.

## 3. Contract Mapping

| Concern | Decisions / ADRs | Data and migration | API | Story / UI | Golden / verification |
|---|---|---|---|---|---|
| Principal and authorization | C01; PD-023; ADR-001-003 | Principal, owner FKs, 0004-0006 | 401 and owner-safe 404 | W1-US-001/017 | Two-Principal, IDOR, ledger, backfill |
| Calories, protein, carbohydrates | H01-H03; PD-005-007 | Profile preference, Target Plan document | Preview/activation, protein object, warnings/errors | W1-US-002-005 | W1-GC-001-007 |
| Rules and Registry | H05/H10; PD-009/025/026; ADR-004/007 | Version columns/documents | `GET /nutrition/registry` | W1-US-008/009 | Manifest, schema, W1-GC-008-015 |
| Food quality foundation | H05-H07; PD-009-013 | 0007-0008; Food/group/trait tables | Food additive contracts | W1-US-009-012; relevant UI states | W1-GC-016-024; constraints and mapping |
| Target Plan lifecycle | H04; PD-008; ADR-005/009/010 | 0009; exclusion/partial constraints | Preview/current/pending/history/replace | W1-US-006/007/014 | W1-GC-029-035; atomicity/concurrency |
| Snapshot and Diary binding | H08; PD-014; ADR-006 | 0010; JSONB v2 and relational links | Backend writer and immutable update surface | W1-US-013/014/016 | W1-GC-025-028; v1/v2/integrity |
| Truthful aggregation | H11; PD-013/022; ADR-008 | Resolved snapshot data only | Nullable counts/coverage/evaluation | W1-US-015; W1-UI-032-036 | Empty/unknown/partial/complete matrix |
| UX and compatibility | PD-000/003/022; Artifacts 17/19 | Legacy rows remain valid | Additive/deprecated fields | W1-US-001-018; W1-UI-001-038 | Existing regressions, RTL, accessibility, devices |

## 4. Per-Stage Delivery Contract

Each stage starts from the latest merged `main` in an isolated worktree. It includes scoped implementation, required tests, an implementation report, strict Product/architecture/security/data/API/legacy/concurrency/UX review, exact-head CI evidence, a Draft PR, and a merge commit guarded by the reviewed head SHA. Main is then synchronized fast-forward-only and the completed worktree is removed.

Merge gates are: Critical 0, High 0, required tests and CI passed, unresolved blocking threads 0, unexpected files 0, frozen deviations 0, and `git diff --check` clean. Medium/Low findings are fixed or explicitly accepted only where Artifact 20 permits.

## 5. Expected File Boundaries

- Stage 01: Backend auth/config/session/models/services/routes, new Alembic revisions, security/migration tests.
- Stage 02: Backend rules/Registry/calculation modules, additive schemas/routes, generated Frontend types only, golden tests.
- Stage 03: Food model/schema/service/API/UI and revisions, Food tests.
- Stage 04: Target Plan model/service/API/Profile UI and tests.
- Stage 05: Diary model/snapshot readers-writer/API and tests.
- Stage 06: Backend aggregation/API plus nutrient-detail UI and tests.
- Stage 07: remaining Wave 1 Frontend integration and conformance tests.
- Stage 08: verification evidence and only narrowly traced defect corrections.
- Stage 09: implementation documentation and register only, unless a failed gate requires a separately reviewed fix PR.

Frozen product artifacts are not implementation working files. Any proposed modification to them requires formal change control and stops normal stage execution.

## 6. Completion Evidence

Every stage report records base/head/merge SHAs, changed files, migrations, API and UI changes, tests, commands and counts, security/data/legacy/rollback review, traceability IDs, residual risks, and verdict. Final completion requires all executable Artifact 20 gates, zero unexplained Artifact 21 gaps, zero frozen deviations, and no later-wave implementation. Physical-device and deployment evidence are reported separately and cannot be fabricated.
