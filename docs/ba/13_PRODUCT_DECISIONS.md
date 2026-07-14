# Product Decisions

This file is the v1 product decision record for myNutri. It applies to the BA package under `docs/ba/` and supersedes unresolved decision questions from the QA audits under `docs/qa/user-story-audit/` and `docs/qa/user-story-audit-v2/`.

Product scope:
- myNutri v1 is an online-only personal nutrition system.
- Offline-first behavior is out of scope for v1.
- Mobile-first responsive web, Arabic RTL, accessibility, validation, and network/API error handling are required.

## D-001 - IndexedDB and Sync Behavior

Question: Should v1 support offline writes, local mutation queues, IndexedDB source-of-truth behavior, or sync push/pull?

Final decision:
Remove offline write behavior from v1.

Rationale:
For a personal-use v1, correctness and simple recovery are more important than offline complexity. A failed write must not look saved.

Impacted features:
- Online API writes.
- Profile, Food, and Diary create/update/delete flows.
- Future offline/sync scope.

Impacted user stories:
- `US-PROFILE-HAPPY-001`
- `US-FOOD-CRUD-001`
- `US-FOOD-CRUD-002`
- `US-FOOD-CRUD-003`
- `US-DIARY-CRUD-001`
- `US-DIARY-EDIT-001`
- `US-DIARY-CRUD-002`
- `US-NETWORK-WRITE-001`
- `US-FUTURE-OFFLINE-001`

Implementation impact:
- Profile, Food, and Diary writes succeed only after a successful API response.
- Failed writes are not queued.
- Failed writes are not saved locally.
- UI must not show "saved locally" or "will sync later" messages.
- IndexedDB must not be treated as a source of truth for personal nutrition data.
- Sync/offline code should be removed, disabled, hidden, or moved to Future Scope.

QA impact:
- Test API failure paths for no local mutation, no queued mutation, preserved input in the same form state until the user changes it, resets it, or navigates away, and visible error feedback.
- Existing sync tests are Future Scope evidence, not v1 acceptance.

Remaining risks:
- Current code still contains IndexedDB, sync queue, sync status UI, and `/sync` route behavior. This is an implementation alignment item, not a v1 requirement.

## D-002 - Service Worker Scope

Question: Should the v1 service worker support offline data behavior?

Final decision:
v1 may keep a simple installable shell only.

Rationale:
Installability is useful on mobile, but cached personal nutrition data must not appear authoritative when the API is unreachable.

Impacted features:
- Optional installable shell.
- Online API reads.
- Network/API error handling.

Impacted user stories:
- `US-SHELL-HAPPY-001`
- `US-SHELL-SCOPE-001`
- `US-NETWORK-READ-001`

Implementation impact:
- Service worker may cache static shell assets only.
- Service worker must not cache personal nutrition API data.
- Service worker must not provide offline data behavior.
- If shell-only behavior is confusing, service worker removal is recommended for v1.

QA impact:
- Test that API data is not served as current when the backend is unreachable.
- Test installable shell separately from personal data loading.

Remaining risks:
- Current `frontend/public/service-worker.js` caches fetched GET responses; this conflicts with v1 unless restricted.

## D-003 - Food Delete Lifecycle

Question: Should v1 hard delete unused foods and archive used foods, or archive all foods?

Final decision:
Superseded by D-025. Food deletion in v1 is now permanent hard delete, not archive/inactive.

Rationale:
The earlier archive-only decision was reversed by the latest Food page product decision. v1 should stay simple and should not introduce active/archive state, archive filters, or inactive catalog records.

Impacted features:
- Food delete.
- Food archive/inactive lifecycle.
- Diary food selection.
- Diary snapshot integrity.

Impacted user stories:
- `US-FOOD-CRUD-003`
- `US-DIARY-INTEGRITY-001`
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`

Implementation impact:
- Do not implement D-003 archive behavior for v1.
- Use D-025 permanent hard delete behavior instead.
- Existing Diary entries remain unchanged through nutrition snapshots even after the Food record is deleted.

QA impact:
- Replace archive tests with hard-delete confirmation, catalog removal, future Diary selection removal, and snapshot integrity tests.

Remaining risks:
- Existing BA/test artifacts that mention archive/inactive must be updated or marked superseded by D-025.

## D-004 - Archive Field Design

Question: Which fields represent food archive state?

Final decision:
Superseded by D-025. v1 must not use archive state fields.

Rationale:
Food archive/inactive state is removed from v1. Permanent delete keeps the Food catalog simpler.

Impacted features:
- Food model.
- Food list filtering.
- Diary food selection.
- Duplicate checks.

Impacted user stories:
- `US-FOOD-HAPPY-001`
- `US-FOOD-CRUD-003`
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`

Implementation impact:
- Do not add `is_active`.
- Do not add `archived_at`.
- Do not show archived status or active/archived filters.

QA impact:
- Verify no archived status, no active/archived filters, and no archive fields are required for v1.

Remaining risks:
- Any implementation plan or test case that expects `is_active`/`archived_at` must be revised.

## D-005 - Archived Foods in Duplicate Checks

Question: Should archived foods block duplicate creation?

Final decision:
Superseded by D-025. Since v1 has no archive/inactive state, duplicate checks apply only to Foods currently present in the catalog. Deleted Foods do not block duplicate creation because they no longer exist.

Rationale:
A personal user should be able to create the same Food again after deleting it. The deleted record is no longer part of the catalog.

