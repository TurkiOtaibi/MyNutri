# Wave 1 Architecture and Security ADRs

## Artifact Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-ADR-13` |
| Version | `1.0` |
| Status | `Approved — Architecture and Security` |
| Wave | `Wave 1 — Nutrition & Data Foundation` |
| Implementation authorization | `No` |
| Owner | Architecture / Security |
| Product Owner approval | Approved |
| Architecture approval | Approved |
| Security approval | Approved |
| Approval date | `2026-07-16` |
| Approval basis | `13A_WAVE1_ARCHITECTURE_SECURITY_REVIEW.md` |
| Critical issues at approval | `0` |
| High issues at approval | `0` |
| Substantive contradictions at approval | `0` |
| Product Owner decisions remaining at approval | `0` |
| Pinned commit/revision | `c7c48746715d24238acd70cd4eea137bf0f87cfd` |
| Implemented Baseline Code Commit | `d6caf0a124e5ffec63cabd1972ed742b3e7fc8bd` |
| Governing Register Commit | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` |
| Governance Decision Direction Commit | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` |

This is the first formal Wave 1 freeze artifact. It translates approved product, contract, architecture, and migration directions into reviewable system boundaries. It does not approve a physical schema, endpoint payload, migration revision, implementation, deployment, or release.

The artifact is brownfield-only. Existing myNutri Foods, Diary, Add Food, Profile, online-only behavior, API compatibility, and regression suites are baseline assets. myNutri and NutriPlan are separate projects. No NutriPlan entity, decision, or scope is used here.

## Governing Sources

| Artifact | Role |
|---|---|
| `PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md` | Governing product intent and wave boundary |
| `10_C01_APPROVED_PRODUCT_OWNER_DECISION.md` | Durable Principal ownership direction |
| `11_C02_APPROVED_PRODUCT_OWNER_DECISION.md` | Modular freeze-package governance |
| `13_H01_APPROVED_PRODUCT_OWNER_DECISION.md` | Deficit and low-energy safety direction |
| `14_H02_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Protein calculation provenance direction |
| `H03_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Carbohydrate warning and rejection direction |
| `H04_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Immutable Target Plan lifecycle direction |
| `H05_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Canonical Nutrition Registry direction |
| `H06_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Food-group contribution and trait direction |
| `H07_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Source, reliability, ingredients, and NOVA direction |
| `H08_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Snapshot v2 and Target Plan binding direction |
| `H09_APPROVED_ARCHITECTURE_MIGRATION_DIRECTION.md` | Alembic, rollout, and rollback direction |
| `H10_APPROVED_RULE_VERSIONING_DIRECTION.md` | Rules package and versioning direction |
| `H11_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Truthful nullable aggregation direction |
| `12_WAVE1_FREEZE_INDEX.md` | Draft authority map and dependency manifest |

## Current Repository Evidence Summary

At the merged governance checkpoint, the runtime is FastAPI, SQLModel, PostgreSQL, Alembic, and Next.js. Relevant evidence includes:

- `backend/app/core/auth.py` validates one bearer token, returns no Principal context, and currently bypasses authentication when the configured token is empty.
- `backend/app/services/profile.py`, `food.py`, `diary.py`, and `aggregation.py` query user data without an ownership predicate.
- `backend/app/main.py` invokes `SQLModel.metadata.create_all` through `create_db_and_tables` during application startup.
- `backend/alembic/versions/0001_initial.py` through `0003_diary_meal_type.py` form the current migration chain.
- `backend/app/services/calc.py` and `nutrients.py` contain current Backend calculations and a six-nutrient definition set; `frontend/lib/nutrients.ts` independently duplicates nutrient metadata.
- `backend/app/models.py` has no Principal or Target Plan model. Diary snapshots are unversioned JSON/JSONB documents with a nullable live Food relationship.
- `backend/app/services/aggregation.py` resolves all historical week targets from the mutable current Profile.
- `backend/app/services/diary.py` scales known snapshot values, but `NutritionTotals` defaults and aggregate behavior can present all-unknown additional nutrients as zero.
- `backend/app/schemas.py` and `backend/app/services/calc.py` use server-local `date.today`; `frontend/lib/dates.ts` uses browser-local dates; no runtime IANA timezone authority is configured. `Asia/Riyadh` appears in Playwright configuration only.

These are baseline observations, not permission to implement before the complete freeze package is approved.

---

## ADR-001 — Durable Single-Principal Ownership

### ADR ID

`ADR-001`

### Title

