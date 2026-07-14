# User Stories

These user stories define myNutri v1 requirements after product decisions D-001 through D-023. Status values distinguish current implementation from required v1 behavior.

## App Shell, Auth, and Installable Shell

### US-APP-HAPPY-001 - Use Arabic RTL App Shell

Feature: App shell and RTL layout
Actor: Single owner
Type: Happy / UX/UI / Arabic/RTL
Priority: P1
Status: Implemented / needs QA verification
Evidence: `frontend/app/layout.tsx`, `frontend/components/AppNav.tsx`, `frontend/app/globals.css`
Confidence: High

User Story:
As a user, I want the app shell to use Arabic RTL layout and clear navigation, so that I can move between Diary, Foods, and Profile naturally.

Acceptance Criteria:
- Given the app loads
  When any main page is rendered
  Then the document language is Arabic and direction is RTL.
- Given I use navigation
  When I select Diary, Foods, or Profile
  Then the selected page opens and the active navigation item is visible.

Verification:
- E2E navigation test.
- RTL visual test.

### US-AUTH-PERM-001 - Protect Personal API Data

Feature: Single-user token auth
Actor: System
Type: Permission / Security / Error Handling
Priority: P0
Status: Implemented / UI error handling needs alignment
Evidence: `backend/app/core/auth.py`, protected route dependencies
Confidence: High

User Story:
As the system, I want protected APIs to require the configured single-user token, so that personal nutrition data is not exposed.

Acceptance Criteria:
- Given a request includes `Authorization: Bearer <token>`
  When it calls protected APIs such as `/profile`, `/foods`, or `/diary`
  Then the API processes the request.
- Given a request has no token or an invalid token
  When it calls a protected API
  Then the API returns 401.
- Given the UI receives 401
  When the page or write action fails
  Then it shows `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` and does not show stale or queued data as saved.

Verification:
- API auth tests.
- UI 401 error test.

### US-SHELL-HAPPY-001 - Use an Optional Installable Online Shell

Feature: Optional installable shell
Actor: Single owner
Type: Mobile/PWA
Priority: P2
Status: Implemented code / v1 constrained
Evidence: `frontend/public/manifest.json`, `frontend/components/InstallPrompt.tsx`
Confidence: High

User Story:
As a user, I want the app to be installable as a simple mobile-friendly shell, so that I can open it conveniently.

Acceptance Criteria:
- Given the install prompt is available
  When I install the app
  Then it can open in standalone mode.
- Given the app is installed
  When personal nutrition data loads
  Then fresh online API data remains the source of truth.

### US-SHELL-SCOPE-001 - Prevent Offline Personal Data Behavior

Feature: Service worker shell scope
Actor: System
Type: PWA / Negative / Privacy
Priority: P0
Status: Required / current code needs alignment
Evidence: `frontend/public/service-worker.js`, `frontend/lib/db.ts`, `docs/ba/13_PRODUCT_DECISIONS.md`
Confidence: High

User Story:
As the product owner, I want any service worker limited to static shell assets, so that cached personal nutrition data is not mistaken for current data.

Acceptance Criteria:
- Given v1 is online-only
  When the service worker is present
  Then it does not cache personal nutrition API data.
- Given the backend is unreachable
  When Profile, Foods, Diary, or Week data cannot load
  Then the app shows a connection error rather than authoritative cached personal data.
- Given shell-only behavior cannot be made clear
  When v1 scope is finalized
  Then service worker removal is recommended.

### US-INFRA-READ-001 - Check API Health

Feature: Health endpoint
Actor: System / QA
Type: Read / Operational
Priority: P1
Status: Confirmed / story added for traceability
Evidence: `backend/app/api/routes/health.py`
Confidence: High

User Story:
As QA, I want a simple API health check, so that online-only read/write failures can be separated from application validation failures during testing.

Acceptance Criteria:
- Given the backend is running
  When `/health` is requested
  Then the API returns a successful health response.
- Given the backend is unreachable
  When the frontend attempts Profile, Foods, or Diary reads
  Then page-specific read failure copy from `06_ERROR_MESSAGES.md` is shown instead of offline/cached personal data.

### US-CONFIG-SEC-001 - Configure Online API Access Safely

Feature: Environment config
Actor: System / Product owner
Type: Security / Configuration
Priority: P1
Status: Confirmed / story added for traceability
Evidence: `backend/app/core/config.py`, `frontend/lib/api.ts`, `.env.example`
Confidence: High

User Story:
As the product owner, I want API URL and token configuration to be explicit, so that the online-only app connects to the intended backend without exposing real secrets in source control.

Acceptance Criteria:
- Given v1 is deployed or run locally
  When frontend API calls are made
  Then they use the configured API base URL and bearer token.
- Given source files are committed
  When repository contents are reviewed
  Then real secrets, private tokens, and `.env` files are not committed as product requirements or sample data.
- Given the API token is missing or invalid
  When a protected API is called
  Then the 401 Arabic message from `06_ERROR_MESSAGES.md` is shown.

## Profile and Targets

### US-PROFILE-SCOPE-001 - Use Single Profile Scope in v1

Feature: Profile scope
Actor: Single owner
Type: Scope / CRUD Boundary
Priority: P0
Status: Confirmed requirement
Evidence: Current single Profile model, product decisions D-016 and D-017
Confidence: High

User Story:
As a user, I want v1 to manage one personal profile, so that profile, foods, diary, and targets stay simple and focused on my own tracking.

Acceptance Criteria:
- Given v1 scope is implemented
  When Profile, Foods, Diary, and targets are used
  Then they are scoped to one personal user and one Profile model.
- Given older planning mentions multiple people/profiles
  When v1 requirements are evaluated
  Then multi-profile support and person switching are treated as Future Scope.
- Given I need to correct profile data
  When I update profile fields and the API succeeds
  Then the existing profile is updated.
- Given profile reset/delete is requested
  When v1 scope is evaluated
  Then profile reset/delete is out of scope and no delete/reset story is required.

### US-PROFILE-HAPPY-001 - Save Profile Stats and Goal Online

Feature: Profile upsert
Actor: Single owner
Type: Happy / CRUD
Priority: P0
Status: Implemented / current code needs online-only alignment
Evidence: `ProfilePage.tsx`, `profile.py`, `profile service`
Confidence: High

User Story:
As a user, I want to save my body stats and goal only after the API succeeds, so that my daily targets are based on real saved data.

Acceptance Criteria:
- Given valid profile fields
  When I save the profile and the API succeeds
  Then the backend creates or updates the single profile row and the page shows updated targets.
- Given the API is unreachable or returns 5xx
  When I save the profile
  Then the profile is not saved locally, no mutation is queued, my input remains visible in the same form state until I edit it, reset it, retry successfully, or navigate away, and the correct Arabic error is shown.
- Given the API returns 422
  When I save
  Then known field errors are shown beside the affected fields and unknown/form-level validation errors show `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`

Field Rules:
- Defined in `04_FIELD_DICTIONARY.md` and `05_VALIDATION_RULES.md`.

### US-PROFILE-STATE-001 - Handle Missing Profile State

Feature: Profile read state
Actor: Single owner
Type: Empty State / Read
Priority: P1
Status: Required / current UI needs verification
Evidence: `ProfilePage.tsx`, `profile.py`
Confidence: Medium

