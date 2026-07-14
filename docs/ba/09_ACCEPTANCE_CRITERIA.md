# Acceptance Criteria

This file consolidates v1 Given/When/Then acceptance criteria after product decisions D-001 through D-023.

## App Shell, RTL, and Mobile

- Given the user opens `/`
  When the route is handled
  Then the user is redirected to `/diary`.
- Given the app shell renders
  When any page loads
  Then HTML language is Arabic and direction is RTL.
- Given viewport width is 360, 390, 430, 768, or desktop width
  When a main page renders
  Then content does not require horizontal scrolling for standard use.
- Given mixed Arabic/English food names display
  When viewed on supported widths
  Then text remains readable and does not overlap controls.
- Given a food name is long
  When it is displayed in a food list or card
  Then it is limited to two lines with ellipsis and does not cause horizontal scrolling or overlap action controls.
- Given a food name is long
  When it is displayed in a food details or edit view
  Then the full food name is readable in RTL layout.

## Health and Configuration

- Given the backend is running
  When `/health` is requested
  Then the API returns a successful health response.
- Given frontend API calls are made
  When environment configuration is loaded
  Then calls use the configured API base URL and bearer token.
- Given repository contents are reviewed
  When source files are committed
  Then real secrets, private tokens, and `.env` files are not included.

## Auth

- Given a protected API request includes the configured bearer token
  When the request is processed
  Then the API executes the route handler.
- Given a protected API request has no token or an invalid token
  When the request is processed
  Then the API returns 401.
- Given the UI receives 401
  When a page or write action fails
  Then `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` is shown.

## Optional Installable Shell and Service Worker

- Given the install prompt is available
  When the user installs the app
  Then the app can open as a standalone shell.
- Given a service worker exists in v1
  When it caches assets
  Then it caches static shell assets only.
- Given personal nutrition API data is requested
  When the backend is unreachable
  Then the service worker does not provide stale personal data as authoritative current data.
- Given existing offline page, offline metadata, or cached-read fallback behavior exists in code
  When v1 requirements are evaluated
  Then that behavior is marked as Future Scope or implementation alignment, not a v1 acceptance requirement.

## Profile

- Given v1 scope is evaluated
  When Profile, Foods, Diary, and targets are used
  Then they are scoped to one personal user and one Profile model.
- Given older planning references multiple people/profiles
  When v1 requirements are used for planning
  Then multi-profile support and profile switching are treated as Future Scope.
- Given the user needs to correct profile data
  When valid profile edits are saved and the API succeeds
  Then the existing Profile is updated rather than reset or deleted.
- Given profile reset/delete is requested
  When v1 scope is evaluated
  Then reset/delete is out of scope for v1.
- Given no profile exists
  When the Profile page loads successfully
  Then `ط£ط¯ط®ظ„ ط¨ظٹط§ظ†ط§طھظƒ ظ„ط­ط³ط§ط¨ ط§ظ„ط£ظ‡ط¯ط§ظپ ط§ظ„ظٹظˆظ…ظٹط©.` is shown and the profile form remains available.
- Given Profile load fails due to timeout/network
  When fresh profile data cannot load
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached personal profile data is not treated as current.
- Given valid profile fields within v1 ranges
  When the user saves and the API succeeds
  Then the profile is created or updated and targets can be displayed.
- Given profile save fails due to network/timeout/5xx
  When the user saves
  Then the profile is not saved locally, no mutation is queued, the same visible input remains in the form until the user edits it, resets it, retries successfully, or navigates away, and Arabic error copy is shown.
- Given profile save returns 422 with known field details
  When the user saves
  Then field-level errors are shown beside the affected fields.
