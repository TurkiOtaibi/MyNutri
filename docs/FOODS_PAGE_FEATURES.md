# Foods Page Features

Single source-of-truth feature reference for the Foods page in myNutri.

Scope: Foods page only. This document covers confirmed behavior from the current codebase and existing documentation. It does not define implementation tasks.

## 1. Page Purpose

The Foods page is the manual food catalog for myNutri. It lets the personal app owner browse, search, create, edit, inspect, and delete foods.

The page is used by the single owner of the personal nutrition system. The current repository still implements a single-profile model through `profile`; the newer multi-person plan is not implemented in the codebase yet.

The Foods page supports the Diary page by providing the food records selected when logging diary entries. When a food is logged in Diary, the system stores a nutrition snapshot so later food edits, archive behavior, or food deletion do not corrupt historical diary totals.

Product decision: foods are shared across all profiles. They are not person-specific. The current codebase already stores foods globally because the `food` table has no `person_id`; however, the current codebase does not yet implement the newer multi-profile Diary model.

Sources:

- `docs/1-SYSTEM-PLAN.md:43`
- `docs/1-SYSTEM-PLAN.md:177`
- `frontend/components/FoodsPage.tsx:130`
- `backend/app/models.py:56`
- `backend/app/models.py:84`
- `backend/app/services/diary.py:29`

## Resolved Product Decisions

These decisions resolve the previously unclear Foods page scope items before user story creation.

| Decision area | Resolved product decision | Current implementation status |
|---|---|---|
| Delete confirmation | Deleting a food must require confirmation. The confirmation must identify the food being deleted. | Not implemented. Current delete fires immediately from the row action. |
| Delete behavior for unused foods | If a food has never been used in diary entries, it may be hard deleted after confirmation. | Partially implemented. Hard delete exists, but confirmation and usage check do not. |
| Delete behavior for used foods | If a food has been used in diary entries, it must not be hard deleted. It must become archived/inactive and hidden from future Diary selection. Existing diary entries remain unchanged through nutrition snapshots. | Planned. Snapshot safety exists, but archive/inactive state and usage-aware delete behavior do not. |
| Empty state | Empty catalog must show an empty state with a clear add-food action. | Partially implemented. Empty message exists; explicit add-food action in the empty state is not confirmed. |
| Loading state | Foods page must show a loading state while foods are being fetched. | Planned. Fetch state exists but no dedicated loading UI is confirmed. |
| Error state | Foods page must show a general error state for load failures that cannot be satisfied from cache. | Planned/partial. Cached fallback exists; clear general error UI is not confirmed. |
| No-results state | Search with no matching results must show a no-results state that is distinct from an empty catalog. | Planned. Current empty message can be reused for zero visible rows. |
| Food count | Count means visible displayed food rows after any active search/filter. | Implemented for current visible list count. |
| Gram-based usage | Foods can be used by serving quantity or gram quantity. Gram quantity is allowed only when serving weight in grams exists. | Planned. Serving quantity exists; gram-based usage does not. |
| Gram calculation | Gram quantity nutrition is calculated proportionally from serving data: `grams / serving_weight_g * per-serving nutrient`. | Planned. Current Diary quantity is serving-based only. |
| Missing serving weight for grams | If serving weight is missing, gram entry must be disabled or show a clear error. | Planned. |
| Duplicate handling | Exact duplicate foods must be blocked or warned before saving. For myNutri, exact duplicates should be blocked with a clear message. Current scope normalizes food name, serving label/unit text, and serving weight where available. Brand participates only if a brand field is added later. | Planned. Current code allows duplicates. |
| Negative net carbs | Net carbs must never be negative. Fiber must not exceed carbs. If fiber exceeds carbs, the form must show a field-level validation error and prevent save/update. | Planned/partial. Current backend computes `carb_g - fiber_g` and can return a negative value. |
| Numeric display precision | Nutrition values should display at up to 2 decimal places, trimming unnecessary trailing zeros. | Planned/partial. Current display precision is not explicitly formatted everywhere. |
| Long text behavior | Long food names and serving labels should wrap within the food row without overlapping actions or causing horizontal scrolling. Truncation is acceptable only if the full value remains available in details or tooltip. | Planned/partial. Responsive layout exists; exact long-text behavior is not specified in code. |

## 2. Feature Map

### 2.1 Food Browsing

- Food list display.
- Food count.
- Food summary row/card.
- Empty list state.

### 2.2 Food Search

- Search input on the Foods page.
- Server-side name search through `GET /foods?q=`.
- Cached offline fallback filters by food name.

### 2.3 Food Filtering

- No confirmed filter feature beyond name search.

### 2.4 Food Sorting

- Backend list is ordered by food name.
- Offline cached foods are ordered by name.
- No user-controlled sort UI is confirmed.

### 2.5 Food Creation

- Add food form.
- Required name, serving label, calories, protein, carbs, and fat.
- Optional serving grams and detail nutrients.
- Offline local save and sync queue.

### 2.6 Food Editing

- Existing food can be loaded into the same form.
- Save calls update behavior.
- Historical diary entries keep their original snapshots.

### 2.7 Food Deletion

- Food can be deleted from the list.
- Delete must require confirmation.
- Unused foods may be hard deleted after confirmation.
- Foods already used in diary entries must be archived/inactive, not hard deleted.
- Archived/inactive foods are hidden from future Diary selection.
- Existing diary entries remain unchanged because nutrition snapshots are used.

