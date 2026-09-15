# Nutrition Versioning and Legacy Target Compatibility Retirement

Status: Approved V2 implementation authority

## Decision

myNutri has one current Nutrition Registry and one current calculation engine.
Active runtime and public contracts therefore do not carry semantic nutrition
version numbers. The following concepts are retired:

- `calculation_engine_version`;
- `nutrition_registry_version`;
- `registry_schema_version`;
- `TargetPlan.calculation_document_schema_version`; and
- numeric-version compatibility branches in clients.

The Nutrition Registry, calculation formulas, safety rules, nutrient
definitions, labels, units, ordering, and target policies are unchanged.

## Integrity without semantic versions

`rules_manifest_hash` is the content fingerprint for the current Registry and
calculation-policy manifest. The committed `rules_manifest.lock.json` contains
that hash, and CI continues to fail on unreviewed manifest drift. Registry HTTP
ETags use the same fingerprint.

The preview hash directly covers `rules_manifest_hash`, the effective date,
normalized Profile inputs, and the calculated result. A rules-manifest change
therefore invalidates an earlier preview even when its numeric output happens to
be unchanged. Target Plan request idempotency remains a separate request-
identity mechanism and is not replaced by either hash.

Registry clients validate the response structure and cross-references at the
API boundary. Required collections, fields, and types must be present; nutrient,
category, and source keys must be unique; subcategory keys must be unique within
each category; and every nutrient target type must be declared by the response.
Invalid payloads fail closed. The frontend does not contain a duplicate nutrient
catalogue.

## Target Plan truth

The live `target_plan` columns are:

- `id`;
- `principal_id`;
- `profile_id`;
- `effective_from`;
- `revision`;
- `calculation_document`; and
- `created_at`.

Rows remain immutable revisions. The database requires a JSON object-valued
calculation document with an object-valued `target_result`; application reads
perform full `TargetResponse` validation. Existing historical JSON documents
are not rewritten. Embedded version keys in those documents are inert historical
metadata. Newly created documents omit semantic version keys.

## Target resolution and Profile

For date `D`, resolution selects one canonical Target Plan for the Principal:

```text
effective_from <= D
ORDER BY effective_from DESC, revision DESC, id DESC
LIMIT 1
```

If no plan applies, both plan and targets are null. There is no transition
snapshot, Profile-as-target fallback, or legacy provenance branch. `Profile`
continues to represent the latest confirmed preferences and inputs; it is not a
substitute historical Target Plan. A first future plan updates Profile but does
not provide targets for earlier dates.

## Diary binding

`DiaryEntry.target_plan_id` remains nullable and owner-bound.
`target_provenance` is retired: a non-null identifier is a persisted Target Plan
binding, while null means no plan applied on that Diary date. Diary creation
without an applicable plan succeeds and nutrition totals remain available;
target-dependent evaluation is omitted.

Past bindings, including null bindings, remain immutable. Today and future
bindings may be recomputed by the controlled Target Plan write transaction and
must equal the canonical plan for the entry date. Principal locking continues to
serialize Diary creation with Target Plan writes.

## API and replay compatibility

The Target Plan API remains exactly:

- `POST /target-plans`;
- `GET /target-plans`; and
- `GET /target-plans/current?date=YYYY-MM-DD`.

Nutrition semantic-version and target-provenance fields are absent from public
responses. Target source responses enforce plan and targets as either both
present or both null.

The shared idempotency ledger and `target_plan.write` remain. Historical
`target_plan.activate` and `target_plan.replace` ledger rows are retained solely
for API retry safety. Replay validates the legacy request hash and referenced
resource, then reconstructs the current response from immutable Target Plan
rows; old response JSON is never returned directly. This API replay adapter is
not legacy Target data compatibility.

## Migration and recovery

Revision `c8e53f0b2d47`, parent `b7d42e9a1c36`, performs one coordinated hard
cutover. It fails closed on unexpected schema, invalid calculation documents or
version metadata, Target Plan ownership/revision errors, non-deterministic Diary
provenance, invalid bindings, incompatible Target Plan idempotency resources, or
any transition-snapshot row. It adds and validates direct calculation-document
shape integrity before dropping semantic-version columns, replaces the Diary
binding guard, removes Diary provenance, and drops the transition snapshot
schema without `CASCADE`.

The migration is forward-only. It cannot recreate truthful semantic versions,
legacy target documents, or Diary provenance after removal. Recovery requires a
matching pre-cutover database restore and application revision. Historical
Alembic revisions remain unchanged.