- Given profile save returns 422 with unknown field or form-level details
  When the user saves
  Then `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown at form level.
- Given birth date is in the future
  When the user saves or previews
  Then save/preview is blocked with `طھط§ط±ظٹط® ط§ظ„ظ…ظٹظ„ط§ط¯ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† ظٹظƒظˆظ† ظپظٹ ط§ظ„ظ…ط³طھظ‚ط¨ظ„.`
- Given age is below 10
  When the user saves or previews
  Then save/preview is blocked with `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ† ظٹظƒظˆظ† 10 ط³ظ†ظˆط§طھ ط£ظˆ ط£ظƒط«ط±.`
- Given age is above 100
  When the user saves or previews
  Then save/preview is blocked with `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ„ط§ ظٹطھط¬ط§ظˆط² 100 ط³ظ†ط©.`

## Target Calculation

- Given valid sex, age, height, weight, activity level, goal, protein/kg, and fat percentage
  When targets are calculated
  Then BMR uses Mifflin-St Jeor, TDEE uses activity factor, target calories use goal factor, and macros are returned.
- Given valid profile inputs change
  When the preview calculation accepts the current valid input set
  Then target preview updates without requiring a save.
- Given profile inputs are invalid
  When preview would be calculated
  Then invalid fields are shown and the preview is not treated as reliable.
- Given carb calories are negative
  When targets are calculated
  Then `carb_g` is clamped to zero and `carb_clamped` is true.

## Current Food Page Acceptance Criteria - D-024/D-026

These criteria supersede older Food criteria that mention archive/inactive lifecycle, `is_active`, `archived_at`, Active/Archived filters, `serving_label`, or `serving_grams` as Food source-of-truth fields.

### Food Routes and Page Structure

- Given the user opens `/foods`
  When the Foods page loads
  Then the page shows browsing/search/list actions and does not show a large inline Add Food form.
- Given the user selects Add Food
  When navigation completes
  Then the route is `/foods/new`.
- Given the user opens `/foods/new`
  When the form loads
  Then the page shows grouped sections for Basic food information, Nutrition basis, Core nutrition values, Default unit, Optional nutrients, and Notes/data source.
- Given the user opens `/foods/new`
  When actions are displayed
  Then no delete action is available.
- Given the user opens `/foods/:id`
  When Food details load
  Then the full Food name and available Food data are shown.
- Given the user opens `/foods/:id/edit`
  When the edit page loads
  Then it reuses the Add Food structure in edit mode.

### Food List

- Given current catalog Foods exist
  When the user opens `/foods` on desktop
  Then the list shows Food name, Brand if available, Category if available, Nutrition basis, Default unit, Calories, Protein, Carbs, Fat, and View/Edit/Delete actions.
- Given current catalog Foods exist
  When the user opens `/foods` on mobile
  Then Foods are displayed as cards showing Food name, Nutrition basis, Default unit, Calories, Protein, Carbs, and Fat.
- Given optional micronutrients exist for a Food
  When the Food appears in the main list/card
  Then optional micronutrients are not shown in that main list/card.
- Given a Food has been deleted
  When the user opens the list, searches, or opens Diary food selection
  Then the deleted Food is absent.
- Given the Foods list is displayed
  When the user inspects filters and columns
  Then there is no Status column, Archived filter, or Active/Archived filter.
- Given a Food name is long or mixed Arabic/English
  When it appears in a list/card
  Then the name is clamped to two lines with ellipsis, remains readable in RTL, and does not cause horizontal scrolling or overlap actions.

### Food Search

- Given current catalog Foods match the search term
  When the user searches by name
  Then only matching current catalog Foods are displayed.
- Given a search term has leading or trailing spaces
  When the search is applied
  Then the term is trimmed before the API search is requested.
- Given a matching Food was permanently deleted earlier
  When the user searches for its name
  Then the deleted Food is not shown.
- Given no current catalog Foods match the search term
  When search finishes
  Then `لا توجد نتائج مطابقة للبحث.` is shown and the empty catalog message is not shown.
- Given the user clears the search term
  When the list reloads successfully
  Then the full current catalog list is shown.
- Given the Foods API is unreachable during search
  When fresh search data cannot load
  Then `تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.` is shown and cached personal Food data is not treated as current.
- Given search results render on mobile
  When the viewport is 360px, 390px, 430px, or 768px
  Then the search input, result cards, and actions remain usable without horizontal scrolling.
- Given search results contain mixed Arabic/English/numeric Food names
  When the page renders in RTL
  Then Food names remain readable and actions do not overlap text.

### Food Loading, Empty, No-Results, and Read-Failure States

- Given the Foods list request is pending
  When `/foods` loads
  Then `جاري تحميل الأطعمة.` is shown in a status region.
- Given the online API returns an empty current catalog
  When `/foods` loads successfully
  Then `لا توجد أطعمة بعد. أضف أول طعام للبدء.` is shown with an Add Food action that navigates to `/foods/new`.
- Given the current catalog has Foods but search returns no matches
  When search finishes
  Then `لا توجد نتائج مطابقة للبحث.` is shown and the empty catalog message is not shown.
- Given the Foods API fails due to timeout, network failure, or server unavailability
  When fresh list data cannot load
  Then `تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.` is shown with a retry action.
- Given the user retries after a failed list read
  When retry is selected
  Then the app requests fresh API data again and does not use cached personal Food data as source of truth.
- Given a state message renders on mobile
  When keyboard, bottom navigation, or safe area is present
  Then the message and primary action remain visible and tappable.
- Given state messages render in Arabic RTL
  When loading, empty, no-results, or error states appear
  Then text direction, icons, and actions remain readable and correctly aligned.

### Food Create and Edit

- Given the user enters valid required Food fields on `/foods/new`
  When the save API succeeds
  Then the Food is created and appears in the current catalog.
- Given the user edits valid fields on `/foods/:id/edit`
  When the save API succeeds
  Then the Food details and list reflect the updated values.
- Given the user opens `/foods/:id/edit`
  When Food detail data loads successfully
  Then the edit form is prefilled with the current Food values.
- Given the edit page loads
  When the form renders
  Then it uses the same grouped structure as Add Food.
- Given the Food was already used in Diary entries
  When Food edit succeeds
  Then existing Diary entries keep their original nutrition snapshots and totals.
- Given the Food was permanently deleted before edit submit
  When the user submits the edit
  Then the stale Food Arabic message is shown and no local update is saved.
- Given the edit API fails
  When the error is shown
  Then visible edited data remains in the form, nothing is saved locally, and no offline mutation is queued.
- Given the user cancels from edit before a successful save
  When the user returns to `/foods`
  Then unsaved changes are not persisted.
- Given the edit page is used on 360px, 390px, 430px, or 768px viewport
  When fields are edited
  Then the form remains usable without horizontal scrolling and the keyboard does not hide the primary save action.
- Given an edited Food name mixes Arabic, English, and numbers
  When the edit page renders in RTL
  Then the full Food name remains readable.
- Given optional nutrients are blank
  When all required fields are valid
  Then saving is allowed.
- Given optional nutrients are provided
  When any optional nutrient violates its min/max rule
  Then saving is blocked with the related Arabic field-level error.
- Given an optional nutrient value is blank
  When required Food fields are valid
  Then the blank optional nutrient does not block saving.
- Given an optional nutrient value is negative
  When the user submits the form
  Then saving is blocked with `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.` near the field.
- Given an optional nutrient value is above its D-026 maximum
  When the user submits the form
  Then saving is blocked with `القيمة الغذائية الإضافية أعلى من الحد المسموح.` near the field.
- Given `fiber_g` is greater than `carb_g`
  When the user submits the form
  Then saving is blocked with the Arabic fiber-greater-than-carbs message.
- Given `added_sugar_g` is greater than `sugar_g` and both are provided
  When the user submits the form
  Then saving is blocked with `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.` near added sugar.
- Given `saturated_fat_g` is greater than `fat_g`
  When the user submits the form
  Then saving is blocked with `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.` near saturated fat.
- Given `trans_fat_g` is greater than `fat_g`
  When the user submits the form
  Then saving is blocked with `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.` near trans fat.
- Given `saturated_fat_g + trans_fat_g` is greater than `fat_g` and all values are provided
  When the user submits the form
  Then saving is blocked with `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.` near the fat fields.
- Given the first invalid optional nutrient is inside a collapsed Optional nutrients section
  When validation fails
  Then the Optional nutrients section opens before focus moves to the first invalid optional nutrient field.
- Given a current catalog Food has the same normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`
  When the user submits a create/edit duplicate
  Then saving is blocked with the Arabic duplicate message.
