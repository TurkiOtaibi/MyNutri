# Open Questions and Product Decisions Audit

This file lists decisions that remain after reviewing `docs/ba/12_OPEN_QUESTIONS.md`, `docs/ba/13_PRODUCT_DECISIONS.md`, and the current codebase.

## Resolved Product Decision

| Decision | Status | QA interpretation |
|---|---|---|
| Offline-first is removed from v1. | Resolved | Offline cache as source of truth, IndexedDB personal data source-of-truth behavior, offline mutation queue, sync push/pull, pending sync states, conflict handling, stale cache behavior, offline writes, and sync rejection handling are Future Scope. |

## Remaining P0/P1 Decisions

| ID | Decision needed | Priority | Risk if unresolved | Recommended decision path |
|---|---|---|---|---|
| D-001 | How to remove, disable, or hide existing IndexedDB/sync behavior for v1. | P0 | Current code violates online-only requirements. | Create implementation decision before build planning. |
| D-002 | Whether the service worker remains for static shell assets only or is removed. | P0 | Cached personal data may appear current. | Choose shell-only SW or no SW for v1. |
| D-003 | Food delete lifecycle: archive all deletes or archive only used foods. | P0 | Delete story is not build-ready. | Select lifecycle rule and field design. |
| D-004 | Archive field design: `is_active`, `archived_at`, `deleted_at`, or another field. | P0 | API/database cannot support required behavior. | Engineering/PO decision needed. |
| D-005 | Whether archived foods participate in duplicate checks. | P0 | Duplicate validation will be inconsistent. | Decide active-only vs all catalog records. |
| D-006 | Exact duplicate key for v1 food fields. | P0 | Product decision mentions brand, but code has no brand field. | Use implemented fields or add brand as future. |
| D-007 | Gram-based diary logging: v1 requirement or future scope. | P0/P1 | Diary story is not testable without API/UI contract. | Decide before serious Diary work. |
| D-008 | Diary future-date policy. | P1 | Users can log future meals without explicit intent. | Allow with warning, allow silently, or block. |
| D-009 | Profile future birth date and age bounds. | P1 | Target calculations can be unrealistic. | Define date bounds. |
| D-010 | Diary entry edit UI scope. | P1 | Backend supports update, UI does not. | Include edit UI or document API-only/future. |
| D-011 | Exact Arabic validation messages for every field and form-level error. | P0 | QA cannot verify UX or a11y accurately. | UX/PO copy matrix required. |
| D-012 | Practical max values for food nutrients, profile height/weight, and diary quantity. | P1 | Extreme data can pass until DB/API failure. | Define product limits. |
| D-013 | API error mapping for 401, 404, 422, timeout, and 5xx. | P0 | Network/error stories are too broad. | Define shared error-handling contract. |
| D-014 | Delete confirmation pattern: dialog, inline confirmation, or undo snackbar. | P0 | Destructive flows remain unsafe. | Pick one pattern and define a11y behavior. |
| D-015 | Mobile device/browser support matrix. | P1 | Mobile QA scope is unclear. | Define target viewports and browsers. |

## Leftover Offline/Sync Contradictions

| ID | Contradiction | Evidence | Required disposition |
|---|---|---|---|
| OLC-001 | Profile save failure queues local mutation. | `frontend/components/ProfilePage.tsx`, `frontend/lib/db.ts` | Remove/disable for v1. |
| OLC-002 | Food save/delete failure writes local IndexedDB and queues mutation. | `frontend/components/FoodsPage.tsx`, `frontend/lib/db.ts` | Remove/disable for v1. |
| OLC-003 | Diary add/delete failure mutates local entries and queues mutation. | `frontend/components/DiaryPage.tsx`, `frontend/lib/db.ts` | Remove/disable for v1. |
| OLC-004 | Sync status UI exposes pending/syncing behavior. | `frontend/components/SyncStatus.tsx`, `frontend/components/Providers.tsx` | Hide/remove for v1. |
| OLC-005 | `/sync` API and sync tests remain active. | `backend/app/api/routes/sync.py`, `backend/app/api/router.py`, `backend/tests/test_sync.py` | Future-scope or exclude from v1 test runs. |

## Can Implementation Planning Start?

Decision:
Only limited implementation planning can start.

Allowed planning:
- Calc engine maintenance.
- Snapshot integrity tests.
- Basic online API CRUD review.
- Requirements cleanup tasks.

Blocked planning:
- Food delete/archive implementation.
- Offline/sync removal implementation details.
- Gram-based diary logging.
- Final validation/error UI.
- Full mobile/a11y QA plan.

## Can QA Test Case Generation Start?

Decision:
Partially.

Can start:
- Calc unit tests.
- Snapshot unit tests.
- Auth API tests.
- Basic existing API behavior tests.

Should wait:
- Food delete/archive tests.
- Duplicate food tests.
- Gram logging tests.
- Arabic validation copy tests.
- Online network-error E2E tests until error UI is specified.
- Mobile/a11y test cases until UI requirements are precise.

