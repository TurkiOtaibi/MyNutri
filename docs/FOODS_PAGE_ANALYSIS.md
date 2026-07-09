# Foods Page Analysis - myNutri

Read-only analysis of the Foods page in the myNutri personal nutrition system.

Scope: Foods page only. This report is based on the project documentation, backend models/schemas/services/API routes, database migration, frontend page/components/API/Dexie/types/layout/CSS/service worker, and tests.

No implementation or refactor is included in this document.

## 1. Foods Page Summary

The Foods page is the manual food catalog for myNutri. Its purpose is to let the single owner create, search, edit, inspect, and delete foods whose nutrition values are later used in Diary logging.

It is a core supporting page. Diary cannot log meaningful food entries without this catalog.

Foods are global/shared in the current codebase. There is no `person_id` on foods, and current Diary entries are not person-scoped either. This matches the current repository documents, but the newer multi-person plan mentions people/profiles and person-scoped diary entries. That multi-person model is not implemented yet.

Primary sources:

- `docs/1-SYSTEM-PLAN.md:43`
- `frontend/components/FoodsPage.tsx:130`
- `backend/app/models.py:56`
- `frontend/lib/types.ts:32`

## 2. Complete Feature List

| Feature | Status | Source | Notes / Risks |
|---|---:|---|---|
| Food list display | Implemented | `frontend/components/FoodsPage.tsx:157` | Shows name, serving label, calories, macros, net carbs. |
| Search by food name | Implemented | `frontend/components/FoodsPage.tsx:142`, `backend/app/services/food.py:38` | Server uses `ilike` on name only. |
| Filtering | Missing | N/A | No category, macro, calorie, or source filters. |
| Sorting | Partially Implemented | `backend/app/services/food.py:39`, `frontend/lib/db.ts:61` | Sorted by name only; no UI sort control. |
| Add food | Implemented | `frontend/components/FoodsPage.tsx:191`, `backend/app/api/routes/foods.py:19` | Works online and queues offline. |
| Edit food | Implemented | `frontend/components/FoodsPage.tsx:109`, `backend/app/services/food.py:75` | Existing diary snapshots are not changed. |
| Delete food | Implemented, risky UX | `frontend/components/FoodsPage.tsx:179`, `backend/app/services/food.py:87` | No confirmation. Hard delete. Diary FK becomes null, snapshot remains. |
| Food details | Implemented | `frontend/components/FoodsPage.tsx:246` | Inline expandable detail block. |
| Food categories | Missing | N/A | Not in schema, DB, UI, or docs. |
| Brand name | Missing | N/A | Not in schema, DB, UI, or docs. |
| Food source/type | Missing | N/A | No manual/imported/custom source field. |
| Serving-based tracking | Implemented | `docs/1-SYSTEM-PLAN.md:99`, `frontend/lib/types.ts:75` | Quantity means number of servings. |
| Gram-based tracking | Partially Implemented | `frontend/components/FoodsPage.tsx:207` | `serving_grams` is stored/displayed, but Diary does not log arbitrary grams. |
| Measurement units | Partially Implemented | `frontend/components/FoodsPage.tsx:198` | `serving_label` is free text; no normalized unit. |
| Nutrition per serving | Implemented | `backend/app/schemas.py:39` | All nutrition values are per one serving. |
| Nutrition per 100g | Missing | N/A | Not stored or calculated. |
| Net carbs | Implemented | `backend/app/services/food.py:10` | `carb_g - fiber_g`, rounded to 2 decimals. Can go negative. |
| Required nutrients | Implemented | `backend/app/schemas.py:43` | Calories, protein, carbs, fat required and `>= 0`. |
| Optional nutrients | Implemented | `backend/app/schemas.py:47` | Saturated fat, trans fat, cholesterol, sodium, fiber, total sugars, added sugar. |
| Snapshot behavior | Implemented | `backend/app/services/diary.py:29`, `backend/tests/test_diary_snapshot.py:5` | Editing/deleting foods does not corrupt old diary nutrition. |
| Empty state | Implemented | `frontend/components/FoodsPage.tsx:186` | Same empty state may appear during loading/error fallback. |
| Loading state | Missing | `frontend/components/FoodsPage.tsx:103` | No explicit loading indicator. |
| Error state | Partially Implemented | `frontend/components/FoodsPage.tsx:54` | Offline fallback exists; server errors are not clearly shown. |
| Success messages | Implemented | `frontend/components/FoodsPage.tsx:62` | Arabic note after save/delete. |
| Delete confirmation | Missing | `frontend/components/FoodsPage.tsx:179` | Delete fires immediately. |
| Mobile responsive layout | Implemented | `frontend/app/globals.css:442` | Grid collapses, but no safe-area handling. |
| RTL Arabic layout | Implemented | `frontend/app/layout.tsx:23` | Arabic labels and RTL root. |
| Accessibility | Partial | `frontend/components/FoodsPage.tsx:169` | Labels exist; icon buttons use `title`, no `aria-label`. |
| API calls | Implemented | `frontend/lib/api.ts:82`, `backend/app/api/routes/foods.py:14` | GET/POST/GET by id/PUT/DELETE. |
| Offline cache/sync | Implemented | `frontend/lib/db.ts:22`, `backend/app/api/routes/sync.py:74` | Queues food POST/PUT/DELETE. |
| Tests | Partial | `backend/tests/test_diary_snapshot.py:5`, `backend/tests/test_sync.py:15` | No direct Foods CRUD/search/validation tests. |