- Given a matching Food was deleted earlier
  When the user creates the same Food again
  Then the deleted Food does not block creation.
- Given a save request is pending
  When the user clicks/taps save repeatedly
  Then exactly one API request is sent.
- Given the save API fails
  When the error is shown
  Then visible entered data remains in the form, nothing is saved locally, and no offline mutation is queued.

### Food Permanent Delete

- Given the user selects Delete for a Food
  When the confirmation dialog opens
  Then it shows the Food name and states deletion is permanent.
- Given the confirmation dialog is open
  When the user selects Cancel or presses Escape
  Then no delete request is sent and the Food remains visible.
- Given the user confirms deletion and the API succeeds
  When the operation completes
  Then the Food is permanently removed from the catalog and disappears from Foods list, search results, and future Diary food selection.
- Given the deleted Food was used in old Diary entries
  When the user views those entries after deletion
  Then the entries remain readable and accurate using snapshot data.
- Given the delete API fails
  When the error is shown
  Then the Food remains visible, no local delete is queued, and retry is possible.
- Given a delete request is pending
  When the user confirms repeatedly
  Then exactly one delete request is sent.
- Given Food delete is implemented
  When the data model is inspected for v1 requirements
  Then `is_active`, `archived_at`, archive status, and restore behavior are not required.

