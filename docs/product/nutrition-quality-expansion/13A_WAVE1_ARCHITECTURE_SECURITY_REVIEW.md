# Wave 1 Artifact 13 Architecture and Security Review

## 1. Review Metadata

| Field | Value |
|---|---|
| Review artifact | `W1-ADR-13A` |
| Reviewed artifact | `W1-ADR-13` |
| Reviewed artifact version | `0.1 Draft` |
| Review type | Independent formal Architecture and Security review |
| Review date | `2026-07-16` |
| Audited branch | `docs/wave1-architecture-security-adrs` |
| Audited HEAD | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` |
| Reviewed Artifact 13 SHA-256 | `F4F36BB85A94ED507100149DD3F6D48413BC94FF705529B45F4A787C821BC2DB` |
| Review scope | ADR-001 through ADR-010 and their combined architecture |
| Product implementation authorization | `No` |

This review assesses whether Artifact 13 provides a complete and consistent architecture and security foundation for drafting Artifact 14. It does not approve, freeze, or implement Artifact 13, and it does not recertify the current implementation as conforming to the proposed architecture.

### Final Approval Disposition

| Field | Value |
|---|---|
| Artifact 13 formal approval | `Approved` |
| Approved version | `1.0` |
| Approval status | `Approved — Architecture and Security` |
| Approval date | `2026-07-16` |
| Pinned revision | `c7c48746715d24238acd70cd4eea137bf0f87cfd` |
| Artifact 14 authoring after merge | Authorized as documentation drafting |
| Product implementation authorization | `No` |

This disposition records the subsequent formal approval without changing the original review evidence, finding counts, or recommendation. Artifact 13 is not Frozen, and Wave 1 product implementation remains unauthorized.

## 2. Audited Branch and HEAD

The review was performed on branch `docs/wave1-architecture-security-adrs` at exact HEAD `b9869dfe0a1dc26190aaa6478f2114da82a0793e`.

The working tree already contained the following pre-review, uncommitted items:

- modified `docs/product/nutrition-quality-expansion/12_WAVE1_FREEZE_INDEX.md`;
- untracked `docs/product/nutrition-quality-expansion/13_WAVE1_ARCHITECTURE_SECURITY_ADRS.md`;
- untracked `frontend/debug-diary.png`.

This review did not alter those items. Their presence is recorded so that this report is not mistaken for a review of a committed freeze-package revision.

## 3. Sources and Repository Evidence Reviewed

### Governing and approved direction sources

- `PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md`, including `PD-000` through `PD-029` and the Wave 1 boundaries.
- `10_C01_APPROVED_PRODUCT_OWNER_DECISION.md` and `11_C02_APPROVED_PRODUCT_OWNER_DECISION.md`.
- `13_H01_APPROVED_PRODUCT_OWNER_DECISION.md` and `14_H02_APPROVED_PRODUCT_OWNER_DIRECTION.md`.
- `H03_APPROVED_PRODUCT_OWNER_DIRECTION.md` through `H08_APPROVED_PRODUCT_OWNER_DIRECTION.md`.
- `H09_APPROVED_ARCHITECTURE_MIGRATION_DIRECTION.md`.
- `H10_APPROVED_RULE_VERSIONING_DIRECTION.md`.
- `H11_APPROVED_PRODUCT_OWNER_DIRECTION.md`.
- `12_WAVE1_FREEZE_INDEX.md` and `13_WAVE1_ARCHITECTURE_SECURITY_ADRS.md`.

### Implementation evidence

- Authentication and configuration: `backend/app/core/auth.py`, `backend/app/core/config.py`, `.env.example`, `docker-compose.yml`, and `frontend/lib/api.ts`.
- Runtime and schema setup: `backend/app/main.py`, `backend/app/db/session.py`, `backend/alembic.ini`, and Alembic revisions `0001_initial`, `0002_foods_v1_per_basis`, and `0003_diary_meal_type`.
- Persistence: `backend/app/models.py`.
- Services and routes: Profile, Food, Diary, aggregation, calculation, and nutrient services under `backend/app/services/` and registered API modules under `backend/app/api/`.
- Frontend authority boundaries: `frontend/lib/nutrients.ts`, API access code, Profile and Diary consumers, and `frontend/playwright.config.ts`.
- Tests: current Backend service, Food, Diary snapshot, Profile/calculation, and Frontend/Playwright evidence relevant to ownership, snapshots, dates, and rules.

The repository evidence confirms Artifact 13's brownfield statements: authentication currently returns no Principal context and accepts empty token configuration; user data has no owner key; runtime invokes `SQLModel.metadata.create_all`; there is no Target Plan; Diary snapshots are unversioned; quantity edits rewrite legacy snapshot fields; Backend and Frontend nutrient definitions are duplicated; Diary aggregation is global and can collapse all-unknown values; no durable idempotency mechanism exists; and date authority currently depends on server or browser local time rather than an explicit IANA configuration.

## 4. ADR-by-ADR Findings

| ADR | Review result | Architecture and security assessment | Correctly delegated detail |
|---|---|---|---|
| `ADR-001` | Pass | Establishes a durable credential-independent Principal, one Profile per Principal, complete owner scoping, non-enumerating cross-owner behavior, and two-Principal verification without introducing multi-user UX. | Principal keys, foreign keys, indexes, provisioning transaction, and physical enforcement belong to Artifacts 14 and 16. |
| `ADR-002` | Pass | Requires typed authenticated Principal context, fail-closed production authentication, Principal-required services, stable `401`/non-enumerating `404`, and no Service Role for normal operations. | Context type, credential mapping, configuration lifecycle, and HTTP envelope belong to Artifacts 14, 15, 16, and 20. |
| `ADR-003` | Pass | Makes Alembic the sole runtime/deployed/integration authority, prohibits runtime schema mutation, preserves revisions 0001-0003, and defines reader-before-writer and non-lossy rollback boundaries. | Revision split, preflight implementation, privileges, writer gate, downgrade matrix, and CI commands belong to Artifacts 14, 16, and 20. |
| `ADR-004` | Pass | Establishes one typed declarative Backend rules authority, pure deterministic calculations, independent versions, immutable released meaning, and manifest integrity without treating a hash as authorization. | Module layout, serialization, decimal types, version-diff mechanics, and release process belong to Artifacts 14, 15, 18, and 20. |
| `ADR-005` | Pass | Defines immutable Target Plan content, Principal ownership, date-effective lifecycle, no overlap, one active/one pending limit, audited replacement, explicit idempotent activation, and atomic Profile/plan persistence. | Physical lifecycle schema, exclusion constraints, document schema, endpoint shapes, and transaction implementation belong to Artifacts 14-16. |
| `ADR-006` | Pass | Defines Backend-only Snapshot v2 writing, strict version dispatch, immutable per-unit values, Principal/date Target Plan binding, no client injection, no v1 enrichment, and fail-visible integrity errors. | JSON schema, v1 discriminator, relational linkage, error envelope, and rollout gate belong to Artifacts 14-16 and 20. |
| `ADR-007` | Pass | Preserves one Backend Registry authority, types-only generation, no client fallback rules, read-only runtime metadata, and fail-closed Registry-dependent mutations for unsupported metadata. | Authentication, cache headers, compatibility range, OpenAPI generation, and UI states belong to Artifacts 15, 17, 19, and 20. |
| `ADR-008` | Pass | Makes nullable nutrient aggregation, coverage, target resolution, and evaluation Principal-scoped and Backend-authoritative; malformed snapshots cannot be silently omitted. | Response precision, compatibility fields, integrity granularity, localization ownership, and query indexes belong to Artifacts 14, 15, 17, 19, and 20. |
| `ADR-009` | Pass | Requires Principal- and operation-scoped idempotency, payload binding, privacy-preserving replay, database-enforced concurrency safety, and atomic Target Plan lifecycle transitions. | Replay schema, canonical hashing, retention, locking, exact Food/Diary applicability, and error codes belong to Artifacts 14-16 and 20. |
| `ADR-010` | Pass | Establishes `Asia/Riyadh` as the deployment-configured Backend calendar authority, prohibits implicit fallback, requires fail-closed configuration, persists plan timezone, and prevents historical reinterpretation. | Configuration key, calendar service, clock injection, persisted type, operational preflight, and API metadata belong to Artifacts 14-16 and 20. |

All ADR IDs are unique. All ten use the allowed status `Approved Direction - Technical Detail Pending` in semantic terms; the source uses the approved typographic dash. Every ADR contains governing decisions, context, repository evidence, decision, alternatives, consequences, security, compatibility, migration, API, testing, deferred scope, unresolved detail, approval ownership, and closure evidence.

## 5. Authentication and Authorization Assessment

### Authentication and Principal establishment

Artifact 13 closes the required architecture direction. Credential validation and ownership identity are separated. Token rotation maps to the same durable Principal. Authentication returns typed immutable Principal context rather than a boolean route guard. Missing or invalid production configuration fails closed, no anonymous/global owner fallback is permitted, and the client cannot establish ownership. External identity-provider selection remains deferred.

### Authorization and isolation

Owner scope covers reads, writes, lists, aggregations, uniqueness, duplicate detection, and lifecycle operations. Cross-owner and nonexistent identifiers share outward `404` semantics after successful authentication, reducing IDOR enumeration. One Profile per Principal is explicit. Normal operations cannot use Service Role. Verification must exercise at least two Principals at route, service, transaction, and aggregation boundaries.

### Ownership migration

The migration boundary is safe at the architecture level: the deployment Principal must be explicitly provisioned; no arbitrary identifier is embedded in a migration; ambiguous or absent provisioning stops migration; ownership starts nullable; counts and orphans are reconciled before constraints become required; and historical nutrition content is not reassigned or rewritten. Exact SQL and transaction staging remain correctly assigned to Artifacts 14 and 16.

## 6. Threat and Failure-Mode Assessment

| Threat or failure mode | Artifact 13 control | Review result |
|---|---|---|
| Missing, empty, or invalid production credential configuration | Fail-closed preflight/protected boundary; no anonymous fallback | Covered |
| Credential rotation changes ownership | Credential-to-durable-Principal mapping; token is not owner key | Covered |
| Client submits another owner identifier | Client ownership fields are non-authoritative; services require authenticated context | Covered |
| IDOR across reads, updates, deletes, lists, or aggregates | Owner predicates plus non-enumerating outward response and two-Principal tests | Covered |
| Migration assigns records to an arbitrary or ambiguous owner | Explicit deployment Principal, stop on ambiguity, count/orphan verification | Covered |
| Runtime creates or mutates an unreviewed schema | Alembic-only authority; runtime `create_all` and startup migration prohibited | Covered |
| Reader cannot understand newly written data | Reader-before-writer gate and compatible application rollback | Covered |
| Target Plan calculation content changes after activation | Immutable server-validated plan document and lifecycle-only transitions | Covered |
| Concurrent activations create overlapping plans | Database constraints, transaction, locking/conflict control, one active/one pending | Covered |
| Same idempotency key is replayed with different content | Principal/operation-scoped key with canonical request binding and rejection | Covered |
| Idempotency response leaks another Principal's result | Principal-scoped replay namespace and privacy-preserving response | Covered |
| Transaction fails after Profile preference mutation | Preference update, lifecycle transitions, and activation are atomic | Covered |
| Client injects snapshot, target identity, provenance, or rule version | Backend-only snapshot writer and Backend date/Principal resolution | Covered |
| Food edit/deletion or rule change alters history | Captured identity and values remain in immutable snapshot; live Food link may become null | Covered |
| Unknown snapshot version falls back to legacy | Exact reader dispatch; unknown or malformed data fails visibly | Covered |
| Malformed snapshot understates totals | Integrity failure prevents silent omission or zero substitution | Covered |
| Frontend or database becomes a second rules authority | Backend package and runtime Registry are authoritative; TS is types-only; DB stores resolved history | Covered |
| Released version content changes silently | Independent versions plus deterministic canonical manifest/hash CI evidence | Covered |
| Current rules reinterpret historical plans or snapshots | Resolved historical values and stored versions remain authoritative | Covered |
| Browser, server-local time, or UTC changes Diary day | Explicit Backend `Asia/Riyadh` calendar abstraction; no fallback | Covered |
| Deployment timezone change shifts history | Formal Change Decision required; existing dates/plans/snapshots cannot be reinterpreted | Covered |

Idempotency retention, cleanup, canonicalization, and conflict envelopes are material details, but Artifact 13 identifies each and assigns approval to Data, API, Security, and QA. Their delegation does not force Artifact 14 to invent product behavior: Artifact 14 can define durable storage and constraints against the already frozen Principal/operation/payload-binding semantics.

## 7. Cross-ADR Consistency Matrix

| Relationship | Result | Assessment |
|---|---|---|
| ADR-001 / ADR-002 | Consistent | Durable Principal identity is established by typed authentication context and required by every user-data service. |
| ADR-003 / ADR-006 | Consistent | Snapshot v2 fields are added through Alembic, dual readers precede writers, and rollback after v2 writes remains reader-compatible. |
| ADR-004 / ADR-007 | Consistent | One Backend package owns rules; the Registry exports metadata; Frontend types and cache do not become authority. |
| ADR-005 / ADR-006 | Consistent | Target Plan date resolution and immutable Diary binding share Principal/date authority; same-date new-user binding is atomic and limited. |
| ADR-005 / ADR-009 | Consistent | Explicit activation and pending replacement use Principal-scoped idempotency, payload binding, transactions, and database constraints. |
| ADR-005 / ADR-006 / ADR-010 | Consistent | Plan lifecycle, entry binding, future-date validation, and Diary dates use one Backend `Asia/Riyadh` calendar. |
| ADR-006 / ADR-008 | Consistent | Strict snapshot readers feed truthful aggregation; malformed or unsupported data cannot be silently zeroed or omitted. |
| ADR-004 / ADR-006 | Consistent | Snapshot v2 stores applicable rule versions while calculation-engine provenance remains in a linked versioned plan where one exists. |
| C01-C02 / H01-H11 | Consistent | Artifact 13 translates approved direction without reopening deferred scope or contradicting ownership, calculation, Registry, plan, snapshot, migration, versioning, or aggregation semantics. |

Substantive contradictions: `0`.

## 8. Deferred-Scope Integrity

The ADR set does not authorize public registration, external identity-provider integration, multiple Profiles, Profile switching, shared/public Foods, arbitrary Target Plan scheduling, backdating, clinical overrides, Progress UI, Wave 3 analysis, AI classification, direct gram/ml Diary logging, offline personal-data storage/sync, historical Target Plan fabrication, Snapshot v1 enrichment, rule administration, or a greenfield rewrite.

myNutri remains distinct from NutriPlan. Existing Foods, Diary, Add Food, Profile, routes, identifiers, and regression behavior remain brownfield baseline assets subject to additive compatibility contracts.

Deferred-scope integrity result: Pass.

## 9. Findings by Severity

### Critical

None.

### High

None.

### Medium

None. The unresolved physical, API, migration, UX, and verification details are explicitly assigned and do not change the approved architecture.

### Low

None.

```text
Critical issues: 0
High issues: 0
Medium issues: 0
Low issues: 0
Substantive contradictions: 0
Product Owner decisions required: 0
```

## 10. Exact Required Corrections

No correction to Artifact 13 is required before formal Architecture and Security approval.

At review completion, formal approval and exact-revision pinning were the remaining governance actions. Formal approval was subsequently recorded, and Artifact 13 was pinned to PR #3 merge revision `c7c48746715d24238acd70cd4eea137bf0f87cfd`. These governance actions are not findings against the architecture content.

## 11. Details Correctly Delegated to Artifacts 14-21

| Artifact | Delegated detail |
|---|---|
| `14_WAVE1_PHYSICAL_DATA_MODEL.md` | Principal and ownership keys; owner-aware uniqueness/indexes; Target Plan lifecycle/document fields and constraints; Snapshot linkage/version fields; idempotency storage; timezone persistence; query indexes. |
| `15_WAVE1_API_CONTRACTS.md` | Authentication/errors; non-enumerating envelopes; Registry endpoint/cache/schema behavior; plan activation/replay contracts; snapshot integrity errors; aggregation semantics and compatibility fields. |
| `16_WAVE1_MIGRATION_ROLLBACK_PLAN.md` | Principal provisioning/backfill; revision split; reader/writer gates; populated rehearsals; rollback/downgrade matrix; no-inference evidence. |
| `17_WAVE1_USER_STORIES_ACCEPTANCE_CRITERIA.md` | User-visible activation, scheduled replacement, Registry failure, integrity failure, and Arabic semantic states without changing architecture. |
| `18_WAVE1_GOLDEN_CALCULATIONS.md` | H01-H03 boundaries, decimal/rounding behavior, resolved targets, and versioned calculation fixtures. |
| `19_WAVE1_UI_STATE_MATRIX.md` | Loading/error/incompatible Registry states, target lifecycle states, coverage qualifiers, and non-authoritative Frontend behavior. |
| `20_WAVE1_VERIFICATION_REGRESSION_PLAN.md` | Two-Principal isolation, fail-closed auth/timezone/schema tests, migration rehearsals, concurrency/replay, strict snapshot readers, manifest/version tests, and baseline regression gates. |
| `21_WAVE1_TRACEABILITY_MATRIX.md` | Bidirectional traceability from PD and approved direction records through ADRs, contracts, implementation evidence, and verification. |

These delegations are appropriately bounded. None requires a new Product Owner decision or an architecture invention before Artifact 14 can be drafted.

## 12. Approval Recommendation

**Verdict: Ready for Architecture/Security Approval**

Artifact 13 is sufficiently complete, consistent, secure, and precise to serve as the architecture foundation for Artifact 14. This review recommendation did not itself approve or freeze Artifact 13. Formal Product Owner, Architecture, and Security approval was subsequently recorded as version `1.0` and pinned to PR #3 merge revision `c7c48746715d24238acd70cd4eea137bf0f87cfd`.

Artifact 13 is `Approved — Architecture and Security` and is not Frozen. Artifacts 14–21 remain required for the final package freeze. Wave 1 remains `Not Ready to Build`, and product implementation remains unauthorized.

## 13. Readiness for Artifact 14

Artifact 14 authoring may begin: **Yes**.

The ten architecture directions exist, Product Owner decisions remaining are zero, substantive contradictions are zero, and no missing architecture/security direction would force Physical Data Model authors to invent product behavior. Artifact 14 must remain a draft until its own Engineering/Data review and must conform to the ownership, immutability, versioning, migration, idempotency, and timezone boundaries in Artifact 13.

```text
Artifact 13 formal review verdict: Ready for Architecture/Security Approval
Critical issues: 0
High issues: 0
Product Owner decisions required: 0
Artifact 14 authoring may begin: Yes
Product implementation authorized: No
```