User Story:
As a user, I want a clear first-use profile state when no profile exists yet, so that I know I need to enter my stats before targets are reliable.

Acceptance Criteria:
- Given no Profile row exists
  When the Profile page loads successfully
  Then `ط£ط¯ط®ظ„ ط¨ظٹط§ظ†ط§طھظƒ ظ„ط­ط³ط§ط¨ ط§ظ„ط£ظ‡ط¯ط§ظپ ط§ظ„ظٹظˆظ…ظٹط©.` is shown and the profile form remains available.
- Given the Profile read fails because the API is unreachable
  When fresh profile data cannot load
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached personal data is not treated as current.

### US-PROFILE-VALIDATION-001 - Reject Invalid Profile Inputs

Feature: Profile validation
Actor: Single owner
Type: Field Validation / Negative
Priority: P0
Status: Required / current code needs alignment
Evidence: `backend/app/schemas.py`, `ProfilePage.tsx`
Confidence: High

User Story:
As a user, I want unrealistic profile values rejected with Arabic messages, so that target calculations remain reliable.

Acceptance Criteria:
- Given birth date is in the future
  When I save or preview
  Then the field shows `طھط§ط±ظٹط® ط§ظ„ظ…ظٹظ„ط§ط¯ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† ظٹظƒظˆظ† ظپظٹ ط§ظ„ظ…ط³طھظ‚ط¨ظ„.`
- Given age is below 10
  When I save or preview
  Then the birth-date field shows `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ† ظٹظƒظˆظ† 10 ط³ظ†ظˆط§طھ ط£ظˆ ط£ظƒط«ط±.`
- Given age is above 100
  When I save or preview
  Then the birth-date field shows `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ„ط§ ظٹطھط¬ط§ظˆط² 100 ط³ظ†ط©.`
- Given height, weight, protein/kg, or fat percentage is outside v1 range
  When I save or preview
  Then the affected field shows a min/max Arabic error and the profile is not persisted.

### US-TARGET-HAPPY-001 - Preview Daily Targets

Feature: Target preview and display
Actor: Single owner
Type: Happy / Calculation
Priority: P0
Status: Implemented / validation alignment needed
Evidence: `calc.py`, `ProfilePage.tsx`, `TargetStrip.tsx`, `test_calc.py`
Confidence: High

User Story:
As a user, I want to preview calories and macros while editing my profile, so that I understand the impact before saving.

Acceptance Criteria:
- Given valid profile inputs
  When inputs change
  Then target preview updates after the current valid input set is accepted by the preview calculation and no save is required for the preview.
- Given profile inputs are invalid
  When preview would be calculated
  Then invalid fields are shown and the preview is not treated as reliable.
- Given carb calories are negative
  When targets are calculated
  Then carbs are clamped to zero and a flag/note is available.

## Current Food Catalog User Stories - D-024/D-026

The stories in this section supersede older Food stories that mention archive/inactive lifecycle, `is_active`, `archived_at`, active/archived filters, `serving_label`, or `serving_grams` as Food source-of-truth fields.

### US-FOOD-NAV-001 - Use Standalone Food Pages

Feature: Food navigation and page structure
Actor: Single owner
Type: UX/UI
Priority: P0
Status: Required
Evidence: D-024
Confidence: High

User Story:
As a user,
I want Foods list, Add Food, Food details, and Edit Food to be separate pages,
so that browsing stays simple and Food forms are comfortable on mobile.

Preconditions:
- User can access the protected Foods area.

Acceptance Criteria:
- Given I open `/foods`
  When the page loads
  Then I see the Foods list/search/browse experience and not a large inline Add Food form.
- Given I select Add Food
  When navigation completes
  Then I am on `/foods/new`.
- Given I open `/foods/new`
  When the page loads
  Then no delete action is shown.
- Given I view an existing Food
  When I open details
  Then I am on `/foods/:id`.
- Given I edit an existing Food
  When the edit page opens
  Then I am on `/foods/:id/edit` and the page uses the same grouped structure as Add Food.

Field Rules:
- N/A.

Negative Scenarios:
- A large inline Add Food form on `/foods` violates v1 requirements.
- Delete action on `/foods/new` violates v1 requirements.

Verification:
- E2E navigation tests.
- Mobile viewport tests for `/foods/new` and `/foods/:id/edit`.

### US-FOOD-HAPPY-001 - Browse Current Food Catalog

Feature: Foods list
Actor: Single owner
Type: Happy path / UX/UI
Priority: P0
Status: Required
Evidence: D-024, D-025
Confidence: High

User Story:
As a user,
I want to browse the current Foods catalog,
so that I can quickly find foods to view, edit, delete, or use later in Diary.

Preconditions:
- At least one Food exists in the catalog.

Acceptance Criteria:
- Given Foods exist
  When I open `/foods`
  Then the desktop list shows Food name, brand if available, category if available, nutrition basis, default unit, calories, protein, carbs, fat, and View/Edit/Delete actions.
- Given I open `/foods` on mobile
  When Foods are displayed
  Then Foods use cards showing Food name, nutrition basis, default unit, calories, protein, carbs, and fat.
- Given a Food name is long
  When it appears in a list/card
  Then it is clamped to two lines with ellipsis and does not overlap actions or cause horizontal scrolling.
- Given a Food has optional micronutrients
  When it appears in the list/card
  Then optional micronutrients are not shown in the main list/card.
- Given an earlier Food was deleted
  When I open `/foods`
  Then that deleted Food is absent.
- Given I open the Foods list
  When I inspect filters/columns
  Then there is no status column, archived filter, or Active/Archived filter.

Field Rules:
- Display uses current Food catalog data only.

Negative Scenarios:
- Deleted Foods must not appear in list/search/future Diary selection.
- Archived-state UI must not appear in v1.

Verification:
- E2E list tests.
- Visual tests at 360, 390, 430, 768, and desktop widths.

### US-FOOD-HAPPY-002 - Search Current Food Catalog

Feature: Food search
Actor: Single owner
Type: Happy path / UX/UI
Priority: P0
Status: Required
Evidence: F-018, D-024, D-025
Confidence: High

User Story:
As a user,
I want to search the current Food catalog by name,
so that I can quickly find a Food without scrolling through the full list.

Preconditions:
- User is on `/foods`.
- Fresh Foods data can be loaded from the online API.

Acceptance Criteria:
- Given current catalog Foods match the search term
  When I enter a search term
  Then only matching current catalog Foods are shown.
- Given the search term has leading or trailing spaces
  When the search is submitted or applied
  Then the term is trimmed before searching.
- Given the matching Food was permanently deleted earlier
  When I search for its name
  Then the deleted Food is not shown.
- Given no current catalog Foods match the search term
  When search finishes
  Then the no-results message `لا توجد نتائج مطابقة للبحث.` is shown.
- Given I clear the search term
  When the list reloads successfully
  Then the full current catalog list is shown again.
- Given the Foods API is unreachable while searching
  When fresh data cannot load
  Then `تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.` is shown and cached personal Food data is not treated as current.
- Given I search on a 360px, 390px, 430px, or 768px viewport
  When results are shown
  Then the search input, result cards, and actions remain usable without horizontal scrolling.
