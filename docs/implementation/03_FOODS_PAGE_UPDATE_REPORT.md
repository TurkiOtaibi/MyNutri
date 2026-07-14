# Foods Page v1 Update Report

Status: Implemented
Scope: Foods v1 update only, plus minimal Diary snapshot safety for Food hard delete history.
BA files changed: No.
QA files changed: No.
Committed: No.

## 1. Summary of Implementation

Implemented the updated Foods v1 requirements:

- `/foods` is now a list/search/browse page only.
- `/foods/new` is a standalone Add Food page.
- `/foods/:id` is a standalone Food details page.
- `/foods/:id/edit` is a standalone Edit Food page reusing the Add Food structure.
- Food nutrition source of truth is now per 100g or per 100ml.
- Default unit fields are implemented: `default_unit_type`, `unit_amount`, and `unit_basis`.
- Food deletion is permanent hard delete with an accessible confirmation dialog.
- No Food archive/inactive behavior was added.
- No `is_active` or `archived_at` fields were added.
- No Active/Archived filters were added.
- D-026 optional nutrient fields and validation ranges are implemented.
- Duplicate Food blocking is implemented for current catalog Foods.
- `sugar_g` is used as the v1 total sugar field; `total_sugars_g` remains only as legacy snapshot compatibility.
- Minimal Diary snapshot safety was updated so new entries preserve enough Food data to remain readable after Food hard delete.

## 2. Files Changed