Durable single-Principal ownership for all user-created data.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-000`, `PD-002`, `PD-023`, `PD-024`, `PD-025`, `PD-029`; `DEC-C01-10`.

### Context

myNutri v1 is a personal single-principal product, but the implemented schema has no durable owner. A bearer token currently gates routes without identifying an owner. Token rotation would therefore have no durable ownership mapping, and future Principal-scoped expansion data cannot be isolated safely.

### Current Repository Evidence

- `Profile`, `Food`, and `DiaryEntry` in `backend/app/models.py` have no Principal foreign key.
- `get_profile` returns the first Profile row.
- Food and Diary list, read, update, delete, duplicate, and aggregation operations have no owner predicate.
- Current tests use one token and do not prove isolation between two Principals.

### Decision

The Backend uses a durable local Principal with a stable internal identifier independent from bearer tokens. The deployment explicitly provisions one Principal, and one Profile is allowed per Principal. Authentication maps each valid credential to that Principal.

All current and future user-created records are Principal-bound. List, read, update, delete, aggregation, uniqueness, duplicate detection, and lifecycle operations are scoped by authenticated Principal. The client cannot submit authoritative `principal_id`, `owner_id`, or `user_id` values. Token rotation changes credentials only and cannot transfer ownership.

Unauthorized and nonexistent resource identifiers use the same outward non-enumerating resource response. The released UX remains single-principal and adds no account or Profile switching behavior.

### Alternatives Considered

- **Token value as owner key:** rejected because credential rotation would change or transfer ownership.
- **Global singleton rows without ownership:** rejected because it cannot enforce isolation or safely evolve.
- **External identity-provider subject as the only owner key:** deferred; a future provider may map to the durable local Principal.

### Consequences

Services and persistence require explicit ownership scope. Existing records require one explicit fail-closed ownership migration. The product remains single-principal while tests exercise at least two Principals.

### Security Impact

This closes the architectural path for cross-owner reads and mutations. Database constraints and service queries must reinforce each other; route authentication alone is insufficient.

### Compatibility Impact

Existing user-facing behavior and route purposes remain. Frontend payloads do not gain authoritative ownership fields. Existing record identifiers remain stable.

### Migration Impact

Use Expand → Migrate → Contract. Provision exactly one deployment Principal, backfill existing Profile, Food, and Diary Entry rows, reconcile counts, reject ambiguous provisioning, then enforce ownership and owner-aware uniqueness. Do not infer ownership or rewrite nutrition history.

### API Impact

Existing APIs become Principal-scoped. Cross-owner and missing IDs share a non-enumerating resource response. Exact error envelopes remain for Artifact 15.

### Testing Obligations

Use at least two Principals to prove isolation for every CRUD operation, list, aggregate, uniqueness rule, duplicate rule, Target Plan, and snapshot binding. Prove token rotation preserves ownership and client owner fields are rejected or ignored as non-authoritative.

### Deferred Scope

Public registration, account management, Profile switching, multiple Profiles per Principal, public/shared Foods, and external identity-provider integration.

### Unresolved Technical Details

Physical key types, foreign keys, owner-aware indexes, provisioning command, transaction split, and database policy belong to Artifacts 14 and 16. Exact outward errors belong to Artifact 15.

### Approval Ownership

Architecture and Security approve the boundary; Engineering/Data approve physical enforcement; API approves outward contracts; QA approves isolation evidence.

### Closure Evidence Required

Approved Artifacts 14–16 and 20–21, executable two-Principal isolation tests, successful fail-closed migration rehearsal, and evidence that every user-data query is owner-scoped.

---

## ADR-002 — Authentication Context and Authorization Boundary

### ADR ID

`ADR-002`

### Title

Typed authenticated Principal context and fail-closed authorization.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-002`, `PD-023`, `PD-024`, `PD-025`, `PD-029`; `DEC-C01-10`.

### Context

Authentication must establish both credential validity and the durable Principal used by services. A route-level pass/fail dependency that returns no identity cannot enforce owner scope throughout the service layer.

### Current Repository Evidence

- `require_single_user` in `backend/app/core/auth.py` returns `None`.
- An empty configured token currently returns successfully instead of failing closed.
- Services accept `Session` and identifiers but no typed Principal context.
- Frontend and tests default to `dev-token`; production configuration requirements are not distinguished.

### Decision

The authentication dependency returns a typed, immutable Principal context containing the stable local Principal identifier and only the authorization metadata required by downstream services. Every user-data service method requires that context; global user-data queries are prohibited.

Missing or invalid credentials return stable `401` semantics. Valid credentials requesting a missing or cross-owner resource receive the same non-enumerating `404` semantics. Principal-scoped reads and writes occur inside owner-scoped transaction boundaries. Missing or invalid production authentication configuration fails application preflight or protected requests closed. Normal product operations never use Service Role.

### Alternatives Considered

- **Boolean route guard only:** rejected because services cannot scope data by owner.
- **Client-provided owner identity:** rejected because the client is not authoritative.
- **External identity provider now:** deferred and not selected by this ADR.

### Consequences

Route dependencies and service signatures change additively around a typed context. Background or administrative operations, if later approved, need an explicit separate security boundary rather than bypassing ownership.

### Security Impact

The context prevents confused-deputy and horizontal-access paths when consistently required. Logs must not expose bearer credentials, and error behavior must not enumerate identifiers.

### Compatibility Impact

Current bearer-token transport may remain during v1. Credential rotation maps to the same Principal. No account-management UI is introduced.

### Migration Impact

Authentication mapping can become authoritative only after the deployment Principal is explicitly provisioned. Deployment must fail closed when the mapping is absent or ambiguous.

### API Impact

Protected routes retain authentication headers while gaining stable authorization semantics. Exact challenge headers, error body, and credential rotation procedure remain for Artifact 15 and deployment documentation.

### Testing Obligations

Test missing, malformed, wrong, and rotated credentials; missing production configuration; cross-owner ID equivalence; service calls without Principal context; and absence of Service Role in normal flows.

### Deferred Scope

External identity providers, registration, password/account recovery, roles, account management, and specialist identities.

### Unresolved Technical Details

Principal-context Python type, credential-to-Principal lookup representation, configuration validation phase, audit fields, and exact `401`/`404` envelopes.

### Approval Ownership

Architecture and Security; API for HTTP behavior; Engineering for dependency injection; QA for security verification.

### Closure Evidence Required

Approved authentication ADR details and API contract, production fail-closed configuration tests, two-Principal service tests, and query-level evidence that no global user-data path remains.

---

## ADR-003 — Alembic Schema Authority

### ADR ID

`ADR-003`

### Title

