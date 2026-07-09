# Recommended Story Updates

These are proposed story updates only. They do not modify application code or BA files.

Count of missing or weak stories proposed: 18.

## P0 and P1 Story Updates

### QA-US-NEW-001 - Handle API Read Failures Per Page

Feature: Online API reads  
Type: Negative / Error Handling  
Priority: P0  
Current status: Missing split from broad network story  
Evidence: `US-NETWORK-ERROR-001`, `frontend/lib/api.ts`, page queries

User story:
As a user, I want each page to show a clear connection error when fresh data cannot load, so that I know the displayed data is not current.

Acceptance criteria:
- Given the Profile, Foods, Diary, or Weekly Summary API read fails
  When the page cannot load fresh data
  Then the page shows a clear connection error and does not present cached personal data as current.
- Given the user retries after the backend is reachable
  When the read succeeds
  Then fresh API data is displayed.

Verification:
E2E/API-down tests for Profile, Foods, Diary day, and Weekly Summary.

### QA-US-NEW-002 - Handle API Write Failures Without Local Persistence

Feature: Online API writes  
Type: Negative / Data Integrity  
Priority: P0  
Current status: Weak / contradicts current code  
Evidence: `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts`

User story:
As a user, I want failed saves and deletes to remain unsaved, so that I do not mistake local queued data for real saved data.

Acceptance criteria:
- Given a Profile, Food, or Diary write fails because the API is unreachable
  When the request fails
  Then no IndexedDB record is written, no mutation is queued, and the UI clearly says the change was not saved.
- Given the user entered form data before the failure
  When the failure message displays
  Then the entered data remains available for retry.

Verification:
Component/E2E tests asserting no queued mutation and preserved form state.

### QA-US-NEW-003 - Rewrite Food Delete and Archive Lifecycle

Feature: Food delete/archive  
Type: CRUD / Destructive / Data Lifecycle  
Priority: P0  
Current status: Needs rewrite  
Evidence: `US-FOOD-CRUD-003`, `backend/app/models.py`, `backend/app/services/food.py`

User story:
As a user, I want food deletion to be confirmed and safe for foods already used in Diary, so that I do not damage my catalog or future logging flow.

Acceptance criteria:
- Given I choose delete for a food
  When the confirmation appears
  Then it names the food and explains whether it will be deleted or archived.
- Given the food has diary usage
  When I confirm
  Then the food becomes inactive/archived, is hidden from future Diary selection, and old diary snapshots remain unchanged.
- Given the food has no diary usage
  When I confirm
  Then the food may be hard deleted after successful API response.
- Given the API fails
  When delete/archive fails
  Then the food remains visible and no local delete/archive is queued.

Decision needed:
Archive field name and restore behavior.

### QA-US-NEW-004 - Resolve Duplicate Food Validation

Feature: Duplicate food prevention  
Type: Field Validation / Negative  
Priority: P0  
Current status: Weak  
Evidence: `US-FOOD-VALIDATION-003`, `docs/ba/12_OPEN_QUESTIONS.md`

User story:
As a user, I want exact duplicate foods blocked before saving, so that the food catalog stays clean and easy to search.

Acceptance criteria:
- Given an active food exists with the same normalized duplicate key
  When I create or edit a food to match it
  Then save is blocked with a clear Arabic duplicate message.
- Given a food has the same name but a different confirmed serving key
  When I save
  Then it is allowed.

Decision needed:
Whether duplicate key uses only `name + serving_label + serving_grams`, or also future `brand`.

### QA-US-NEW-005 - Validate Net Carbs Cannot Be Negative

Feature: Net carbs validation  
Type: Field Validation / Negative  
Priority: P0  
Current status: Weak / missing implementation  
Evidence: `services/food.py`, `US-FOOD-VALIDATION-002`

User story:
As a user, I want fiber values validated against carbs, so that net carbs never display as a negative number.

Acceptance criteria:
- Given `fiber_g` is greater than `carb_g`
  When I create or edit a food
  Then save is blocked before persistence and the fiber field displays a clear Arabic error.
