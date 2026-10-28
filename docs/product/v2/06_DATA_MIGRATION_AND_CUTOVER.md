# V2 Data Migration and Cutover

## APPROVED TARGET login cutover — pending #114

Historical lifecycle migrations remain immutable schema evidence. Supabase Auth runtime
integration is removed in #113 while PostgreSQL hosting and `DATABASE_URL` remain.
The future #114 cutover deletes current test accounts/private data, retains Foods and
scrubbed Principal tombstones, and recreates the single Admin through the internal
create/reset command. This is an approved target, not authorization to execute it.

Issue #110 and its 27 October 2026 decisions retain scrubbed Principal tombstones and never rewrite Food attribution IDs or transfer them to the Admin. The local deletion lifecycle purges private rows, including internal sessions, and scrubs username/hash along with existing identity data. The internal credential/session schema and Admin command are CURRENT in #110, specified in V2 02/11; the reviewed destructive cutover procedure remains pending #114. No cutover is authorized here. (BR-AUT-001/017, BR-USM-043, BR-FOD-021.)

## CURRENT migration authority


The Admin-managed lifecycle below is approved migration authority implemented
by forward revision `b6e4c2a78190`, following private Labs revision
`e8b7a42f6c31`.

## Private Labs note transition

Issue #106 authorizes revision `d8a6e4c90312`, parent `c7f5d3b89201`, for BR-LAB-017. Upgrade adds nullable `lab_result.note VARCHAR(500)` without changing existing facts or receipts. Downgrade drops only this column and refuses if any note is non-null. Test both directions only on disposable loopback PostgreSQL. Apply the migration before the new backend runs; production execution needs separate release authorization.

## Food duplicate identity transition

Revision `c7f5d3b89201` follows `b6e4c2a78190` and implements the Product Owner decision of 25 October 2026 for BR-FOD-029. It backfills non-null `food.normalized_brand` using the same case folding and whitespace normalization as names, mapping absent/blank brands to an empty string. The unique Food identity includes normalized name, normalized brand, and the existing serving definition. Upgrade locks Food and checks collisions before replacing the constraint. Downgrade restores the former identity only if no cross-brand rows collide; otherwise it stops without rewriting or deleting data. Release migration still requires explicit authorization.

## Historical Admin-managed account lifecycle transition

Revision `b6e4c2a78190` remains frozen. Its Principal status, unique Admin index,
creation idempotency and legacy identity/tombstone columns remain in the schema.
It preserved existing Principals/private data. Historical Supabase Auth links,
leases and cross-system sagas are not current runtime instructions: #113 removes
provider admission, create/reset/delete operations and reconciliation without
rewriting this migration or converting existing accounts.

Current deletion remains local: lock out the Principal, purge private dependents
and sessions under its lock, and scrub the tombstone without changing Food rows or
attribution IDs. All private writers retain Principal-first locking and status
checks; the #128 conditional session refresh remains the narrow exception described
in V2 02/03/11. The future destructive cutover needs its own reviewed #114 procedure
and explicit release authorization. Migration tests still prove single-Admin and
ownership constraints, populated upgrade preservation and historical downgrade guards.

## Migration topology

The simplified Food/current-Diary contract is introduced by Alembic revision:

- revision: `f47a2c9d6e13`
- parent: `8a91c4e7d2f6`

Day Logging Status is removed by the coordinated hard-cutover revision:

- revision: `a6c81e4f2d90`
- parent: `f47a2c9d6e13`

The Target Plan lifecycle is replaced by immutable date-effective revisions in:

- revision: `b7d42e9a1c36`
- parent: `a6c81e4f2d90`

Nutrition semantic versioning and legacy Target compatibility are retired in:

- revision: `c8e53f0b2d47`
- parent: `b7d42e9a1c36`

The Food catalog is unified and permanent deletion receives its final cascade and
database-privilege boundaries in:

