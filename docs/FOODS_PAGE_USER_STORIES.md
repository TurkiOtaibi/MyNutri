# Foods Page User Stories

## 1. Overview

This file defines user stories for the myNutri Foods page based only on `docs/FOODS_PAGE_FEATURES.md`.

The Foods page is the shared manual food catalog used by the Diary page. It supports browsing, search, food CRUD, nutrition entry, serving and gram-based usage rules, validation, offline behavior, and diary snapshot safety.

This file is ready for implementation planning and QA test case generation. It does not change product scope, application code, or data models.

Note: `FOODS_PAGE_FEATURES.md` currently contains 40 `FPF-*` entries after the search no-results state was added. This file covers all 40.

## 2. User Story Map

### 2.1 Browse Foods

- `US-FPF-001-1` - Browse active saved foods.
- `US-FPF-002-1` - View visible food count.
- `US-FPF-005-1` - View foods sorted by name.
- `US-FPF-040-1` - Retain food timestamps.

### 2.2 Search/Filter/Sort Foods

- `US-FPF-003-1` - Search foods by name.
- `US-FPF-004-1` - Keep advanced filters out of current scope.
- `US-FPF-005-1` - View foods sorted by name.
- `US-FPF-024-1` - See search no-results state.

### 2.3 Create Food

- `US-FPF-006-1` - Add a new food.
- `US-FPF-011-1` - Enter required core nutrition.
- `US-FPF-012-1` - Enter optional detail nutrients.
- `US-FPF-014-1` - Enter serving label.
- `US-FPF-015-1` - Enter serving weight in grams.
- `US-FPF-018-1` - Validate required text.
- `US-FPF-019-1` - Validate non-negative numbers.
- `US-FPF-020-1` - Enter decimal numbers.
- `US-FPF-034-1` - Block exact duplicates.

### 2.4 Edit Food

- `US-FPF-007-1` - Edit an existing food.
- `US-FPF-011-1` - Maintain required core nutrition.
- `US-FPF-012-1` - Maintain optional detail nutrients.
- `US-FPF-013-1` - Prevent negative net carbs.
- `US-FPF-034-1` - Block duplicate edits.

### 2.5 Delete/Archive Food

- `US-FPF-008-1` - Confirm delete and remove/archive food.
- `US-FPF-009-1` - Preserve diary history when food is archived or deleted.

### 2.6 Food Details

- `US-FPF-010-1` - View food detail nutrients.
- `US-FPF-040-1` - Retain timestamp metadata.

### 2.7 Nutrition and Serving Logic

- `US-FPF-011-1` - Required core nutrients.
- `US-FPF-012-1` - Optional nutrients.
- `US-FPF-013-1` - Net carbs.
- `US-FPF-014-1` - Serving label.
- `US-FPF-015-1` - Serving weight.
- `US-FPF-016-1` - Gram-based usage.
- `US-FPF-017-1` - Keep per-100g mode out of current scope.
- `US-FPF-020-1` - Decimal values and precision.

### 2.8 Validation and Errors

- `US-FPF-018-1` - Required text validation.
- `US-FPF-019-1` - Numeric non-negative validation.
- `US-FPF-023-1` - General error state.
- `US-FPF-034-1` - Duplicate blocking.

### 2.9 Empty/Loading/No-Results States

- `US-FPF-021-1` - Empty catalog state.
- `US-FPF-022-1` - Loading state.
- `US-FPF-023-1` - General error state.
- `US-FPF-024-1` - Search no-results state.

### 2.10 Mobile UX

- `US-FPF-028-1` - Responsive layout.
- `US-FPF-029-1` - RTL Arabic layout.
- `US-FPF-030-1` - Accessibility basics.

### 2.11 Diary Integration

- `US-FPF-016-1` - Gram-based diary usage.
- `US-FPF-033-1` - Diary snapshot integration.
- `US-FPF-009-1` - Delete/archive safety for diary history.

### 2.12 Data/API Behavior

- `US-FPF-026-1` - Offline food cache.
- `US-FPF-027-1` - Offline mutation queue.
- `US-FPF-031-1` - API CRUD behavior.
- `US-FPF-032-1` - Food database persistence.

### 2.13 QA/Testing

- `US-FPF-035-1` - Food-related QA coverage.

## 3. Detailed User Stories

### US-FPF-001-1: Browse Active Saved Foods

* Related feature: FPF-001
* Priority: Must Have
* User story: As a user, I want to view my active saved foods in a list, so that I can reuse them when logging meals.
* Preconditions:
  * The user is on the Foods page.
  * At least one active food exists.
* Acceptance criteria:
  * Given active foods exist
    When the Foods page loads successfully
    Then each active food is shown as a separate row or card.
  * Given a food is archived/inactive
    When the active food list is displayed
    Then the archived/inactive food is not shown as a normal active catalog item.
  * Given a food row is shown
    When the user scans the row
    Then the row shows name, serving label, calories, protein, carbs, fat, and net carbs.
* Validation rules:
  * No user input is validated in this story.
  * Displayed records must be valid food records from the active catalog.
* Edge cases:
  * One food.
  * Many foods.
  * Duplicate legacy data.
  * Very long food names.
* UI behavior:
  * Rows must be visually distinct.
  * Long names must not overlap action buttons.
* Error behavior:
  * Load failure is handled by `US-FPF-023-1`.
* Mobile behavior:
  * Rows must remain readable without horizontal scrolling.
* Data/API notes:
  * Uses food list data from `GET /foods` or cached foods.
* QA test scenarios:
  * Verify one active food appears.
  * Verify multiple active foods appear.
  * Verify inactive foods are excluded once archive behavior exists.
* Risks/gaps:
  * Long-name layout needs QA coverage.
  * Active/archive filtering is not implemented.

### US-FPF-002-1: View Visible Food Count

* Related feature: FPF-002
* Priority: Should Have
* User story: As a user, I want to see how many foods are currently visible, so that I understand the size of the displayed list.
* Preconditions:
  * The Foods page has loaded list data or a resolved state.
* Acceptance criteria:
  * Given foods are visible
    When the list is rendered
    Then the count equals the number of visible food rows.
  * Given a search is active
    When matching foods are displayed
    Then the count reflects only visible matching rows.
  * Given no foods are visible
    When an empty or no-results state is displayed
    Then the count is `0` or is not shown in a misleading way.
* Validation rules:
  * Count must be a non-negative integer.
* Edge cases:
  * Count `0`.
  * Count `1`.
  * Large counts.
* UI behavior:
  * Count appears near the list header.
* Error behavior:
  * Count must not show stale data during a general error state.
* Mobile behavior:
  * Count remains readable or can be omitted if space is constrained.
* Data/API notes:
  * Count is based on visible rows, not total server catalog size.
* QA test scenarios:
  * Verify count matches visible rows with and without search.
* Risks/gaps:
  * Failed-request count behavior depends on error-state implementation.

### US-FPF-003-1: Search Foods by Name

* Related feature: FPF-003
* Priority: Must Have
* User story: As a user, I want to search foods by name, so that I can find the right food quickly.
* Preconditions:
  * The food catalog has one or more foods.
* Acceptance criteria:
  * Given the user enters a search term
    When matching food names exist
    Then only matching visible food rows are shown.
  * Given the search term is cleared
    When the list refreshes
    Then the active food list is shown again.
  * Given cached foods are used offline
    When a search term is entered
    Then cached foods are filtered by name.
* Validation rules:
  * Search text does not create or modify food records.
  * Empty search means no search filter.
* Edge cases:
  * Arabic text.
  * English text.
  * Mixed Arabic/English names.
  * Symbols in food names.
* UI behavior:
  * Search input remains visible above the list.
* Error behavior:
  * No matches use `US-FPF-024-1`.
  * Load failure uses `US-FPF-023-1`.
* Mobile behavior:
  * Search input must be easy to tap and type into.
* Data/API notes:
  * Online search uses `GET /foods?q=`.
  * Offline fallback searches cached food names.
* QA test scenarios:
  * Search by exact name.
  * Search by partial name.
  * Clear search and verify full active list returns.
* Risks/gaps:
  * No direct search test currently exists.

### US-FPF-004-1: Keep Advanced Food Filters Out of Current Scope

