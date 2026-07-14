# Implementation Alignment Audit

This file separates implementation mismatches from BA readiness. Current code not matching BA does not by itself make BA not ready.

## Summary

| Area | Count |
|---|---:|
| Implementation alignment items found | 18 |
| Offline/sync current-code contradictions | 10 |
| Critical implementation alignment items | 5 |
| High implementation alignment items | 10 |
| Medium implementation alignment items | 3 |

## Alignment Items

| ID | Severity | Area | Evidence | Current behavior | Required v1 behavior |
|---|---|---|---|---|---|
| ALIGN-V2-001 | Critical | Profile failed write | `ProfilePage.tsx`, `frontend/lib/db.ts` | Failed save queues local mutation and shows local sync message. | Failed write must not save locally or queue. |
| ALIGN-V2-002 | Critical | Food failed write/delete | `FoodsPage.tsx`, `frontend/lib/db.ts` | Failed save/delete writes IndexedDB and queues mutation. | Failed write/delete must not save locally or queue. |
| ALIGN-V2-003 | Critical | Diary failed create/delete | `DiaryPage.tsx`, `frontend/lib/db.ts` | Failed add/delete mutates IndexedDB and queues mutation. | Failed write/delete must not save locally or queue. |
| ALIGN-V2-004 | High | Cached read fallback | `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `db.ts` | API read failure returns cached Profile/Foods/Diary/Week data. | Read failure must show connection error; cached data must not be source of truth. |
| ALIGN-V2-005 | High | Service worker cache | `frontend/public/service-worker.js` | Caches fetched GET responses and serves cached responses offline. | Static shell assets only; no personal API data as current. |
| ALIGN-V2-006 | High | Sync status UI | `SyncStatus.tsx`, `Providers.tsx` | Shows pending/syncing/offline status and flush button. | Pending sync states are Future Scope. |
| ALIGN-V2-007 | High | Sync API | `backend/app/api/router.py`, `backend/app/api/routes/sync.py` | `/sync/pull` and `/sync/push` mounted and mutate resources. | Sync push/pull is Future Scope for v1. |
| ALIGN-V2-008 | Medium | Offline page/copy | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx` | UI/metadata copy says app works offline and syncs changes. | Offline write/sync copy must not appear in v1. |
| ALIGN-V2-009 | Critical | Food archive fields | `backend/app/models.py`, migration, schemas | `Food` lacks `is_active` and `archived_at`. | Archive lifecycle requires both fields. |
| ALIGN-V2-010 | Critical | Food delete behavior | `backend/app/services/food.py`, `FoodsPage.tsx` | Delete hard deletes without confirmation. | Delete archives after confirmation. |
| ALIGN-V2-011 | High | Active food filtering | `list_foods`, `DiaryPage` food selector | No active filter because archive fields absent. | Active Foods list and Diary selector hide archived foods. |
| ALIGN-V2-012 | High | Duplicate food prevention | Food service/schema/DB | No active duplicate check. | Block active duplicate by normalized key. |
| ALIGN-V2-013 | High | Validation ranges | `backend/app/schemas.py`, UI forms | Ranges are looser/different than D-009/D-012. | Enforce v1 ranges and Arabic messages. |
| ALIGN-V2-014 | High | Net carbs | `services/food.py`, `services/diary.py`, `db.ts` | `fiber_g > carb_g` can produce negative net carbs. | Block `fiber_g > carb_g`. |
| ALIGN-V2-015 | High | Gram Diary logging | `backend/app/schemas.py`, `frontend/lib/types.ts`, `DiaryPage.tsx` | Only serving `quantity` exists. | Serving and gram modes required. |
| ALIGN-V2-016 | High | Diary edit scope | `backend/app/schemas.py`, `routes/diary.py`, `DiaryPage.tsx` | Backend can update date/food/quantity; UI lacks edit. | UI permits quantity-only edit; food/date/snapshot not editable. |
| ALIGN-V2-017 | High | Diary delete confirmation | `DiaryPage.tsx` | Delete button calls mutation directly. | Confirmation shows food name/date before API delete. |
| ALIGN-V2-018 | Medium | Long food names and serving label | `FoodsPage.tsx`, `globals.css` | No two-line ellipsis; UI label still grams-per-serving wording. | Two-line list/card truncation and D-019 label required. |

## Offline/Sync Current-Code Contradictions

Count: 10

1. Profile read falls back to cached IndexedDB data.
2. Food read/search falls back to cached IndexedDB data.
3. Diary day/week reads fall back to cached/offline-built data.
4. Profile failed save queues local mutation.
5. Food failed save/delete queues local mutation.
6. Diary failed add/delete queues local mutation.
7. Service worker caches fetched GET responses and serves cached responses.
8. `SyncStatus` exposes pending/sync/offline states.
9. `/sync/pull` and `/sync/push` remain mounted and active.
10. Offline page and metadata copy promise local data/offline sync behavior.

BA status:
These are implementation alignment items, not accepted v1 BA requirements.
