# Field Dictionary

This dictionary is the v1 product field source of truth. "Current alignment" identifies where current code already matches or needs implementation alignment.

General validation and accessibility rules:
- Field-level errors display near the affected field.
- Form-level errors display above or near the form action area.
- Field errors must be available to assistive technology with `aria-invalid` and `aria-describedby`.
- On submit validation failure, focus moves to the first invalid visible field. If the first invalid field is inside a collapsed optional section, that section opens before focus moves to the field.
- Arabic validation copy is defined in `docs/ba/06_ERROR_MESSAGES.md`.

## Profile Form

Scope note:
- v1 has one Profile model only. Multi-profile/person fields and profile switching are Future Scope per D-016.
- Profile reset/delete fields or controls are out of scope per D-017.

| Field | Arabic label | Type/control | Required | Default | Allowed values / range | Placeholder | Error placement | DB/API mapping | Current alignment | Decisions |
|---|---|---|---:|---|---|---|---|---|---|---|
| `sex` | الجنس | Select | Yes | `male` | `male`, `female` | None | Field-level | `profile.sex`, `ProfileUpsert.sex` | Select exists | D-011 |
| `birth_date` | تاريخ الميلاد | Date | Yes | `1995-01-01` | Valid date; age 10-100; not future | None | Field-level | `profile.birth_date` | Code accepts any date | D-009, D-011 |
| `height_cm` | الطول | Number | Yes | `175` | 100-250 cm | None | Field-level | `profile.height_cm` | Code currently `> 0` | D-012 |
| `weight_kg` | الوزن | Number | Yes | `80` | 20-300 kg | None | Field-level | `profile.weight_kg` | Code currently `> 0` | D-012 |
| `activity_level` | النشاط | Select | Yes | `moderate` | `sedentary`, `light`, `moderate`, `active`, `very_active` | None | Field-level | `profile.activity_level` | Select exists | D-011 |
| `goal` | الهدف | Select | Yes | `cut` | `cut`, `maintain`, `bulk` | None | Field-level | `profile.goal` | Select exists | D-011 |
| `protein_per_kg` | بروتين لكل كجم | Number | Yes | `1.8` | 1.0-3.0 | None | Field-level | `profile.protein_per_kg` | Code currently 1.6-2.2 | D-012 |
| `fat_pct` | نسبة الدهون | Number | Yes | `0.25` | 0.15-0.40 | None | Field-level | `profile.fat_pct` | Code currently 0.20-0.30 | D-012 |

Accepted input:
- Numeric fields accept decimal numbers where useful.
- Select fields accept only listed values.
- Birth date uses browser date input plus server validation.

## Food Form and Entity

### Current v1 Food Field Dictionary - D-024/D-025

| `serving_label` | Legacy serving label | Text | Legacy/current-code field | Empty | Superseded by D-025 default-unit fields for v1 source of truth | N/A | N/A | `food.serving_label` | Code min only | Superseded by D-025 |

Food model principles:
- Food creation uses standalone `/foods/new`.
- Food edit uses `/foods/:id/edit` and reuses the Add Food structure.
- Food detail uses `/foods/:id`.
- Nutrition values are stored per 100g or per 100ml.
- Serving-based nutrition is not the Food source of truth.
- Food deletion is permanent hard delete. Do not use archive/inactive fields in v1.
- Optional nutrients are collapsed by default.

