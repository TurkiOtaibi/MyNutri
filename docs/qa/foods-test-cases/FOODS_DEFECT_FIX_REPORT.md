# Foods v1 Defect Fix Report

Date: 2026-07-10
Scope: six defects identified by `FOODS-AUTO-001`
Environment: local frontend and backend with PostgreSQL `mynutri_dev`

## 1. Defects Fixed

| Test case | Defect | Resolution |
|---|---|---|
| `FOOD-TC-124` | Repeated delete confirmation sent two DELETE requests. | Added an immediate submission lock in the confirmation dialog. Repeated click or Enter events are ignored while deletion is active. |
| `FOOD-TC-059` | Food name above 120 characters was accepted. | Create and update schemas reject normalized names above 120 characters. Frontend validation and input constraints use the same limit. |
| `FOOD-TC-073` | Brand above 80 characters was accepted. | Create and update schemas reject normalized brands above 80 characters. Frontend validation and input constraints use the same limit. |
| `FOOD-TC-074` | Category above 80 characters was accepted. | Create and update schemas reject normalized categories above 80 characters. Frontend validation and input constraints use the same limit. |
| `FOOD-TC-149` | Notes above 500 characters were accepted. | Create and update schemas reject normalized notes above 500 characters. Frontend validation and textarea constraints use the same limit. |
| `FOOD-TC-150` | Data source above 120 characters was accepted. | Create and update schemas reject normalized data sources above 120 characters. Frontend validation and input constraints use the same limit. |

## 2. Files Changed

- `backend/app/schemas.py`
- `backend/app/services/food_validation_errors.py`
- `backend/tests/test_foods.py`
- `frontend/lib/food.ts`
- `frontend/components/FoodFormPage.tsx`
- `frontend/components/FoodDeleteDialog.tsx`
- `docs/qa/foods-test-cases/FOODS_DEFECT_FIX_REPORT.md`

No BA files, QA test-case definitions, product decisions, migrations, archive behavior, or offline/sync behavior were changed.

## 3. Validation Behavior Changed

- Added backend text limits in one `FOOD_TEXT_MAX` mapping for `name`, `brand`, `category`, `notes`, and `data_source`.
- Limits apply to both `FoodCreate` and `FoodUpdate` after whitespace normalization.
- Over-limit API responses use the existing structured field contract with code `above_max` and Arabic message `القيمة أعلى من الحد المسموح.`.
- Added frontend `foodTextMax` constants and matching validation in `validateFoodForm`.
- Form inputs expose matching `maxLength` constraints.
- Existing values at the exact maximum remain valid; values one character above are rejected.

## 4. Delete Double-Submit Behavior Changed

- The first confirm action synchronously sets a local submission lock before invoking the mutation.
- Confirm and Cancel are disabled while deletion is active.
- The confirm label changes to `جاري الحذف...`.
- Repeated click and Enter events are ignored while locked.
- Success continues to close/navigate or refresh through the existing mutation callbacks.
- Failure clears the lock after the mutation settles, re-enables the actions, and retains the existing Arabic error behavior.

## 5. Tests Run

| Check | Result |
|---|---|
| Targeted Playwright: `FOOD-TC-124`, `059`, `073`, `074`, `149`, `150` | 6 passed |
| Delete and validation Playwright regression subset | 45 passed |
| Full Foods Playwright suite | 151 passed; all 153 CSV IDs mapped |
| Focused backend Foods tests | 19 passed |
| Full backend test suite | 23 passed, 1 Future-Scope sync test skipped |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| Ruff | Passed |

The full Playwright report is available at `frontend/playwright-report/index.html`; the JSON result is at `frontend/test-results/foods-results.json`.

## 6. Test Results

- All six previously failing test cases now pass.
- No Foods Playwright regression failures remain.
- No backend regression failures remain.
- PostgreSQL contained zero Foods after automated cleanup.

## 7. Remaining Risks

- The automated browser run uses Chromium. The previously documented real Safari, iPhone Safari, Android Chrome, visual RTL, and assistive-technology confirmations remain manual.
- Backend tests emit the existing Starlette/httpx deprecation warning; it does not affect these fixes.
- No database column-length migration was added. Enforcement is intentionally at the API/schema and frontend layers requested for this defect scope.

## 8. Automation Status

Foods automation is green for this build: **151 of 151 Playwright tests passed**. The Foods implementation is ready for the remaining manual browser/device/accessibility checks.
