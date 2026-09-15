# Target Plan Date-Effective Model

Status: Approved V2 implementation authority

## Decision

Target Plans are immutable, dated calculation revisions. They have no mutable
lifecycle status and no active, scheduled, pending, closed, or superseded state.
For a requested Diary date, the authoritative plan is the canonical
revision at the greatest `effective_from` not later than that date.

One or more future effective points may exist. Each
`(principal_id, effective_from)` has immutable revisions numbered from 1; the
greatest revision is canonical for that effective point. A same-date change
inserts revision N+1 and preserves every older revision. Target Plan rows cannot
be updated or deleted by normal application behavior.

Writes are accepted only when `effective_from` is the database-derived current
Riyadh Diary date or later. The Backend captures that date after locking the
Principal and Profile and checks it again before commit. A request that crosses
the Riyadh date boundary and has become historical fails and rolls back.
Historical reads remain valid for any date.

## Data ownership and calculation truth

`Profile` is the latest confirmed preference/input state. A `TargetPlan` is the
immutable dated calculation result produced from confirmed inputs. Target Plan
calculation documents preserve the calculated result. Nutrition formulas and
Registry content are protected by the current rules-manifest fingerprint and
preview hash rather than persisted semantic version numbers.

The live Target Plan row contains only `id`, `principal_id`, `profile_id`,
`effective_from`, `revision`, `calculation_document`, and `created_at`. The
database enforces direct calculation-document shape, positive
revisions, uniqueness of `(principal_id, effective_from, revision)`, owner-safe
Profile and Diary references, and a resolver index ordered by Principal,
effective date, revision, and identifier.

## Diary binding

`DiaryEntry.target_plan_id` is the nullable authoritative entry-level binding;
there is no separate target-provenance state. Past Diary bindings are immutable.
Today and future are
editable: after a new effective point or revision is inserted, the same atomic
transaction recomputes all eligible Diary bindings from that date up to, but not
including, the next distinct effective point. The update is not limited to rows
that referenced the immediately preceding revision.

Principal locking serializes Target Plan writes with Diary creation. The
database binding guard rejects cross-owner plans, non-canonical revisions, and
omitting an applicable canonical plan on a new Diary row. Null is accepted only
when no plan applies to the entry date.

## No-plan behavior

Resolution returns the canonical Target Plan or null. It never substitutes
Profile inputs or a legacy transition snapshot. A Principal with no applicable
plan receives null plan and targets. A first future plan updates the latest
confirmed Profile immediately, but dates before `effective_from` remain without
targets. Diary writes for those dates succeed with a null binding.

## Public API and transaction

The complete public Target Plan API is:

- `POST /target-plans`
- `GET /target-plans`
- `GET /target-plans/current?date=YYYY-MM-DD`

The write operation requires `Idempotency-Key`, an explicit `effective_from`, a
confirmed preview hash, and the existing safety validation. It locks Principal
then Profile, creates the immutable revision, rebinds eligible Diary rows,
updates Profile, completes idempotency, rechecks the Riyadh date, and commits
once.

New writes use operation namespace `target_plan.write`. Completed historical API
`target_plan.activate` and `target_plan.replace` records remain replayable only
when the submitted request is equivalent and references an owned plan at the
same effective date. Replay reconstructs the current response from Target Plan
rows and never exposes the stored lifecycle response JSON directly. This replay
adapter does not provide legacy Target data fallback. Ambiguous,
invalid, or conflicting key reuse fails closed.

Both GET operations and Target Plan resolution used by Profile, admin, Diary,
and week summaries are pure reads. They perform no lifecycle DML, flush, commit,
or lifecycle row lock. The week resolver loads bounded canonical revisions once
and resolves the seven dates in memory.

## Contract retirement

These operations are absent:

- `POST /target-plans/activate`
- `POST /target-plans/pending/replace`
- `GET /target-plans/pending`

Public Target Plan contracts expose no lifecycle status, effective period,
activation/closure/supersession metadata, lifecycle links, semantic Nutrition
versions, or target provenance. History is ordered
by `effective_from DESC, revision DESC, id DESC`. The top-level
`WeekSummary.targets` field is absent; each `DaySummary.targets` is the
authoritative date-specific target.

## Migration and rollback boundary

Revision `b7d42e9a1c36`, parent `a6c81e4f2d90`, performs the coordinated hard
cutover. It validates existing ownership, lineage, calculation, Diary,
idempotency, and extension dependencies; backfills revisions from valid
same-date replacement chains; rebinds only current/future Diary rows; replaces
the protection triggers; and removes lifecycle schema. Historical Alembic
revisions and legacy idempotency rows remain unchanged.

Revision `c8e53f0b2d47`, parent `b7d42e9a1c36`, adds direct calculation-document
shape integrity, drops semantic Nutrition version columns, replaces the Diary
binding guard with target-plan-only canonical rules, removes Diary provenance,
and drops empty legacy transition-snapshot schema. Historical calculation JSON
and Target Plan API idempotency rows remain unchanged.

Both cutovers are forward-only. They cannot synthesize the removed lifecycle
state, semantic version claims, legacy target documents, or Diary provenance.
Recovery requires the matching
pre-cutover database restore and application revision; downgrade is rejected.
