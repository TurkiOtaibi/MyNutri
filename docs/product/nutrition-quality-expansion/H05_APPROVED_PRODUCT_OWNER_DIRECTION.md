# H05 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H05` |
| Issue ID | `H05` |
| Severity | High |
| Title | Nutrient registry is incomplete and duplicated |
| Product/contract direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H05 product/contract blocker only. It does not authorize implementation and does not close H05.

## 2. Approved Canonical Registry Direction

The Backend owns one canonical, machine-readable, versioned Nutrition Registry. The Frontend must not maintain an independently editable nutrient registry.

The approved Wave 1 nutrient fields are exactly:

1. `fiber_g`
2. `added_sugar_g`
3. `saturated_fat_g`
4. `trans_fat_g`
5. `sodium_mg`
6. `potassium_mg`
7. `cholesterol_mg`
8. `calcium_mg`
9. `iron_mg`
10. `magnesium_mg`
11. `zinc_mg`
12. `selenium_mcg`
13. `vitamin_b12_mcg`
14. `folate_dfe_mcg`
15. `vitamin_a_rae_mcg`
16. `iodine_mcg`

The approved target types are exactly:

1. `minimum`
2. `maximum`
3. `adequate`
4. `recommended`
5. `range`
6. `monitor_only`
7. `minimize`

Deferred nutrients remain excluded even when legacy database columns already exist for some of them.

## 3. Approved Registry API Direction

Provide one additive read-only capability equivalent to:

```text
GET /nutrition/registry
```

Exact authentication policy and HTTP caching headers require Architecture, Security, and API approval.

The response contains:

- `nutrition_registry_version`.
- `registry_schema_version`.
- Nutrient definitions.

Each definition contains at least:

- Stable key and canonical storage field.
- Arabic label, unit, display precision, and display order.
- Target type and target source.
- Target-rule metadata.
- Completeness participation.
- Diary coverage participation.

Architecture and API owners may add technically required fields while preserving this meaning. Registry definitions and rule metadata do not replace personalized resolved targets returned by Profile Preview and immutable Target Plan contracts.

## 4. Approved Frontend Contract

The Frontend consumes Registry metadata from the authoritative Backend contract. TypeScript types may be generated from OpenAPI, but generated output contains types only and must not become the source for labels, targets, ordering, or rules.

An in-memory or session query cache is allowed. Offline personal-data storage or a separate persistent nutrition-rule authority is not.

If Registry metadata cannot be loaded:

- Show an explicit loading or error state.
- Do not fabricate labels, targets, or target types.
- Do not activate a Target Plan against an unknown or incompatible Registry version.
- Preserve unrelated baseline behavior where it remains truthful.

Detailed retry and compatibility states belong in the formal API, User Story, UI State, and Verification artifacts.

## 5. Approved Versioning

Use independent values equivalent to:

- `nutrition_registry_version`: semantic version.
- `registry_schema_version`: integer.

A semantic Registry-version change is required when a change affects a stable key, canonical unit, target type, target rule, calculation participation, completeness or coverage interpretation, or semantic interpretation of a stored value.

Purely presentational changes follow the formal Rule Versioning policy and must not make a historical Target Plan or Snapshot ambiguous. Target Plans and Diary Snapshot v2 store the `nutrition_registry_version` that governed their values.

## 6. Approved Personalized Target Calculation

The Backend calculates all personalized nutrient targets.

- Calorie-derived targets use authoritative `final_target_calories` from the proposed or activated Target Plan.
- Sex-derived targets use Profile sex captured by the activated Target Plan.
- Age-derived targets use age on the plan's `effective_from` Diary calendar date.
- Later Profile changes do not rewrite an activated Target Plan.
- A newly activated plan uses newly approved Profile inputs.
- The Frontend does not calculate nutrient targets.

Exact formulas remain those approved in `PD-009` and must be recorded and golden-tested in formal freeze artifacts.

## 7. Approved New Exact Nullable Food Fields

Add these exact nullable fields through the approved additive migration:

- `selenium_mcg`
- `iodine_mcg`
- `folate_dfe_mcg`
- `vitamin_a_rae_mcg`

Existing rows receive `null`. Do not infer or backfill values. Known numeric zero remains known zero; `null` remains unknown.

Exact database types, precision, validation maxima, indexes, and rollback behavior require Engineering/Data approval.

## 8. Approved Legacy Ambiguous-Field Behavior

Existing generic fields `folate_mcg` and `vitamin_a_mcg` remain deprecated legacy compatibility data.

- They are not automatically converted to `folate_dfe_mcg` or `vitamin_a_rae_mcg`.
- They do not satisfy exact Folate DFE or Vitamin A RAE targets.
- They do not count as the exact new field being complete.
- They are not used by new Target Plans, Snapshot v2 exact nutrient values, or new nutrition analysis.
- Existing values remain readable and are not deleted by migration.
- They may be displayed with meaning equivalent to `قيمة قديمة غير محددة المعيار`.
- New Food creation uses exact DFE and RAE fields.
- Editing an existing Food does not silently delete or reinterpret a legacy value.
- Manually replacing it with an exact value requires a source explicitly supporting DFE or RAE.
- The system performs no automatic conversion.

Formal Food/API/UX contracts define the exact compatibility payload, edit behavior, and deprecation period.

## 9. Approved Target Plan And Snapshot Behavior

Every newly activated Target Plan stores resolved applicable nutrient targets, target types and/or the immutable resolved target document, `nutrition_registry_version`, and relevant rule versions.

Diary Snapshot v2 stores all approved nutrient values as `number` or `null`.

- Unknown is never stored as zero.
- Legacy generic folate or vitamin A values do not populate exact DFE or RAE fields.
- Snapshot v1 remains readable.
- Historical snapshots use their stored schema and Registry versions.
- Newer Registry rules do not silently reinterpret old snapshots.

## 10. Compatibility And Deferred Scope

Preserve existing Food records; compatible Profile, Foods, Diary, and Add Food routes; nullable nutrient values; historical Diary snapshots; online-only architecture; generated frontend types where useful; and unrelated baseline behavior.

This decision does not add deferred nutrients, nutrient-level source provenance, supplement or laboratory tracking, clinical target exceptions, recipe nutrient calculation, offline personal-data storage, direct gram/ml Diary logging, Progress UI, Nutrition Pattern Analysis UI, or unrelated UI redesign.

## 11. Approval And Work Boundaries

Registry ownership and product semantics are approved. Exact physical types, endpoint schema, authentication and caching, compatibility payloads, migration and rollback, UX states, implementation, verification, and traceability remain open for designated approvers.

## 12. Recorded Status

```text
Artifact ID: DEC-H05
Selected direction:
Backend canonical Registry plus runtime Registry API plus generated
TypeScript types only
Approved nutrient count: 16
Approved target types: 7
Frontend independently editable registry: Prohibited
New exact nullable Food fields: 4
Legacy generic folate/vitamin A conversion: Prohibited
Legacy ambiguous values: Preserved but excluded from exact targets and
exact-field completeness
Product/contract blocker: Resolved
Architecture, Data, API, Migration, UX, implementation, and verification:
Still open
H05 overall status: Open
```

H05 remains open until all formal contracts, migration, implementation, version binding, verification, and traceability evidence are approved.
