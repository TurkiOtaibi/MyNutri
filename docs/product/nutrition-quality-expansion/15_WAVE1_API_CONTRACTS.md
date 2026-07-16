# Wave 1 API Contracts

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-API-15` |
| Version | `1.0` |
| Status | `Approved — API and Architecture` |
| Owner | API / Architecture |
| Approver | API / Architecture |
| Approval date | `2026-07-16` |
| Review evidence | `15A_WAVE1_API_CONTRACTS_REVIEW.md` |
| Critical / High findings | `0 / 0` |
| Product decisions remaining | `0` |
| Pinned revision | `400366b39abb73bb2e2d2ba82c79c1cd524d6e67` |
| Implementation authorization | `No` |

## 1. Common Boundary

All user-data routes require bearer authentication. A valid credential resolves an immutable Backend `PrincipalContext`; request bodies never accept authoritative `principal_id`, `owner_id`, or `user_id`. Missing/invalid credentials return `401`. A valid Principal requesting a missing or cross-owner identifier receives the same `404` body. Normal operations never use Service Role.

Dates are Gregorian `YYYY-MM-DD`; Backend `Asia/Riyadh` determines today/next date. Decimal values are JSON numbers serialized to the display precision specified by the Registry, while persisted results retain Artifact 14 precision.

### Error envelope

```json
{"error":{"code":"STABLE_CODE","message_ar":"رسالة عربية محايدة","dimension":null,"details":{},"request_id":"uuid"}}
```

`details` contains no cross-owner identifiers or credentials. Validation uses `422`; authentication `401`; owner-scoped absent resource `404`; idempotency/content conflict `409`; unsupported representation/version `409`; transient server failure `500/503` as applicable.

## 2. Authentication Semantics

- `Authorization: Bearer <credential>` is transport, not ownership identity.
- Empty/missing production auth configuration fails startup/preflight and protected requests closed.
- Token rotation maps to the same Principal and does not change resource IDs.
- Stable codes: `AUTHENTICATION_REQUIRED`, `INVALID_CREDENTIAL`, `RESOURCE_NOT_FOUND`.

## 3. Nutrition Registry

### `GET /nutrition/registry`

Returns `200` with:

```json
{
  "registry_schema_version":1,
  "nutrition_registry_version":"1.0.0",
  "calculation_engine_version":"2.0.0",
  "food_group_rules_version":"1.0.0",
  "source_reliability_rules_version":"1.0.0",
  "nova_rules_version":"1.0.0",
  "snapshot_schema_version":2,
  "analysis_rules_version":null,
  "analysis_rules_status":"reserved_for_wave_3",
  "rules_manifest_hash":"sha256-hex",
  "nutrients":[], "food_groups":[], "traits":[],
  "source_types":[], "reliability_levels":[], "nova":{}
}
```

Nutrient entries include stable key/storage field, Arabic label, unit, precision/order, target type/source/rule descriptor, completeness and Diary-coverage flags. Personalized resolved targets are excluded.

`ETag` is the manifest hash; `Cache-Control: private, max-age=300, must-revalidate`; `If-None-Match` may return `304`. Unsupported schema uses `INCOMPATIBLE_NUTRITION_REGISTRY` and blocks Registry-dependent writes. No static client fallback is authorized.

## 4. Profile and Target Calculation

Existing Profile route purposes and top-level target fields remain additive-compatible.

### `GET /profile`

Returns current Profile preferences, legacy/current target source, effective plan summary, pending plan summary, and current resolved targets. No Profile returns owner ID.

### `POST /profile/preview`

Accepts Profile draft inputs including `sex`, `birth_date`, `height_cm`, `weight_kg`, `activity_level`, `goal`, `protein_per_kg`, `fat_pct`, and `selected_cut_intensity`. It never persists.

Success contains top-level `calories`, `protein_g`, `carb_g`, `fat_g`, deprecated `carb_clamped:false`, resolved additional targets, warnings, and:

```json
{
 "selected_cut_intensity":0.20,
 "requested_deficit_kcal":500.0,
 "applied_deficit_kcal":500.0,
 "deficit_cap_applied":false,
 "final_target_calories":2000,
 "safety_outcome":"normal",
 "can_activate":true,
 "protein_calculation":{
   "basis":"actual_weight",
   "bmi_used":24.50,
   "actual_weight_kg":75.00,
   "reference_weight_kg":null,
   "calculation_weight_kg":75.00,
   "protein_per_kg":1.20,
   "target_g":90.0,
   "calculation_engine_version":"2.0.0"
 },
 "calculation_warnings":[]
}
```

Basis values: `actual_weight`, `adjusted_weight`. Warning entries have `code`, `severity`, `dimension`, `value`, `reference_value`, `message_ar`. Carb warning codes/bounds follow H03. Non-positive raw/final allocation returns `422 NON_POSITIVE_CARBOHYDRATE_ALLOCATION`; no successful response returns `carb_clamped:true`.

Safety outcomes: `normal`, `specialist_review_required`, `very_low_energy_blocked`. Preview may return blocked results with `can_activate:false`; activation returns `422 SPECIALIST_REVIEW_REQUIRED` or `422 VERY_LOW_ENERGY_TARGET_BLOCKED`.

## 5. Target Plan Lifecycle

### `POST /target-plans/activate`

Requires `Idempotency-Key` (1-128 visible ASCII characters) and explicit `confirmed:true`. Body contains the same draft input contract as preview plus `expected_preview_hash`. It cannot submit effective date, owner, resolved outputs, calculation document, or versions.

Backend recalculates, verifies preview hash, applies H01/H03 blocks, determines current/next date, atomically updates Profile preferences and creates/transitions the plan. Returns `201` for first commit or the original status/body with `Idempotent-Replayed: true` for same key/payload. Same key/different canonical payload returns `409 IDEMPOTENCY_KEY_REUSED`. Stale preview returns `409 PREVIEW_RESULT_CHANGED` with no persistence.

### Reads

- `GET /target-plans/current?date=YYYY-MM-DD`: date-effective plan or legacy/no-source descriptor.
- `GET /target-plans/pending`: pending next-date plan or `null`.
- `GET /target-plans?cursor=&limit=`: reverse chronological history; default 20, max 100; opaque cursor.

### Pending replacement

`POST /target-plans/pending/replace` requires idempotency and explicit `replace_confirmed:true`. It returns new plan plus superseded plan summary; old pending row remains audit history. Stable conflicts: `TARGET_PLAN_ALREADY_EFFECTIVE`, `TARGET_PLAN_OVERLAP`, `NO_PENDING_TARGET_PLAN`, `PENDING_PLAN_REPLACEMENT_CONFIRMATION_REQUIRED`.

## 6. Food Contract

Existing list/read/create/update/delete routes remain owner-scoped. Create/update supports all current fields plus four exact nullable nutrients, controlled primary category/kind/group status/completeness, source, ingredients, and NOVA structures. Numeric `0` is retained; null is unknown.

Food response adds:

```json
{
 "nutrition_source":{"type":"official_product_label","name":"Label","reference":null,"reliability":"high","reliability_rules_version":"1.0.0"},
 "ingredients":{"text":null,"source_type":null,"source_name":null,"source_reference":null},
 "nova":{"classification":"unknown","review_status":"reviewed","rules_version":"1.0.0"},
 "primary_category_key":"dairy_fortified_alternatives",
 "food_kind":"simple",
 "group_data_status":"known",
 "group_data_completeness":"complete",
 "group_contributions":[], "analytical_traits":[]
}
```

The client cannot submit reliability or rules versions. Contributions are replaced atomically as a complete submitted set on create/update; each has group key, optional subtype, amount per 100 basis, and known/estimated status. The client does not send unit. Duplicate groups, zero/out-of-range amounts, incompatible subtype, or sum >100 return `422` stable validation codes.

Source name is required for non-unknown source types. Ingredient source is required when text is supplied; source name is required for known types. Saving a NOVA selection sets `reviewed`; `unknown+reviewed` is valid. Legacy `category`/`data_source` remain response compatibility fields; ambiguous vitamin/folate fields are exposed under `legacy_nutrition` and never populate exact fields.

Hard delete returns `204`, cascades classification children, clears Diary live Food links, and never alters snapshots. Cross-owner/missing IDs both return `404 RESOURCE_NOT_FOUND`.

## 7. Diary Contract

### Create

`POST /diary/entries` accepts only `food_id`, `entry_date`, `meal_type`, `quantity` (and legacy optional client ID only under its characterized compatibility rule). Unknown keys such as snapshot, totals, owner, target plan, provenance, or versions return `422 NON_AUTHORITATIVE_FIELD`.

Backend resolves owner Food, date target provenance, constructs/validates Snapshot v2, and commits atomically. Response may retain normalized fields and adds `snapshot_schema_version:2`, nullable `target_plan_id`, and `target_provenance`.

### Update/delete

`PATCH /diary/entries/{id}` accepts only `quantity` and/or `meal_type`. Food/date/snapshot/binding changes return `422 IMMUTABLE_DIARY_ENTRY_FIELD`; changing Food/date requires delete/create. Delete returns `204`.

## 8. Diary Summaries and Truthful Aggregation

Day and week summaries are Principal-scoped and resolve historical targets by Diary date. Every Registry nutrient participating in coverage returns:

```json
{
 "key":"fiber_g", "amount":18.0,
 "known_entry_count":3, "total_entry_count":4,
 "coverage_percent":75.0, "coverage_state":"partial",
 "amount_qualifier":"at_least",
 "target":{"type":"minimum","value":30.0,"unit":"g","source":"versioned_plan"},
 "evaluation":"indeterminate_partial_coverage",
 "progress_percent":null, "remaining":null, "available":null
}
```

Empty: amount/coverage null, no evaluation. All unknown: amount null, coverage `0`, qualifier unavailable. Partial: known sum and `at_least`; asymmetric H11 evaluation only. Complete: exact amount and full target evaluation. Overall coverage is arithmetic mean of included nutrient coverage; null on empty day.

Malformed/unsupported snapshot prevents numeric summary and returns `409 DIARY_SUMMARY_DATA_INTEGRITY_ERROR` with nested owner-visible entry references and cause codes `UNSUPPORTED_DIARY_SNAPSHOT_VERSION` or `INVALID_DIARY_SNAPSHOT_DATA`. It is never partial network failure, zero, or silent omission.

## 9. Compatibility and Deprecation

- Existing top-level target/macronutrient fields remain.
- `carb_clamped` remains additive-deprecated and always false on success; removal requires a major API change.
- Snapshot v1 remains readable but raw snapshot JSON is not a public write contract.
- Existing route purposes remain; new lifecycle capabilities are additive.
- Legacy Food fields remain readable throughout Wave 1.
- Generated TypeScript is types-only.

## 10. Loading, Failure, and Localization

API returns stable machine codes; approved Arabic message intent is server-provided for safety/domain errors, while reusable UI labels come from Registry/Frontend localization contracts. Blank alert bodies are prohibited. Retries are safe only for GET or mutations with approved idempotency.

## 11. Deferred Scope

No public registration, multi-profile, shared Foods, offline sync, direct gram/ml logging, Progress/Analysis, clinical override, AI classification, recipe engine, or unrelated route redesign.
