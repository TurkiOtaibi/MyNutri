# User Story Quality Audit

The BA package contains 27 user stories. The set is useful, but multiple stories are too broad, depend on unresolved product decisions, or contain acceptance criteria that cannot yet be implemented consistently.

## Story Quality Findings

| User story ID | Issue | Severity | Why it matters | Recommended fix |
|---|---|---|---|---|
| `US-SHELL-HAPPY-001` | Combines installability, service worker behavior, online-only data rules, and connection errors. | High | The story is too broad and hides the service-worker scope decision. | Split installable shell from online-only data/cache behavior. |
| `US-PROFILE-HAPPY-001` | Says API failure should not save or queue, but current code queues failed saves. | Critical | The story is correct for v1, but implementation evidence contradicts it. | Add explicit no-local-save/no-queue acceptance criteria and implementation tasks later. |
| `US-PROFILE-VALIDATION-001` | Validation story lacks birth-date bounds, max height/weight, error messages, and timing. | High | QA cannot create complete negative tests. | Expand profile validation matrix and Arabic error copy. |
| `US-TARGET-HAPPY-001` | Does not cover preview API failure or invalid profile input during preview. | Medium | The live preview may fail silently or show stale target data. | Add preview loading/error acceptance criteria. |
| `US-FOOD-HAPPY-001` | Food list story does not separate loading, empty catalog, no-results, and API error states. | High | QA cannot distinguish expected states. | Add or split state-specific stories. |
| `US-FOOD-HAPPY-002` | Search story assumes distinct no-results behavior that is missing in code and weakly specified. | Medium | No-results can be confused with empty catalog. | Define no-results UI copy and reset behavior. |
| `US-FOOD-CRUD-001` | Create story is too broad and relies on incomplete field validation. | High | Food data quality is central to Diary totals. | Split create happy path from full field validation, duplicate, and network failure stories. |
| `US-FOOD-VALIDATION-001` | Missing max lengths, accepted characters, trim/whitespace normalization, numeric max values, and exact Arabic messages. | High | Validation is not testable enough. | Add field-level rule matrix and acceptance criteria. |
| `US-FOOD-VALIDATION-002` | Correctly requires no negative net carbs, but lacks exact trigger timing and error text. | High | Developers may implement frontend-only or inconsistent validation. | Specify frontend and backend validation, save/update triggers, and Arabic field error. |
| `US-FOOD-VALIDATION-003` | Duplicate definition is incomplete because brand is not implemented and archived-food behavior is unresolved. | High | Duplicate blocking can be inconsistent. | Resolve duplicate keys and archived-food participation. |
| `US-FOOD-CRUD-002` | Edit story does not cover duplicate-on-edit, validation errors, network errors, or snapshot proof. | Medium | Editing food can corrupt catalog expectations or hide failed updates. | Add edit-specific negative criteria. |
| `US-FOOD-CRUD-003` | Delete/archive story includes missing architecture decisions: archive field, usage check, active filtering. | Critical | Destructive behavior cannot be implemented safely from this story alone. | Rewrite after lifecycle decision. |
| `US-DIARY-CRUD-001` | Serving logging story conflicts with current offline queue behavior on API error. | High | Failed diary writes may appear saved. | Add no-local-entry/no-queue behavior and tests. |
| `US-DIARY-VALIDATION-001` | Quantity validation lacks max, blank behavior, invalid food recovery, and Arabic message details. | High | Totals can be distorted or QA cannot verify validation. | Expand diary validation rules. |
| `US-DIARY-CRUD-002` | Delete story lacks confirmation/undo decision and conflicts with current queued delete behavior. | High | Accidental deletion and offline contradiction remain. | Decide confirmation/undo and add no-queue delete failure criteria. |
| `US-DIARY-GRAM-001` | Planned gram logging is not backed by an API/UI contract. | High | It is not implementation-ready. | Mark Decision Needed or define payload, mode, and calculation rules. |
| `US-NETWORK-ERROR-001` | One story covers all read/write/network/server validation failures. | High | Too broad for implementation and QA. | Split by read failures, write failures, status codes, and page contexts. |
| `US-A11Y-001` | Accessibility criteria are generic. | High | QA cannot verify exact labels, focus, live regions, and error semantics. | Add field error and icon-button accessibility stories. |
| `US-MOBILE-001` | Mobile story lacks keyboard, safe-area, fixed widget, and touch-target details. | Medium | Daily mobile use may regress. | Add mobile acceptance criteria per page/form. |
| `US-QA-001` | Test story names many coverage areas but does not map test types to stories/features. | Medium | QA planning remains vague. | Add a QA matrix by feature, test type, and priority. |

## Duplicate and Overlap Review

No exact duplicate user stories were found. There is functional overlap between:
- `US-NETWORK-ERROR-001` and the network criteria embedded in Profile/Food/Diary CRUD stories.
- `US-FUTURE-OFFLINE-001` and `US-SHELL-HAPPY-001`.

This overlap is acceptable as product emphasis, but should be clarified:
- Keep `US-NETWORK-ERROR-001` as an umbrella requirement only if page-specific stories carry testable acceptance criteria.
- Keep `US-FUTURE-OFFLINE-001` as a scope-control story, not an implementation story.

## Stories That Are Not Yet Testable Enough

| Story | Reason |
|---|---|
| `US-FOOD-CRUD-003` | Archive field and usage-check behavior are not defined. |
| `US-DIARY-GRAM-001` | No grams payload, UI mode, or API behavior exists. |
| `US-NETWORK-ERROR-001` | Too broad and lacks error copy/status mapping. |
| `US-A11Y-001` | No precise accessible names, error semantics, or focus rules. |
| `US-QA-001` | Describes coverage goals but not concrete verification scope. |