## 3. Foods Page User Stories

| User story | Acceptance criteria | Validation / error behavior | Source |
|---|---|---|---|
| As a user, I want to see my saved foods, so that I can reuse them when logging meals. | List shows food name, serving, calories, protein, carbs, fat, net carbs. | Empty list shows Arabic empty state. | `frontend/components/FoodsPage.tsx:157` |
| As a user, I want to search by food name, so that I can find foods quickly. | Search sends `q` to API; offline fallback filters cached names. | No "no search results" distinction from empty catalog. | `frontend/components/FoodsPage.tsx:37`, `backend/app/services/food.py:41` |
| As a user, I want to add a food with core nutrition, so that I can log it later. | Name, serving label, calories, protein, carbs, fat are saved. | Backend rejects negative numbers; UI does not show custom server errors. | `frontend/components/FoodsPage.tsx:191`, `backend/app/schemas.py:40` |
| As a user, I want optional detail nutrients hidden by default, so that the form stays manageable. | Optional fields are inside native `<details>`. | Empty optional fields save as `null`. | `frontend/components/FoodsPage.tsx:214` |
| As a user, I want to edit a food, so that I can correct values. | Edit fills the form and save calls `PUT /foods/{id}`. | Old diary entries keep old snapshot values. | `frontend/components/FoodsPage.tsx:109`, `backend/app/services/diary.py:29` |
| As a user, I want to delete a food, so that unused foods do not clutter the catalog. | Delete calls API or queues offline delete. | No confirmation; used diary entries keep snapshot but lose live `food_id`. | `frontend/components/FoodsPage.tsx:179`, `backend/app/models.py:91` |
| As a user, I want food values to work offline, so that I can manage the catalog without connection. | Cache stores foods; offline mutations queue. | Conflict resolution is simple replay/last-write style, not field-level merge. | `frontend/lib/db.ts:57`, `backend/app/api/routes/sync.py:74` |
| As a user, I want to enter grams, so that weighed foods are accurate. | Current system only stores optional grams per serving. | No Diary gram input or gram-to-serving conversion exists. | `frontend/components/FoodsPage.tsx:207` |

## 4. CRUD Analysis

### Create Food

Entry point is the right-side form on `/foods`.

Fields:

- Name
- Serving label
- Serving grams
- Calories
- Protein
- Carbs
- Fat
- Optional detail nutrients

Defaults are empty name/serving, `0` for required nutrition, and `null` for optional values.

Sources:

- `frontend/components/FoodsPage.tsx:11`
- `backend/app/api/routes/foods.py:19`
- `backend/app/services/food.py:52`

Duplicate names are allowed. If the client sends an existing `id`, backend updates that row instead of creating a duplicate.

### Read Foods

The frontend calls `GET /foods?q=`.

Sources:

- `frontend/lib/api.ts:82`
- `backend/app/services/food.py:38`
- `backend/app/api/routes/foods.py:24`

Backend sorts by name and optionally searches by name. Details are inline in the UI, not a separate details page, although the API supports `GET /foods/{food_id}`.

Loading and error states are weak.

### Update Food

Edit icon copies a food into the same form, excluding response-only fields.

Sources:

- `frontend/components/FoodsPage.tsx:109`
- `backend/app/api/routes/foods.py:29`
- `backend/app/services/diary.py:29`

Existing diary entries are not recalculated because Diary stores `nutrition_snapshot`.

### Delete Food

Delete icon immediately calls delete; there is no confirmation.

Sources:

- `frontend/components/FoodsPage.tsx:179`
- `backend/app/services/food.py:87`
- `backend/app/models.py:91`

