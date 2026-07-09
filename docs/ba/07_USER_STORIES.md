# User Stories

These user stories are reverse-engineered from the current codebase and existing documentation. They mix implemented, missing, and recommended behavior; each status is explicit.

## App Shell, Auth, and Optional Installable Shell

### US-APP-HAPPY-001 - Use Arabic RTL App Shell

Feature: App shell and RTL layout  
Actor: Single owner  
Type: Happy / UX/UI / Arabic/RTL  
Priority: P1  
Status: Implemented  
Evidence: `frontend/app/layout.tsx`, `frontend/components/AppNav.tsx`, `frontend/app/globals.css`  
Confidence: High

User Story:
As a user, I want the app shell to use Arabic RTL layout and clear navigation, so that I can move between Diary, Foods, and Profile naturally.

Acceptance Criteria:
- Given the app loads
  When any main page is rendered
  Then the document language is Arabic and direction is RTL.
- Given I use the top navigation
  When I select Diary, Foods, or Profile
  Then the selected page opens and the active navigation item is visible.

Verification:
- E2E navigation test.
- Visual RTL responsive test.

### US-AUTH-PERM-001 - Protect Personal API Data

Feature: Single-user token auth  
Actor: System  
Type: Permission / Security  
Priority: P0  
Status: Implemented  
Evidence: `backend/app/core/auth.py`, protected route dependencies  
Confidence: High

User Story:
As the system, I want protected APIs to require the configured single-user token, so that personal nutrition data is not exposed.

Acceptance Criteria:
- Given a request includes `Authorization: Bearer <token>`
  When it calls v1 protected APIs such as `/profile`, `/foods`, or `/diary`
  Then the API processes the request.
- Given a request has no token or an invalid token
  When it calls a protected API
  Then the API returns an authorization error.

Verification:
- API auth tests for every protected router.

### US-SHELL-HAPPY-001 - Use an Optional Installable Online Shell

Feature: Optional installable shell  
Actor: Single owner  
Type: Mobile/PWA  
Priority: P1  
Status: Implemented code / v1 constrained  
Evidence: `frontend/public/manifest.json`, `frontend/components/InstallPrompt.tsx`, `frontend/public/service-worker.js`  
Confidence: High

User Story:
As a user, I want the app to be installable as a simple mobile-friendly shell, so that I can open it conveniently while still using online API data as the source of truth.

Acceptance Criteria:
- Given the install prompt is available
  When the user installs the app
  Then the app can open in standalone mode.
- Given the backend/API cannot be reached
  When the user tries to load personal nutrition data
  Then the app shows a clear connection error.
- Given offline-first data behavior exists in code
  When v1 requirements are applied
  Then cached personal nutrition data and offline writes are not treated as source of truth.

Status note:
- Offline-first behavior is removed from v1. IndexedDB cache, queued mutations, stale cache states, and sync are Future Scope.

## Profile and Targets

### US-PROFILE-HAPPY-001 - Save Profile Stats and Goal

