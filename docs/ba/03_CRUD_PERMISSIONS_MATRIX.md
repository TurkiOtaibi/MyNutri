# CRUD and Permissions Matrix

## Actors

| Actor | Status | Notes |
|---|---|---|
| Single owner/user | Confirmed | The app is personal and protected by one token. |
| System | Confirmed | Computes targets, snapshots, totals, and online API responses. |
| Guest | Blocked for protected APIs | Protected routers require bearer token unless token is configured empty. |
| Admin | Missing | No admin role exists. |
| Moderator | Missing | No moderation role exists. |
| Non-owner | Not applicable/currently missing | No multi-user ownership model exists. |

## Permission Enforcement

Protected routers:

- `/profile`
- `/foods`
- `/diary`
- `/sync` exists in code but is out of scope for v1 online-only product behavior.

Evidence: each router has `dependencies=[Depends(require_single_user)]`.

Public router:

- `/health`

## Profile CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | Evidence | Gaps |
|---|---|---:|---:|---|---|
| Create | Single owner | Yes, via token | Yes, save profile | `PUT /profile`, `ProfilePage` | No explicit create vs update UX distinction; v1 must not queue offline profile saves |
| Read detail | Single owner | Yes | Yes | `GET /profile` | 404 empty-profile behavior not documented in UI |
| Read list | N/A | N/A | N/A | Single row only | Multi-profile missing |
| Update | Single owner | Yes | Yes | `PUT /profile` | No custom Arabic validation errors |
| Delete | Missing | N/A | No | No route | Decide whether reset/delete profile is needed |
| Archive/restore | Missing | N/A | No | N/A | Not needed for current personal v1 |

## Food CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | Evidence | Gaps |
|---|---|---:|---:|---|---|
| Create | Single owner | Yes, token + schema | Yes | `POST /foods`, `FoodsPage` | Duplicate prevention missing; validation errors weak; v1 requires no offline queued create |
| Read list | Single owner | Yes | Yes | `GET /foods`, `FoodsPage` | No pagination; no archive filter |
| Read detail | Single owner | Yes | Partial inline UI | `GET /foods/{id}`, inline details | Dedicated detail route not used |
| Update | Single owner | Yes | Yes | `PUT /foods/{id}`, edit form | Duplicate prevention missing; v1 requires no offline queued update |
| Delete | Single owner | Yes | Yes | `DELETE /foods/{id}`, delete icon | No confirmation; hard delete only; v1 requires no offline queued delete |
| Archive/restore | Missing | No | No | No model field | Required by root Foods decisions for used foods |
| Update any/delete any | Same as single owner | Token only | Yes | Single-user app | No ownership checks because no owners |

Food dependency behavior:

- Current hard delete removes `food`.
- `diary_entry.food_id` becomes `NULL` at DB level.
- Diary nutrition remains because `nutrition_snapshot` is stored.

## DiaryEntry CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | Evidence | Gaps |
|---|---|---:|---:|---|---|
| Create | Single owner | Yes | Yes | `POST /diary`, add meal form | Gram mode missing; no profile/person scope; v1 requires no offline queued entry |
| Read list/day | Single owner | Yes | Yes | `GET /diary?entry_date=`, day view | No pagination |
| Read detail | Single owner | Yes | Not separately exposed | `GET /diary/{entry_id}` | No UI detail route |
| Update | Single owner | Yes | No | `PUT /diary/{entry_id}` | Backend capability not covered by UI/stories |
| Delete | Single owner | Yes | Yes | `DELETE /diary/{entry_id}` | No confirmation; delete is hard; v1 requires no offline queued delete |
| Archive/restore | Missing | N/A | No | N/A | Not confirmed |

## Future Scope: SyncOperation / QueuedMutation CRUD

Offline-first is removed from v1. The rows below document current code evidence only; they are not v1 product requirements.

| Action | v1 status | Evidence | Notes |
|---|---|---|---|
| Queue local mutation | Out of scope for v1 | `frontend/lib/db.ts` | No changes should be queued offline in v1. |
| Read pending count | Out of scope for v1 | `getPendingMutationCount`, `SyncStatus` | Pending sync states are Future Scope. |
| Push operations | Out of scope for v1 | `POST /sync/push`, `flushQueuedMutations` | Conflict/replay behavior is Future Scope. |
| Pull server state | Out of scope for v1 | `GET /sync/pull`, `pullServerState` | v1 should load fresh data from normal API routes. |
| Delete accepted local operations | Out of scope for v1 | `bulkDelete` accepted IDs | Future Scope only. |

## CRUD Gaps

1. Food delete confirmation missing.
2. Food used-vs-unused delete decision missing.
3. Food archive/inactive DB/API field missing.
4. Food restore behavior not defined.
5. Food duplicate prevention missing.
6. Food category/brand/source CRUD intentionally missing/out of scope.
7. Profile delete/reset not defined.
8. Multi-profile/person CRUD missing despite later planning context.
9. Diary update API exists but UI/story scope is unclear.
10. Diary delete confirmation missing.
11. Diary person ownership/scope missing.
12. Diary future-date policy missing.
13. Current offline queue/sync behavior must be removed, disabled, or deferred for v1.
14. Online connection-error states are missing or unclear for Profile, Foods, Diary, and Week reads/writes.
15. Invalid/server-rejected data must not be saved locally or queued.
16. API authorization error UI missing.
17. Local cached personal data must not be treated as a v1 source of truth.
18. Pagination/large dataset behavior missing for foods and diary.