| Field | Arabic label | Type/control | Required | Default | Allowed values / range | Placeholder/helper | Error placement | DB/API mapping | Current alignment | Decisions |
|---|---|---|---:|---|---|---|---|---|---|---|
| `id` | N/A | Hidden/system UUID | No on create | UUID | UUID | N/A | N/A | `food.id` | Exists | N/A |
| `name` | اسم الطعام | Text | Yes | Empty | 1+ chars after trim; practical max 120 chars; Arabic/English letters, numbers, spaces, common punctuation; display as plain text | None | Field-level | `food.name` | Exists; max/normalization needs alignment | D-006, D-011, D-025 |
| `brand` | العلامة التجارية | Text | Optional | Empty/null | Practical max 80 chars; plain text | None | Field-level if invalid | `food.brand` | Missing | D-025 |
| `category` | التصنيف | Text | Optional | Empty/null | Practical max 80 chars; free text in v1 | None | Field-level if invalid | `food.category` | Missing | D-025 |
| `nutrition_basis` | أساس القيم الغذائية | Select/segmented control | Yes | `per_100g` | `per_100g`, `per_100ml` | None | Field-level | `food.nutrition_basis` | Missing | D-025 |
| `calories` | السعرات | Number | Yes | Empty | 0-3000 per 100g/per 100ml | None | Field-level | `food.calories` | Exists; max/source-basis alignment needed | D-012, D-025 |
| `protein_g` | البروتين | Number | Yes | Empty | 0-300 g per 100g/per 100ml | None | Field-level | `food.protein_g` | Exists; max/source-basis alignment needed | D-012, D-025 |
| `carb_g` | الكربوهيدرات | Number | Yes | Empty | 0-500 g per 100g/per 100ml | None | Field-level | `food.carb_g` | Exists; max/source-basis alignment needed | D-012, D-025 |
| `fat_g` | الدهون | Number | Yes | Empty | 0-300 g per 100g/per 100ml | None | Field-level | `food.fat_g` | Exists; max/source-basis alignment needed | D-012, D-025 |
| `default_unit_type` | الوحدة الافتراضية | Select | Yes | `g` for per 100g; `ml` for per 100ml | `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon` | None | Field-level | `food.default_unit_type` | Missing | D-025 |
| `unit_amount` | مقدار الوحدة | Number | Yes | Empty | Greater than 0; recommended practical range 0.01-5000; represents the amount of `unit_basis` in one default unit | Example: `1 slice = 30g` | Field-level | `food.unit_amount` | Missing | D-025 |
| `unit_basis` | أساس الوحدة | Select | Yes | `g` for per 100g; `ml` for per 100ml | `g`, `ml` | None | Field-level | `food.unit_basis` | Missing | D-025 |
| `fiber_g` | الألياف | Number | Optional | `null` | 0-100 g and must be `<= carb_g` when provided | None | Field-level | `food.fiber_g` | Code does not enforce `<= carb_g` | D-026 |
| `sugar_g` | السكر | Number | Optional | `null` | 0-100 g; total sugar per 100g/per 100ml | None | Field-level | `food.sugar_g` | Missing; current code uses `total_sugars_g` | D-026 |
| `total_sugars_g` | Legacy total sugars | Number | Legacy/current-code field | `null` | Superseded by current v1 `sugar_g`; may be used only for migration/backward compatibility if implementation needs it | None | Field-level | `food.total_sugars_g` | Code `>= 0`; no max | Superseded by D-025/D-026 |
| `added_sugar_g` | السكر المضاف | Number | Optional | `null` | 0-100 g; must be `<= sugar_g` if both are provided | None | Field-level | `food.added_sugar_g` | Code `>= 0`; no max | D-026 |
| `saturated_fat_g` | الدهون المشبعة | Number | Optional | `null` | 0-100 g; `<= fat_g`; saturated + trans `<= fat_g` if all provided | None | Field-level | `food.saturated_fat_g` | Code `>= 0`; no max | D-026 |
| `trans_fat_g` | الدهون المتحولة | Number | Optional | `null` | 0-100 g; `<= fat_g`; saturated + trans `<= fat_g` if all provided | None | Field-level | `food.trans_fat_g` | Code `>= 0`; no max | D-026 |
| `sodium_mg` | الصوديوم | Number | Optional | `null` | 0-50000 mg | None | Field-level | `food.sodium_mg` | Code `>= 0`; no max | D-026 |
| `cholesterol_mg` | الكوليسترول | Number | Optional | `null` | 0-2000 mg | None | Field-level | `food.cholesterol_mg` | Exists; max alignment needed | D-012, D-025, D-026 |
| `potassium_mg` | البوتاسيوم | Number | Optional | `null` | 0-10000 mg | None | Field-level | `food.potassium_mg` | Missing | D-025, D-026 |
| `calcium_mg` | الكالسيوم | Number | Optional | `null` | 0-5000 mg | None | Field-level | `food.calcium_mg` | Missing | D-025, D-026 |
| `iron_mg` | الحديد | Number | Optional | `null` | 0-100 mg | None | Field-level | `food.iron_mg` | Missing | D-025, D-026 |
| `magnesium_mg` | المغنيسيوم | Number | Optional | `null` | 0-1000 mg | None | Field-level | `food.magnesium_mg` | Missing | D-025, D-026 |
| `zinc_mg` | الزنك | Number | Optional | `null` | 0-100 mg | None | Field-level | `food.zinc_mg` | Missing | D-025, D-026 |
| `vitamin_d_mcg` | فيتامين د | Number | Optional | `null` | 0-250 mcg; stored in mcg | None | Field-level | `food.vitamin_d_mcg` | Missing | D-025, D-026 |
| `vitamin_b12_mcg` | فيتامين ب12 | Number | Optional | `null` | 0-1000 mcg | None | Field-level | `food.vitamin_b12_mcg` | Missing | D-025, D-026 |
| `vitamin_c_mg` | فيتامين ج | Number | Optional | `null` | 0-5000 mg | None | Field-level | `food.vitamin_c_mg` | Missing | D-025, D-026 |
| `vitamin_a_mcg` | فيتامين أ | Number | Optional | `null` | 0-3000 mcg | None | Field-level | `food.vitamin_a_mcg` | Missing | D-025, D-026 |
| `folate_mcg` | الفولات | Number | Optional | `null` | 0-2000 mcg | None | Field-level | `food.folate_mcg` | Missing | D-025, D-026 |
| `vitamin_k_mcg` | فيتامين ك | Number | Optional | `null` | 0-2000 mcg | None | Field-level | `food.vitamin_k_mcg` | Missing | D-025, D-026 |
| `notes` | ملاحظات | Textarea | Optional | Empty/null | Practical max 500 chars; plain text | None | Field-level if invalid | `food.notes` | Missing | D-025 |
| `data_source` | مصدر البيانات | Text | Optional | Empty/null | Practical max 120 chars; plain text | None | Field-level if invalid | `food.data_source` | Missing | D-025 |
| `net_carbs_g` | صافي الكربوهيدرات | Computed display | N/A | Computed | `carb_g - fiber_g`; never negative because `fiber_g <= carb_g` | N/A | N/A | Response/display only | Current service can return negative | D-011, D-025 |
| `created_at` | تاريخ الإنشاء | System datetime | N/A | Server time | Datetime | N/A | N/A | `food.created_at` | Exists | N/A |
| `updated_at` | تاريخ التحديث | System datetime | N/A | Server time | Datetime | N/A | N/A | `food.updated_at` | Exists | N/A |

