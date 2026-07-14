# Feature Coverage Audit

Source feature map: `docs/ba/01_FEATURE_MAP.md`

Coverage scale:
- Fully Covered: enough stories/criteria exist for BA planning and QA design.
- Partially Covered: core coverage exists but needs cleanup, added edge cases, or clearer acceptance.
- Missing: no meaningful story/criteria coverage.
- Future Scope Covered: feature is explicitly out of v1 and has scope story/decision.

## Feature Coverage Table

| Feature ID | Feature | Covered by story IDs | Status | Notes |
|---|---|---|---|---|
| F-001 | App shell and RTL layout | `US-APP-HAPPY-001`, `US-MOBILE-001`, `US-A11Y-001` | Fully Covered | Strong enough for v1; visual QA still required. |
| F-002 | Home route redirect | Acceptance criteria only | Partially Covered | Covered in `09_ACCEPTANCE_CRITERIA.md`; no dedicated story. Low risk. |
| F-003 | Top navigation | `US-APP-HAPPY-001` | Fully Covered | Diary/Foods/Profile nav covered. |
| F-004 | Optional installable shell | `US-SHELL-HAPPY-001`, `US-SHELL-SCOPE-001` | Fully Covered | Install shell is scoped without offline data behavior. |
| F-005 | Service worker shell scope | `US-SHELL-SCOPE-001`, `US-NETWORK-READ-001` | Fully Covered | BA is clear; current code conflicts. |
| F-006 | Mobile responsive support matrix | `US-MOBILE-001`, `US-A11Y-001` | Fully Covered | Viewports and mixed text are covered. |
| F-007 | Single-user token auth | `US-AUTH-PERM-001`, `US-ERROR-MAPPING-001` | Fully Covered | API 401 and UI 401 covered. |
| F-008 | Health endpoint | None | Partially Covered | Implemented infrastructure feature, but no story or traceability row. Low BA gap. |
| F-009 | Environment config | None | Partially Covered | No story. Acceptable if treated as implementation/config requirement; traceability can be improved. |
| F-010 | Read profile | `US-PROFILE-HAPPY-001`, `US-NETWORK-READ-001` | Partially Covered | Missing-profile state is in AC/message docs, but lacks a focused user story. |
| F-011 | Upsert profile | `US-PROFILE-HAPPY-001`, `US-NETWORK-WRITE-001` | Fully Covered | Online-only save and 422 are covered. |
| F-012 | Profile validation bounds | `US-PROFILE-VALIDATION-001` | Fully Covered | Field dictionary and validation rules define ranges. |
| F-013 | Live target preview | `US-TARGET-HAPPY-001`, `US-PROFILE-VALIDATION-001` | Fully Covered | Preview invalid-state behavior is covered. |
| F-014 | Calc engine | `US-TARGET-HAPPY-001` | Fully Covered | Formula behavior and clamp covered; tests exist. |
| F-015 | Target display | `US-TARGET-HAPPY-001`, `US-DIARY-HAPPY-001` | Fully Covered | Profile and Diary display covered. |
| F-016 | Multiple people/profiles | `US-PROFILE-SCOPE-001` | Future Scope Covered | Explicitly out of v1 through D-016. |
| F-017 | Active food list | `US-FOOD-HAPPY-001` | Fully Covered | Active-only list and archived hiding covered. |
| F-018 | Food search | `US-FOOD-HAPPY-002`, `US-FOOD-STATE-001` | Fully Covered | Active-only search and no-results covered. |
| F-019 | Food create | `US-FOOD-CRUD-001`, validation stories | Fully Covered | Create, optional nutrients, duplicate, errors covered. |
| F-020 | Food edit | `US-FOOD-CRUD-002`, validation stories | Partially Covered | Edit-after-archive/stale edit edge is not explicit. |
| F-021 | Food details | `US-FOOD-HAPPY-003`, `US-MOBILE-001` | Fully Covered | Optional nutrient display and full long name in detail covered. |
| F-022 | Food archive/delete | `US-FOOD-CRUD-003`, `US-A11Y-001` | Fully Covered | Confirmation, cancel, archive, failure, snapshots covered. |
| F-023 | Food archive fields | `US-FOOD-CRUD-003` | Fully Covered | `is_active` and `archived_at` defined in decisions and field dictionary. |
| F-024 | Duplicate food prevention | `US-FOOD-VALIDATION-003` | Fully Covered | Active-only duplicate and archived duplicate behavior covered. |
| F-025 | Net carbs validation | `US-FOOD-VALIDATION-002` | Fully Covered | `fiber_g <= carb_g` covered. |
| F-026 | Serving grams metadata | `US-FOOD-CRUD-001`, `US-DIARY-GRAM-001` | Fully Covered | Field naming and validation covered. |
| F-027 | Food state handling | `US-FOOD-STATE-001`, `US-NETWORK-READ-001` | Fully Covered | Loading, empty, no-results, API errors covered. |
| F-028 | Diary day view | `US-DIARY-HAPPY-001` | Fully Covered | Entries, empty day, read error covered. |
| F-029 | Add diary entry by servings | `US-DIARY-CRUD-001`, `US-DIARY-VALIDATION-001` | Fully Covered | Create, date, quantity, API failure covered. |
| F-030 | Add diary entry by grams | `US-DIARY-GRAM-001`, `US-DIARY-VALIDATION-001` | Partially Covered | User behavior is clear; API/storage contract remains high BA gap. |
| F-031 | Diary quantity edit | `US-DIARY-EDIT-001`, `US-DIARY-VALIDATION-001` | Fully Covered | Quantity-only edit, mode-specific quantity, failure covered. |
| F-032 | Delete diary entry | `US-DIARY-CRUD-002`, `US-A11Y-001` | Fully Covered | Confirmation, cancel, success, failure, totals covered. |
| F-033 | Future date block | `US-DIARY-VALIDATION-001` | Fully Covered | Create/edit future date block covered. |
| F-034 | Nutrition snapshot | `US-DIARY-INTEGRITY-001`, gram story | Fully Covered | Serving snapshot covered; gram snapshot required. |
| F-035 | Weekly summary | `US-DIARY-HAPPY-002` | Fully Covered | Sunday-Saturday, no entries, API error covered. |
| F-036 | Online API reads | `US-NETWORK-READ-001`, page stories | Partially Covered | Read-specific Arabic copy remains high BA gap. |
| F-037 | Online API writes | `US-NETWORK-WRITE-001`, CRUD stories | Fully Covered | No queue/no local save covered. |
| F-038 | API error mapping | `US-ERROR-MAPPING-001` | Partially Covered | Mapping exists; read-vs-write copy gap remains. |
| F-039 | Arabic validation messages | validation stories, `US-A11Y-001` | Fully Covered | Exact copy file exists; implementation must align. |
| F-040 | Accessibility basics | `US-A11Y-001` | Partially Covered | Core coverage exists, but "where practical" weakens testability. |
| F-041 | Mobile/RTL quality | `US-MOBILE-001` | Fully Covered | Viewports, keyboard, mixed text, long names covered. |
| F-042 | Backend and frontend tests | `US-QA-001` | Partially Covered | Test areas exist, but story is broad and lacks test-data matrix. |
| F-043 | IndexedDB cache and offline mutation queue | `US-FUTURE-OFFLINE-001`, D-001 | Future Scope Covered | BA correctly excludes from v1. |
| F-044 | Sync push/pull and pending sync states | `US-FUTURE-OFFLINE-001`, D-001 | Future Scope Covered | BA correctly excludes from v1. |

## Coverage Summary

| Coverage category | Count |
|---|---:|
| Fully Covered | 30 |
| Partially Covered | 10 |
| Future Scope Covered | 4 |
| Missing | 0 |

## Main Coverage Risks

1. Gram-mode Diary behavior is covered from a user perspective but not from a final API/storage contract perspective.
2. Health endpoint and environment config are implemented features without user-story traceability; low risk if deliberately treated as technical requirements.
3. Accessibility and QA stories are broad and should be sharpened before final QA case generation.
4. Read-error behavior is covered generally but lacks exact Arabic copy for non-write failures.