Impacted features:
- Food create.
- Food edit.
- Duplicate food validation.
- Food archive lifecycle.

Impacted user stories:
- `US-FOOD-VALIDATION-003`
- `US-FOOD-CRUD-001`
- `US-FOOD-CRUD-002`

Implementation impact:
- Duplicate checks query current catalog Foods only.
- Deleted Foods are absent and cannot block new Food creation.

QA impact:
- Test duplicate current catalog Food is blocked.
- Test the same Food can be created again after deletion.

Remaining risks:
- Requires duplicate normalization support without archive filters.

## D-006 - Exact Duplicate Key for v1

Question: What defines a duplicate food in v1?

Final decision:
A duplicate food is a current catalog Food with the same normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`.

Rationale:
The latest Food page decision makes nutrition values per 100g/per 100ml the source of truth and adds a default unit model. The duplicate key should match the fields that define how the Food is identified and usually logged.

Impacted features:
- Food create.
- Food edit.
- Duplicate food validation.

Impacted user stories:
- `US-FOOD-VALIDATION-003`

Implementation impact:
- Trim whitespace.
- Collapse repeated spaces.
- Compare English case-insensitively.
- Normalize Arabic by trimming and collapsing whitespace.
- Normalize `nutrition_basis`.
- Normalize `default_unit_type`.
- Compare `unit_amount` numerically.
- Normalize `unit_basis`.
- Do not include deleted Foods because they no longer exist.
- Do not include brand/category/notes/data source in the duplicate key.

QA impact:
- Test casing differences.
- Test repeated spaces.
- Test Arabic spacing.
- Test same name with different nutrition basis/default unit is allowed.
- Test exact current catalog duplicate is blocked.
- Test duplicate creation is allowed after the original Food is deleted.

Remaining risks:
- No current duplicate service or database constraint exists.

## D-007 - Gram-Based Diary Logging

Question: Is gram-based diary logging required in v1?

Final decision:
Gram-based diary logging is required in v1.

Rationale:
Weighed food logging is a core practical need for personal nutrition tracking.

Impacted features:
- Diary create.
- Food nutrition basis and default-unit data.
- Nutrition calculation.
- Diary snapshot.

Impacted user stories:
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`
- `US-DIARY-VALIDATION-001`
- `US-DIARY-INTEGRITY-001`

Implementation impact:
- User can log by servings or grams.
- Gram mode is calculated from the Food nutrition basis and logged gram amount.
- For Foods whose nutrition basis is `per_100g`, gram mode uses grams directly.
- Default-unit logging uses the Food default unit amount and unit basis.
- Diary snapshot freezes calculated nutrition at logging time.

QA impact:
- Test serving mode.
- Test gram mode with Food nutrition basis/default-unit data that can support gram calculation.
- Test gram mode disabled/error when the selected Food's nutrition basis/default-unit data cannot support an unambiguous gram calculation.
- Test snapshot totals do not change after Food edits or deletion.

Remaining risks:
- Current Diary UI/API supports serving quantity only.
- The latest Food model introduces per 100ml Foods; exact Diary API naming for direct ml logging is not yet separately defined. If Product wants direct ml logging, add a future decision for a `ml` or amount-based log mode.

## D-008 - Future Diary Dates

Question: Should future diary dates be allowed in v1?

Final decision:
Future diary dates are not allowed in v1.

Rationale:
v1 is a tracking app, not a future meal planner.

Impacted features:
- Diary create.
- Diary edit.
- Weekly summary.

