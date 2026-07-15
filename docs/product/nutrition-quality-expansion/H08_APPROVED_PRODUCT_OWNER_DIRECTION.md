# H08 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H08` |
| Issue ID | `H08` |
| Severity | High |
| Title | Snapshot v2 and Target Plan binding do not exist |
| Product/Snapshot direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H08 product/contract blocker only. It does not authorize implementation and does not close H08.

## 2. Approved Storage Direction

Diary Snapshot v2 uses a versioned, Backend-validated JSONB envelope.

Diary Entry also uses relational fields for:

- Principal ownership;
- nullable Target Plan linkage;
- target provenance;
- snapshot schema version;
- entry date;
- meal type;
- quantity.

The Backend is the only authoritative Snapshot v2 writer. The client does not send authoritative nutrition snapshots, nutrition totals, Target Plan IDs, target provenance, or rule versions.

## 3. Approved Target Provenance

Supported meanings are exactly:

```text
versioned_plan
legacy_unversioned
no_target_source
```

- `versioned_plan` requires a valid Target Plan relationship.
- `legacy_unversioned` has no fabricated Target Plan.
- `no_target_source` has no fabricated target values.
- The Backend resolves provenance using authenticated Principal and Diary entry date.
- The client cannot select provenance.

## 4. Target Plan Resolution

When creating an entry, the Backend resolves the Target Plan effective for `Principal + entry_date`.

- A scheduled plan is not used before `effective_from`.
- An ended plan is not used on or after its exclusive `effective_to`.
- Binding is immutable after entry creation.
- Later Profile changes or Target Plans do not rebind an existing entry.

### 4.1 New-user first activation on the current date

If a genuinely new Profile had no prior target source and explicitly activates its first Target Plan for the current Diary date, same-date entries for that Principal with `target_provenance = no_target_source` and `target_plan_id = null` are bound to the newly activated plan in the same activation transaction.

Their nutrition snapshots are not modified. Prior-date entries are not rebound.

### 4.2 Existing legacy user

The first versioned Target Plan begins on the next Diary date. Current-date entries remain `legacy_unversioned` and are not rebound to the next-date plan.

## 5. Snapshot v2 Value Basis

Snapshot v2 stores authoritative values for one captured logging unit. `DiaryEntry.quantity` remains a separate multiplier.

The Snapshot preserves the captured unit definition:

- Food nutrition basis;
- default unit type;
- unit amount;
- unit basis.

The Backend calculates entry totals as:

```text
captured per-unit value × DiaryEntry quantity
```

- Known numeric values scale with quantity.
- Explicit zero remains zero and known.
- Null remains null.
- Changing quantity modifies quantity only.
- Changing meal modifies `meal_type` only.
- Neither operation modifies or rebuilds the Snapshot.
- Quantity and meal edits do not reread the source Food.
- Direct gram/ml logging remains deferred and is not introduced through this contract.

## 6. Required Conceptual Snapshot v2 Content

The exact physical JSON schema remains subject to the formal Physical Data Model and API Contracts. Snapshot v2 preserves equivalent content for the following areas.

### 6.1 Schema identity

```text
schema_version = 2
```

The relational `snapshot_schema_version` and envelope schema identity must agree under the approved technical contract.

### 6.2 Food identity and captured unit

- Food ID at capture where available;
- Food name;
- brand where present;
- nutrition basis;
- default unit type;
- unit amount;
- unit basis;
- primary category;
- Food kind.

### 6.3 Nutrition per captured unit

- calories;
- protein;
- carbohydrate;
- fat;
- all 16 approved Wave 1 nutrient values as number or null.

### 6.4 Nutrition completeness

Snapshot v2 stores enough resolved completeness information to preserve historical state truthfully. Known zero remains known and unknown remains unknown. Exact counts and status representation remain for the formal schema.

### 6.5 Food groups

- group-data status;
- group-data completeness;
- quantitative contributions resolved for one captured unit;
- analytical traits;
- `food_group_rules_version`.

### 6.6 Nutrition source

- controlled source type;
- source name and reference where applicable;
- resolved source reliability;
- `source_reliability_rules_version`.

### 6.7 NOVA

- classification;
- review status;
- `nova_rules_version`.

### 6.8 Versions

- `nutrition_registry_version`;
- `food_group_rules_version`;
- `source_reliability_rules_version`;
- `nova_rules_version`;
- `snapshot_schema_version`.

