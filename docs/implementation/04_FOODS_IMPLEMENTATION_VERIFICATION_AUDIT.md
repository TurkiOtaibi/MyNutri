# Foods Implementation Verification Audit

Status: Report-only verification
Date: 2026-07-09
Scope: Foods v1 implementation against finalized BA decisions, regenerated Foods QA test cases, migration files, and current frontend/backend code.
Application code changed by this audit: No.

## 1. Overall Verdict

Verdict: Pass with notes

The Foods v1 implementation substantially matches the finalized BA decisions and regenerated Foods test baseline. The core product decisions are implemented: standalone Food pages, permanent hard delete, per-100g/per-100ml nutrition source of truth, D-026 optional nutrient ranges, duplicate blocking, no archive/inactive state, and minimal Diary snapshot safety after Food hard delete.

Manual QA can start, but one high implementation gap remains: direct backend/API validation for core numeric bounds still uses default Pydantic English messages for some failures. The frontend Food form has Arabic field-level validation, but API-level negative tests can still receive English validation messages for fields such as `calories < 0`.

Critical implementation gaps: 0
High implementation gaps: 1
Manual QA readiness: Ready with focused notes
Commit recommendation: Do not commit as final until the API Arabic validation-message gap is fixed or explicitly accepted.

## 2. BA Decision Compliance

| Decision / Requirement | Status | Evidence | Notes |
|---|---:|---|---|
| D-024 Add Food standalone page | Covered | `frontend/app/foods/new/page.tsx`, `frontend/app/foods/[id]/page.tsx`, `frontend/app/foods/[id]/edit/page.tsx`, `frontend/components/FoodFormPage.tsx` | `/foods` is list-only; Add button links to `/foods/new`. |
| D-025 Food permanent hard delete | Covered | `backend/app/services/food.py:173`, `backend/app/api/routes/foods.py:34`, `frontend/components/FoodDeleteDialog.tsx` | Uses `session.delete(food)` and 204 response. No archive flow found. |
| D-026 optional nutrient ranges | Covered | `backend/app/schemas.py:37`, `frontend/lib/food.ts:89`, `backend/tests/test_foods.py:75` | Backend and frontend cover max ranges and cross-field rules. |
| Per 100g / per 100ml source of truth | Covered | `backend/app/models.py:85`, `frontend/lib/types.ts:4`, `frontend/components/FoodFormPage.tsx:149` | `nutrition_basis` is required and displayed. |
| No archive/inactive behavior | Covered | `rg is_active/archived_at/archive/inactive` returned no app/backend/test matches | No `is_active`, `archived_at`, status column, or active/archived filter in current implementation paths. |
| No offline/sync behavior reintroduced | Covered | `rg Dexie/IndexedDB/SyncStatus/pending sync` returned no app/backend/test matches; `frontend/lib/api.ts:34` uses `cache: "no-store"` | Service worker is shell-only; no write queue or sync UI found. |
| `sugar_g` is total sugar | Covered | `frontend/lib/types.ts:48`, `frontend/components/FoodFormPage.tsx:214`, `backend/app/models.py:100` | `total_sugars_g` is not exposed on Food forms/details. |
| `added_sugar_g` is added sugar | Covered | `frontend/lib/types.ts:49`, `frontend/components/FoodFormPage.tsx:215`, `backend/app/models.py:101` | Cross-field validation applies only when both sugar fields are present. |
| `total_sugars_g` legacy only | Covered | `backend/app/schemas.py:284`, `backend/app/services/diary.py:84`, `frontend/lib/types.ts:88` | Present only in Diary snapshot compatibility/totals, not Food input/response UI. |
| Duplicate Food blocking | Covered | `backend/app/services/food.py:88`, `backend/app/services/food.py:112`, `backend/tests/test_foods.py:46` | Key uses normalized name, nutrition basis, default unit type, unit amount, and unit basis. |
| Food delete confirmation | Covered | `frontend/components/FoodDeleteDialog.tsx:41` | Dialog shows food name and permanent-delete copy. |
| Deleted Food disappears from list/search/future Diary selection | Covered by design; needs browser QA | `DELETE /foods/{id}` hard deletes; list/search use current `Food` table; Diary selector uses `listFoods()` | Needs manual flow confirmation after API-backed delete. |
| Diary snapshot remains readable after Food delete | Covered | `backend/app/models.py:134`, `backend/app/services/diary.py:40`, `backend/tests/test_foods.py:96` | `food_id` nullable with `ON DELETE SET NULL`; snapshot stores display/nutrition data. |
| Optional nutrients collapsed by default | Covered | `frontend/components/FoodFormPage.tsx:210` | `<details>` has no default `open`; opens when optional field errors exist. |
| Arabic validation/error messages | Partially covered | `frontend/lib/food.ts:84`, `backend/app/schemas.py:101`, `backend/app/services/food.py:47` | Frontend and custom backend validators are Arabic; core Pydantic bound errors remain English. |
| Mobile RTL behavior | Partially covered; needs manual QA | `frontend/app/layout.tsx:23`, `frontend/app/globals.css:661`, `frontend/app/globals.css:446` | RTL is set globally; mobile card CSS and two-line name clamp implemented. Needs viewport verification. |
| Accessibility basics | Partially covered | `frontend/components/FoodFormPage.tsx:317`, `frontend/components/FoodDeleteDialog.tsx:43`, `frontend/components/FoodsPage.tsx:200` | Field associations and dialog labels exist; focus-first-invalid is not implemented. |
| Network/API failure behavior | Covered; needs manual QA | `frontend/lib/api.ts:44`, `frontend/components/FoodsPage.tsx:89`, `frontend/components/FoodFormPage.tsx:83` | Failed writes are not queued and input remains in component state. |