Impacted user stories:
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`
- `US-DIARY-VALIDATION-001`
- `US-DIARY-EDIT-001`

Implementation impact:
- User can log for today or past dates only.
- Future dates show Arabic validation error.
- Future meal planning is out of scope for v1.

QA impact:
- Test today and past dates are allowed.
- Test tomorrow/future dates are blocked.

Remaining risks:
- Current code does not enforce a future-date rule.

## D-009 - Profile Birth Date and Age Bounds

Question: What birth-date and age bounds should v1 enforce?

Final decision:
Birth date cannot be in the future. Minimum age is 10 years. Maximum age is 100 years.

Rationale:
These limits keep target calculations realistic for a simple personal-use app.

Impacted features:
- Profile validation.
- Target preview.
- Target calculation.

Impacted user stories:
- `US-PROFILE-VALIDATION-001`
- `US-TARGET-HAPPY-001`

Implementation impact:
- Reject future birth dates.
- Reject users younger than 10 or older than 100.
- Apply to save and target preview.

QA impact:
- Test exact age boundaries.
- Test future date.
- Test preview does not calculate from invalid birth date.

Remaining risks:
- Current backend schema accepts any valid date.

## D-010 - Diary Entry Edit UI Scope

Question: What diary edit behavior is in v1?

Final decision:
Include minimal Diary edit in v1.

Rationale:
Quantity mistakes are common; changing the food/date/snapshot adds more complexity and risk.

Impacted features:
- Diary edit.
- Diary snapshot.
- Diary totals.

Impacted user stories:
- `US-DIARY-EDIT-001`
- `US-DIARY-INTEGRITY-001`

Implementation impact:
- User can edit quantity only.
- User edits the mode-specific quantity only: servings or grams.
- User cannot change food after entry creation.
- User cannot change entry date.
- User cannot manually edit nutrition snapshot.

QA impact:
- Test quantity edit refreshes totals.
- Test food/date/snapshot are not editable.
- Test failed edit is not saved or queued.

Remaining risks:
- Backend currently supports editing date/food/quantity; UI does not expose edit.

## D-011 - Arabic Validation Messages

Question: Are exact Arabic validation and error messages required before implementation?

Final decision:
Arabic validation messages are required before implementation.

Rationale:
The product is Arabic-first and QA needs exact expected messages.

Impacted features:
- Profile validation.
- Food validation.
- Diary validation.
- Network/API errors.
- Delete confirmation.
- Accessibility.

Impacted user stories:
- `US-PROFILE-VALIDATION-001`
- `US-FOOD-VALIDATION-001`
- `US-FOOD-VALIDATION-002`
- `US-FOOD-VALIDATION-003`
- `US-DIARY-VALIDATION-001`
- `US-NETWORK-READ-001`
- `US-NETWORK-WRITE-001`
- `US-ERROR-MAPPING-001`
- `US-A11Y-001`

Implementation impact:
- Required field: `ظ‡ط°ط§ ط§ظ„ط­ظ‚ظ„ ظ…ط·ظ„ظˆط¨.`
- Invalid number: `ط£ط¯ط®ظ„ ط±ظ‚ظ…ظ‹ط§ طµط­ظٹط­ظ‹ط§.`
- Below minimum: `ط§ظ„ظ‚ظٹظ…ط© ط£ظ‚ظ„ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.`
- Above maximum: `ط§ظ„ظ‚ظٹظ…ط© ط£ط¹ظ„ظ‰ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.`
- Duplicate food: `هذا الطعام موجود مسبقًا بنفس الوحدة.`
- Fiber greater than carbs: `ط§ظ„ط£ظ„ظٹط§ظپ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† طھظƒظˆظ† ط£ظƒط¨ط± ظ…ظ† ط§ظ„ظƒط±ط¨ظˆظ‡ظٹط¯ط±ط§طھ.`
- Gram mode unavailable: `لا يمكن التسجيل بالجرام لهذا الطعام لأن بيانات الوحدة أو أساس القيم الغذائية غير مكتملة.`
- Future diary date: `ظ„ط§ ظٹظ…ظƒظ† طھط³ط¬ظٹظ„ ظٹظˆظ…ظٹط§طھ ط¨طھط§ط±ظٹط® ظ…ط³طھظ‚ط¨ظ„ظٹ.`
- Network/API failure: `طھط¹ط°ط± ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ط®ط§ط¯ظ…. ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ.`
- Unauthorized access: `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.`
- Server error: `ط­ط¯ط« ط®ط·ط£ ظپظٹ ط§ظ„ط®ط§ط¯ظ…. ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Food delete confirmation: `سيتم حذف {food_name} نهائيًا من كتالوج الأطعمة. ستبقى اليوميات السابقة كما هي لأنها تستخدم نسخة غذائية محفوظة.`

QA impact:
- Field-level and form-level tests must assert exact Arabic copy.
- Accessibility tests must verify messages are associated with fields or announced.

Remaining risks:
- Current UI mostly relies on browser/backend defaults and general notes.

## D-012 - Practical Max Values

Question: What practical v1 ranges should validation enforce?

Final decision:
Use the v1 ranges listed below.

Rationale:
Practical ranges prevent unrealistic data and database precision failures while keeping the app simple.

Impacted features:
- Profile validation.
- Food validation.
- Diary validation.
- Target preview.

Impacted user stories:
- `US-PROFILE-VALIDATION-001`
- `US-FOOD-VALIDATION-001`
- `US-DIARY-VALIDATION-001`
- `US-DIARY-GRAM-001`
- `US-DIARY-EDIT-001`

Implementation impact:
- Profile height: 100-250 cm.
- Profile weight: 20-300 kg.
- Protein per kg: 1.0-3.0.
- Fat percentage: 15%-40%.
- Food calories per 100g/per 100ml: 0-3000.
- Protein: 0-300 g.
- Carbs: 0-500 g.
- Fat: 0-300 g.
- Fiber: superseded by D-026 optional nutrient range, 0-100 g.
- Sugar: superseded by D-026 optional nutrient range, 0-100 g.
- Sodium: superseded by D-026 optional nutrient range, 0-50000 mg.
- Cholesterol: superseded by D-026 optional nutrient range, 0-2000 mg.
- Unit amount: 1-2000 g/ml according to `unit_basis`.
- Diary serving quantity: 0.01-50.
- Diary gram quantity: 1-5000 g.

QA impact:
- Boundary tests for min, max, below min, and above max.

Remaining risks:
- Current schemas use looser ranges.

## D-013 - API Error Mapping

Question: How should v1 handle API errors?

Final decision:
Use shared online-only API error behavior.

Rationale:
The same error class should lead to predictable UI behavior across Profile, Foods, and Diary.

Impacted features:
- Online API reads.
- Online API writes.
- Auth.
- Validation.

Impacted user stories:
- `US-NETWORK-READ-001`
- `US-NETWORK-WRITE-001`
- `US-ERROR-MAPPING-001`
- `US-AUTH-PERM-001`

Implementation impact:
- 401 Unauthorized: show access/session error.
- 404 Not Found: show item not found or refresh-required message.
- 422 Validation Error: show field-level errors for known fields; if the API returns an unknown field or form-level validation error, show the form-level 422 message from `06_ERROR_MESSAGES.md`.
- Timeout / Network Error: show connection error and do not save locally.
- 5xx Server Error: show server error and ask user to try again.
- Failed writes preserve the user's visible input in the same form state until the user changes it, resets it, or navigates away.

