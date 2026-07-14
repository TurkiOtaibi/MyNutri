# Validation Rules

This file defines v1 validation behavior. Current code may be looser; those differences are implementation alignment items.

## Global Rules

| Area | Rule | Arabic message |
|---|---|---|
| Required field | Empty required field is invalid. | `ظ‡ط°ط§ ط§ظ„ط­ظ‚ظ„ ظ…ط·ظ„ظˆط¨.` |
| Invalid number | Non-numeric or malformed numeric input is invalid. | `ط£ط¯ط®ظ„ ط±ظ‚ظ…ظ‹ط§ طµط­ظٹط­ظ‹ط§.` |
| Below minimum | Value lower than allowed minimum is invalid. | `ط§ظ„ظ‚ظٹظ…ط© ط£ظ‚ظ„ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.` |
| Above maximum | Value higher than allowed maximum is invalid. | `ط§ظ„ظ‚ظٹظ…ط© ط£ط¹ظ„ظ‰ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.` |
| Server validation | 422 maps to field-level errors for known fields. Unknown field/form-level 422 errors use the form-level validation message. | `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Network failure | Do not save locally or queue. Preserve the visible input in the same form state until the user edits it, resets it, retries successfully, or navigates away. | `طھط¹ط°ط± ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ط®ط§ط¯ظ…. ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ.` |

## Profile

| Field | v1 rule | Current evidence | Current alignment |
|---|---|---|---|
| `sex` | Required enum: `male`, `female`. | `models.Sex`, `ProfilePage` | Aligned |
| `birth_date` | Required valid date; not future; age 10-100. | `ProfileUpsert` | Needs alignment |
| `height_cm` | Required number 100-250. | Current schema `> 0` | Needs alignment |
| `weight_kg` | Required number 20-300. | Current schema `> 0` | Needs alignment |
| `activity_level` | Required enum: `sedentary`, `light`, `moderate`, `active`, `very_active`. | `models.ActivityLevel` | Aligned |
| `goal` | Required enum: `cut`, `maintain`, `bulk`. | `models.Goal` | Aligned |
| `protein_per_kg` | Required number 1.0-3.0. | Current schema 1.6-2.2 | Needs alignment |
| `fat_pct` | Required number 0.15-0.40. | Current schema 0.20-0.30 | Needs alignment |

Profile validation timing:
- Validate on save.
- Validate before target preview is treated as reliable.
- Invalid profile data is not saved locally, not queued, and not persisted remotely.

## Food

### Current v1 Food Validation - D-024/D-026

This section supersedes older Food validation rows that depend on `serving_label`, `serving_grams`, `is_active`, `archived_at`, or archive-only delete.

| Field / behavior | v1 rule | Current evidence | Current alignment |
|---|---|---|---|
| Add Food route | Food creation happens on `/foods/new`; the `/foods` list must not contain a large inline Add Food form. | Current UI evidence uses `FoodsPage.tsx` list/form patterns | Needs alignment |
| Edit Food route | Food edit happens on `/foods/:id/edit` and reuses Add Food structure in edit mode. | Current UI evidence is inline/page component based | Needs alignment |
| Food detail route | Food details are available at `/foods/:id`. | Current UI evidence has inline details | Needs alignment |
| `name` | Required; trim; reject empty after trim; max 120 chars; normalize for duplicate check; display as plain text. | `FoodBase.name` min length 1 | Needs alignment |
| `brand` | Optional; trim; max 80 chars if provided; display as plain text. | Missing | Needs alignment |
| `category` | Optional; trim; max 80 chars if free text; if implemented as select, only accepted options are valid. | Missing | Needs alignment |
| `nutrition_basis` | Required enum: `per_100g`, `per_100ml`. | Missing | Needs alignment |
| `calories` | Required number 0-3000 per 100g/per 100ml. | Current schema `>= 0` | Needs max/source-basis alignment |
| `protein_g` | Required number 0-300 g per 100g/per 100ml. | Current schema `>= 0` | Needs max/source-basis alignment |
| `carb_g` | Required number 0-500 g per 100g/per 100ml. | Current schema `>= 0` | Needs max/source-basis alignment |
| `fat_g` | Required number 0-300 g per 100g/per 100ml. | Current schema `>= 0` | Needs max/source-basis alignment |
| `default_unit_type` | Required enum: `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon`. | Missing | Needs alignment |
| `unit_amount` | Required number greater than 0; recommended practical range 0.01-5000 until a tighter product range is approved. | Missing | Needs alignment |
| `unit_basis` | Required enum: `g`, `ml`. | Missing | Needs alignment |
| Optional nutrients | All optional; blank means null/unknown and does not block save. If provided, values must be numeric, `>= 0`, and within D-026 max ranges. | Partial existing fields | Needs D-026 alignment |
| `fiber_g` | Optional number 0-100 g and must be `<= carb_g` when provided. | Current schema `>= 0`; no cross-field rule | Needs D-026 alignment |
| `sugar_g` | Optional number 0-100 g; current v1 field for total sugar. Empty value does not block saving. | Current code uses `total_sugars_g` | Needs D-026 mapping alignment |
| `added_sugar_g` | Optional number 0-100 g. If both `sugar_g` and `added_sugar_g` are provided, `added_sugar_g <= sugar_g`. If `sugar_g` is blank, valid `added_sugar_g` is allowed. | Current schema `>= 0`; no cross-field rule | Needs D-026 alignment |
| `net_carbs_g` | Computed as `carb_g - fiber_g`; must not be negative because `fiber_g > carb_g` is rejected. | Current service can return negative | Needs alignment |
| `vitamin_d_mcg` | Optional number 0-250 mcg; stored in mcg. IU is not a stored v1 unit. | Missing | Needs D-026 alignment |
| Duplicate Food | Current-catalog duplicate by normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis` is blocked. Deleted Foods do not block duplicate creation. | No current check | Needs alignment |
| Hard delete | Delete requires confirmation. Cancel makes no changes. Confirm permanently deletes after successful API response. Failed delete does not hide the Food locally or queue mutation. | Current code hard deletes without required confirmation | Needs alignment |
| No archive fields | `is_active` and `archived_at` are not v1 fields; archived status and Active/Archived filters must not be shown. | Missing fields; older BA required them | Superseded by D-025 |

