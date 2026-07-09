# QA User Story Coverage Audit - Executive Summary

Audit mode: full requirements coverage audit.

Scope:
- BA outputs under `docs/ba/`.
- Current codebase under `backend/` and `frontend/`.
- Product scope: myNutri v1 is online-only. Offline-first behavior is Future Scope.

Report-only status:
- Application code changed: No.
- Existing BA files changed: No.
- Audit documentation created under `docs/qa/user-story-audit/`.

## Evidence Reviewed

| Area | Evidence |
|---|---|
| BA package | `docs/ba/00_EXECUTIVE_SUMMARY.md` through `docs/ba/13_PRODUCT_DECISIONS.md` |
| Backend API and models | `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/api/routes/*.py`, `backend/app/services/*.py` |
| Frontend UI and API client | `frontend/components/*.tsx`, `frontend/lib/api.ts`, `frontend/lib/db.ts`, `frontend/public/service-worker.js` |
| Tests | `backend/tests/test_calc.py`, `backend/tests/test_diary_snapshot.py`, `backend/tests/test_sync.py` |

## Audit Counts

| Metric | Count |
|---|---:|
| BA features reviewed | 38 |
| BA user stories reviewed | 27 |
| BA requirements gaps reviewed | 30 |
| Critical issues found | 2 |
| High issues found | 9 |
| Missing or weak stories identified | 18 |
| Field validation and error-message gaps identified | 26 |
| Leftover offline/sync contradictions in current code | 5 |

## Overall QA Verdict

Verdict: Partially Ready

Readiness score: 6 / 10

Main reason:
The BA package now correctly states that v1 is online-only, and it contains usable feature, CRUD, field, validation, negative scenario, acceptance, and traceability coverage. However, several core stories still depend on unresolved product decisions or contain acceptance criteria that are not specific enough for implementation and QA. The biggest blocker is that current code still actively queues offline writes and uses sync/cache behavior, directly contradicting the approved online-only v1 scope.

Implementation planning:
- Can start only for stable, confirmed slices such as calc behavior, snapshot behavior, basic API CRUD discovery, and UI cleanup planning.
- Should not start for broad v1 implementation until the Critical and High findings below are resolved.

QA test case generation:
- Can start partially for confirmed behavior: target calc, snapshot integrity, token auth, basic CRUD API contracts.
- Full v1 QA test generation should wait until network-error behavior, delete/archive lifecycle, duplicate rules, gram logging, and Arabic error copy are resolved.

## Critical Findings

### Finding QA-US-001

Severity: Critical  
Category: Online-only scope contradiction  
Feature: Online API writes, connection errors, future offline/sync  
Affected stories: `US-PROFILE-HAPPY-001`, `US-FOOD-CRUD-001`, `US-FOOD-CRUD-002`, `US-FOOD-CRUD-003`, `US-DIARY-CRUD-001`, `US-DIARY-CRUD-002`, `US-NETWORK-ERROR-001`, `US-FUTURE-OFFLINE-001`  
Evidence:
- `docs/ba/13_PRODUCT_DECISIONS.md`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/components/DiaryPage.tsx`
- `frontend/lib/db.ts`
- `backend/app/api/routes/sync.py`

Issue:
BA says failed writes must not be saved locally or queued. Current code still queues failed Profile/Food/Diary writes, writes local IndexedDB records, shows "saved locally and will sync" messages, and exposes sync push/pull behavior.

Why it matters:
This can make invalid or failed data appear saved, makes QA results ambiguous, and violates the approved v1 product decision.

Recommended fix:
Before implementation planning, update stories and acceptance criteria to require a shared online-only error pattern, and create implementation tasks to remove, disable, or hide offline queue/sync behavior for v1.

### Finding QA-US-002

Severity: Critical  
Category: Destructive data lifecycle  
Feature: Food delete/archive  
Affected stories: `US-FOOD-CRUD-003`, `US-DIARY-INTEGRITY-001`  
Evidence:
- `docs/ba/03_CRUD_PERMISSIONS_MATRIX.md`
- `docs/ba/07_USER_STORIES.md`
- `backend/app/models.py`
- `backend/app/services/food.py`
- `frontend/components/FoodsPage.tsx`

Issue:
The BA story requires delete confirmation and archive/inactive behavior for foods used in diary entries. Current code hard deletes immediately, has no confirmation, no archive field, no active/inactive filter, and no usage check.

Why it matters:
This is a destructive catalog action. Snapshot data protects diary nutrition totals, but the catalog lifecycle is still undefined and can remove foods from future selection without warning.

Recommended fix:
Resolve the food lifecycle design before implementation: confirmation behavior, used-food detection, archive field, hidden-from-selection behavior, and duplicate behavior for archived foods.

## High Findings

| ID | Severity | Area | Issue |
|---|---|---|---|
| QA-US-003 | High | Field validation | Food/Profile/Diary stories do not define full max values, accepted characters, trimming, empty numeric behavior, or complete Arabic error messages. |
| QA-US-004 | High | Duplicate foods | Duplicate prevention is required but the story is not fully testable because archived-food participation and exact normalized fields remain open. |
| QA-US-005 | High | Negative net carbs | `fiber_g <= carb_g` is required but not implemented, and story coverage needs exact field-level error copy and trigger timing. |
| QA-US-006 | High | Gram logging | Gram-based diary logging is planned but the API/UI data contract is missing. It should be a Decision Needed item before build work. |
| QA-US-007 | High | Network errors | `US-NETWORK-ERROR-001` is too broad; it must be split by read/write, page, status type, and retry behavior. |
| QA-US-008 | High | Current service worker/PWA scope | Optional installable shell is allowed, but current service worker caches GET responses and offline navigation, which may conflict with online-only personal data rules. |
| QA-US-009 | High | Diary scope | Backend diary update exists but UI/story scope is unclear; future diary date behavior is also unresolved. |
| QA-US-010 | High | Accessibility | Stories require accessible controls, but field error semantics, focus movement, `aria-invalid`, and live regions are not specified. |
| QA-US-011 | High | Testability | Existing tests cover calc, snapshot, and future-scope sync. Direct Profile/Food/Diary CRUD, network-error, auth, UI, mobile, RTL, and a11y coverage is missing. |

## Readiness Summary

| Dimension | Score | Status |
|---|---:|---|
| Story coverage | 70 / 100 | Needs requirements cleanup |
| CRUD coverage | 68 / 100 | Needs missing scenarios |
| Field validation coverage | 52 / 100 | High risk |
| Negative scenario coverage | 65 / 100 | Needs cleanup |
| UX/UI coverage | 63 / 100 | Needs details |
| Mobile/RTL/a11y coverage | 58 / 100 | High risk |
| Online-only scope alignment | 45 / 100 | Not ready |
| Testability | 60 / 100 | Needs QA expansion |

## Top 5 Fixes Before Broad Implementation

1. Remove, disable, or clearly future-scope all offline queue/sync behavior in implementation requirements.
2. Finalize Food delete/archive lifecycle including confirmation, used-food check, archive field, active filtering, and duplicate behavior.
3. Split online network-error stories into page-specific read/write scenarios with no local persistence.
4. Complete field validation dictionaries with max values, accepted characters, trim behavior, Arabic messages, and error placement.
5. Decide gram-based diary logging contract, including UI mode, API payload, calculations, and missing serving weight behavior.