QA impact:
- API and UI tests for 401, 404, 422, timeout/network, and 5xx.
- Verify no local save or queue on failed writes.

Remaining risks:
- Current UI has broad mutation errors and local queue fallback.

## D-021 - Diary Entry Quantity Mode Contract

Question: What exact API and storage contract should v1 use for serving/default-unit and gram-based Diary entries?

Final decision:
Use one mode-specific `quantity` field with an explicit `log_mode`.

Rationale:
This keeps the v1 Diary API simple while making it unambiguous whether the submitted quantity is default units/servings or grams. D-025 updates the Food source of truth to per 100g/per 100ml plus default-unit fields, so Diary calculations must use the Food nutrition basis and snapshot the calculated totals.

Impacted features:
- Diary create by default unit/servings.
- Diary create by grams.
- Diary quantity edit.
- Diary snapshot integrity.
- Weekly/day aggregation.
- Food deletion snapshot safety.

Impacted user stories:
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`
- `US-DIARY-GRAM-CONTRACT-001`
- `US-DIARY-EDIT-001`
- `US-DIARY-INTEGRITY-001`

Implementation impact:
- Diary create request payload is `{ entry_date, food_id, log_mode, quantity }`.
- `log_mode` is required and allowed values are `servings` and `grams`.
- If `log_mode="servings"`, `quantity` means count of the Food default unit and must be 0.01-50.
- If `log_mode="grams"`, `quantity` means grams and must be 1-5000.
- Gram totals are calculated from Food nutrition values and `nutrition_basis`. For `per_100g`, multiplier is `quantity / 100`.
- Default-unit/serving totals use `quantity * unit_amount` converted against `nutrition_basis` and `unit_basis`.
- If a Food uses `per_100ml`, direct gram logging requires a clear implementation conversion decision before build; until then, gram mode should be enabled only where the Food's basis/unit data can produce an unambiguous gram calculation.
- Do not add a separate persisted `grams` field in v1. The UI gram input maps to `quantity` when `log_mode="grams"`.
- Persisted Diary entries expose `log_mode`, `quantity`, `entry_date`, `food_id`, `nutrition_snapshot`, and computed totals.
- `nutrition_snapshot` stores Food name at logging time, nutrition basis at logging time, nutrition values at logging time, `log_mode`, logged quantity, default unit data used for the calculation, and calculated totals.
- Calculated totals are rounded to two decimals.
- Diary totals and weekly summaries use `nutrition_snapshot.calculated_totals`, not the current Food row.
- Diary edit request payload is `{ quantity }` only.
- Diary edit keeps `log_mode`, `food_id`, `entry_date`, nutrition basis, Food identity, and snapshot nutrition values immutable.
- When editing a gram-mode entry, the new `quantity` is grams and recalculates only calculated totals from the original snapshot data.

QA impact:
- Test serving/default-unit create payload and gram create payload separately.
- Test gram mode is blocked or errors when Food basis/unit data cannot support an unambiguous gram calculation.
- Test edit preserves `log_mode`, Food identity, entry date, nutrition basis, and snapshot nutrition values.
- Test day and weekly totals use snapshot calculated totals after Food edits or deletion.

Remaining risks:
- Current code does not expose gram-mode Diary API/UI and may need model/schema/API alignment.
- Product may need a future decision for direct ml logging if `per_100ml` Foods are common.
## D-022 - Exact Arabic Read-Failure Copy

Question: What exact Arabic copy should v1 show when online API reads fail?

Final decision:
Use page-specific read-failure messages and do not reuse write-failure copy for read failures.

Rationale:
Read failures do not save data, so the user needs a clear loading/currentness message rather than a save failure message.

Impacted features:
- Profile load.
- Foods list load.
- Food detail load.
- Diary day load.
- Weekly summary load.
- General online API reads.

Impacted user stories:
- `US-NETWORK-READ-001`
- `US-NETWORK-READ-COPY-001`
- `US-ERROR-MAPPING-001`
- `US-PROFILE-HAPPY-001`
- `US-FOOD-HAPPY-001`
- `US-FOOD-HAPPY-003`
- `US-DIARY-HAPPY-001`
- `US-DIARY-HAPPY-002`

Implementation impact:
- General read/network failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Profile load failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Foods list load failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Food detail load failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Diary day load failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Weekly summary load failure: `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.`
- Read failures must not display `ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ` because no write was attempted.
- Cached personal nutrition data must not be displayed as current source-of-truth data when fresh API data cannot load.

QA impact:
- Test each page-specific read failure message.
- Test cached/offline fallback does not hide the read failure.

Remaining risks:
- Current UI may fall back to cached IndexedDB data on read failure and needs implementation alignment.

## D-023 - Stale Items, Duplicate Submit, Retry, and Minimum Accessibility Behavior

Question: How should v1 handle stale records, repeated submits, retries, and minimum accessibility behavior?

Final decision:
Use conservative online-only submit handling and explicit stale-record messages.

Rationale:
The personal-use v1 should prevent accidental duplicate writes and avoid pretending stale or locally queued data has been saved.

Impacted features:
- Profile, Food, and Diary writes.
- Food edit/delete and Diary logging.
- Diary edit/delete.
- Error handling.
- Accessibility.

Impacted user stories:
- `US-FOOD-EDGE-001`
- `US-UX-STATUS-001`
- `US-NETWORK-WRITE-001`
- `US-ERROR-MAPPING-001`
- `US-A11Y-001`
- `US-DIARY-EDIT-001`
- `US-DIARY-CRUD-002`

Implementation impact:
- While a write request is pending, the submit/confirm action is disabled and repeated clicks/taps send exactly one API request.
- If a request fails, the user's visible form input remains unchanged until the user edits it, resets it, retries successfully, or navigates away.
- Retry after failure resubmits the same currently visible input; no offline/local mutation is created.
- If a Food is deleted before edit/delete/log submit completes, show `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` and do not save locally.
- If a Food changes before Diary submit, the backend must validate the selected current server Food at submit time; the snapshot uses the server-confirmed Food values returned by the successful API response.
- If a diary entry no longer exists before edit/delete completes, show `ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظٹظˆظ…ظٹط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` and do not locally update/delete it.
- On submit validation failure, focus moves to the first invalid visible field.
- If the first invalid field is inside a collapsed optional section, the section opens before focus moves to the invalid field.
- Async success/loading messages render in a `role="status"` or `aria-live="polite"` region.
- Error/destructive messages render in `role="alert"` or an equivalent assertive live region.
- Confirmation dialogs have an accessible name and description, place initial focus on the safest action, close on Cancel or Escape without changes, and return focus to the triggering control or nearest safe action.

QA impact:
- Test slow API duplicate-submit prevention.
- Test retry after network/API failure.
- Test stale Food and stale Diary record failures.
- Test focus management, live-region announcements, and keyboard dialog behavior.

Remaining risks:
- Current UI likely needs alignment for duplicate-submit, stale-record, and accessibility behaviors.

## D-014 - Delete Confirmation Pattern

Question: What delete confirmation pattern should v1 use for Food delete?

Final decision:
Superseded in part by D-025. Use a confirmation dialog for permanent Food delete.

Rationale:
A dialog is required because v1 delete permanently removes the Food from the catalog.

Impacted features:
- Food delete.
- Accessibility.
- Mobile UX.

Impacted user stories:
- `US-FOOD-CRUD-003`
- `US-A11Y-001`
- `US-MOBILE-001`

Implementation impact:
- Dialog shows the food name.
- Dialog clearly states deletion is permanent.
- Cancel makes no changes.
- Confirm permanently deletes the Food from the catalog.
- Dialog is keyboard accessible.
- Focus returns to a safe place after closing.
- No typing food name required in v1.

QA impact:
- Test dialog open, cancel, confirm, keyboard use, focus management, and mobile readability.

Remaining risks:
- Current UI deletes immediately with no dialog.

## D-015 - Mobile Device and Browser Support Matrix

Question: Which mobile/desktop devices and viewport widths are required for v1 acceptance?

Final decision:
Use the v1 support matrix below.

Rationale:
Daily nutrition tracking is mobile-heavy, and the app is Arabic-first RTL.

Impacted features:
- App shell.
- Profile form.
- Foods list/form.
- Diary day/week views.
- Error and confirmation UI.

Impacted user stories:
- `US-APP-HAPPY-001`
- `US-MOBILE-001`
- `US-A11Y-001`
- `US-FOOD-CRUD-003`

Implementation impact:
- Support iPhone Safari latest two iOS versions.
- Support Android Chrome latest two major versions.
- Support desktop Chrome latest.
- Support desktop Safari latest.
- Viewport checks: 360px, 390px, 430px, 768px, and desktop width.
- No horizontal scrolling.
- Buttons have usable touch targets.
- Keyboard must not hide critical form actions.
- Arabic RTL and mixed Arabic/English text remain readable.

QA impact:
- Visual/responsive checks for each viewport.
- Mobile form interaction tests.
- RTL/mixed text readability checks.

Remaining risks:
- Current responsive CSS exists but has not been verified against this matrix.

## D-016 - Multi-Profile Scope

Question: Is multi-person/profile support included in v1?

Final decision:
Multi-profile support is Future Scope. v1 uses the current single Profile model only.

Rationale:
The current implementation has one profile resource and no person/profile switcher. Keeping v1 single-profile preserves the personal-use scope and avoids adding profile ownership, switching, and person-scoped diary behavior before the core flows are stable.

Impacted features:
- Profile.
- Foods.
- Diary.
- Target calculation.
- Future people/profile switching.

Impacted user stories:
- `US-PROFILE-SCOPE-001`
- `US-PROFILE-HAPPY-001`
- `US-FOOD-HAPPY-001`
- `US-DIARY-HAPPY-001`

Implementation impact:
- Do not add People/Profile switching to v1 requirements.
- Do not require person-specific food catalogs in v1.
- Keep Profile, Foods, and Diary scoped to one personal user.
- Multi-profile data model changes remain Future Scope.

QA impact:
- Do not create v1 acceptance tests for switching people/profiles.
- Verify the app behavior is consistent for one personal profile only.
- Treat older multi-person planning notes as Future Scope unless explicitly reapproved.

Remaining risks:
- Older planning documents mention multiple people; implementation planning must follow this decision for v1.

## D-017 - Profile Reset/Delete

Question: Should v1 support deleting or resetting the Profile?

Final decision:
Profile reset/delete is out of scope for v1. v1 supports editing/updating the existing Profile only.

Rationale:
A personal user can correct profile data by editing the existing fields. Delete/reset adds recovery and empty-state complexity without being required for daily tracking.

Impacted features:
- Profile edit.
- Target calculation.
- Profile CRUD scope.

Impacted user stories:
- `US-PROFILE-SCOPE-001`
- `US-PROFILE-HAPPY-001`
- `US-PROFILE-VALIDATION-001`

Implementation impact:
- Do not add profile delete/reset UI or API behavior to v1 requirements.
- Existing profile correction is handled through edit/update.
- If profile delete/reset exists later, it must be separately specified.

QA impact:
- Do not create v1 delete/reset profile test cases.
- QA should verify profile edits can correct bad data within validation limits.

Remaining risks:
- Users who want to clear all profile data must edit fields manually in v1.

## D-018 - Diary Entry Delete Confirmation

Question: Should deleting a Diary entry require confirmation?

Final decision:
Deleting a Diary entry requires a simple confirmation in v1.

Rationale:
Diary deletion directly changes daily and weekly totals. A lightweight confirmation prevents accidental loss while keeping the flow practical.

Impacted features:
- Diary entry delete.
- Daily totals.
- Weekly totals.
- Online API writes.
- Accessibility.

Impacted user stories:
- `US-DIARY-CRUD-002`
- `US-NETWORK-WRITE-001`
- `US-A11Y-001`

Implementation impact:
- Confirmation shows the food name and date.
- Cancel makes no change.
- Confirm deletes the diary entry.
- Daily and weekly totals update after successful API response.
- No offline/local delete is allowed.

QA impact:
- Test confirmation content, cancel, confirm, keyboard use, API success, API failure, and totals refresh.
- Verify no local deletion or queued mutation occurs when the API fails.

Remaining risks:
- Current Diary delete behavior may need UI confirmation and online-only alignment.

## D-019 - Serving Grams Naming

Question: Should `serving_grams` be renamed in the API/code to match product wording?

Final decision:
Superseded by D-024 and D-025 for Food catalog modeling. v1 Food creation/editing must use nutrition values per 100g/per 100ml plus default-unit fields (`default_unit_type`, `unit_amount`, `unit_basis`). Do not treat `serving_grams` as the Food source-of-truth field for current v1 requirements.

Rationale:
The latest Food page decision replaced serving-based nutrition with per-100g/per-100ml nutrition plus a default unit. Keeping `serving_grams` as the primary Food model requirement would contradict D-025.

Impacted features:
- Food form.
- Food API schema.
- Diary gram logging.
- Field dictionary.

Impacted user stories:
- `US-FOOD-CRUD-001`
- `US-FOOD-CRUD-002`
- `US-DIARY-GRAM-001`

Implementation impact:
- Replace Food catalog requirements that depend on `serving_grams` with `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`.
- Current code may still contain `serving_grams`; treat that as an implementation alignment item, not the current v1 requirement.

QA impact:
- Remove v1 test expectations that require `serving_grams` in Food create/edit.
- Add tests for the D-024/D-025 default-unit model.

Remaining risks:
- Current code and older BA/test artifacts may still reference `serving_grams`; update them before final implementation planning/test execution.
## D-020 - Long Food Name Display

Question: How should long food names behave in lists/cards and detail/edit views?

Final decision:
Long food names must remain readable without breaking mobile layout.

Rationale:
Food names can contain long Arabic, English, or mixed text. List views need compact predictable cards, while detail/edit views should show the full value.

Impacted features:
- Food list/cards.
- Food details.
- Food edit.
- Mobile and RTL layout.
- Accessibility/visual QA.

Impacted user stories:
- `US-FOOD-HAPPY-001`
- `US-FOOD-HAPPY-003`
- `US-MOBILE-001`

Implementation impact:
- In food lists/cards, show up to two lines then truncate with ellipsis.
- In food details/edit views, show the full food name.
- Mixed Arabic/English names must remain readable in RTL layout.
- Long names must not cause horizontal scrolling or overlap actions.

QA impact:
- Visual QA must include long Arabic, long English, and mixed Arabic/English food names at required viewport widths.
- Verify action buttons remain reachable and visible.

Remaining risks:
- Current UI may not enforce two-line truncation consistently.

## D-024 - Add Food as Standalone Page

Question: Should Food creation happen inline on the Foods list, or on a dedicated page?

Final decision:
Food creation must be a dedicated standalone page in v1.

Rationale:
The Food form has enough required fields, optional nutrients, default-unit data, validation, and mobile constraints that an inline form on the list page would be cramped and error-prone.

Impacted features:
- Foods list.
- Add Food.
- Food details.
- Food edit.
- Mobile Food UX.
- Accessibility.

Impacted user stories:
- `US-FOOD-NAV-001`
- `US-FOOD-CRUD-001`
- `US-FOOD-CRUD-002`
- `US-FOOD-HAPPY-001`
- `US-FOOD-HAPPY-003`
- `US-MOBILE-001`
- `US-A11Y-001`

Implementation impact:
- Foods list route: `/foods`.
- Add Food route: `/foods/new`.
- Food details route: `/foods/:id`.
- Edit Food route: `/foods/:id/edit`.
- The Foods list page must not contain a large inline Add Food form.
- Add Food must be a comfortable mobile-first page.
- Edit Food should reuse the Add Food structure in edit mode.
- Add Food must not show delete because the Food does not exist yet.
- Delete may appear in Food Details and Food Edit pages.

QA impact:
- Test route navigation between list, add, detail, and edit.
- Test Add Food has no delete action.
- Test Edit Food reuses the same field grouping.
- Test mobile keyboard and scroll behavior on the standalone Add Food page.

Remaining risks:
- Current UI uses a list-page form pattern and may need route/component restructuring.

## D-025 - Food Deletion Is Permanent Hard Delete in v1

Question: Should v1 archive/inactivate foods or permanently delete them from the catalog?

Final decision:
Food deletion in myNutri v1 is permanent hard delete, not archive/inactive.

Rationale:
For a personal-use v1, permanent deletion is simpler than archive state, status filtering, and inactive catalog lifecycle. Diary history remains safe because Diary entries must use frozen nutrition snapshots.

Impacted features:
- Food delete.
- Food list/search.
- Food details/edit.
- Diary food selection.
- Diary snapshot integrity.
- Duplicate Food handling.
- Data model and API contract.

Impacted user stories:
- `US-FOOD-CRUD-003`
- `US-FOOD-VALIDATION-003`
- `US-DIARY-INTEGRITY-001`
- `US-DIARY-CRUD-001`
- `US-DIARY-GRAM-001`
- `US-A11Y-001`

Implementation impact:
- Remove Food archive/inactive behavior from v1.
- Do not use `is_active`.
- Do not use `archived_at`.
- Do not show Archived status in the Foods page.
- Do not show Active/Archived filters.
- Delete Food must require confirmation.
- Confirmation dialog must show the Food name and clearly state deletion is permanent.
- Cancel makes no changes.
- Confirm permanently deletes the Food from the Food catalog after successful API response.
- Deleted Foods disappear from Foods list, Food search results, and future Diary food selection.
- Existing Diary entries remain unchanged because they use frozen nutrition snapshots.
- If the user wants the same Food again later, they must create it again as a new Food.

Food data model requirements:
- Nutrition values are stored per 100g or per 100ml.
- Serving-based nutrition is not the Food source of truth.
- Required core fields: `name`, `nutrition_basis`, `calories`, `protein_g`, `carb_g`, `fat_g`, `default_unit_type`, `unit_amount`, `unit_basis`.
- Optional basic fields: `brand`, `category`, `notes`, `data_source`.
- Allowed `nutrition_basis`: `per_100g`, `per_100ml`.
- Allowed `default_unit_type`: `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon`.
- Allowed `unit_basis`: `g`, `ml`.
- Default unit labels: English `Default unit`, Arabic `ط§ظ„ظˆط­ط¯ط© ط§ظ„ط§ظپطھط±ط§ط¶ظٹط©`.
- Unit amount labels: English `Unit amount`, Arabic `ظ…ظ‚ط¯ط§ط± ط§ظ„ظˆط­ط¯ط©`.
- Unit basis labels: English `Unit basis`, Arabic `ط£ط³ط§ط³ ط§ظ„ظˆط­ط¯ط©`.

Optional nutrients:
- Optional nutrients are supported but are not required.
- Optional nutrients are grouped in a collapsed section by default.
- Section label: English `Optional nutrients`, Arabic `ط§ظ„ظ‚ظٹظ… ط§ظ„ط؛ط°ط§ط¦ظٹط© ط§ظ„ط¥ط¶ط§ظپظٹط©`.
- Optional nutrients: `fiber_g`, `sugar_g`, `added_sugar_g`, `saturated_fat_g`, `trans_fat_g`, `sodium_mg`, `cholesterol_mg`, `potassium_mg`, `calcium_mg`, `iron_mg`, `magnesium_mg`, `zinc_mg`, `vitamin_d_mcg`, `vitamin_b12_mcg`, `vitamin_c_mg`, `vitamin_a_mcg`, `folate_mcg`, `vitamin_k_mcg`.
- Vitamin D is stored in mcg. IU may be display/helper text only in a later decision.

Food page structure:
- Add Food page sections: Basic food information, Nutrition basis, Core nutrition values, Default unit, Optional nutrients, Notes and data source.
- Optional nutrients are collapsed by default.
- Required fields are clearly marked.
- Save action is easy to reach on mobile.
- Back/cancel returns to Foods page without saving.
- Duplicate submit is prevented.
- Network/API failure preserves entered data and shows Arabic error.

Foods list requirements:
- Desktop columns: Food name, Brand if available, Category if available, Nutrition basis, Default unit, Calories, Protein, Carbs, Fat, Actions View/Edit/Delete.
- Mobile cards show Food name, Nutrition basis, Default unit, Calories, Protein, Carbs, and Fat.
- Do not show optional micronutrients in the main list/table.
- Do not include Status column, Archived filter, or Active/Archived filter.
- Long Food names show up to two lines with ellipsis in lists/cards and full name in details/edit.
- Mixed Arabic/English text remains readable in RTL layout.

Diary snapshot requirements:
- Diary entries must not depend on the Food record remaining available.
- Snapshot must preserve at minimum: Food name at logging time, nutrition basis at logging time, nutrition values at logging time, logged quantity, log mode, and calculated totals.
- If current implementation still depends on `food_id` for historical display, document it as an implementation alignment item.

Duplicate handling:
- Duplicate checks apply only to Foods currently in the catalog.
- Deleted Foods do not block duplicate creation.
- Duplicate key uses normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`.