### Diary Snapshot After Food Delete

- Given a Diary entry is created from a Food
  When the Food is later deleted
  Then the Diary entry still has Food name at logging time, nutrition basis at logging time, nutrition values at logging time, logged quantity, log mode, and calculated totals.
- Given the Food record no longer exists
  When an old Diary entry is displayed
  Then the UI does not depend on the Food record to show historical Food identity or totals.

## Legacy Food Catalog Read and Search

The legacy Food criteria below are retained for traceability only. If they conflict with D-024, D-025, or D-026, the current criteria above control v1 requirements.

## Food Catalog Read and Search

- Given current catalog foods exist
  When the Foods page loads successfully
  Then current foods are displayed by name order with nutrition basis, default unit, calories, and macros.
- Given a food is permanently deleted
  When the Foods list or search loads
  Then the deleted food is not shown.
- Given foods are loading
  When the API request is pending
  Then `ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ط§ظ„ط£ط·ط¹ظ…ط©.` is shown.
- Given no current catalog foods exist
  When the request succeeds
  Then `ظ„ط§ طھظˆط¬ط¯ ط£ط·ط¹ظ…ط© ط¨ط¹ط¯. ط£ط¶ظپ ط£ظˆظ„ ط·ط¹ط§ظ… ظ„ظ„ط¨ط¯ط،.` is shown.
- Given a search term has no current-catalog matches
  When search finishes
  Then `ظ„ط§ طھظˆط¬ط¯ ظ†طھط§ط¦ط¬ ظ…ط·ط§ط¨ظ‚ط© ظ„ظ„ط¨ط­ط«.` is shown.
- Given Foods API read fails due to timeout/network
  When the page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached Foods data is not treated as current.
- Given Food detail API read fails due to timeout/network
  When the details or edit view cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and edit submit is unavailable until fresh data loads.

## Food Create and Edit

- Given valid food fields and no current-catalog duplicate exists
  When the user saves a new food and the API succeeds
  Then the food is persisted with D-025 per-100g/per-100ml nutrition basis and default unit fields.
