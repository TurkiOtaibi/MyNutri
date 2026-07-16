# Stage 04 Target Plans Implementation Report

## 1. Stage Identity

| Field | Value |
|---|---|
| Stage | 04 - Immutable Target Plans |
| Branch | `impl/wave1-04-target-plans` |
| Worktree | `C:\Users\DELTA\Desktop\MyNutri-wave1-04-resumed` |
| Base SHA | `6252bfcdbd0c391284fd4adbdf8d5dfcf9e9cb24` |
| Change decision | `W1-CD-01` |
| Change-package merge | `8b6c9d9f459d25af090d1bb726766f9aaf8a3cf4` |
| Re-pin merge | `6252bfcdbd0c391284fd4adbdf8d5dfcf9e9cb24` |
| Implementation commit | Pending |
| Pull request | Pending |

## 2. Frozen Authority

Implemented H01-H04, ADR-005/009/010, W1-CD-01, and Artifacts 14-18/20-21 as revised to version 1.1. Later-wave scheduling, backdating, multi-profile behavior, Progress, Analysis, and clinical modes remain excluded.

## 3. Preserved Exploratory Work

The original dirty Stage 4 worktree at base `9121b893bbe582d851c7570cdb899a8564a896ae` was archived without commit or push. Its external patch SHA-256 is `a4c001675c6913dc637a2eb52a0bcb2b7b2fbd900e501f81d1d2605a5528bc53`. Only compatible calendar, model, and schema concepts were reimplemented. The obsolete combined migration was discarded; no patch file is tracked.

## 4. Implementation

- Added explicit `Asia/Riyadh` configuration validation and Backend Diary-date helpers.
- Added Profile cut-intensity persistence and effective-date-aware target calculation.
- Added immutable `legacy_target_transition_snapshots` with owner-consistent foreign keys, one-row/Profile and Principal/date uniqueness, closed document construction, and a database mutation-rejection trigger.
- Added immutable Target Plan lifecycle fields, document/version persistence, active/pending uniqueness, effective-period exclusion, and controlled lifecycle mutation trigger.
- Added Principal/operation-scoped idempotency persistence and deterministic preview/request hashing.
- Added atomic first activation, pending replacement, rollback, replay, payload conflict, and Principal/Profile locking.
- Added current-date transition source, next-date plan source, pending/history reads, and no-current-Profile historical fallback.
- Added explicit Profile confirmation UI, scheduled-plan disclosure, replacement confirmation, stable retry identity, and duplicate-submit suppression.
- Corrected two baseline regression defects found by the full gate: Food edit hydration/response-field stripping and a self-contained Diary empty-state fixture.

## 5. Migrations

- `0009_legacy_target_transition_expand`: reader-first immutable transition table and Alembic ledger width required by the approved revision ID.
- `0010_target_plan_expand`: Profile cut intensity, Target Plans, deferred owner-consistent supersession FK, non-overlap/cardinality enforcement, immutable content trigger, and idempotency records.
- Revisions `0001` through `0003` remain byte-identical and immutable.
- No historical transition snapshot or Target Plan is backfilled.
- Downgrade below the snapshot-aware floor fails after data exists; application rollback requires a compatible reader.

## 6. API and Frontend

- Added `POST /target-plans/activate`, `POST /target-plans/pending/replace`, `GET /target-plans/current`, `GET /target-plans/pending`, and `GET /target-plans`.
- Preview returns a deterministic hash; clients cannot submit owner, effective date, target output, or calculation document authority.
- `GET /profile` resolves today's immutable transition target after activation and exposes current/pending summaries without owner IDs or raw JSON.
- Frontend uses Preview, explicit confirmation, idempotent activation, and distinct current/scheduled target cards.

## 7. Tests and Evidence

| Gate | Result |
|---|---|
| Backend full suite | `112 passed`, `1` expected Future Scope skip |
| PostgreSQL migration/rehearsal suite | `7 passed` |
| Target Plan and legacy transition contract tests | `11 passed` |
| Concurrent first activation | One snapshot, one plan, one idempotency record; losing request rejected |
| Atomic failure injection | Snapshot, Profile update, plan, and idempotency all rolled back |
| Profile E2E | `12/12 passed` |
| Full nonvisual Playwright regression | `243/243 passed` |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| `git diff --check` | Passed |

The first broad E2E run reported three reproducible baseline defects. They were corrected without changing frozen Product behavior, then the complete 243-test gate passed. Generated screenshots and test-result artifacts are excluded.

The final strict review also corrected opaque history pagination, lifecycle row locking, visible-ASCII idempotency validation, and truthful pre-transition legacy target resolution. Focused contract tests and the complete Backend suite passed after these corrections.

## 8. Security and Data Review

- Every plan, snapshot, replay key, read, and mutation is Principal scoped.
- Client owner identity, timezone, effective date, target results, and documents are rejected by closed schemas.
- Row locks and database constraints provide defense in depth against duplicate first transitions and pending plans.
- Cross-Principal reads return no owner data; two-Principal tests pass.
- Snapshot and plan content cannot be updated through Product operations; PostgreSQL triggers enforce immutability.
- Unknown/null values are preserved; no target history or Diary row is fabricated or rewritten.

## 9. Compatibility and Rollback

Existing Profile `PUT` remains additive compatibility behavior, but the Wave 1 UI uses explicit plan activation. Legacy Diary provenance is unchanged. The transition snapshot is neither a Target Plan nor Diary nutrition snapshot. Reader-before-writer deployment and the post-write compatible-reader floor are mandatory.

## 10. Independent Review Findings

| Severity | Finding | Disposition |
|---|---|---|
| Critical | None | N/A |
| High | None | N/A |
| Medium | Immediate supersession FK conflicted with pending-plan uniqueness | Corrected with a deferred owner-consistent FK and PostgreSQL rehearsal |
| Medium | Food edit could submit before response hydration and leaked response-only fields into update payload | Corrected; targeted and full E2E passed |
| Low | Starlette TestClient deprecation warning | Retained as dependency-maintenance risk |

## 11. Residual Risks

- Snapshot v2 Diary binding remains Stage 05.
- Backend nutrient aggregation remains Stage 06.
- Physical iPhone Safari and Android Chrome evidence remains a Stage 08 production-release gate.
- No production deployment was performed.

## 12. Stage Verdict

```text
Critical findings: 0
High findings: 0
Legacy transition golden scenarios: 100% passed
Atomicity tests: Passed
Concurrency tests: Passed
Owner isolation: Passed
Migration rehearsals: Passed
Rollback compatibility checks: Passed
Frozen-contract deviations: 0
Later-wave features introduced: 0
Stage verdict: Ready to Merge
```