QA impact:
- Replace archive/inactive tests with permanent-delete confirmation, catalog removal, future Diary selection removal, duplicate-after-delete, and snapshot-after-delete tests.
- Add tests for standalone Add/Edit routes, per-100g/per-100ml fields, default unit fields, optional nutrients, mobile cards, and accessibility.

Remaining risks:
- Current code and existing QA test cases may still reflect archive/inactive and serving-based assumptions.
- Database/API schema changes will be required later, but no migration is created by this decision record.

## D-026 - Optional Nutrient Validation Ranges

Question: What maximum values and cross-field rules should v1 enforce for optional Food nutrients?

Final decision:
Optional nutrients are optional in v1. Blank optional nutrient fields must not block saving. If an optional nutrient is provided, it must be numeric, greater than or equal to 0, and within the v1 maximum for the Food nutrition basis value, meaning per 100g or per 100ml.

Rationale:
Optional nutrients improve detail without making Food creation heavy. Practical max values and cross-field rules prevent impossible nutrition data while preserving the simple v1 Food form.

Impacted features:
- Add Food.
- Edit Food.
- Optional nutrients collapsed section.
- Food validation.
- Arabic field-level errors.
- QA test data and validation tests.

Impacted user stories:
- `US-FOOD-CRUD-001`
- `US-FOOD-CRUD-002`
- `US-FOOD-VALIDATION-001`
- `US-FOOD-VALIDATION-002`
- `US-FOOD-VALIDATION-004`
- `US-A11Y-001`