* Related feature: FPF-004
* Priority: Could Have
* User story: As a user, I want the Foods page to stay simple without unconfirmed advanced filters, so that daily food entry remains fast.
* Preconditions:
  * The current confirmed scope includes name search only.
* Acceptance criteria:
  * Given the current Foods page scope
    When user stories are implemented
    Then category, macro-range, source, and advanced filter controls are not required.
  * Given the user needs to find food
    When using the current scope
    Then name search is the confirmed discovery method.
* Validation rules:
  * No filter-specific validation applies.
* Edge cases:
  * User has many foods; search remains the supported method.
* UI behavior:
  * No unconfirmed filter UI should be introduced by these stories.
* Error behavior:
  * N/A.
* Mobile behavior:
  * Avoid adding filter controls that increase mobile complexity.
* Data/API notes:
  * No filter API is required beyond search query.
* QA test scenarios:
  * Verify no user story requires category/macro/source filtering.
* Risks/gaps:
  * Advanced filtering is intentionally postponed.

### US-FPF-005-1: View Foods Sorted by Name

* Related feature: FPF-005
* Priority: Should Have
* User story: As a user, I want foods to appear in a predictable name order, so that I can scan my catalog consistently.
* Preconditions:
  * Multiple foods exist.
* Acceptance criteria:
  * Given multiple foods exist
    When the Foods page loads
    Then foods are ordered by name.
  * Given cached foods are displayed
    When the cached list is used
    Then cached foods are also ordered by name.
  * Given no sort control exists
    When the user views the list
    Then no manual sorting behavior is expected.
* Validation rules:
  * No user input validation applies.
* Edge cases:
  * Arabic names.
  * English names.
  * Mixed-language names.
  * Same or similar names.
* UI behavior:
  * No sort selector is required.
* Error behavior:
  * Sorting is not shown if list load fails and no cache exists.
* Mobile behavior:
  * Order must be consistent on mobile and desktop.
* Data/API notes:
  * Backend and cache sort by name.
* QA test scenarios:
  * Verify sorted order from API result.
  * Verify cached sorted order.
* Risks/gaps:
  * Locale-aware Arabic/English sort behavior may not match expectations.

### US-FPF-006-1: Add New Food

* Related feature: FPF-006
* Priority: Must Have
* User story: As a user, I want to add a new food, so that I can log it later in my diary.
* Preconditions:
  * The user is on the Foods page.
* Acceptance criteria:
  * Given valid required fields are entered
    When the user saves the food
    Then the food is added to the active catalog.
  * Given the save succeeds
    When the list refreshes
    Then the new food appears in the list.
  * Given the device is offline or API save fails but local queue is available
    When the user saves
    Then the food is saved locally and queued for sync with clear feedback.
* Validation rules:
  * Name and serving label are required.
  * Calories, protein, carbs, and fat are required and non-negative.
  * Exact duplicates are blocked.
  * Fiber cannot exceed carbs.
* Edge cases:
  * Arabic name.
  * English name.
  * Decimal nutrition values.
  * Duplicate food.
* UI behavior:
  * Add form remains visible and usable.
  * Success feedback is shown.
* Error behavior:
  * Field-level validation errors are shown for invalid inputs.
  * General save errors are shown separately from offline queued success.
* Mobile behavior:
  * Form fields must be usable on small screens.
* Data/API notes:
  * Online create uses `POST /foods`.
  * Offline create uses local UUID and mutation queue.
* QA test scenarios:
  * Create valid food.
  * Attempt duplicate create.
  * Create while offline and verify queued state.
* Risks/gaps:
  * Duplicate blocking and clear server validation errors are not implemented.

### US-FPF-007-1: Edit Existing Food

* Related feature: FPF-007
* Priority: Must Have
* User story: As a user, I want to edit an existing food, so that I can correct its serving or nutrition values.
* Preconditions:
  * At least one active food exists.
* Acceptance criteria:
  * Given a food exists
    When the user selects edit
    Then the form is populated with that food's editable fields.
  * Given valid changes are saved
    When the update succeeds
    Then the food list shows the updated summary.
  * Given the edited food was previously used in Diary
    When the food is saved
    Then existing diary entries remain unchanged because they use snapshots.
* Validation rules:
  * Same validation as create.
  * Edit cannot create an exact duplicate of another food.
  * Fiber cannot exceed carbs.
* Edge cases:
  * Editing only name.
  * Editing only nutrition.
  * Clearing optional fields.
  * Editing a used food.
* UI behavior:
  * Edit mode is visually clear.
  * Cancel returns the form to add mode.
* Error behavior:
  * Field-level and general errors are visible.
* Mobile behavior:
  * Edit form remains usable on small screens.
* Data/API notes:
  * Online update uses `PUT /foods/{food_id}`.
* QA test scenarios:
  * Edit name.
  * Edit nutrition.
  * Attempt duplicate edit.
* Risks/gaps:
  * Direct edit validation tests are missing.

### US-FPF-008-1: Confirm Delete and Remove or Archive Food

* Related feature: FPF-008
* Priority: Must Have
* User story: As a user, I want food deletion to require confirmation and handle used foods safely, so that I do not accidentally damage my catalog or diary history.
* Preconditions:
  * The user selects delete on a food row.
* Acceptance criteria:
  * Given the user selects delete
    When the confirmation appears
    Then the confirmation identifies the food name.
  * Given the user cancels confirmation
    When the dialog closes
    Then no food is deleted or archived.
  * Given the food has never been used in diary entries
    When the user confirms delete
    Then the food may be hard deleted.
  * Given the food has been used in diary entries
    When the user confirms delete
    Then the food is archived/inactive, not hard deleted.
  * Given a used food is archived
    When the user adds future diary entries
    Then the archived food is hidden from future selection.
* Validation rules:
  * Delete requires explicit confirmation.
  * System must determine whether the food has diary usage.
* Edge cases:
  * Accidental tap.
  * Food already archived.
  * Offline delete/archive.
* UI behavior:
  * Confirmation must be clear and not destructive by default.
* Error behavior:
  * Delete/archive failure shows a clear error.
* Mobile behavior:
  * Confirmation must be usable on small screens.
* Data/API notes:
  * Current hard delete exists; product scope requires usage-aware archive behavior.
* QA test scenarios:
  * Cancel deletion.
  * Delete unused food.
  * Archive used food.
* Risks/gaps:
  * Confirmation, usage check, and archive/inactive field are not implemented.

### US-FPF-009-1: Preserve Diary History After Archive or Delete

* Related feature: FPF-009
* Priority: Must Have
* User story: As a user, I want old diary entries to keep their original nutrition after a food is edited, archived, or deleted, so that my historical tracking stays accurate.
* Preconditions:
  * A diary entry exists for a food.
* Acceptance criteria:
  * Given a diary entry was created from a food
    When the food is edited
    Then the diary entry keeps its original nutrition snapshot.
  * Given a diary entry was created from a food
    When the food is archived or deleted
    Then the diary entry remains readable and totals remain unchanged.
  * Given a used food is archived
    When future diary food selection is shown
    Then the archived food is not available for new selection.
* Validation rules:
  * Diary totals must use snapshots, not live food joins.
* Edge cases:
  * Food deleted after many diary entries.
  * Food nutrition changed after logging.
* UI behavior:
  * Historical diary entries remain stable.
* Error behavior:
  * Archive/delete failure must not alter diary snapshots.
* Mobile behavior:
  * No special mobile behavior.
* Data/API notes:
  * Uses `nutrition_snapshot`.
* QA test scenarios:
  * Log food, edit food, verify old diary totals.
  * Log food, archive/delete food, verify old diary totals.
* Risks/gaps:
  * Archive/inactive behavior is not implemented.

### US-FPF-010-1: View Food Details

* Related feature: FPF-010
* Priority: Should Have
* User story: As a user, I want to view optional food details, so that I can inspect nutrients beyond the main row summary when needed.
* Preconditions:
  * At least one food exists.
* Acceptance criteria:
  * Given a food row is visible
    When the user opens details
    Then optional nutrients and serving grams are shown.
  * Given optional values are missing
    When details are shown
    Then missing values display as a neutral placeholder.
  * Given details are closed
    When the user returns to the list
    Then the row remains usable.
