# Negative Scenario Audit

Sources:
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- Current backend/frontend code

## Overall Coverage

Negative coverage is strong for the main product risks:
- Auth failure.
- Online read/write failure.
- No offline queue in v1.
- Food validation.
- Food duplicate handling.
- Food archive confirmation/failure.
- Diary future date.
- Diary quantity validation.
- Missing `serving_grams`.
- Snapshot integrity.
- Mobile/RTL/a11y basics.

Remaining gaps are edge and testability gaps, not fundamental product contradictions.

## Covered Negative Paths

| Area | Covered scenarios |
|---|---|
| Auth | Missing/invalid bearer token, UI 401 message. |
| Profile | Missing profile, invalid date/age/ranges, API save failure, server validation. |
| Foods | Empty catalog, no search results, API load failure, blank text, invalid numbers, negative/high values, duplicate, archive failure, archived diary history. |
| Diary | No foods, invalid quantities, missing serving grams, archived food before submit, future date, API failure, edit forbidden fields, delete confirmation/failure. |
| Weekly | Week normalization, no entries, missing profile, read failure, future days visible but not writable. |
| Online-only | API read/write failure, no queue, no stale cache source-of-truth, sync future scope. |
| Mobile/RTL/a11y | Supported widths, keyboard reachability, icon names, validation focus, dialogs, mixed text. |

## Missing or Weak Negative Scenarios

| Gap ID | Scenario | Severity | Why it matters | Recommended BA fix |
|---|---|---|---|---|
| NEG-001 | Rapid double submit for Profile/Food/Diary writes. | Medium | Duplicate requests can create duplicate foods/entries or race states. | Add pending-state acceptance criteria for all writes. |
| NEG-002 | Food is archived/deleted after edit form opens but before save. | Medium | Stale edit can change inactive data or show misleading success. | Add stale edit 404/refresh-required criteria. |
| NEG-003 | Diary entry already deleted before confirm/delete response. | Medium | Delete flow needs not-found recovery. | Add 404 criteria for delete/edit stale entry. |
| NEG-004 | Invalid enum sent directly to API. | Low | UI selects valid options, but API tests need invalid enum behavior. | Add API validation scenario for invalid `sex`, `activity_level`, `goal`, `log_mode`. |
| NEG-005 | HTML/script input in food name/serving label. | Medium | Field dictionary forbids rendered markup, but no negative scenario exists. | Add escaped rendering or rejection criteria. |
| NEG-006 | Service worker cached navigation while API is down. | Medium | BA says shell may remain, but personal data must not look current. | Add scenario for cached shell plus failed data APIs. |
| NEG-007 | Long single-token food name. | Low | D-020 covers long names generally, but single long token can break layout. | Add long unbroken Arabic/English token visual scenario. |

## Offline/Sync Negative Scope

BA correctly marks these as Future Scope:
- Offline writes.
- IndexedDB source of truth.
- Offline mutation queue.
- Sync push/pull.
- Pending sync states.
- Conflict handling.
- Stale cache behavior.

Current code still implements these behaviors. This is implementation alignment, not a BA contradiction.