## 3. Test Case Coverage Status

Regenerated Foods test cases reviewed: 142
P0 test cases: 83
Source: `docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv`

| Major test area | Implementation status | Evidence | Notes |
|---|---:|---|---|
| Standalone Foods routes | Covered | `/foods`, `/foods/new`, `/foods/[id]`, `/foods/[id]/edit` pages exist | Needs live navigation smoke test. |
| Food list, columns, mobile cards | Covered / needs visual QA | `FoodsPage.tsx`, `globals.css` | Table/card switching and long-name truncation should be verified at 360/390/430/768 widths. |
| Food search and no-results | Covered | `frontend/lib/api.ts:85`, `backend/app/services/food.py:129`, `FoodsPage.tsx:177` | Exact/partial Arabic-English search needs manual/API QA. |
| Food create/edit/details | Covered | `FoodFormPage.tsx`, `FoodDetailsPage.tsx`, `backend/app/api/routes/foods.py` | Save failure preserves current form state. |
| Food hard delete | Covered | `FoodDeleteDialog.tsx`, `useFoodDelete.ts`, backend `delete_food` | Dialog accessibility and stale delete need browser/API verification. |
| Duplicate blocking | Covered | `backend/tests/test_foods.py:46`, `FoodFormPage.tsx:267` | No database unique constraint, so concurrent duplicate race remains a low/medium backend risk. |
| D-026 optional nutrients | Covered | Frontend and backend validators plus backend tests | Direct API messages for core numeric bounds are not fully Arabic. |
| Sugar mapping | Covered | `sugar_g` in Food model/types/UI; `total_sugars_g` only in snapshots | Legacy snapshot compatibility preserved. |
| Diary snapshot after Food delete | Covered | `backend/tests/test_foods.py:96`, `backend/app/services/diary.py:40` | Existing historical snapshots should remain readable. |
| Online-only behavior | Covered | No Dexie/sync markers; `apiFetch` uses `cache: "no-store"` | Service worker caches shell/navigation only, not API data. |
| Arabic/RTL/mobile/a11y | Partially covered / needs manual QA | Arabic labels/messages, RTL layout, ARIA field wiring | Focus-first-invalid and live-region severity need targeted QA. |

## 4. Migration Risk Assessment

Migration file reviewed: `backend/alembic/versions/0002_foods_v1_per_basis.py`

| Check | Status | Evidence / Risk |
|---|---:|---|
| Migration renders for PostgreSQL | Passed | `alembic upgrade head --sql` completed successfully; generated SQL size 12,434 bytes. |
| Safe defaults for existing Food rows | Mostly covered | Adds server defaults for `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis` before removing defaults. |
| Best-effort conversion from old serving data | Covered with risk | `serving_grams` rows are converted to per-100 values; rows without valid `serving_grams` default to 100g and may need manual review for nutrition accuracy. |
| Removing `serving_label`, `serving_grams`, `total_sugars_g` does not break Food code | Covered | Current Food model/types/forms no longer use them. |
| Legacy Diary snapshot display after removed Food columns | Covered | Legacy fields remain in `NutritionSnapshot`; `DiaryPage` still falls back to `snapshot.serving_label`. |
| Production migration rehearsal | Not verified | SQL render passed, but no live PostgreSQL upgrade/downgrade rehearsal was run in this audit. |

Migration risks:
- Existing Food rows without reliable `serving_grams` will be treated as per 100g with `unit_amount = 100`; nutrition values may require data review.
- No database-level duplicate constraint exists, so duplicate blocking is service-level and can race under simultaneous requests.
- Downgrade recreates old columns as best effort and should not be relied on as a data-fidelity rollback without a backup.

## 5. Runtime / Manual Verification Needed

Manual QA should verify these before final commit/release:

1. `/foods`, `/foods/new`, `/foods/:id`, and `/foods/:id/edit` navigation in a real browser.
2. Food delete confirm/cancel/confirm flows, including stale repeated delete.
3. Deleted Food no longer appears in list/search and future Diary Food selection.
4. Existing Diary entries remain readable after Food hard delete.
5. Mobile viewports: 360px, 390px, 430px, 768px, desktop.
6. Mixed Arabic/English long Food names in list cards/table and details/edit pages.
7. Optional nutrients are collapsed by default and open when invalid optional fields exist.
8. Keyboard flow through delete dialog, Escape cancel, and focus return.
9. Network/API failures for list, detail, create, edit, and delete.
10. Direct API negative validation responses for Arabic-message consistency.

