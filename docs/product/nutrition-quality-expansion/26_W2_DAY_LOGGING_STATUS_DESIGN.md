# Wave 2 Day Logging Status Design Contract

**Status:** Draft — design/spike only; implementation not authorized
**Decision:** PD-015
**Design version:** 1.0-draft
**Repository baseline:** `89e83928406d90a38f383fff23752583fffee753`
**Calendar authority:** Backend `Asia/Riyadh` Diary calendar

## 1. Purpose and authority

This contract turns PD-015's public vocabulary into one reviewable implementation design:

- `unregistered`: the owner has not started or explicitly opened that Diary day;
- `partial`: the owner has activity for the day but has not explicitly completed it;
- `complete`: the owner explicitly declared the day complete.

Logging status is independent of Food nutrient coverage. A completed day can contain entries with partial nutrient coverage. Conversely, an entry with complete nutrient data never completes the day automatically.

The proposed contract makes an intentionally empty completed day zero-intake evidence for that date. It counts as a completed day for the PD-016 day-count threshold. Metric-specific analysis still applies its own coverage rule to non-empty days. This proposal becomes authoritative only when Product and Data/Analysis approve it in `26B_W2_DAY_LOGGING_STATUS_APPROVAL_REPORT.md`.

No application behavior is implemented by these documents.

## 2. Invariants

1. The authenticated `Principal` owns every status, command, entry, replay, and history row.
2. Public status is exactly `unregistered | partial | complete`.
3. Only an owner command can create `complete`; entries and migration never infer it.
4. A completed day is immutable to entry create/edit/delete until the owner reopens it.
5. Reopening is explicit and changes `complete` to `partial`, including an empty completed day.
6. Once a day has owner activity, deleting its last entry leaves it `partial`; it does not erase the audit fact that logging began.
7. An absent status row with legacy entries projects `partial`; an absent row without entries projects `unregistered`.
8. Future Diary dates cannot be completed, reopened, or mutated.
9. Past and current dates may be completed or reopened.
10. Each request captures one Backend `CalendarAuthority`; every date check and response in that request uses that snapshot.
11. A status transition and the affected Diary entry/snapshot mutation commit atomically or roll back together.
12. Admin access is read-only. No admin route may complete, reopen, or mutate an owner's status.
13. Incomplete and unregistered dates are missing evidence, never zero-intake evidence.
14. An explicitly empty completed date is zero-intake evidence and must be distinguishable from missing evidence.
15. All transport contracts originate in Backend OpenAPI and flow to the Frontend generated contracts; no handwritten transport DTO is permitted.

## 3. Current-state inventory at the pinned baseline

