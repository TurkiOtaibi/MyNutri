# V2 Data Migration and Cutover

## Migration topology

The simplified Food/current-Diary contract is introduced by Alembic revision:

- revision: `f47a2c9d6e13`
- parent: `8a91c4e7d2f6`

Day Logging Status is removed by the coordinated hard-cutover revision:

- revision: `a6c81e4f2d90`
- parent: `f47a2c9d6e13`

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

## Downgrade boundary

Revision `f47a2c9d6e13` intentionally fails closed on downgrade because the
removed snapshot payloads and retired product schemas cannot be reconstructed
without fabricating historical data and reintroducing obsolete contracts. Roll
forward or restore an approved backup. A production rollback or cleanup remains
separately authorized operational work.

Revision `a6c81e4f2d90` also fails closed on downgrade. Deleted status, history,
and command-idempotency rows cannot be reconstructed faithfully. Roll forward
or restore an approved backup with the matching application revision.
