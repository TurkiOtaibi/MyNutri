# Entity and Resource Inventory

## Profile

| Attribute | Detail |
|---|---|
| Type | SQLModel database table |
| Table | `profile` |
| Purpose | Stores the single user's body stats and goal inputs used to compute targets |
| Visibility | Private to the single owner token |
| Owner field | Missing; ownership is implicit through single-user app |
| System-computed fields | Targets are computed on response, not stored |
| Timestamps | `updated_at` only |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/services/profile.py` |
| Confidence | High |

Fields: `id`, `sex`, `birth_date`, `height_cm`, `weight_kg`, `activity_level`, `goal`, `protein_per_kg`, `fat_pct`, `updated_at`.

Open questions:

- Should future multi-person support replace `profile` with `person` or add people alongside the current profile table?
- Should profile have `created_at`?

## Food

| Attribute | Detail |
|---|---|
| Type | SQLModel database table |
| Table | `food` |
| Purpose | Manual food catalog used by Diary logging |
| Visibility | Private to the single owner token |
| Owner field | Missing; ownership is implicit through single-user app |
| System-computed fields | `net_carbs_g` is computed in responses |
| Timestamps | `created_at`, `updated_at` |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/services/food.py`, `frontend/components/FoodsPage.tsx` |
| Confidence | High |

Fields: `id`, `name`, `serving_label`, `serving_grams`, `calories`, `protein_g`, `carb_g`, `fat_g`, `saturated_fat_g`, `trans_fat_g`, `cholesterol_mg`, `sodium_mg`, `fiber_g`, `total_sugars_g`, `added_sugar_g`, `created_at`, `updated_at`.

Relationships:

- `diary_entry.food_id` references `food.id` with `ON DELETE SET NULL`.
- Diary entries also copy nutrition into `nutrition_snapshot`.

Open questions:

- Should all deletes become archive/inactive for simplicity?
- What field should represent archive state: `is_active`, `archived_at`, or another lifecycle field?
- Should duplicate checking be server-enforced with a normalized unique index?

## DiaryEntry

| Attribute | Detail |
|---|---|
| Type | SQLModel database table |
| Table | `diary_entry` |
| Purpose | Stores one logged food event for one date |
| Visibility | Private to the single owner token |
| Owner/person field | Missing in current code; no `person_id` |
| System-computed fields | `totals` computed from snapshot and quantity |
| Timestamps | `created_at` only |
| Evidence | `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/services/diary.py`, `frontend/components/DiaryPage.tsx` |
| Confidence | High |

Fields: `id`, `entry_date`, `food_id`, `quantity`, `nutrition_snapshot`, `created_at`.

Relationships:

- Optional FK to `food.id`.
- Snapshot stores copied food values so historical entries survive food edits/deletes.

Open questions:

- Should Diary update be exposed in the UI?
- Should future dates be allowed?
- Should meal type remain deferred?
- Should diary entries become person-scoped?

## NutritionSnapshot

| Attribute | Detail |
|---|---|
| Type | JSON/value object stored inside DiaryEntry |
| Purpose | Freezes food nutrition values at log time |
| Evidence | `backend/app/services/diary.py`, `backend/app/schemas.py`, `backend/tests/test_diary_snapshot.py` |
| Confidence | High |

Fields mirror Food input plus `food_id`: `name`, `serving_label`, `serving_grams`, `calories`, `protein_g`, `carb_g`, `fat_g`, optional detail nutrients.

Open questions:

- Should snapshots include the food display name forever even after food deletion? Current code does.
- Should snapshots include archive status? Not currently.

## NutritionTotals

| Attribute | Detail |
|---|---|
| Type | Computed response/value object |
| Purpose | Shows totals for diary entries, days, and weeks |
| Evidence | `backend/app/schemas.py`, `backend/app/services/diary.py` |
| Confidence | High |

Totals are calculated as per-serving snapshot values multiplied by `quantity`, rounded to two decimals.

## TargetResponse / TargetResult

| Attribute | Detail |
|---|---|
| Type | Computed response/value object |
| Purpose | Shows BMR, TDEE, target calories, macros, and carb clamp flag |
| Evidence | `backend/app/services/calc.py`, `backend/app/schemas.py`, `backend/tests/test_calc.py` |
| Confidence | High |

Open questions:

- Should target snapshots be stored with diary entries in a later version? Current docs defer this.

## SyncOperation

| Attribute | Detail |
|---|---|
| Type | API payload |
| Purpose | Future-scope payload for replaying queued offline mutations; not part of v1 online-only requirements |
| Evidence | `backend/app/schemas.py`, `backend/app/api/routes/sync.py`, `frontend/lib/types.ts` |
| Confidence | High |
| v1 status | Out of scope / Future Scope |

Fields: `method`, `path`, `body`, `client_id`, `created_at`.

## QueuedMutation

| Attribute | Detail |
|---|---|
| Type | IndexedDB entity |
| Purpose | Future-scope local pending mutation; v1 must not queue offline writes |
| Evidence | `frontend/lib/db.ts`, `frontend/lib/types.ts` |
| Confidence | High |
| v1 status | Out of scope / Future Scope |

Fields: `id`, `method`, `path`, `body`, `created_at`, `status`.

## Local Cache Stores

Product decision: local cached personal nutrition data must not be treated as source of truth in v1. Any IndexedDB stores in the current code are implementation evidence only and should be removed, disabled, or deferred for v1.

| Store | Key/index evidence | Purpose |
|---|---|---|
| `foods` | `id,name,updated_at` | Future-scope local food cache; out of v1 source-of-truth behavior |
| `diaryEntries` | `id,entry_date,food_id,created_at` | Future-scope local diary cache; out of v1 source-of-truth behavior |
| `profile` | `id,updated_at` | Future-scope local profile cache; out of v1 source-of-truth behavior |
| `mutations` | `++id,created_at,status` | Future-scope offline write queue; explicitly removed from v1 |

Evidence: `frontend/lib/db.ts`.