* Validation rules:
  * No input validation applies.
* Edge cases:
  * All optional values missing.
  * Some optional values set to `0`.
* UI behavior:
  * Details are inline and do not replace the list.
* Error behavior:
  * Missing optional fields do not crash display.
* Mobile behavior:
  * Details must not force horizontal scrolling.
* Data/API notes:
  * Uses existing `FoodResponse`.
* QA test scenarios:
  * Open and close details.
  * Verify placeholder for missing optional values.
* Risks/gaps:
  * Timestamps and usage count are not shown.

### US-FPF-011-1: Enter Required Core Nutrition

* Related feature: FPF-011
* Priority: Must Have
* User story: As a user, I want to enter calories, protein, carbs, and fat per serving, so that food totals can be calculated correctly.
* Preconditions:
  * The user is adding or editing a food.
* Acceptance criteria:
  * Given the user enters valid core nutrients
    When the food is saved
    Then calories, protein, carbs, and fat are stored per serving.
  * Given any required core nutrient is missing
    When the user saves
    Then the food is not saved and a field-level error is shown.
  * Given a core nutrient is negative
    When the user saves
    Then the food is not saved.
* Validation rules:
  * Calories, protein, carbs, and fat are required.
  * Values must be numeric and `>= 0`.
* Edge cases:
  * `0` value.
  * Decimal value.
  * Very large value.
* UI behavior:
  * Required fields are visually clear.
* Error behavior:
  * Required and invalid number errors are visible.
* Mobile behavior:
  * Numeric keyboard should be usable where supported.
* Data/API notes:
  * Stored in the food record as per-serving values.
* QA test scenarios:
  * Save valid values.
  * Try negative values.
  * Try missing values.
* Risks/gaps:
  * Current required numeric defaults can hide missing data as `0`.

### US-FPF-012-1: Enter Optional Detail Nutrients

* Related feature: FPF-012
* Priority: Should Have
* User story: As a user, I want optional nutrient fields to be available but not required, so that I can add detail only when I have it.
* Preconditions:
  * The user is adding or editing a food.
* Acceptance criteria:
  * Given optional detail values are entered
    When the food is saved
    Then those values are stored.
  * Given optional detail values are left empty
    When the food is saved
    Then the food is still saved.
  * Given an optional numeric value is negative
    When the user saves
    Then the field shows an error.
* Validation rules:
  * Optional values may be blank.
  * Provided optional values must be numeric and `>= 0`.
  * Fiber must not exceed carbs.
* Edge cases:
  * All optional fields empty.
  * Optional value `0`.
  * Fiber greater than carbs.
* UI behavior:
  * Optional details are grouped separately from core fields.
* Error behavior:
  * Invalid optional fields show field-level errors.
* Mobile behavior:
  * Optional section must be usable without overwhelming the form.
* Data/API notes:
  * Blank optional values are stored as `null`.
* QA test scenarios:
  * Save without optional values.
  * Save with partial optional values.
  * Try negative optional values.
* Risks/gaps:
  * No upper bounds are defined.

### US-FPF-013-1: Prevent Negative Net Carbs

* Related feature: FPF-013
* Priority: Must Have
* User story: As a user, I want net carbs to never be negative, so that nutrition totals remain understandable and valid.
* Preconditions:
  * The user enters or edits carbs and fiber.
* Acceptance criteria:
  * Given fiber is less than or equal to carbs
    When net carbs are calculated
    Then net carbs equal `carbs - fiber`.
  * Given fiber is missing
    When net carbs are calculated
    Then fiber is treated as `0`.
  * Given fiber is greater than carbs
    When the user saves
    Then the food is not saved and fiber shows a field-level error.
* Validation rules:
  * `fiber_g <= carb_g`.
  * Net carbs must not display below `0`.
* Edge cases:
  * Fiber missing.
  * Fiber equals carbs.
  * Fiber greater than carbs.
* UI behavior:
  * Net carbs display must be clear in list rows.
* Error behavior:
  * Fiber error blocks save/update.
* Mobile behavior:
  * Error must be visible near the fiber field.
* Data/API notes:
  * `net_carbs_g` is computed, not stored.
* QA test scenarios:
  * Verify valid net carbs.
  * Verify fiber greater than carbs is blocked.
* Risks/gaps:
  * Current implementation can return negative net carbs.

### US-FPF-014-1: Enter Serving Label

* Related feature: FPF-014
* Priority: Must Have
* User story: As a user, I want to describe the serving in plain text, so that each food's nutrition values match how I actually eat it.
* Preconditions:
  * The user is adding or editing a food.
* Acceptance criteria:
  * Given a serving label is entered
    When the food is saved
    Then the label is stored and shown in the list.
  * Given the serving label is empty
    When the user saves
    Then the field shows a required error.
  * Given Arabic or English serving text is entered
    When saved
    Then it displays correctly.
* Validation rules:
  * Serving label is required.
  * Minimum length is 1 non-empty value.
* Edge cases:
  * Long serving label.
  * Mixed Arabic/English label.
* UI behavior:
  * Placeholder should clarify examples such as grams, piece, or plate.
* Error behavior:
  * Empty label blocks save.
* Mobile behavior:
  * Long label wraps without breaking layout.
* Data/API notes:
  * Stored as `serving_label`.
* QA test scenarios:
  * Save with Arabic label.
  * Save with English label.
  * Try empty label.
* Risks/gaps:
  * No normalized serving unit enum exists.

### US-FPF-015-1: Enter Serving Weight in Grams

* Related feature: FPF-015
* Priority: Should Have
* User story: As a user, I want to optionally enter serving weight in grams, so that gram-based usage can be calculated when weight is known.
* Preconditions:
  * The user is adding or editing a food.
* Acceptance criteria:
  * Given serving weight is entered as a positive number
    When the food is saved
    Then the value is stored.
  * Given serving weight is blank
    When the food is saved
    Then the food is saved but gram-based usage is unavailable.
  * Given serving weight is `0` or negative
    When the user saves
    Then a field-level error is shown.
* Validation rules:
  * Optional for serving-based usage.
  * Required for gram-based usage.
  * If provided, must be `> 0`.
* Edge cases:
  * Blank value.
  * Decimal grams.
  * `0`.
* UI behavior:
  * Field is clearly optional on the Foods page.
* Error behavior:
  * Invalid serving weight blocks save.
* Mobile behavior:
  * Numeric input must be usable.
* Data/API notes:
  * Current field is `serving_grams`; product term is `serving_weight_g`.
* QA test scenarios:
  * Save without serving weight.
  * Save with positive serving weight.
  * Try `0`.
* Risks/gaps:
  * Current UI/backend mismatch allows `0` in UI while backend rejects it.

### US-FPF-016-1: Use Food by Gram Quantity

* Related feature: FPF-016
* Priority: Must Have
* User story: As a user, I want to use a food by gram quantity when serving weight exists, so that weighed foods are tracked accurately.
* Preconditions:
  * The food has per-serving nutrition values.
  * Gram entry is attempted from Diary or a food-use flow.
* Acceptance criteria:
  * Given a food has serving weight in grams
    When the user enters a gram quantity
    Then nutrition totals are calculated as `grams / serving_weight_g * per-serving nutrient`.
  * Given serving weight is missing
    When the user tries gram entry
    Then gram entry is disabled or a clear error is shown.
  * Given gram quantity is valid
    When the entry is saved
    Then totals are stored/calculated consistently with serving-based entries.
* Validation rules:
  * Gram quantity must be numeric and greater than `0`.
  * Serving weight is required for gram mode.
* Edge cases:
  * Decimal grams.
  * Gram quantity equal to serving weight.
  * Very small gram quantity.
* UI behavior:
  * Gram mode must not be offered as usable when serving weight is missing.
* Error behavior:
  * Missing serving weight shows a clear error or disabled state.
* Mobile behavior:
  * Gram quantity input must be usable on mobile.
* Data/API notes:
  * Current Diary input is serving-based only; gram behavior is planned product scope.
* QA test scenarios:
  * Use grams when serving weight exists.
  * Try grams without serving weight.
* Risks/gaps:
  * Gram-based usage is not implemented.

### US-FPF-017-1: Keep Per-100g Mode Out of Current Scope

