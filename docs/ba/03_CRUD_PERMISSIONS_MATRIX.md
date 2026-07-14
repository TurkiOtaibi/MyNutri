# CRUD and Permissions Matrix

## Actors

| Actor | Status | Notes |
|---|---|---|
| Single owner/user | Confirmed | Personal-use app protected by one token. |
| System | Confirmed | Computes targets, snapshots, totals, validation, and online API responses. |
| Guest | Blocked for protected APIs | Protected routers require bearer token unless token is configured empty. |
| Admin | Not in v1 | No admin role. |
| Moderator | Not in v1 | No moderation role. |
| Non-owner | Not applicable | No multi-user ownership model in v1. |
| Additional people/profiles | Future Scope | D-016 keeps v1 scoped to one Profile model. |

## Permission Enforcement

Protected API areas:
- `/profile`
- `/foods`
- `/diary`

Future Scope:
- `/sync` exists in code but is not a v1 product requirement.
- Multi-profile/person switching is not a v1 product requirement.
- Profile reset/delete is not a v1 product requirement.
- Offline page, service-worker API caching, IndexedDB personal data caches, and cached-read fallbacks are not v1 source-of-truth behavior.

Public:
- `/health`

## Profile CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | v1 behavior | Current code alignment |
|---|---|---:|---:|---|---|
| Create/update | Single owner | Yes | Yes | Save only after successful API response; no local queue; repeated submit sends one request; failed save keeps visible input for retry. | Current UI can queue failed save; needs alignment. |
| Read detail | Single owner | Yes | Yes | Load fresh online data, show missing profile state, or show exact D-022 profile read-failure copy. | Partial. |
| Preview targets | Single owner | Yes | Yes | Validate profile bounds before showing reliable preview. | Current validation ranges need alignment. |
| Delete/reset | Not in v1 | N/A | No | Out of scope for v1; correct data by editing existing profile fields. | Missing by design per D-017. |

## Food CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | v1 behavior | Current code alignment |
|---|---|---:|---:|---|---|
| Create | Single owner | Yes | Yes | Create Food only from standalone `/foods/new` after API success; nutrition source of truth is per 100g/per 100ml; block current-catalog duplicates; repeated submit sends one request. | Current UI/form/model need D-024/D-025 alignment. |
| Read list | Single owner | Yes | Yes | `/foods` shows current catalog Foods only. Deleted Foods are absent. No archived/status filters. Read failure shows exact D-022 Foods list message. | Current UI needs D-024 list column/card alignment. |
| Read detail | Single owner | Yes | Yes | `/foods/{id}` shows Food details, full long Food name, and optional nutrients. 404/stale state returns detail read-failure or stale-item behavior. Old Diary uses snapshot, not Food detail. | Current inline detail behavior needs route/read-error alignment. |
| Update | Single owner | Yes | Yes | `/foods/{id}/edit` reuses Add Food structure in edit mode; updates after API success; duplicate check applies to current catalog Foods; stale food edit is rejected. | Duplicate/network/stale/route alignment missing. |
| Delete | Single owner | Yes | Yes | Confirmation dialog shows Food name and permanent-delete warning. Confirm permanently hard deletes from catalog after successful API response; cancel makes no change; repeated confirm sends one request. | Current code hard deletes but lacks required confirmation/copy and snapshot verification. |
| Archive/restore | Not in v1 | N/A | No | Food archive/inactive lifecycle is Future Scope and superseded by D-025. Do not use `is_active`, `archived_at`, archived status, or Active/Archived filters. | Earlier BA archive assumptions are superseded. |

Food deletion and dependency behavior:
- Delete is permanent hard delete from the Food catalog.
- Deleted Foods disappear from `/foods`, Food search results, and future Diary food selection.
- Existing Diary entries remain unchanged because they use frozen nutrition snapshots.
- Deleted Foods do not block duplicate creation.
- If the user wants the same Food again later, they create it again as a new Food.
- No restore behavior exists in v1.