### 2.8 Food Details

- Inline details area shows optional nutrition fields and serving grams.
- Detail view is toggled from the food row.

### 2.9 Nutrition Fields

- Required: calories, protein, carbs, fat.
- Optional: saturated fat, trans fat, cholesterol, sodium, fiber, total sugars, added sugar.
- Computed response field: net carbs.

### 2.10 Serving and Measurement Logic

- Food values are stored per serving.
- `serving_label` is free text.
- `serving_grams` is optional metadata.
- No normalized serving unit enum is confirmed.

### 2.11 Gram-Based Usage

- Serving weight in grams can be stored.
- Foods can be used by serving quantity or gram quantity.
- Gram quantity is allowed only when serving weight in grams exists.
- Gram-based nutrition is calculated proportionally from serving data and serving weight.
- If serving weight is missing, gram entry must be disabled or show a clear error.

### 2.12 Validation

- Backend validates name and serving label length >= 1.
- Backend validates required numeric nutrients >= 0.
- Backend validates optional numeric nutrients >= 0 if provided.
- Backend validates `serving_grams > 0` if provided.
- Product scope requires fiber to be less than or equal to carbs.
- Product scope requires exact duplicate foods to be blocked with a clear message.
- Frontend uses HTML required fields and number inputs.
- Custom validation messages are not confirmed.

### 2.13 Empty/Loading/Error States

- Empty catalog must show an empty state with an add-food action.
- Loading state must be shown while foods are being fetched.
- General error state must be shown for load failures.
- Search no-results state must be distinct from empty catalog.
- Current implementation only partially satisfies this scope.

### 2.14 Mobile/Responsive Behavior

- Layout uses responsive grids.
- RTL Arabic root layout is implemented.
- Long food names and serving labels should wrap within the food row without overlapping actions or causing horizontal scrolling.
- Truncation is acceptable only if the full value remains available in details or tooltip.
- Safe-area behavior is not confirmed.

### 2.15 Diary Integration

- Diary entry creation copies current food values into `nutrition_snapshot`.
- Diary totals are calculated as `snapshot * quantity`.
- Deleting/editing a food does not corrupt old diary totals.

### 2.16 Data/API Integration

- Frontend API functions exist for list, create, update, delete.
- Backend `/foods` routes exist for list, create, read by id, update, delete.
- Food table exists in SQLModel and Alembic migration.
- Dexie stores cached foods.
- Sync route supports food create/update/delete operations.

### 2.17 Tests

- Snapshot behavior is tested.
- Sync push idempotency and food update ordering are tested indirectly.
- Direct food CRUD/search/validation tests are missing.

## 3. Feature List

### FPF-001: Food List Display

* Description: Displays saved foods as list rows/cards on the Foods page.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:157`.
* Related UI: Food row/card in the list area.
* Related API/database: `GET /foods`, `food` table.
* Related tests: No direct list display test confirmed.
* Notes: Rows show name, serving label, calories, protein, carbs, fat, and net carbs.
* Risks: Current implementation needs QA coverage for long names and layout overflow.

### FPF-002: Food Count

* Description: Shows the number of currently displayed food rows.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:139`.
* Related UI: List header count in Arabic.
* Related API/database: Uses current frontend list data.
* Related tests: No direct test confirmed.
* Notes: Count is based on `filteredFoods.length`. Product decision: count means visible displayed rows after active search/filter.
* Risks: Count behavior during failed requests still depends on the error-state implementation.

### FPF-003: Food Search by Name

* Description: Allows searching foods by name.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:143`, `backend/app/services/food.py:41`.
* Related UI: Search input with placeholder `اسم الطعام`.
* Related API/database: `GET /foods?q=`, `Food.name.ilike`.
* Related tests: No direct search test confirmed.
* Notes: Cached fallback filters by `food.name.toLowerCase().includes(...)`.
* Risks: Product scope requires a distinct no-results state, but current implementation can show the generic empty message.

### FPF-004: Food Filtering

* Description: Filtering by category, macro range, source, or other attributes.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Search by name exists, but no separate filters are confirmed.
* Risks: Should not be assumed in user stories or QA unless added later.

### FPF-005: Food Sorting

* Description: Food list is sorted by name.
* Status: Partially Implemented.
* Priority: Should Have.
* Source location: `backend/app/services/food.py:39`, `frontend/lib/db.ts:61`.
* Related UI: No sort selector.
* Related API/database: Backend query orders by `Food.name`; cached foods order by name.
* Related tests: No direct sorting test confirmed.
* Notes: Sorting direction and locale-aware Arabic sorting are not defined.
* Risks: Arabic/English mixed sorting may not match user expectations.

### FPF-006: Add New Food

* Description: Creates a new food in the shared catalog.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:191`, `backend/app/api/routes/foods.py:19`.
* Related UI: Add food form with submit button.
* Related API/database: `POST /foods`, `food` table.
* Related tests: Covered indirectly by sync test only.
* Notes: Offline create generates a client UUID and queues sync.
* Risks: Duplicate names are allowed; server validation errors are not clearly surfaced.

### FPF-007: Edit Existing Food