* Related feature: FPF-017
* Priority: Could Have
* User story: As a user, I want nutrition entry to stay per serving in the current version, so that adding foods remains simple.
* Preconditions:
  * The current Foods page scope is per-serving nutrition.
* Acceptance criteria:
  * Given the user creates or edits a food
    When entering nutrition
    Then values are entered per serving.
  * Given per-100g data is available externally
    When using the current Foods page
    Then the user must convert it to per-serving values before entry.
  * Given user stories are generated
    When scope is checked
    Then per-100g UI or API behavior is not required.
* Validation rules:
  * No per-100g validation applies.
* Edge cases:
  * User has label data per 100g only.
* UI behavior:
  * Do not show unconfirmed per-100g mode.
* Error behavior:
  * N/A.
* Mobile behavior:
  * N/A.
* Data/API notes:
  * No per-100g fields are confirmed.
* QA test scenarios:
  * Verify stories do not require per-100g fields.
* Risks/gaps:
  * Per-100g mode is postponed.

### US-FPF-018-1: Validate Required Text Fields

* Related feature: FPF-018
* Priority: Must Have
* User story: As a user, I want required text fields to be validated, so that foods are saved with usable names and serving labels.
* Preconditions:
  * The user is creating or editing a food.
* Acceptance criteria:
  * Given name is empty
    When the user saves
    Then the name field shows an error and save is blocked.
  * Given serving label is empty
    When the user saves
    Then the serving label field shows an error and save is blocked.
  * Given valid text is entered
    When the user saves
    Then the text is accepted.
* Validation rules:
  * Name required.
  * Serving label required.
  * Whitespace-only values should be treated as invalid.
* Edge cases:
  * Arabic text.
  * English text.
  * Symbols.
  * Long text.
* UI behavior:
  * Errors appear near fields.
* Error behavior:
  * Required text errors block save/update.
* Mobile behavior:
  * Errors remain visible near inputs.
* Data/API notes:
  * Backend minimum length exists; product expects practical non-empty validation.
* QA test scenarios:
  * Empty name.
  * Empty serving label.
  * Whitespace-only text.
* Risks/gaps:
  * Whitespace-only behavior is not explicitly implemented.

### US-FPF-019-1: Validate Non-Negative Numbers

* Related feature: FPF-019
* Priority: Must Have
* User story: As a user, I want nutrition numbers to reject negative values, so that my food data stays valid.
* Preconditions:
  * The user is creating or editing a food.
* Acceptance criteria:
  * Given any nutrient value is negative
    When the user saves
    Then save is blocked and the field shows an error.
  * Given all nutrient values are zero or positive
    When the user saves
    Then numeric validation passes.
  * Given an optional numeric field is blank
    When the user saves
    Then the blank optional field is accepted.
* Validation rules:
  * Required numeric fields must be present and `>= 0`.
  * Optional numeric fields may be blank or `>= 0`.
  * Serving weight must be `> 0` when provided.
* Edge cases:
  * `0`.
  * Decimal value.
  * Negative decimal.
* UI behavior:
  * Invalid fields are clearly marked.
* Error behavior:
  * Numeric errors block save/update.
* Mobile behavior:
  * Numeric errors remain visible after keyboard dismissal.
* Data/API notes:
  * Backend schemas enforce non-negative nutrients.
* QA test scenarios:
  * Try negative core nutrient.
  * Try negative optional nutrient.
  * Save optional blanks.
* Risks/gaps:
  * Server validation messages are not clearly surfaced.

### US-FPF-020-1: Enter Decimal Values and Display Precision

* Related feature: FPF-020
* Priority: Should Have
* User story: As a user, I want decimal nutrition and serving values to be accepted and displayed cleanly, so that I can enter realistic food labels.
* Preconditions:
  * The user is entering numeric values.
* Acceptance criteria:
  * Given a valid decimal value is entered
    When the food is saved
    Then the decimal value is accepted.
  * Given a calculated value has decimals
    When shown in the UI
    Then it displays up to 2 decimal places and trims unnecessary trailing zeros.
  * Given diary totals are calculated
    When serving or gram quantity is decimal
    Then totals are rounded consistently to 2 decimals.
* Validation rules:
  * Decimal values must still satisfy min rules.
* Edge cases:
  * `0.5`.
  * `1.25`.
  * More than 2 decimal input.
* UI behavior:
  * Display format is readable and consistent.
* Error behavior:
  * Invalid numeric input shows a field-level error.
* Mobile behavior:
  * Decimal entry should be practical on mobile keyboards.
* Data/API notes:
  * Numeric persistence uses numeric fields.
* QA test scenarios:
  * Save decimal nutrients.
  * Verify display precision.
* Risks/gaps:
  * Current display precision is not explicitly formatted everywhere.

### US-FPF-021-1: Show Empty Catalog State

* Related feature: FPF-021
* Priority: Must Have
* User story: As a user, I want a clear empty catalog state with an add-food action, so that I know how to start building my catalog.
* Preconditions:
  * The Foods page has loaded successfully.
  * No active foods exist.
* Acceptance criteria:
  * Given no active foods exist
    When the Foods page finishes loading
    Then an empty catalog message is shown.
  * Given the empty catalog state is shown
    When the user wants to add food
    Then an add-food action or form is available.
  * Given search is active with no results
    When no matches exist
    Then the no-results state is shown instead of empty catalog.
* Validation rules:
  * No input validation applies.
* Edge cases:
  * First-time user.
  * All foods archived.
* UI behavior:
  * Empty state must not show fake rows.
* Error behavior:
  * Empty state must not be used for load failure.
* Mobile behavior:
  * Add action remains reachable.
* Data/API notes:
  * Empty means successful load with zero active foods.
* QA test scenarios:
  * Fresh catalog.
  * All foods inactive.
* Risks/gaps:
  * Current empty state lacks a dedicated empty-state add action.

### US-FPF-022-1: Show Loading State

* Related feature: FPF-022
* Priority: Must Have
* User story: As a user, I want the Foods page to show loading while foods are being fetched, so that I know the page is working.
* Preconditions:
  * The user opens the Foods page.
  * Food list request is in progress.
* Acceptance criteria:
  * Given foods are being fetched
    When the list is not ready
    Then a loading state is shown.
  * Given loading is active
    When no data has loaded yet
    Then the empty catalog state is not shown prematurely.
  * Given cached foods are available
    When the app chooses to show cache
    Then loading or sync status does not confuse cached data with final server state.
* Validation rules:
  * No input validation applies.
* Edge cases:
  * Slow network.
  * Initial load.
  * Refresh after mutation.
* UI behavior:
  * Loading indicator is visually distinct from empty/error states.
* Error behavior:
  * If load fails, transition to error or cached fallback state.
* Mobile behavior:
  * Loading state must fit mobile layout.
* Data/API notes:
  * Based on fetch/query state.
* QA test scenarios:
  * Simulate slow API response.
* Risks/gaps:
  * Dedicated loading UI is not implemented.

### US-FPF-023-1: Show General Error State

* Related feature: FPF-023
* Priority: Must Have
* User story: As a user, I want clear error messages when Foods data cannot be loaded or saved, so that I understand what happened and do not confuse errors with an empty catalog.
* Preconditions:
  * A list or mutation request fails.
* Acceptance criteria:
  * Given food list loading fails and no cache can satisfy the page
    When the Foods page resolves
    Then a general error state is shown.
  * Given a server validation error occurs
    When saving a food
    Then the error is displayed clearly and not presented as offline success.
  * Given cached foods are shown after a load failure
    When cache is used
    Then the UI communicates that cached/offline data is being used.
* Validation rules:
  * Field-level errors remain tied to fields.
  * General errors cover request/load failures.
* Edge cases:
  * Server unavailable.
  * Network offline.
  * Validation error.
  * Sync failure.
* UI behavior:
  * Error state is distinct from empty and no-results states.
* Error behavior:
  * Error message is visible and actionable enough for personal use.
* Mobile behavior:
  * Error text must be readable on mobile.
* Data/API notes:
  * `apiFetch` errors and offline cache paths must be represented accurately.
* QA test scenarios:
  * Simulate server error.
  * Simulate offline with no cache.
  * Simulate validation error.