- Given the query or Food names mix Arabic, English, and numbers
  When results render in RTL layout
  Then text remains readable and actions do not overlap names.

Field Rules:
- Search query is optional.
- Search query is trimmed.
- Search applies to current catalog Food names.
- Deleted Foods do not appear because they are no longer in the catalog.

Negative Scenarios:
- Network/API failure shows the Foods list read-failure Arabic message.
- No-results state is distinct from empty catalog state.
- Search must not use stale local cache as source of truth.

Verification:
- API/search tests.
- E2E search and no-results tests.
- Mobile RTL visual checks.

### US-FOOD-STATE-001 - Show Food Loading, Empty, No-Results, and Read-Failure States

Feature: Food state handling
Actor: Single owner
Type: UX/UI / Error handling
Priority: P0
Status: Required
Evidence: F-027, D-013, D-022, D-024, D-025, D-026
Confidence: High

User Story:
As a user,
I want the Foods page to clearly show loading, empty, no-results, and read-failure states,
so that I know whether to wait, add a Food, change search, or retry the connection.

Preconditions:
- User is on `/foods`.

Acceptance Criteria:
- Given the Foods list request is pending
  When `/foods` loads
  Then `جاري تحميل الأطعمة.` is shown in a status region.
- Given the online API returns an empty current catalog
  When `/foods` loads successfully
  Then `لا توجد أطعمة بعد. أضف أول طعام للبدء.` is shown with an Add Food action that navigates to `/foods/new`.
- Given the current catalog has Foods but the search returns no matches
  When search finishes
  Then `لا توجد نتائج مطابقة للبحث.` is shown and the empty catalog message is not shown.
- Given the Foods list API fails because of timeout, network failure, or server unavailability
  When fresh data cannot load
  Then `تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.` is shown with a retry action.
- Given a retry is available
  When I retry after a failed read
  Then the app requests fresh API data again and does not treat cached personal Food data as current.
- Given these states render on mobile
  When the keyboard, bottom navigation, or safe area is present
  Then the state message and primary action remain visible and tappable.
- Given the UI is Arabic RTL
  When state messages render
  Then text direction, icons, and actions remain readable and correctly aligned.

Field Rules:
- N/A.

Negative Scenarios:
- Loading state must not show stale Food rows as current.
- Empty catalog must not appear when a search query simply has no matches.
- Read failure must not say data was saved locally or will sync later.

Verification:
- Component state tests.
- E2E loading/empty/no-results/read-failure tests.
- Mobile and RTL checks.

### US-FOOD-CRUD-001 - Create Food on Standalone Page

Feature: Food create
Actor: Single owner
Type: CRUD / Happy path
Priority: P0
Status: Required
Evidence: D-024, D-025
Confidence: High

User Story:
As a user,
I want to add a Food on a dedicated page with grouped fields,
so that I can accurately save nutrition data without a cramped list-page form.

Preconditions:
- User is on `/foods/new`.
- Backend API is reachable.

Acceptance Criteria:
- Given I enter valid required fields
  When I submit the Add Food form
  Then the Food is saved only after a successful API response and I return to or can navigate back to `/foods`.
- Given I open `/foods/new`
  When I inspect the form
  Then fields are grouped into Basic food information, Nutrition basis, Core nutrition values, Default unit, Optional nutrients, and Notes/data source.
- Given optional nutrients are not expanded
  When the page first loads
  Then the Optional nutrients section is collapsed by default.
- Given optional nutrients are blank
  When I submit valid required fields
  Then blank optional nutrients do not block saving.
- Given I select back/cancel
  When I confirm leaving or navigate away
  Then no Food is saved unless the save API has already succeeded.
- Given a save request is pending
  When I tap/click save repeatedly
  Then exactly one API request is sent.

Field Rules:
- Required: `name`, `nutrition_basis`, `calories`, `protein_g`, `carb_g`, `fat_g`, `default_unit_type`, `unit_amount`, `unit_basis`.
- Optional: `brand`, `category`, optional nutrients, `notes`, `data_source`.
- Nutrition basis: `per_100g` or `per_100ml`.
- Default unit type: `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon`.
- Unit basis: `g` or `ml`.
- Vitamin D is stored in mcg.

Negative Scenarios:
- Network/API failure preserves entered data, shows Arabic error, and does not save locally or queue.
- Missing required fields show Arabic field-level errors.
- Invalid optional nutrient values show errors only when provided.

Verification:
- API tests.
- Component validation tests.
- E2E Add Food tests.

### US-FOOD-CRUD-002 - Edit Food on Standalone Page

Feature: Food edit
Actor: Single owner
Type: CRUD / Happy path / Negative path
Priority: P0
Status: Required
Evidence: F-020, D-023, D-024, D-025, D-026
Confidence: High

User Story:
As a user,
I want to edit an existing Food on a dedicated edit page,
so that I can correct Food details without changing old Diary history.

Preconditions:
- Food exists in the current catalog.
- User opens `/foods/:id/edit`.
- Backend API is reachable.

Acceptance Criteria:
- Given I open `/foods/:id/edit`
  When the Food detail loads successfully
  Then the edit form is prefilled with the current Food values.
- Given the edit page loads
  When I inspect the form
  Then it uses the same grouped structure as Add Food: Basic food information, Nutrition basis, Core nutrition values, Default unit, Optional nutrients, and Notes/data source.
- Given I submit valid changes
  When the save API succeeds
  Then the Food details and `/foods` list show the updated current catalog values.
- Given the edited Food was already used in Diary entries
  When the edit succeeds
  Then existing Diary entries keep their original snapshot values and totals.
- Given the edit would create a current catalog duplicate using the D-025 duplicate key
  When I submit
  Then saving is blocked and the duplicate Arabic message is shown.
- Given optional nutrients are blank
  When required fields are valid
  Then blank optional nutrients do not block saving.
- Given provided optional nutrients violate D-026
  When I submit
  Then saving is blocked with field-level Arabic errors.
- Given the Food was permanently deleted before I submit edits
  When I submit
  Then the stale Food Arabic message is shown and no local update is saved.
- Given the save API fails
  When the error is shown
  Then visible edited data remains in the form, nothing is saved locally, and no offline mutation is queued.
- Given the save request is pending
  When I tap/click save repeatedly
  Then exactly one API request is sent.
- Given I cancel or navigate back before a successful save
  When I return to `/foods`
  Then unsaved changes are not persisted.
- Given I use the edit page on 360px, 390px, 430px, or 768px viewport
  When I edit fields
  Then the form remains usable without horizontal scrolling and the keyboard does not hide the primary save action.
- Given the Food name mixes Arabic, English, and numbers
  When the edit page renders in RTL
  Then the full Food name remains readable.

Field Rules:
- Editable fields follow the Food field dictionary.
- System fields `id`, `created_at`, and `updated_at` are not user-editable.
- Delete may be available from edit only for an existing Food; Add Food must not show delete.

Negative Scenarios:
- Duplicate current catalog Food is blocked.
- Stale/deleted Food edit is rejected.
- Network/API failure preserves visible form input.
- D-026 optional nutrient validation blocks invalid provided values.

Verification:
- API update tests.
- Component form validation tests.
- E2E edit, stale edit, duplicate edit, and network failure tests.
- Mobile RTL checks.

### US-FOOD-VALIDATION-003 - Block Current Catalog Duplicate Food