| Layer | Existing symbol/path | Baseline fact | Day-status delta |
| --- | --- | --- | --- |
| Ownership | `backend/app/models.py::Principal` and `PrincipalContext` | Diary access is Principal-scoped. | Add owner-bound status and history FKs; preserve not-found isolation. |
| Entries | `backend/app/models.py::DiaryEntry` | Rows bind `principal_id`, `entry_date`, snapshot, target provenance, quantity, meal, and timestamps. | Entry transactions must lock/update the day aggregate. |
| Entry API | `backend/app/api/routes/diary.py` | Owner GET/list, POST, PATCH, and DELETE exist; future create dates are rejected. | Add version precondition and completed-day conflict without changing snapshot semantics. |
| Entry service | `backend/app/services/diary.py::{create_entry,update_entry,delete_entry}` | Mutations commit Diary entry and nutrition snapshot together; create supports client UUID replay. | Preserve atomicity and client UUID behavior while adding a day lock/version. |
| Daily/weekly projection | `backend/app/schemas.py::{DaySummary,WeekSummary}` and `backend/app/services/aggregation.py` | Seven daily summaries expose totals, targets, provenance, coverage, and weekly totals. | Add status/version/entry count/analysis eligibility; do not convert missing days to zeros. |
| Calendar | `backend/app/core/calendar.py` and `CalendarAuthorityResponse` | `current_diary_date`, `calendar_timezone`, and `next_rollover_at` are server-authoritative. | Capture once per request; browser `new Date()` is never status authority. |
| Admin | `backend/app/api/routes/admin.py`, `backend/app/services/diary.py::admin_diary_page` | Admin Diary monitoring is bounded, owner-isolated, and GET-only. | Add bounded status projection only; no status write route. |
| Idempotency | `backend/app/models.py::IdempotencyRecord` and `backend/app/services/target_plans.py` | Principal + operation + key is unique; canonical hash, stored response, and conflict behavior exist. | Reuse this mechanism for complete/reopen commands. |
| Frontend orchestration | `frontend/components/DiaryPage.tsx` | Calendar/query/mutation/session orchestration and subject-change cancellation live here. | Keep command orchestration, cache invalidation, calendar snapshot, and focus restoration here. |
| Frontend feature | `frontend/features/diary/diary-summary.tsx`, `diary-entry-dialogs.tsx`, `diary-hooks.ts`, `diary-model.ts`, `diary.module.css` | Presentation, dialogs, model helpers, invalidation, and styling are isolated. | Put status presentation/copy in this boundary; keep business orchestration in `DiaryPage`. |
| Transport types | `frontend/lib/generated/openapi.ts`, projected through `frontend/lib/types.ts` | Backend OpenAPI is generated transport authority. | Generate status/command DTOs and map them to UI state; do not hand-author equivalents. |
| Tests | `backend/tests/test_diary_*`, `test_calendar_authority.py`, `test_admin_monitoring_performance.py`; Frontend Vitest/Playwright/StrictMode suites | Entry snapshot races, aggregation, calendar rollover, Principal isolation, admin GET, accessibility, and session behavior have foundations. | Add state, concurrency, migration, contract, UX, and analysis-consumer tests listed in section 13. |

There is no current status table, status field, complete/reopen route, status UI, or status implementation test.

## 4. Authoritative state model

### 4.1 Selected model

Use a persisted owner/date aggregate named `diary_day_status` plus deterministic legacy projection. This is preferred over a fully derived model because explicit completion, reopen history, optimistic concurrency, and intentionally empty completion cannot be reconstructed from entries.

The write model stores only `partial` or `complete`. `unregistered` is the canonical absence state. Projection is:

```text
status row complete                         -> complete
status row partial                          -> partial
no status row and one or more Diary entries -> partial (legacy compatibility)
no status row and no Diary entries          -> unregistered
```

Every new entry mutation materializes or updates the aggregate to `partial`. Migration creates no status row for historical dates. Therefore historical entry dates project `partial` but historical completion is never inferred.

### 4.2 State/event matrix

`v` is the current day version. Successful state-changing operations increment it exactly once. A no-change command does not increment it.

| Prior projection / condition | Event | Outcome | Owner message class | Analysis meaning |
| --- | --- | --- | --- | --- |
| no row, no entries (`unregistered`) | read | `unregistered`, version `0` | neutral | missing evidence; exclude |
| no row, legacy entries (`partial`) | read | `partial`, version `0` | incomplete | missing completion; exclude |
| `unregistered` | first entry create with version `0` | materialize `partial`, `v=1` | saved/incomplete | exclude |
| `partial` | additional entry | remain `partial`, `v+1` | saved/incomplete | exclude |
| `partial` | edit entry | remain `partial`, `v+1` | saved/incomplete | exclude |
| `partial`, entries > 1 | delete entry | remain `partial`, `v+1` | deleted/incomplete | exclude |
| `partial`, last entry | delete entry | remain persisted `partial`, count `0`, `v+1` | empty/incomplete | exclude; not zero evidence |
| `unregistered`, empty | explicit complete | persist `complete`, count `0`, `v=1` | empty-complete success | include as explicit zero-intake day |
| `partial`, any count | explicit complete | persist `complete`, `v+1` | complete success | include; apply metric coverage |
| `complete` | duplicate complete with current version and new key | no change | already complete | unchanged inclusion |
| `complete` | replay same key and request | replay stored response | complete success | unchanged inclusion |
| `complete` | explicit reopen | persist `partial`, `v+1` | reopened | exclude immediately |
| empty `complete` | explicit reopen | persist empty `partial`, `v+1` | reopened/empty | exclude; not zero evidence |
| `partial` or `unregistered` | reopen | no change | already open | exclude |
| `complete` | create/edit/delete entry | `409 DAY_ALREADY_COMPLETE` | reopen required | keep prior completed evidence |
| any | stale expected version | `409 DAY_VERSION_CONFLICT` | refresh and retry | no change |
| any | future-dated mutation | `422 FUTURE_DIARY_DATE` | future disabled | no evidence |
| past/current | valid command | same rules as above | contextual success | status-specific |
| any | transaction failure | full rollback | retryable error | prior state retained |