- Given `fiber_g` is blank
  When net carbs are calculated
  Then fiber is treated as zero.

Verification:
Backend validation test, form validation test, food list/details display test.

### QA-US-NEW-006 - Complete Food Field Validation

Feature: Food validation  
Type: Field Validation  
Priority: P0  
Current status: Weak  
Evidence: `docs/ba/04_FIELD_DICTIONARY.md`, `docs/ba/05_VALIDATION_RULES.md`

User story:
As a user, I want each food field to validate clearly, so that my saved nutrition data is accurate.

Acceptance criteria:
- Given a required food field is empty, whitespace-only, invalid, too long, negative, or outside max limits
  When I save
  Then save is blocked and the affected field shows a specific Arabic error.
- Given optional nutrient fields are blank
  When I save
  Then they are stored as unknown/null, not forced to zero unless I entered zero.

Decision needed:
Max values, accepted characters, Arabic messages.

### QA-US-NEW-007 - Split Food List States

Feature: Food browsing/search  
Type: UX/UI / State Handling  
Priority: P1  
Current status: Weak  
Evidence: `US-FOOD-HAPPY-001`, `US-FOOD-HAPPY-002`, `FoodsPage.tsx`

User story:
As a user, I want the Foods page to distinguish loading, empty catalog, no search results, and connection errors, so that I know what action to take.

Acceptance criteria:
- Given foods are loading
  When the page waits for the API
  Then a loading state is shown.
- Given no foods exist
  When the load succeeds
  Then an empty catalog state with an add-food action is shown.
- Given a search has no matches
  When the load succeeds
  Then a no-results state appears and does not imply the catalog is empty.
- Given the API fails
  When fresh foods cannot load
  Then a connection error is shown.

### QA-US-NEW-008 - Decide Gram-Based Diary Logging Contract

Feature: Gram-based diary logging  
Type: Decision Needed / Calculation  
Priority: P0 if in v1, P2 if future  
Current status: Not testable  
Evidence: `US-DIARY-GRAM-001`, `serving_grams`

User story:
As a user, I want to log foods by grams when serving weight exists, so that weighed foods produce accurate totals.

Acceptance criteria:
- Given a food has `serving_grams`
  When I enter grams
  Then totals are calculated as `grams / serving_grams * per-serving values`.
- Given a food lacks `serving_grams`
  When I choose gram mode
  Then gram entry is disabled or a clear Arabic error is shown.

Decision needed:
API payload shape and whether v1 supports grams or keeps serving-only logging.

### QA-US-NEW-009 - Define Diary Date Policy

Feature: Diary entry date  
Type: Decision Needed / Edge  
Priority: P1  
Current status: Missing  
Evidence: `docs/ba/08_NEGATIVE_SCENARIOS.md`, `DiaryEntryCreate`

User story:
As a user, I want diary date rules to be clear, so that I know whether future or very old entries are allowed.

Acceptance criteria:
- Given a date is outside the allowed range
  When I submit a diary entry
  Then the entry is rejected with a field-level Arabic error.

Decision needed:
Allow or block future dates, and define any oldest allowed date.

### QA-US-NEW-010 - Decide Diary Edit Scope

Feature: Diary update API  
Type: Decision Needed / CRUD  
Priority: P1  
Current status: Missing  
Evidence: `backend/app/api/routes/diary.py`, no edit UI

User story:
As a user, I want to know whether diary entries can be edited, so that mistakes can be corrected consistently.

Acceptance criteria:
- Given edit is in v1
  When I edit date, food, or quantity
  Then the entry updates only after a successful API response.
- Given edit is not in v1
  When requirements are implemented
  Then the backend update API is hidden from the UI scope or documented as API-only.

### QA-US-NEW-011 - Define Profile Birth-Date and Metric Bounds

Feature: Profile validation  
Type: Field Validation / Edge  
Priority: P1  
Current status: Weak  
Evidence: `ProfileUpsert`, BA open questions

User story:
As a user, I want impossible profile values rejected, so that target calculations remain realistic.

