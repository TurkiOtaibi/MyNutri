# Foods Validation Fix Recheck

Status: Report-only targeted recheck
Date: 2026-07-10
Scope: Recheck the Foods Arabic API validation fix against `04_FOODS_IMPLEMENTATION_VERIFICATION_AUDIT.md`, `05_FOODS_ARABIC_API_VALIDATION_FIX_REPORT.md`, and current backend/frontend code.
Application code changed by this recheck: No.

## 1. Verdict

Verdict: Pass

The previous High implementation gap is resolved for in-scope Foods create/update validation failures. Food API validation errors now use a structured, mappable detail contract with Arabic messages, and the frontend Food form maps explicit `field` values before falling back to `loc`.

High gaps remaining: 0

Foods can proceed to PostgreSQL migration rehearsal and formal Manual QA.

## 2. Previous High Gap Recheck

Previous High gap:
- Direct Food API validation could return raw/default Pydantic English messages for core field failures such as `calories < 0`.

Current status: Resolved

Evidence:
- `backend/app/services/food_validation_errors.py` defines the Food-specific error contract and Arabic messages.
- `backend/app/api/routes/foods.py` validates create/update request bodies through `validate_food_payload(...)`.
- `backend/app/services/food.py` maps validation failures that happen after merging partial Food updates.
- `backend/tests/test_foods.py` includes API-level tests for required fields, invalid enums, numeric min/max errors, cross-field errors, optional nutrient max errors, duplicate Food errors, and update validation after merge.

## 3. Error Contract Verification

Current structured error detail shape:

```json
{
  "loc": ["body", "calories"],
  "field": "calories",
  "code": "below_min",
  "msg": "القيمة أقل من الحد المسموح.",
  "type": "greater_than_equal"
}
```

Contract status: Pass

Verified fields:
- `loc`: present and compatible with existing FastAPI-style field mapping.
- `field`: present for field-level errors.
- `code`: present and stable enough for QA/API assertions.
- `msg`: Arabic for known Food validation failures.
- `type`: present for original/framework or app error type.

## 4. Arabic Message Coverage

Status: Pass

Verified Arabic message constants in `backend/app/services/food_validation_errors.py`:
- Required field
- Invalid number
- Below minimum
- Above maximum
- Invalid select/enum option
- Whitespace-only Food name
- Duplicate Food
- Optional nutrient below 0
- Optional nutrient above max
- `fiber_g > carb_g`
- `added_sugar_g > sugar_g`
- `saturated_fat_g > fat_g`
- `trans_fat_g > fat_g`
- `saturated_fat_g + trans_fat_g > fat_g`

The code inspection confirmed these are stored as Arabic UTF-8 strings. Some PowerShell output renders Arabic as mojibake, but Python UTF-8 inspection showed the source strings are valid Arabic codepoints.

## 5. Frontend Mapping Verification

Status: Pass

Evidence:
- `frontend/components/FoodFormPage.tsx` now reads `item.field` when present.
- It falls back to `loc[loc.length - 1]` for backwards compatibility.
- It maps known fields to `FoodFormErrors`, so Arabic API field messages appear near the related Food form fields.
- Unknown or non-field 422 details fall back to the existing Arabic form-level validation message.
- Network/server failures still use the existing Arabic write failure message and do not queue or save locally.

## 6. Raw English Message Exposure

Status: Pass for in-scope Food form/API validation failures

Evidence:
- Known Food create/update validation failures are passed through `format_food_validation_errors(...)`.
- Numeric range errors are mapped to Arabic min/max messages instead of raw Pydantic messages.
- Enum errors are mapped to the Arabic invalid-select message.
- Unknown field/form-level validation errors use the Arabic generic validation message.
- Frontend Food form maps the backend structured `msg` value and otherwise shows Arabic generic errors.

Residual note:
- A severely malformed request body outside the normal Food form path may still be handled by FastAPI's generic request validation before reaching the Food-specific mapper. This is not a user-facing Foods form path and is not a remaining High gap for v1.

## 7. D-024 / D-025 / D-026 Alignment

| Decision | Recheck status | Evidence |
|---|---:|---|
| D-024 Add Food standalone page | Still aligned | `/foods/new`, `/foods/:id`, `/foods/:id/edit` routes remain implemented; this fix did not alter page structure. |
| D-025 Food permanent hard delete | Still aligned | `DELETE /foods/{food_id}` still calls `delete_food`; no archive behavior found. |
| D-026 optional nutrient validation ranges | Still aligned | D-026 messages and field validators remain in schema/helper; tests cover optional nutrient max and cross-field rules. |
| Per 100g/per 100ml source of truth | Still aligned | No serving-based source-of-truth change introduced. |

## 8. Archive/Inactive Regression Scan

Status: Pass

Scan result:
- No `is_active`, `archived_at`, Active/Archived filter, or archive/inactive runtime behavior was found in current backend/frontend/test implementation paths.

## 9. Offline/Sync Regression Scan

Status: Pass

Scan result:
- No Dexie/IndexedDB runtime dependency, mutation queue, pending sync UI, `SyncStatus`, saved-locally/will-sync-later messaging, or `/sync` backend route was found in current backend/frontend/test implementation paths.

## 10. Tests Reviewed / Run

Commands run during this recheck:

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
- `fastapi.testclient` emits an upstream `StarletteDeprecationWarning` about `httpx`. This does not affect Foods validation behavior.

Build note:
- `npm run build` temporarily updated generated `frontend/next-env.d.ts`; it was restored so this recheck does not leave application-code changes.

## 11. Remaining Non-High Notes

These are not blockers for the validation fix:
- Frontend component/E2E tests are still not present for browser-level Food form error rendering.
- Manual QA is still required for mobile RTL, visual field placement, and accessibility behavior.
- PostgreSQL migration rehearsal is still pending.
- Duplicate Food blocking remains service-level rather than database-enforced.

## 12. Final Recommendation

The Foods Arabic API validation fix is verified. Proceed to:

1. PostgreSQL migration rehearsal against representative existing Food and Diary data.
2. Formal Manual QA for Foods.
3. Browser-level checks for Arabic field errors, delete dialog behavior, mobile RTL layout, and accessibility basics.