* Risks/gaps:
  * Server validation errors are not clearly displayed.

### US-FPF-024-1: Show Search No-Results State

* Related feature: FPF-024
* Priority: Must Have
* User story: As a user, I want a specific no-results state when my search finds no foods, so that I know I should change or clear the search.
* Preconditions:
  * Search is active.
* Acceptance criteria:
  * Given search text is entered
    When no matching foods exist
    Then a no-results state is shown.
  * Given no-results is shown
    When the user clears the search
    Then the active food list or empty catalog state returns.
  * Given the catalog itself is empty
    When no search is active
    Then empty catalog state is shown, not no-results.
* Validation rules:
  * No input validation applies.
* Edge cases:
  * Search with spaces.
  * Arabic search text.
  * English search text.
* UI behavior:
  * No-results must be visually distinct from empty catalog.
* Error behavior:
  * Load failure must not show no-results.
* Mobile behavior:
  * Clear-search action should be accessible.
* Data/API notes:
  * Applies to server search and cached search.
* QA test scenarios:
  * Search unmatched term.
  * Clear search.
* Risks/gaps:
  * Current implementation can show generic empty state.

### US-FPF-025-1: Show Success Feedback

* Related feature: FPF-025
* Priority: Should Have
* User story: As a user, I want clear success feedback after saving or deleting food, so that I know my action completed.
* Preconditions:
  * The user performs create, edit, delete, archive, or queued offline action.
* Acceptance criteria:
  * Given a food is saved successfully
    When the save completes
    Then a success message is shown.
  * Given a food is deleted or archived successfully
    When the action completes
    Then a success message is shown.
  * Given an action is saved locally for sync
    When local queue succeeds
    Then the message clearly states that sync is pending.
* Validation rules:
  * Success message must not appear for failed validation.
* Edge cases:
  * Offline queued save.
  * Offline queued delete/archive.
* UI behavior:
  * Message appears near the relevant Foods page action area.
* Error behavior:
  * Error messages must not be styled as success.
* Mobile behavior:
  * Feedback remains visible after form submit.
* Data/API notes:
  * Tied to mutation results and queue behavior.
* QA test scenarios:
  * Verify save success.
  * Verify offline queued message.
* Risks/gaps:
  * Message duration and placement are not fully defined.

### US-FPF-026-1: Use Offline Food Cache

* Related feature: FPF-026
* Priority: Should Have
* User story: As a user, I want my food catalog to be available from cache when offline, so that I can still view foods without a connection.
* Preconditions:
  * Foods were previously cached.
  * Network/API is unavailable.
* Acceptance criteria:
  * Given cached foods exist
    When the food list request fails
    Then cached foods are displayed.
  * Given search is active while using cache
    When the user searches
    Then cached foods are filtered by name.
  * Given no cache exists and request fails
    When the page resolves
    Then a general error or offline-empty state is shown.
* Validation rules:
  * Cached data must still follow display rules.
* Edge cases:
  * Stale cached food.
  * Empty cache.
* UI behavior:
  * Cached/offline state should be distinguishable where practical.
* Error behavior:
  * No cache plus failure shows error, not empty catalog.
* Mobile behavior:
  * Cache display works on mobile.
* Data/API notes:
  * Uses Dexie `foods` table.
* QA test scenarios:
  * Load offline with cache.
  * Load offline without cache.
* Risks/gaps:
  * Stale cache state is not clearly communicated.

### US-FPF-027-1: Queue Offline Food Mutations

* Related feature: FPF-027
* Priority: Should Have
* User story: As a user, I want food changes to be queued when offline, so that I can continue managing my catalog and sync later.
* Preconditions:
  * The user creates, edits, deletes, or archives a food while API mutation cannot complete.
* Acceptance criteria:
  * Given create fails because the app is offline
    When local storage is available
    Then the food is saved locally and queued for sync.
  * Given update fails because the app is offline
    When local storage is available
    Then the local food is updated and queued for sync.
  * Given delete/archive fails because the app is offline
    When local storage is available
    Then the local state changes and sync is queued.
* Validation rules:
  * Invalid food data must not be queued as success.
* Edge cases:
  * Duplicate create offline.
  * Sync retry.
  * Same food edited multiple times offline.
* UI behavior:
  * Pending sync status is clear.
* Error behavior:
  * Queue failure is shown as error.
* Mobile behavior:
  * Offline messages fit small screens.
* Data/API notes:
  * Uses mutation queue and `/sync/push`.
* QA test scenarios:
  * Queue create.
  * Queue edit.
  * Queue delete/archive.
* Risks/gaps:
  * Conflict behavior is simple and user-facing conflicts are not defined.

### US-FPF-028-1: Use Responsive Foods Layout

* Related feature: FPF-028
* Priority: Must Have
* User story: As a user, I want the Foods page to adapt to my screen size, so that I can manage foods on desktop and phone.
* Preconditions:
  * The user opens Foods page on any supported viewport.
* Acceptance criteria:
  * Given a desktop viewport
    When the Foods page is displayed
    Then list and form layout remain readable.
  * Given a mobile viewport
    When the Foods page is displayed
    Then content stacks or reflows without horizontal scrolling.
  * Given long row text exists
    When displayed
    Then it wraps or truncates without overlapping actions.
* Validation rules:
  * No data validation applies.
* Edge cases:
  * Very long names.
  * Long serving labels.
  * Last row near fixed UI.
* UI behavior:
  * Layout remains stable.
* Error behavior:
  * Error/empty/loading states are also responsive.
* Mobile behavior:
  * No unintended horizontal scrolling.
  * Touch targets remain usable.
* Data/API notes:
  * N/A.
* QA test scenarios:
  * Test desktop, tablet, and small phone widths.
* Risks/gaps:
  * Long text behavior requires QA coverage.

### US-FPF-029-1: Support RTL Arabic Layout

* Related feature: FPF-029
* Priority: Must Have
* User story: As a user, I want the Foods page to support Arabic RTL layout, so that it feels natural for Arabic-first daily use.
* Preconditions:
  * The app root is Arabic RTL.
* Acceptance criteria:
  * Given the Foods page loads
    When Arabic labels are displayed
    Then layout direction is RTL.
  * Given mixed Arabic/English food names are displayed
    When rows render
    Then text remains readable.
  * Given form fields are shown
    When the user scans labels
    Then labels align with RTL layout.
* Validation rules:
  * Arabic and English text are accepted for relevant text fields.
* Edge cases:
  * Mixed-language names.
  * Numbers inside Arabic text.
* UI behavior:
  * RTL layout applies consistently.
* Error behavior:
  * Error messages should follow the same layout direction.
* Mobile behavior:
  * RTL layout remains readable on small screens.
* Data/API notes:
  * Text values are stored as strings.
* QA test scenarios:
  * Arabic name.
  * English name.
  * Mixed name.
* Risks/gaps:
  * Mixed LTR/RTL long text wrapping requires QA coverage.

### US-FPF-030-1: Provide Accessibility Basics

* Related feature: FPF-030
* Priority: Should Have
* User story: As a user, I want the Foods page controls to be understandable and keyboard/screen-reader friendly enough for personal daily use, so that I can manage foods reliably.
* Preconditions:
  * The Foods page has form fields and row actions.
* Acceptance criteria:
  * Given a form field is displayed
    When assistive technology inspects it
    Then the field has an associated label.
  * Given an icon-only action is displayed
    When assistive technology inspects it
    Then the action has an accessible name.
  * Given optional details are collapsed
    When keyboard users navigate
    Then the details control can be reached and toggled.
* Validation rules:
  * Error messages should be associated with fields where possible.
* Edge cases:
  * Icon-only delete/edit/detail actions.
  * Collapsible optional fields.
* UI behavior:
  * Controls have visible focus behavior.
* Error behavior:
  * Validation errors are perceivable.
* Mobile behavior:
  * Touch targets remain large enough.
* Data/API notes:
  * N/A.
* QA test scenarios:
  * Keyboard navigation.
  * Screen-reader label check.
* Risks/gaps:
  * Icon buttons currently rely on titles; accessibility tests are missing.

### US-FPF-031-1: Save and Retrieve Foods Through API