- revision: `d9f64a1c3e58`
- parent: `c8e53f0b2d47`

Private Labs persistence and durable create receipts are introduced in:

- revision: `e8b7a42f6c31`
- parent: `d9f64a1c3e58`

Admin-managed account lifecycle fields and constraints are introduced in the sole head:

- revision: `b6e4c2a78190`
- parent: `e8b7a42f6c31`

`lab_result` stores Principal-owned entered facts in unscaled `NUMERIC`, retaining
fractional trailing zeros. PostgreSQL requires finite nonnegative values with
normalized numeric text length at most 128, nonempty bounded test/unit keys,
a non-null date, and `ON DELETE RESTRICT` ownership. The unique B-tree on
`(principal_id, test_key, test_date)` supports scoped reads in either date order;
no redundant descending index is needed. Time-dependent date validation and
catalog thresholds remain backend rules, not database checks. All privileges
on this private table are revoked from `PUBLIC` and existing `anon`/`authenticated`.
Existing table grants are unchanged.

Only `lab_results.create.v1` receipts require null `expires_at`; every other
operation still requires expiry. Completion/uniqueness checks, the expiry index,
Target Plan timestamps, and replay documents remain unchanged.

Historical revisions remain unchanged so the base-to-head chain is
reconstructable. Their retired tables, columns, and guards are removed only by
the new revision.

## Food transition

The revision adds `primary_category`, `subcategory`,
`nutrition_data_source`, and `ingredients`, backfills them, applies current
constraints, then removes the retired active columns.

Taxonomy migration follows these rules:

- known primary plus known valid subcategory maps deterministically;
- known primary plus unknown subcategory maps to the known primary and `other`;
- unknown primary maps to `other` and `other`.

Nutrition source migration follows these rules:

- `official_product_label` becomes `official`;
- every other legacy source value becomes `estimated`.

Only explicitly confirmed official data can become `official`. Ingredient text
moves from the legacy text column to `ingredients`; ingredient provenance is
not carried forward. Optional nutrient nulls remain null.

## Diary transition

Food nutrition snapshots and their version column are removed. Every Diary row
must have a resolvable `food_id`. The migration derives and stores the historical
recorded unit type, amount, basis, and optional label from the predecessor
payload before dropping that payload.

Migration stops without schema change when a Diary row has a null/orphan Food
reference, when its recorded measurement cannot be derived safely, or when its
recorded mass/volume dimension conflicts with the current referenced Food. It
never guesses Food identity or a mass/volume conversion.

Revision `d9f64a1c3e58` changes the final Diary-to-Food foreign
key to non-null `ON DELETE CASCADE`, removes archive columns/constraints/index,
and revokes direct Food mutation from `PUBLIC`, `anon`, and `authenticated`.
The migration itself deletes no Food or Diary data.
Current Diary totals are calculated from current Food nutrition and the stored
historical consumed measurement.

## Retired schema

The revision removes current schema objects for NOVA, Pattern Analysis, Weekly
Priority, Food Group Contributions, Food Analytical Traits, and their obsolete
guard schema. The migration fails closed and reports populated retired tables;
it does not silently delete those rows.

Existing relevant development/test data is experimental. Ephemeral automated
test databases may be rebuilt. Persistent non-production cleanup and every
production cleanup operation require separate authorization.

The Day Logging Status retirement permanently deletes only idempotency rows
whose operation is `diary_day_complete` or `diary_day_reopen` and whose
`resource_type` is `diary_day_status`. It then drops
`diary_day_status_history` before `diary_day_status`. Target Plan and unrelated
idempotency rows remain. No status data is exported or preserved. Historical
Alembic files remain byte-for-byte unchanged.

## Target Plan date-effective transition

Revision `b7d42e9a1c36` fails closed unless every Target Plan has valid Principal
and Profile ownership, the then-current calculation/version metadata, and an unambiguous
same-date predecessor/superseder chain; every Diary binding is owner-safe; and
every legacy Target Plan idempotency row can be replayed deterministically.

