# Traceability Audit

This audit checks whether BA requirements can be traced to stories, code evidence, and tests, and whether current code contradicts the online-only v1 scope.

## Traceability Summary

| Area | Traceability status | Notes |
|---|---|---|
| Feature to story | Partial | Most product features have at least one story, but several are too broad or missing. |
| Story to code evidence | Strong | BA files usually cite relevant components/routes/services. |
| Story to validation fields | Partial | Field names exist, but rules/messages are incomplete. |
| Story to tests | Weak | Direct API/UI/network/a11y/mobile tests are mostly missing. |
| Online-only decision to code | Weak | BA decision is clear, but implementation still contains offline queue/sync behavior. |

## Critical Traceability Contradictions

| ID | Product requirement | Contradicting code evidence | Severity | Impact |
|---|---|---|---|---|
| TRACE-001 | Failed Profile writes must not be queued or saved locally. | `frontend/components/ProfilePage.tsx` calls `queueMutation` in `onError`. | Critical | Failed profile save can appear saved locally. |
| TRACE-002 | Failed Food writes/deletes must not be queued or saved locally. | `frontend/components/FoodsPage.tsx` writes IndexedDB and calls `queueMutation` in mutation errors. | Critical | Invalid or failed food changes can appear saved/deleted. |
| TRACE-003 | Failed Diary writes/deletes must not be queued or saved locally. | `frontend/components/DiaryPage.tsx` creates/deletes local entries and queues mutations in `onError`. | Critical | Diary totals can change without successful API response. |
| TRACE-004 | Sync push/pull and pending sync states are Future Scope. | `frontend/components/SyncStatus.tsx`, `frontend/lib/db.ts`, `backend/app/api/routes/sync.py`, `backend/app/api/router.py`. | High | Future behavior remains user-visible and API-visible. |
| TRACE-005 | Cached personal nutrition data must not be source of truth. | `frontend/public/service-worker.js` caches GET responses and serves offline page; `frontend/lib/db.ts` caches Profile/Foods/Diary. | High | Stale data may be perceived as current. |

Leftover offline/sync contradictions: 5.

## Story to Evidence Matrix

| Story | Code evidence | Test evidence | Traceability readiness | Gaps |
|---|---|---|---|---|
| `US-APP-HAPPY-001` | `layout.tsx`, `AppNav.tsx`, `globals.css` | Missing E2E/visual | Medium | RTL/mobile tests missing. |
| `US-AUTH-PERM-001` | `auth.py`, protected routers | Missing auth tests | Medium | UI 401 behavior missing. |
| `US-SHELL-HAPPY-001` | `manifest.json`, `InstallPrompt.tsx`, `service-worker.js` | Missing | Low | SW behavior conflicts with online-only scope. |
| `US-PROFILE-HAPPY-001` | `ProfilePage.tsx`, `profile.py`, `profile service` | Missing route/UI tests | Low | Current onError queues local save. |
| `US-PROFILE-VALIDATION-001` | `schemas.py`, `ProfilePage.tsx` | Missing validation tests | Medium | Error copy and date policy missing. |
| `US-TARGET-HAPPY-001` | `calc.py`, `ProfilePage.tsx`, `TargetStrip.tsx` | `test_calc.py` | High | Preview error UI missing. |
| `US-FOOD-HAPPY-001` | `FoodsPage.tsx`, `foods.py` | Missing | Medium | State distinctions weak. |
| `US-FOOD-HAPPY-002` | `food.py`, `FoodsPage.tsx`, `api.ts` | Missing | Medium | No-results and network tests missing. |
| `US-FOOD-CRUD-001` | `FoodsPage.tsx`, `foods.py`, `schemas.py` | Missing | Low | Local queue conflict, validation gaps. |
| `US-FOOD-VALIDATION-001` | `schemas.py`, `FoodsPage.tsx` | Missing | Medium | Full field matrix incomplete. |
| `US-FOOD-VALIDATION-002` | `food.py`, `schemas.py` | Missing | Medium | Required behavior not implemented. |
| `US-FOOD-VALIDATION-003` | BA docs only | Missing | Low | Duplicate rule unresolved. |
| `US-FOOD-CRUD-002` | `FoodsPage.tsx`, `food.py` | Missing | Medium | Duplicate/network edit errors weak. |
| `US-FOOD-CRUD-003` | `FoodsPage.tsx`, `food.py`, `models.py` | Missing | Low | Archive field and confirmation missing. |
| `US-FOOD-HAPPY-003` | `FoodsPage.tsx` | Missing UI tests | Medium | Details are implemented but not tested. |
| `US-DIARY-HAPPY-001` | `DiaryPage.tsx`, `diary.py` | Missing | Medium | Read failure behavior weak. |
| `US-DIARY-CRUD-001` | `DiaryPage.tsx`, `diary.py`, `diary service` | Snapshot test partial | Low | Current onError queues local entry. |
| `US-DIARY-VALIDATION-001` | `schemas.py`, `DiaryPage.tsx` | Missing | Medium | Quantity/date validation incomplete. |
| `US-DIARY-INTEGRITY-001` | `diary.py`, `test_diary_snapshot.py` | Present | High | Strongest story/test alignment. |
| `US-DIARY-CRUD-002` | `DiaryPage.tsx`, `diary.py` | Missing | Low | Current onError queues delete; no confirmation. |
| `US-DIARY-HAPPY-002` | `aggregation.py`, `DiaryPage.tsx` | Missing | Medium | Timezone/network cases missing. |
| `US-DIARY-GRAM-001` | BA docs only; `serving_grams` exists | Missing | Low | API/UI contract missing. |
| `US-NETWORK-ERROR-001` | `api.ts`, page mutation handlers | Missing | Low | Too broad; code contradicts it. |
| `US-FUTURE-OFFLINE-001` | `db.ts`, `sync.py`, `test_sync.py` | Future-scope sync test | Medium | Correct scope, active code conflict. |
| `US-A11Y-001` | Components | Missing | Low | Criteria too generic. |
| `US-MOBILE-001` | `globals.css` | Missing | Medium | Needs visual/mobile matrix. |
| `US-QA-001` | `backend/tests` | Partial | Medium | Needs concrete test matrix. |

## Test Traceability Gaps

| Area | Current tests | Missing tests |
|---|---|---|
| Calc engine | `backend/tests/test_calc.py` | UI preview and API preview error tests. |
| Diary snapshot | `backend/tests/test_diary_snapshot.py` | API create/edit/delete snapshot regression. |
| Sync | `backend/tests/test_sync.py` | Future Scope only for v1. |
| Profile API | None direct | GET/PUT/preview validation, 401, 404, network/error mapping. |
| Food API | None direct | CRUD, search, duplicate, net carbs, validation, delete/archive. |
| Diary API | None direct | Create/list/week/update/delete validation and date behavior. |
| Frontend | None visible | E2E, component, accessibility, mobile/RTL visual tests. |
| Online network errors | None visible | API down, timeout, 401, 404, 422, 5xx, no local queue. |