The API hard-deletes the food. DB uses `ON DELETE SET NULL` for diary `food_id`, while diary nutrition survives through snapshot.

## 5. Field-by-Field Analysis

| Field | Arabic UI label | Type | Required | Default | Validation | UI / DB / API | Notes |
|---|---|---:|---:|---:|---|---|---|
| `id` | Not shown | UUID | API response | Generated | UUID | DB/API only | Client can send id for offline create. |
| `name` | الاسم | string | Yes | `""` | min length 1 backend; HTML required | `frontend/components/FoodsPage.tsx:195`, `backend/app/schemas.py:40` | No trim/max/duplicate rule. Arabic/English/symbols accepted unless browser/server rejects structurally. |
| `brand_name` | N/A | N/A | N/A | N/A | N/A | Missing | Not implemented/documented. |
| `category` | N/A | N/A | N/A | N/A | N/A | Missing | Not implemented/documented. |
| `serving_label` | الحصة | string | Yes | `""` | min length 1 backend; HTML required | `frontend/components/FoodsPage.tsx:198`, `backend/app/schemas.py:41` | Placeholder: `15 g / حبة / طبق`. Free text. |
| `serving_unit` | N/A | N/A | N/A | N/A | N/A | Missing | No unit enum/dropdown. |
| `serving_grams` | غرام الحصة | number/null | No | `null` | Backend `> 0`; UI allows `min=0` | `frontend/components/FoodsPage.tsx:207`, `backend/app/schemas.py:42` | UI/backend mismatch for `0`. |
| `calories` | السعرات | number | Yes | `0` | `>= 0` | `frontend/components/FoodsPage.tsx:208`, `backend/app/models.py:63` | No calorie/macro consistency check. |
| `protein_g` | البروتين g | number | Yes | `0` | `>= 0` | `frontend/components/FoodsPage.tsx:209` | Per serving. |
| `carb_g` | الكارب g | number | Yes | `0` | `>= 0` | `frontend/components/FoodsPage.tsx:210` | Used for net carbs. |
| `fat_g` | الدهون g | number | Yes | `0` | `>= 0` | `frontend/components/FoodsPage.tsx:211` | Per serving. |
| `fiber_g` | ألياف g | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:221` | Used in net carbs. |
| `total_sugars_g` | سكر كلي g | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:222` | Optional. |
| `added_sugar_g` | سكر مضاف g | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:223` | Optional. |
| `sodium_mg` | صوديوم mg | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:220` | Optional. |
| `cholesterol_mg` | كوليسترول mg | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:219` | Optional. |
| `saturated_fat_g` | دهون مشبعة g | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:217` | Optional. |
| `trans_fat_g` | دهون متحولة g | number/null | No | `null` | `>= 0` | `frontend/components/FoodsPage.tsx:218` | Optional. |
| `net_carbs_g` | صافي الكارب | computed number | Response only | computed | none | `backend/app/services/food.py:10` | Not stored. Can be negative. |
| `notes` | N/A | N/A | N/A | N/A | N/A | Missing | Not implemented/documented. |
| `created_at` | Not shown | datetime | DB/API | server | none exposed | `backend/app/schemas.py:80` | Not visible in UI. |
| `updated_at` | Not shown | datetime | DB/API | server | none exposed | `backend/app/schemas.py:81` | Not visible in UI. |

All numeric UI fields use number input behavior through `NumberField` in `frontend/components/FoodsPage.tsx:272`. No max length, accepted character whitelist, or custom validation messages are defined.

## 6. Nutrition Calculation Rules

Nutrition values are stored per serving, not per 100g.

Sources:

- `docs/1-SYSTEM-PLAN.md:99`
- `backend/app/schemas.py:39`

Current calculation rules:

- Net carbs: `carb_g - fiber_g`, using `0` when fiber is missing, rounded to 2 decimals.
- Diary totals: `nutrition_snapshot * quantity`, rounded to 2 decimals.
- Offline Diary totals use equivalent frontend calculation.
- Custom grams are not supported in Diary.
- `serving_grams` is metadata only in current UI.
- Decimals are accepted.
- Negative values are rejected by backend for food nutrients.
- Zero values are allowed.
- Missing optional nutrients remain `null`.
- Missing required nutrients are prevented backend-side, but frontend defaults core nutrients to `0`.
- No consistency check verifies calories against protein/carbs/fat.

Sources:

- `backend/app/services/food.py:10`
- `backend/app/services/diary.py:46`
- `frontend/lib/db.ts:210`

