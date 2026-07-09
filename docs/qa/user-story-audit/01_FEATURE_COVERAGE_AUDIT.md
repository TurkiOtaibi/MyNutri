# Feature Coverage Audit

Coverage was evaluated against `docs/ba/01_FEATURE_MAP.md`, `docs/ba/07_USER_STORIES.md`, and current code evidence.

Legend:
- Fully Covered: Story coverage is enough for implementation and QA.
- Partially Covered: A story exists, but important acceptance criteria, validation, negative path, or code-alignment details are missing.
- Missing: No adequate story exists.
- Future Scope: Correctly excluded from v1, but current code may still contain implementation evidence.
- Decision Needed: Product or engineering decision is required before the feature is build-ready.

## Coverage Table

| Feature ID | Feature | Covered by user story IDs | Coverage status | Readiness score | Notes |
|---|---|---|---|---:|---|
| F-001 | App shell and RTL layout | `US-APP-HAPPY-001` | Fully Covered | 85 | Needs visual/RTL tests but story is usable. |
| F-002 | Home route redirect | `US-APP-HAPPY-001`, acceptance file | Partially Covered | 75 | Redirect is in acceptance criteria, not an explicit story. |
| F-003 | Top navigation | `US-APP-HAPPY-001` | Fully Covered | 85 | Navigation actor and benefit are clear. |
| F-004 | Optional installable shell | `US-SHELL-HAPPY-001` | Partially Covered | 60 | Needs service-worker scope decision so shell does not imply offline data. |
| F-005 | Offline-first shell/data behavior | `US-FUTURE-OFFLINE-001` | Future Scope | 70 | Correctly future-scoped in BA; current code still contradicts v1. |
| F-006 | Responsive layout | `US-MOBILE-001` | Partially Covered | 65 | Mobile behavior is broad; safe area, keyboard, and fixed widget overlap are weak. |
| F-007 | Single-user token auth | `US-AUTH-PERM-001` | Partially Covered | 75 | API behavior covered; UI auth-error behavior missing. |
| F-008 | Health endpoint | None | Missing | 55 | Low product impact, but no story or QA expectation exists. |
| F-009 | CORS and environment config | None | Missing | 50 | Technical feature needs traceability or should be moved out of user-story scope. |
| F-010 | Read profile | `US-PROFILE-HAPPY-001` | Partially Covered | 70 | Missing explicit 404 empty-profile UI and network read error coverage. |
| F-011 | Upsert profile | `US-PROFILE-HAPPY-001`, `US-PROFILE-VALIDATION-001` | Partially Covered | 65 | Story conflicts with current queued-save behavior; Arabic errors missing. |
| F-012 | Live target preview | `US-TARGET-HAPPY-001` | Partially Covered | 75 | Happy path covered; preview error/loading behavior weak. |
| F-013 | Calc engine | `US-TARGET-HAPPY-001` | Fully Covered | 90 | Backed by calc tests; UI tests still missing. |
| F-014 | Target display | `US-TARGET-HAPPY-001` | Partially Covered | 80 | Core display covered; missing no-profile/network states. |
| F-015 | Multiple people/profiles | None | Decision Needed | 40 | Feature is missing in code and not resolved as v1 or future scope. |
| F-016 | Food list | `US-FOOD-HAPPY-001` | Partially Covered | 78 | Summary fields covered; loading/error/no-results split is weak. |
| F-017 | Food search | `US-FOOD-HAPPY-002` | Partially Covered | 70 | Search exists; no-results and API failure behavior need stronger criteria. |
| F-018 | Food create | `US-FOOD-CRUD-001`, `US-FOOD-VALIDATION-*` | Partially Covered | 60 | Duplicate, Arabic validation, and no-queue behavior are not implementation-ready. |
| F-019 | Food edit | `US-FOOD-CRUD-002` | Partially Covered | 65 | Happy path covered; validation, duplicate edit, and network errors weak. |
| F-020 | Food details | `US-FOOD-HAPPY-003` | Fully Covered | 80 | Inline details are covered; detail route not required. |
| F-021 | Food delete | `US-FOOD-CRUD-003` | Partially Covered | 45 | Destructive flow is not safe or testable enough. |
| F-022 | Food archive/inactive lifecycle | `US-FOOD-CRUD-003` | Partially Covered | 35 | No field/API model decision; archive behavior not build-ready. |
| F-023 | Net carbs | `US-FOOD-VALIDATION-002` | Partially Covered | 55 | Calculation exists, but negative prevention is missing in code and needs exact error behavior. |
| F-024 | Duplicate food prevention | `US-FOOD-VALIDATION-003` | Partially Covered | 50 | Duplicate fields and archived-food participation unresolved. |
| F-025 | Gram metadata | `US-DIARY-GRAM-001` | Partially Covered | 65 | Storage exists, usage behavior is missing. |
| F-026 | Diary day view | `US-DIARY-HAPPY-001` | Partially Covered | 75 | Happy/empty states covered; read error and stale cache rules need stronger criteria. |
| F-027 | Add diary entry by servings | `US-DIARY-CRUD-001`, `US-DIARY-VALIDATION-001` | Partially Covered | 65 | Serving logging covered; no-queue write failure contradicts current code. |
| F-028 | Delete diary entry | `US-DIARY-CRUD-002` | Partially Covered | 60 | Missing confirmation/undo decision; current code queues failed delete. |
| F-029 | Update diary entry API | None | Decision Needed | 35 | Backend supports update but UI/story scope is unclear. |
| F-030 | Nutrition snapshot | `US-DIARY-INTEGRITY-001` | Fully Covered | 90 | Strong story and direct unit test evidence. |
| F-031 | Weekly summary | `US-DIARY-HAPPY-002` | Partially Covered | 78 | Core aggregation covered; timezone and network errors need work. |
| F-032 | Gram-based diary logging | `US-DIARY-GRAM-001` | Partially Covered | 45 | Planned but no API/UI field contract. |
| F-033 | Online API reads | `US-NETWORK-ERROR-001` | Partially Covered | 55 | One broad story is not enough for Profile/Foods/Diary/Week read failure states. |
| F-034 | Online API writes | `US-NETWORK-ERROR-001` | Partially Covered | 35 | BA is correct, but current code queues failed writes. |
| F-035 | Connection error handling | `US-NETWORK-ERROR-001` | Partially Covered | 45 | Missing page-specific UI copy, retry behavior, and status-code mapping. |
| F-036 | IndexedDB cache and offline mutation queue | `US-FUTURE-OFFLINE-001` | Future Scope | 60 | Correctly excluded from v1; current code still active. |
| F-037 | Sync push/pull and pending sync states | `US-FUTURE-OFFLINE-001` | Future Scope | 60 | Correctly future-scoped; `/sync` and `SyncStatus` still exist in code. |
| F-038 | Backend tests | `US-QA-001` | Partially Covered | 55 | Existing tests are partial; sync test is future-scope evidence, not v1 coverage. |

## Coverage Summary

| Status | Count |
|---|---:|
| Fully Covered | 5 |
| Partially Covered | 24 |
| Missing | 2 |
| Future Scope | 3 |
| Decision Needed | 4 |

## Features Needing Story Work Before Implementation

1. F-021 and F-022: Food delete/archive lifecycle.
2. F-024: Duplicate food prevention.
3. F-032: Gram-based diary logging.
4. F-033 to F-035: Online read/write/network error states.
5. F-015 and F-029: Multiple profiles and diary update scope decisions.

