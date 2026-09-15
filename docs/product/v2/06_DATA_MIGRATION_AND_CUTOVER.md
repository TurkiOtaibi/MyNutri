# V2 Data Migration and Cutover

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

The final Diary-to-Food foreign key is non-null and `ON DELETE RESTRICT`.
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
9. Confirm future Diary create, update, and delete work without `If-Match`.
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
