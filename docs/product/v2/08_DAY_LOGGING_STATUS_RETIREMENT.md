# Day Logging Status Retirement

Status: Approved V2 implementation authority

## Decision

Day Logging Status is removed completely. myNutri has no complete/reopen day
commands, persisted day completion state, optimistic day-status versioning,
day-status history, or day-status command idempotency. This decision removes
and replaces former PD-015 and the deleted Plan 031 design, golden-vector,
approval, and verifier artifacts.

Diary entry create, update, and delete are owner-scoped operations over diary
entries. They require no `If-Match`, do not consult or mutate a day-status state
machine, and allow past, current, and future Diary dates. Create-time Principal
locking remains where required to serialize Target Plan binding. Food lookup,
captured measurement, immutable target binding, client UUID replay, current-Food
nutrition, and unrelated idempotency remain unchanged.

## API and presentation

The following operations are absent:

- `GET /diary/days/{diary_date}/status`
- `PUT /diary/days/{diary_date}/complete`
- `PUT /diary/days/{diary_date}/reopen`
- `GET /admin/users/{principal_id}/diary-days`

`DaySummary` contains no logging status, status version, entry count, or
completion timestamp. Day and week summaries derive solely from diary entries,
current Food nutrition, and Target Plan context. The frontend exposes no status
card, badge, label, icon, action, banner, toast, or reopen flow and introduces no
replacement status vocabulary.

## Data retirement

Revision `a6c81e4f2d90` permanently deletes only shared idempotency rows matching
both of these conditions:

- operation is `diary_day_complete` or `diary_day_reopen`;
- `resource_type` is `diary_day_status`.

It then drops `diary_day_status_history` before `diary_day_status`. The data is
not preserved or exported. Target Plan and all unrelated idempotency rows remain.
The revision is forward-only and fails closed on downgrade because deleted data
cannot be reconstructed faithfully.

Historical Alembic migrations remain immutable so clean databases can reproduce
the full base-to-head chain. Target Plan lifecycle behavior is now governed by
[the date-effective model](09_TARGET_PLAN_DATE_EFFECTIVE_MODEL.md). Migration-history
re-baselining, Nutrition Versioning changes, deployment, and production mutation
remain outside this implementation authority.
