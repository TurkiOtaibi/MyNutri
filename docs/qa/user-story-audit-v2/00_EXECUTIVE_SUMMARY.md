# Fresh QA Audit v2 - Executive Summary

Audit mode: full, fresh audit from current BA package and current codebase.

Report-only audit:
- Application code changed: No.
- BA files changed: No.
- Previous QA audit files changed: No.
- New files created only under `docs/qa/user-story-audit-v2/`.

## Scope Reviewed

BA evidence:
- `docs/ba/00_EXECUTIVE_SUMMARY.md`
- `docs/ba/01_FEATURE_MAP.md`
- `docs/ba/03_CRUD_PERMISSIONS_MATRIX.md`
- `docs/ba/04_FIELD_DICTIONARY.md`
- `docs/ba/05_VALIDATION_RULES.md`
- `docs/ba/06_ERROR_MESSAGES.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `docs/ba/10_TRACEABILITY_MATRIX.md`
- `docs/ba/11_REQUIREMENTS_GAPS.md`
- `docs/ba/12_OPEN_QUESTIONS.md`
- `docs/ba/13_PRODUCT_DECISIONS.md`

Code evidence:
- Backend models, schemas, routes, services, migrations, and tests under `backend/`.
- Frontend routes, components, API client, IndexedDB/sync utilities, service worker, manifest, CSS, and types under `frontend/`.

## Verdict

Overall verdict: Partially Ready
Readiness score: 8/10

Main reason:
The BA package is mostly internally consistent, product decisions D-001 through D-020 are closed, and the offline-first behavior is correctly marked Future Scope in BA. The package is close to implementation-planning ready, but two high-risk BA ambiguities remain: gram-mode Diary API/storage contract and read-specific network error copy.

## Counts

| Metric | Count |
|---|---:|
| Features reviewed from `01_FEATURE_MAP.md` | 44 |
| User stories reviewed from `07_USER_STORIES.md` | 33 |
| Product decisions reviewed | 20 |
| Critical BA issues | 0 |
| High BA issues | 2 |
| Remaining BA gaps | 7 |
| Missing/improved story or criteria proposals | 7 |
| Implementation alignment items found | 18 |
| Leftover offline/sync current-code contradictions | 10 |

## Critical BA Findings

None.

No BA contradiction was found that makes the core v1 impossible to implement. The current code still contains major offline/sync behavior, but BA documents this as Future Scope or implementation alignment rather than v1 accepted behavior.

## High BA Findings

### BA-HIGH-001 - Gram-mode Diary API/storage contract is still ambiguous

Evidence:
- `docs/ba/04_FIELD_DICTIONARY.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `frontend/lib/types.ts`
- `backend/app/schemas.py`

Issue:
BA requires gram-based Diary logging, but it does not fully specify the API/storage contract. It names `log_mode`, `quantity`, and `grams`, but still says exact API shape must align. It is unclear whether the backend stores grams separately, stores a serving-equivalent quantity, stores both `log_mode` and mode quantity, or freezes only calculated totals.

Impact:
Developers can implement incompatible API contracts, and QA cannot write final API/E2E tests for gram-mode create/edit/snapshot behavior.

Recommended BA fix:
Add a product decision or acceptance criteria defining the exact Diary create/update payload and persisted fields for serving mode and gram mode.

### BA-HIGH-002 - Read-specific network error copy is not exact

Evidence:
- `docs/ba/06_ERROR_MESSAGES.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/components/DiaryPage.tsx`

Issue:
BA requires exact Arabic validation/error messages, but the current network message is write-oriented: it says changes were not saved. Read failure stories mention a read-appropriate connection copy, but `06_ERROR_MESSAGES.md` does not define exact read-failure Arabic text.

Impact:
QA cannot assert exact copy for Profile/Foods/Diary/Week read failures, and the UI may show misleading save language during load failures.

Recommended BA fix:
Add exact Arabic copy for API read failure and distinguish it from failed write copy.

## BA Readiness

Implementation planning can start: Yes, conditionally.

Planning can start for stable areas: Profile validation, Food archive, duplicate food, API error mapping, online-only writes, mobile/RTL, and accessibility. Gram-mode Diary API/storage and read-specific error copy should be resolved before coding those areas.

QA test case generation can start: Yes, conditionally.

QA can begin test cases for most v1 behavior. Final API/E2E cases for gram-mode Diary logging and exact read-error copy should wait for the BA fixes above.

## Top 5 Fixes Before Implementation

1. Define the exact gram-mode Diary API/storage contract.
2. Add exact Arabic read-failure network error copy.
3. Replace vague acceptance wording such as "where practical", "where possible", and "D-013 applies" with minimum observable behavior where used for QA-critical flows.
4. Add stale/duplicate-submit edge acceptance criteria for Food save/archive and Diary create/edit/delete.
5. Add BA traceability for current offline page/metadata copy and cached-read fallbacks as implementation alignment evidence.

## Top 5 QA Focus Areas

1. Online-only behavior: no local save, no queue, no source-of-truth IndexedDB.
2. Food lifecycle: archive fields, confirmation, active filtering, duplicate checks.
3. Diary correctness: serving logging, gram logging, quantity-only edit, delete confirmation, future-date block, snapshot integrity.
4. Field validation: v1 ranges, Arabic messages, negative net carbs, missing serving grams.
5. Mobile/RTL/accessibility: required viewport matrix, mixed text, long food names, dialogs, icon buttons, field errors.
