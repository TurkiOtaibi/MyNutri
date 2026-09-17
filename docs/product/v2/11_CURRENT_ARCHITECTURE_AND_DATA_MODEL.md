# Current architecture and data model

Status: current architecture and data authority.

## System shape

myNutri has a Next.js Arabic/RTL frontend, FastAPI Backend, PostgreSQL schema
managed by Alembic, and Supabase Auth. Personal API behavior is online-only. The
PWA caches only the static shell. The generated OpenAPI contract is the frontend
API boundary.

## Runtime entities and ownership

There are six persisted application entities:

| Entity | Scope and purpose |
|---|---|
| `Principal` | Durable authenticated owner and `user`/`admin` authorization identity |
| `Profile` | One per Principal; latest confirmed calculation inputs/preferences |
| `TargetPlan` | Principal-owned immutable dated calculation revision |
| `IdempotencyRecord` | Principal/operation/key-scoped replay and atomic completion record |
| `Food` | Global shared catalog row; Admin-created/updated/deleted |
| `DiaryEntry` | Principal-owned consumed Food measurement and optional TargetPlan binding |

Database ownership constraints prevent a Diary entry from referencing another
Principal's TargetPlan and prevent a TargetPlan from referencing another
Principal's Profile. Food is deliberately global. Private routes derive the owner
from `PrincipalContext`; clients do not submit another user's Principal ID.

## Profile and TargetPlan

Profile is latest confirmed input, not historical target truth. A TargetPlan stores
`id`, `principal_id`, `profile_id`, `effective_from`, positive `revision`, immutable
`calculation_document`, and `created_at`. The document is an object containing an
object-valued `target_result`; historical embedded metadata remains inert.

For date D, resolution selects the row for the Principal with the greatest
`effective_from <= D`, then greatest revision, then identifier. Same-date writes
insert revision N+1. Writes are allowed only for the database-derived Riyadh today
or future; reads may resolve any date. GET resolution is pure read.

No applicable plan returns `plan = null` and `targets = null`. Profile and a legacy
snapshot never substitute. A first future plan updates Profile immediately while
earlier dates remain without targets.

## Diary binding and Food truth

`DiaryEntry.target_plan_id` is nullable. Past bindings are immutable. Today/future
eligible rows are rebound transactionally when a new canonical TargetPlan changes
their effective interval. Database protection enforces same-owner canonical binding.

Diary entries store Food ID, date, meal, quantity, and captured unit type/amount/basis/
label. They do not store nutrition snapshots. Totals use current Food nutrition and
the captured consumed measurement. `food_id` is non-null with `ON DELETE CASCADE`.
Deleting one global Food therefore deletes every referencing Diary entry across all
Principals atomically. TargetPlans and unrelated Diary entries remain.

## Transactions and locking

- TargetPlan write: Principal row lock, Profile row lock, same-date revision lock,
  insert revision, eligible Diary row locks/rebinding, Profile update, idempotency
  completion, Riyadh date recheck, one commit.
- Diary create/update/delete: Principal lock for target binding, shared Food namespace
  advisory protection, relevant Food/Diary locks, response construction while
  protected, one commit.
- Food create/update/delete: Principal authorization/lock where applicable, exclusive
  Food namespace advisory lock for mutation, Food row lock for update/delete, one commit.

This order serializes plan/Diary and Food/Diary races without weakening database FKs.

## Idempotency

TargetPlan writes use `target_plan.write` with `Idempotency-Key`, canonical request
hash, in-progress/completed state, resource reference, and replay response. Historical
`target_plan.activate` and `target_plan.replace` records remain replayable through a
strict adapter that validates legacy-equivalent hashes and reconstructs the current
response from the referenced TargetPlan. Stored legacy response JSON is never returned
directly; ambiguous or conflicting reuse fails closed.

Diary client UUID replay remains separate. Retired Day-status idempotency is absent.

## API and navigation

Current Backend route families are account (`/me`, `/calendar`), Profile, Target Plans,
Nutrition Registry, Foods, Diary, Admin user monitoring, and health. Foods expose
exactly GET/POST `/foods`, GET `/foods/picker`, and GET/PUT/DELETE `/foods/{food_id}`.
`GET /foods` is paginated. The frontend canonical pages are Diary, Foods and Food
detail/create/edit, Profile, Admin user monitoring, auth, and offline shell. There is
no `/admin/foods` route.

## Migration and recovery

The sole Alembic head is `d9f64a1c3e58`. Historical migrations remain immutable and
reconstruct the schema. Destructive cutovers are forward-only: real rollback after
removed schema or data requires a matching pre-cutover database restore and compatible
application revision, not a synthesized downgrade.

## Explicitly absent

There is no Day Logging Status, complete/reopen command, TargetPlan lifecycle state,
pending plan, semantic Nutrition version, legacy Target transition snapshot/Profile
fallback, Diary target provenance, Food Archive/Restore, separate Admin Food UI, Sync
route/queue, Food V3 public schema, dual-array Food response, uncategorized sentinel,
or `/admin/foods` compatibility route.