Example:

Food:

- `calories=120`
- `protein_g=18`
- `carb_g=7`
- `fiber_g=1`
- `quantity=2`

Totals:

- `240 kcal`
- `36g protein`
- `14g carbs`
- `12g net carbs`

Confirmed in `backend/tests/test_diary_snapshot.py:21`.

## 7. Validation and Error Messages

| Case | Current behavior | Source | Issue |
|---|---|---|---|
| All fields empty | Name/serving browser required can block; core numbers default to `0`. | `frontend/components/FoodsPage.tsx:195` | Empty numeric fields do not behave as truly empty. |
| Required text empty | HTML required; backend min length 1. | `backend/app/schemas.py:40` | No custom Arabic message. Whitespace-only likely accepted. |
| Calories empty | UI converts empty to `0`. | `frontend/components/FoodsPage.tsx:208` | User may accidentally save 0 calories. |
| Macros empty | UI converts empty to `0`. | `frontend/components/FoodsPage.tsx:209` | Same risk. |
| Negative values | Backend rejects `ge=0`; UI has `min=0`. | `backend/app/schemas.py:43` | Server error not clearly rendered. |
| Extremely high values | DB numeric precision may fail; no Pydantic max. | `backend/app/models.py:63` | Risk of unclear DB/server error. |
| Decimals | Accepted. | `frontend/components/FoodsPage.tsx:293` | Step behavior exists, no formatting display rule. |
| Arabic/English text | Accepted. | `backend/app/schemas.py:40` | No character restrictions. |
| Symbols | Accepted in text. | `backend/app/schemas.py:40` | Could be fine for personal use. |
| `serving_grams=0` | UI allows, backend rejects. | `backend/app/schemas.py:42` | Clear mismatch. |
| Server errors | `apiFetch` throws, but Foods page mutation error mostly treats as offline/local save. | `frontend/components/FoodsPage.tsx:64` | Real validation errors may be misrepresented. |

## 8. UI/UX Review

The page is mostly practical for personal use: list on one side, form on the other, optional details collapsed, Arabic RTL, and quick edit. The core form is still heavier than ideal because it always shows serving grams plus four core numbers, but it is acceptable for manual catalog entry.

Strict issues:

- Delete is too dangerous without confirmation.
- Required numeric fields are not obvious as required because they prefill `0`.
- No clear loading/error state; empty, offline fallback, and no-results can look similar.
- No duplicate warning; personal users can create repeated foods accidentally.
- Details view is useful but does not show created/updated date or whether a food is used in Diary.
- Search is simple and usable; filters are absent, which is acceptable for a simple personal v1.
- Arabic/RTL is comfortable overall, but validation messages are browser/server default rather than product language.

## 9. Mobile and Responsive Behavior

Responsive behavior exists:

- Main grid collapses below 920px.
- Form grid collapses below 640px.
- Food rows use a stable two-column layout for text/actions.
- Icon buttons are 40px targets.

Sources:

- `frontend/app/globals.css:442`
- `frontend/app/globals.css:476`
- `frontend/app/globals.css:361`
- `frontend/app/globals.css:260`

Risks:

- No explicit iPhone safe-area padding.
- Fixed install/sync UI may compete with lower content on very small screens.
- Number inputs on mobile are usable, but there is no input mode or custom decimal handling.
- No sticky save action; long optional details require scrolling.
- Delete action remains one tap on mobile, increasing accidental delete risk.

## 10. Data Model and API Mapping

| Layer | Foods mapping |
|---|---|
| DB table | `food` table with required core nutrients and optional detail nutrients. Source: `backend/app/models.py:56`. |
| Migration | Food columns and index on name. Source: `backend/alembic/versions/0001_initial.py:47`. |
| Backend schemas | `FoodBase`, `FoodCreate`, `FoodUpdate`, `FoodResponse`, `NutritionSnapshot`. Source: `backend/app/schemas.py:39`. |
| Backend service | CRUD, search, net carbs. Source: `backend/app/services/food.py:10`. |
| API routes | `/foods` GET/POST/GET id/PUT/DELETE. Source: `backend/app/api/routes/foods.py:14`. |
| Frontend page | `FoodsPage`. Source: `frontend/components/FoodsPage.tsx:130`. |
| Frontend API | `listFoods`, `createFood`, `updateFood`, `deleteFood`. Source: `frontend/lib/api.ts:82`. |
| Offline store | Dexie `foods` table. Source: `frontend/lib/db.ts:22`. |
| Sync | `/sync/push` handles food POST/PUT/DELETE. Source: `backend/app/api/routes/sync.py:74`. |
| Tests | Snapshot and sync tests only; no direct Foods CRUD validation tests. |

