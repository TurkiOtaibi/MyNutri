# Error Message Matrix

Most field-level error messages are missing as product-owned Arabic copy. Current behavior relies on browser validation, backend Pydantic/FastAPI responses, or generic notes.

## Confirmed Messages and Notes

| Scenario | Message source | Message behavior | Evidence | Confidence |
|---|---|---|---|---|
| Invalid/missing API token | Backend JSON detail | `"Invalid or missing single-user token."` | `backend/app/core/auth.py` | High |
| Missing profile | Backend 404 detail; frontend converts to `null` | `"Profile not found."`; UI shows target prompt through no targets | `profile.py`, `api.ts`, `TargetStrip` | High |
| Food not found | Backend 404 detail | `"Food not found."` | `services/food.py` | High |
| Diary entry not found | Backend 404 detail | `"Diary entry not found."` | `services/diary.py` | High |
| Save profile success | Inline note | Arabic success note | `ProfilePage` | High |
| Save profile connection failure | Required v1 message | Show clear connection error; do not save or queue | Product decision; current `ProfilePage` behavior needs alignment | High |
| Save food success | Inline note | Arabic success note | `FoodsPage` | High |
| Save food connection failure | Required v1 message | Show clear connection error; do not save or queue | Product decision; current `FoodsPage` behavior needs alignment | High |
| Delete food success | Inline note | Arabic delete success note | `FoodsPage` | High |
| Delete food connection failure | Required v1 message | Show clear connection error; do not delete locally or queue | Product decision; current `FoodsPage` behavior needs alignment | High |
| No foods for diary | Inline note/state | Arabic note tells user to add foods first | `DiaryPage` | High |
| Add diary success | Inline note | Arabic success note | `DiaryPage` | High |
| Add diary connection failure | Required v1 message | Show clear connection error; do not create a local entry or queue | Product decision; current `DiaryPage` behavior needs alignment | High |
| Delete diary success | Inline note | Arabic delete success note | `DiaryPage` | High |
| Optional installable shell unavailable/offline page | Future Scope / not v1 data behavior | May explain connection problem, but must not imply offline writes are supported | `frontend/app/offline/page.tsx` | Medium |
| Sync status | Future Scope / out of v1 | Pending/syncing labels are not v1 requirements | `SyncStatus` | High |

## Missing Field-Level Arabic Messages

| Field/scenario | Required message status | Evidence | Severity |
|---|---|---|---|
| Profile invalid height | Missing | `ProfilePage`, `ProfileUpsert` | Medium |
| Profile invalid weight | Missing | `ProfilePage`, `ProfileUpsert` | Medium |
| Profile invalid advanced ranges | Missing | `ProfilePage`, `ProfileUpsert` | Medium |
| Food name empty | Missing custom Arabic message | `FoodsPage`, `FoodBase.name` | High |
| Food serving label empty | Missing custom Arabic message | `FoodsPage`, `FoodBase.serving_label` | High |
| Food required numeric blank | Missing; current defaults can become 0 | `FoodsPage` | High |
| Food negative nutrients | Missing custom Arabic message | `FoodBase` | High |
| Food `serving_grams=0` | Missing clear message | UI/backend mismatch | Medium |
| Food duplicate | Missing; rule not implemented | Root Foods docs | High |
| Food `fiber_g > carb_g` | Missing; rule not implemented | Root Foods docs | High |
| Diary invalid quantity | Missing custom Arabic message | `DiaryPage`, `DiaryEntryCreate` | High |
| Diary food deleted/not found | Missing user-facing recovery | `create_entry`, `DiaryPage` | Medium |
| API unreachable / connection error | Missing required v1 message | Product decision | High |
| Unauthorized API request | Missing user-facing message | `apiFetch`, protected APIs | Medium |

## Requirements for Future Error Copy

Every form-level and field-level validation error should define:

- Arabic message.
- Trigger.
- Placement near the field when field-specific.
- Screen reader behavior.
- Whether input is preserved.
- Whether a network error should keep input visible for retry.
- Confirmation that invalid data is not saved locally or queued.

High-priority messages to write first:

1. Food name is required.
2. Serving label is required.
3. Calories/protein/carbs/fat are required and must be non-negative.
4. Serving grams must be greater than 0 when provided.
5. Fiber cannot exceed carbs.
6. This food already exists.
7. Quantity must be greater than 0.
8. Cannot connect to the server. Check your connection and try again.
9. Your changes were not saved because the server could not be reached.
10. Authorization failed; check the configured single-user token.

## Future Scope Messages

Offline cache, queued mutations, pending sync, sync rejection, stale cache, and conflict messages are explicitly Future Scope and should not be required for v1 QA coverage.