## 5. Ownership, authorization, time, and privacy

- Owner endpoints derive `principal_id` only from `PrincipalContext`; payloads never accept it.
- Queries use `(principal_id, diary_date)` and owner-scoped entry IDs. A cross-owner entry remains `404 RESOURCE_NOT_FOUND`, not `403`, to avoid existence disclosure.
- Admin may read status through the existing authenticated admin boundary. Admin responses contain status, date, entry count, timestamps, and version, but not idempotency keys or request hashes.
- Admin has no complete/reopen route. Attempts through owner routes operate on the admin's own Principal only and never accept a subject override.
- Logs include request ID, operation, result code, date, and opaque Principal ID. They exclude nutrition payloads and idempotency keys.
- One call to `diary_calendar_authority()` is captured before validation or locks. `requested_date > captured.current_diary_date` is rejected.
- A rollover after capture does not change the in-flight decision. The response returns the captured calendar metadata. The next request captures the new date.
- Frontend status queries and mutations include the authenticated subject/session identity in their cache ownership. Subject change aborts in-flight work, clears prior status data, closes dialogs, and never presents a prior subject's success.

## 6. Concurrency, idempotency, and transactions

### 6.1 Version and lock order

All day-affecting mutations use one PostgreSQL transaction and this order:

1. lock owner `principal` row;
2. resolve the date's Target Plan under existing target-plan ordering when entry creation needs it;
3. lock or atomically create `(principal_id, diary_date)` in `diary_day_status`;
4. acquire the existing Food namespace/Food locks when entry creation needs them;
5. lock affected `diary_entry` rows in stable UUID order;
6. read/create the Principal-scoped `idempotency_record` for complete/reopen;
7. write entry snapshot, status, history, and replay response;
8. commit once.

The implementation must reconcile current entry-service lock ordering to this one before adding the aggregate. It must not bolt a day lock after a Food lock and create an inversion.

Every owner mutation supplies the last observed day version. Entry routes use `If-Match: "day-{version}"`; complete/reopen request bodies use `expected_version` and also accept the same ETag. A mismatch returns the latest safe day projection in a `409` response. Version `0` represents absence.

### 6.2 Idempotency

- `PUT /diary/days/{date}/complete` and `PUT /diary/days/{date}/reopen` require `Idempotency-Key`.
- Operation names are `diary_day_complete` and `diary_day_reopen`.
- Canonical request hash covers operation, ISO date, expected version, and authenticated Principal ID.
- Same Principal + operation + key + hash replays the stored status and original HTTP status with `Idempotent-Replayed: true`.
- Same key with a different hash returns `409 IDEMPOTENCY_KEY_REUSED`.
- Different keys racing on one version serialize on the Principal/day locks: one changes state; the other receives `DAY_VERSION_CONFLICT`.
- Existing entry-create client UUID replay remains intact and participates in the same day transaction.

### 6.3 Two-session schedules

**Entry versus complete**

```text
A captures date/version v          B captures same date/version v
A locks Principal + day
B waits on Principal
A creates entry + partial history, commits v+1
B wakes, compares expected v to v+1, rolls back -> 409 DAY_VERSION_CONFLICT
```

**Delete versus complete**