- Given optional nutrient fields are blank
  When the user saves
  Then blank optional values are stored as null/unknown.
- Given food create or edit API fails
  When the user saves
  Then no local food is created/updated, no mutation is queued, the same visible draft remains in the form until the user edits it, resets it, retries successfully, or navigates away, and Arabic error copy is shown.
- Given a current-catalog duplicate exists by normalized name, nutrition basis, default unit type, unit amount, and unit basis
  When the user creates or edits a matching food
  Then save is blocked with `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ…ظˆط¬ظˆط¯ ظ…ط³ط¨ظ‚ظ‹ط§ ط¨ظ†ظپط³ ط§ظ„ط­طµط©.`
- Given a matching food was previously deleted
  When the user creates a new matching food
  Then save is allowed.
- Given a food used in Diary is edited
  When the edit succeeds
  Then existing Diary entries keep their original snapshot values.

## Food Field Validation

- Given required text is empty or whitespace-only
  When the user saves
  Then save is blocked with `ظ‡ط°ط§ ط§ظ„ط­ظ‚ظ„ ظ…ط·ظ„ظˆط¨.`
- Given numeric input is invalid
  When the user saves
  Then save is blocked with `ط£ط¯ط®ظ„ ط±ظ‚ظ…ظ‹ط§ طµط­ظٹط­ظ‹ط§.`
- Given a numeric value is below its v1 minimum
  When the user saves
  Then save is blocked with `ط§ظ„ظ‚ظٹظ…ط© ط£ظ‚ظ„ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.`
- Given a numeric value is above its v1 maximum
  When the user saves
  Then save is blocked with `ط§ظ„ظ‚ظٹظ…ط© ط£ط¹ظ„ظ‰ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.`
- Given `fiber_g > carb_g`
  When the user saves a food
  Then save is blocked with `ط§ظ„ط£ظ„ظٹط§ظپ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† طھظƒظˆظ† ط£ظƒط¨ط± ظ…ظ† ط§ظ„ظƒط±ط¨ظˆظ‡ظٹط¯ط±ط§طھ.`
- Given `fiber_g` is blank
  When net carbs are calculated
  Then fiber is treated as zero.

## Food Permanent Delete and Stale Food Handling

- Given the user selects delete on a food
  When the confirmation dialog opens
  Then it shows the food name and explains that deletion is permanent.
- Given the user cancels or presses Escape
  When the dialog closes
  Then no food changes occur.
- Given the user confirms delete and the API succeeds
  When delete completes
  Then the food is permanently removed from the catalog and hidden from Foods list, search, and future Diary selection.
- Given delete API fails
  When the failure is handled
  Then the food remains visible in the catalog, no local delete is queued, and an Arabic error is shown.
- Given old Diary entries reference the deleted food
  When those entries are viewed
  Then nutrition snapshot values remain unchanged.
- Given a food is deleted after the user opens edit mode
  When the user submits the edit
  Then the edit is rejected with `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` and no local update is saved.
- Given a food is deleted after it is selected for Diary logging
  When the user submits the Diary entry
  Then the entry is not created and `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown.
- Given selected Food values change before Diary submit
  When the API accepts the entry
  Then the snapshot uses server-confirmed Food values from the successful API response.
- Given selected Food values change before Diary submit and the API rejects the stale submission
  When the rejection is handled
  Then `طھظ… طھط؛ظٹظٹط± ط¨ظٹط§ظ†ط§طھ ط§ظ„ط·ط¹ط§ظ… ظ‚ط¨ظ„ ط§ظ„ط­ظپط¸. ط­ط¯ظ‘ط« ط§ظ„ط¨ظٹط§ظ†ط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and no local entry is created.

## Diary Create by Servings

- Given current catalog Foods exist, selected date is today or past, and serving quantity is 0.01-50
  When the user submits `{ entry_date, food_id, log_mode: "servings", quantity }` and the API succeeds
  Then a Diary entry is created and daily/weekly totals refresh.