Current duplicate key:
- Current catalog Foods only.
- Normalized `name`.
- Normalized `nutrition_basis`.
- Normalized `default_unit_type`.
- Numeric `unit_amount`.
- Normalized `unit_basis`.
- Deleted Foods do not block duplicate creation.
- Brand, category, notes, and data source are not part of the v1 duplicate key.

Food page grouping:
- Basic food information: `name`, `brand`, `category`.
- Nutrition basis: `nutrition_basis`.
- Core nutrition values: `calories`, `protein_g`, `carb_g`, `fat_g`.
- Default unit: `default_unit_type`, `unit_amount`, `unit_basis`.
- Optional nutrients: collapsed by default, label `Optional nutrients` / `القيم الغذائية الإضافية`.
- Notes and data source: `notes`, `data_source`.

Sugar field mapping:
- `sugar_g` is the current v1 field for total sugar.
- `added_sugar_g` is the current v1 field for added sugar.
- Both values are optional nutrients measured in grams per 100g or per 100ml according to `nutrition_basis`.
- Empty `sugar_g` does not block saving.
- Empty `added_sugar_g` does not block saving.
- If `added_sugar_g` is provided while `sugar_g` is blank, saving is allowed as long as `added_sugar_g` itself is valid.
- If both `sugar_g` and `added_sugar_g` are provided, `added_sugar_g` must not exceed `sugar_g`.
- `total_sugars_g` is a legacy/current-code field name and is not the current v1 BA source-of-truth field.

Legacy rows below are retained for code-evidence history only. If they conflict with this D-024/D-026 section, this section controls v1 requirements.