## 6. Implementation Gaps

### GAP-FOOD-001 - Core API numeric validation messages are not fully Arabic

Severity: High
Area: Backend validation / API error behavior
Evidence:
- `backend/app/schemas.py:74-79` uses Pydantic `Field(gt/ge/le)` for core fields without custom Arabic messages.
- Direct validation of `calories = -1` returns `Input should be greater than or equal to 0`.

Impact:
Direct API clients, missed frontend validation paths, or automated API tests can receive English validation messages, while BA and test cases require Arabic validation/error messages.

Recommended fix:
Add API-level Arabic validation mapping for required/core numeric/enum validation errors, or add a FastAPI validation exception handler that maps known Food validation failures to approved Arabic messages.

### GAP-FOOD-002 - Focus-first-invalid behavior is not implemented

Severity: Medium
Area: Accessibility / form UX
Evidence:
- `frontend/components/FoodFormPage.tsx:111-121` sets errors and note but does not focus the first invalid field.
- Field-level `aria-invalid` and `aria-describedby` are implemented at `FoodFormPage.tsx:317`, `370`, and `404`.

Impact:
BA accessibility criteria and regenerated QA case `FOOD-TC-135` expect invalid-field focus behavior. Manual keyboard/screen-reader QA may fail this item.

Recommended fix:
After validation failure, expand the optional section if needed, then focus the first invalid input by field ID or ref.

### GAP-FOOD-003 - Error live-region roles are inconsistent for write failures

Severity: Medium
Area: Accessibility / async errors
Evidence:
- `FoodFormPage.tsx:161` uses `role="alert"` only when `hasFoodErrors(errors)` is true; network write failures use `role="status"`.
- `FoodsPage.tsx:82` and `FoodDetailsPage.tsx:79` display delete errors in status regions.

Impact:
Screen reader announcement behavior for destructive/write failures may be too passive.

Recommended fix:
Use `role="alert"` or assertive live region for write/delete failures and validation errors; reserve `role="status"` for loading/success.

### GAP-FOOD-004 - No automated frontend/E2E coverage for Foods UI

Severity: Medium
Area: Test coverage
Evidence:
- Backend tests cover service/schema behavior.
- No Playwright/component test files were found for the new Foods pages.

Impact:
Mobile cards, RTL layout, route navigation, dialog behavior, and browser API failure states depend on manual QA until UI tests are added.

Recommended fix:
Add component/E2E tests after manual QA stabilizes the UI behavior.

### GAP-FOOD-005 - Duplicate blocking is not database-enforced

Severity: Low to Medium
Area: Backend data integrity
Evidence:
- `ensure_not_duplicate` scans existing Foods in `backend/app/services/food.py:112`.
- No database unique index exists for normalized duplicate key.

Impact:
Concurrent create requests could create duplicates despite service-level validation.

Recommended fix:
Accept for personal-use v1 if low risk, or add a generated normalized key/unique constraint in a later hardening pass.

## 7. Regression Risks

| Risk | Severity | Notes |
|---|---:|---|
| Existing Food data with unknown serving weight may be migrated as per 100g inaccurately. | Medium | Requires backup and spot-check after migration. |
| Existing Diary snapshots with old fields need production data verification. | Medium | Code supports legacy snapshot fields; run manual historical-entry checks. |
| Service worker can serve shell pages offline. | Low | This is allowed as shell-only behavior; API data is not cached as source of truth. |
| Diary update service still allows broader update fields. | Medium / out of Foods scope | Not changed by Foods implementation; keep for later Diary phase. |
| Accessibility details may fail stricter screen-reader tests. | Medium | Focus-first-invalid and assertive error announcements need follow-up. |

## 8. Tests Reviewed / Run

Commands run during this audit:

```text
frontend: npm run typecheck
Result: passed

backend: python -m pytest
Result: 10 passed, 1 skipped

backend: python -m ruff check
Result: passed

backend: alembic upgrade head --sql
Result: passed; SQL rendered successfully
```

Relevant backend test coverage:
- `backend/tests/test_foods.py`
- `backend/tests/test_diary_snapshot.py`

Skipped test:
- `backend/tests/test_sync.py` is skipped as Future Scope / offline-sync behavior.

## 9. Can Foods Move to Manual QA?

Yes. Foods can move to formal manual QA with the notes above.

Manual QA should not treat the implementation as final-release ready until:
- API Arabic validation-message behavior is fixed or explicitly accepted.
- Mobile RTL and accessibility flows are browser-verified.
- A PostgreSQL migration rehearsal is completed against realistic existing Food and Diary data.

## 10. Commit Recommendation

Do not commit as final yet if the standard is full BA/test-case compliance. The implementation is ready for manual QA, but the API Arabic validation-message gap should be fixed or accepted before a final commit.

If the team wants a checkpoint commit before manual QA, label it clearly as an implementation checkpoint, not release-ready.