- Given serving quantity is invalid
  When the user submits
  Then save is blocked with a field-level Arabic error.

## Diary Create by Grams and Quantity Mode Contract

- Given selected current-catalog Food has nutrition basis/default-unit data that supports an unambiguous gram calculation and gram quantity is 1-5000
  When the user submits `{ entry_date, food_id, log_mode: "grams", quantity: <grams> }`
  Then the API calculates totals from the Food nutrition basis and stores the server-confirmed snapshot.
- Given selected Food cannot support an unambiguous gram calculation from its nutrition basis/default-unit data
  When gram mode is selected
  Then gram entry is disabled or `لا يمكن التسجيل بالجرام لهذا الطعام لأن بيانات الوحدة أو أساس القيم الغذائية غير مكتملة.` is shown.
- Given gram-mode entry is saved
  When the Diary entry is returned
  Then `nutrition_snapshot` includes food identity, nutrition basis, nutrition values at logging time, default-unit data used for calculation, `log_mode="grams"`, `logged_quantity`, and `calculated_totals`.
- Given serving-mode entry is saved
  When the Diary entry is returned
  Then `serving_multiplier = quantity`.
- Given gram-mode entry is saved
  When the Diary entry is returned
  Then this legacy criterion is superseded by D-025: current v1 recalculates totals from the original nutrition basis/default-unit snapshot data.
- Given day or weekly totals are displayed
  When Diary entries are aggregated
  Then aggregation uses `nutrition_snapshot.calculated_totals`, not current Food nutrition values.

## Diary Date, Edit, Delete, and Snapshot

- Given selected Diary date is future
  When the user creates or edits an entry
  Then save is blocked with `ظ„ط§ ظٹظ…ظƒظ† طھط³ط¬ظٹظ„ ظٹظˆظ…ظٹط§طھ ط¨طھط§ط±ظٹط® ظ…ط³طھظ‚ط¨ظ„ظٹ.`
- Given an entry was logged by servings
  When the user edits it
  Then only serving quantity can be changed within 0.01-50.
- Given an entry was logged by grams
  When the user edits it
  Then only gram quantity can be changed within 1-5000.
- Given the user edits an entry
  When the edit UI appears
  Then `log_mode`, food, entry date, and snapshot nutrition values are not editable.
- Given the user saves an edit
  When the API request is sent
  Then the payload is `{ quantity }` only.
- Given edit API fails
  When the user saves
  Then the existing entry remains unchanged, no mutation is queued, and the same visible edit value remains available for retry until the user edits it, resets it, retries successfully, or navigates away.
- Given the user selects delete on a Diary entry
  When the confirmation dialog opens
  Then it shows the food name and entry date.
- Given the Diary delete confirmation dialog is open
  When the user cancels or closes it
  Then no Diary entry changes.
- Given the user confirms Diary delete and the API succeeds
  When the response returns
  Then the entry is removed and daily and weekly totals refresh.
- Given Diary delete API fails
  When the failure is handled
  Then the entry remains visible, totals remain unchanged, and no local delete is queued.
- Given a Diary entry no longer exists before edit/delete completes
  When the API rejects the request
  Then `ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظٹظˆظ…ظٹط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and no local update/delete is applied.
- Given a Diary entry is created from a food
  When the food is edited or permanently deleted later
  Then Diary entry totals stay unchanged.

## Diary Day and Weekly Summary Reads

- Given entries exist for the selected day
  When the Diary day loads
  Then entries are listed with food name, mode/quantity, calories, and macros.
- Given no entries exist for the selected day
  When the Diary day loads
  Then `ظ„ط§ طھظˆط¬ط¯ ظˆط¬ط¨ط§طھ ظ…ط³ط¬ظ„ط© ظ„ظ‡ط°ط§ ط§ظ„ظٹظˆظ….` is shown.
- Given Diary day API read fails due to timeout/network
  When the page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached day totals are not treated as current.
- Given any selected date
  When weekly summary is requested
  Then the backend normalizes the range to Sunday through Saturday.
- Given Diary entries exist inside the week
  When the week is returned
  Then each day includes totals and the week includes weekly totals.
- Given weekly summary API read fails due to timeout/network
  When the page cannot load fresh data
  Then `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and cached weekly totals are not treated as current.

