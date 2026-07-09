# Negative and Edge Scenarios

## Auth and Permission

| Scenario | Expected behavior | Status | Evidence / gap |
|---|---|---|---|
| Missing bearer token calls protected API | API returns 401 | Confirmed | `require_single_user` |
| Invalid bearer token calls protected API | API returns 401 | Confirmed | `require_single_user` |
| Empty configured token | API allows requests | Confirmed | `require_single_user` returns when expected token is empty |
| Unauthorized user action | Clear UI message | Missing | No explicit auth error UX |

## Profile

| Scenario | Expected behavior | Status |
|---|---|---|
| Profile not created | `/profile` returns 404; frontend treats as `null` | Confirmed |
| Invalid height/weight | Reject with validation error | Backend confirmed; custom UI missing |
| Future birth date | Decision needed | Open Question |
| Advanced values outside range | Reject | Backend confirmed; custom UI missing |
| API unreachable during profile save | Do not save or queue; preserve input and show connection error | Required for v1 / current code needs alignment |

## Foods

| Scenario | Expected behavior | Status |
|---|---|---|
| Empty food catalog | Show empty state | Confirmed basic state; add action missing |
| Search no matches | Show distinct no-results state | Missing/planned |
| API load fails | Show clear connection error; do not use cached personal data as source of truth | Required for v1 / current code needs alignment |
| Food name blank | Block save | Backend/browser partial |
| Food name whitespace-only | Block save | Missing |
| Serving label blank | Block save | Backend/browser partial |
| Required numeric blank | Block save | Missing; can become `0` |
| Negative nutrient | Block save | Backend confirmed; UI message missing |
| Extremely high nutrient | Reject or show clear error | Decision needed |
| `serving_grams=0` | Reject with clear error | Backend rejects; UI mismatch |
| `fiber_g > carb_g` | Block save | Missing/planned |
| Exact duplicate food | Block save | Missing/planned |
| Delete tapped accidentally | Confirmation required | Missing |
| Delete used food | Archive/inactive, not hard delete | Missing/planned |
| Delete unused food | Hard delete allowed after confirmation | Partially implemented without confirmation |
| API unreachable during food delete | Do not delete locally or queue; show connection error | Required for v1 / current code needs alignment |
| Deleted food used by diary | Historical nutrition remains through snapshot | Confirmed |

## Diary

| Scenario | Expected behavior | Status |
|---|---|---|
| No foods exist | Disable submit and show add-food note | Confirmed |
| Quantity zero or negative | Reject | Backend and UI min partial; custom error missing |
| Quantity blank/non-number | Reject | Incomplete |
| Food deleted before log submit | API rejects; UI recovery needed | Partial |
| API unreachable during diary add | Do not create local entry or queue; show connection error | Required for v1 / current code needs alignment |
| Delete diary entry accidentally | Confirmation recommended | Missing |
| Future date entry | Decision needed | Open Question |
| Backend diary update | UI scope unclear | Open Question |
| Missing profile targets | Show profile prompt/no targets | Confirmed via `TargetStrip` |

## Weekly Summary

| Scenario | Expected behavior | Status |
|---|---|---|
| Week start passed as weekday | Normalize to Sunday | Confirmed |
| No entries in week | Return seven days with zero totals | Confirmed |
| Profile missing | Targets are null | Confirmed |
| API unreachable during weekly summary load | Show clear connection error; do not treat cached totals as source of truth | Required for v1 / current code needs alignment |
| Timezone boundary | Decision needed | Open Question |

## Online Network Errors and Future Offline Scope

| Scenario | Expected behavior | Status |
|---|---|---|
| Backend/API unreachable on read | Show connection error; do not show stale personal nutrition data as authoritative | Required for v1 |
| Backend/API unreachable on write | Do not save locally, do not queue, preserve form input, show connection error | Required for v1 |
| Server validation rejects write | Do not queue as offline mutation; show field/form error | Required for v1 |
| Pending mutations exist in current code | Should not be used in v1 | Future Scope |
| Sync push/pull | Should not be required for v1 | Future Scope |
| Conflict/concurrent offline edit | Not applicable to v1 | Future Scope |
| Stale cache behavior | Not applicable to v1 source-of-truth behavior | Future Scope |
| Local cached personal data | Must not be v1 source of truth | Required for v1 |

## Mobile, RTL, Accessibility

| Scenario | Expected behavior | Status |
|---|---|---|
| Small screen | Single-column forms and readable nav | Confirmed |
| Long Arabic/English food names | Wrap without overlap | Partially confirmed by CSS; not tested |
| Bottom fixed widgets overlap content | Avoid overlap/safe area for install prompt or connection UI | Partial |
| Icon-only buttons | Accessible names | Partial; `title` used |
| Validation errors | Field-level, accessible, Arabic | Missing |
| Keyboard-only use | Focusable controls and visible focus | Partial |
| Screen reader status | Connection/error status announced | Missing/partial |