Feature: Duplicate food handling
Actor: Single owner
Type: Field validation / Negative path
Priority: P0
Status: Required
Evidence: D-006, D-025
Confidence: High

User Story:
As a user,
I want the system to prevent exact duplicate Foods currently in my catalog,
so that my Food list stays clean without blocking foods I deleted earlier.

Preconditions:
- At least one matching Food exists in the current catalog.

Acceptance Criteria:
- Given a current catalog Food has the same normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`
  When I submit a create or edit that would duplicate it
  Then save is blocked and the duplicate Arabic message is shown.
- Given a previously matching Food was deleted
  When I create the same Food again
  Then the deleted Food does not block creation.
- Given the name differs only by repeated spaces or English case
  When the other duplicate key fields match
  Then the duplicate is blocked.
- Given brand or category differs
  When the duplicate key fields match
  Then the duplicate is still blocked because brand/category are not part of the key.

Field Rules:
- Duplicate key: normalized `name`, `nutrition_basis`, `default_unit_type`, numeric `unit_amount`, normalized `unit_basis`.

Negative Scenarios:
- Duplicate check must not include deleted Foods.

Verification:
- API/service duplicate tests.
- E2E duplicate message test.

### US-FOOD-VALIDATION-004 - Validate Optional Nutrient Ranges

Feature: Optional nutrient validation
Actor: Single owner
Type: Field validation / Negative path
Priority: P0
Status: Required
Evidence: D-026
Confidence: High

User Story:
As a user,
I want optional nutrients to be optional but validated when entered,
so that I can save simple foods quickly while preventing impossible nutrition details.

Preconditions:
- User is on `/foods/new` or `/foods/:id/edit`.
- Optional nutrients section is available and collapsed by default.

Acceptance Criteria:
- Given all optional nutrient fields are blank
  When required Food fields are valid and I save
  Then blank optional nutrients do not block saving.
- Given an optional nutrient value is `0`
  When I save
  Then the value is accepted as a real zero.
- Given an optional nutrient value is negative
  When I save
  Then saving is blocked and `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.` appears near that field.
- Given an optional nutrient value is above its D-026 maximum
  When I save
  Then saving is blocked and `القيمة الغذائية الإضافية أعلى من الحد المسموح.` appears near that field.
- Given `fiber_g` is greater than `carb_g`
  When I save
  Then saving is blocked and `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.` appears near fiber.
- Given `added_sugar_g` is greater than `sugar_g` and both are provided
  When I save
  Then saving is blocked and `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.` appears near added sugar.
- Given `saturated_fat_g` is greater than `fat_g`
  When I save
  Then saving is blocked and `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.` appears near saturated fat.
- Given `trans_fat_g` is greater than `fat_g`
  When I save
  Then saving is blocked and `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.` appears near trans fat.
- Given `saturated_fat_g + trans_fat_g` is greater than `fat_g` and all values are provided
  When I save
  Then saving is blocked and `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.` appears near the fat fields.
- Given the first invalid optional nutrient is inside the collapsed optional section
  When validation fails
  Then the optional section opens and focus moves to the first invalid field.

Field Rules:
- D-026 ranges apply per 100g/per 100ml nutrition basis.
- Fiber, sugar, and added sugar: 0-100 g.
- Saturated fat and trans fat: 0-100 g.
- Cholesterol: 0-2000 mg.
- Sodium: 0-50000 mg.
- Potassium: 0-10000 mg.
- Calcium: 0-5000 mg.
- Iron: 0-100 mg.
- Magnesium: 0-1000 mg.
- Zinc: 0-100 mg.
- Vitamin D: 0-250 mcg.
- Vitamin B12: 0-1000 mcg.
- Vitamin C: 0-5000 mg.
- Vitamin A: 0-3000 mcg.
- Folate: 0-2000 mcg.
- Vitamin K: 0-2000 mcg.

Negative Scenarios:
- Non-numeric optional nutrient values show the invalid number Arabic error.
- Optional nutrient validation failure does not save locally and does not queue offline writes.

Verification:
- API validation tests for each D-026 range.
- Component tests for collapsed-section expansion and field-level errors.
- E2E tests for create/edit optional nutrient failures.

### US-FOOD-CRUD-003 - Permanently Delete Food With Confirmation

Feature: Food delete
Actor: Single owner
Type: CRUD / Destructive action
Priority: P0
Status: Required
Evidence: D-025
Confidence: High

User Story:
As a user,
I want Food deletion to require confirmation and permanently remove the Food from my catalog,
so that I avoid accidental deletion while keeping the catalog simple.

Preconditions:
- Food exists in the current catalog.

Acceptance Criteria:
- Given I choose Delete for a Food
  When the confirmation dialog opens
  Then it shows the Food name and states deletion is permanent.
- Given the confirmation dialog is open
  When I select Cancel or press Escape
  Then no API delete is sent and the Food remains visible.
- Given I confirm deletion and the API succeeds
  When the operation completes
  Then the Food disappears from Foods list, Food search results, and future Diary food selection.
- Given the Food was used in old Diary entries
  When I delete the Food
  Then old Diary entries remain readable and accurate through their nutrition snapshots.
- Given the delete API fails
  When the error is shown
  Then the Food remains visible, no local delete is queued, and input/state can be retried.
- Given the delete request is pending
  When I confirm repeatedly
  Then exactly one delete request is sent.

Field Rules:
- N/A.

Negative Scenarios:
- No archive/inactive state is created.
- No `is_active` or `archived_at` value is required.
- No restore action exists in v1.

Verification:
- API delete tests.
- E2E confirmation/cancel/confirm tests.
- Snapshot-after-delete regression tests.
- Accessibility dialog tests.

### US-FOOD-HAPPY-003 - View Food Details

Feature: Food details
Actor: Single owner
Type: Read / Happy path
Priority: P1
Status: Required
Evidence: D-024, D-025
Confidence: High

User Story:
As a user,
I want to view full Food details on a dedicated details page,
so that I can inspect the full name, nutrition basis, default unit, core nutrition, optional nutrients, notes, and data source before editing or deleting.

Preconditions:
- Food exists in the current catalog.

Acceptance Criteria:
- Given I open `/foods/:id`
  When Food details load successfully
  Then the page shows the full Food name and available Food data.
- Given optional nutrients are missing
  When details load
  Then missing optional nutrients are not shown as required or blocking errors.
- Given the Food detail API fails
  When the page cannot load fresh data
  Then the exact Food detail read-failure Arabic copy is shown.

Field Rules:
- Details display data as plain text and must not execute markup.

Negative Scenarios:
- Deleted Food details should show not-found/stale behavior rather than a stale cached source of truth.

Verification:
- E2E detail view tests.
- Network failure tests.

## Legacy Food Catalog User Stories

The legacy Food stories below are retained for traceability only. If they mention archive/inactive state, `is_active`, `archived_at`, Active/Archived filters, `serving_label`, or `serving_grams` as the Food source-of-truth, the current D-024, D-025, and D-026 stories above control v1 requirements.

## Food Catalog

### LEGACY-US-FOOD-HAPPY-001 - Browse Current Foods

Feature: Current food list
Actor: Single owner
Type: Happy / Read
Priority: P0
Status: Superseded by current D-024/D-025 Food list stories
Evidence: `FoodsPage.tsx`, `foods.py`
Confidence: High

User Story:
As a user, I want to browse current saved foods, so that I can reuse them for meal logging.

Acceptance Criteria:
- Given current catalog foods exist
  When the Foods page loads successfully
  Then each current food row/card shows the D-025 list summary fields.
- Given a food is permanently deleted
  When the Foods page loads
  Then the deleted food is not shown.
- Given no current catalog foods exist
  When the page loads
  Then the empty catalog state is shown.

### LEGACY-US-FOOD-HAPPY-002 - Search Current Foods by Name

Feature: Food search
Actor: Single owner
Type: Happy / Read
Priority: P0
Status: Implemented / state handling needs alignment
Evidence: `FoodsPage.tsx`, `food.py`
Confidence: High

User Story:
As a user, I want to search current foods by name, so that I can find a food quickly.

Acceptance Criteria:
- Given current catalog foods match the search term
  When I search
  Then only matching current catalog foods are shown.
- Given no current catalog foods match
  When search finishes
  Then the no-results state `ظ„ط§ طھظˆط¬ط¯ ظ†طھط§ط¦ط¬ ظ…ط·ط§ط¨ظ‚ط© ظ„ظ„ط¨ط­ط«.` is shown.
- Given a permanently deleted food name matches
  When I search
  Then the deleted food is not shown.

### LEGACY-US-FOOD-STATE-001 - Show Food Loading, Empty, No-Results, and Error States

Feature: Food state handling
Actor: Single owner
Type: UX/UI / Error Handling
Priority: P1
Status: Required / current code partial
Evidence: `FoodsPage.tsx`, QA audit
Confidence: High

User Story:
As a user, I want the Foods page to clearly distinguish loading, empty, no-results, and connection errors, so that I know what to do next.

Acceptance Criteria:
- Given foods are loading
  When the API request is pending
  Then `ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ط§ظ„ط£ط·ط¹ظ…ط©.` is shown.
- Given no current catalog foods exist
  When the request succeeds
  Then `ظ„ط§ طھظˆط¬ط¯ ط£ط·ط¹ظ…ط© ط¨ط¹ط¯. ط£ط¶ظپ ط£ظˆظ„ ط·ط¹ط§ظ… ظ„ظ„ط¨ط¯ط،.` is shown with add-food access.
- Given search has no matches
  When the request succeeds
  Then no-results copy is shown.
- Given the API cannot load foods
  When the request fails
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown for network/timeout failures and cached personal food data is not treated as current.

### LEGACY-US-FOOD-CRUD-001 - Create Food

Feature: Food create
Actor: Single owner
Type: Happy / CRUD / Field Validation
Priority: P0
Status: Implemented / validation and online-only alignment needed
Evidence: `FoodsPage.tsx`, `foods.py`, `schemas.py`
Confidence: High

User Story:
As a user, I want to add a current catalog food with D-025 nutrition and default-unit values, so that I can log it in Diary.

Acceptance Criteria:
- Given required food fields are valid and no current-catalog duplicate exists
  When I save and the API succeeds
  Then the food is created with D-025 per-100g/per-100ml nutrition basis and default-unit fields.
- Given optional nutrient values are blank
  When I save
  Then they are stored as null/unknown, not forced to zero.
- Given the API fails
  When I save
  Then the food is not created locally, no mutation is queued, the draft remains visible in the same form state until I edit it, reset it, retry successfully, or navigate away, and the correct Arabic error is shown.

### LEGACY-US-FOOD-VALIDATION-001 - Reject Invalid Food Fields

Feature: Food validation
Actor: Single owner
Type: Field Validation / Negative
Priority: P0
Status: Required / current code needs alignment
Evidence: `schemas.py`, `FoodsPage.tsx`
Confidence: High

User Story:
As a user, I want invalid food values rejected clearly, so that food totals stay accurate.

Acceptance Criteria:
- Given name or serving label is empty or whitespace-only
  When I save
  Then save is blocked with `ظ‡ط°ط§ ط§ظ„ط­ظ‚ظ„ ظ…ط·ظ„ظˆط¨.`
- Given any numeric field is non-numeric
  When I save
  Then save is blocked with `ط£ط¯ط®ظ„ ط±ظ‚ظ…ظ‹ط§ طµط­ظٹط­ظ‹ط§.`
- Given a value is below minimum or above maximum
  When I save
  Then save is blocked with the matching min/max Arabic message.

### LEGACY-US-FOOD-VALIDATION-002 - Prevent Negative Net Carbs

Feature: Net carbs validation
Actor: Single owner
Type: Field Validation / Negative
Priority: P0
Status: Required / current code needs alignment
Evidence: `services/food.py`, `schemas.py`
Confidence: High

User Story:
As a user, I want fiber validated against carbs, so that net carbs never become negative.

Acceptance Criteria:
- Given `fiber_g` is greater than `carb_g`
  When I create or update a food
  Then save is blocked with `ط§ظ„ط£ظ„ظٹط§ظپ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† طھظƒظˆظ† ط£ظƒط¨ط± ظ…ظ† ط§ظ„ظƒط±ط¨ظˆظ‡ظٹط¯ط±ط§طھ.`
- Given `fiber_g` is blank
  When net carbs are calculated
  Then fiber is treated as zero.

### LEGACY-US-FOOD-VALIDATION-003 - Block Current-Catalog Duplicate Foods

Feature: Duplicate food handling
Actor: Single owner
Type: Field Validation / Negative
Priority: P0
Status: Required / current code needs alignment
Evidence: Product decisions D-005, D-006; no current duplicate check
Confidence: High

User Story:
As a user, I want exact current-catalog duplicate foods blocked, so that my catalog stays clean.

Acceptance Criteria:
- Given a current-catalog food exists with the same normalized name, nutrition basis, default unit type, unit amount, and unit basis
  When I create or edit a matching food
  Then save is blocked with `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ…ظˆط¬ظˆط¯ ظ…ط³ط¨ظ‚ظ‹ط§ ط¨ظ†ظپط³ ط§ظ„ط­طµط©.`
- Given a matching food was permanently deleted
  When I create a new matching food
  Then save is allowed.
- Given the same name has a different nutrition basis or default unit identity
  When I save
  Then it is allowed.

### LEGACY-US-FOOD-CRUD-002 - Edit Food

Feature: Food edit
Actor: Single owner
Type: Happy / CRUD
Priority: P0
Status: Implemented / validation and online-only alignment needed
Evidence: `FoodsPage.tsx`, `foods.py`
Confidence: High

User Story:
As a user, I want to edit an existing current catalog food, so that I can correct its nutrition or default-unit values.

Acceptance Criteria:
- Given I select edit on an existing current catalog food
  When the form enters edit mode
  Then editable fields are populated.
- Given valid changes do not create a current-catalog duplicate
  When the API succeeds
  Then the food shows updated values.
- Given the food was already used in Diary
  When I update the food
  Then existing diary entries keep original snapshot values.
- Given the API fails
  When I save changes
  Then the food is not updated locally, no mutation is queued, and the edited values remain visible in the same form state until I edit them, reset them, retry successfully, or navigate away.

### LEGACY-US-FOOD-CRUD-003 - Delete Food Permanently With Confirmation

Feature: Food permanent delete
Actor: Single owner
Type: CRUD / Destructive / Accessibility
Priority: P0
Status: Superseded by D-025 hard-delete requirement / current code needs confirmation alignment
Evidence: `FoodsPage.tsx`, `food.py`, product decision D-025
Confidence: High

User Story:
As a user, I want food deletion to require confirmation and permanently remove the food from the catalog, so that the catalog stays clean while old Diary entries remain intact through snapshots.

Acceptance Criteria:
- Given I select delete on a food
  When the dialog opens
  Then it shows the food name and explains deletion is permanent.
- Given I cancel or press Escape
  When the dialog closes
  Then no food is changed.
- Given I confirm and the API succeeds
  When delete completes
  Then the Food is permanently removed from the catalog and disappears from Foods list, search, and future Diary selection.
- Given the API fails
  When delete fails
  Then the food remains visible, no local delete is queued, and an Arabic error is shown.
- Given old diary entries used the food
  When the food is deleted
  Then existing entries keep their snapshot nutrition.

### LEGACY-US-FOOD-EDGE-001 - Handle Stale Food During Edit, Delete, or Diary Logging

Feature: Food stale-record handling
Actor: Single owner
Type: Edge / Negative / Data Integrity
Priority: P0
Status: Required / current code needs alignment
Evidence: D-023, D-025, Diary food selection
Confidence: High

User Story:
As a user, I want the app to detect when a selected food is no longer current, so that I do not save diary entries or edits from stale food data.

Acceptance Criteria:
- Given a food is deleted after I open edit mode
  When I submit the edit
  Then the edit is rejected with `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` and no local update is saved.
- Given a food is deleted after I select it for Diary logging
  When I submit the diary entry
  Then the entry is not created and `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given a selected food changes before Diary submit
  When the API accepts the diary entry
  Then the snapshot uses the server-confirmed food values returned by the successful API response.
