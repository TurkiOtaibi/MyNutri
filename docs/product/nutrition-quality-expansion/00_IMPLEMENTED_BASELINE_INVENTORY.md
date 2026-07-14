# myNutri Implemented Baseline Inventory

Audit date: 2026-07-14

Repository: `C:\Users\DELTA\Desktop\مستشار`

Branch: `main`

HEAD: `fd50b51` (`chore: initial project upload`)

## 1. Purpose And Evidence Rules

This document records the system that actually exists in the current brownfield worktree. It does not treat a planning report as proof of implementation.

Evidence precedence used by this audit:

1. Current source, migrations, route registration, schemas, and tests.
2. The live local PostgreSQL development schema, inspected read-only.
3. Git history and staged/unstaged/untracked state.
4. Automated result artifacts and implementation reports.
5. BA, architecture, and system-planning documents.

The requested source named **myNutri Implemented Baseline & Expansion Delta Decision Register v1.1 Draft** was not found in the repository or in the locally available attachment paths searched during the audit. Therefore:

- The D-001 through D-026 classifications use `docs/ba/13_PRODUCT_DECISIONS.md`.
- Nutrition-quality decisions are assigned provisional IDs `NQ-001` through `NQ-025` from the approved expansion scope supplied for this work.
- Any classification that depends on the missing v1.1 register remains provisional until that source is supplied.

## 2. Git Baseline

### 2.1 Committed baseline

The repository has one commit. `HEAD`, local `main`, and `origin/main` all point to `fd50b51`.

That commit contains the original implementation, including:

- FastAPI, SQLModel, Alembic, and the initial database migration.
- Next.js application routes for Profile, Foods, and Diary.
- Server-side Mifflin-St Jeor target calculation.
- Initial Food and Diary snapshot concepts.
- Offline-first artifacts including `/sync`, IndexedDB/Dexie code, and sync status UI.
- Serving-based Food source fields and a flat Diary implementation.

The committed state is not the current implemented product.

### 2.2 Current uncommitted baseline

`git diff HEAD --stat` reports **158 changed paths**, approximately **25,413 insertions** and **2,733 deletions**. The worktree contains staged, unstaged, and untracked changes.

Major uncommitted groups:

| Group | Git state | Current behavior |
|---|---|---|
| Online-only alignment | staged/unstaged | `/sync`, Dexie, and SyncStatus removed; writes require API success |
| Foods v1 per-basis model | staged/unstaged | per-100g/per-100ml source, default-unit model, hard delete, optional nutrients |
| Migration `0002_foods_v1_per_basis` | staged | applied in local PostgreSQL |
| Migration `0003_diary_meal_type` | **untracked** | applied in local PostgreSQL |
| Diary meal sections and quantity UX | unstaged/untracked | meal type, compact Diary, Add Food sheet, quantity stepper |
| Profile redesign and preview | unstaged/untracked | draft/preview/save, advanced defaults, unified targets |
| Nutrition-quality expansion | **untracked plus unstaged edits** | six-nutrient registry, additional targets, coverage, Food completeness |
| Playwright infrastructure and suites | staged/unstaged/untracked | Foods, Diary, Profile, visual, and nutrition-quality coverage |
| Reports/screenshots | staged/untracked | implementation and visual evidence |

There are **107 untracked paths** before this audit's output files. They include 83 screenshots, migration `0003`, two backend services, nutrition tests, Profile tests, Diary tests, and `frontend/lib/nutrients.ts`. `frontend/debug-diary.png` is also untracked and is not a product source artifact.

### 2.3 Reproducibility consequence

Checking out `main` does not reproduce the current application or the current local database migration chain. The implemented baseline is currently a worktree state, not a versioned baseline.

## 3. Runtime And Technology Inventory

| Layer | Current implementation |
|---|---|
| Frontend | Next.js 16.2.10 App Router, React 19.2.7, TypeScript 6.0.3 |
| Client state | TanStack Query 5.101.2; API is source of truth |
| UI primitives | Base UI RC, Lucide icons, project CSS tokens in `frontend/app/globals.css` |
| Backend | FastAPI, SQLModel, Pydantic, SQLAlchemy/Alembic |
| Database | Local PostgreSQL development database `mynutri_dev` |
| Authentication | Single bearer token dependency on protected routers |
| Browser tests | Playwright 1.61.1 |
| Backend tests/lint | pytest and Ruff |
| PWA scope | Installable shell only; no personal-data IndexedDB source of truth or mutation queue |

## 4. PostgreSQL Baseline

The local database was inspected read-only. No production connection was used.

- Database: `mynutri_dev`
- Alembic revision: `0003_diary_meal_type`
- Tables: `profile`, `food`, `diary_entry`, `alembic_version`
- Data present at audit time: 1 Profile, 22 Foods, 13 Diary entries

### 4.1 Profile table

Persisted fields:

- `id`
- `sex`
- `birth_date`
- `height_cm`
- `weight_kg`
- `activity_level`
- `goal`
- `protein_per_kg`
- `fat_pct`
- `updated_at`

Daily targets and additional nutrient targets are derived and are not persisted.

### 4.2 Food table

Core and identity fields:

- `id`, `name`, `brand`, `category`
- `nutrition_basis`
- `default_unit_type`, `unit_amount`, `unit_basis`
- `calories`, `protein_g`, `carb_g`, `fat_g`
- `notes`, `data_source`
- timestamps

Nullable optional nutrient fields:

- `fiber_g`, `sugar_g`, `added_sugar_g`
- `saturated_fat_g`, `trans_fat_g`
- `sodium_mg`, `cholesterol_mg`, `potassium_mg`
- `calcium_mg`, `iron_mg`, `magnesium_mg`, `zinc_mg`
- `vitamin_d_mcg`, `vitamin_b12_mcg`, `vitamin_c_mg`
- `vitamin_a_mcg`, `folate_mcg`, `vitamin_k_mcg`

No `is_active` or `archived_at` Food column exists.

### 4.3 Diary entry table

Fields:

- `id`
- `entry_date`
- nullable `food_id` with `ON DELETE SET NULL`
- `quantity`
- non-null `meal_type`
- JSONB `nutrition_snapshot`
- `created_at`

The JSONB snapshot already supports nullable additional nutrients. A new nutrition-quality column migration is not required.

## 5. Migration Inventory

| Revision | Git state | Database state | Purpose |
|---|---|---|---|
| `0001_initial` | committed | applied | Initial Profile, Food, Diary schema |
| `0002_foods_v1_per_basis` | staged, uncommitted | applied | Per-100 source, default units, optional Food nutrients, legacy conversion |
| `0003_diary_meal_type` | **untracked** | applied | Adds `meal_type`; existing rows default to `unspecified` |

The nutrition-quality expansion itself adds no migration. It reuses nullable Food nutrient columns and Diary JSONB snapshots already introduced by the uncommitted baseline.

## 6. API Inventory

All application routers are protected by the current single-user token except health.

### 6.1 Registered routes

| Area | Method and route | Current contract |
|---|---|---|
| Health | `GET /health` | Health response |
| Profile | `GET /profile` | Saved profile plus calculated targets |
| Profile | `PUT /profile` | Validate and save one profile; returns authoritative calculated targets |
| Profile | `POST /profile/preview` | Validate and calculate without persistence |
| Foods | `GET /foods` | Legacy list or structured search/filter/sort/pagination response |
| Foods | `POST /foods` | Create Food with structured validation errors |
| Foods | `GET /foods/{id}` | Food details |
| Foods | `PUT /foods/{id}` | Update Food |
| Foods | `DELETE /foods/{id}` | Permanent hard delete |
| Diary | `GET /diary` | Entries, optionally filtered by date |
| Diary | `GET /diary/week` | Sunday-first weekly totals and targets |
| Diary | `POST /diary` | Create serving/default-unit entry and snapshot |
| Diary | `GET /diary/{id}` | Entry details |
| Diary | `PUT /diary/{id}` | Update quantity and optional meal type only |
| Diary | `DELETE /diary/{id}` | Permanent Diary entry delete |

`/sync` is not registered in the current router.

### 6.2 Additive nutrition target contract

`TargetResponse` includes:

- calculated calories and macros
- `carb_clamped`
- `additional_targets[]`

Each current additional target contains key, Arabic label, unit, precision, order, target type, target source, and nullable numeric target. Only fiber has a numeric target (`30 g`, minimum). This addition is backward compatible because the frontend type marks it optional and the schema uses a default empty list.

## 7. Calculation Engine Baseline

`backend/app/services/calc.py` remains the sole target calculation implementation.

Preserved rules:

- Mifflin-St Jeor BMR.
- Activity factors: 1.2, 1.375, 1.55, 1.725, 1.9.
- Goal factors: cut 0.8, maintain 1.0, bulk 1.1.
- Protein: current weight times configured protein-per-kg.
- Fat: target calories times configured fat ratio, divided by 9.
- Carbs: remaining calories divided by 4.
- Target calories use rounded raw target; macro outputs use one decimal place.

Current defaults:

- Protein: `1.2 g/kg` for both sexes.
- Fat: male `0.25`, female `0.30` when omitted/new/restored.
- Existing saved values are not rewritten automatically.

Current negative-carbohydrate behavior clamps carbs to zero and returns `carb_clamped=true`. The Profile UI does not visibly explain or block this condition.

## 8. Module Baseline

### 8.1 Foods

Implemented in the worktree:

