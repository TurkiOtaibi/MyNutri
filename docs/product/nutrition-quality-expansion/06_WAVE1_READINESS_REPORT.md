# Nutrition Quality Wave 1 Readiness Report

Audit date: 2026-07-14

Branch: `main`

HEAD: `fd50b51`

## 1. Readiness Verdict

**Verdict: Conditional No-Go for declaring Wave 1 complete or release-ready.**

**Implementation readiness: Ready for a small, targeted reconciliation wave after two critical prerequisites are resolved.**

The product is not missing the whole Nutrition Quality expansion. Most of it already exists in the current worktree and has recent automated evidence. The remaining product deltas are narrow but material:

1. Replace the duplicated backend/frontend nutrient registries with one source.
2. Stop presenting all-unknown Diary nutrient data as numeric zero.
3. Define and expose the approved negative-carbohydrate outcome.
4. Complete requirement-level regression coverage.

Wave 1 cannot be signed off now because the implementation/migrations are not reproducible from Git and the named governing v1.1 decision register is unavailable.

## 2. Exact Implemented Baseline

### Committed and still valid

- FastAPI/SQLModel/PostgreSQL architecture.
- Single-user bearer-token model.
- Mifflin-St Jeor calculation engine.
- Current activity and goal factor algorithms.
- Diary snapshot principle.
- Core Profile, Food, and Diary route families.

### Current worktree behavior

- Online-only runtime with no Dexie/sync route/mutation queue.
- Foods per-100g/per-100ml model and serving-first presentation.
- Standalone Food create/details/edit routes.
- Search, category, sorting, pagination, Arabic errors, optional nutrients.
- Permanent Food hard delete and snapshot-safe history.
- Diary Gregorian week/day UX, meal sections, quantity stepper, Add Food sheet.
- Diary quantity/meal edit, delete confirmation, and frozen snapshot aggregation.
- Redesigned Profile with server preview, dirty state, advanced settings, save guard.
- Protein default 1.2 and sex-aware fat defaults.
- Six additional nutrients in Profile, Food Details, Diary meal totals/details.
- Food data completeness and Diary data coverage.
- RTL macro progress and meal macro totals.

## 3. Exact Uncommitted Baseline

The current behavior is not represented by `HEAD`.

Key uncommitted dependencies include:

- `backend/alembic/versions/0002_foods_v1_per_basis.py` (staged).
- `backend/alembic/versions/0003_diary_meal_type.py` (untracked).
- Updated backend models, schemas, Food/Diary/Profile services and routes.
- `backend/app/services/nutrients.py` (untracked).
- `backend/tests/test_nutrition_quality.py` (untracked).
- Updated Profile, Diary, Foods, Food Details, and Add Food frontend components.
- `frontend/lib/nutrients.ts` (untracked).
- Profile, Diary, and nutrition-quality Playwright tests, many untracked.
- Nutrition-quality screenshots and implementation report, untracked.

The local PostgreSQL database is already at revision `0003_diary_meal_type`.

## 4. Partial Implementations

| Area | Implemented portion | Missing/incorrect portion |
|---|---|---|
| Nutrient registry | Same six definitions exist in both runtimes | Two editable sources, not one central registry |
| Unknown nutrient handling | Backend stores/aggregates null correctly | Diary all-unknown UI displays `0 ... على الأقل` |
| Negative carbs | Server clamps and returns `carb_clamped` | UI does not explain or block the invalid configuration |
| Profile calculation explanation | Mifflin and general inputs described | Protein grams/kg, fat calorie %, remaining carbs not explicit |
| Nutrition tests | Broad backend/frontend scenarios pass | Requirement-level matrix is incomplete |
| D-009/D-012 validation | Some future/positive/range checks exist | Age and Profile range decisions conflict with code |
| D-022 read copy | Contextual errors exist | Current Profile/Diary copy differs from decision text |
| PWA shell | No API/IndexedDB source-of-truth | Physical/offline shell behavior not fully verified |

## 5. Exact Wave 1 Additions And Modifications

### Required additions

1. One repository-owned nutrient definition contract consumed by Python and TypeScript.
2. Characterization tests for registry identity, null/zero, snapshots, coverage, and default/custom behavior.
3. Explicit approved `carb_clamped` UX/API handling.
4. Formal decision entries for the current Nutrition Quality rules if absent from the v1.1 register.

