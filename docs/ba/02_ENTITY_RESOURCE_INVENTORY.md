# Entity and Resource Inventory

This inventory separates v1 requirements from current implementation evidence and Future Scope behavior.

## Profile

| Attribute | Value |
|---|---|
| v1 status | Confirmed |
| Purpose | Store the single user's stats and goal for target calculation. |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `frontend/components/ProfilePage.tsx` |
| API routes | `GET /profile`, `PUT /profile`, `POST /profile/preview` |
| Relationships | Used by target preview and weekly target display. |
| Current implementation gap | Validation ranges in code are looser/different than D-009 and D-012. |

Fields:
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

v1 requirements:
- v1 uses one Profile model only.
- Multi-profile/person switching is Future Scope.
- Profile reset/delete is out of scope; correction happens by editing existing fields.
- Birth date cannot be future.
- Age must be 10-100.
- Height must be 100-250 cm.
- Weight must be 20-300 kg.
- Protein per kg must be 1.0-3.0.
- Fat percentage must be 15%-40%.
- Save succeeds only after API success.
- Failed save is not queued or saved locally.

## TargetResponse

| Attribute | Value |
|---|---|
| v1 status | Confirmed |
| Purpose | Return calculated calories/macros from profile inputs. |
| Evidence | `backend/app/services/calc.py`, `backend/app/schemas.py` |
| Stored? | No |

Fields:
- `bmr`
- `tdee`
- `target_calories`
- `protein_g`
- `carb_g`
- `fat_g`
- `carb_clamped`

## Current Food Entity - D-024/D-025

This section supersedes older Food entity rows that treat archive/inactive fields or serving-based nutrition as v1 source of truth.