Feature: Profile upsert  
Actor: Single owner  
Type: Happy / CRUD  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/ProfilePage.tsx`, `backend/app/api/routes/profile.py`, `backend/app/services/profile.py`  
Confidence: High

User Story:
As a user, I want to save my body stats and goal, so that my daily targets can be calculated.

Acceptance Criteria:
- Given valid profile fields
  When I save the profile
  Then the backend creates or updates the single profile row.
- Given save succeeds
  When the response returns
  Then the page shows the updated targets and a success note.
- Given the API is unreachable
  When I save the profile
  Then the profile is not saved or queued, my input remains visible, and a clear connection error is shown.

Field Rules:
- `height_cm > 0`
- `weight_kg > 0`
- `protein_per_kg` from 1.6 to 2.2
- `fat_pct` from 0.2 to 0.3

### US-PROFILE-VALIDATION-001 - Reject Invalid Profile Inputs

Feature: Profile validation  
Actor: Single owner  
Type: Field Validation / Negative  
Priority: P0  
Status: Partial  
Evidence: `backend/app/schemas.py`, `frontend/components/ProfilePage.tsx`  
Confidence: High

User Story:
As a user, I want invalid profile values rejected with clear Arabic messages, so that calculated targets are reliable.

Acceptance Criteria:
- Given height or weight is zero or negative
  When I save
  Then save is blocked and a field-level Arabic error is shown.
- Given protein/kg or fat percentage is outside the allowed range
  When I save
  Then save is blocked and the affected field shows an Arabic error.

Status note:
- Backend validation exists; custom frontend Arabic errors are missing.

### US-TARGET-HAPPY-001 - Preview Daily Targets

Feature: Target preview and display  
Actor: Single owner  
Type: Happy / Calculation  
Priority: P0  
Status: Implemented  
Evidence: `backend/app/services/calc.py`, `frontend/components/ProfilePage.tsx`, `frontend/components/TargetStrip.tsx`  
Confidence: High

User Story:
As a user, I want to preview calories and macros while editing my profile, so that I understand the impact before saving.

Acceptance Criteria:
- Given valid profile inputs
  When inputs change
  Then target preview updates after a short delay.
- Given carb calories are negative
  When targets are calculated
  Then carbs are clamped to zero and a flag/note is available.

Verification:
- Unit tests for calc formulas.
- Component test for target display.

## Food Catalog

### US-FOOD-HAPPY-001 - Browse Saved Foods

Feature: Food list  
Actor: Single owner  
Type: Happy / Read  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/FoodsPage.tsx`, `backend/app/api/routes/foods.py`  
Confidence: High

User Story:
As a user, I want to browse saved foods, so that I can reuse them for meal logging.

Acceptance Criteria:
- Given foods exist
  When the Foods page loads
  Then each food row shows name, serving, calories, protein, carbs, fat, and net carbs.
- Given no foods exist
  When the Foods page loads
  Then an empty state is shown.

### US-FOOD-HAPPY-002 - Search Foods by Name

Feature: Food search  
Actor: Single owner  
Type: Happy / Read  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/FoodsPage.tsx`, `backend/app/services/food.py`  
Confidence: High

User Story:
As a user, I want to search foods by name, so that I can find a food quickly.

Acceptance Criteria:
- Given a search term matches saved foods
  When I search
  Then only matching foods are shown.
- Given the API is unreachable
  When I search or load foods
  Then a clear connection error is shown and cached personal nutrition data is not treated as source of truth.
- Given no matches exist
  When I search
  Then a distinct no-results state is shown.

Status note:
- Search exists; distinct no-results state is missing.

### US-FOOD-CRUD-001 - Create Food

Feature: Food create  
Actor: Single owner  
Type: Happy / CRUD / Field Validation  
Priority: P0  
Status: Implemented / Partial  
Evidence: `frontend/components/FoodsPage.tsx`, `backend/app/api/routes/foods.py`, `backend/app/schemas.py`  
Confidence: High

User Story:
As a user, I want to add a food with serving and nutrition values, so that I can log it in Diary.

Acceptance Criteria:
- Given name, serving label, calories, protein, carbs, and fat are valid
  When I save
  Then the food is created and appears in the list.
- Given optional nutrient values are left blank
  When I save
  Then the food is still created with optional fields as null.
- Given the API is unreachable
  When I save
  Then the food is not created locally, no mutation is queued, the form input is preserved, and a clear connection error is shown.

Gaps:
- Duplicate checks are missing.
- Custom Arabic validation errors are missing.
- Current code may treat validation/network errors as local queued saves; v1 requires no local queued save.

### US-FOOD-VALIDATION-001 - Reject Invalid Food Fields

Feature: Food validation  
Actor: Single owner  
Type: Field Validation / Negative  
Priority: P0  
Status: Partial  
Evidence: `backend/app/schemas.py`, `frontend/components/FoodsPage.tsx`  
Confidence: High

User Story:
As a user, I want invalid food values rejected clearly, so that food totals stay accurate.

Acceptance Criteria:
- Given name or serving label is empty or whitespace-only
  When I save
  Then save is blocked with a field-level Arabic error.
- Given any required nutrient is blank, non-numeric, or negative
  When I save
  Then save is blocked with a field-level Arabic error.
- Given `serving_grams` is provided as zero or negative
  When I save
  Then save is blocked with a field-level Arabic error.

Status note:
- Backend has some validation, but whitespace, custom messages, and UI/server consistency are incomplete.

### US-FOOD-VALIDATION-002 - Prevent Negative Net Carbs

Feature: Net carbs validation  
Actor: Single owner  
Type: Field Validation / Negative  
Priority: P0  
Status: Missing / documented planned  
Evidence: `backend/app/services/food.py`, `docs/FOODS_PAGE_FEATURES.md`  
Confidence: High

User Story:
As a user, I want fiber to be validated against carbs, so that net carbs never become negative.

Acceptance Criteria:
- Given `fiber_g` is greater than `carb_g`
  When I save or update a food
  Then save is blocked and the fiber field shows a clear Arabic error.
- Given fiber is blank
  When net carbs are calculated
  Then fiber is treated as zero.

### US-FOOD-VALIDATION-003 - Block Exact Duplicate Foods

Feature: Duplicate food handling  
Actor: Single owner  
Type: Field Validation / Negative  
Priority: P0  
Status: Missing / documented planned  
Evidence: `docs/FOODS_PAGE_FEATURES.md`, `backend/app/services/food.py`  
Confidence: High

User Story:
As a user, I want exact duplicate foods blocked, so that my catalog stays clean.

Acceptance Criteria:
- Given an active food exists with the same normalized name, serving label, and serving grams where available
  When I try to save a duplicate
  Then save is blocked with a clear duplicate message.
- Given the same name has a different serving label or serving grams
  When I save
  Then it is allowed unless product defines a stricter duplicate rule.

Open Question:
- Should archived foods participate in duplicate checks?

### US-FOOD-CRUD-002 - Edit Food

Feature: Food edit  
Actor: Single owner  
Type: Happy / CRUD  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/FoodsPage.tsx`, `backend/app/api/routes/foods.py`, `backend/app/services/food.py`  
Confidence: High