* Description: Updates an existing food record.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:109`, `backend/app/api/routes/foods.py:29`.
* Related UI: Edit icon loads food into the form.
* Related API/database: `PUT /foods/{food_id}`.
* Related tests: Covered indirectly by sync test only.
* Notes: Response-only fields are stripped before editing.
* Risks: No direct validation or UI regression tests confirmed.

### FPF-008: Delete Food

* Description: Removes or archives a food from the active catalog after user confirmation.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:179`, `backend/app/services/food.py:87`.
* Related UI: Delete icon button in the row.
* Related API/database: Current API uses `DELETE /foods/{food_id}` hard delete. Product scope requires usage-aware hard delete for unused foods and archive/inactive behavior for used foods.
* Related tests: No direct delete test confirmed.
* Notes: Delete confirmation is required. Used foods must be archived/inactive and hidden from future Diary selection.
* Risks: Current implementation has no confirmation, no usage check, and no archive/inactive field.

### FPF-009: Delete Safety for Diary History

* Description: Existing diary entries keep nutrition snapshots even if the original food is archived or deleted.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `backend/app/models.py:91`, `backend/app/services/diary.py:29`.
* Related UI: Product scope requires delete confirmation to warn when a food has existing diary usage.
* Related API/database: Current DB uses `diary_entry.food_id` with `ON DELETE SET NULL`; `nutrition_snapshot` stores copied values. Product scope requires archive/inactive state for used foods.
* Related tests: Snapshot test covers freeze behavior.
* Notes: Historical nutrition survives. Used foods should remain available to old diary entries through snapshots and hidden from new Diary selection.
* Risks: Current implementation can hard delete a used food and does not provide archive/inactive semantics.

### FPF-010: Food Details

* Description: Shows optional nutrient details and serving grams for a selected food.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:246`.
* Related UI: Inline detail panel toggled by details icon.
* Related API/database: Uses current `FoodResponse` data.
* Related tests: No direct UI test confirmed.
* Notes: Missing values display as `-`.
* Risks: Created/updated timestamps and diary usage count are not shown.

### FPF-011: Required Core Nutrition Fields

* Description: Stores calories, protein, carbs, and fat per serving.
* Status: Implemented.
* Priority: Must Have.
* Source location: `backend/app/schemas.py:43`, `frontend/components/FoodsPage.tsx:208`.
* Related UI: Number fields for السعرات, البروتين g, الكارب g, الدهون g.
* Related API/database: Non-null numeric columns in `food`.
* Related tests: No direct food validation test confirmed.
* Notes: Frontend default is `0`.
* Risks: Empty required numeric fields can effectively become `0`.

### FPF-012: Optional Detail Nutrients

* Description: Stores optional saturated fat, trans fat, cholesterol, sodium, fiber, total sugars, and added sugar.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:215`, `backend/app/schemas.py:47`.
* Related UI: Collapsible details section labeled `تفاصيل اختيارية`.
* Related API/database: Nullable numeric food columns.
* Related tests: No direct food validation test confirmed.
* Notes: Optional values save as `null` when empty.
* Risks: No upper bounds are defined.

### FPF-013: Net Carbs Calculation

* Description: Computes net carbs from carbs and fiber without allowing negative net carbs.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `backend/app/services/food.py:10`.
* Related UI: List row shows `صافي الكارب`.
* Related API/database: `net_carbs_g` is response-only and not stored.
* Related tests: Snapshot test checks net carbs total.
* Notes: Product decision: fiber must not exceed carbs. If fiber exceeds carbs, save/update must be blocked with a field-level validation error.
* Risks: Current implementation treats missing fiber as `0` but can return negative net carbs when fiber exceeds carbs.

### FPF-014: Serving Label

* Description: Stores a free-text serving description.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:198`, `backend/app/schemas.py:41`.
* Related UI: Field label `الحصة`, placeholder `15 g / حبة / طبق`.
* Related API/database: `serving_label`.
* Related tests: No direct validation test confirmed.
* Notes: Free text supports Arabic and English.
* Risks: No normalized unit or max length.

### FPF-015: Serving Weight in Grams

* Description: Stores optional grams per serving.
* Status: Partially Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:207`, `backend/app/schemas.py:42`.
* Related UI: Field label `غرام الحصة`.
* Related API/database: `serving_grams`.
* Related tests: No direct validation test confirmed.
* Notes: Stored/displayed but not used for diary gram logging.
* Risks: UI allows `0` while backend requires `> 0`.

### FPF-016: Gram-Based Diary Usage

* Description: Allows using a food by serving quantity or gram quantity.
* Status: Planned.
* Priority: Must Have.
* Source location: N/A.
* Related UI: Diary food entry must allow gram quantity only when serving weight in grams exists.
* Related API/database: Current diary input uses `quantity` as servings. Product scope requires gram quantity calculation based on serving weight.
* Related tests: N/A.
* Notes: Gram nutrition formula: `grams / serving_weight_g * per-serving nutrient`.
* Risks: Current implementation stores serving grams as metadata only and has no gram entry behavior.

### FPF-017: Nutrition Per 100g

* Description: Stores or displays nutrition values per 100g.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Current model is per serving only.
* Risks: Should not be included in stories unless product confirms it.

### FPF-018: Required Text Validation