```text
A locks Principal + day, completes and commits v+1
B wakes with expected v, rolls back -> 409 DAY_VERSION_CONFLICT
If B refreshed to v+1, delete is rejected -> 409 DAY_ALREADY_COMPLETE
```

**Duplicate command**

```text
A stores complete response under key K and commits
B uses K with identical canonical request -> exact replay, no version increment
B uses K with another request -> 409 IDEMPOTENCY_KEY_REUSED
```

**Subject change**

```text
Frontend aborts subject A request and clears A cache
Late A response is ignored by session signal
Subject B fetches with a distinct Principal-bound cache key
```

**Calendar rollover**

```text
Request captures 2026-08-15 before midnight
Clock crosses midnight while waiting for a lock
The request still validates against 2026-08-15 and reports that snapshot
The next request captures 2026-08-16; no sleeps or client clock are involved
```

## 7. Persistence and migration contract

### 7.1 Data dictionary

#### `diary_day_status`

| Column | Type | Null | Rule |
| --- | --- | --- | --- |
| `id` | UUID | no | server-generated primary key |
| `principal_id` | UUID | no | FK `principal.id ON DELETE RESTRICT` |
| `diary_date` | date | no | Backend Diary calendar date |
| `status` | text | no | check in `partial`, `complete` |
| `version` | bigint | no | check `version >= 1`; increments on every state/entry mutation |
| `entry_count` | integer | no | check `entry_count >= 0`; transactionally maintained and verified against entries in tests/preflight |
| `completed_at` | timestamptz | yes | non-null only when status is `complete` |
| `reopened_at` | timestamptz | yes | last explicit reopen time; independent of completion |
| `created_at` | timestamptz | no | UTC server time |
| `updated_at` | timestamptz | no | UTC server time |

Constraints and indexes:

- unique `uq_diary_day_status_principal_date (principal_id, diary_date)`;
- check `ck_diary_day_status_value`;
- check `ck_diary_day_status_completion`: complete requires `completed_at`, partial requires it null;
- index `ix_diary_day_status_principal_date_desc (principal_id, diary_date DESC)` for weekly/admin reads;
- composite owner FK conventions match existing Principal-owned tables.

#### `diary_day_status_history`

| Column | Type | Null | Rule |
| --- | --- | --- | --- |
| `id` | UUID | no | primary key |
| `day_status_id` | UUID | no | FK to status row, `ON DELETE RESTRICT` |
| `principal_id` | UUID | no | owner denormalization guarded by composite FK |
| `diary_date` | date | no | immutable event date |
| `from_status` | text | yes | null means public `unregistered`; otherwise partial/complete |
| `to_status` | text | no | partial/complete |
| `event_type` | text | no | entry_created, entry_edited, entry_deleted, completed, reopened |
| `day_version` | bigint | no | unique with day row; positive |
| `entry_id` | UUID | yes | affected entry for entry events |
| `actor_principal_id` | UUID | no | must equal owner for Wave 2 writes |
| `occurred_at` | timestamptz | no | UTC server time |
| `request_id` | text | yes | operational correlation, not a credential |

Unique `(day_status_id, day_version)` prevents duplicate history. Index `(principal_id, diary_date, day_version)` supports audit reads. No nutrition payload or idempotency key is stored in history.

### 7.2 Upgrade and backfill

| Phase | Fresh database | Populated database | Fail-closed check |
| --- | --- | --- | --- |
| Preflight | verify expected predecessor Alembic revision | additionally count invalid future dates/owner orphans; query only | abort on unexpected revision, orphan, or incompatible object |
| DDL | create two tables, constraints, indexes additively | same, with transactional DDL | abort if conflicting objects differ |
| Backfill | none | create no status/history rows | assert both new tables remain empty immediately after migration |
| Compatibility | new app projects absent+no entry unregistered | absent+legacy entries partial | assert no historical row is complete |
| Activation | deploy readers before writers or in one compatible release | same | startup preflight verifies tables/constraints before enabling commands |