| Field | Arabic label | Type/control | Required | Default | Allowed values / range | Placeholder | Error placement | DB/API mapping | Current alignment | Decisions |
|---|---|---|---:|---|---|---|---|---|---|---|
| `id` | N/A | Hidden/system UUID | No on create | UUID | UUID | N/A | N/A | `food.id`, `FoodCreate.id` | Exists | N/A |
| `name` | الاسم | Text | Yes | Empty | 1+ chars after trim; practical max 120 chars; Arabic/English letters, numbers, spaces, common punctuation | None | Field-level | `food.name`, `FoodBase.name` | Code min only | D-006, D-011 |
| `serving_label` | Legacy serving label | Text | Legacy/current-code field | Empty | Superseded by D-025 default-unit fields for v1 source of truth | N/A | N/A | `food.serving_label` | Code min only | Superseded by D-025 |
| `serving_grams` | Legacy serving grams | Number | Legacy/current-code field | `null` | Superseded by D-025 default-unit fields for v1 source of truth | N/A | N/A | `food.serving_grams` | Code `> 0`; UI min/label mismatch | Superseded by D-025 |
| `calories` | السعرات | Number | Yes | Empty required input | 0-3000 | None | Field-level | `food.calories` | Code `>= 0`; no max | D-012 |
| `protein_g` | البروتين g | Number | Yes | Empty required input | 0-300 g | None | Field-level | `food.protein_g` | Code `>= 0`; no max | D-012 |
| `carb_g` | الكارب g | Number | Yes | Empty required input | 0-500 g | None | Field-level | `food.carb_g` | Code `>= 0`; no max | D-012 |
| `fat_g` | الدهون g | Number | Yes | Empty required input | 0-300 g | None | Field-level | `food.fat_g` | Code `>= 0`; no max | D-012 |
| `saturated_fat_g` | الدهون المشبعة | Number | Optional | `null` | 0-100 g; `<= fat_g`; saturated + trans `<= fat_g` if all provided | None | Field-level | `food.saturated_fat_g` | Code `>= 0`; no max | D-026 |
| `trans_fat_g` | الدهون المتحولة | Number | Optional | `null` | 0-100 g; `<= fat_g`; saturated + trans `<= fat_g` if all provided | None | Field-level | `food.trans_fat_g` | Code `>= 0`; no max | D-026 |
| `cholesterol_mg` | كوليسترول mg | Number | Optional | `null` | 0-2000 mg | None | Field-level | `food.cholesterol_mg` | Code `>= 0`; no max | D-012 |
| `sodium_mg` | الصوديوم | Number | Optional | `null` | 0-50000 mg | None | Field-level | `food.sodium_mg` | Code `>= 0`; no max | D-026 |
| `fiber_g` | الألياف | Number | Optional | `null` | 0-100 g and must be `<= carb_g` when provided | None | Field-level | `food.fiber_g` | Code does not enforce `<= carb_g` | D-026 |
| `total_sugars_g` | Legacy total sugars | Number | Legacy/current-code field | `null` | Superseded by current v1 `sugar_g`; may be used only for migration/backward compatibility if implementation needs it | None | Field-level | `food.total_sugars_g` | Code `>= 0`; no max | Superseded by D-025/D-026 |
| `added_sugar_g` | السكر المضاف | Number | Optional | `null` | 0-100 g; must be `<= sugar_g` if both are provided | None | Field-level | `food.added_sugar_g` | Code `>= 0`; no max | D-026 |
| `net_carbs_g` | صافي الكارب | Computed display | N/A | Computed | `carb_g - fiber_g`, never negative because `fiber_g <= carb_g` | N/A | N/A | Response only | Code can return negative | D-011 |
| `is_active` | Not v1 | System boolean | Not v1 | N/A | Superseded by D-025; do not add for v1 | N/A | N/A | N/A | Not required | D-025 |
| `archived_at` | Not v1 | System datetime/null | Not v1 | N/A | Superseded by D-025; do not add for v1 | N/A | N/A | N/A | Not required | D-025 |
| `created_at` | تاريخ الإنشاء | System datetime | N/A | Server time | Datetime | N/A | N/A | `food.created_at` | Exists | N/A |
| `updated_at` | تاريخ التحديث | System datetime | N/A | Server time | Datetime | N/A | N/A | `food.updated_at` | Exists | N/A |

Food text normalization:
- Trim leading/trailing whitespace.
- Collapse repeated spaces.
- Compare English case-insensitively.
- Normalize Arabic by trimming and collapsing whitespace.

Food duplicate key:
- Current catalog foods only.
- Normalized `name`.
- `nutrition_basis`.
- `default_unit_type`.
- `unit_amount`.
- `unit_basis`.
- Deleted Foods do not block duplicate creation because they no longer exist.
- Brand is not part of v1 duplicate key.