Alembic as sole deployed and integration schema authority.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-008`, `PD-009`, `PD-011`, `PD-012`, `PD-014`, `PD-023`, `PD-024`, `PD-026`, `PD-029`; `ADR-DIR-H09`.

### Context

Wave 1 requires additive, ordered, reproducible schema evolution. Runtime metadata creation can hide migration gaps and produce a schema that was never proven through the migration chain.

### Current Repository Evidence

- `backend/app/main.py` calls `create_db_and_tables` at startup.
- `backend/app/db/session.py` implements that function with `SQLModel.metadata.create_all`.
- Alembic revisions are ordered `0001_initial → 0002_foods_v1_per_basis → 0003_diary_meal_type`.
- Unit tests use `create_all`; current integration evidence does not consistently construct PostgreSQL through Alembic.

### Decision

Alembic is the sole schema authority for runtime, local application development, deployed, integration, migration-verification, and release environments. Runtime `metadata.create_all` and automatic runtime migrations are prohibited.

`create_all` is limited to unmistakably isolated disposable unit-test fixtures that are not imported by runtime and do not count as migration evidence. Integration and migration tests use disposable PostgreSQL databases upgraded by Alembic.

Revisions 0001–0003 are immutable. Wave 1 uses additive nullable-first revisions, explicit preflight, reader-before-writer deployment, and retains legacy fields/readers. Rollback after new-format writes uses a compatible application reader; lossy production schema downgrade is prohibited.

### Alternatives Considered

- **Continue runtime `create_all`:** rejected because it creates a second schema authority.
- **Automatic startup `alembic upgrade head`:** rejected because startup must not mutate schema silently.
- **Squash 0001–0003:** rejected because the verified baseline chain is immutable.

### Consequences

Deployment and local startup require an explicit migration step. Runtime may perform a read-only revision compatibility check and fail clearly on missing, behind, divergent, or unsupported schema state.

### Security Impact

Restricting schema mutation to approved migration operations narrows privileged database access. Application credentials should not require schema-owner privileges during normal runtime.

### Compatibility Impact

Readers support old and new rows before new writers activate. No legacy field or Snapshot v1 reader is removed in Wave 1.

### Migration Impact

The logical order follows H09: Principal expansion/provision/backfill/enforcement; Food fields and normalized classification structures; Target Plans and versions; Diary ownership/linkage/version support; compatible readers; then controlled writers.

### API Impact

The API must not expose new write behavior until its database revision and compatible readers are present. A schema incompatibility is an operational startup/preflight failure, not a partial API mode invented at runtime.

### Testing Obligations

Prove one Alembic head, fresh upgrade, upgrade from populated 0003, migration ledger consistency, ownership reconciliation, mixed-format readers, permitted downgrade/re-upgrade, compatible application rollback, and absence of runtime `create_all`.

### Deferred Scope

Contract/removal migrations, legacy field removal, Snapshot v1 reader removal, and runtime auto-migration.

### Unresolved Technical Details

Exact revision split, preflight command, privilege separation, downgrade support per revision, writer-enable mechanism, and CI commands belong to Artifacts 14, 16, and 20.

### Approval Ownership

Architecture, Security, Engineering/Data, and QA.

### Closure Evidence Required

Approved physical model and migration plan, executable PostgreSQL rehearsals, model-versus-migration drift check, and runtime-startup test proving no schema mutation.

---

## ADR-004 — Backend-Owned Nutrition Rules Package

### ADR ID

`ADR-004`

### Title

Typed, declarative, versioned Backend nutrition-rules authority.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-002`, `PD-009`, `PD-010`, `PD-012`, `PD-014`, `PD-025`, `PD-026`; `DEC-H05`, `DEC-H06`, `DEC-H07`, `ADR-DIR-H10`.

### Context

Wave 1 calculations, nutrients, food groups, source reliability, NOVA, and snapshot interpretation must share one authority and retain historical version provenance.

### Current Repository Evidence

- `backend/app/services/calc.py` contains the current calculation engine.
- `backend/app/services/nutrients.py` defines six additional nutrients and four target types.
- `frontend/lib/nutrients.ts` independently duplicates labels, order, target metadata, and fallback values.
- No canonical manifest, rule hash, Registry endpoint, or independent version bundle exists.

### Decision

One typed, declarative Backend package owns versions, nutrients, macro policy, deficit policy, food groups, source reliability, NOVA, snapshot schema, and the reserved future analysis boundary. Definitions are machine-readable; calculations are pure, deterministic, decimal-safe where boundaries require it, and free of runtime side effects.

The database stores resolved historical results and applicable version references, not editable current rule definitions. TypeScript may contain generated types only and cannot own labels, order, target values, formulas, mappings, or meanings.

Independent initial versions follow `ADR-DIR-H10`: nutrition Registry `1.0.0`, calculation engine `2.0.0`, food-group rules `1.0.0`, source-reliability rules `1.0.0`, NOVA rules `1.0.0`, Registry schema `1`, and Snapshot schema `2`. Analysis rules remain reserved and inactive until Wave 3. A deterministic canonical manifest and hash detect released-content mutation and missing semantic version bumps.

### Alternatives Considered

- **Independent Backend and Frontend registries:** rejected because they drift.
- **Database-editable rules:** rejected because Wave 1 has no governed rule-administration product.
- **One umbrella version only:** rejected because independent provenance must remain visible.

### Consequences

Existing rules are reorganized behind one authority without a greenfield rewrite. Historical records remain resolved and are not recalculated with current rules.

### Security Impact

No client or database editor can alter calculation authority. Manifest integrity is verification evidence; it is not a cryptographic authorization mechanism.

### Compatibility Impact

Existing top-level target fields remain. Additive Registry metadata and generated types support migration. Legacy records remain explicitly unversioned.

### Migration Impact

Add nullable version fields where required. New Target Plans and Snapshot v2 require applicable non-null versions; current versions are never backfilled into historical records.

### API Impact

The Registry API exposes metadata and a version bundle, not Python source or personalized targets. Unsupported versions and schemas fail explicitly with stable meanings finalized in Artifact 15.

### Testing Obligations

Prove deterministic calculations and manifest serialization, required semantic version bumps, immutable released versions, unsupported-version errors, legacy null-version behavior, and agreement between package and Registry API.

### Deferred Scope

Wave 3 analysis activation, rule administration, Frontend rule editing, offline rule authority, and replaying every legacy calculation implementation.

