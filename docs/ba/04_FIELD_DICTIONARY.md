# Field Dictionary

This dictionary separates confirmed code behavior from missing product decisions. Arabic labels are listed where they are clear from UI context; exact copy should be verified in browser because console output may display source encoding incorrectly.

## Profile Form

| Field | Arabic label | UI control | Required | Default | Allowed values / range | Placeholder | Error message | Evidence | Confidence |
|---|---|---|---:|---|---|---|---|---|---|
| `sex` | الجنس | Select | Yes | `male` | `male`, `female` | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |
| `birth_date` | تاريخ الميلاد | Date input | Yes | `1995-01-01` | Date string; no min/max confirmed | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |
| `height_cm` | الطول | Number | Yes | `175` | Backend `> 0`; UI min `1` | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |
| `weight_kg` | الوزن | Number | Yes | `80` | Backend `> 0`; UI min `1`, step `0.1` | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |
| `activity_level` | النشاط | Select | Yes | `moderate` | `sedentary`, `light`, `moderate`, `active`, `very_active` | None | Missing custom Arabic message | `ProfilePage`, `models.ActivityLevel` | High |
| `goal` | الهدف | Select | Yes | `cut` | `cut`, `maintain`, `bulk` | None | Missing custom Arabic message | `ProfilePage`, `models.Goal` | High |
| `protein_per_kg` | بروتين لكل كجم | Number | Yes | `1.8` | Backend `1.6` to `2.2`; UI min/max match | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |
| `fat_pct` | نسبة الدهون | Number | Yes | `0.25` | Backend `0.2` to `0.3`; UI min/max match | None | Missing custom Arabic message | `ProfilePage`, `schemas.ProfileUpsert` | High |

Missing profile field rules:

- No maximum age or future birth-date rule.
- No maximum height/weight beyond DB numeric precision.
- No accepted character rules because profile has no text name field.
- No custom Arabic validation copy.

## Food Form and Entity