Legacy serving grams note:
- `serving_grams` belongs to the older serving-based Food model and is superseded by D-025 for v1 Food source-of-truth.
- Current v1 Food UI uses `Default unit`, `Unit amount`, and `Unit basis` instead.

Forbidden input:
- HTML/script input is not accepted as rendered markup.
- Control characters are not accepted.

## Diary Entry Form and Entity

| Field | Arabic label | Type/control | Required | Default | Allowed values / range | Placeholder | Error placement | DB/API mapping | Current alignment | Decisions |
|---|---|---|---:|---|---|---|---|---|---|---|
| `id` | N/A | Hidden/system UUID | Optional create | UUID | UUID | N/A | N/A | `diary_entry.id` | Exists | N/A |
| `entry_date` | التاريخ | Date | Yes | Today | Today or past only; future blocked | None | Field-level | `diary_entry.entry_date` | Future allowed today | D-008 |
| `food_id` | الطعام | Select | Yes | First current catalog Food if available | Existing current catalog Food UUID | N/A | Field-level/form-level | `diary_entry.food_id` | Current code checks Food existence; needs D-025 deleted-Food snapshot alignment | D-021, D-025 |
| `log_mode` | طريقة التسجيل | Segmented control / radio | Yes | `servings` | `servings`, `grams` | N/A | Field-level | `DiaryEntryCreate.log_mode`, `DiaryEntryResponse.log_mode`, required v1 persisted entry field | Missing | D-007, D-021 |
| `quantity` | الكمية | Number | Yes | `1` | Serving mode: 0.01-50 servings. Gram mode: 1-5000 grams. | N/A | Field-level | `diary_entry.quantity`, `DiaryEntryCreate.quantity`, `DiaryEntryUpdate.quantity` | Current backend `> 0`; no mode-specific max | D-012, D-021 |
| `serving_grams` | Legacy serving grams | Number | Legacy/current-code field | `null` | Superseded by D-025 default-unit fields for v1 source of truth | N/A | N/A | `food.serving_grams` | Code `> 0`; UI min/label mismatch | Superseded by D-025 |
| `nutrition_snapshot` | N/A | System JSON | Yes | Generated | Food identity, nutrition basis, nutrition values at logging time, default-unit data used for calculation, `log_mode`, `logged_quantity`, and calculated totals at log time | N/A | N/A | `diary_entry.nutrition_snapshot` | Exists for serving mode; gram/default-unit contract missing | D-007, D-021, D-025 |
| `created_at` | تاريخ الإنشاء | System datetime | N/A | Server time | Datetime | N/A | N/A | `diary_entry.created_at` | Exists | N/A |

Diary edit fields:
- Editable in v1: mode-specific `quantity` only.
- Not editable in v1: `log_mode`, `food_id`, `entry_date`, and snapshot nutrition values.
- Edit payload is `{ quantity }` only.
- For gram-mode entries, the edit quantity is grams and must remain within 1-5000.
- For serving-mode entries, the edit quantity is servings and must remain within 0.01-50.

Diary quantity mode contract:
- Create payload is `{ entry_date, food_id, log_mode, quantity }`.
- `quantity` is serving count when `log_mode="servings"`.
- `quantity` is grams when `log_mode="grams"`.
- A separate persisted `grams` field is not part of v1.
- Gram mode calculates totals from the selected Food's `nutrition_basis` and logged gram amount. For `per_100g`, multiplier is `quantity / 100`.
- Serving/default-unit mode calculates totals from the Food's `unit_amount` and `unit_basis` against the Food nutrition basis.
- `nutrition_snapshot.calculated_totals` stores the calculated totals used by day and weekly summaries.
- The snapshot must preserve Food name at logging time, nutrition basis at logging time, nutrition values at logging time, logged quantity, log mode, and calculated totals so Diary history remains readable after the Food is deleted.
- Current code may still depend on `food_id` or serving-based snapshot values for historical display; that is an implementation alignment item under D-025.

## API/System Fields

| Field | Status | Notes |
|---|---|---|
| `Authorization` header | Required for protected APIs | 401 maps to Arabic access/session error. |
| `SyncOperation.method/path/body` | Future Scope | Not a v1 requirement. |
| `QueuedMutation.status` | Future Scope | Pending/syncing states are not v1 requirements. |
| IndexedDB cache tables | Future Scope | Must not be source of truth in v1. |
