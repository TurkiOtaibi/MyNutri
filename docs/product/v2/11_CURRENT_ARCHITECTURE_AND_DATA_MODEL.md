# Current architecture and data model

Status: current architecture and data authority.

## System shape

myNutri has a Next.js Arabic/RTL frontend, FastAPI Backend, PostgreSQL schema
managed by Alembic, and Supabase Auth. Personal API behavior is online-only. The
PWA caches only the static shell. The generated OpenAPI contract is the frontend
API boundary.
Labs is a standalone domain. Its medical personal reads/writes follow the same
online-only/static-shell isolation and do not call the nutrition engine.

## Runtime entities and ownership

There are seven persisted application entities:

| Entity | Scope and purpose |
|---|---|
| `Principal` | Durable authenticated owner and `user`/`admin` authorization identity |
| `Profile` | One per Principal; latest confirmed calculation inputs/preferences |
| `TargetPlan` | Principal-owned immutable dated calculation revision |
| `IdempotencyRecord` | Principal/operation/key-scoped replay and atomic completion record |
| `LabResult` | Principal-owned entered laboratory facts; private backend persistence |
| `Food` | Global shared catalog row; Admin-created/updated/deleted |
| `DiaryEntry` | Principal-owned consumed Food measurement and optional TargetPlan binding |

Database ownership constraints prevent a Diary entry from referencing another
Principal's TargetPlan and prevent a TargetPlan from referencing another
Principal's Profile. Food is deliberately global. Private routes derive the owner
from `PrincipalContext`; clients do not submit another user's Principal ID.
Catalog tests, categories, panels, statuses, reference zones, canonical values
and medical-rule versions are not database entities.

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
Sex is immutable after the first successful Profile save. Profile retains its
nutrition age 10–100 validation; Labs separately requires age >=18 on each test
date. A DOB update is rejected atomically if it invalidates any stored adult Labs
history. A successful change invalidates Labs queries for fresh interpretation.

## Labs persistence

`LabResult` stores `id`, `principal_id`, `test_key`, `test_date`, `entered_value`,
`entered_unit`, and timezone-aware `created_at`/`updated_at`. Entered values use
unscaled `NUMERIC`; PostgreSQL preserves fractional trailing zeros and enforces
finite nonnegative values and normalized text length at most 128. Test/unit keys
are nonempty strings bounded to 64 characters. Ownership uses `ON DELETE RESTRICT`.
The unique B-tree on `(principal_id, test_key, test_date)` also supports scoped
reverse date scans without a separate descending index. Current interpretation,
reference ranges, and canonical values are not stored authoritative facts.
Time-dependent date validation and medical catalog rules belong to the backend.
Direct table privileges for `PUBLIC`, `anon`, and `authenticated` are revoked.

The immutable packaged `backend/app/labs/catalog.v1.json` owns exactly 51 tests,
15 categories and 7 selection-only panels. Each read uses one current catalog
version and a consistent Profile/results snapshot. Exact rational conversions
and comparisons derive canonical display, Status and age-aware chart zones before
display-only rounding. No entered fact changes when rules or an accepted DOB change.
All history is returned; latest `test_date` is distinct from latest remaining
`updated_at`. Owner CRUD is allowed; every admin Labs surface is read-only.

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

Labs create/edit/delete and Profile demographic changes share the Principal-first
lock order and recheck current role/Profile/history. Create saves every result
and its receipt once; any failure rolls back the entire batch and receipt. Edit
changes only date/value/unit; delete removes the owned fact physically.

## Idempotency

TargetPlan writes use `target_plan.write` with `Idempotency-Key`, canonical request
hash, in-progress/completed state, resource reference, and replay response. Historical
`target_plan.activate` and `target_plan.replace` records remain replayable through a
strict adapter that validates legacy-equivalent hashes and reconstructs the current
response from the referenced TargetPlan. Stored legacy response JSON is never returned
directly; ambiguous or conflicting reuse fails closed.

`lab_results.create.v1` receipts are durable with null `expires_at`; all other
operations require non-null expiry. The existing completion/uniqueness checks
and expiry index remain. Target Plan expiry and replay data are unchanged.
Labs hashes retain decimal scale and unit while normalizing row order. Same-key
same-payload replay returns the original ID-only receipt even after edit/delete
or rule/DOB changes; it never recreates deleted facts. Different payload is 409.
The browser keeps ambiguous payload/key only in actor-scoped volatile memory and
uses a fresh GET after success/replay; an unresolved retry cannot edit the payload.

Diary client UUID replay remains separate. Retired Day-status idempotency is absent.

## API and navigation

Current Backend route families are account (`/me`, `/calendar`), Profile, Target Plans,
Nutrition Registry, Foods, Diary, Admin user monitoring, and health. Foods expose
exactly GET/POST `/foods`, GET `/foods/picker`, and GET/PUT/DELETE `/foods/{food_id}`.
`GET /foods` is paginated. The frontend canonical pages are Diary, Foods and Food
detail/create/edit, Profile, Admin user monitoring, auth, and offline shell. There is
no `/admin/foods` route.

Labs adds exactly these eight operations:

| Method | Path |
|---|---|
| GET | `/labs/catalog` |
| GET | `/labs` |
| GET | `/labs/tests/{test_key}` |
| POST | `/labs/results` |
| PATCH | `/labs/results/{result_id}` |
| DELETE | `/labs/results/{result_id}` |
| GET | `/admin/users/{principal_id}/labs` |
| GET | `/admin/users/{principal_id}/labs/tests/{test_key}` |

All Labs responses are `no-store`. POST requires `Idempotency-Key`, returns 201
and exposes `Idempotent-Replayed` through the existing bounded CORS policy.
There is no admin mutation operation. Frontend paths are `/labs`, `/labs/{testKey}`,
`/admin/users/{principalId}/labs` and `/admin/users/{principalId}/labs/{testKey}`;
batch add and edit are dialogs. These provide the six approved views. `التحاليل`
joins the existing top navigation. Query keys include actor and selected subject;
fresh reads occur on opening/focus and successful events, without polling.
Admin subject activation removes only other selected subjects' Labs queries;
same-subject overview/detail navigation preserves current queries and cache.

## Migration and recovery

The sole Alembic head is `e8b7a42f6c31`. Historical migrations remain immutable and
reconstruct the schema. Destructive cutovers are forward-only: real rollback after
removed schema or data requires a matching pre-cutover database restore and compatible
application revision, not a synthesized downgrade.

## Explicitly absent

There is no Day Logging Status, complete/reopen command, TargetPlan lifecycle state,
pending plan, semantic Nutrition version, legacy Target transition snapshot/Profile
fallback, Diary target provenance, Food Archive/Restore, separate Admin Food UI, Sync
route/queue, Food V3 public schema, dual-array Food response, uncategorized sentinel,
or `/admin/foods` compatibility route.
Labs adds no persisted Status/reference/canonical snapshot, custom or editable
medical catalog, pregnancy field, automatic biomarker, nutrition coupling,
browser personal-data persistence, API caching, offline queue, polling or export/sharing.