### Unresolved Technical Details

Exact Python modules, canonical serialization, hash artifact, decimal types, package release process, and CI version-diff mechanism.

### Approval Ownership

Architecture and Engineering own package boundaries; Security reviews integrity and authority; API owns exposed metadata; QA owns determinism and versioning evidence.

### Closure Evidence Required

Approved module/manifest contract, Registry and persistence contracts, golden calculations, semantic-version CI tests, and proof that no independently authoritative Frontend rules remain.

---

## ADR-005 — Hybrid Immutable Target Plan Aggregate

### ADR ID

`ADR-005`

### Title

Hybrid relational/document Target Plan with immutable calculation content.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-005`, `PD-006`, `PD-007`, `PD-008`, `PD-023`, `PD-024`, `PD-025`, `PD-026`, `PD-029`; `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`.

### Context

The current Profile is mutable and targets are recalculated on read. Wave 1 requires an explainable immutable result that applies by Diary date without inventing historical plans.

### Current Repository Evidence

- No Target Plan model or route exists.
- Profile save mutates one Profile row and commits immediately.
- Preview calculates without persistence, but Profile responses always calculate current targets.
- Weekly summaries use current Profile targets for every historical date.

### Decision

Target Plan is a hybrid aggregate. Relational fields govern identity, Principal/Profile ownership, lifecycle, calendar-date effective interval, activation, idempotency, predecessor/supersession, and applicable versions. A Backend-validated versioned calculation document preserves authoritative inputs, resolved outcomes, warnings, safety state, additional targets, custom settings, and rule versions.

`effective_from` is inclusive and `effective_to` exclusive. A genuinely new Profile with no prior target source may explicitly activate its first plan for the current Diary date. Existing legacy Profiles and subsequent changes activate for the next Diary date. Backdating and arbitrary future scheduling are prohibited.

At most one plan is effective for a Principal/date and at most one next-date pending plan exists. Replacing a pending plan preserves the old plan as superseded-before-effective audit history. Preview never persists. Activation requires explicit confirmation and idempotency, atomically updates approved Profile inputs/preferences and creates or transitions the immutable plan. Activated calculation content is never edited or rewritten.

### Alternatives Considered

- **Mutable current-target row:** rejected because it cannot preserve history.
- **Document-only plan:** rejected because lifecycle and non-overlap enforcement need relational constraints.
- **Relational column for every calculation detail:** not selected because versioned provenance evolves; core lifecycle remains relational.
- **Fabricated historical plans:** prohibited.

### Consequences

Current, proposed, and scheduled targets become distinct concepts. Backend date resolution is authoritative. The minimal Profile confirmation states are Wave 1; full Progress review UI remains deferred.

### Security Impact

Every plan and lifecycle transition is Principal-scoped. Concurrency and idempotency prevent duplicate or overlapping plans. Calculation documents must be server-generated and validated.

### Compatibility Impact

Existing Profile routes remain baseline assets pending an additive compatibility plan. Dates before first versioned activation remain legacy/unversioned. Existing top-level target fields may continue in compatible responses.

### Migration Impact

Add relational lifecycle and versioned document storage without fabricating history. Existing Profiles remain inputs. First activation establishes the first plan according to new-versus-legacy date rules.

### API Impact

Requires additive non-persisting preview, explicit activation, current effective plan, next scheduled plan, history, and pending replacement capabilities. Exact endpoints and payloads belong to Artifact 15.

### Testing Obligations

Test immutability, no overlap, first/new and first/legacy dates, no backdating, scheduled replacement audit, atomic rollback, idempotent replay, payload mismatch, concurrent activation, H01/H03 rejection, and historical date resolution.

### Deferred Scope

Arbitrary scheduling, scheduling date picker, clinician plans/override, multiple Profiles, Progress UI, four-week review UI, and historical plan fabrication.

### Unresolved Technical Details

Physical lifecycle enum, JSON schema, constraints, effective-date authority from ADR-010, idempotency storage, pagination, error envelopes, and Profile-route compatibility.

### Approval Ownership

Architecture, Security, Engineering/Data, API, BA/UX, and QA.

### Closure Evidence Required

Resolved ADR-010, approved Artifacts 14–20, database non-overlap/concurrency evidence, atomic activation tests, and traceability to H01–H04.

---

## ADR-006 — Snapshot v2 Boundary

### ADR ID

`ADR-006`

### Title

Backend-written versioned Diary Snapshot v2 with immutable target binding.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-008`, `PD-013`, `PD-014`, `PD-023`, `PD-024`, `PD-025`, `PD-026`; `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`.

### Context

Historical Diary values must survive Food edits, rule changes, and Target Plan changes. The new format must coexist with existing snapshots without false enrichment or silent fallback.

### Current Repository Evidence

- `DiaryEntry.nutrition_snapshot` is JSON/JSONB with no schema-version field.
- `make_snapshot` copies current Food values and serving metadata.
- Quantity edits currently rewrite `logged_quantity` and `calculated_totals` inside the legacy snapshot document.
- No Principal, Target Plan link, target provenance, Registry version, source reliability, NOVA, group contribution, or trait snapshot fields exist.

### Decision

Snapshot v2 is a Backend-generated and Backend-validated JSONB envelope. Diary Entry keeps relational Principal ownership, nullable Target Plan linkage, target provenance, snapshot schema version, entry date, meal type, and quantity.

Approved provenance meanings are `versioned_plan`, `legacy_unversioned`, and `no_target_source`. The Backend resolves provenance and the effective Target Plan from authenticated Principal plus entry date. The binding is immutable.

When a genuinely new Profile with no prior target source activates its first plan for the current Diary date, same-date entries for that Principal with `no_target_source` and no Target Plan are bound to the new plan in the activation transaction. Their nutrition snapshots are not modified, and prior-date entries are not rebound. For an existing legacy user, the first versioned plan begins on the next Diary date; current-date `legacy_unversioned` entries remain unbound.