- Given a selected food changes before Diary submit and the API rejects the stale submission
  When the rejection is handled
  Then `طھظ… طھط؛ظٹظٹط± ط¨ظٹط§ظ†ط§طھ ط§ظ„ط·ط¹ط§ظ… ظ‚ط¨ظ„ ط§ظ„ط­ظپط¸. ط­ط¯ظ‘ط« ط§ظ„ط¨ظٹط§ظ†ط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and no local diary entry is created.

### LEGACY-US-FOOD-HAPPY-003 - View Food Details

Feature: Food details
Actor: Single owner
Type: Happy / Read
Priority: P1
Status: Implemented
Evidence: `FoodsPage.tsx`
Confidence: High

User Story:
As a user, I want to view optional nutrient details, so that I can inspect food values beyond the row summary.

Acceptance Criteria:
- Given a food row exists
  When I open details
  Then nutrition basis, default unit, core nutrition values, and optional nutrient fields are shown.
- Given an optional field is missing
  When details display
  Then a neutral placeholder is shown.
- Given the food detail API read fails
  When the details view cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and edit submit is unavailable until fresh data loads.

## Diary and Weekly Tracking

### US-DIARY-HAPPY-001 - View Diary for Selected Day

Feature: Diary day view
Actor: Single owner
Type: Happy / Read
Priority: P0
Status: Implemented / online error alignment needed
Evidence: `DiaryPage.tsx`, `diary.py`
Confidence: High

User Story:
As a user, I want to view diary entries for a selected day, so that I can see what I logged.

Acceptance Criteria:
- Given entries exist for the selected date
  When the day view loads
  Then entries are listed with food name, mode/quantity, calories, and macros.
- Given no entries exist
  When the day view loads
  Then `ظ„ط§ طھظˆط¬ط¯ ظˆط¬ط¨ط§طھ ظ…ط³ط¬ظ„ط© ظ„ظ‡ط°ط§ ط§ظ„ظٹظˆظ….` is shown.
- Given the API read fails
  When the page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached diary data is not treated as current.

### US-DIARY-CRUD-001 - Add Diary Entry by Servings

Feature: Diary create by servings
Actor: Single owner
Type: Happy / CRUD
Priority: P0
Status: Implemented / validation and online-only alignment needed
Evidence: `DiaryPage.tsx`, `diary.py`
Confidence: High

User Story:
As a user, I want to log a food by serving quantity, so that my daily totals update.

Acceptance Criteria:
- Given at least one current catalog Food exists, selected date is today/past, and serving quantity is 0.01-50
  When I submit and the API succeeds
  Then a diary entry is created for the selected date and totals refresh.
- Given the API fails
  When I submit
  Then the entry is not created locally, no mutation is queued, input remains visible in the same form state until I edit it, reset it, retry successfully, or navigate away, and an Arabic error is shown.

### US-DIARY-GRAM-001 - Add Diary Entry by Grams

Feature: Diary create by grams
Actor: Single owner
Type: Happy / Calculation / Field Validation
Priority: P0
Status: Required / missing in current code
Evidence: D-007, D-021, D-025
Confidence: High

User Story:
As a user, I want to log food by grams when the Food can support gram calculation, so that weighed foods are accurate.

Acceptance Criteria:
- Given the selected current catalog Food has nutrition basis/default-unit data that supports an unambiguous gram calculation and grams are 1-5000
  When I submit in gram mode
  Then gram totals are calculated from Food nutrition basis/default-unit snapshot data.
- Given the selected Food cannot support an unambiguous gram calculation from nutrition basis/default-unit data
  When gram mode is selected
  Then gram entry is disabled or shows `لا يمكن التسجيل بالجرام لهذا الطعام لأن بيانات الوحدة أو أساس القيم الغذائية غير مكتملة.`
- Given gram-mode entry is saved
  When the diary entry is returned
  Then the snapshot includes `log_mode="grams"`, `logged_quantity`, nutrition basis, nutrition values at logging time, default-unit data used for calculation, and `calculated_totals`.

### US-DIARY-GRAM-CONTRACT-001 - Use Final Diary Quantity Mode Contract

Feature: Diary API/storage contract
Actor: System
Type: Data Contract / Calculation
Priority: P0
Status: Required / current code needs alignment
Evidence: D-021, `diary.py`, `schemas.py`, `services/diary.py`
Confidence: High

User Story:
As the system, I want Diary entries to store an explicit quantity mode, so that serving-based and gram-based entries calculate and edit correctly.

Acceptance Criteria:
- Given the user logs by servings
  When the API receives create payload `{ entry_date, food_id, log_mode: "servings", quantity }`
  Then `quantity` is validated as serving count 0.01-50.
- Given the user logs by grams
  When the API receives create payload `{ entry_date, food_id, log_mode: "grams", quantity }`
  Then `quantity` is validated as grams 1-5000 and the selected Food must have nutrition basis/default-unit data that supports an unambiguous gram calculation.
- Given a Diary entry is persisted
  When it is returned by the API
  Then it includes `log_mode`, mode-specific `quantity`, `nutrition_snapshot`, and calculated totals.
- Given totals are calculated
  When `log_mode="servings"`
  Then `serving_multiplier = quantity`.
- Given totals are calculated
  When `log_mode="grams"`
  Then this legacy criterion is superseded by D-025: current v1 recalculates totals from the original nutrition basis/default-unit snapshot data.
- Given day or weekly totals are displayed
  When entries are aggregated
  Then aggregation uses `nutrition_snapshot.calculated_totals`, not current Food nutrition values.

### US-DIARY-VALIDATION-001 - Reject Invalid Diary Inputs

Feature: Diary validation
Actor: Single owner
Type: Field Validation / Negative
Priority: P0
Status: Required / current code needs alignment
Evidence: `schemas.py`, `DiaryPage.tsx`
Confidence: High

User Story:
As a user, I want invalid diary dates and quantities rejected, so that totals are accurate.

Acceptance Criteria:
- Given selected date is in the future
  When I create or edit a diary entry
  Then save is blocked with `ظ„ط§ ظٹظ…ظƒظ† طھط³ط¬ظٹظ„ ظٹظˆظ…ظٹط§طھ ط¨طھط§ط±ظٹط® ظ…ط³طھظ‚ط¨ظ„ظٹ.`
- Given serving quantity is outside 0.01-50
  When I submit
  Then save is blocked with the matching min/max Arabic error.
- Given gram quantity is outside 1-5000
  When I submit
  Then save is blocked with the matching min/max Arabic error.
- Given no current catalog Foods exist
  When I view the add form
  Then submit is disabled and `ط£ط¶ظپ ط·ط¹ط§ظ…ظ‹ط§ ط£ظˆظ„ظ‹ط§ ظ‚ط¨ظ„ طھط³ط¬ظٹظ„ ط§ظ„ظˆط¬ط¨ط§طھ.` is shown.

### US-DIARY-EDIT-001 - Edit Diary Quantity Only

Feature: Diary quantity edit
Actor: Single owner
Type: CRUD / Edit
Priority: P1
Status: Required / current code needs alignment
Evidence: `backend/app/api/routes/diary.py`, no edit UI
Confidence: High

User Story:
As a user, I want to edit only the quantity of a diary entry, so that I can correct amount mistakes without changing historical food identity.

Acceptance Criteria:
- Given an entry was logged by servings
  When I edit it
  Then only serving quantity can be changed within 0.01-50.
- Given an entry was logged by grams
  When I edit it
  Then only gram quantity can be changed within 1-5000.
- Given I edit an entry
  When the UI is shown
  Then `log_mode`, food, entry date, and snapshot nutrition values are not editable.
- Given I submit an edit
  When the API request is sent
  Then the payload is `{ quantity }` only.
- Given I edit a gram-mode entry
  When the API succeeds
  Then the original `log_mode`, food identity, entry date, and snapshot nutrition values remain unchanged while `calculated_totals` are recalculated from the new gram quantity.
- Given the API fails
  When I save the edit
  Then the old entry remains unchanged and no mutation is queued.

### US-DIARY-INTEGRITY-001 - Preserve Nutrition Snapshots

Feature: Diary snapshot
Actor: System
Type: Data Integrity
Priority: P0
Status: Implemented / gram-mode extension required
Evidence: `diary.py`, `test_diary_snapshot.py`
Confidence: High

User Story:
As the system, I want each diary entry to store a nutrition snapshot, so that historical totals do not change after food edits or permanent Food deletion.

Acceptance Criteria:
- Given a serving-mode diary entry is created
  When the food is edited or permanently deleted later
  Then diary entry totals stay unchanged.
- Given a gram-mode diary entry is created
  When the food is edited or permanently deleted later
  Then the calculated gram-mode snapshot totals stay unchanged.
- Given the user edits a diary entry
  When quantity changes
  Then `log_mode`, food/date identity, and snapshot nutrition values are not manually changed.

### US-DIARY-CRUD-002 - Delete Diary Entry Online

Feature: Diary delete
Actor: Single owner
Type: CRUD / Destructive
Priority: P1
Status: Implemented / confirmation and online-only alignment needed
Evidence: `DiaryPage.tsx`, `diary.py`, D-018
Confidence: High

User Story:
As a user, I want to confirm deletion of a mistaken diary entry and delete it only after the API succeeds, so that my daily and weekly totals are corrected without accidental loss.

Acceptance Criteria:
- Given I select delete on a diary entry
  When the confirmation dialog opens
  Then it shows the food name and entry date.
- Given the confirmation dialog is open
  When I cancel or close it
  Then no diary entry changes.
- Given I confirm deletion and the API succeeds
  When the response returns
  Then the entry is removed and daily and weekly totals refresh.
- Given the API fails
  When I delete an entry
  Then the entry remains visible, no local delete is queued, and an Arabic error is shown.
- Given the entry was already deleted before my edit or delete request completes
  When the API rejects the request
  Then `ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظٹظˆظ…ظٹط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and no local update/delete is applied.

