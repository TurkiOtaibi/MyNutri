# Wave 1 Verification and Regression Plan

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-VERIFY-20` |
| Version | `1.1` |
| Status | `Approved — QA, Security, and Engineering` |
| Owner | QA / Security / Engineering |
| Approver | QA / Security / Engineering |
| Approval date | `2026-07-16` |
| Review | `20A_WAVE1_VERIFICATION_REGRESSION_REVIEW.md` |
| Change review | `W1-CD-01A_LEGACY_TARGET_TRANSITION_IMPACT_REVIEW.md` |
| Critical / High / Product decisions | `0 / 0 / 0` |
| Pinned revision | `9d4911d2c8c55cfc02ad1ddfe891e8e9833fc1cf` |
| Implementation authorization | `No` |

## 1. Gate Policy

No Wave 1 implementation merges with any Critical/High defect, failed required check, unexplained traceability gap, migration mismatch, cross-Principal access, historical mutation, or false null/zero result. Evidence must belong to the exact final head. Existing meaningful regression tests cannot be weakened/deleted. This plan defines future implementation gates; current product tests are not re-certified by this documentation workflow.

## 2. Test Layers

### W1-CD-01 mandatory gate

- PostgreSQL fresh/populated migration proves the new table starts empty; constraints, owner-consistent FK, one-row/Profile uniqueness, exact Riyadh timezone check, JSON schema validation, and update/delete rejection execute.
- Two-Principal API/service tests prove resolution and errors cannot expose another owner's snapshot or target values.
- Transaction fault injection at each write boundary proves snapshot, Profile, plan/lifecycle, and idempotency completion roll back together.
- Parallel PostgreSQL activation and replacement tests prove one snapshot, one pending plan, immutable snapshot reuse, and no overlap.
- Golden `W1-GC-036..046` pass exactly, including transition-date target equality, immediate Profile update, tomorrow's plan, prior-date unavailable, new-Profile no-snapshot, replay/conflict, and Riyadh midnight.
- Historical resolution tests fail if mutable current Profile is queried as fallback after transition.
- Reader-before-writer deployment and mixed old/new rows pass before writer enablement. Rollback below the snapshot-aware compatibility floor is rejected after writes; no-write downgrade/re-upgrade is rehearsed losslessly.
- API regression preserves provenance enum and returns only normalized additive source detail. UI regression proves existing current/scheduled/legacy states remain truthful with no new feature.

This gate is mandatory for Stage 4 merge. A skipped PostgreSQL concurrency, atomicity, or rollback-floor test is a failure, not a pass.

### Backend unit and golden

- Pure decimal calculation tests for all `W1-GC-001` through `035`.
- Existing Mifflin/activity/goal/rounding baseline unchanged except approved H01-H03 deltas.
- BMI unrounded branch; exact 30; no intermediate rounding.
- All 16 targets and age/sex/calorie boundaries.
- Registry manifest deterministic hash and semantic bump checks.
- Source/reliability, NOVA, group serving/cap/exclusion rules.
- Nullable aggregation/coverage/evaluation matrix.

### API contract

- OpenAPI/schema snapshots for Artifact 15 additive requests/responses/errors.
- Unknown authoritative fields rejected.
- `401`, owner-safe `404`, validation `422`, conflict/incompatibility `409`.
- Registry ETag/304/cache and unsupported schema.
- Preview/save/activation identical calculations; blocked outcomes no persistence.
- Pagination/cursors, compatibility fields, `carb_clamped=false` only.

### Security and ownership

For at least Principal A/B, run CRUD/list/aggregate/duplicate/uniqueness/plan/snapshot tests. Prove IDOR denial for Food, Diary, Profile, Target Plan, idempotency replay, and integrity identifiers. Test token rotation, empty/missing/invalid production auth, no client owner authority, no global service path, no Service Role normal flow, and logs without credentials.

### Target Plan transaction/concurrency

- Preview no write.
- Activation atomic Profile+plan+lifecycle+same-date binding.
- H01/H03 failure rolls back all.
- One active/one pending and exclusion constraints under parallel PostgreSQL transactions.
- Same key/same payload replay; mismatch conflict; distinct-key race.
- Pending replacement audit and rollback.
- Riyadh current/next date and no backdating/arbitrary scheduling.

### Food/group/source

- 16 nutrient validation including known zero/null and exact DFE/RAE.
- Legacy fields preserved/excluded from exact completeness.
- Contribution >0<=100, uniqueness, partial totals, concurrent total >100 rejection.
- Traits independent; subtype/serving/fortification/overlap rules.
- Controlled source mapping, unknown, multiple→mixed, non-editable reliability.
- Ingredients source transitions; NOVA unknown/reviewed; no inference.
- Hard delete preserves Diary snapshots and clears live link.

### Snapshot and aggregation

- Backend-only writer rejects injection.
- Golden v1 and v2 fixtures; strict version dispatch; malformed/unsupported fail visible.
- Food edit/delete, rule/version change, quantity, and meal never mutate v2.
- Mixed v1/v2; null/zero/all-unknown/partial/complete/empty.
- Historical Target Plan source; current Profile cannot reinterpret.
- Partial asymmetric min/max/range and monitor/minimize.

## 3. Migration and Database Gates

Use disposable PostgreSQL, never SQLite as migration evidence:

1. one Alembic head and immutable 0001-0003 hashes;
2. fresh upgrade head;
3. populated 0003 upgrade;
4. absent/ambiguous Principal fail closed;
5. row-count/orphan/owner reconciliation;
6. no snapshot/legacy nutrient hash change;
7. constraints/indexes/types match Artifact 14;
8. reader-before-writer and mixed-version deployment;
9. safe interruption/resume;
10. permitted lossless downgrade/re-upgrade before writes;
11. compatible app rollback after v2/plan writes;
12. lossy downgrade rejection;
13. exact Alembic ledger equality and model-schema drift detection;
14. runtime startup proves no `create_all` or auto-migration.

## 4. Frontend and E2E Gates

Preserve existing Profile, Diary, Foods, Food Details, Add Food, navigation, accessibility, and visual suites. Add tests for every `W1-UI-001` through `038` and `W1-US-001` through `018` where observable.

Required browser assertions:

- Registry loading/error/incompatible and no fallback rules.
- Profile defaults/custom/restore, preview, safety, protein basis, carb warnings/errors.
- Current/proposed/pending/replacement/idempotency states.
- Food 16 nutrients, zero/null, legacy ambiguity, group/source/NOVA transitions.
- Diary v2 response, quantity/meal update, delete history, provenance, coverage/integrity.
- focus order/trap/restore, keyboard-only, Escape, reduced motion, no blank alerts.
- semantic progress names/values and color-independent statuses.

## 5. Responsive, RTL, Accessibility

Automated viewport matrix: 320×568, 360×800, 390×844, 430×932. Assert `scrollWidth<=clientWidth`, 44px targets, safe wrapping, attached units, no overlap, sheet safe area, and no hidden primary action. Run RTL direction and bidi-value assertions. Run axe on each major state with zero serious/critical violations; manual screen-reader names/status/focus review remains required.

## 6. Physical-Device Matrix

| Device evidence | Required before release | Current status |
|---|---:|---|
| Real iPhone Safari, dynamic bars, home indicator, keyboard, touch/sheet scroll | Yes | Pending implementation |
| Real Android Chrome, keyboard, back/Escape equivalent, touch scroll | Yes | Pending implementation |
| Installed PWA shell/navigation and online-only failure behavior | Yes | Pending implementation |

Pending physical evidence does not block documentation freeze or implementation start, but blocks Wave 1 release sign-off. No physical verification is claimed here.

## 7. CI Stages and Commands

Repository commands must be finalized against implementation tooling; minimum gates:

```text
cd backend && ruff check .
cd backend && pytest
cd backend && alembic heads
cd frontend && corepack pnpm lint
cd frontend && corepack pnpm typecheck
cd frontend && corepack pnpm test
cd frontend && corepack pnpm build
cd frontend && corepack pnpm playwright test
git diff --check
```

Dedicated CI jobs: static/type/lint; Backend unit/golden; disposable PostgreSQL integration/security; migration/rollback; Frontend unit/build; Playwright functional/accessibility; visual regression; artifact/evidence publication. Jobs fail closed and use no production/shared secrets or databases.

## 8. Evidence Contract

For each gate retain exact commit SHA, command, start/end, environment/tool versions, exit code, test counts, failure logs, migration ledger, schema fingerprint, screenshots/axe reports where applicable, and reviewer. Secrets and personal data are redacted. Reruns replace neither failed evidence nor head identity; final sign-off links the successful exact-head run.

## 9. Severity and Sign-off

- Critical: unauthorized access, ownership loss, historical corruption, unsafe migration; zero allowed.
- High: material contract missing/wrong, blocked safety bypass, null→zero, incompatible writer; zero allowed.
- Medium/Low: may remain only with owner, scope, risk acceptance, and no contract/readiness impact.

Required release sign-offs: Product/BA for acceptance; Architecture/Security for boundaries; Engineering/Data/Ops for schema/migration; API; UX/Accessibility; QA; physical-device QA. Documentation approval does not substitute for implementation evidence.

## 10. Regression Inventory to Preserve

Preserve current Backend calculation/Profile/Food/Diary/snapshot/aggregation tests; Frontend Profile/Diary/Foods/Food Details/Add Food functional and visual tests; RTL/accessibility checks; build/type/lint; and migration-chain tests. Any expected snapshot change requires explicit contract traceability and reviewer approval, never blanket regeneration.

## 11. Deferred Scope

No test gate authorizes later-wave Progress/Analysis, offline sync, direct gram/ml logging, multi-profile, public Foods, clinical mode, AI, or deployment/release during documentation authoring.