| Attribute | Requirement |
|---|---|
| Entity | Food |
| Purpose | Current catalog item used for future Diary logging. Deleted Foods are permanently removed from the catalog. |
| Routes | `/foods`, `/foods/new`, `/foods/:id`, `/foods/:id/edit` |
| API routes | `GET /foods`, `POST /foods`, `GET /foods/{id}`, `PUT /foods/{id}`, `DELETE /foods/{id}` |
| Nutrition source of truth | Values per 100g or per 100ml. |
| Required fields | `name`, `nutrition_basis`, `calories`, `protein_g`, `carb_g`, `fat_g`, `default_unit_type`, `unit_amount`, `unit_basis` |
| Optional basic fields | `brand`, `category`, `notes`, `data_source` |
| Optional nutrients | `fiber_g`, `sugar_g`, `added_sugar_g`, `saturated_fat_g`, `trans_fat_g`, `sodium_mg`, `cholesterol_mg`, `potassium_mg`, `calcium_mg`, `iron_mg`, `magnesium_mg`, `zinc_mg`, `vitamin_d_mcg`, `vitamin_b12_mcg`, `vitamin_c_mg`, `vitamin_a_mcg`, `folate_mcg`, `vitamin_k_mcg` |
| Delete lifecycle | Permanent hard delete with confirmation; no archive/inactive status in v1. |
| Duplicate key | Current-catalog normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`. |
| Diary dependency | Existing Diary entries remain readable through frozen snapshots after Food deletion. |
| Current implementation gap | Current code uses serving-based fields, lacks standalone Food routes, lacks D-025 fields, and hard deletes without required confirmation/copy. |

Out of v1 for Food:
- `is_active`
- `archived_at`
- Archived status.
- Active/Archived filters.
- Restore.

## Legacy Food

The legacy Food inventory below is retained for code-evidence history only. It is not a current v1 requirement source. If it conflicts with the D-024/D-026 section above, the current section controls v1 requirements.

## Food

| Attribute | Value |
|---|---|
| v1 status | Legacy evidence / superseded where it conflicts with D-024, D-025, or D-026 |
| Purpose | Historical evidence for the earlier serving-based catalog model. Current v1 uses the Food section above. |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `frontend/components/FoodsPage.tsx` |
| API routes | `GET /foods`, `POST /foods`, `GET /foods/{id}`, `PUT /foods/{id}`, `DELETE /foods/{id}` |
| Relationships | Referenced by Diary at creation time; nutrition snapshot preserves history. |
| Current implementation gap | Current code uses serving-based fields, lacks D-025 fields, lacks duplicate check, lacks D-026 optional nutrient validation, and hard deletes without required confirmation/copy. |

Current fields:
- `id`
- `name`
- `serving_label`
- `serving_grams`
- `calories`
- `protein_g`
- `carb_g`
- `fat_g`
- `saturated_fat_g`
- `trans_fat_g`
- `cholesterol_mg`
- `sodium_mg`
- `fiber_g`
- `total_sugars_g`
- `added_sugar_g`
- `created_at`
- `updated_at`

Superseded fields not required in v1:
- `is_active`
- `archived_at`

Legacy naming note:
- `serving_grams` was used by the older serving-based model. D-025 replaces this as Food source of truth with per-100g/per-100ml nutrition plus default unit fields.
- Long food names still show up to two lines with ellipsis in lists/cards and full text in details/edit views.

Derived response field:
- `net_carbs_g = carb_g - fiber_g`

v1 lifecycle:
- D-025 supersedes the earlier archive behavior.
- v1 uses permanent Food hard delete after confirmation.
- Deleted Foods no longer exist in the catalog and do not block duplicate creation.
- Existing Diary entries remain readable through snapshots.

## DiaryEntry

| Attribute | Value |
|---|---|
| v1 status | Confirmed / needs gram and edit alignment |
| Purpose | Store what was eaten on a date. |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `frontend/components/DiaryPage.tsx` |
| API routes | `GET /diary`, `GET /diary/{id}`, `POST /diary`, `PUT /diary/{id}`, `DELETE /diary/{id}` |
| Relationships | Has nullable `food_id`; owns `nutrition_snapshot`. |
| Current implementation gap | Current create uses serving quantity only and lacks D-021 `log_mode`; update API allows food/date changes, but v1 permits quantity-only edit. |

Current fields:
- `id`
- `entry_date`
- `food_id`
- `log_mode` (required v1 field: `servings` or `grams`)
- `quantity`
- `nutrition_snapshot`
- `created_at`

Required v1 behavior:
- Create request payload is `{ entry_date, food_id, log_mode, quantity }`.
- If `log_mode="servings"`, `quantity` means serving count and must be 0.01-50.
- If `log_mode="grams"`, `quantity` means grams and must be 1-5000, and the selected current-catalog Food must have nutrition basis/default-unit data that supports an unambiguous gram calculation.
- A separate persisted `grams` field is not part of v1.
- Future dates are blocked.
- Edit payload is `{ quantity }` only.
- `log_mode`, Food, date, and per-serving snapshot values are not editable after creation.
- Edit recalculates `serving_multiplier` and `nutrition_snapshot.calculated_totals` from the original snapshot and new mode-specific quantity.
- Failed writes are not queued or saved locally.

## NutritionSnapshot

| Attribute | Value |
|---|---|
| v1 status | Confirmed / needs gram-mode implementation alignment |
| Purpose | Freeze nutrition values at log time so history does not change after Food edits or permanent Food deletion. |
| Evidence | `backend/app/services/diary.py`, `backend/tests/test_diary_snapshot.py` |

v1 behavior:
- Snapshot stores food identity at log time, `log_mode`, `logged_quantity`, per-serving nutrition values, `serving_multiplier`, and calculated totals.
- Serving-mode snapshot uses `serving_multiplier = quantity`.
- Legacy superseded by D-025: earlier gram snapshots used `serving_grams`; v1 now calculates from nutrition basis/default-unit snapshot data.
- Day and weekly totals use `nutrition_snapshot.calculated_totals`, not the current Food row.
- User cannot manually edit snapshot.

## WeekSummary

| Attribute | Value |
|---|---|
| v1 status | Confirmed |
| Purpose | Aggregate Diary totals Sunday through Saturday. |
| Evidence | `backend/app/services/aggregation.py`, `frontend/components/DiaryPage.tsx` |

v1 behavior:
- Week is Sunday through Saturday.
- Future Diary creation is blocked, but viewing a week containing future days is allowed with zero/future-day totals as applicable.
- API read failures use exact D-022 weekly summary copy: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`

## Auth Token

| Attribute | Value |
|---|---|
| v1 status | Confirmed |
| Purpose | Protect personal API data for single owner. |
| Evidence | `backend/app/core/auth.py` |

v1 behavior:
- Protected routes require valid bearer token unless token is configured empty in development.
- 401 response maps to Arabic access/session error.

## Service Worker

| Attribute | Value |
|---|---|
| v1 status | Constrained shell-only or recommended removal |
| Purpose | Optional installable shell support only. |
| Evidence | `frontend/public/service-worker.js`, `Providers.tsx` |

v1 requirement:
- Must not cache personal nutrition API data.
- Must not provide offline data behavior.

## Future Scope: SyncOperation and QueuedMutation

| Resource | v1 status | Evidence | Notes |
|---|---|---|---|
| `SyncOperation` | Future Scope | `backend/app/schemas.py`, `backend/app/api/routes/sync.py` | Not a v1 product requirement. |
| `QueuedMutation` | Future Scope | `frontend/lib/db.ts`, `frontend/lib/types.ts` | Failed writes must not be queued in v1. |
| IndexedDB personal data stores | Future Scope | `frontend/lib/db.ts` | Must not be source of truth in v1. |
| Offline page / cached-read fallback behavior | Future Scope / implementation alignment | `frontend/app/offline/page.tsx`, `frontend/lib/db.ts`, `frontend/public/service-worker.js` | Existing offline/cached-read artifacts must not provide v1 personal data source-of-truth behavior. |