The migration never scans entries to infer completion. It does not rewrite `diary_entry` or snapshots. Legacy days receive a row only on their first post-release mutation/command, at which point the transaction counts existing owner/date entries and establishes version `1`.

### 7.3 Rollback and downgrade

- Application rollback is safe while additive tables remain; the old application ignores them and existing Diary entries remain unchanged.
- During the rollback window, disable new status writers through normal deployment rollback, not by deleting data.
- Alembic downgrade must fail closed if either new table contains a row. It prints only aggregate counts and instructs the operator to restore the compatible application; it never drops status/history data automatically.
- A later, separately approved destructive retirement may export and verify history before table removal. That is outside this design.
- Migration failure rolls back DDL transactionally. A partially created or constraint-mismatched schema fails startup/preflight rather than serving a partial feature.

## 8. API and OpenAPI contract

### 8.1 Projections

Add these fields to `DaySummary` and each day in `WeekSummary`:

| Field | Type | Meaning |
| --- | --- | --- |
| `logging_status` | enum | public status |
| `logging_status_version` | integer >= 0 | optimistic concurrency version |
| `entry_count` | integer >= 0 | owner/date entry count |
| `analysis_eligible` | boolean | true only for complete |
| `completed_at` | datetime/null | explicit completion time |

Add `GET /diary/days/{date}/status -> DiaryDayStatusResponse`. Reads allow past/current/future projections, but future responses are `unregistered`, version `0`, commands disabled. The response includes `calendar.current_diary_date`, `calendar.calendar_timezone`, and `calendar.next_rollover_at` from one snapshot.

Admin may receive the same projection through a bounded additive GET under `/admin/users/{principal_id}/diary-days`; it remains read-only and Principal-isolated.

### 8.2 Commands

| Method/path | Body/header | Success | Important failures |
| --- | --- | --- | --- |
| `PUT /diary/days/{date}/complete` | `{"expected_version": n}`, `Idempotency-Key`, bearer auth | `200 DiaryDayStatusResponse` | 401, 409 stale/key reuse, 422 future/invalid |
| `PUT /diary/days/{date}/reopen` | same | `200 DiaryDayStatusResponse` | 401, 409 stale/key reuse, 422 future/invalid |
| existing entry POST/PATCH/DELETE | `If-Match: "day-n"` plus existing body | existing response plus `ETag`/day version | 409 complete/stale, existing 404/422 |

Pydantic models are named, `extra="forbid"`, and emitted by OpenAPI. The Frontend regenerates `frontend/lib/generated/openapi.ts`; `frontend/lib/types.ts` may narrow generated types but may not duplicate their transport shape.

### 8.3 HTTP/code classes and Arabic owner messages

| HTTP | Code | Arabic message | Retry class |
| --- | --- | --- | --- |
| 400 | `INVALID_IDEMPOTENCY_KEY` | `تعذر التحقق من الطلب. أعد المحاولة.` | new request key |
| 401 | `AUTHENTICATION_REQUIRED` | `انتهت الجلسة. سجّل الدخول للمتابعة.` | authenticate |
| 403 | `ADMIN_WRITE_FORBIDDEN` | `لا يملك المشرف صلاحية تعديل حالة يوم المستخدم.` | never from admin UI |
| 404 | `RESOURCE_NOT_FOUND` | `تعذر العثور على السجل المطلوب.` | refresh/navigation |
| 409 | `DAY_ALREADY_COMPLETE` | `أعد فتح اليوم قبل تعديل الوجبات.` | explicit reopen |
| 409 | `DAY_VERSION_CONFLICT` | `تغيّرت بيانات اليوم. حدّث الصفحة ثم حاول مجددًا.` | refetch |
| 409 | `IDEMPOTENCY_KEY_REUSED` | `تعارض الطلب مع محاولة سابقة.` | new request after refetch |
| 422 | `FUTURE_DIARY_DATE` | `لا يمكن تغيير حالة يوم مستقبلي.` | choose valid date |
| 422 | `VALIDATION_ERROR` | field-level Arabic validation | correct input |
| 500 | `DAY_STATUS_WRITE_FAILED` | `تعذر حفظ حالة اليوم. لم تُفقد بياناتك؛ حاول مجددًا.` | safe retry |