Implementation impact:
- Blank optional nutrients are stored as null/unknown and do not block saving.
- Entered zero is valid.
- Negative optional nutrient values are invalid.
- Above-maximum optional nutrient values are invalid.
- Optional nutrient errors are field-level and Arabic.
- If the first invalid optional nutrient is inside the collapsed optional section, the section opens before focus moves to that field.

Validation ranges per 100g/per 100ml:

| Nutrient | Field | Range |
|---|---|---|
| Fiber | `fiber_g` | 0-100 g |
| Sugar | `sugar_g` | 0-100 g |
| Added sugar | `added_sugar_g` | 0-100 g |
| Saturated fat | `saturated_fat_g` | 0-100 g |
| Trans fat | `trans_fat_g` | 0-100 g |
| Cholesterol | `cholesterol_mg` | 0-2000 mg |
| Sodium | `sodium_mg` | 0-50000 mg |
| Potassium | `potassium_mg` | 0-10000 mg |
| Calcium | `calcium_mg` | 0-5000 mg |
| Iron | `iron_mg` | 0-100 mg |
| Magnesium | `magnesium_mg` | 0-1000 mg |
| Zinc | `zinc_mg` | 0-100 mg |
| Vitamin D | `vitamin_d_mcg` | 0-250 mcg |
| Vitamin B12 | `vitamin_b12_mcg` | 0-1000 mcg |
| Vitamin C | `vitamin_c_mg` | 0-5000 mg |
| Vitamin A | `vitamin_a_mcg` | 0-3000 mcg |
| Folate | `folate_mcg` | 0-2000 mcg |
| Vitamin K | `vitamin_k_mcg` | 0-2000 mcg |