* Description: Name and serving label are required.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:195`, `backend/app/schemas.py:40`.
* Related UI: HTML `required` inputs.
* Related API/database: `FoodBase.name`, `FoodBase.serving_label`.
* Related tests: No direct validation test confirmed.
* Notes: Backend minimum length is 1.
* Risks: Whitespace-only text behavior is not explicitly handled.

### FPF-019: Numeric Non-Negative Validation

* Description: Nutrition numbers must be non-negative.
* Status: Implemented.
* Priority: Must Have.
* Source location: `backend/app/schemas.py:43`, `frontend/components/FoodsPage.tsx:272`.
* Related UI: Number inputs with min behavior.
* Related API/database: Food schemas use `ge=0` for nutrients.
* Related tests: No direct food validation test confirmed.
* Notes: Optional nutrients validate only when provided.
* Risks: Server errors are not clearly shown in the UI.

### FPF-020: Decimal Numeric Input

* Description: Numeric fields accept decimal values.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:293`, `backend/app/models.py:62`.
* Related UI: Number inputs use step behavior.
* Related API/database: Numeric DB columns.
* Related tests: Snapshot totals test uses quantity multiplication but no direct food decimal test.
* Notes: Frontend number conversion uses JavaScript `Number(...)`.
* Risks: Display precision for food list values is not fully defined.

### FPF-021: Empty Food List State

* Description: Shows a clear empty catalog state with an add-food action.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:186`.
* Related UI: Arabic state note `لا توجد أطعمة بعد.`
* Related API/database: Uses frontend list length.
* Related tests: No direct UI test confirmed.
* Notes: Product scope requires empty catalog to be distinct from loading, error, and search no-results.
* Risks: Current implementation shows a message but no dedicated empty-state add-food action is confirmed.

### FPF-022: Loading State

* Description: Shows a dedicated state while the food list is loading.
* Status: Planned.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:103`.
* Related UI: N/A.
* Related API/database: React Query fetch state exists but is not rendered as a clear loading state.
* Related tests: N/A.
* Notes: Product scope requires loading state before empty state is shown.
* Risks: User may see empty state while data is still loading.

### FPF-023: Error State

* Description: Shows a clear error when food list or mutations fail.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:54`, `frontend/components/FoodsPage.tsx:64`.
* Related UI: Local note messages for saved/deleted/offline queue.
* Related API/database: `apiFetch` throws API errors; offline fallback uses cache and queue.
* Related tests: No direct UI error test confirmed.
* Notes: Product scope requires a general error state for load failures, with cached data shown only when available and clearly distinguishable from empty catalog.
* Risks: Real validation/server errors may look like offline local success.

### FPF-024: Search No-Results State

* Description: Shows a dedicated no-results state when search returns no matching foods.
* Status: Planned.
* Priority: Must Have.
* Source location: `frontend/components/FoodsPage.tsx:37`, `frontend/components/FoodsPage.tsx:186`.
* Related UI: Search input and list state area.
* Related API/database: `GET /foods?q=`.
* Related tests: No direct UI test confirmed.
* Notes: Product scope requires no-results to be distinct from an empty catalog.
* Risks: Current implementation can show the same empty message for no foods and no search matches.

### FPF-025: Success Feedback Messages

* Description: Shows save/delete success notes.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:62`, `frontend/components/FoodsPage.tsx:92`.
* Related UI: Arabic note text.
* Related API/database: Follows mutation success paths.
* Related tests: No direct UI test confirmed.
* Notes: Offline queued success has a separate Arabic message.
* Risks: Message placement and persistence duration are not defined.

### FPF-026: Offline Food Cache

* Description: Stores fetched foods in IndexedDB for offline reads.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/lib/db.ts:22`, `frontend/lib/db.ts:57`.
* Related UI: Foods page falls back to cached foods on query failure.
* Related API/database: Dexie `foods` table.
* Related tests: Sync test exists, but no direct offline UI test confirmed.
* Notes: Cached foods are ordered by name.
* Risks: Stale cache state is not clearly communicated.

### FPF-027: Offline Food Mutation Queue

* Description: Queues create/update/delete food operations when API mutation fails.
* Status: Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:69`, `frontend/components/FoodsPage.tsx:80`, `frontend/components/FoodsPage.tsx:97`.
* Related UI: Offline local save/delete notes.
* Related API/database: Dexie mutation queue, `/sync/push`.
* Related tests: `backend/tests/test_sync.py:15`.
* Notes: Client-generated UUIDs support replayable creates.
* Risks: Conflict handling is simple; user-facing conflict behavior is not defined.

### FPF-028: Responsive Layout