User Story:
As a user, I want to edit an existing food, so that I can correct its serving or nutrition values.

Acceptance Criteria:
- Given I select edit on a food
  When the form enters edit mode
  Then the food's editable fields are populated.
- Given valid changes are saved
  When the update succeeds
  Then the list shows the updated values.
- Given the food was already used in Diary
  When I update the food
  Then existing diary entries keep their original snapshot values.

### US-FOOD-CRUD-003 - Delete or Archive Food Safely

Feature: Food delete/archive  
Actor: Single owner  
Type: CRUD / Destructive / Negative  
Priority: P0  
Status: Partial / Missing planned safety  
Evidence: `frontend/components/FoodsPage.tsx`, `backend/app/services/food.py`, `docs/FOODS_PAGE_FEATURES.md`  
Confidence: High

User Story:
As a user, I want food deletion to require confirmation and handle used foods safely, so that I do not accidentally damage my catalog or diary history.

Acceptance Criteria:
- Given I select delete
  When confirmation appears
  Then it names the food and explains the outcome.
- Given I cancel
  When the dialog closes
  Then no food is deleted or archived.
- Given the food has never been used in Diary
  When I confirm delete
  Then the food may be hard deleted.
- Given the food has been used in Diary
  When I confirm delete
  Then it becomes archived/inactive and is hidden from future selection.

Status note:
- Current code hard deletes immediately and has no archive field.

### US-FOOD-HAPPY-003 - View Food Details

Feature: Food details  
Actor: Single owner  
Type: Happy / Read  
Priority: P1  
Status: Implemented  
Evidence: `frontend/components/FoodsPage.tsx`  
Confidence: High

User Story:
As a user, I want to view optional nutrient details, so that I can inspect food values beyond the row summary.

Acceptance Criteria:
- Given a food row exists
  When I open details
  Then serving grams and optional nutrient fields are shown.
- Given an optional field is missing
  When details display
  Then a neutral placeholder is shown.

## Diary and Weekly Tracking

### US-DIARY-HAPPY-001 - View Diary for Selected Day