Snapshot values represent one captured logging unit; quantity is a separate multiplier. Quantity or meal updates do not rebuild or mutate Snapshot v2. The Backend never rereads Food for those updates. The client cannot submit authoritative snapshots, totals, Target Plan IDs, provenance, or versions.

Dedicated v1 and v2 readers normalize valid data internally. V1 is never rewritten or enriched. Unknown versions do not fall back to v1. Malformed or unsupported data produces explicit integrity failure and cannot be zeroed or silently omitted. After v2 writes begin, application rollback requires a v2-capable reader.

### Alternatives Considered

- **Fully normalized snapshot columns:** not selected because the versioned historical envelope evolves and would couple readers to current schema.
- **Client-generated snapshot:** rejected as untrusted and inconsistent.
- **Rewrite v1 as v2:** rejected because it would fabricate unavailable history.
- **Recalculate from current Food:** rejected because snapshots are immutable history.

### Consequences

Writers become transactional and version-aware. Readers must preserve v1 compatibility throughout Wave 1. Quantity scaling occurs at aggregation time from immutable captured-unit values.

### Security Impact

Food lookup, snapshot construction, and Target Plan resolution occur in one Principal-scoped Backend transaction. Client-supplied ownership or provenance is never trusted.

### Compatibility Impact

Existing normalized response fields may remain. Raw JSONB need not become a public Frontend contract. Existing v1 entries remain readable and unmodified.

### Migration Impact

Add nullable ownership/linkage/version fields, deploy dual readers before v2 writer, validate existing v1 rows, then enable writer. No v1 content backfill or enrichment.

### API Impact

Create accepts user inputs equivalent to Food, date, meal, and quantity only. Update permits quantity and meal only. Changing Food/date uses delete-and-create. Exact rejection/ignore policy for extra client fields belongs to Artifact 15.

### Testing Obligations

Test Food edit/delete immutability, quantity scaling, meal movement, v1/v2 mixed reads, known zero/null, unknown versions, malformed documents, target-date binding, same-date first-plan binding, legacy behavior, and rollback compatibility.

### Deferred Scope

Direct gram/ml logging, full ingredients snapshot, snapshot rewriting, offline writes, and historical enrichment.

### Unresolved Technical Details

Exact JSON schema, validation dispatch, relational columns, same-date binding query, integrity response envelope, writer feature gate, and v1 shape discriminator.

### Approval Ownership

Architecture, Security, Engineering/Data, API, and QA.

### Closure Evidence Required

Approved schema and API contracts, dual-reader fixtures, populated migration rehearsal, integrity-failure tests, and proof that v2 writes cannot occur before compatible readers deploy.

---

## ADR-007 — Backend Registry and Frontend Metadata Boundary

### ADR ID

`ADR-007`

### Title

Authoritative runtime Nutrition Registry with non-authoritative Frontend types.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-009`, `PD-010`, `PD-011`, `PD-012`, `PD-014`, `PD-025`, `PD-026`; `DEC-H05`, `DEC-H06`, `DEC-H07`, `ADR-DIR-H10`.

### Context

The Frontend needs labels, units, order, target descriptors, group/trait definitions, source mappings, NOVA meanings, and versions without becoming a second rule authority.

### Current Repository Evidence

- Backend and Frontend each contain their own six-nutrient metadata.
- The Frontend metadata includes labels, ordering, types, sources, and fallback target values.
- No `/nutrition/registry` route exists.
- `apiFetch` uses `cache: "no-store"`; no Registry-specific query/session cache exists.

### Decision

An additive read-only `GET /nutrition/registry` capability exposes authoritative Backend-owned nutrient, food-group, analytical-trait, source-reliability, NOVA, schema, and version metadata. It also exposes the deterministic rules-manifest hash and compatibility metadata approved by H10.

The Frontend consumes this runtime metadata and may cache it in memory or a query/session cache. It has no independent fallback Registry. Generated TypeScript contains types only. When Registry metadata is unavailable or its schema is unsupported, the Frontend shows a truthful loading/error/incompatible state and blocks Registry-dependent mutations and Target Plan activation. It does not fabricate metadata.

Personalized resolved targets remain in Profile Preview and Target Plan contracts, not the Registry endpoint.

### Alternatives Considered

- **Static TypeScript Registry:** rejected because it can drift from Backend rules.
- **Generated TypeScript values:** rejected; generation is types-only.
- **Persistent offline fallback Registry:** rejected by the online-only architecture and authority boundary.
- **Database-managed Registry:** rejected for Wave 1.

### Consequences

Registry-dependent screens require a runtime dependency and explicit unavailable/incompatible states. Unrelated baseline behavior may continue only when still truthful without Registry metadata.

### Security Impact

The Registry is read-only and contains no user nutrition history. Authentication and cache visibility still require explicit review to avoid accidental policy inconsistency or stale incompatible metadata.

### Compatibility Impact

The capability is additive. Existing top-level fields remain. Old Frontend versions must not receive new writer behavior they cannot interpret; version/schema negotiation is explicit.

### Migration Impact

No Registry metadata rows are required. Persistence changes concern exact Food fields and version references defined in later artifacts.

### API Impact

Artifact 15 must define authentication, caching/ETag semantics, version bundle, schema incompatibility, stable errors, and retry behavior without exposing Python source.

### Testing Obligations

Prove API/package agreement, all stable keys, cache invalidation by version/hash, unsupported-schema blocking, no fallback rules, generated types-only boundary, and personalized-target exclusion.

### Deferred Scope

Offline rule storage, Registry administration UI, AI classification, nutrient provenance, and personalized target calculation in the Frontend.

### Unresolved Technical Details

Endpoint authentication, cache headers, client query-cache lifetime, schema compatibility range, OpenAPI generation command, and unavailable-state ownership.

### Approval Ownership

Architecture, Security, API, Frontend Engineering, BA/UX, and QA.

### Closure Evidence Required

Approved Registry API and UI-state contracts, one Backend metadata source, generated-type audit, unavailable/incompatible tests, and proof that Registry-dependent writes fail closed.

---

## ADR-008 — Backend-Authoritative Diary Aggregation

### ADR ID

`ADR-008`

### Title

Principal-scoped nullable Diary aggregation and historical target resolution.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-002`, `PD-008`, `PD-009`, `PD-013`, `PD-014`, `PD-023`, `PD-025`, `PD-029`; `DEC-H05`, `DEC-H08`, `ADR-DIR-H10`, `DEC-H11`.