### US-DIARY-HAPPY-002 - View Weekly Summary

Feature: Weekly summary
Actor: Single owner
Type: Happy / Read
Priority: P0
Status: Implemented / network error alignment needed
Evidence: `aggregation.py`, `DiaryPage.tsx`
Confidence: High

User Story:
As a user, I want a Sunday-to-Saturday weekly summary, so that I can compare daily calories against targets.

Acceptance Criteria:
- Given a selected date
  When weekly summary is requested
  Then the system normalizes the week to Sunday through Saturday.
- Given entries exist in the week
  When the week displays
  Then each day shows calories and progress against targets.
- Given the API read fails
  When the week cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached weekly totals are not treated as current.

## Online Data and Error Handling

### US-NETWORK-READ-001 - Handle API Read Failures

Feature: Online API reads
Actor: Single owner
Type: Negative / Error Handling
Priority: P0
Status: Required / current code needs alignment
Evidence: `api.ts`, page queries, D-001, D-013, D-022
Confidence: High

User Story:
As a user, I want a clear error when fresh data cannot load, so that I know the displayed data is not current.

Acceptance Criteria:
- Given Profile, Foods, Diary, or Week API read fails due to timeout/network
  When the page cannot load fresh data
  Then the page-specific read failure message from `06_ERROR_MESSAGES.md` is shown and cached personal data is not treated as current.