The migration adds `revision`, maps each valid same-date chain root-to-final to
revisions 1..N, then enforces positive revisions and uniqueness of
`(principal_id, effective_from, revision)`. Existing single-row groups become
revision 1. Today/future Diary rows are rebound to the canonical date-effective
revision; past rows are not changed. The Target Plan guard is replaced with an
UPDATE/DELETE rejection and the Diary guard admits only controlled canonical
today/future rebinding.

After validation, the migration removes Target Plan lifecycle constraints,
partial indexes, period exclusion, self-referencing lifecycle foreign keys, and
the lifecycle-only columns. It removes `btree_gist` only after catalog inspection
proves there is no remaining application dependency. Calculation documents,
Nutrition Versioning fields, legacy transition snapshots, Profile ownership,
Diary Target Plan references/provenance, and all Target Plan idempotency rows are
preserved.

## Nutrition versioning and legacy Target compatibility transition

Revision `c8e53f0b2d47` fails closed unless Target Plan documents and ownership,
revision canonicality, Diary bindings, legacy replay resources, and the empty
legacy transition/provenance census are valid. It replaces the relational
document-version check with a direct JSON-object/`target_result` shape check,
then removes the three semantic version columns without rewriting historical
calculation JSON.

The same revision removes the empty transition snapshot table and its trigger,
removes Diary target provenance, and replaces the Diary binding guard with
`target_plan_id`-only canonicality. A null binding is the sole representation
of no applicable Target Plan. Existing Target Plan and Diary rows, Profile
ownership, immutable revision history, shared idempotency rows, Nutrition
Registry content, and manifest/preview integrity are preserved.

## Cutover gates

Before any release authorization:

1. Verify the sole head and exact revision chain.
2. Run a clean disposable PostgreSQL base-to-head upgrade.
3. Run model/migration drift and offline upgrade SQL checks.
4. Prove orphan and ambiguous measurement preflights fail without partial change.
5. Regenerate OpenAPI and generated TypeScript deterministically.
6. Run backend, frontend, E2E, architecture, and current-Food-truth regression tests.
7. Confirm retired endpoints, fields, tables, configuration, and navigation are absent.
8. Confirm Day Logging Status routes, schemas, generated types, UI, tables, and
   status-specific idempotency rows are absent.
9. Confirm Diary creation allows past dates without limit and future dates through
   Asia/Riyadh today + 7 days, rejecting later new entries per BR-DRY-028. Existing
   entries retain update/delete rules; these operations require no `If-Match`.
10. Confirm historical migrations are byte-for-byte unchanged.
11. Confirm Target Plan revisions, same-date canonical selection, future Diary
    rebinding, past binding immutability, and legacy replay adaptation.
12. Confirm all Target Plan GET paths produce no lifecycle DML, flush, commit, or
    lifecycle lock and the three retired lifecycle operations are absent.
13. Confirm new calculation documents and public contracts expose no semantic
    nutrition versions while historical calculation JSON is unchanged.
14. Confirm Registry structural validation and manifest/preview hash drift
    protection fail closed without numeric compatibility gates.
15. Confirm transition snapshots, legacy target provenance, and Profile-as-target
    fallback are absent; no-plan dates return null plan/targets and Diary rows may
    retain a null `target_plan_id`.
16. Confirm `d9f64a1c3e58` removed Food archive columns, installed the Diary Food
    `ON DELETE CASCADE`, preserved existing Food/Diary rows during migration, and
    revoked direct Food mutation from `PUBLIC`, `anon`, and `authenticated`.