Backend:
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/food.py`
- `backend/app/services/diary.py`
- `backend/alembic/versions/0002_foods_v1_per_basis.py`
- `backend/tests/test_diary_snapshot.py`
- `backend/tests/test_foods.py`

Frontend:
- `frontend/app/foods/new/page.tsx`
- `frontend/app/foods/[id]/page.tsx`
- `frontend/app/foods/[id]/edit/page.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/components/FoodFormPage.tsx`
- `frontend/components/FoodDetailsPage.tsx`
- `frontend/components/FoodDeleteDialog.tsx`
- `frontend/components/useFoodDelete.ts`
- `frontend/components/DiaryPage.tsx`
- `frontend/lib/api.ts`
- `frontend/lib/food.ts`
- `frontend/lib/types.ts`
- `frontend/app/globals.css`

Documentation:
- `docs/implementation/03_FOODS_PAGE_UPDATE_REPORT.md`

Note: the working tree already contained prior Phase 1 and BA documentation changes before this implementation.

## 3. Database/Migration Changes

Created migration:
- `backend/alembic/versions/0002_foods_v1_per_basis.py`

Food table changes:
- Added `brand`.
- Added `category`.
- Added `nutrition_basis`.
- Added `default_unit_type`.
- Added `unit_amount`.
- Added `unit_basis`.
- Added `sugar_g`.
- Added D-026 optional nutrient fields:
  - `potassium_mg`
  - `calcium_mg`
  - `iron_mg`
  - `magnesium_mg`
  - `zinc_mg`
  - `vitamin_d_mcg`
  - `vitamin_b12_mcg`
  - `vitamin_c_mg`
  - `vitamin_a_mcg`
  - `folate_mcg`
  - `vitamin_k_mcg`
- Added `notes`.
- Added `data_source`.
- Removed old catalog source-of-truth fields:
  - `serving_label`
  - `serving_grams`
  - `total_sugars_g`

Migration behavior:
- Existing `total_sugars_g` values are copied into `sugar_g`.
- Existing serving-based nutrition is best-effort converted to per-100g when `serving_grams` exists.
- Existing rows without `serving_grams` default to per-100g with a 100g unit amount.

Not added:
- `is_active`
- `archived_at`
- Any archive/inactive status fields.

Migration verification:
- PostgreSQL SQL rendering passed with `alembic upgrade head --sql`.
- A SQLite Alembic smoke run was attempted but stopped in the existing `0001_initial` migration before this new migration because `0001_initial` uses PostgreSQL `JSONB` directly. Backend tests still pass using SQLModel `create_all`; production target remains PostgreSQL.

## 4. API Changes

Food API behavior is updated through schemas/services while keeping the same endpoint paths:

- `GET /foods`
  - Lists current catalog Foods only.
  - Supports `q` search by Food name.
  - Returns new per-100g/per-100ml/default-unit fields.

- `POST /foods`
  - Creates a Food using the v1 Food contract.
  - Blocks current-catalog duplicates.
  - Validates D-026 optional nutrients and cross-field rules.

- `GET /foods/{food_id}`
  - Returns Food details with core, optional, metadata, and timestamps.

- `PUT /foods/{food_id}`
  - Updates existing Food data.
  - Revalidates the full merged Food record.
  - Blocks duplicates against other current catalog Foods.

- `DELETE /foods/{food_id}`
  - Permanently deletes the Food.
  - Does not archive or inactivate.
  - Repeated/stale delete returns not found.

Structured duplicate error:
- Returns HTTP 422 with Arabic message: `هذا الطعام موجود مسبقًا بنفس الوحدة.`

## 5. Frontend Route/Page Changes

Routes implemented/aligned:

- `/foods`
  - List/search/browse only.
  - Add Food button links to `/foods/new`.
  - Desktop table columns: name, brand, category, nutrition basis, default unit, calories, protein, carbs, fat, actions.
  - Mobile cards show name, nutrition basis, default unit, calories, protein, carbs, fat.
  - Loading, empty, no-results, and error states are implemented.

- `/foods/new`
  - Standalone Add Food page.
  - No delete action.
  - Grouped sections:
    - Basic food information.
    - Nutrition basis.
    - Core nutrition values.
    - Default unit.
    - Optional nutrients.
    - Notes and data source.

- `/foods/:id`
  - Standalone Food details page.
  - Shows full Food name, metadata, core nutrition, optional nutrients, notes, data source, created/updated dates.
  - Includes Edit and Delete actions.

- `/foods/:id/edit`
  - Standalone Edit Food page.
  - Reuses Add Food structure.
  - Loads existing Food values.
  - Save happens only after successful API response.
  - Delete may be triggered from this page.

## 6. Validation Changes

Frontend validation:
- Required Food name.
- Food name cannot be whitespace-only.
- Required nutrition basis.
- Required core nutrition values.
- Required unit type, unit amount, and unit basis.
- Unit amount: 1-2000.
- Calories: 0-3000.
- Protein: 0-300g.
- Carbs: 0-500g.
- Fat: 0-300g.
- Optional nutrients are optional when blank.
- Optional nutrients validate min/max when provided.
- Cross-field rules:
  - `fiber_g <= carb_g`
  - `added_sugar_g <= sugar_g` only when both are provided.
  - `saturated_fat_g <= fat_g`
  - `trans_fat_g <= fat_g`
  - `saturated_fat_g + trans_fat_g <= fat_g`

Backend validation:
- Pydantic schema validates Food ranges and cross-field rules.
- Service layer revalidates merged update payloads.
- Duplicate checks run in service layer for create and update.

Arabic UI errors:
- Field-level Arabic errors are shown near fields.
- Form-level Arabic save/network errors preserve user input.
- Duplicate errors are mapped to the Food name field when returned by the API.

## 7. Duplicate Handling Status

Implemented.

Duplicate key:
- Normalized Food name.
- Nutrition basis.
- Default unit type.
- Unit amount.
- Unit basis.

Normalization:
- Trims whitespace.
- Collapses repeated spaces.
- Uses case-folded comparison for English.
- Arabic text is normalized by trimming/collapsing whitespace.

Deleted Foods:
- Do not block duplicate creation because hard-deleted Foods no longer exist in the catalog.

## 8. Hard Delete Status

Implemented.

Frontend:
- Delete requires confirmation.
- Dialog shows the Food name.
- Dialog states deletion is permanent.
- Cancel makes no changes.
- Confirm calls the API and disables the button while pending.
- Dialog supports Escape cancel and focus restoration.

Backend:
- `delete_food` permanently deletes the Food row.
- No archive/inactive fields or filters are used.

After delete:
- Food disappears from `/foods`.
- Food disappears from search because it is no longer in the catalog.
- Food disappears from future Diary selection because Diary uses the current Foods API list.

## 9. Diary Snapshot Safety Status

Implemented as a minimal compatibility adjustment.

Changed:
- New Diary snapshots preserve:
  - Food ID.
  - Food name.
  - Brand/category.
  - Nutrition basis.
  - Default unit fields.
  - Core nutrition values.
  - Optional nutrient values.
  - Notes/data source.
  - Logged quantity.
  - Calculated totals.
- Diary response totals are calculated from the snapshot.
- Diary UI displays snapshot/default-unit values without requiring the Food row.
- Legacy snapshot fields `serving_label`, `serving_grams`, and `total_sugars_g` remain supported only for old diary rows.

Not implemented in this Foods-only phase:
- Diary gram-mode UI.
- Diary `log_mode` API migration.
- Diary quantity-only edit.
- Diary delete confirmation.

## 10. Tests Added/Updated

Added:
- `backend/tests/test_foods.py`

Covered:
- Duplicate blocking with normalized name.
- Same Food name allowed when default unit differs.
- Duplicate creation allowed after hard delete.
- Optional nutrient cross-field validation.
- D-026 optional nutrient maximum ranges.
- Diary snapshot remains readable after Food hard delete.

Updated:
- `backend/tests/test_diary_snapshot.py`
  - Uses the new per-100g/default-unit Food model.
  - Verifies snapshot totals from default-unit quantity.

No frontend automated tests were added because the current frontend test framework is not set up.

## 11. Test Results

Passed:
- `npm run typecheck`
- `npm run build`
- `python -m pytest`
  - Result: `10 passed, 1 skipped`
- `python -m ruff check`
- `alembic upgrade head --sql` with PostgreSQL dialect
- Targeted forbidden-reference scans:
  - No `is_active`.
  - No `archived_at`.
  - No archive/inactive runtime requirement.
  - No Dexie/IndexedDB/sync queue references reintroduced.

Additional check:
- `git diff --check` against implementation-touched files passed.
- Full `git diff --check` still reports trailing whitespace in pre-existing BA docs that were not edited in this implementation because BA edits were explicitly out of scope.

## 12. Remaining Risks or Follow-Up Items

1. Frontend E2E tests are not present.
   - Impact: hard-delete dialog, standalone routing, mobile cards, and Arabic field errors need browser-level QA.
   - Recommended follow-up: add Playwright coverage for regenerated Foods test cases.

2. Migration was SQL-rendered for PostgreSQL but not executed against a live PostgreSQL database in this environment.
   - Impact: production migration should be tested against a real PostgreSQL instance before release.

3. Existing Food rows without `serving_grams` can only be migrated with best-effort defaults.
   - Impact: old catalog nutrition may need manual review after migration.

4. Diary gram-mode requirements remain out of this Foods-only phase.
   - Impact: Foods data model supports future gram/default-unit calculation, but Diary UI/API still uses the previous quantity flow.

5. Legacy snapshot compatibility keeps `serving_label`, `serving_grams`, and `total_sugars_g` in snapshot response types.
   - Impact: these are not v1 Food catalog fields and are intentionally kept only so old diary entries remain readable.

6. Some older BA/QA docs in the working tree still show pre-implementation alignment notes.
   - Impact: documentation cleanup may be useful later, but BA/QA edits were out of scope for this implementation.