### 8.4 Closed JSON examples

Successful empty completion:

```json
{
  "date": "2026-08-15",
  "logging_status": "complete",
  "logging_status_version": 1,
  "entry_count": 0,
  "analysis_eligible": true,
  "completed_at": "2026-08-15T18:20:00Z",
  "calendar": {
    "current_diary_date": "2026-08-15",
    "calendar_timezone": "Asia/Riyadh",
    "next_rollover_at": "2026-08-15T21:00:00Z"
  }
}
```

Replay returns the identical document and status with header `Idempotent-Replayed: true`.

Stale conflict:

```json
{
  "detail": {
    "code": "DAY_VERSION_CONFLICT",
    "message_ar": "تغيّرت بيانات اليوم. حدّث الصفحة ثم حاول مجددًا.",
    "current": {
      "date": "2026-08-15",
      "logging_status": "partial",
      "logging_status_version": 8,
      "entry_count": 2,
      "analysis_eligible": false,
      "completed_at": null
    }
  }
}
```

Future rejection:

```json
{
  "detail": {
    "code": "FUTURE_DIARY_DATE",
    "message_ar": "لا يمكن تغيير حالة يوم مستقبلي.",
    "current_diary_date": "2026-08-15",
    "calendar_timezone": "Asia/Riyadh"
  }
}
```

The remaining closed response examples are:

```json
{
  "invalid_idempotency_key_400": {
    "detail": {"code": "INVALID_IDEMPOTENCY_KEY", "message_ar": "تعذر التحقق من الطلب. أعد المحاولة."}
  },
  "authentication_401": {
    "detail": {"code": "AUTHENTICATION_REQUIRED", "message_ar": "انتهت الجلسة. سجّل الدخول للمتابعة."}
  },
  "admin_write_403": {
    "detail": {"code": "ADMIN_WRITE_FORBIDDEN", "message_ar": "لا يملك المشرف صلاحية تعديل حالة يوم المستخدم."}
  },
  "not_found_404": {
    "detail": {"code": "RESOURCE_NOT_FOUND", "message_ar": "تعذر العثور على السجل المطلوب."}
  },
  "complete_conflict_409": {
    "detail": {"code": "DAY_ALREADY_COMPLETE", "message_ar": "أعد فتح اليوم قبل تعديل الوجبات."}
  },
  "key_reuse_409": {
    "detail": {"code": "IDEMPOTENCY_KEY_REUSED", "message_ar": "تعارض الطلب مع محاولة سابقة."}
  },
  "validation_422": {
    "detail": {"code": "VALIDATION_ERROR", "message_ar": "تحقق من بيانات الطلب.", "fields": {"expected_version": "يجب أن يكون رقم الإصدار صفرًا أو أكبر."}}
  },
  "write_failure_500": {
    "detail": {"code": "DAY_STATUS_WRITE_FAILED", "message_ar": "تعذر حفظ حالة اليوم. لم تُفقد بياناتك؛ حاول مجددًا.", "request_id": "req_example"}
  }
}
```

The future-date block above is the closed future `422` example. A rollover success has the ordinary success shape and echoes the single captured calendar even if the clock rolls over during lock wait; it never silently mixes calendar snapshots.

## 9. Daily, weekly, and analysis semantics

- Daily totals retain existing arithmetic. Status adds evidence meaning; it does not rewrite totals.
- Weekly payloads return all seven dates with status. `weekly_totals` must not be used by analysis as though partial/unregistered days were zeros.
- Future analysis consumers select only `analysis_eligible=true` days.
- A complete day with zero entries contributes exact zero intake and counts toward the four-complete-day threshold.
- A complete non-empty day counts toward the day threshold, while each metric additionally requires sufficient entry nutrient coverage under PD-013/PD-016.
- Partial and unregistered days contribute neither zero nor a denominator day.
- Reopening removes the day from analysis immediately; recomputation/versioning of later Analysis Snapshots belongs to Wave 3.
- Logging completion is not a claim that nutrient coverage, goals, or healthy eating are complete.