17. Confirm `a1d9b7f23645` is the sole head and agrees with all eight models (#113; Product Owner approval, 28 October 2026); the trigger-only change adds no model fields;
    clean and populated-base upgrades preserve existing facts, grants and replay.
18. Prove packaged Labs catalog availability, private privileges, finite/unscaled
    numeric storage, unique owner/test/date, and operation-specific receipt expiry.
19. Prove online empty-Labs downgrade succeeds, while any LabResult or in-progress/
    completed Labs receipt refuses downgrade without deletion. Offline downgrade
    must refuse. Preserve every historical migration hash.

Development migration and production-config simulation preflight run only against
an explicitly identified disposable loopback PostgreSQL database, with the target
asserted before schema/row changes. They provide no production authorization.

## Downgrade boundary

Revision `f47a2c9d6e13` intentionally fails closed on downgrade because the
removed snapshot payloads and retired product schemas cannot be reconstructed
without fabricating historical data and reintroducing obsolete contracts. Roll
forward or restore an approved backup. A production rollback or cleanup remains
separately authorized operational work.

Revision `a6c81e4f2d90` also fails closed on downgrade. Deleted status, history,
and command-idempotency rows cannot be reconstructed faithfully. Roll forward
or restore an approved backup with the matching application revision.

Revision `b7d42e9a1c36` fails closed on downgrade. Removed lifecycle state cannot
be reconstructed from immutable revisions without fabricating history. Recovery
requires the matching pre-cutover database restore and old application revision.

Revision `c8e53f0b2d47` also fails closed on downgrade. Removed semantic version
columns, provenance, and legacy transition schema cannot be synthesized. Recovery
requires the matching pre-cutover database restore and application revision.

Revision `d9f64a1c3e58` also fails closed on downgrade. Archive state cannot be
reconstructed and post-cutover permanent Food deletion may already have removed
Diary history. Recovery requires the matching pre-cutover database restore and
application revision.

Revision `e8b7a42f6c31` permits an online downgrade only when both LabResult facts
and Labs create receipts are absent. It locks the affected tables before checking,
refuses populated rollback without deleting data, and restores `expires_at NOT NULL`
only in an empty Labs schema. Offline downgrade is unavailable; production recovery
still requires explicit release authorization and the approved restore policy.

Issue #108 authorizes revision `e9b7f5d01423`, parent `d8a6e4c90312`, for BR-USM-031. Upgrade adds nullable `principal.disabled_at TIMESTAMP WITH TIME ZONE`; existing rows remain null. Downgrade drops only this timestamp, preserving account status and all other data. Render applies migrations at start; production execution remains subject to explicit release authorization. Test upgrade/downgrade only on disposable loopback PostgreSQL.


## Internal authentication transition

Issue #110 authorizes revision `f0c8a6e12534`, parent `e9b7f5d01423` (27 October 2026; BR-AUT-001/007/008/011/017, BR-PRF-024–026, BR-USM-030/033). Upgrade adds nullable username/normalized username/password hash/lock/last-login fields, defaulted initial-change and failure-count fields, and `auth_session` with token hashes and timestamps. Existing identities/emails remain unchanged. Direct PUBLIC/anon/authenticated access to credentials and sessions is revoked; the new session table has default-deny RLS. Downgrade drops the internal session table and new credential fields, losing internal credentials/sessions but retaining Principals and domain data; it does not restore direct Data API grants. This is not a safe authentication rollback after internal-only accounts are in use without an explicitly reviewed recovery plan. Apply before the backend built from this revision runs; Render applies migrations at start. Production execution requires separate release authorization.

## Target Plan purge guard (#113)

Product Owner approval of 28 October 2026 authorizes revision `a1d9b7f23645`, parent `f0c8a6e12534`. It replaces only the guard function: Target Plan DELETE requires an owning Principal in `deleting`; every UPDATE and all other DELETEs remain rejected. The existing account transaction sets that status before purging private rows and scrubbing the tombstone, preserving Food attribution. Downgrade restores unconditional rejection and cannot restore purged rows. Neither direction changes columns or existing data. Test upgrade/downgrade only on disposable loopback PostgreSQL; production execution requires separate release authorization.