* Related feature: FPF-031
* Priority: Must Have
* User story: As a user, I want food list and changes to save and load reliably, so that my catalog is persistent.
* Preconditions:
  * Backend API is available.
* Acceptance criteria:
  * Given foods exist
    When the Foods page loads
    Then foods are retrieved from the API.
  * Given valid create/update/delete/archive actions occur
    When the API succeeds
    Then the UI reflects the persisted result.
  * Given the API returns validation errors
    When the user submits invalid data
    Then the UI shows clear validation feedback.
* Validation rules:
  * API must enforce field rules consistently with the UI.
* Edge cases:
  * 404 food.
  * Validation failure.
  * Auth failure.
* UI behavior:
  * User sees updated state after successful API operation.
* Error behavior:
  * API errors display clearly.
* Mobile behavior:
  * Same behavior on mobile.
* Data/API notes:
  * Uses `/foods` CRUD endpoints.
* QA test scenarios:
  * API list, create, update, delete/archive, validation error.
* Risks/gaps:
  * Direct food route CRUD tests are missing.

### US-FPF-032-1: Persist Foods in the Database

* Related feature: FPF-032
* Priority: Must Have
* User story: As a user, I want foods to persist in the catalog, so that I do not need to re-enter them each day.
* Preconditions:
  * Food data is saved through the API or sync.
* Acceptance criteria:
  * Given a food is saved
    When the page is reloaded
    Then the food remains available.
  * Given a food is updated
    When the page is reloaded
    Then updated values remain.
  * Given a food is archived/inactive
    When future selection is shown
    Then inactive state is respected.
* Validation rules:
  * Database state must not accept invalid required fields.
* Edge cases:
  * Duplicate legacy rows.
  * Archived food.
* UI behavior:
  * Persisted state appears after refresh.
* Error behavior:
  * Persistence failures show errors.
* Mobile behavior:
  * Same behavior on mobile.
* Data/API notes:
  * Uses `food` table and planned archive/inactive state.
* QA test scenarios:
  * Save, reload, verify.
  * Update, reload, verify.
* Risks/gaps:
  * No archive/inactive field exists yet.

### US-FPF-033-1: Store Diary Nutrition Snapshots

* Related feature: FPF-033
* Priority: Must Have
* User story: As a user, I want diary entries to keep a copy of the food nutrition at log time, so that historical totals remain accurate.
* Preconditions:
  * The user logs a food in Diary.
* Acceptance criteria:
  * Given a food is logged
    When the diary entry is created
    Then the current per-serving food nutrition is copied into `nutrition_snapshot`.
  * Given the original food is later edited
    When the old diary entry is viewed
    Then old totals remain unchanged.
  * Given the original food is archived or deleted
    When the old diary entry is viewed
    Then old totals remain unchanged.
* Validation rules:
  * Snapshot totals use quantity and copied values.
* Edge cases:
  * Optional nutrients missing.
  * Decimal quantities.
  * Gram-based entries when implemented.
* UI behavior:
  * Diary history remains stable.
* Error behavior:
  * Failed snapshot creation blocks diary entry save.
* Mobile behavior:
  * N/A for Foods page display.
* Data/API notes:
  * Uses `nutrition_snapshot`.
* QA test scenarios:
  * Snapshot freeze after edit.
  * Snapshot survives archive/delete.
* Risks/gaps:
  * Multi-profile Diary model is not implemented.

### US-FPF-034-1: Block Exact Duplicate Foods

* Related feature: FPF-034
* Priority: Must Have
* User story: As a user, I want exact duplicate foods to be blocked, so that my catalog stays clean and I do not select the wrong duplicate later.
* Preconditions:
  * The user creates or edits a food.
* Acceptance criteria:
  * Given an active food already exists with the same normalized name, serving label/unit text, and serving weight where available
    When the user tries to save another exact match
    Then save is blocked and a clear duplicate message is shown.
  * Given the same name has a different serving label or serving weight
    When the user saves
    Then it is not treated as an exact duplicate.
  * Given brand is not in current active scope
    When duplicate matching runs
    Then brand is not required for matching.
* Validation rules:
  * Normalize name and serving text before comparison.
  * Include serving weight when available.
* Edge cases:
  * Different casing.
  * Extra spaces.
  * Arabic/English names.
* UI behavior:
  * Duplicate message is shown near the form.
* Error behavior:
  * Duplicate blocks create/update.
* Mobile behavior:
  * Duplicate message remains visible.
* Data/API notes:
  * Current code has no uniqueness constraint.
* QA test scenarios:
  * Exact duplicate.
  * Same name different serving.
  * Extra spaces/case differences.
* Risks/gaps:
  * Duplicate blocking is not implemented.

### US-FPF-035-1: Cover Foods Behavior With QA Tests

* Related feature: FPF-035
* Priority: Must Have
* User story: As a user, I want Foods page behavior to be covered by tests, so that my daily nutrition tracking does not regress.
* Preconditions:
  * Foods page features are implemented or planned for implementation.
* Acceptance criteria:
  * Given Foods CRUD exists
    When automated tests run
    Then create, list, search, update, delete/archive, and validation behaviors are covered.
  * Given Diary snapshot behavior exists
    When tests run
    Then snapshot safety is covered.
  * Given sync behavior exists
    When tests run
    Then food sync create/update/delete/archive paths are covered.
* Validation rules:
  * Tests must include invalid data cases.
* Edge cases:
  * Duplicate foods.
  * Fiber greater than carbs.
  * Used-food archive.
* UI behavior:
  * UI tests should cover major states.
* Error behavior:
  * Error-state tests should cover API and network failures.
* Mobile behavior:
  * Mobile/responsive tests should cover long text and row actions.
* Data/API notes:
  * Existing tests cover snapshot and sync indirectly.
* QA test scenarios:
  * Add direct CRUD/search/validation tests.
* Risks/gaps:
  * Direct food CRUD tests are missing.

### US-FPF-036-1: Keep Brand Field Out of Current Scope

* Related feature: FPF-036
* Priority: Could Have
* User story: As a user, I want food entry to remain fast without requiring brand, so that I can add personal foods quickly.
* Preconditions:
  * Brand is not part of confirmed active scope.
* Acceptance criteria:
  * Given the user adds a food
    When the form is displayed
    Then brand is not required.
  * Given duplicate handling runs
    When brand is absent
    Then duplicate matching still works using confirmed fields.
* Validation rules:
  * No brand validation applies.
* Edge cases:
  * User wants to distinguish branded foods; use name/serving label in current scope.
* UI behavior:
  * Do not block food creation due to missing brand.
* Error behavior:
  * N/A.
* Mobile behavior:
  * Keeping brand out reduces form length.
* Data/API notes:
  * No brand field is confirmed.
* QA test scenarios:
  * Verify create does not require brand.
* Risks/gaps:
  * Brand may be useful later but is postponed.

### US-FPF-037-1: Keep Category Field Out of Current Scope

* Related feature: FPF-037
* Priority: Could Have
* User story: As a user, I want food entry to work without categories, so that maintaining my personal catalog stays simple.
* Preconditions:
  * Category is not part of confirmed active scope.
* Acceptance criteria:
  * Given the user adds or edits a food
    When saving
    Then category is not required.
  * Given the user browses foods
    When viewing the current Foods page scope
    Then category filtering is not required.
* Validation rules:
  * No category validation applies.
* Edge cases:
  * Large catalog may later need categories, but not current scope.
* UI behavior:
  * No category control is required.
* Error behavior:
  * N/A.
* Mobile behavior:
  * Excluding categories reduces mobile form complexity.
* Data/API notes:
  * No category field is confirmed.
* QA test scenarios:
  * Verify stories do not require category.
* Risks/gaps:
  * Category/tagging is postponed.

### US-FPF-038-1: Keep Food Source or Type Out of Current Scope

* Related feature: FPF-038
* Priority: Could Have
* User story: As a user, I want all foods to be treated as manually entered foods in the current version, so that the catalog stays simple.
* Preconditions:
  * Public imports and barcode scanning are out of scope.
* Acceptance criteria:
  * Given the user adds a food
    When saving
    Then source/type is not required.
  * Given food data is displayed
    When source/type is absent
    Then the row still displays normally.
* Validation rules:
  * No source/type validation applies.