Food page validation timing:
- Required and numeric rules validate on submit and after touched fields blur/change.
- Optional nutrients validate only when provided.
- If first invalid field is inside the collapsed Optional nutrients section, the section opens before focus moves to that field.
- Duplicate check runs on save against current catalog Foods.
- Network/API failure preserves visible entered data and shows Arabic error; no local save or queue.
- Duplicate submit is prevented while the save/delete request is pending.

### Optional Nutrient Validation Matrix - D-026

All values below are per nutrition basis value, meaning per 100g or per 100ml.

| Field | v1 rule | Arabic error when invalid |
|---|---|---|
| `fiber_g` | Optional; 0-100 g; must be `<= carb_g`. | Negative: `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.` Above max: `القيمة الغذائية الإضافية أعلى من الحد المسموح.` Cross-field: `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.` |
| `sugar_g` | Optional; 0-100 g. | Negative/above max optional nutrient messages. |
| `added_sugar_g` | Optional; 0-100 g; must be `<= sugar_g` if both are provided. If `sugar_g` is blank, a valid `added_sugar_g` is allowed. | Cross-field: `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.` |
| `saturated_fat_g` | Optional; 0-100 g; must be `<= fat_g`. | Cross-field: `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.` |
| `trans_fat_g` | Optional; 0-100 g; must be `<= fat_g`; `saturated_fat_g + trans_fat_g <= fat_g` if all are provided. | Cross-field: `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.` Sum rule: `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.` |
| `cholesterol_mg` | Optional; 0-2000 mg. | Negative/above max optional nutrient messages. |
| `sodium_mg` | Optional; 0-50000 mg. | Negative/above max optional nutrient messages. |
| `potassium_mg` | Optional; 0-10000 mg. | Negative/above max optional nutrient messages. |
| `calcium_mg` | Optional; 0-5000 mg. | Negative/above max optional nutrient messages. |
| `iron_mg` | Optional; 0-100 mg. | Negative/above max optional nutrient messages. |
| `magnesium_mg` | Optional; 0-1000 mg. | Negative/above max optional nutrient messages. |
| `zinc_mg` | Optional; 0-100 mg. | Negative/above max optional nutrient messages. |
| `vitamin_d_mcg` | Optional; 0-250 mcg. | Negative/above max optional nutrient messages. |
| `vitamin_b12_mcg` | Optional; 0-1000 mcg. | Negative/above max optional nutrient messages. |
| `vitamin_c_mg` | Optional; 0-5000 mg. | Negative/above max optional nutrient messages. |
| `vitamin_a_mcg` | Optional; 0-3000 mcg. | Negative/above max optional nutrient messages. |
| `folate_mcg` | Optional; 0-2000 mcg. | Negative/above max optional nutrient messages. |
| `vitamin_k_mcg` | Optional; 0-2000 mcg. | Negative/above max optional nutrient messages. |