### Required modifications

1. Diary additional nutrient aggregate must be nullable when no entry has a known value.
2. Diary row must render `غير متوفر` and no progress/status when `known=0`.
3. Frontend nutrient definitions must stop duplicating backend target/label/order data.
4. Profile explanation must state the approved macro allocation in user language.
5. Expansion-specific tests must be split into executable requirement-level cases.
6. Implementation report claims must be corrected after the fixes.

### Explicitly not required

- No new database table or column.
- No new nutrition migration.
- No persisted target values.
- No client target formula.
- No extra numeric targets beyond fiber.
- No gram mode within Wave 1.
- No health score.

## 6. Exact Schema Delta

### From current database to completed Wave 1

**None.**

Current nullable Food fields and Diary JSONB snapshots support all approved Wave 1 values.

### From committed `HEAD` to current baseline

Large and uncommitted:

- Food per-basis/default-unit schema and optional nutrients (`0002`).
- Diary meal type (`0003`).
- Profile default code changes (no DB column change).

This baseline delta must be versioned before Wave 1 sign-off.

## 7. Exact Migration Delta

- Required new Wave 1 migration: **none**.
- Required baseline action: version and rehearse `0002` and `0003`.
- Required data rule: preserve null unknowns; never backfill zero.
- Required compatibility rule: preserve existing Profile values and legacy Diary snapshots.

## 8. Exact API Delta

### Already present, uncommitted

- `POST /profile/preview`.
- Additive `TargetResponse.additional_targets`.
- Diary response totals containing nullable nutrient values.

### Required for Wave 1 completion

- No new route is required.
- Keep `additional_targets` backward compatible and derive it from the one shared registry.
- Formalize `carb_clamped` behavior in the existing response/error contract.
- Preserve all current route paths and enums.

## 9. Existing Tests That Must Be Preserved

### Backend

- Calculation tests, including Mifflin, factors, rounding, and clamp behavior.
- Foods API/service/validation/pagination tests.
- Diary snapshot and hard-delete safety tests.
- Food import and idempotency tests.
- Current nutrition-quality tests.

### Frontend

- Full Foods Playwright baseline.
- Full Diary functional/visual/Add Food/final-polish baseline.
- Full Profile functional/visual baseline.
- Nutrition-quality functional/visual specs.
- Online-only/no-IndexedDB assertions.

### Quality gates

- Backend pytest.
- Ruff.
- Frontend TypeScript typecheck.
- Frontend production build.
- Playwright Foods project/full relevant suite.
- `git diff --check`.

## 10. New Required Tests

### Critical behavior

- One shared registry is identical in backend target payload and frontend display order.
- All unknown values render `غير متوفر`, never numeric zero.
- Known explicit zero renders zero and counts toward coverage.
- Partial known totals render the known sum as `على الأقل`.
- `carb_clamped` follows the approved reject/warning behavior.

### Profile

- Male/female omitted defaults through API.
- Existing 1.8/0.25 saved values remain unchanged.
- Sex switch updates only prior default, not custom fat.
- Restore Defaults does not persist before save.
- Preview and PUT return matching targets for identical input.
- Explanation copy covers protein/fat/carbs allocation.

### Diary/snapshots

- Six nutrients captured on create.
- Quantity edit scales positive/zero and preserves null.
- Meal move does not recreate snapshot source values.
- Food edit/delete cannot mutate historical additional nutrients.
- Meal macro totals update after add/edit/move/delete.
- Coverage exactness across multiple mixed-completeness entries.
- Details sheet focus, Escape, safe area, and widths 320/360/390/430.

### Food Details

- Six nutrient values and units.
- Fiber percentage only; no fabricated target percentages.
- Completeness numerator/denominator and all threshold boundaries.
- Missing list only contains supported tracked nutrients.
- Completeness absent from Foods list, Add Food, Diary search, and Diary rows.

## 11. Issue Summary

### Critical - 2

1. **C01: Unversioned implemented baseline and migration chain.** Local DB is at an untracked migration.
2. **C02: Missing v1.1 governing decision register.** Exact approved-decision reconciliation cannot be certified.

### High - 5