* Edge cases:
  * Imported-food concepts are postponed.
* UI behavior:
  * No source/type control is required.
* Error behavior:
  * N/A.
* Mobile behavior:
  * Excluding source/type keeps the form shorter.
* Data/API notes:
  * No source/type field is confirmed.
* QA test scenarios:
  * Verify create/edit does not require source/type.
* Risks/gaps:
  * Source/type is unnecessary until import features exist.

### US-FPF-039-1: Keep Notes Field Out of Current Scope

* Related feature: FPF-039
* Priority: Could Have
* User story: As a user, I want food entry to avoid optional notes in the current version, so that the form stays focused on nutrition.
* Preconditions:
  * Notes are not part of confirmed active scope.
* Acceptance criteria:
  * Given the user creates or edits a food
    When saving
    Then notes are not required.
  * Given no notes field exists
    When food is displayed
    Then the list and details still provide required nutrition information.
* Validation rules:
  * No notes validation applies.
* Edge cases:
  * User wants context; use food name/serving label in current scope.
* UI behavior:
  * No notes field is required.
* Error behavior:
  * N/A.
* Mobile behavior:
  * Excluding notes keeps the form shorter.
* Data/API notes:
  * No notes field is confirmed.
* QA test scenarios:
  * Verify no story requires notes.
* Risks/gaps:
  * Notes are postponed.

### US-FPF-040-1: Retain Created and Updated Timestamps

* Related feature: FPF-040
* Priority: Should Have
* User story: As a user, I want the system to retain created and updated dates for foods, so that food records have audit metadata if needed.
* Preconditions:
  * A food is created or updated.
* Acceptance criteria:
  * Given a food is created
    When it is persisted
    Then `created_at` and `updated_at` are set.
  * Given a food is updated
    When the update succeeds
    Then `updated_at` changes.
  * Given the Foods page displays the standard list
    When timestamps are not shown
    Then this is acceptable unless a future audit UI is confirmed.
* Validation rules:
  * Timestamps are system-managed and not user editable.
* Edge cases:
  * Offline create/update sync.
* UI behavior:
  * No timestamp display is required in current UI.
* Error behavior:
  * Timestamp failure should be treated as persistence failure.
* Mobile behavior:
  * N/A.
* Data/API notes:
  * API returns timestamp metadata.
* QA test scenarios:
  * Create food and verify timestamps.
  * Update food and verify updated timestamp.
* Risks/gaps:
  * Timestamps are not visible for user auditing.

## 4. Validation Matrix