D-026 cross-field validation timing:
- Run cross-field validation on submit.
- Run cross-field validation after all involved fields have parseable values.
- Blank optional nutrient fields are ignored by D-026 cross-field rules except when the rule explicitly says "if both/all values are provided".
- `0` is a valid provided value.
- `sugar_g` is the v1 total sugar field. `total_sugars_g` is legacy/current-code naming and is not the current BA source-of-truth field.
- `added_sugar_g` may be provided while `sugar_g` is blank. The `added_sugar_g <= sugar_g` rule runs only when both fields are provided.

Legacy rows below are retained for code-evidence history only. If they conflict with this D-024/D-026 section, this section controls v1 requirements.

| Field | v1 rule | Current evidence | Current alignment |
|---|---|---|---|
| `name` | Required; trim; reject empty after trim; max 120 chars; normalize for duplicate check. | `FoodBase.name` min length 1 | Needs alignment |
| `serving_label` | Legacy serving-based field; not D-025 source of truth. | `FoodBase.serving_label` min length 1 | Superseded by `default_unit_type`, `unit_amount`, and `unit_basis` |
| `serving_grams` | Legacy serving-based field; not D-025 source of truth. | Current schema `> 0`; UI min/label mismatch | Superseded by per-100g/per-100ml nutrition basis and default-unit fields |
| `calories` | Required number 0-3000. | Current schema `>= 0` | Needs max alignment |
| `protein_g` | Required number 0-300 g. | Current schema `>= 0` | Needs max alignment |
| `carb_g` | Required number 0-500 g. | Current schema `>= 0` | Needs max alignment |
| `fat_g` | Required number 0-300 g. | Current schema `>= 0` | Needs max alignment |
| `saturated_fat_g` | Optional number 0-100 g and must satisfy D-026 fat cross-field rules. | Current schema `>= 0` if present | Needs D-026 alignment |
| `trans_fat_g` | Optional number 0-100 g and must satisfy D-026 fat cross-field rules. | Current schema `>= 0` if present | Needs D-026 alignment |
| `cholesterol_mg` | Optional number 0-2000 mg. | Current schema `>= 0` if present | Needs max alignment |
| `sodium_mg` | Optional number 0-50000 mg. | Current schema `>= 0` if present | Needs D-026 alignment |
| `fiber_g` | Optional number 0-100 g and must be `<= carb_g`. | Current schema `>= 0`; no cross-field rule | Needs D-026 alignment |
| `total_sugars_g` | Legacy/current-code name; D-025 field is `sugar_g`, optional 0-100 g. | Current schema `>= 0` if present | Needs D-026 naming/range alignment |
| `added_sugar_g` | Optional number 0-100 g and must be `<= sugar_g` if both are provided. | Current schema `>= 0` if present | Needs D-026 alignment |
| `net_carbs_g` | Computed as `carb_g - fiber_g`; must not be negative. | Current service can return negative | Needs alignment |
| Duplicate food | Current-catalog duplicate by normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis` is blocked. | No current check | Needs D-025 alignment |
| `is_active` | Not a v1 field. | Missing | Superseded by D-025 |
| `archived_at` | Not a v1 field. | Missing | Superseded by D-025 |

Food optional nutrient blank behavior:
- Blank optional nutrient fields are stored as null/unknown.
- Entered `0` is a real zero.

Food delete validation:
- D-025 supersedes older archive-only delete validation.
- Confirmation is required.
- Confirmation shows the Food name and clearly states deletion is permanent.
- Cancel makes no changes.
- Confirm permanently deletes the Food from the catalog after successful API response.
- Failed delete does not hide the Food locally and does not queue a mutation.
- Deleted Foods disappear from Foods list, Food search results, and future Diary selection.
- Existing Diary entries remain readable and accurate through nutrition snapshots.

## Diary Entry

| Field | v1 rule | Current evidence | Current alignment |
|---|---|---|---|
| `entry_date` | Required valid date; today or past only. | Current schema valid date only | Needs alignment |
| `food_id` | Required current-catalog food UUID for new entries. Deleted Foods cannot be selected for future Diary entries. Existing Diary entries use snapshots after Food deletion. | Current service checks food exists | Needs D-025 snapshot/deleted-food alignment |
| `log_mode` | Required enum: `servings` or `grams`. | Missing | Needs alignment |
| `quantity` | Required mode-specific number. Serving mode: 0.01-50 servings. Gram mode: 1-5000 grams. | Current schema `> 0` | Needs mode/max alignment |
| `grams` | UI-only gram-mode input alias for `quantity`; required in gram mode; totals are calculated from Food nutrition basis and gram amount. | Missing | Needs alignment |
| `nutrition_snapshot` | System-generated D-021/D-025 object with Food name, nutrition basis, nutrition values, `log_mode`, logged quantity, and calculated totals. Not user editable. | Exists | Needs gram/default-unit and deleted-Food extension |

Diary edit validation:
- Only mode-specific `quantity` is editable.
- `log_mode` is immutable after creation.
- Food cannot be changed.
- Entry date cannot be changed.
- Snapshot nutrition values cannot be manually changed.
- Edit payload is `{ quantity }` only.
- Editing a gram-mode entry recalculates `calculated_totals` from the original snapshot and new gram quantity.
- Failed edit is not saved locally or queued.

Diary delete validation:
- Confirmation is required before deletion.
- Confirmation must show food name and entry date.
- Cancel makes no change.
- Confirm deletes only after successful API response.
- Failed delete does not remove the entry locally and does not queue a mutation.

Stale item, duplicate submit, and retry validation:
- While a write request is pending, the submit/confirm action is disabled and repeated clicks/taps send exactly one API request.
- If a write request fails, the user's visible input stays unchanged in the same form until the user edits it, resets it, retries successfully, or navigates away.
- Retry after a failed request resubmits the current visible input and does not use a local/offline queued mutation.
- If a selected Food is deleted before edit/delete/log submit completes, the request fails with a stale-food message and no local mutation.
- If a selected Food changes before Diary submit, the API validates the current server Food at submit time; a successful response uses the server-confirmed Food values for the snapshot.
- If a Diary entry has already been deleted before edit/delete completes, the request fails with a stale-diary-entry message and no local update/delete.

## API Error Mapping

| Error | v1 behavior | Arabic message |
|---|---|---|
| 401 Unauthorized | Show access/session error; do not show stale/queued data as saved. | `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` |
| 404 Not Found | Show item not found or refresh-required message. | `ط§ظ„ط¹ظ†طµط± ط؛ظٹط± ظ…ظˆط¬ظˆط¯. ط­ط¯ظ‘ط« ط§ظ„طµظپط­ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| 422 Validation Error | Show field-level errors for known fields; show form-level 422 message for unknown field or form-level validation errors. | `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Timeout / Network Error | Show connection error; preserve the visible input for write forms; do not save locally. | `طھط¹ط°ط± ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ط®ط§ط¯ظ…. ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ.` |
| 5xx Server Error | Show server error and ask user to try again. | `ط­ط¯ط« ط®ط·ط£ ظپظٹ ط§ظ„ط®ط§ط¯ظ…. ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |

Read failure copy:

| Read area | Arabic message |
|---|---|
| General API/network read | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Profile load | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Foods list load | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Food detail load | `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Diary day load | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |
| Weekly summary load | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |

## Online-Only Persistence Rules

| Area | Rule |
|---|---|
| Reads | Load fresh data from API or show connection/error state. |
| Writes | Persist only after successful API response. |
| Failed writes | Do not queue, do not save locally, do not show saved state. |
| IndexedDB | Not source of truth in v1. |
| Sync | Future Scope only. |
| Offline/cached reads | Cached personal nutrition data is not displayed as current when fresh API data cannot load. |

## Validation Alignment Items

1. Profile bounds in code do not match v1 ranges.
2. Food text trim/max/normalization rules are missing.
3. Food numeric max ranges are missing.
4. D-026 optional nutrient ranges and cross-field rules are missing, including `fiber_g <= carb_g`.
5. Duplicate current-catalog Food blocking is missing.
6. Food archive fields are not v1 requirements; D-025 supersedes them.
7. Diary gram mode is missing, including D-021 `log_mode` contract.
8. Future diary date block is missing.
9. Diary delete confirmation may be missing.
10. `serving_grams` source-of-truth assumptions are superseded by D-025 default-unit requirements.
11. Read-failure messages and cached-read fallback behavior need UI alignment with D-022.
12. Duplicate-submit, stale-record, retry, and minimum accessibility behaviors need UI/API alignment with D-023.