### Context

Nutrient totals and coverage must distinguish explicit zero, unknown, partial coverage, complete coverage, empty days, and integrity failure. Historical evaluation must use the target source for the Diary date.

### Current Repository Evidence

- `NutritionTotals` initializes core values to numeric zero and additional values to null.
- `add_totals` skips null inputs and adds known values into `data.get(key) or 0`, allowing all-unknown aggregate state to collapse into numeric zero after aggregation flows.
- `weekly_summary` is global, uses current Profile targets for every day, and has no coverage-state response.
- Frontend nutrient details currently derive presentation from totals rather than an authoritative semantic aggregate contract.

### Decision

The Backend owns Principal-scoped nutrient aggregation, known-entry counts, total-entry counts, coverage, amount qualifiers, target resolution, and evaluation semantics. One aggregate is returned for every applicable Registry nutrient participating in Diary coverage.

Explicit zero is known; null is unknown. States are `no_entries`, `all_unknown`, `partial`, and `complete`; qualifiers are `unavailable`, `at_least`, and `exact`. All-unknown amount is null with zero coverage. Partial amount is a confirmed minimum. Malformed or unsupported snapshots trigger integrity failure and are not silently omitted.

Targets resolve from the versioned plan, legacy source, or no source for the Diary date. The mutable current Profile never reinterprets historical days. The Frontend renders Backend semantics and does not independently aggregate, infer coverage, convert null to zero, or determine achievement.

### Alternatives Considered

- **Frontend aggregation:** rejected because it duplicates rules and can mis-handle null.
- **Treat missing as zero:** rejected as false precision.
- **Silently skip malformed snapshots:** rejected because totals would be understated.
- **Use current Profile targets for history:** rejected because it rewrites meaning.

### Consequences

Summary responses become semantic rather than totals-only. Partial-coverage target evaluation follows the asymmetric H11 rules; definitive remaining/available amounts are suppressed where evidence is incomplete.

### Security Impact

All entries, plans, counts, and integrity details are Principal-scoped. Affected entry identifiers, when exposed, are visible only to their owner under non-enumerating rules.

### Compatibility Impact

Existing core totals may remain as additive compatibility fields where truthful. New nullable/coverage semantics must not be collapsed by older serializers. Snapshot v1 remains supported.

### Migration Impact

No H11-specific backfill. Snapshot v2 and Target Plan migrations provide future provenance; legacy rows retain unknowns.

### API Impact

Artifact 15 defines aggregate fields, counts, precision, evaluation meanings, target references, integrity errors, and compatibility behavior.

### Testing Obligations

Test empty, all-unknown, partial, complete, known-zero, mixed v1/v2, each target type, asymmetric partial evaluation, malformed/unsupported snapshots, overall coverage, historical targets, and two-Principal isolation.

### Deferred Scope

Seven-day Nutrition Pattern Analysis, Progress UI, weekly recommendations, clinical interpretation, and offline aggregation.

### Unresolved Technical Details

Aggregation service interface, precision, integrity-failure granularity, compatibility fields, response localization boundary, and query-performance indexes.

### Approval Ownership

Architecture, Security, API, BA/UX, and QA.

### Closure Evidence Required

Approved API/UI contracts, centralized Backend aggregation tests, historical target fixtures, integrity-error tests, and proof that TypeScript has no authoritative aggregation implementation.

---

## ADR-009 — Idempotency and Concurrency

### ADR ID

`ADR-009`

### Title