- Given the API returns 401, 404, or 5xx
  When a read fails
  Then the UI shows the exact Arabic 401, 404, or 5xx message defined in `06_ERROR_MESSAGES.md`.

### US-NETWORK-READ-COPY-001 - Show Exact Read Failure Messages

Feature: Online API reads
Actor: Single owner
Type: Error Handling / UX Copy
Priority: P0
Status: Required / current UI needs alignment
Evidence: D-022, `06_ERROR_MESSAGES.md`
Confidence: High

User Story:
As a user, I want read failures to use page-specific Arabic messages, so that I know what failed to load.

Acceptance Criteria:
- Given Profile load fails because of timeout/network
  When the Profile page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given Foods list load fails because of timeout/network
  When the Foods page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given Food detail load fails because of timeout/network
  When the detail/edit view cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given Diary day load fails because of timeout/network
  When the Diary day cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given Weekly summary load fails because of timeout/network
  When the weekly summary cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given a generic read fails outside the named areas
  When no page-specific message applies
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.

### US-NETWORK-WRITE-001 - Handle API Write Failures Without Local Persistence

Feature: Online API writes
Actor: Single owner
Type: Negative / Data Integrity
Priority: P0
Status: Required / current code needs alignment
Evidence: `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts`
Confidence: High

User Story:
As a user, I want failed saves and deletes to remain unsaved, so that I do not mistake local queued data for real saved data.