Mismatch:

The current repository uses `profile`, not `person`, and `diary_entry` has no `person_id`.

Source:

- `backend/app/models.py:36`

The newer plan says multiple people/profiles and person-scoped diary. Foods are still correctly global/shared, but Diary integration is not yet multi-person.

## 11. Risks and Gaps

| Risk | Severity | Impact | Evidence | Recommended fix |
|---|---:|---|---|---|
| Delete has no confirmation | High | Accidental catalog deletion | `frontend/components/FoodsPage.tsx:179` | Add confirm dialog with food name. |
| Numeric required fields default to 0 | High | Invalid foods can be saved unintentionally | `frontend/components/FoodsPage.tsx:15` | Use empty state for required numbers and show visible errors. |
| Server errors not clearly displayed | High | User may think invalid save was queued offline | `frontend/components/FoodsPage.tsx:64` | Separate validation/server errors from offline fallback. |
| Gram tracking unclear | Medium | User may assume gram-based logging works | `frontend/components/FoodsPage.tsx:207` | Either add gram logging conversion or label it as metadata. |
| `serving_grams=0` mismatch | Medium | UI accepts value backend rejects | `backend/app/schemas.py:42` | Use UI min `0.01` or backend `ge=0`. |
| No duplicate handling | Medium | Catalog clutter | `backend/app/services/food.py:52` | Warn on same/similar name. |
| No direct CRUD tests | Medium | Regressions likely | `backend/tests/test_sync.py:15` | Add API tests for create/search/update/delete/validation. |
| No explicit loading/error/no-results states | Medium | Confusing UX | `frontend/components/FoodsPage.tsx:186` | Separate states. |
| Net carbs can be negative | Low | Strange display if fiber > carbs | `backend/app/services/food.py:12` | Decide whether to clamp to 0 or allow. |
| No max numeric/text bounds in API | Low/Medium | DB errors or messy data | `backend/app/schemas.py:39` | Add practical maxes and trim text. |

## Suggested Features - Not Confirmed

These are not currently implemented or clearly documented as v1 Foods features:

- Brand name.
- Category/tag.
- Frequently used or recently logged foods.
- Per-100g nutrition mode.
- Gram-based Diary entry conversion.
- Duplicate detection by normalized name and serving.
- Food usage count before delete.
- Import/barcode/public database.

Current docs explicitly keep public food APIs and barcode scanning out of scope in `docs/1-SYSTEM-PLAN.md:208`.

## 12. Final Foods Page Feature Map

1. Food browsing: implemented list, inline cards, empty state.
2. Food creation: implemented form, online/offline save, weak visible validation.
3. Food editing: implemented same-form edit, snapshot-safe for old diary entries.
4. Food deletion: implemented hard delete, offline queue, missing confirmation.
5. Food details: implemented inline optional nutrient detail block.
6. Search/filter/sort: search by name implemented; name sort implemented; filters missing.
7. Nutrition fields: core and selected optional nutrients implemented; micros missing/out of scope.
8. Measurement and serving logic: serving-based implemented; grams metadata only; no per-100g.
9. Validation: backend basic numeric/text validation; frontend minimal HTML validation; messages weak.
10. Mobile UX: responsive grid implemented; safe-area/sticky actions not implemented.
11. Diary integration: snapshot implemented; current Diary is not person-scoped.
12. Data/API integration: solid CRUD endpoints plus Dexie/sync.
13. Tests: indirect snapshot/sync coverage; missing direct Foods API/UI validation coverage.

## 13. Final Recommendation

The Foods page is usable for light personal daily use, but it is not ready for serious long-term tracking until the risky UX and validation gaps are fixed.

Top 5 fixes before serious use:

1. Add delete confirmation.
2. Fix required numeric fields so empty is visibly invalid, not silently `0`.
3. Show clear server validation errors separately from offline queue messages.
4. Clarify or complete gram-based behavior.
5. Add direct Foods CRUD/search/validation tests.

Postpone:

- Categories.
- Brand.
- Barcode scanning.
- Public food database.
- Recipes.
- Micronutrients.
- Advanced filters.

Do not add yet:

- Multi-user permissions.
- Complex food databases.
- Recipe composition.
- Per-user food isolation.

The simplest excellent version is: fast searchable shared catalog, name + serving + four core nutrients, optional details collapsed, safe edit/delete, clear Arabic validation, and snapshot-safe Diary logging.