## DiaryEntry CRUD

| Action | Allowed actor | Server-enforced? | UI exposed? | v1 behavior | Current code alignment |
|---|---|---:|---:|---|---|
| Create by servings | Single owner | Yes | Yes | Request payload `{ entry_date, food_id, log_mode: "servings", quantity }`; Food must exist in current catalog; date today/past; quantity 0.01-50 default units/servings. | Range/future-date/log_mode/default-unit alignment missing. |
| Create by grams | Single owner | Required | Missing | Request payload `{ entry_date, food_id, log_mode: "grams", quantity }`; selected Food must support gram calculation from its nutrition basis/default unit data; quantity 1-5000 grams. | Missing. |
| Read day/list | Single owner | Yes | Yes | Online read; show entries, empty state, or exact D-022 Diary day read-failure copy. | Partial; error copy needs alignment. |
| Read detail | Single owner | Yes | Not separately exposed | API can read entry; no dedicated v1 screen required. | Partial. |
| Update quantity | Single owner | Required | Missing | Request payload `{ quantity }` only; edit quantity only in original `log_mode`; no food/date/log_mode/per-serving snapshot edit; stale entry rejected. | Backend currently allows broader update; UI missing. |
| Delete | Single owner | Yes | Yes | Requires confirmation showing food name/date; delete online only after API success; no local queue; repeated confirm sends one request; stale entry rejected. | Confirmation and online-only behavior need alignment. |

Diary dependency behavior:
- Food edit/delete does not change existing diary entries.
- Snapshot calculated totals remain the historical source for diary totals.
- Serving-mode `quantity` means serving count; gram-mode `quantity` means grams per D-021.
- Future dates are blocked for create and quantity edit.

## Future Scope: SyncOperation / QueuedMutation CRUD

Offline-first is removed from v1. Rows below document current code evidence only.

| Action | v1 status | Evidence | Required v1 disposition |
|---|---|---|---|
| Queue local mutation | Future Scope | `frontend/lib/db.ts` | Do not queue failed writes. |
| Read pending count | Future Scope | `getPendingMutationCount`, `SyncStatus` | Do not expose pending sync state in v1. |
| Push operations | Future Scope | `POST /sync/push`, `flushQueuedMutations` | Exclude from v1 behavior. |
| Pull server state | Future Scope | `GET /sync/pull`, `pullServerState` | v1 loads via normal online API routes. |
| Sync rejection/conflict handling | Future Scope | `sync.py` | Not a v1 requirement. |
| Offline page/cached read fallback | Future Scope / alignment item | `frontend/app/offline/page.tsx`, `frontend/lib/db.ts`, `service-worker.js` | Do not present cached personal data as current after API read failure. |

## Remaining CRUD Alignment Items

1. Current Profile save fallback queues failed writes.
2. Current Food create/update/delete fallback queues failed writes.
3. Current Diary add/delete fallback queues failed writes.
4. Food archive fields are no longer required; any existing archive implementation plan is superseded by D-025.
5. Food delete currently hard deletes but lacks D-025 confirmation/copy and snapshot-after-delete verification.
6. Food standalone routes `/foods/new`, `/foods/{id}`, and `/foods/{id}/edit` are missing or need verification.
7. Food per-100g/per-100ml data model and default-unit fields are missing.
8. Gram-based Diary create and D-021 `log_mode` contract are missing.
9. Diary quantity-only edit UI is missing.
10. Backend Diary update allows more than v1 UI scope.
11. Diary delete confirmation showing food name/date may be missing.
12. Food `serving_grams` source-of-truth assumptions are superseded by D-025 default-unit model.
13. Long food name two-line truncation needs verification.
14. Cached-read fallbacks and offline page/metadata need alignment to online-only v1.
15. Duplicate-submit, stale item, retry, and accessibility behaviors need D-023 alignment.