Acceptance Criteria:
- Given a Profile, Food, or Diary write fails
  When the API does not return success
  Then no IndexedDB record is written, no mutation is queued, and no saved/synced-later message appears.
- Given the user entered form data before failure
  When failure message displays
  Then the same visible input remains in the form until the user edits it, resets it, retries successfully, or navigates away.

### US-ERROR-MAPPING-001 - Apply Shared API Error Mapping

Feature: API error mapping
Actor: System
Type: Error Handling / Validation
Priority: P0
Status: Required / current code needs alignment
Evidence: D-013, D-022, `frontend/lib/api.ts`
Confidence: High

User Story:
As the system, I want API errors mapped consistently, so that users receive clear Arabic recovery messages.

Acceptance Criteria:
- Given API returns 401
  When the UI handles it
  Then `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` is shown.
- Given API returns 404
  When the UI handles it
  Then `ط§ظ„ط¹ظ†طµط± ط؛ظٹط± ظ…ظˆط¬ظˆط¯. ط­ط¯ظ‘ط« ط§ظ„طµظپط­ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given API returns 422
  When known field details are available
  Then field errors are shown beside the affected fields.
- Given API returns 422 with unknown field or form-level details
  When the UI handles it
  Then `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown at form level.
- Given timeout/network or 5xx occurs
  When the UI handles it
  Then the message shown is exactly the timeout/network or 5xx Arabic message defined in `06_ERROR_MESSAGES.md` for that action or page.

### US-UX-STATUS-001 - Prevent Duplicate Submits and Support Retry

Feature: Online submit state handling
Actor: Single owner
Type: UX/UI / Negative / Data Integrity
Priority: P0
Status: Required / current code needs alignment
Evidence: D-023, Profile/Food/Diary write flows
Confidence: High

User Story:
As a user, I want save and delete actions to block repeated submits while pending, so that slow network conditions do not create duplicate writes.

Acceptance Criteria:
- Given a Profile, Food, or Diary write request is pending
  When I click or tap the same submit/confirm action again
  Then the UI sends exactly one API request and shows `ط§ظ„ط·ظ„ط¨ ظ‚ظٹط¯ ط§ظ„ظ…ط¹ط§ظ„ط¬ط©. ط§ظ†طھط¸ط± ط­طھظ‰ ظٹظƒطھظ…ظ„.` or keeps the action disabled with a visible pending state.
- Given the pending write succeeds
  When the response returns
  Then the success state is shown only once and the page reflects the successful API response.
- Given the pending write fails
  When the error is shown
  Then the form input remains visible, the action is re-enabled, and retry submits the current visible input without using any offline/local queue.
- Given a Food permanent-delete or Diary delete confirmation is pending
  When I press Confirm repeatedly
  Then only one delete request is sent.

### US-FUTURE-OFFLINE-001 - Defer Offline Cache and Sync

Feature: Future offline cache and sync
Actor: Product team
Type: Future Scope
Priority: P3
Status: Future Scope
Evidence: `backend/app/api/routes/sync.py`, `frontend/lib/db.ts`, `backend/tests/test_sync.py`
Confidence: High

User Story:
As the product team, I want offline cache and sync deferred out of v1, so that v1 stays simple and reliable.

Acceptance Criteria:
- Given v1 scope is implemented
  When Profile, Food, or Diary writes fail
  Then changes are not queued offline.
- Given future offline-first work is planned
  When requirements are revisited
  Then sync queue, stale cache, conflict handling, pending sync states, and rejected sync operations are defined separately.

## Accessibility, Mobile, and Tests

### US-A11Y-001 - Provide Accessible Controls and Errors

Feature: Accessibility basics
Actor: Keyboard or screen-reader user
Type: Accessibility
Priority: P1
Status: Required / current code needs alignment
Evidence: UI components, D-011, D-014, D-015, D-018, D-023
Confidence: Medium

User Story:
As a keyboard or screen-reader user, I want controls, dialogs, and validation errors to be accessible, so that I can use the app reliably.

Acceptance Criteria:
- Given an icon-only button exists
  When inspected by assistive technology
  Then it has an accessible name.
- Given a field validation error occurs
  When the form is submitted
  Then the invalid field uses `aria-invalid`, its error is associated, and focus moves to the first invalid visible field.
- Given the first invalid field is inside a collapsed optional section
  When the form is submitted
  Then the section opens and focus moves to that invalid field.
- Given a Food permanent-delete or Diary delete confirmation dialog opens
  When using keyboard
  Then the dialog has an accessible name and description, initial focus is on the safest action, Escape/cancel closes without changes, and focus returns to the triggering control or nearest safe action after close.
- Given an async error/status appears
  When it is shown
  Then success/loading messages render in a `role="status"` or `aria-live="polite"` region and error/destructive messages render in `role="alert"` or an equivalent assertive live region.

### US-MOBILE-001 - Use the App on Supported Mobile and Desktop Viewports

Feature: Mobile/RTL UX
Actor: Mobile user
Type: Mobile / UX/UI / RTL
Priority: P1
Status: Required / needs QA verification
Evidence: `globals.css`, D-015, D-020
Confidence: High

User Story:
As a mobile user, I want pages and forms to remain readable and tappable, so that daily tracking works on my phone.

Acceptance Criteria:
- Given viewport width is 360, 390, 430, 768, or desktop width
  When a main page renders
  Then no horizontal scrolling is needed for standard use.
- Given buttons are displayed on mobile
  When I tap them
  Then touch targets are usable.
- Given keyboard opens on a form
  When I enter values
  Then critical form actions and errors remain reachable.
- Given Arabic/English mixed food text is shown
  When viewed on supported widths
  Then text remains readable and does not overlap controls.
- Given a food name is long
  When it is shown in food lists or cards
  Then it is limited to two lines with an ellipsis and does not cause horizontal scrolling or overlap action controls.
- Given a food name is long
  When it is shown in food details or edit views
  Then the full name remains readable in RTL layout.

### US-QA-001 - Cover Core v1 Behavior With Tests

Feature: Test coverage
Actor: Product owner / QA
Type: Testability
Priority: P1
Status: Required / current tests partial
Evidence: `backend/tests/test_calc.py`, `backend/tests/test_diary_snapshot.py`, `backend/tests/test_sync.py`
Confidence: High

User Story:
As QA, I want v1 behavior covered by focused tests, so that future changes do not break daily nutrition tracking.

Acceptance Criteria:
- Given tests run
  When calc and snapshot behavior are exercised
  Then existing test coverage passes and gram-mode snapshot behavior is added.
- Given Profile, Food, Diary, and online network behavior are changed
  When regression tests run
  Then CRUD, validation, archive, duplicate, network error, mobile, RTL, and accessibility behaviors are covered.
- Given sync tests exist
  When v1 test scope is evaluated
  Then sync tests are treated as Future Scope unless Engineering keeps them outside v1 acceptance.
- Given QA prepares v1 regression data
  When test data is created
  Then it includes boundary Profile values, duplicate current-catalog foods, deleted-food snapshot cases, Foods with D-025 default-unit data, D-026 optional nutrient failures, serving Diary entries, gram Diary entries, stale Food/Diary cases, duplicate-submit cases, and network/API read/write failures.