## 10. Arabic UX, accessibility, and responsive contract

### 10.1 Exact proposed copy

| State/action | Arabic copy |
| --- | --- |
| unregistered badge | `غير مسجل` |
| partial badge | `التسجيل غير مكتمل` |
| complete badge | `تم تسجيل اليوم` |
| complete action | `إنهاء تسجيل اليوم` |
| reopen action | `إعادة فتح اليوم` |
| empty confirmation title | `إنهاء يوم دون وجبات؟` |
| empty confirmation body | `سيُحتسب هذا اليوم المكتمل على أنه لم يُسجل فيه تناول غذائي. يمكنك إعادة فتحه لاحقًا.` |
| empty confirm button | `إنهاء اليوم دون وجبات` |
| populated confirmation | `تأكد من اكتمال وجباتك قبل إنهاء تسجيل اليوم.` |
| completed edit explanation | `أعد فتح اليوم قبل إضافة وجبة أو تعديلها أو حذفها.` |
| partial analysis note | `لن يُعامل هذا اليوم كاستهلاك صفري، ولن يدخل في التحليل حتى تنهي تسجيله.` |
| retry | `إعادة المحاولة` |

Product Owner approval of this exact copy is required before freeze.

### 10.2 Interaction

- Day header and compact week cells expose visible text plus a non-color status icon.
- Completing a populated day uses a confirmation dialog. Empty completion uses the stronger empty confirmation above.
- On success, close the dialog, announce through a polite live region, and focus the status heading. On failure, keep the dialog and focus the error/retry action.
- Editing a complete day opens a reopen confirmation; successful reopen restores focus to the originally invoked Add/Edit/Delete control, then performs no hidden mutation. The owner invokes the desired entry action again.
- Loading shows a status skeleton with `aria-busy`; it never flashes `unregistered` before data arrives.
- Initial error uses `role="alert"` and a retry button. Background refresh failure preserves the last verified state and labels it stale.
- Keyboard order follows date navigation, status heading/action, summary, then meal sections. Dialog focus is trapped and Escape cancels without state change.
- Screen-reader names include the full Arabic date and status. Live announcements do not repeat on React StrictMode remounts or idempotent replays.
- At widths 320, 360, 390, and 430 px, badge and action wrap beneath the date without horizontal scroll or clipped focus rings. Touch targets remain at least 44 by 44 CSS pixels.
- RTL visual order follows Arabic reading order; numeric dates/versions use `<bdi>` where exposed. No directional CSS assumes LTR.
- Future days show `غير مسجل` as projection with disabled status commands and the reason `لا يمكن إنهاء تسجيل يوم مستقبلي.`

## 11. Frontend architecture boundary

- `DiaryPage.tsx` owns calendar capture, active date, authenticated subject, status/week queries, complete/reopen mutations, cache invalidation, abort handling, and post-mutation focus requests.
- `frontend/features/diary/*` owns presentation, dialog composition, Arabic labels, domain mapping helpers, and CSS.
- `invalidateDiary` expands to invalidate entry, week, and status projections atomically after mutation.
- Generated OpenAPI types are the transport authority. A small domain mapping may turn the generated enum into display metadata, but it must remain exhaustive and compile-fail on a new server status.
- Complete/reopen mutation state is separate from entry mutation state so a failure cannot show the wrong retry action.
- Session/subject identity is part of all query ownership. Late responses after logout or subject change are ignored.

## 12. Golden vectors

`26A_W2_DAY_LOGGING_STATUS_GOLDEN_VECTORS.json` is a versioned, seeded state-machine corpus. It covers untouched and legacy projection, first/additional/edit/delete entry behavior, last deletion, empty/populated completion, reopen, completed-day write blocking, replay/key conflict, stale versions, two-session winners, past/future dates, and rollover.

`tools/verify_w2_day_logging_status_vectors.py` is a standard-library reference oracle. It validates and replays the corpus and must never be imported by Backend or Frontend application code.

