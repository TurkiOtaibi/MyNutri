# H10 Approved Architecture And Rule Versioning Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `ADR-DIR-H10` |
| Issue ID | `H10` |
| Severity | High |
| Title | Independent rule versions and one Backend-owned rules package do not exist |
| Architecture/rule-versioning direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H10 architecture/versioning direction blocker only. It does not authorize implementation and does not close H10.

## 2. Approved Backend Rules-Package Direction

The Backend owns one typed, declarative, versioned nutrition-rules package. It conceptually contains independently testable modules for:

- versions;
- nutrients;
- macro policy;
- deficit policy;
- food groups;
- source reliability;
- NOVA;
- snapshot schema;
- future analysis policy.

Architecture may select exact Python paths provided there is one Backend authority, modules have no runtime side effects, calculations are pure and deterministic, definitions are machine-readable and exportable where required, the Frontend cannot become an independent authority, and database rows do not become dynamically editable rule definitions.

The database stores resolved historical results and version references, not the editable current rule source.

## 3. Approved Initial Versions

```text
nutrition_registry_version = 1.0.0
calculation_engine_version = 2.0.0
food_group_rules_version = 1.0.0
source_reliability_rules_version = 1.0.0
nova_rules_version = 1.0.0

registry_schema_version = 1
snapshot_schema_version = 2

analysis_rules_version = null
analysis_rules_status = reserved_for_wave_3
```

- `analysis_rules_version` remains inactive and receives no fabricated Wave 1 version.
- Wave 1 reserves only its stable identifier and package boundary; Wave 3 assigns the first active semantic version.
- Legacy records remain explicitly unversioned.
- No legacy Profile, Target Plan, or Snapshot receives current versions through inference or backfill.
- The first governed calculation engine is `2.0.0` because H01, H02, and H03 change the approved semantics over legacy unversioned calculation behavior.
- Legacy behavior is not assigned a fabricated `1.x` version.

## 4. Independent Version Ownership

The following remain independent:

- `nutrition_registry_version`;
- `calculation_engine_version`;
- `food_group_rules_version`;
- `source_reliability_rules_version`;
- `nova_rules_version`;
- `analysis_rules_version`;
- `registry_schema_version`;
- `snapshot_schema_version`.

An optional `product_nutrition_rules_version` may be added later for operational convenience. It must not replace an independent version, become sole persisted provenance, reinterpret history, or be required to close H10.

## 5. Semantic Version-Bump Policy

Governed rule sets use semantic versions.

### 5.1 Major

A Major version is required when a change can alter meaning, interpretation, or calculated outcome for an existing key or rule, including formula, operation order, rounding, safety boundary, nutrient unit, stable-key removal/rename, target type/rule, Food-group serving/overlap/target/cap/subtype/exclusion, source reliability level/mapping, NOVA meaning, persisted historical interpretation, or incompatible Registry semantics.

### 5.2 Minor

A Minor version is required for backward-compatible additive capability, including a new nutrient without changing existing meaning, new Food group or trait without changing existing rules, new source type without changing current mappings, optional Registry metadata, or an additive optional API field that changes no existing calculation or meaning.

### 5.3 Patch

A Patch is allowed only for proven behavior-preserving, non-semantic spelling, grammar, label, explanation, documentation, example, or metadata corrections that do not affect calculation, target, storage, completeness, coverage, or historical interpretation.

A bug fix that changes an actual calculated result or historical meaning is not a Patch merely because it is called a fix. It requires the applicable semantic version increase.

## 6. Schema-Version Policy

`registry_schema_version` and `snapshot_schema_version` use integer versions. Increment the relevant integer when serialized or persisted structure requires a new reader or validation dispatch.

- Readers dispatch by exact supported schema version.
- Unknown versions do not fall back to current versions.
- An absent version is legacy only when data matches the approved legacy shape.
- New writers are enabled only after compatible readers deploy.
- Snapshot v2 remains version `2` for the exact H08 contract.
- A future incompatible Snapshot envelope receives a new integer version.

## 7. Immutable Released Versions And Manifest Integrity

A released version identifier must never point to different semantic content.

The Backend produces a canonical serialized rules manifest containing at least every active independent version, active stable keys, semantic rule metadata, Registry/schema versions, analysis reserved/active state, and package release metadata required for verification.

Generate a deterministic manifest hash equivalent to SHA-256.

- The same version bundle and canonical content produce the same hash.
- Governed content changes without an applicable version bump fail CI.
- Reusing an old version string with different content is prohibited.
- Serialization is deterministic.
- The hash is verification evidence, not a substitute for independent versions.

Exact manifest filename and canonical serialization require Architecture and QA approval.

## 8. Registry API Version Bundle

`GET /nutrition/registry` exposes authoritative metadata and a version bundle equivalent to:

- `registry_schema_version`;
- `nutrition_registry_version`;
- `calculation_engine_version`;
- `food_group_rules_version`;
- `source_reliability_rules_version`;
- `nova_rules_version`;
- `snapshot_schema_version`;
- `analysis_rules_version`;
- `analysis_rules_status`;
- `rules_manifest_hash`.

The API may expose additional compatibility metadata. It does not expose Python source. It exposes stable keys, display metadata, target-rule descriptors, explanation parameters, compatibility, and version metadata. Personalized resolved targets remain in Profile Preview and Target Plan responses.

Authentication and HTTP caching remain for formal Architecture, Security, and API approval.

## 9. Frontend Boundary

OpenAPI generation may create TypeScript types only. Generated Frontend artifacts must not contain authoritative labels, ordering, targets, formulas, group definitions, source mappings, NOVA meanings, version-bump policy, or rule values.

Frontend metadata comes from the runtime Backend Registry contract. In-memory or query/session caching is allowed. Offline nutrition-rule authority and independently editable fallback Registries are prohibited.

If Registry metadata or a supported schema cannot be loaded, the Frontend does not fabricate metadata. Registry-dependent creation or Target Plan activation is blocked truthfully with approved loading, retry, unavailable, or incompatible states. Unrelated baseline behavior may continue only where correct without the Registry.

## 10. Persistence Mapping

### 10.1 Target Plan

Every newly activated Target Plan persists each version that actually governed its calculation and resolved targets, including at least `calculation_engine_version`, `nutrition_registry_version`, and the H04 Target Plan document schema version. Unrelated versions are not persisted merely because they exist globally.

### 10.2 Snapshot v2

Every Snapshot v2 persists `snapshot_schema_version`, `nutrition_registry_version`, `food_group_rules_version`, `source_reliability_rules_version`, and `nova_rules_version`.

`calculation_engine_version` remains in the linked Target Plan when a versioned plan exists and is not fabricated for `legacy_unversioned` or `no_target_source` entries.

### 10.3 Future Analysis Snapshot

`analysis_rules_version` is reserved in Wave 1. Analysis Snapshot persistence and its first active version remain deferred to Wave 3.

## 11. Historical Interpretation And Errors

Target Plans and Snapshots store resolved historical values and are not recalculated using current rules after version changes.

- Target Plans remain immutable resolved records.
- Snapshot values remain captured historical values.
- Versions provide provenance and compatibility dispatch.
- Historical records do not receive current versions retroactively.
- Current rules do not reinterpret old resolved values.
- Wave 1 need not replay every old calculation engine.
- The Backend retains readers for every claimed supported data/schema version.
- Operations requiring unsupported old executable rules fail explicitly instead of using current rules.

Approved stable error meanings include:

```text
UNSUPPORTED_RULE_VERSION
UNSUPPORTED_REGISTRY_SCHEMA_VERSION
INCOMPATIBLE_NUTRITION_REGISTRY
```

Exact HTTP mappings and envelopes require formal API approval.

## 12. Migration And Compatibility

Use H09 `Expand → Migrate → Contract` sequencing.

- Add nullable version fields where required.
- New governed Target Plans and Snapshot v2 records require non-null applicable versions.
- Legacy rows remain null/unversioned according to approved legacy type.
- Do not backfill current versions into history.
- Compatible readers deploy before versioned writers.
- No legacy reader or compatibility field is removed during Wave 1.
- Rollback after versioned data exists requires a compatible reader.

## 13. CI And Verification

Formal verification must prove one Backend package owns governed rules, no independently editable Frontend Registry remains, generated TypeScript contains types only, exact initial versions are exposed, manifest serialization/hash are deterministic, semantic changes without the correct bump fail, unchanged-content bumps are flagged for review, unsupported versions fail explicitly, legacy null versions remain legacy, Target Plans and Snapshot v2 persist applicable versions, historical interpretation survives current-rule bumps, Registry API and package versions agree, and full regressions pass.

## 14. Deferred And Prohibited Scope

This direction does not implement Wave 3 analysis, assign active `analysis_rules_version`, add database-editable rule administration or a Frontend rule editor, introduce offline rule authority, recalculate history, remove legacy readers, create formal freeze artifacts, or authorize product implementation.

## 15. Status

```text
Artifact ID: ADR-DIR-H10
Selected direction: Typed declarative Backend rules package
Frontend authoritative rules: Prohibited
Generated TypeScript output: Types only
Independent versions: Required
Initial governed calculation engine: 2.0.0
Registry schema version: 1
Snapshot schema version: 2
Analysis rules: Reserved and inactive until Wave 3
Released version mutation: Prohibited
Canonical manifest hash verification: Required
Legacy version backfill: Prohibited
Historical recalculation with current rules: Prohibited
Architecture/versioning blocker: Resolved
Technical contracts, physical persistence, implementation, migration, and verification: Still open
H10 overall status: Open
```

H10 remains open until the formal contracts are approved and pinned, rule ownership and persistence are implemented, migration and compatibility evidence passes, and final verification and traceability close.