* Description: Foods page layout adapts across desktop and mobile widths.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/app/globals.css:442`, `frontend/app/globals.css:476`.
* Related UI: Workspace grid, form grid, food row.
* Related API/database: N/A.
* Related tests: No visual/mobile test confirmed.
* Notes: Grid collapses at responsive breakpoints.
* Risks: Long text and bottom fixed UI overlap behavior need QA coverage.

### FPF-029: RTL Arabic Layout

* Description: Page is Arabic-first and RTL.
* Status: Implemented.
* Priority: Must Have.
* Source location: `frontend/app/layout.tsx:23`, `frontend/components/FoodsPage.tsx:130`.
* Related UI: Arabic labels and RTL document direction.
* Related API/database: N/A.
* Related tests: No direct RTL UI test confirmed.
* Notes: Mixed Arabic/English food names are possible.
* Risks: Mixed LTR/RTL long text wrapping requires QA coverage.

### FPF-030: Accessibility Basics

* Description: Uses labels for form inputs and titles on icon buttons.
* Status: Partially Implemented.
* Priority: Should Have.
* Source location: `frontend/components/FoodsPage.tsx:169`, `frontend/components/FoodsPage.tsx:284`.
* Related UI: Labeled fields, icon buttons with `title`.
* Related API/database: N/A.
* Related tests: No accessibility test confirmed.
* Notes: Native `<details>` is used for optional details.
* Risks: Icon buttons lack confirmed `aria-label`; keyboard/focus behavior is not tested.

### FPF-031: API CRUD Endpoints

* Description: Backend exposes CRUD routes for foods.
* Status: Implemented.
* Priority: Must Have.
* Source location: `backend/app/api/routes/foods.py:14`.
* Related UI: Foods page API functions.
* Related API/database: `/foods`, `/foods/{food_id}`.
* Related tests: No direct food route CRUD test confirmed.
* Notes: Routes require single-user auth dependency.
* Risks: CRUD endpoint behavior lacks direct tests.

### FPF-032: Food Database Table

* Description: Stores food catalog records.
* Status: Implemented.
* Priority: Must Have.
* Source location: `backend/app/models.py:56`, `backend/alembic/versions/0001_initial.py:47`.
* Related UI: All Foods page operations.
* Related API/database: `food` table, `ix_food_name`.
* Related tests: No direct DB model test confirmed.
* Notes: Food name is indexed.
* Risks: No uniqueness constraint for duplicate food names.

### FPF-033: Diary Snapshot Integration

* Description: Diary entries copy the food's current nutritional values at log time.
* Status: Implemented.
* Priority: Must Have.
* Source location: `backend/app/services/diary.py:29`, `frontend/lib/db.ts:232`.
* Related UI: Diary page uses foods when adding entries.
* Related API/database: `nutrition_snapshot`.
* Related tests: `backend/tests/test_diary_snapshot.py:5`.
* Notes: Snapshot protects history from future food edits.
* Risks: Current code is not person-scoped.

### FPF-034: Food Duplicate Handling

* Description: Prevents exact duplicate foods before save.
* Status: Planned.
* Priority: Must Have.
* Source location: N/A.
* Related UI: Create/edit form must show a clear duplicate message.
* Related API/database: No current unique constraint on food name or serving data.
* Related tests: N/A.
* Notes: Product decision: exact duplicates are blocked. Duplicate matching uses normalized food name, serving label/unit text, and serving weight where available. Brand participates only if a brand field is added later.
* Risks: Current implementation allows duplicate foods and has no duplicate-warning UI.

### FPF-035: Food-Related Tests

* Description: Automated tests for food behavior.
* Status: Partially Implemented.
* Priority: Must Have.
* Source location: `backend/tests/test_diary_snapshot.py:5`, `backend/tests/test_sync.py:15`.
* Related UI: N/A.
* Related API/database: Snapshot and sync behavior.
* Related tests: Existing tests are indirect for Foods page.
* Notes: Food route validation/search/delete tests are missing.
* Risks: CRUD regressions may pass unnoticed.

### FPF-036: Brand Field

* Description: Stores a food brand name.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Not confirmed by current code or docs.
* Risks: Do not include in v1 user stories unless confirmed.

### FPF-037: Category Field

* Description: Stores food category or tag.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Not confirmed by current code or docs.
* Risks: Adding categories can increase data-entry friction.

### FPF-038: Food Source or Type

* Description: Marks food as manual/imported/custom or similar source type.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Public food database import is out of scope in current docs.
* Risks: Source/type is unnecessary until imports exist.

### FPF-039: Notes Field

* Description: Stores free-text notes about a food.
* Status: Missing.
* Priority: Could Have.
* Source location: N/A.
* Related UI: N/A.
* Related API/database: N/A.
* Related tests: N/A.
* Notes: Not confirmed by current code or docs.
* Risks: Could add form complexity without daily value.

### FPF-040: Created and Updated Timestamps

* Description: Tracks creation and update timestamps for foods.
* Status: Partially Implemented.
* Priority: Should Have.
* Source location: `backend/app/models.py:74`, `backend/app/schemas.py:80`.
* Related UI: Not displayed on Foods page.
* Related API/database: `created_at`, `updated_at`.
* Related tests: No direct test confirmed.
* Notes: Returned in API response.
* Risks: Not visible to the user when auditing food changes.

## 4. Field Inventory

| Field name | Label | Type | Required/Optional | Default value | Placeholder | Allowed values | Min/max rules | Validation message | UI location | Database/API mapping | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Food name / `name` | الاسم | Text | Required | Empty string in frontend draft | None | Text; Arabic/English/symbols not restricted | Backend min length 1; product scope requires normalized duplicate check | Duplicate message required by product scope; current custom message not implemented | Form, list row | `food.name`, `FoodBase.name` | Duplicate matching normalizes name text. |
| Brand | N/A | N/A | Missing | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Suggested only, not confirmed. |
| Category | N/A | N/A | Missing | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Suggested only, not confirmed. |
| Serving size / `serving_label` | الحصة | Text | Required | Empty string in frontend draft | `15 g / حبة / طبق` | Free text | Backend min length 1; no max confirmed | Browser/backend default, no custom message confirmed | Form, list row | `food.serving_label`, `FoodBase.serving_label` | Represents serving description, not a normalized unit. |
| Serving unit | N/A | N/A | Missing | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No unit dropdown/enum confirmed. |
| Serving weight in grams / `serving_weight_g` product term, current `serving_grams` field | غرام الحصة | Number | Optional for serving use; required for gram-based usage | `null` | None | Positive number if provided | Backend `> 0`; product scope requires gram entry disabled/error when missing | Clear error required when gram entry is attempted without serving weight | Form, details; future gram-entry UI | `food.serving_grams`, `FoodBase.serving_grams` | UI/backend mismatch for 0 remains an implementation gap. |
| Calories / `calories` | السعرات | Number | Required | `0` | None | Number >= 0 | Backend `ge=0`; DB Numeric(8,2) | Backend/default browser message, no custom message confirmed | Form, list row | `food.calories`, `FoodBase.calories` | Empty UI value can become 0. |
| Protein / `protein_g` | البروتين g | Number | Required | `0` | None | Number >= 0 | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Form, list row | `food.protein_g`, `FoodBase.protein_g` | Per serving. |
| Carbs / `carb_g` | الكارب g | Number | Required | `0` | None | Number >= 0 | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Form, list row | `food.carb_g`, `FoodBase.carb_g` | Used for net carbs. |
| Fat / `fat_g` | الدهون g | Number | Required | `0` | None | Number >= 0 | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Form, list row | `food.fat_g`, `FoodBase.fat_g` | Per serving. |
| Fiber / `fiber_g` | ألياف g | Number | Optional | `null` | None | Number >= 0 if provided and must not exceed carbs | Backend `ge=0`; product scope requires `fiber_g <= carb_g` | Field-level error required when fiber exceeds carbs | Optional form details, details panel | `food.fiber_g`, `FoodBase.fiber_g` | Used in net carbs; current backend does not enforce fiber <= carbs. |
| Total sugar / `total_sugars_g` | سكر كلي g | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.total_sugars_g`, `FoodBase.total_sugars_g` | Optional display only. |
| Added sugar / `added_sugar_g` | سكر مضاف g | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.added_sugar_g`, `FoodBase.added_sugar_g` | Optional display only. |
| Sodium / `sodium_mg` | صوديوم mg | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(8,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.sodium_mg`, `FoodBase.sodium_mg` | Optional display only. |
| Cholesterol / `cholesterol_mg` | كوليسترول mg | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(8,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.cholesterol_mg`, `FoodBase.cholesterol_mg` | Optional display only. |
| Saturated fat / `saturated_fat_g` | دهون مشبعة g | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.saturated_fat_g`, `FoodBase.saturated_fat_g` | Optional display only. |
| Trans fat / `trans_fat_g` | دهون متحولة g | Number | Optional | `null` | None | Number >= 0 if provided | Backend `ge=0`; DB Numeric(7,2) | Backend/default browser message, no custom message confirmed | Optional form details, details panel | `food.trans_fat_g`, `FoodBase.trans_fat_g` | Optional display only. |
| Net carbs / `net_carbs_g` | صافي الكارب | Number | Computed | Computed | N/A | Computed number, never below 0 | Product scope requires fiber <= carbs and net carbs not negative | N/A for direct input; fiber field shows error if invalid | List row, API response | `FoodResponse.net_carbs_g` | Current implementation can return negative values if fiber exceeds carbs. |
| Active/archive status / `is_active` or `archived_at` | Not implemented | Boolean/datetime | Planned | Active by default | N/A | Active or archived/inactive | N/A | N/A | Future list/detail/admin behavior | Planned DB/API field | Required by product scope for used-food delete behavior; exact field name is technical design, not decided here. |
| Notes | N/A | N/A | Missing | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Suggested only, not confirmed. |
| Created date / `created_at` | Not shown | Datetime | API/DB | Server timestamp | N/A | Datetime | N/A | N/A | Not shown | `food.created_at`, `FoodResponse.created_at` | Returned by API, not displayed. |
| Updated date / `updated_at` | Not shown | Datetime | API/DB | Server timestamp | N/A | Datetime | N/A | N/A | Not shown | `food.updated_at`, `FoodResponse.updated_at` | Returned by API, not displayed. |

## 5. CRUD Coverage

### 5.1 Create Food

* Entry point: Add food form on `/foods`.
* Expected behavior: User enters required core fields and optional details, then saves a food to the catalog.
* Validation: Name and serving label required; calories, protein, carbs, fat required and non-negative; optional nutrient fields non-negative if provided; serving weight must be positive if provided; fiber must not exceed carbs; exact duplicate foods must be blocked with a clear duplicate message.
* Success behavior: Form resets, note says `تم حفظ الطعام.`, list invalidates/refetches. Offline fallback saves locally and queues sync with a local success note.
* Error behavior: Field-level validation errors are required for duplicate foods and fiber greater than carbs. Current implementation does not clearly display validation/server errors.
* Edge cases: Duplicate food, empty numeric values becoming 0, serving grams 0 mismatch, extremely high values, Arabic/English names, fiber greater than carbs.
* Gaps: Duplicate blocking, fiber <= carbs validation, custom validation messages, and direct API validation tests are not implemented.

Sources:

- `frontend/components/FoodsPage.tsx:54`
- `frontend/components/FoodsPage.tsx:62`
- `backend/app/api/routes/foods.py:19`
- `backend/app/services/food.py:52`

### 5.2 Read Foods

* Entry point: Opening `/foods`; frontend calls `listFoods(search)`.
* Expected behavior: Display active saved foods with summary nutrition values and visible-row count. Archived/inactive foods must be hidden from future Diary selection and should not appear as normal active catalog items.
* Validation: No user input validation except search text handling.
* Success behavior: Foods are cached locally after successful fetch.
* Error behavior: Product scope requires distinct loading, empty, no-results, and general error states. Current implementation falls back to cached foods; clear general error state is not implemented.
* Edge cases: Empty catalog, no search results, cached stale foods, duplicate names from legacy data, large catalogs, long names, archived/inactive foods.
* Gaps: Dedicated loading state, general error state, no-results state, active/archived filtering, and direct list/search tests are not implemented.

Sources:

- `frontend/components/FoodsPage.tsx:37`
- `frontend/components/FoodsPage.tsx:40`
- `backend/app/api/routes/foods.py:14`
- `backend/app/services/food.py:38`

### 5.3 Update Food

* Entry point: Edit icon on a food row.
* Expected behavior: Selected food values load into the form; save updates the food.
* Validation: Same numeric/text constraints as create, with update schema fields optional. Updating a food must also block exact duplicates and fiber greater than carbs.
* Success behavior: Form resets, note says food was saved, list invalidates/refetches. Offline fallback updates local cache and queues PUT.
* Error behavior: Field-level errors are required for duplicate conflicts and fiber greater than carbs. Current server validation errors are not clearly displayed.
* Edge cases: Editing only name, editing only nutrition, setting optional fields to empty, setting serving grams to 0, editing food already used in Diary, edit creates exact duplicate.
* Gaps: Duplicate blocking, fiber <= carbs validation, no explicit warning that historical diary entries keep old values, and no direct update validation test.

Sources:

- `frontend/components/FoodsPage.tsx:109`
- `backend/app/api/routes/foods.py:29`
- `backend/app/services/food.py:75`
- `backend/app/services/diary.py:29`

### 5.4 Delete Food

* Entry point: Delete icon on a food row.
* Expected behavior: Delete requires confirmation. If the food is unused, it may be hard deleted. If the food has diary usage, it must be archived/inactive and hidden from future Diary selection. Existing diary entries remain unchanged through snapshots.
* Validation: Food id must exist for normal delete/archive. System must determine whether the food has diary usage before choosing hard delete or archive behavior.
* Success behavior: User receives a clear success message. Active food list refreshes. Archived used foods disappear from active selection.
* Error behavior: Delete errors must be shown clearly. Current implementation has no confirmation and server errors are not clearly displayed.
* Edge cases: Food used in diary, food unused, offline delete/archive, deleting already removed food through sync, accidental tap on mobile.
* Gaps: Confirmation dialog, usage check, archive/inactive field, archive behavior, and user-facing explanation of diary snapshot safety are not implemented.

Sources:

- `frontend/components/FoodsPage.tsx:89`
- `frontend/components/FoodsPage.tsx:179`
- `backend/app/api/routes/foods.py:34`
- `backend/app/models.py:91`
- `backend/app/api/routes/sync.py:103`

## 6. Nutrition Calculation Rules

### Values Per Serving

Implemented. All stored food nutrition values represent one serving, matching `serving_label`.

Sources:

- `docs/1-SYSTEM-PLAN.md:99`
- `backend/app/schemas.py:39`

### Values Per 100g

Missing. No per-100g fields, conversion, or UI mode is confirmed.

### Serving Quantity

Implemented in Diary. Diary entry `quantity` is the number of servings and can be decimal.

Sources:

- `docs/1-SYSTEM-PLAN.md:106`
- `backend/app/schemas.py:109`

### Gram Quantity

Planned product scope. Foods can be used by gram quantity only when serving weight in grams exists.

Calculation:

`gram_multiplier = entered_grams / serving_weight_g`

Each nutrient total is calculated as:

`per_serving_nutrient * gram_multiplier`

If serving weight is missing, gram entry must be disabled or must show a clear field-level error. Current implementation stores `serving_grams` but does not support gram-based Diary usage.

### Decimal Values

Implemented. Numeric UI fields use number input behavior, backend fields are numeric, and diary totals round to two decimals.

Sources:

- `frontend/components/FoodsPage.tsx:293`
- `backend/app/models.py:62`
- `backend/app/services/diary.py:51`

### Rounding

Implemented for current computed values. Net carbs and diary totals are rounded to two decimals in backend services. Frontend offline totals also round to two decimals.

Product decision: nutrition values should display at up to 2 decimal places and trim unnecessary trailing zeros.

Sources:

- `backend/app/services/food.py:12`
- `backend/app/services/diary.py:51`
- `frontend/lib/db.ts:210`

### Zero Values

Implemented. Food nutrient values can be zero because schemas use `ge=0`. Frontend required nutrition draft defaults to `0`.

Risk: Empty required numeric inputs can become `0`, which may hide missing data.

### Negative Values

Negative nutrient values are rejected by backend validation.

Product decision: net carbs must not become negative. Fiber must not exceed carbs. If `fiber_g > carb_g`, save/update must be blocked with a field-level validation error on fiber. Net carbs display should never show a value below 0.

Sources:

- `backend/app/schemas.py:43`
- `backend/app/services/food.py:12`

### Missing Values

Required core nutrients should not be missing in saved foods. Optional nutrients can be `null`. Food details display missing optional values as `-`.

Sources:

- `backend/app/schemas.py:43`
- `backend/app/schemas.py:47`
- `frontend/components/FoodsPage.tsx:263`

### Snapshot Behavior When Used in Diary Entries

Implemented. Diary copies the food values at log time into `nutrition_snapshot`; totals are calculated from snapshot multiplied by quantity. Old diary totals are protected from later food edits or food deletion.

Sources:

- `backend/app/services/diary.py:29`
- `backend/app/services/diary.py:46`
- `backend/tests/test_diary_snapshot.py:5`

## 7. Risks and Gaps

| Risk | Severity | Impact | Evidence | Recommended fix |
|---|---:|---|---|---|
| Delete confirmation not implemented | High | Accidental food deletion, especially on mobile | `frontend/components/FoodsPage.tsx:179` | Implement required confirmation with food name. |
| Used-food archive behavior not implemented | High | Used foods can be hard deleted instead of archived/inactive | `backend/app/services/food.py:87`, `backend/app/models.py:56` | Add usage-aware delete behavior and archive/inactive state. |
| Required numeric fields default to 0 | High | User can save incomplete nutrition accidentally | `frontend/components/FoodsPage.tsx:15` | Use empty state for required numeric fields and visible validation. |
| Server validation errors are not clearly displayed | High | User may think invalid data was saved locally | `frontend/components/FoodsPage.tsx:64` | Separate validation/server errors from offline fallback. |
| Loading state is missing | Medium | Empty catalog and loading state can be confused | `frontend/components/FoodsPage.tsx:103` | Add explicit loading indicator. |
| Error/no-results/empty states are not distinct | Medium | User may misunderstand failed load or search result | `frontend/components/FoodsPage.tsx:186` | Separate empty, no-results, and error states. |
| Serving grams UI/backend mismatch | Medium | UI allows 0 while backend rejects 0 | `backend/app/schemas.py:42`, `frontend/components/FoodsPage.tsx:207` | Align UI min with backend or change backend rule. |
| Gram-based usage is not implemented | Medium | User cannot log by grams even though product scope allows it | `frontend/components/FoodsPage.tsx:207` | Implement serving-weight-gated gram entry and proportional calculation. |
| Duplicate blocking is not implemented | Medium | Catalog clutter and wrong food selection | `backend/app/services/food.py:52` | Block exact duplicates using normalized name, serving label/unit text, and serving weight. |
| Fiber <= carbs validation is not implemented | Medium | Net carbs can become negative | `backend/app/services/food.py:12` | Add field-level validation on fiber and prevent save/update when fiber exceeds carbs. |
| No direct Foods CRUD tests | Medium | API regressions can pass unnoticed | `backend/tests/test_sync.py:15` | Add direct tests for create/list/search/update/delete/validation. |
| Mixed Arabic/English long text behavior is not tested | Low | Long names may affect readability | `frontend/app/layout.tsx:23` | Implement and test wrapping/no-overlap behavior. |
| Created/updated timestamps are not visible | Low | User cannot inspect recency from UI | `backend/app/schemas.py:80` | Show timestamps only if useful for personal auditing. |

## 8. Suggested Features — Not Confirmed

These are useful ideas but are not confirmed by the current codebase or docs:

- Brand field.
- Category or tags.
- Food source/type.
- Notes field.
- Frequently used foods.
- Recently logged foods.
- Per-100g nutrition mode.
- Delete undo.

Do not mix these into confirmed v1 user stories unless product scope changes.

## 9. Final Summary

### Is the Foods Page Feature Scope Clear?

Yes. The product scope is now clear enough for user story generation.

Confirmed scope: shared manual food catalog across profiles, list/search/add/edit/delete/details, per-serving nutrition, gram-based usage when serving weight exists, optional detail nutrients, non-negative net carbs, duplicate blocking, distinct loading/empty/no-results/error states, offline cache/sync, and diary snapshot integration.

### Top 5 Must-Have Features

1. Food list display.
2. Add new food.
3. Edit existing food.
4. Confirmed delete behavior with confirmation, archive/inactive handling for used foods, and diary-safe snapshots.
5. Required per-serving nutrition fields with duplicate and net-carb validation.

### Top 5 Risks

1. Current code does not implement confirmed delete confirmation or used-food archive behavior.
2. Required numeric fields default to `0`.
3. Server validation errors are not clearly displayed.
4. Current code does not implement distinct loading/error/no-results states.
5. Current code does not implement confirmed gram-based usage or duplicate blocking.

### What Should Be Handled Before Writing User Stories

No blocking product decisions remain for the requested focus areas. User stories can now be written against the resolved scope.

Use these story-generation rules:

1. Count means visible displayed rows after active search/filter.
2. Empty catalog, no-results, loading, and general error states must be separate.
3. Gram entry is allowed only when serving weight in grams exists.
4. Exact duplicate foods are blocked before save.
5. Fiber cannot exceed carbs; net carbs must never display below `0`.

### What Should Be Postponed

1. Brand/category/source fields.
2. Public food database import.
3. Barcode scanning.
4. Recipes.
5. Micronutrient expansion.
6. Complex filters.
7. Per-user food isolation.