Principal-scoped idempotency, replay, and concurrent mutation boundaries.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-008`, `PD-023`, `PD-024`, `PD-025`, `PD-026`, `PD-029`; `DEC-C01-10`, `DEC-H04`, `DEC-H08`.

### Context

Target activation and pending-plan replacement can create conflicting lifecycle records under retries or concurrent requests. Existing Food and Diary create flows also accept optional client IDs, but those IDs are not an authorization or complete replay contract.

### Current Repository Evidence

- Profile, Food, and Diary services commit mutations independently.
- Target Plan storage and activation do not exist.
- Food and Diary create schemas accept optional IDs; an existing ID can route to update behavior.
- No `Idempotency-Key` storage, payload fingerprint, replay record, database non-overlap constraint, or concurrent-write test exists.

### Decision

Target Plan activation and scheduled-plan replacement require a stable request identity equivalent to `Idempotency-Key`. Within one Principal scope, the same key and semantically identical request returns the original committed result; the same key with different content is rejected. A failed transaction cannot leave a reusable success record or partial Profile/plan state.

Database constraints and Backend transactions enforce at most one plan effective for a Principal/date and one pending next-date plan. Pending replacement, lifecycle audit, Profile preference update, and plan activation are one transaction. Locking or conflict control must prevent duplicate or overlapping plans under concurrency.

Food and Diary mutation contracts must explicitly identify which operations require replay protection, preserve any approved client-ID compatibility, and ensure client-generated IDs never bypass Principal scope, duplicate checks, or immutable snapshot rules. This ADR does not define endpoint payloads.

### Alternatives Considered

- **Client retries without server idempotency:** rejected for Target Plan activation.
- **Idempotency key without payload binding:** rejected because key reuse could return the wrong result.
- **Application-only pre-checks:** rejected because concurrent writes require database enforcement.
- **Global idempotency namespace:** rejected because request identity is Principal-scoped.

### Consequences

The Backend needs durable or transactionally reliable replay records and canonical request comparison. Conflict and replay responses must be stable and privacy-preserving.

### Security Impact

Keys are scoped to authenticated Principal and operation. Cross-owner key reuse reveals no result. Stored request fingerprints must avoid credentials and unnecessary sensitive payload retention.

### Compatibility Impact

Existing Profile preview remains non-persisting and needs no idempotency record. Existing Food/Diary client-ID behavior requires explicit characterization before compatibility changes.

### Migration Impact

Physical idempotency storage, unique constraints, plan overlap enforcement, and lifecycle audit representation belong to Artifact 14/16. No historical replay records are fabricated.

### API Impact

Artifact 15 defines required headers, canonical request identity, replay response, payload mismatch, conflict, retry window/retention, and Food/Diary applicability.

### Testing Obligations

Test same-key replay, same-key different payload, concurrent distinct keys, transaction rollback and retry, pending replacement, cross-Principal key isolation, non-overlap constraints, and characterized Food/Diary duplicate behavior.

### Deferred Scope

Generic distributed workflow orchestration, offline synchronization replay, public API clients, and endpoint shapes not required by Wave 1.

### Unresolved Technical Details

Replay-record schema, canonical payload hashing, retention, locking strategy, database constraints, error codes, and exact Food/Diary operation coverage.

### Approval Ownership

Architecture and Security; Engineering/Data for transaction and constraint design; API for replay contract; QA for concurrency evidence.

### Closure Evidence Required

Approved physical and API contracts, deterministic replay tests, concurrent PostgreSQL evidence, atomic activation failure tests, and no cross-owner information disclosure.

---

## ADR-010 — Calendar Date and Timezone Authority

### ADR ID

`ADR-010`

### Title

Authoritative timezone for Diary calendar dates and Target Plan effectiveness.

### Status

`Approved Direction — Technical Detail Pending`

### Governing Decisions

`PD-003`, `PD-008`, `PD-013`, `PD-023`, `PD-024`, `PD-025`, `PD-026`, `PD-029`; `DEC-H04`, `DEC-H08`.

### Context

Approved behavior applies Target Plans to complete Diary calendar dates. A timezone authority is required to determine “current Diary date,” first-plan same-date activation, next-date activation, age on effective date, future-date rejection, and midnight transitions. The Product Owner has now approved one deployment-configured IANA timezone with `Asia/Riyadh` as the initial authoritative value.

### Current Repository Evidence

- Backend validation and age calculation use server-local `date.today()`.
- Frontend `todayInputValue` derives browser-local date.
- Profile birth-date display uses UTC solely to preserve a date-only value.
- Playwright sets `timezoneId: "Asia/Riyadh"`, but test configuration is not runtime product authority.
- Settings, `.env.example`, and `docker-compose.yml` contain no IANA timezone configuration.
- No Principal/Profile timezone field exists.

### Decision

Wave 1 uses one deployment-configured IANA timezone. The initial approved timezone is `Asia/Riyadh`. The Backend is authoritative for the current Diary date and next Diary date, including Diary entry dates, Target Plan effective dates, age-at-effective-date calculation, future-date validation, scheduled activation, and summaries.

Production startup fails closed when timezone configuration is absent, invalid, or not recognized as an IANA timezone. Development, tests, CI, and migration rehearsals configure the timezone explicitly. Server-host local timezone and UTC are not the user-facing Diary calendar authority, and no silent fallback is allowed. The Frontend may display dates but cannot submit, select, or infer the authoritative timezone.

Every newly activated Target Plan preserves the calendar timezone that governed its lifecycle. Changing the deployment timezone requires a formal Change Decision and must not reinterpret existing Diary dates, Target Plans, or historical snapshots.

### Alternatives Considered

#### Selected — One deployment-configured IANA timezone

The deployment explicitly configures one IANA zone, such as `Asia/Riyadh`; the Backend derives the Diary calendar date from it.

- **Advantages:** matches the single-principal deployment model; no Profile schema/UI field; deterministic server authority; closest to current test assumptions.
- **Risks:** moving the deployment or user to another zone requires an explicit operational/product change; configuration absence must fail closed for date-dependent writes.
- **Compatibility:** changes server/browser-midnight behavior from implicit local clocks to one explicit zone.

#### Not selected — Principal/Profile-owned IANA timezone

The durable Principal or Profile stores an IANA zone used by Backend date resolution.

- **Advantages:** supports future travel or identity-provider mapping without changing ownership; explicit per-owner history.
- **Risks:** adds schema, API, migration default, validation, and potentially UI behavior not yet approved; changing timezone affects next/current date boundaries and needs lifecycle rules.
- **Compatibility:** requires an explicit value for the existing deployment and rules for timezone changes.

#### Not selected — UTC-only date authority

The Backend defines current Diary date by UTC.

- **Advantages:** minimal configuration and consistent infrastructure behavior.
- **Risks:** a Riyadh user’s Diary day changes at 03:00 local time, which is likely inconsistent with personal daily tracking; browser-local UI could disagree near midnight.
- **Compatibility:** materially changes visible day boundaries relative to current Asia/Riyadh test assumptions.

### Consequences

All date-dependent Backend operations must use one calendar abstraction rather than direct `date.today()`. Tests need controllable clock and timezone inputs. Every environment must explicitly configure a valid IANA identifier; Wave 1 production uses `Asia/Riyadh`.

### Security Impact

The Backend remains authoritative; clients cannot manipulate effective dates through timezone claims. Invalid or missing production configuration prevents startup rather than allowing date-dependent operations under an implicit zone.

### Compatibility Impact

The explicit `Asia/Riyadh` day boundary replaces previously implicit server/browser-local behavior. Existing date-only records remain Gregorian dates and are not shifted or rewritten. A later timezone change cannot reinterpret their historical meaning.

### Migration Impact

The selected deployment-level direction requires no Profile timezone field and no historical date migration. Target Plan persistence must preserve its governing timezone. Existing Diary dates and snapshots are not rewritten.

### API Impact

The API contract must state that “today” and next-date effectiveness use the configured Backend IANA timezone and may expose non-authoritative display metadata. The client cannot submit an authoritative timezone or effective date.

### Testing Obligations

Test midnight boundaries, daylight-saving transitions where applicable, invalid/missing zone, browser/server zone disagreement, current/next-date activation, future-date rejection, age boundaries, and unchanged stored date-only values.

### Deferred Scope

Profile-owned timezone, device/browser timezone detection, timezone-selection UI, multi-timezone support, automatic travel detection, arbitrary scheduling, and historical date shifting.

### Unresolved Technical Details

Architecture must define the configuration key and validation lifecycle, calendar service interface, clock injection, Target Plan timezone representation, operational preflight, approved Change Decision procedure, and API metadata. Security and Operations must verify that no server-local or silent UTC fallback remains.

### Approval Ownership

The Product Owner has approved visible day-boundary behavior. Architecture and Security approve the calendar abstraction and fail-closed operational contract. API, BA/UX, Operations, and QA approve exposed behavior and evidence.

### Closure Evidence Required

Approved calendar service and failure behavior; explicit `Asia/Riyadh` configuration in each environment; persisted Target Plan timezone; traceability into Artifacts 14–20; and boundary tests using the selected IANA model.

### Approved Product Owner Decision Record

```text
Product Owner decision: Approved
Authoritative timezone: Asia/Riyadh
Timezone source: Backend deployment configuration
Frontend timezone authority: Prohibited
Silent fallback: Prohibited
Historical reinterpretation after timezone change: Prohibited
ADR-010 decision blocker: Resolved
Technical configuration, validation, testing, and operational evidence:
Still open
```

---

## Cross-ADR Constraints

1. ADR-001 and ADR-002 are prerequisites for every Principal-bound schema, API, migration, and aggregation contract.
2. ADR-003 governs all physical changes designed in Artifacts 14 and 16.
3. ADR-004 and ADR-007 provide one Backend rule/metadata authority; neither permits a TypeScript or database-editable substitute.
4. ADR-005 and ADR-006 share the approved `Asia/Riyadh` Principal/date resolution contract; their technical closure depends on ADR-010 configuration, persistence, and verification details.
5. ADR-006 and ADR-008 preserve known-zero/null and fail on malformed or unsupported historical data.
6. ADR-009 applies to Target Plan activation and any other mutation explicitly designated by the API contract; it does not authorize a new endpoint shape.
7. No ADR permits historical Target Plan fabrication, Snapshot v1 enrichment, legacy version backfill, deferred feature implementation, or a broad rewrite.

## Artifact-Level Unresolved Blockers

| Blocker | Required resolution |
|---|---|
| ADR-010 timezone authority | Product Owner decision resolved; Architecture/Security/API/Operations/QA technical closure remains |
| ADR-001–ADR-002 | Exact Principal/auth context, schema, configuration, and non-enumerating API contracts |
| ADR-003 | Physical migration plan, preflight, privileges, rollback, and executable PostgreSQL evidence |
| ADR-004 and ADR-007 | Exact package, manifest, Registry API, caching, and compatibility contracts |
| ADR-005 | Physical Target Plan model, lifecycle constraints, API, and atomic transaction contract |
| ADR-006 | Snapshot v2 JSON schema, relational linkage, reader/writer rollout, and integrity envelope |
| ADR-008 | Exact aggregation API and Arabic UI semantics |
| ADR-009 | Idempotency persistence, canonical request identity, concurrency constraints, and API errors |
| Artifact pinning | Complete at PR #3 merge revision `c7c48746715d24238acd70cd4eea137bf0f87cfd` |

## Artifact Lifecycle and Package Closure Conditions

Artifact 13 formal approval is complete and is independent from completion of Artifacts 14–21. Artifact 13 does not return to Draft because later artifacts remain incomplete. It is approved and pinned to the PR #3 merge revision, so Artifact 14 documentation authoring may begin.

Artifacts 14–21 resolve the delegated technical contracts and provide the traceability and verification required for the final Wave 1 package freeze. They are package-freeze dependencies, not prerequisites for Artifact 13 approval.

The Wave 1 package may become Frozen and authorize Wave 1 implementation only when:

1. Artifact 13 is pinned to the PR #3 merge revision.
2. ADR-010 configuration, persistence, API, operational, and verification details are resolved in their assigned later artifacts.
3. Artifacts 14–21 are completed, formally reviewed, approved, and pinned.
4. All decisions are traceable in Artifact 21 with no unexplained gaps.
5. The final readiness recheck reports zero Critical and High unresolved issues and no remaining Product Owner decisions.
6. The exact Final Freeze Package Commit is recorded in the Freeze Index.
7. No deferred scope is reopened.

```text
Artifact 13 version: 1.0
Artifact 13 status: Approved — Architecture and Security
Artifact 13 formal approval: Complete
Product Owner approval: Approved
Architecture approval: Approved
Security approval: Approved
Formal review: Passed
Critical findings: 0
High findings: 0
Substantive contradictions: 0
Product Owner decisions remaining: 0
Pinned revision: c7c48746715d24238acd70cd4eea137bf0f87cfd
Artifact 13 frozen: No
Artifact 14 authoring: Allowed only after PR #3 is merged and the Artifact 13 merge SHA is recorded
Artifacts 14–21: Pending
Freeze Package status: Draft — Not Frozen
Wave 1 implementation authorization: No
```
