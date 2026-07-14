# Foods Arabic API Validation Fix Report

Status: Implemented
Scope: Fix only the remaining high implementation gap from `04_FOODS_IMPLEMENTATION_VERIFICATION_AUDIT.md`: Food API validation errors leaking default Pydantic/English messages.
Application code changed: Yes, limited to Food API validation/error mapping and targeted tests.
BA files changed: No.
QA files changed: No.
Committed: No.

## 1. Summary of Fix

Food create/update API validation now returns structured Arabic validation details for known Food v1 failures instead of exposing raw Pydantic English messages.

The fix keeps the existing FastAPI-style `detail` list shape and extends each item with:

- `loc`: compatible location array, e.g. `["body", "calories"]`
- `field`: direct field name, e.g. `calories`
- `code`: stable application error code, e.g. `below_min`
- `msg`: Arabic user-facing message
- `type`: original or application error type

Food create/update routes now validate raw request JSON through a Food-specific mapper before calling services. Food update also maps validation errors that occur after merging partial updates with the existing Food record.

## 2. Files Changed

Backend:
- `backend/app/services/food_validation_errors.py`
- `backend/app/api/routes/foods.py`
- `backend/app/schemas.py`
- `backend/app/services/food.py`
- `backend/tests/test_foods.py`

Frontend:
- `frontend/components/FoodFormPage.tsx`

Documentation:
- `docs/implementation/05_FOODS_ARABIC_API_VALIDATION_FIX_REPORT.md`

## 3. Error Contract Used

Example response detail item:

```json
{
  "loc": ["body", "calories"],
  "field": "calories",
  "code": "below_min",
  "msg": "القيمة أقل من الحد المسموح.",
  "type": "greater_than_equal"
}
```

Duplicate Food response detail:

```json
{
  "loc": ["body", "name"],
  "field": "name",
  "code": "duplicate_food",
  "msg": "هذا الطعام موجود مسبقًا بنفس الوحدة.",
  "type": "value_error.duplicate_food"
}
```

Frontend mapping:
- Uses `field` when present.
- Falls back to the existing `loc` behavior for compatibility.
- Unknown/non-field failures still show the existing Arabic form-level error.
- Network/API/server failures still use the existing Arabic form-level message and do not queue or save locally.

## 4. Arabic Messages Covered

Covered Food API validation failures:

- Required Food fields: `هذا الحقل مطلوب.`
- Whitespace-only Food name: `اسم الطعام مطلوب.`
- Invalid select/enum values: `اختر قيمة صحيحة.`
- Invalid numeric format: `أدخل رقمًا صحيحًا.`
- Below minimum / negative values: `القيمة أقل من الحد المسموح.`
- Above maximum values: `القيمة أعلى من الحد المسموح.`
- Duplicate Food: `هذا الطعام موجود مسبقًا بنفس الوحدة.`
- Optional nutrient below 0: `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.`
- Optional nutrient above max: `القيمة الغذائية الإضافية أعلى من الحد المسموح.`
- `fiber_g > carb_g`: `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.`
- `added_sugar_g > sugar_g`: `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.`
- `saturated_fat_g > fat_g`: `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- `trans_fat_g > fat_g`: `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- `saturated_fat_g + trans_fat_g > fat_g`: `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.`

## 5. Tests Added / Updated

Updated `backend/tests/test_foods.py` with API-level coverage for:

- Missing required Food fields.
- Invalid nutrition basis / unit basis enum values.
- Negative core nutrition values.
- Above-max core nutrition values.
- Whitespace-only Food name.
- Unit amount less than or equal to 0.
- Field-level cross-field errors.
- Optional nutrient above maximum.
- Structured duplicate Food error.
- Update validation for directly invalid fields.
- Update validation after merging partial edit data with the existing Food record.

Existing service/schema tests still cover:
- Duplicate blocking by normalized key.
- Same Food name with different default unit allowed.
- Duplicate recreation after hard delete.
- D-026 optional nutrient validation.
- Diary snapshot survival after Food hard delete.

Frontend automated tests were not added because the frontend test framework is not currently set up. The frontend mapper was hardened to support the explicit `field` property.

## 6. Test Results

Required checks run:

```text
backend: python -m pytest
Result: 18 passed, 1 skipped, 1 warning

backend: python -m ruff check
Result: passed

frontend: npm run typecheck
Result: passed

frontend: npm run build
Result: passed
```

Warning:
- `fastapi.testclient` emits an upstream `StarletteDeprecationWarning` about `httpx`; this is from the installed test client dependency and not from the Food validation implementation.

## 7. Remaining Risks

1. Frontend Foods behavior still needs manual QA for browser rendering, field display, and accessibility behaviors.
2. No frontend component/E2E tests exist for the Food form error rendering.
3. Duplicate blocking remains service-level and is not backed by a database unique constraint.
4. PostgreSQL migration rehearsal is still pending and should run before release.

## 8. Gap Resolution Status

High gap from `04_FOODS_IMPLEMENTATION_VERIFICATION_AUDIT.md`: Resolved.

Food API validation failures now produce structured Arabic field-level or form-level details that the frontend can display without exposing raw Pydantic/English messages.

Foods can proceed to PostgreSQL migration rehearsal and formal manual QA.