1. **H01: Duplicate nutrient registries** can drift across API/Profile/Diary/Food Details.
2. **H02: All-unknown Diary nutrients display as zero**, violating the central data-honesty rule.
3. **H03: Negative carbohydrate state is silent** despite `carb_clamped` being returned.
4. **H04: Expansion-specific automated coverage is incomplete** against the approved matrix.
5. **H05: Applied migrations `0002`/`0003` are not both committed**, blocking clean rehearsal/deployment.

### Medium - 6

1. Profile macro explanation is incomplete.
2. Profile age/range decisions conflict with current validation.
3. Read-failure copy differs from D-022 in Profile/Diary.
4. Nutrition implementation report overstates centralization/null behavior.
5. Physical-device QA is pending.
6. LAN dev CORS/API configuration is session-dependent and has produced failed preflights.

### Low - 2

1. Untracked debug screenshot should be excluded from a checkpoint.
2. No explicit frontend lint script exists.

## 12. Contradictions Between Code And Documents

| Document statement | Actual current system | Resolution needed |
|---|---|---|
| System Plan: offline-first | Online-only worktree | Supersede/update System Plan |
| Architecture: Dexie and `/sync` | Removed/unregistered | Supersede/update architecture |
| System Plan: Food values per serving | Per-100 source | Supersede/update plan |
| System Plan: meal type deferred | Meal type migrated and live | Record current decision |
| System Plan: micros excluded | Optional nutrients and six tracked nutrients live | Record current decision |
| D-007/D-021: gram mode required | Serving-only API/UI | Resolve/defer formally |
| D-009: age 10-100 | Not enforced | Implement or supersede |
| D-012: Profile ranges | Current schema differs | Select authoritative ranges |
| D-010: quantity-only edit | Quantity plus meal type | Formalize supersession |
| D-022: exact copy | Profile/Diary use newer copy | Confirm approved copy |
| Implementation report: centralized registry | Two registries | Correct after centralization |
| Implementation report: unknown never zero | Diary all-unknown UI shows zero-at-least | Correct behavior and report |

## 13. Superseded Historical Assumptions

- Archive/inactive Food lifecycle.
- `is_active` and `archived_at`.
- Serving-based Food source fields.
- Offline write queue and sync API.
- Dexie personal-data source of truth.
- Meal type deferred to v2.
- Micronutrients excluded from the product.
- One fixed 1.8 protein default for new profiles.
- A single 25% fat default for both sexes.

## 14. Verification Evidence Reviewed

### Current source and environment

- `git status`, `git diff HEAD`, and sole commit history.
- All three Alembic migrations.
- Read-only PostgreSQL schema and current revision.
- Backend routes, models, schemas, services, and tests.
- Frontend routes, components, API/types/helpers, CSS, and Playwright suites.
- System Plan, Architecture Services, BA decisions, and implementation reports.

### Latest preserved automated results

- Playwright JSON artifact: **245 passed, 0 failed** on 2026-07-12.
- Nutrition implementation report: backend **42 passed, 1 skipped**.
- Focused backend: **14 passed**.
- Typecheck: passed.
- Production build: passed.
- Ruff: passed.
- `git diff --check`: passed at that verification run.

This audit did not rerun mutation-capable E2E suites because the task is report-only and the current local development database contains data. It inspected the latest result artifact and the executable tests. Final Wave 1 implementation must rerun every gate from a versioned baseline.

## 15. Recommended Wave 1 Gate

### Before implementation

1. Supply the v1.1 register.
2. Resolve `carb_clamped`, Profile ranges, gram-mode status, and read-copy authority.
3. Create a verified checkpoint of current source/migrations/tests.

### Before completion sign-off

1. Central registry is single-source.
2. Unknown-only rendering is corrected.
3. All required focused tests pass.
4. Full existing regressions pass.
5. Clean PostgreSQL migration rehearsal passes.
6. Reports/system architecture are reconciled.
7. Physical-device QA status remains explicit.

## 16. Final Recommendation

Do not start a broad nutrition rewrite. The architecture and data model already support Wave 1.

Proceed with a **targeted stabilization implementation** only after the governing source and Git baseline are fixed. The expected product-code change should be small: one shared registry contract, one nullable Diary aggregation correction, explicit negative-carb handling, a Profile explanation update, and focused tests. No new database migration or new nutrient API route is currently justified.