Acceptance criteria:
- Given a future birth date or unrealistic height/weight is entered
  When I save or preview targets
  Then the affected field shows a clear Arabic error and targets are not persisted from invalid input.

Decision needed:
Age, height, and weight limits.

### QA-US-NEW-012 - Handle Authorization Errors in UI

Feature: Single-user token auth  
Type: Permission / Error Handling  
Priority: P0  
Current status: Missing UI behavior  
Evidence: `require_single_user`, protected routes

User story:
As a user, I want a clear message when API access is unauthorized, so that I know the app cannot load or save personal data.

Acceptance criteria:
- Given the API returns 401
  When a protected page loads or writes
  Then the UI shows an authorization error and does not show stale or queued data as saved.

### QA-US-NEW-013 - Constrain Service Worker Scope for v1

Feature: Optional installable shell  
Type: PWA / Scope Control  
Priority: P0  
Current status: Weak / Decision Needed  
Evidence: `service-worker.js`, `US-SHELL-HAPPY-001`

User story:
As the product owner, I want the installable shell to avoid offline personal data behavior in v1, so that users do not mistake cached data for current data.

Acceptance criteria:
- Given v1 is online-only
  When the service worker is present
  Then it does not make personal nutrition API data appear current when the backend is unreachable.

Decision needed:
Remove service worker or restrict to static shell assets only.

### QA-US-NEW-014 - Make Field Errors Accessible

Feature: Accessibility  
Type: Accessibility / Field Validation  
Priority: P1  
Current status: Weak  
Evidence: `US-A11Y-001`, form components

User story:
As a screen-reader or keyboard user, I want validation errors announced and associated with fields, so that I can correct them efficiently.

Acceptance criteria:
- Given a field validation error occurs
  When the form is submitted
  Then the invalid field has `aria-invalid`, error text is connected with `aria-describedby`, and focus moves to the first invalid field.

### QA-US-NEW-015 - Define Mobile Safe-Area and Keyboard Behavior

Feature: Mobile UX  
Type: Mobile / UX  
Priority: P1  
Current status: Weak  
Evidence: `US-MOBILE-001`, `globals.css`

User story:
As a mobile user, I want forms and fixed messages to avoid the keyboard and safe areas, so that I can complete daily tracking without hidden controls.

Acceptance criteria:
- Given the app runs on a small mobile viewport
  When a form input is focused
  Then submit actions and error messages remain reachable without horizontal scrolling.

### QA-US-NEW-016 - Add Direct API CRUD Test Story

Feature: Test coverage  
Type: Testability  
Priority: P1  
Current status: Weak  
Evidence: `US-QA-001`, missing tests

User story:
As QA, I want direct API tests for Profile, Food, and Diary CRUD, so that backend behavior is verified independently of the UI.

Acceptance criteria:
- Given API tests run
  When Profile, Food, and Diary CRUD operations are exercised
  Then success, validation, 401, 404, and delete/archive cases are verified.

### QA-US-NEW-017 - Add Online Network Error Tests

Feature: Online-only network errors  
Type: Testability / Negative  
Priority: P1  
Current status: Missing  
Evidence: `PD-001`, no visible network-error tests

User story:
As QA, I want tests for API unreachable and server error states, so that v1 never silently queues or locally saves failed writes.

Acceptance criteria:
- Given the API is unreachable or returns 5xx
  When read/write flows execute
  Then errors are shown and no offline mutation is created.

### QA-US-NEW-018 - Resolve Multi-Profile Scope

Feature: Multiple people/profiles  
Type: Decision Needed  
Priority: P1  
Current status: Missing/unclear  
Evidence: `F-015`, current single `Profile` model

User story:
As the product owner, I want the v1 profile scope decided, so that stories do not assume person-scoped diary data when the code supports only one profile.

Acceptance criteria:
- Given v1 remains single-profile
  When stories mention people/profiles
  Then multi-person behavior is moved to Future Scope.
- Given multi-profile is included in v1
  When requirements are updated
  Then Person CRUD, person_id diary scope, profile switcher, and migration stories are added.

