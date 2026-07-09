# Acceptance Criteria

This file provides consolidated Given/When/Then criteria for core myNutri behavior.

## App Shell

- Given the user opens `/`
  When the route is handled
  Then the user is redirected to `/diary`.
- Given the app shell renders
  When the page loads
  Then the HTML language is Arabic and direction is RTL.
- Given the user selects a navigation link
  When the link is activated
  Then the corresponding route opens.

## Auth

- Given a protected API request includes the configured bearer token
  When the request is processed
  Then the API executes the route handler.
- Given a protected API request has no token or an invalid token
  When the request is processed
  Then the API returns 401 with an authorization error.

## Profile

- Given no profile exists
  When the frontend requests `/profile`
  Then the frontend receives `null` profile state and can prompt for profile inputs.
- Given valid profile fields
  When the user saves
  Then the profile is created or updated and targets are returned.
- Given invalid profile fields
  When the user saves
  Then save is rejected and field-level Arabic errors should identify the invalid fields.
- Given profile inputs change
  When preview is requested
  Then the system returns calculated targets without persisting the profile.

## Target Calculation

- Given sex, age, height, weight, activity level, goal, protein/kg, and fat percentage
  When targets are calculated
  Then BMR uses Mifflin-St Jeor, TDEE uses activity factor, target calories use goal factor, and macros are returned.
- Given carb calories are negative
  When targets are calculated
  Then `carb_g` is clamped to zero and `carb_clamped` is true.

## Food Catalog

- Given foods exist
  When the Foods page loads successfully
  Then foods are displayed by name order with serving, calories, macros, and net carbs.
- Given a search term is entered
  When matching food names exist
  Then only matching foods display.
- Given a search term has no matches
  When search finishes
  Then a no-results state displays and is distinct from empty catalog.
- Given valid food fields
  When the user saves a new food
  Then the food is persisted and appears in the catalog.
- Given invalid food fields
  When the user saves
  Then save is blocked and field-level Arabic errors display.
- Given an exact duplicate active food exists
  When the user saves a matching food
  Then save is blocked with a duplicate message.
- Given `fiber_g > carb_g`
  When the user saves
  Then save is blocked and net carbs must not become negative.
- Given the user edits a food
  When valid changes are saved
  Then the current food record changes, but old diary entries remain unchanged.
- Given the user deletes a food
  When confirmation is cancelled
  Then the food remains unchanged.
- Given the user confirms deletion of an unused food
  When the operation succeeds
  Then the food is removed from the active catalog.
- Given the user confirms deletion of a used food
  When the operation succeeds
  Then the food becomes archived/inactive and is hidden from future diary selection.

## Diary

- Given foods exist
  When the user selects a food, date, and positive serving quantity
  Then a diary entry is created and daily totals update.
- Given no foods exist
  When the user opens Diary
  Then the add-entry action is disabled and the page tells the user to add foods first.
- Given invalid quantity
  When the user submits
  Then diary creation is blocked with a field-level Arabic error.
- Given a diary entry is created
  When food values are later edited or deleted
  Then the diary entry keeps the original nutrition snapshot.
- Given a diary entry is deleted
  When delete succeeds
  Then it is removed from the selected day and totals refresh.

## Weekly Summary

- Given any selected date
  When weekly summary is requested
  Then the backend normalizes the range to Sunday through Saturday.
- Given diary entries exist inside the week
  When the week is returned
  Then each day includes totals and the week includes weekly totals.
- Given profile exists
  When weekly summary is returned
  Then targets are included.
- Given profile is missing
  When weekly summary is returned
  Then targets are null.

## Online Network Error Handling

- Given an API read fails because the backend is unreachable
  When the page loads
  Then a clear connection error is displayed.
- Given an API read fails
  When local cached personal nutrition data exists
  Then cached data is not treated as the v1 source of truth.
- Given an API write fails because the backend is unreachable
  When the user submits Profile, Food, or Diary changes
  Then no local mutation is queued and no local personal data is marked as saved.
- Given a write fails
  When the error is shown
  Then the user's form input remains available for retry.
- Given invalid data is rejected by the backend
  When the response returns
  Then the invalid data is not saved locally or queued.

## Future Scope: Offline and Sync

- Given v1 is implemented
  When offline cache, pending sync, sync push/pull, stale cache, or conflict behavior is requested
  Then the behavior is treated as Future Scope and excluded from v1 acceptance.

## Mobile, RTL, Accessibility

- Given a mobile viewport
  When a page renders
  Then content does not require horizontal scrolling for standard use.
- Given icon-only buttons exist
  When assistive technology reads the control
  Then the button has an accessible name.
- Given a field validation error occurs
  When the form is submitted
  Then the error is accessible and displayed near the field.