Full ingredients text is not required in Diary Snapshot v2. Calculation-engine provenance remains in the linked Target Plan when a versioned plan exists and is not fabricated for legacy records.

## 7. Snapshot Immutability

After creation, Snapshot v2 is not rebuilt or reinterpreted because of:

- Food edit or hard deletion;
- Registry change;
- source-reliability rule change;
- NOVA change;
- food-group rule change;
- Profile change;
- Target Plan change;
- quantity change;
- meal movement.

The nullable live Food relationship may be cleared by approved hard deletion while captured identity remains in the Snapshot.

## 8. Snapshot v1 Compatibility

Legacy v1 detection requires both:

- relational `snapshot_schema_version` is null;
- JSON matches the approved legacy v1 shape.

Such rows use the dedicated v1 reader.

- V1 is not rewritten as v2.
- V1 is not enriched from current Food.
- V1 receives no inferred food groups, NOVA, controlled source, reliability, or Target Plan.
- V1 remains readable throughout Wave 1.
- V1 and v2 normalize internally into a shared aggregation model.
- An absent version does not permit treating arbitrary JSON as v1.

## 9. Unsupported Or Malformed Data

Unknown snapshot versions must not fall back to v1.

Malformed v1 or v2 data must not be treated as zero, silently excluded, repaired through current Food data, or used to produce apparently complete totals.

Use stable error meanings equivalent to:

```text
UNSUPPORTED_DIARY_SNAPSHOT_VERSION
INVALID_DIARY_SNAPSHOT_DATA
```

Exact HTTP and response envelopes remain for the API Contracts. Day/week summaries disclose that totals are unavailable because of a data-integrity error rather than returning understated totals. Affected identifiers may be returned only to the authenticated owner under the non-enumerating security contract.

## 10. API Creation And Update Contract

Diary create accepts only authoritative user inputs equivalent to:

- `food_id`;
- `entry_date`;
- `meal_type`;
- `quantity`.

The Backend transaction:

1. establishes Principal;
2. loads the owner-scoped Food;
3. resolves date-effective Target Plan and provenance;
4. constructs and validates Snapshot v2;
5. persists the Diary Entry.

Client-supplied snapshots, target IDs, versions, or totals are rejected or explicitly ignored according to the final API contract and are never authoritative.

Diary update permits only `quantity` and `meal_type`. It does not permit changing Food identity, entry date, Target Plan binding, target provenance, snapshot version, or snapshot content. Changing Food or date requires the approved delete-and-create flow.

The API may preserve existing normalized response fields and add `snapshot_schema_version`, `target_plan_id`, and `target_provenance`. Raw JSONB storage need not become a public Frontend contract.

## 11. Migration And Rollout Order

Use `Expand → Migrate → Contract`.

Approved sequence:

1. establish Principal and Target Plan dependencies;
2. add nullable relational linkage and snapshot-version support;
3. deploy readers supporting v1 and v2 while the writer still creates v1;
4. validate all current v1 rows;
5. enable the Backend v2 writer only after compatibility verification;
6. never backfill or enrich v1 snapshot content;
7. retain the v1 reader throughout Wave 1.

After the first v2 snapshot is written, rollback is permitted only to an application release that can read v2. Do not roll back to a pre-v2-reader application after v2 data exists.

## 12. Compatibility And Scope

Preserve existing Diary routes and normalized response fields where compatible, frozen historical snapshots, current serving-based logging, Food hard-delete behavior, and existing Diary/Add Food behavior.

This decision does not introduce direct gram/ml Diary logging, historical snapshot enrichment, historical Target Plan fabrication, Progress UI, later-wave analysis, offline personal-data storage, or unrelated redesign.

## 13. Status

```text
Artifact ID: DEC-H08
Selected direction: Versioned JSONB envelope with relational ownership and Target Plan linkage
Snapshot writer: Backend only
Snapshot values: Per captured logging unit
Quantity stored separately: Yes
Quantity edit mutates Snapshot: No
Meal movement mutates Snapshot: No
Target Plan resolution: Principal plus Diary date
Client-authoritative Snapshot or Target Plan: Prohibited
Snapshot v1 rewrite or enrichment: Prohibited
Malformed/unsupported snapshots treated as zero: Prohibited
Product/contract blocker: Resolved
Architecture, Security, Data, API, Migration, UX, implementation, and verification: Still open
H08 overall status: Open
```

H08 remains open until the formal technical contracts are approved and pinned, implementation and migration complete, mixed-history and rollback behavior are verified, traceability closes, and the final readiness recheck passes.