Cross-field rules:
- `fiber_g` must not exceed `carb_g`.
- `added_sugar_g` must not exceed `sugar_g` if both are provided.
- `saturated_fat_g` must not exceed `fat_g`.
- `trans_fat_g` must not exceed `fat_g`.
- `saturated_fat_g + trans_fat_g` must not exceed `fat_g` if all values are provided.

Sugar field mapping:
- `sugar_g` is total sugar for current v1 Food payloads and storage.
- `added_sugar_g` is added sugar for current v1 Food payloads and storage.
- Both fields are optional and measured per 100g or per 100ml according to `nutrition_basis`.
- Blank `sugar_g` does not block saving.
- Blank `added_sugar_g` does not block saving.
- If `added_sugar_g` is provided while `sugar_g` is blank, saving is allowed when `added_sugar_g` is otherwise valid.
- `added_sugar_g <= sugar_g` is enforced only when both values are provided.
- `total_sugars_g` is legacy/current-code naming and not the current v1 BA source-of-truth field.

Arabic error messages:
- Negative optional nutrient value: `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.`
- Optional nutrient above maximum: `القيمة الغذائية الإضافية أعلى من الحد المسموح.`
- Fiber greater than carbs: `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.`
- Added sugar greater than sugar: `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.`
- Saturated fat greater than fat: `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- Trans fat greater than fat: `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- Saturated fat plus trans fat greater than total fat: `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.`

QA impact:
- Add boundary tests for each optional nutrient minimum, maximum, above-maximum, and decimal values where relevant.
- Add cross-field validation tests for fiber/carbs, added sugar/sugar, saturated fat/fat, trans fat/fat, and saturated+trans fat/fat.
- Verify blank optional nutrients do not block create/edit.
- Verify Arabic field-level errors appear near the related fields and are accessible.

Remaining risks:
- Current code does not include all optional nutrient fields or D-026 cross-field validation.

## Future Scope Exclusions

The following remain out of scope for v1:
- Offline cache as source of truth.
- IndexedDB personal data source-of-truth behavior.
- Offline mutation queue.
- Sync push/pull.
- Pending sync states.
- Conflict handling.
- Stale cache behavior.
- Offline Profile/Food/Diary writes.
- Sync rejection handling.
- Future meal planning.
- Food archive/inactive lifecycle.
- Food Active/Archived status filters.
- Multi-person profiles and profile switching.
- Profile reset/delete.