- Standalone `/foods/new`, `/foods/{id}`, and `/foods/{id}/edit` routes.
- Per-100g/per-100ml source-of-truth values.
- Shared serving calculation utilities for derived list/details values.
- Search, category filtering, sorting, pagination, mobile Load More.
- Structured Arabic validation errors.
- Optional D-026 nutrient validation and cross-field checks.
- Permanent hard delete with confirmation and duplicate-submit protection.
- No archive/inactive fields or UI.
- Food Details additional nutrient display and completeness indicator.

### 8.2 Diary

Implemented in the worktree:

- Gregorian, Western-numeral, Sunday-first date/week navigation.
- Breakfast/lunch/dinner/snack sections plus conditional legacy `unspecified` section.
- Serving quantity range 0.01-50 and polished quantity stepper.
- Add Food two-state bottom sheet.
- Quantity and meal-type editing; Food/date/snapshot identity remain immutable.
- Snapshot-derived daily, weekly, meal calorie, and meal macro totals.
- Delete confirmation and duplicate mutation prevention.
- Compact macro progress with RTL fill, minimum marker, and over-target clamping.
- Daily nutritional-details sheet for six additional nutrients.
- Per-nutrient and overall snapshot-data coverage.

Direct gram-mode logging is not implemented.

### 8.3 Profile

Implemented in the worktree:

- Mobile settings-style Profile page.
- Draft-only sex/activity/goal selection sheets.
- Advanced protein and fat settings.
- Sex-aware defaults and Restore Defaults.
- Debounced server preview using `/profile/preview`.
- Dirty-state save bar, navigation guard, validation mapping, retry behavior.
- Unified current targets and separate expected targets.
- Additional nutrient targets section.

### 8.4 Add Food

Implemented in the worktree:

- Search/select and configure states.
- Recent and all Foods display from existing data flow.
- Meal preselection from section add actions.
- Decimal serving quantity, live snapshot-based preview, safe-area footer.
- Unsaved-change confirmation, duplicate-submit prevention, failure preservation.
- No offline queue and no gram mode.

## 9. Snapshot And Unknown-Value Baseline

Backend behavior is correct and explicit:

- `make_snapshot` copies each supported nutrient as a number or `null`.
- Explicit zero remains zero.
- Missing values remain `null`.
- Quantity edits scale known values and retain unknowns as `null`.
- Meal moves do not recreate the snapshot.
- Food edit/delete does not mutate prior Diary snapshots.
- Aggregation skips `null` and preserves an all-unknown aggregate as `null`.

Frontend exception:

- The Diary nutritional-details aggregator initializes each sum to zero. If every entry is unknown for a nutrient, it displays `0 [unit] على الأقل` and target status based on zero. This does not change stored data, but it violates the approved user-facing distinction between unknown and known zero.

## 10. Nutrient Registry Baseline

The six initial nutrients are implemented twice:

- `backend/app/services/nutrients.py`
- `frontend/lib/nutrients.ts`

Both currently define:

1. Fiber: minimum, fixed, 30 g.
2. Sodium: maximum, unconfigured.
3. Saturated fat: maximum, unconfigured.
4. Added sugar: maximum, unconfigured.
5. Potassium: minimum, unconfigured.
6. Cholesterol: monitor-only, unconfigured.

The values match today, but this is two registries rather than one centralized source. Profile and Diary overlay server target metadata; Food Details reads the frontend constants directly.

## 11. Automated Verification Inventory

Current declared test inventory:

- 39 backend test functions, with additional parameterized executions.
- 204 Playwright `test(...)` declarations.
- Foods QA CSV baseline: 153 cases.

Latest preserved full Playwright result artifact:

- `frontend/test-results/foods-results.json`
- Timestamp: 2026-07-12
- Result: **245 passed, 0 failed**

Latest nutrition-quality report records:

- Backend: **42 passed, 1 skipped**.
- Focused backend calculation/snapshot/nutrition: **14 passed**.
- Ruff: passed.
- Frontend typecheck: passed.
- Frontend production build: passed.
- Full Playwright project: **245 passed**.
- Focused nutrition-quality Playwright: **3 passed**.
- Visual specs: passed.
- `git diff --check`: passed at that run.

These results are evidence for the current worktree lineage, but they are not CI evidence tied to a commit SHA. The nutrition-quality functional suite contains only three broad scenarios and does not cover every approved expansion rule.

## 12. Baseline Summary

| Baseline area | Audit result |
|---|---|
| Core server calculation | Implemented and tested |
| Online-only architecture | Implemented in worktree; not committed |
| Foods v1 | Implemented and broadly tested; not committed |
| Diary redesign and meal grouping | Implemented and broadly tested; not committed |
| Profile redesign and preview | Implemented and tested; not committed |
| Nutrition-quality expansion | Substantially implemented; uncommitted; two material correctness/architecture gaps remain |
| PostgreSQL schema | At revision `0003`; migration chain not fully tracked |
| Decision governance | Incomplete because the named v1.1 register is unavailable |
| Physical-device QA | Pending |