## 13. Acceptance and future implementation test matrix

| Requirement | Positive oracle | Negative/boundary oracle | Required suite |
| --- | --- | --- | --- |
| Three-state projection | absent/empty, legacy entries, persisted states match vectors | unknown persisted value rejected by DB/OpenAPI | unit + Postgres |
| Empty completion | explicit command produces complete/count 0 | migration never creates it | service + migration + contract |
| Entry transitions | first/add/edit/delete update partial/version | completed-day writes 409; stale write rolls back | Postgres service + API |
| Atomic snapshots | entry, snapshot, status, history commit together | injected failure leaves all prior values | Postgres transaction |
| Concurrency | deterministic two-session schedules | no lost update/deadlock; second writer 409 | Postgres concurrency without sleeps |
| Idempotency | same key/hash exact replay | same key/different hash conflict; different key stale conflict | API + Postgres |
| Principal isolation | owner reads/writes own date | cross-owner entry/status returns 404; cache separated | Backend + Playwright sessions |
| Admin boundary | bounded GET shows status | every admin write path absent/403; GET does not mutate | backend contract/query count |
| Calendar | captured current/past succeeds | future 422; rollover uses one snapshot | unit with injected clock + API |
| Migration | fresh/populated upgrade; legacy entries project partial | zero backfilled complete/status rows; invalid predecessor fails | Alembic PostgreSQL |
| Rollback | old app reads entries with additive tables | downgrade refuses non-empty tables; no data loss | migration rollback gate |
| OpenAPI | named schemas/enums/examples generated | generic object, missing field, handwritten duplicate fail | contract drift + architecture |
| Weekly projection | seven statuses and versions | incomplete days not analysis zeros | aggregation + contract |
| Analysis eligibility | complete included; empty complete exact zero | partial/unregistered excluded; low metric coverage qualified | future Wave 3 consumer tests |
| Arabic UX | exact approved copy and success focus | error/retry, stale refresh, cancel, future disabled | Playwright RTL |
| Accessibility | keyboard, dialog trap, live region, labels | no color-only state, duplicate announcements, focus loss | axe + Playwright + StrictMode |
| Responsive | 320/360/390/430 snapshots and interactions | no overflow/clipping or sub-44px action | Linux visual/Playwright |
| Subject change | abort/clear/refetch for new Principal | late prior response cannot render/announce | two-session Playwright |

Mutation evidence must prove the gates fail when: a migration marks legacy days complete; a status enum value is removed; the entry transaction omits status/history; expected-version checks are bypassed; Admin gains a write route; partial days enter analysis; or generated contracts drift.

## 14. PD-015 traceability

| PD-015 clause | Model | API | UI | Verification |
| --- | --- | --- | --- | --- |
| `unregistered | partial | complete` | absence/partial/complete projection | generated enum in daily/weekly/status responses | exhaustive Arabic badges | vectors + OpenAPI + architecture |
| one entry is not complete | entry writes materialize partial | entry response/status remains partial | incomplete message | transition/Postgres/Playwright |
| explicit completion | persisted command transition/history | idempotent complete endpoint | confirmation and focus | service/API/E2E |
| intentionally empty complete | complete row with count 0 | response eligible true/count 0 | stronger Arabic confirmation | vector/migration/analysis/E2E |
| incomplete is not zero | partial/unregistered excluded | explicit `analysis_eligible=false` | explanatory note | aggregation/future consumer tests |
| strong analysis uses complete days | eligibility derives only from complete | daily/weekly field | complete badge, no analysis claim | future Wave 3 tests |

## 15. Freeze gate and implementation handoff

The four Plan 031 artifacts may be circulated for review. Implementation remains prohibited until the approval report contains all six named role approvals and `Decision status: Frozen for implementation`.

Any approval that changes edit/reopen semantics, empty-complete analysis, the persisted model, Principal ownership, or concurrency requires updating the design, vectors, oracle replay, and approval report before freeze. A Draft or partial approval cannot authorize migrations or source changes.