| Field | Rule | Valid examples | Invalid examples | Error message | Related user stories |
|---|---|---|---|---|---|
| Food name / `name` | Required; trim before validation; participates in normalized duplicate check | `Egg`, `رز أبيض`, `Greek yogurt 2%` | Empty, whitespace-only, exact duplicate | `Food name is required.` / `This food already exists.` | `US-FPF-006-1`, `US-FPF-018-1`, `US-FPF-034-1` |
| Serving label / `serving_label` | Required; trim before validation; participates in duplicate check | `100 g`, `1 piece`, `طبق` | Empty, whitespace-only | `Serving label is required.` | `US-FPF-014-1`, `US-FPF-018-1` |
| Serving weight / `serving_grams` | Optional for serving use; required for gram use; if provided must be `> 0` | `100`, `30.5` | `0`, `-5`, non-number | `Serving weight must be greater than 0.` | `US-FPF-015-1`, `US-FPF-016-1` |
| Gram quantity | Required only in gram mode; must be `> 0`; disabled/error if serving weight missing | `50`, `125.5` | `0`, `-1`, blank in gram mode | `Enter grams greater than 0.` / `Gram entry requires serving weight.` | `US-FPF-016-1` |
| Calories / `calories` | Required number `>= 0` | `0`, `120`, `85.5` | Empty, `-1`, non-number | `Calories must be 0 or greater.` | `US-FPF-011-1`, `US-FPF-019-1` |
| Protein / `protein_g` | Required number `>= 0` | `0`, `18`, `3.5` | Empty, `-2`, non-number | `Protein must be 0 or greater.` | `US-FPF-011-1`, `US-FPF-019-1` |
| Carbs / `carb_g` | Required number `>= 0`; must be `>= fiber_g` when fiber provided | `0`, `25`, `10.5` | Empty, `-1`, less than fiber | `Carbs must be 0 or greater.` | `US-FPF-011-1`, `US-FPF-013-1`, `US-FPF-019-1` |
| Fat / `fat_g` | Required number `>= 0` | `0`, `5`, `2.25` | Empty, `-1`, non-number | `Fat must be 0 or greater.` | `US-FPF-011-1`, `US-FPF-019-1` |
| Fiber / `fiber_g` | Optional number `>= 0`; must not exceed carbs | Blank, `0`, `4` when carbs `10` | `-1`, `11` when carbs `10` | `Fiber cannot exceed carbs.` | `US-FPF-012-1`, `US-FPF-013-1` |
| Saturated fat / `saturated_fat_g` | Optional number `>= 0` | Blank, `0`, `1.5` | `-1`, non-number | `Saturated fat must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Trans fat / `trans_fat_g` | Optional number `>= 0` | Blank, `0`, `0.1` | `-0.1`, non-number | `Trans fat must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Cholesterol / `cholesterol_mg` | Optional number `>= 0` | Blank, `0`, `30` | `-1`, non-number | `Cholesterol must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Sodium / `sodium_mg` | Optional number `>= 0` | Blank, `0`, `120` | `-1`, non-number | `Sodium must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Total sugars / `total_sugars_g` | Optional number `>= 0` | Blank, `0`, `8` | `-1`, non-number | `Total sugars must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Added sugar / `added_sugar_g` | Optional number `>= 0` | Blank, `0`, `5` | `-1`, non-number | `Added sugar must be 0 or greater.` | `US-FPF-012-1`, `US-FPF-019-1` |
| Net carbs / `net_carbs_g` | Computed as `carbs - fiber`; must never be negative | `10 carbs - 3 fiber = 7` | Any result below `0` | `Fiber cannot exceed carbs.` | `US-FPF-013-1` |
| Active/archive status | System-managed; active by default; used foods archive instead of hard delete | Active, archived | User-edited status in standard form | N/A | `US-FPF-008-1`, `US-FPF-009-1`, `US-FPF-032-1` |
| Created/updated timestamps | System-managed; not user editable | Valid server timestamp | User-entered timestamp | N/A | `US-FPF-040-1` |

## 5. Acceptance Criteria Checklist

| Behavior | Covered | Related user stories |
|---|---:|---|
| Display active food list | Yes | `US-FPF-001-1` |
| Show visible count | Yes | `US-FPF-002-1` |
| Search by name | Yes | `US-FPF-003-1` |
| Keep advanced filters out of current scope | Yes | `US-FPF-004-1` |
| Sort by name | Yes | `US-FPF-005-1` |
| Create food | Yes | `US-FPF-006-1` |
| Edit food | Yes | `US-FPF-007-1` |
| Delete requires confirmation | Yes | `US-FPF-008-1` |
| Used foods archive instead of hard delete | Yes | `US-FPF-008-1`, `US-FPF-009-1` |
| Food details | Yes | `US-FPF-010-1` |
| Required core nutrition | Yes | `US-FPF-011-1` |
| Optional nutrients | Yes | `US-FPF-012-1` |
| Net carbs non-negative | Yes | `US-FPF-013-1` |
| Serving label | Yes | `US-FPF-014-1` |
| Serving weight | Yes | `US-FPF-015-1` |
| Gram-based usage | Yes | `US-FPF-016-1` |
| Per-100g out of scope | Yes | `US-FPF-017-1` |
| Required text validation | Yes | `US-FPF-018-1` |
| Non-negative numeric validation | Yes | `US-FPF-019-1` |
| Decimal values | Yes | `US-FPF-020-1` |
| Empty state | Yes | `US-FPF-021-1` |
| Loading state | Yes | `US-FPF-022-1` |
| Error state | Yes | `US-FPF-023-1` |
| Search no-results state | Yes | `US-FPF-024-1` |
| Success feedback | Yes | `US-FPF-025-1` |
| Offline cache | Yes | `US-FPF-026-1` |
| Offline mutation queue | Yes | `US-FPF-027-1` |
| Responsive layout | Yes | `US-FPF-028-1` |
| RTL layout | Yes | `US-FPF-029-1` |
| Accessibility basics | Yes | `US-FPF-030-1` |
| API behavior | Yes | `US-FPF-031-1` |
| Database persistence | Yes | `US-FPF-032-1` |
| Diary snapshot | Yes | `US-FPF-033-1` |
| Duplicate handling | Yes | `US-FPF-034-1` |
| QA coverage | Yes | `US-FPF-035-1` |
| Brand out of scope | Yes | `US-FPF-036-1` |
| Category out of scope | Yes | `US-FPF-037-1` |
| Source/type out of scope | Yes | `US-FPF-038-1` |
| Notes out of scope | Yes | `US-FPF-039-1` |
| Timestamps | Yes | `US-FPF-040-1` |

## 6. QA Coverage Matrix

| Test area | Positive tests | Negative tests | Edge cases | Mobile tests | Regression tests | Related user stories |
|---|---|---|---|---|---|---|
| Browse foods | `QA-001` active foods display | `QA-002` inactive foods hidden | `QA-003` duplicate legacy names | `QA-004` long names no overlap | `QA-005` list remains after reload | `US-FPF-001-1`, `US-FPF-002-1` |
| Search/filter/sort | `QA-006` search matching name | `QA-007` no-results state | `QA-008` mixed-language search | `QA-009` search input usable | `QA-010` sorted order after refresh | `US-FPF-003-1`, `US-FPF-004-1`, `US-FPF-005-1`, `US-FPF-024-1` |
| Create food | `QA-011` create valid food | `QA-012` missing required fields | `QA-013` decimal values | `QA-014` form usable on phone | `QA-015` created food persists; `QA-016` offline create queues | `US-FPF-006-1`, `US-FPF-011-1`, `US-FPF-012-1` |
| Edit food | `QA-017` edit name | `QA-018` duplicate edit blocked | `QA-019` clear optional values | `QA-020` edit form responsive | `QA-021` old diary snapshot unchanged | `US-FPF-007-1`, `US-FPF-033-1` |
| Delete/archive food | `QA-022` confirm unused food delete | `QA-023` cancel delete | `QA-024` archive used food | `QA-025` confirmation usable on mobile | `QA-026` old diary unchanged; `QA-027` archived food hidden | `US-FPF-008-1`, `US-FPF-009-1` |
| Food details | `QA-028` open details | `QA-029` missing optional values display placeholder | `QA-030` all optional fields set | `QA-031` details no horizontal scroll | `QA-032` details close/reopen stable | `US-FPF-010-1` |
| Nutrition and serving | `QA-033` per-serving totals valid | `QA-034` fiber greater than carbs blocked | `QA-035` net carbs equals zero | `QA-036` field errors visible on mobile | `QA-037` gram formula stable; `QA-038` missing serving weight blocks grams; `QA-039` decimal rounding | `US-FPF-011-1` to `US-FPF-017-1`, `US-FPF-020-1` |
| Validation and errors | `QA-040` valid save succeeds | `QA-041` negative values blocked | `QA-042` whitespace text blocked | `QA-043` errors readable on mobile | `QA-044` server validation shown; `QA-045` duplicate blocked; `QA-046` invalid data not queued | `US-FPF-018-1`, `US-FPF-019-1`, `US-FPF-023-1`, `US-FPF-034-1` |
| States/offline | `QA-047` empty catalog state | `QA-048` loading state before empty | `QA-049` API error state | `QA-050` states fit mobile | `QA-051` cached list offline; `QA-052` offline no cache error | `US-FPF-021-1` to `US-FPF-027-1` |
| Mobile/RTL/accessibility | `QA-053` RTL layout | `QA-054` icon action accessible names missing check | `QA-055` long mixed text | `QA-056` no horizontal scrolling; `QA-057` touch targets usable | `QA-058` keyboard navigation; `QA-059` focus visible | `US-FPF-028-1`, `US-FPF-029-1`, `US-FPF-030-1` |
| Diary integration | `QA-060` serving entry snapshot | `QA-061` missing food fails safely | `QA-062` optional nutrient snapshot | `QA-063` diary selection usable on mobile | `QA-064` edit/archive/delete does not change old totals | `US-FPF-009-1`, `US-FPF-016-1`, `US-FPF-033-1` |
| Data/API | `QA-065` API list | `QA-066` API validation error | `QA-067` archived state persistence | `QA-068` mobile uses same API behavior | `QA-069` sync replay idempotent; `QA-070` timestamps update | `US-FPF-031-1`, `US-FPF-032-1`, `US-FPF-040-1` |
| QA regression suite | `QA-071` CRUD happy path suite | `QA-072` CRUD negative suite | `QA-073` duplicate and fiber rules | `QA-074` mobile visual suite | `QA-075` snapshot and sync regression suite | `US-FPF-035-1` |

## 7. Remaining Risks and Gaps

| Gap | Impact | Related user stories | Recommended follow-up |
|---|---|---|---|
| Delete confirmation not implemented | Accidental deletion risk | `US-FPF-008-1` | Add confirmation requirement to implementation backlog. |
| Used-food archive behavior not implemented | Used foods can be hard deleted instead of archived/inactive | `US-FPF-008-1`, `US-FPF-009-1`, `US-FPF-032-1` | Add usage-aware archive behavior and active/inactive state. |
| Required numeric fields default to `0` | Incomplete nutrition can be saved accidentally | `US-FPF-006-1`, `US-FPF-011-1`, `US-FPF-019-1` | Treat empty required numeric fields as invalid. |
| Server validation errors are not clearly displayed | User may think invalid data was saved | `US-FPF-006-1`, `US-FPF-007-1`, `US-FPF-023-1` | Separate validation errors from offline success paths. |
| Loading state is missing | Loading can look like empty catalog | `US-FPF-022-1` | Add dedicated loading state. |
| Error/no-results/empty states are not distinct | User can misunderstand page state | `US-FPF-021-1`, `US-FPF-023-1`, `US-FPF-024-1` | Implement separate states. |
| Serving grams UI/backend mismatch | UI can accept `0` while backend rejects it | `US-FPF-015-1`, `US-FPF-016-1` | Align UI and backend rule to `> 0`. |
| Gram-based usage is not implemented | Weighed food tracking is unavailable | `US-FPF-016-1` | Implement serving-weight-gated gram mode. |
| Duplicate blocking is not implemented | Catalog clutter and wrong food selection | `US-FPF-034-1` | Add normalized duplicate check and message. |
| Fiber <= carbs validation is not implemented | Net carbs can become negative | `US-FPF-013-1` | Add field-level validation. |
| No direct Foods CRUD tests | Regressions can pass unnoticed | `US-FPF-031-1`, `US-FPF-035-1` | Add route/service/UI tests. |
| Mixed Arabic/English long text behavior is not tested | Mobile and RTL rows may break | `US-FPF-028-1`, `US-FPF-029-1` | Add responsive and mixed-text tests. |
| Created/updated timestamps are not visible | User cannot audit recency in UI | `US-FPF-040-1` | Keep hidden unless product later needs audit display. |

## 8. Final Readiness Verdict

### Are the Foods page user stories ready for implementation?

Yes. The stories are specific enough to guide implementation. The stories intentionally include current implementation gaps as risks, not as hidden assumptions.

### Are they ready for QA test case generation?

Yes. The stories include acceptance criteria, validation rules, edge cases, error behavior, mobile behavior, API notes, and QA scenarios.

### Top 5 Implementation Risks

1. Delete confirmation and used-food archive behavior require model/API/UI changes.
2. Gram-based usage requires Diary flow and calculation changes.
3. Duplicate blocking requires normalized comparison rules across create and edit.
4. Validation errors must be separated from offline queue success behavior.
5. Empty/loading/error/no-results states must be split clearly in the UI.

### Top 5 QA Focus Areas

1. Delete/archive safety and diary snapshot preservation.
2. Required-field, duplicate, and fiber <= carbs validation.
3. Serving vs gram calculation and rounding.
4. Offline cache/sync behavior.
5. Mobile RTL layout with long Arabic/English food names.