| Field | Arabic label | UI control | Required | Default | Allowed values / range | Placeholder | Error message | DB/API mapping | Evidence | Confidence |
|---|---|---|---:|---|---|---|---|---|---|---|
| `id` | N/A | Hidden/system | No on create | UUID | UUID | N/A | N/A | `food.id`, `FoodCreate.id` | `models.Food`, `schemas.FoodCreate` | High |
| `name` | الاسم | Text | Yes | `""` | Backend min length 1; no trim/max/characters confirmed | None | Browser/default only; no custom Arabic | `food.name`, `FoodBase.name` | `FoodsPage`, `schemas.FoodBase` | High |
| `brand` | N/A | Missing | N/A | N/A | N/A | N/A | N/A | Missing | Root Foods docs suggest not confirmed | High |
| `category` | N/A | Missing | N/A | N/A | N/A | N/A | N/A | Missing | Root Foods docs suggest not confirmed | High |
| `serving_label` | الحصة | Text | Yes | `""` | Backend min length 1; no trim/max/characters confirmed | `15 g / حبة / طبق` | Browser/default only; no custom Arabic | `food.serving_label`, `FoodBase.serving_label` | `FoodsPage`, `schemas.FoodBase` | High |
| `serving_grams` | غرام الحصة | Number | Optional | `null` | Backend `> 0` if present; UI min `0`, step `0.01` | None | No custom Arabic; backend rejects 0 | `food.serving_grams`, `FoodBase.serving_grams` | `FoodsPage`, `schemas.FoodBase` | High |
| `calories` | السعرات | Number | Yes | `0` | Backend `>= 0`; DB Numeric(8,2); no max in schema | None | No custom Arabic | `food.calories`, `FoodBase.calories` | `FoodsPage`, `schemas.FoodBase` | High |
| `protein_g` | البروتين g | Number | Yes | `0` | Backend `>= 0`; DB Numeric(7,2); no max in schema | None | No custom Arabic | `food.protein_g`, `FoodBase.protein_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `carb_g` | الكارب g | Number | Yes | `0` | Backend `>= 0`; no `fiber <= carb` check | None | No custom Arabic | `food.carb_g`, `FoodBase.carb_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `fat_g` | الدهون g | Number | Yes | `0` | Backend `>= 0`; DB Numeric(7,2); no max in schema | None | No custom Arabic | `food.fat_g`, `FoodBase.fat_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `saturated_fat_g` | دهون مشبعة g | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.saturated_fat_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `trans_fat_g` | دهون متحولة g | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.trans_fat_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `cholesterol_mg` | كوليسترول mg | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.cholesterol_mg` | `FoodsPage`, `schemas.FoodBase` | High |
| `sodium_mg` | صوديوم mg | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.sodium_mg` | `FoodsPage`, `schemas.FoodBase` | High |
| `fiber_g` | ألياف g | Number | Optional | `null` | Backend `>= 0`; product docs require `<= carb_g` | None | No custom Arabic; required future field error | `food.fiber_g` | `FoodsPage`, `schemas.FoodBase`, root Foods docs | High |
| `total_sugars_g` | سكر كلي g | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.total_sugars_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `added_sugar_g` | سكر مضاف g | Number | Optional | `null` | Backend `>= 0` if present | None | No custom Arabic | `food.added_sugar_g` | `FoodsPage`, `schemas.FoodBase` | High |
| `net_carbs_g` | صافي الكارب | Computed display | N/A | Computed | `carb_g - fiber_g`; can be negative today | N/A | N/A | Response only | `services/food.py`, `FoodResponse` | High |
| `created_at` | Not shown | System | N/A | Server time | Datetime | N/A | N/A | `food.created_at`, `FoodResponse.created_at` | `models.Food`, `schemas.FoodResponse` | High |
| `updated_at` | Not shown | System | N/A | Server time | Datetime | N/A | N/A | `food.updated_at`, `FoodResponse.updated_at` | `models.Food`, `schemas.FoodResponse` | High |

Missing food field rules:

- Max length for text fields.
- Trim and whitespace collapse behavior.
- Accepted/forbidden character rules.
- Duplicate normalization details in code.
- Product-owned Arabic validation messages.
- Practical max values for nutrients.
- Consistent `serving_grams` minimum between UI and backend.

## Diary Entry Form and Entity

| Field | Arabic label | UI control | Required | Default | Allowed values / range | Placeholder | Error message | Evidence | Confidence |
|---|---|---|---:|---|---|---|---|---|---|
| `id` | N/A | Hidden/system | Optional create | UUID | UUID | N/A | N/A | `DiaryEntryCreate`; v1 does not require local offline IDs | High |
| `entry_date` | Date picker in header | Date input | Yes | Today | Date; no future/past range confirmed | N/A | Missing custom Arabic | `DiaryPage`, `DiaryEntryCreate` | High |
| `food_id` | الطعام | Select | Yes | First available food by fallback | Existing food UUID | N/A | Note shown if no food exists | `DiaryPage`, `DiaryEntryCreate` | High |
| `quantity` | الكمية بالحصة | Number | Yes | `1` | Backend `> 0`; UI min `0.01`, step `0.01` | N/A | Missing custom Arabic | `DiaryPage`, `DiaryEntryCreate` | High |
| `nutrition_snapshot` | N/A | System JSON | Yes | Generated on create/update when food changes | Snapshot object | N/A | N/A | `services/diary.py` | High |
| `created_at` | Not shown | System | N/A | Server/client time | Datetime | N/A | N/A | `models.DiaryEntry`, `frontend/lib/db.ts` | High |

Missing diary field rules:

- No gram quantity field.
- No meal type field.
- No `person_id`.
- No future-date policy.
- No max quantity.
- No edit UI field behavior despite backend update API.

## Future Scope: Sync Fields

Offline-first is removed from v1. These fields exist in the current codebase, but they are not v1 product requirements and must not be used to justify offline writes, pending sync states, or local personal data as source of truth.

| Field | Type | Required | Allowed values | Evidence | Gaps |
|---|---|---:|---|---|---|
| `method` | String | Future Scope | `POST`, `PUT`, `DELETE` in frontend type; backend accepts uppercase and rejects unsupported combos | `SyncOperation`, `sync.py` | Out of scope for v1 |
| `path` | String | Future Scope | `/profile`, `/foods`, `/foods/{id}`, `/diary`, `/diary/{id}` | `sync.py` | Out of scope for v1 |
| `body` | Object/null | Future Scope | Depends on method/path | `sync.py` | Out of scope for v1 |
| `client_id` | String/null | Future Scope | Local mutation id string | `frontend/lib/db.ts` | Out of scope for v1 |
| `created_at` | Datetime/null | Future Scope | Local timestamp | `SyncOperation` | Out of scope for v1 |
