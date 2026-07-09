# BA Executive Summary

Reverse-engineered requirements package for the current myNutri codebase.

Mode: full  
Scope: entire repository, including backend, frontend, docs, tests, online API behavior, optional installable shell behavior, and previous QA audit outputs.  
Report-only: yes. No application code was changed.

## Product Summary

myNutri v1 is a personal Arabic-first RTL nutrition tracker defined as an online-only web system.

The current codebase implements a single-owner, single-profile system with:

- Profile and target calculation.
- Food catalog CRUD.
- Diary logging by serving quantity.
- Sunday-to-Saturday weekly summary.
- Nutrition snapshots for historical diary accuracy.
- Online API reads and writes for Profile, Foods, and Diary.
- Single-user token protection on API routes.

Product decision: offline-first behavior is removed from v1. IndexedDB caches, offline mutation queues, sync push/pull, stale cache states, conflict handling, and offline writes are Future Scope. v1 changes are saved only after a successful API response.

## Current Implementation Status

| Area | Status | Evidence | Confidence |
|---|---|---|---|
| Arabic-first RTL responsive shell | Confirmed | `frontend/app/layout.tsx`, `frontend/public/manifest.json`, `frontend/components/Providers.tsx` | High |
| Single-user auth | Confirmed | `backend/app/core/auth.py`, protected routers | High |
| Profile and target calculation | Confirmed | `backend/app/models.py`, `backend/app/services/calc.py`, `frontend/components/ProfilePage.tsx` | High |
| Food catalog CRUD | Confirmed | `backend/app/api/routes/foods.py`, `frontend/components/FoodsPage.tsx` | High |
| Diary logging by serving quantity | Confirmed | `backend/app/api/routes/diary.py`, `frontend/components/DiaryPage.tsx` | High |
| Diary nutrition snapshots | Confirmed | `backend/app/services/diary.py`, `backend/tests/test_diary_snapshot.py` | High |
| Weekly aggregation | Confirmed | `backend/app/services/aggregation.py`, `frontend/components/DiaryPage.tsx` | High |
| Online-only v1 data behavior | Required / not fully aligned with current code | Product decision in `13_PRODUCT_DECISIONS.md`; current offline/sync code exists in `frontend/lib/db.ts` and `backend/app/api/routes/sync.py` | High |
| Offline cache and sync queue | Future Scope / out of v1 | `frontend/lib/db.ts`, `backend/app/api/routes/sync.py`, `frontend/components/SyncStatus.tsx` | High |
| Multi-person profiles | Missing | No `person` table, no `person_id` on diary entries | High |
| Food archive/inactive lifecycle | Missing | No archive field; hard delete in `backend/app/services/food.py` | High |
| Gram-based diary logging | Missing | `DiaryEntryInput.quantity` is servings only | High |

## Product Areas Discovered

1. App Shell, Navigation, RTL, and optional installable shell.
2. Single-User Authentication.
3. Profile and Target Calculation.
4. Food Catalog.
5. Diary and Weekly Tracking.
6. Online Data Access and Network Error Handling.
7. Health/Infrastructure.
8. QA/Test Coverage.

## Entities and Resources Discovered

| Entity/resource | Type | Status | Evidence |
|---|---|---|---|
| Profile | Database entity | Confirmed | `backend/app/models.py`, `backend/app/schemas.py` |
| Food | Database entity | Confirmed | `backend/app/models.py`, `backend/app/schemas.py` |
| DiaryEntry | Database entity | Confirmed | `backend/app/models.py`, `backend/app/schemas.py` |
| NutritionSnapshot | JSON/value object | Confirmed | `backend/app/services/diary.py`, `backend/app/schemas.py` |
| NutritionTotals | Computed value object | Confirmed | `backend/app/schemas.py`, `frontend/lib/db.ts` |
| TargetResponse / TargetResult | Computed value object | Confirmed | `backend/app/services/calc.py`, `backend/app/schemas.py` |
| SyncOperation | API payload | Future Scope / out of v1 | `backend/app/api/routes/sync.py`, `frontend/lib/types.ts` |
| QueuedMutation | IndexedDB entity | Future Scope / out of v1 | `frontend/lib/db.ts`, `frontend/lib/types.ts` |
| Local cache stores | IndexedDB stores | Future Scope / not source of truth in v1 | `frontend/lib/db.ts` |

## Counts

| Metric | Count |
|---|---:|
| Product areas | 8 |
| Entities/resources | 9 |
| Features documented | 38 |
| User stories generated | 27 |
| CRUD gaps | 18 |
| Field/validation gaps | 42 |
| Open questions | 30 |

## Highest-Risk Requirement Gaps

1. Food delete is a hard delete without confirmation, while root Foods requirements require confirmation and archive/inactive behavior for used foods.
2. The app is implemented as single-profile, while some later planning context discusses multi-person profiles.
3. Required food numeric fields default to `0`, which can hide missing nutrition data.
4. Server validation/API errors are often treated like offline success and queued locally in the current code; v1 now requires no offline queue and no save without API success.
5. Net carbs can become negative because `fiber_g <= carb_g` is not enforced.
6. Gram-based diary usage is planned in Foods requirements but not implemented.
7. No custom Arabic field-level validation messages are defined.
8. No direct Food/Profile/Diary route validation test suite exists beyond calc and snapshot tests; existing sync tests are now future-scope evidence.
9. Online network error handling requirements need implementation alignment because current code can fall back to local cache/queue behavior.
10. Accessibility is partial: labels exist, but icon-only actions rely mostly on `title`.

## Readiness

The codebase is usable as a personal nutrition tracker, but requirements are not fully ready for implementation expansion until the open product decisions in `12_OPEN_QUESTIONS.md` are resolved.

Recommended next step: run the QA user-story coverage auditor against this `docs/ba` package, then revise the BA stories before implementation planning.
