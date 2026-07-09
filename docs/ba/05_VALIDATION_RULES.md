# Validation Rules

## Profile

| Field | Confirmed rule | Source | UI alignment | Gap |
|---|---|---|---|---|
| `sex` | Must be enum `male` or `female` | `models.Sex`, `ProfileUpsert` | Select options align | No custom Arabic error |
| `birth_date` | Must be valid date | `ProfileUpsert` | Date input | No future-date or age bounds |
| `height_cm` | `> 0` | `ProfileUpsert.height_cm` | UI min `1` | No max |
| `weight_kg` | `> 0` | `ProfileUpsert.weight_kg` | UI min `1`, step `0.1` | No max |
| `activity_level` | Must be enum | `models.ActivityLevel` | Select options align | No custom Arabic error |
| `goal` | Must be enum | `models.Goal` | Select options align | No custom Arabic error |
| `protein_per_kg` | `1.6` to `2.2` | `ProfileUpsert.protein_per_kg` | UI min/max align | No custom Arabic error |
| `fat_pct` | `0.2` to `0.3` | `ProfileUpsert.fat_pct` | UI min/max align | No custom Arabic error |

## Food

| Field | Confirmed rule | Source | UI alignment | Gap |
|---|---|---|---|---|
| `name` | Min length 1 | `FoodBase.name` | HTML required | Whitespace-only likely accepted; no max; no Arabic error |
| `serving_label` | Min length 1 | `FoodBase.serving_label` | HTML required | Whitespace-only likely accepted; no max; no Arabic error |
| `serving_grams` | Optional; if provided `> 0` | `FoodBase.serving_grams` | UI min is `0` | UI/backend mismatch for `0` |
| `calories` | Required; `>= 0` | `FoodBase.calories` | Required number; default `0` | Empty can become `0`; no max |
| `protein_g` | Required; `>= 0` | `FoodBase.protein_g` | Required number; default `0` | Empty can become `0`; no max |
| `carb_g` | Required; `>= 0` | `FoodBase.carb_g` | Required number; default `0` | No `fiber <= carb` enforcement |
| `fat_g` | Required; `>= 0` | `FoodBase.fat_g` | Required number; default `0` | Empty can become `0`; no max |
| Optional nutrients | If provided `>= 0` | `FoodBase` optional fields | Number inputs min `0` | No max |
| `net_carbs_g` | Computed as `carb_g - fiber_g` | `services/food.py` | Display only | Can be negative |
| Duplicate food | No rule in code | N/A | N/A | Root Foods docs require blocking exact duplicates |

## Diary Entry

| Field | Confirmed rule | Source | UI alignment | Gap |
|---|---|---|---|---|
| `entry_date` | Valid date | `DiaryEntryCreate` | Date input | No future/past policy |
| `food_id` | Must reference existing food | `create_entry` calls `get_food` | Select from foods | Empty foods handled by note and disabled button |
| `quantity` | `> 0` | `DiaryEntryCreate.quantity` | UI min `0.01`, step `0.01` | No max; empty becomes `Number("")` if cleared |
| `nutrition_snapshot` | Generated from current food values | `make_snapshot` | System only | No version/schema validation |

## Future Scope: Sync

| Field | Confirmed rule | Source | Gap |
|---|---|---|---|
| `operations` | Exists in current code; defaults to empty list | `SyncPushRequest` | Out of scope for v1 online-only behavior |
| `method/path` | Runtime-supported combinations only | `apply_operation` | Out of scope for v1 online-only behavior |
| Operation body | Validated against target schema during apply | `apply_operation` | Out of scope for v1 online-only behavior |

## Online-Only v1 Validation Rules

| Area | Rule | Status |
|---|---|---|
| API unreachable | Show a clear connection error and do not save data | Required for v1 |
| Server validation error | Show validation error and do not queue or persist locally | Required for v1 |
| Profile save | Persist only after successful `PUT /profile` response | Required for v1 |
| Food create/update/delete | Persist UI state only after successful `/foods` API response | Required for v1 |
| Diary create/delete/update | Persist UI state only after successful `/diary` API response | Required for v1 |
| Local cache | Must not be treated as source of truth for v1 | Required for v1 |

## Validation Consistency Gaps

1. Food `serving_grams`: frontend allows `0`, backend rejects `0`.
2. Food required numeric fields: frontend defaults to `0`, making missing-vs-zero unclear.
3. Food server validation errors: mutation error handlers currently can queue local changes; v1 requires showing the error and not saving locally.
4. Food duplicate blocking: required by root Foods docs, missing in code.
5. Net carbs: root Foods docs require non-negative net carbs and `fiber_g <= carb_g`; code does not enforce this.
6. Profile future birth date: no product rule.
7. Diary future date: no product rule.
8. Diary update: backend supports it, UI does not.
9. No custom Arabic field-level validation messages.
10. No max text lengths or practical max numeric limits.