Feature: Diary day view  
Actor: Single owner  
Type: Happy / Read  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/DiaryPage.tsx`, `backend/app/api/routes/diary.py`  
Confidence: High

User Story:
As a user, I want to view diary entries for a selected day, so that I can see what I logged.

Acceptance Criteria:
- Given entries exist for the selected date
  When the day view loads
  Then entries are listed with food name, quantity, calories, and macros.
- Given no entries exist
  When the day view loads
  Then an empty-day state is shown.

### US-DIARY-CRUD-001 - Add Diary Entry by Serving

Feature: Diary create  
Actor: Single owner  
Type: Happy / CRUD  
Priority: P0  
Status: Implemented  
Evidence: `frontend/components/DiaryPage.tsx`, `backend/app/services/diary.py`  
Confidence: High

User Story:
As a user, I want to log a food by serving quantity, so that my daily totals update.

Acceptance Criteria:
- Given at least one food exists and quantity is positive
  When I submit the diary form
  Then a diary entry is created for the selected date.
- Given API creation succeeds
  When the entry is returned
  Then day entries and weekly totals refresh.
- Given the API is unreachable
  When I submit
  Then the entry is not created locally, no mutation is queued, the form input is preserved, and a clear connection error is shown.

### US-DIARY-VALIDATION-001 - Reject Invalid Diary Quantity

Feature: Diary validation  
Actor: Single owner  
Type: Field Validation / Negative  
Priority: P0  
Status: Partial  
Evidence: `backend/app/schemas.py`, `frontend/components/DiaryPage.tsx`  
Confidence: High

User Story:
As a user, I want invalid diary quantities rejected, so that totals are accurate.

Acceptance Criteria:
- Given quantity is zero, negative, blank, or non-numeric
  When I submit the diary form
  Then creation is blocked with a field-level Arabic error.
- Given no foods exist
  When I view the add form
  Then submit is disabled and the page tells me to add foods first.

### US-DIARY-INTEGRITY-001 - Preserve Nutrition Snapshots

Feature: Diary snapshot  
Actor: System  
Type: Data Integrity  
Priority: P0  
Status: Implemented  
Evidence: `backend/app/services/diary.py`, `backend/tests/test_diary_snapshot.py`  
Confidence: High

User Story:
As the system, I want each diary entry to store a nutrition snapshot, so that historical totals do not change after food edits or deletion.

Acceptance Criteria:
- Given a diary entry is created from a food
  When the food is edited later
  Then the diary entry totals stay unchanged.
- Given a food is deleted
  When old diary entries are read
  Then snapshot nutrition remains available.

### US-DIARY-CRUD-002 - Delete Diary Entry

Feature: Diary delete  
Actor: Single owner  
Type: CRUD / Destructive  
Priority: P1  
Status: Implemented / Partial  
Evidence: `frontend/components/DiaryPage.tsx`, `backend/app/api/routes/diary.py`  
Confidence: High

User Story:
As a user, I want to delete a mistaken diary entry, so that my daily totals are corrected.

Acceptance Criteria:
- Given I delete an entry
  When the delete succeeds
  Then the entry is removed and totals refresh.
- Given the API is unreachable
  When I delete an entry
  Then the entry remains visible, no local delete is queued, and a clear connection error is shown.

Gap:
- Delete confirmation is not implemented.

### US-DIARY-HAPPY-002 - View Weekly Summary

Feature: Weekly summary  
Actor: Single owner  
Type: Happy / Read  
Priority: P0  
Status: Implemented  
Evidence: `backend/app/services/aggregation.py`, `frontend/components/DiaryPage.tsx`  
Confidence: High

User Story:
As a user, I want a Sunday-to-Saturday weekly summary, so that I can compare daily calories against targets.

Acceptance Criteria:
- Given a selected date
  When the weekly summary is requested
  Then the system normalizes the week to Sunday through Saturday.
- Given entries exist in the week
  When the week displays
  Then each day shows calories and progress against targets.

### US-DIARY-GRAM-001 - Log Food by Grams

Feature: Gram-based diary usage  
Actor: Single owner  
Type: Recommended / Missing  
Priority: P1  
Status: Missing / documented planned  
Evidence: `docs/FOODS_PAGE_FEATURES.md`, no current Diary field/API |  
Confidence: High

User Story:
As a user, I want to log food by grams when serving grams exist, so that weighed foods are accurate.

Acceptance Criteria:
- Given a food has `serving_grams`
  When I enter grams
  Then nutrition totals are calculated as `grams / serving_grams * per-serving values`.
- Given a food has no `serving_grams`
  When I choose gram mode
  Then gram entry is disabled or a clear Arabic error is shown.

## Online Data and Future Offline Scope

### US-NETWORK-ERROR-001 - Show Connection Errors Without Saving

Feature: Online-only network error handling  
Actor: Single owner  
Type: Negative / Error Handling  
Priority: P0  
Status: Required / current code needs alignment  
Evidence: Product decision in `13_PRODUCT_DECISIONS.md`, `frontend/lib/api.ts`, page mutation handlers  
Confidence: High

User Story:
As a user, I want a clear connection error when the backend cannot be reached, so that I know my data was not saved.

Acceptance Criteria:
- Given a Profile, Food, or Diary write cannot reach the API
  When the request fails
  Then no local mutation is queued and no local data is treated as saved.
- Given a read request cannot reach the API
  When data cannot be loaded
  Then the page shows a clear connection error rather than stale cached personal data.
- Given invalid data is rejected by the backend
  When the response returns
  Then the user sees validation/error feedback and the invalid data is not saved.

### US-FUTURE-OFFLINE-001 - Defer Offline Cache and Sync

Feature: Offline cache and sync  
Actor: System  
Type: Future Scope  
Priority: P3  
Status: Future  
Evidence: `backend/app/api/routes/sync.py`, `frontend/lib/db.ts`, `backend/tests/test_sync.py`  
Confidence: High

User Story:
As the product team, I want offline cache and sync deferred out of v1, so that the first version stays simple and reliable.

Acceptance Criteria:
- Given v1 scope is implemented
  When Profile, Food, or Diary writes fail due to network/API availability
  Then changes are not queued offline.
- Given future offline-first work is planned
  When requirements are revisited
  Then sync queue, stale cache, conflict handling, and pending sync states are defined separately.

Status note:
- Current sync/IndexedDB code exists but is not a v1 requirement.

## Accessibility, Mobile, and Tests

### US-A11Y-001 - Provide Accessible Controls

Feature: Accessibility basics  
Actor: Keyboard or screen-reader user  
Type: Accessibility  
Priority: P1  
Status: Partial  
Evidence: labels in forms, `title` on icon buttons, status/error UI requirements  
Confidence: Medium

User Story:
As a keyboard or screen-reader user, I want controls and status updates to be accessible, so that I can use the app reliably.

Acceptance Criteria:
- Given an icon-only button exists
  When inspected by assistive technology
  Then it has an accessible name.
- Given a validation error occurs
  When the form is submitted
  Then focus and screen-reader behavior identify the field that needs attention.

### US-MOBILE-001 - Use the App on Small Screens

Feature: Responsive/mobile UX  
Actor: Mobile user  
Type: Mobile / UX/UI  
Priority: P1  
Status: Implemented / Partial  
Evidence: `frontend/app/globals.css`, optional install prompt / connection error UI requirements  
Confidence: High

User Story:
As a mobile user, I want pages and forms to remain readable and tappable, so that daily tracking works on my phone.

Acceptance Criteria:
- Given viewport width is under 640px
  When a main page renders
  Then form grids and target strips use one column.
- Given long mixed Arabic/English food names
  When rows render
  Then text does not overlap action buttons.

Gap:
- Safe-area handling and fixed-widget overlap are not fully specified.

### US-QA-001 - Cover Core Behavior With Tests

Feature: Test coverage  
Actor: Product owner / QA  
Type: Testability  
Priority: P1  
Status: Partial  
Evidence: `backend/tests/test_calc.py`, `backend/tests/test_diary_snapshot.py`, `backend/tests/test_sync.py`  
Confidence: High

User Story:
As a product owner, I want core app behavior covered by tests, so that future changes do not break daily nutrition tracking.

Acceptance Criteria:
- Given tests run
  When calc and snapshot behavior are exercised
  Then existing test cases pass.
- Given Food, Profile, Diary, and online network behavior are changed
  When regression tests run
  Then CRUD, validation, connection error, mobile, RTL, and accessibility behaviors are covered.

Status note:
- Backend unit/integration tests exist for selected behavior. Existing sync tests become Future Scope; direct CRUD/UI/network/mobile/a11y coverage is missing.