## Online Network and API Errors

- Given an API read fails because the backend is unreachable
  When the page loads
  Then the exact page-specific read failure message from `06_ERROR_MESSAGES.md` is shown and cached personal data is not treated as source of truth.
- Given an API write fails
  When Profile, Food, or Diary changes are submitted
  Then no local mutation is queued and no local data is marked as saved.
- Given invalid data is rejected by the backend with known field details
  When the response returns
  Then field-level errors are shown beside affected fields and invalid data is not saved locally or queued.
- Given invalid data is rejected by the backend with unknown field or form-level details
  When the response returns
  Then `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` is shown and invalid data is not saved locally or queued.
- Given 401, 404, 422, timeout/network, or 5xx occurs
  When the UI handles the response
  Then the exact Arabic message from `06_ERROR_MESSAGES.md` is used for that status and action/page.

## Duplicate Submit and Retry

- Given a Profile, Food, or Diary write request is pending
  When the user clicks or taps the same submit/confirm action again
  Then the UI sends exactly one API request and either disables the action or shows `ط§ظ„ط·ظ„ط¨ ظ‚ظٹط¯ ط§ظ„ظ…ط¹ط§ظ„ط¬ط©. ط§ظ†طھط¸ط± ط­طھظ‰ ظٹظƒطھظ…ظ„.`
- Given the pending write succeeds
  When the response returns
  Then the success state is shown once and the page reflects the successful API response.
- Given the pending write fails
  When the error is shown
  Then the form input remains visible, the action is re-enabled, and retry submits the current visible input without using an offline/local queue.
- Given a Food permanent-delete or Diary delete confirmation is pending
  When the user presses Confirm repeatedly
  Then only one delete request is sent.

## Future Scope: Offline and Sync

- Given v1 is implemented
  When offline cache, IndexedDB source-of-truth behavior, offline mutation queue, sync push/pull, pending sync, stale cache, conflict, or sync rejection behavior is requested
  Then the behavior is treated as Future Scope and excluded from v1 acceptance.
- Given existing code contains IndexedDB, sync endpoints, sync status UI, offline pages, service-worker API caching, or cached-read fallbacks
  When BA requirements are evaluated
  Then those items are documented as implementation alignment/Future Scope and do not override online-only v1 requirements.

## Accessibility

- Given an icon-only button exists
  When assistive technology reads the control
  Then the button has an accessible name.
- Given field validation error occurs
  When the form is submitted
  Then the error is displayed near the field, associated with the field through `aria-describedby`, the field has `aria-invalid=true`, and focus moves to the first invalid visible field.
- Given the first invalid field is inside a collapsed optional section
  When the form is submitted
  Then the section opens and focus moves to that invalid field.
- Given the Food permanent-delete or Diary delete confirmation dialog opens
  When used with keyboard
  Then the dialog has an accessible name and description, initial focus is on the safest action, Escape/cancel closes without changes, and focus returns to the triggering control or nearest safe action after close.
- Given loading or success status appears
  When it is shown
  Then it is announced through `role="status"` or `aria-live="polite"`.
- Given error or destructive status appears
  When it is shown
  Then it is announced through `role="alert"` or an equivalent assertive live region.

## QA Test Data

- Given QA prepares v1 regression data
  When test data is created
  Then it includes boundary Profile values, duplicate current-catalog foods, deleted-food snapshot cases, Foods with D-025 default-unit data, D-026 optional nutrient failures, serving Diary entries, gram Diary entries, stale Food/Diary cases, duplicate-submit cases, and network/API read/write failures.
