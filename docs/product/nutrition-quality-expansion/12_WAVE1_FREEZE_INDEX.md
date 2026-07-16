# Wave 1 Freeze Index

> **This Freeze Index is a draft manifest.**
>
> **It does not authorize Wave 1 implementation.**
>
> **It is not a Ready to Build declaration.**

## 1. Header Metadata

| Field | Value |
|---|---|
| Document ID | `W1-FREEZE-INDEX-12` |
| Document title | Wave 1 Freeze Index |
| Version | Pending |
| Status | `Draft — Not Frozen` |
| Created date | 2026-07-15 |
| Last updated date | 2026-07-16 |
| Implemented Baseline Code Commit | `d6caf0a124e5ffec63cabd1972ed742b3e7fc8bd` |
| Governing Register Commit | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` |
| Governance Decision Direction Commit | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` |
| Final Freeze Package Commit | Pending |
| Wave | Wave 1 - Nutrition & Data Foundation |
| Readiness verdict | `Not Ready to Build` |
| Critical issue count | 2 |
| High unresolved issue count | 11 |
| Product Owner approval | Pending |
| Architecture approval | Pending |
| Security approval | Pending |
| Engineering/Data approval | Pending |
| API approval | Pending |
| BA/UX approval | Pending |
| QA approval | Pending |

The approved C02 Product Owner decision selects this linked modular package structure. That approval does not approve this draft index, its missing artifacts, or implementation.

## 2. Lifecycle Status Vocabulary

| Status | Meaning |
|---|---|
| `Not Created` | Required artifact does not exist |
| `Draft` | Exists but is incomplete, unapproved, or unpinned |
| `Under Review` | Submitted to all required approvers; not approved |
| `Approved` | Required authorities approved the exact pinned revision |
| `Frozen` | Approved artifact is included in the recorded Final Freeze Package Commit |
| `Superseded` | Replaced by an identified later approved artifact/version |

An uncommitted local file cannot be `Approved` or `Frozen` freeze evidence.

## 3. Governing And Supporting Sources

| Artifact ID | Exact path | Purpose | Status | Version | Pinned commit/revision | Owner | Approver | Approval date | Dependencies | Supersedes | Blocking issues |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `PDR-V1.1` | `docs/product/nutrition-quality-expansion/PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md` | Governing product decisions and scope freeze | Approved | `1.1` | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` | Pending | Pending | Pending | None | Incomplete prior v1.1 copy | None |
| `AUDIT-07` | `docs/product/nutrition-quality-expansion/07_PRODUCT_DECISION_RECONCILIATION.md` | Supporting decision-to-baseline reconciliation evidence; not an implementation contract | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`; implemented baseline | Prior provisional 07 result | C01, C02, and H01-H11 technical completion remain open |
| `READINESS-08` | `docs/product/nutrition-quality-expansion/08_WAVE1_READINESS_RECHECK.md` | Supporting readiness and gap evidence; not an implementation contract | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `AUDIT-07` | Prior provisional 08 result | Critical 2; High 11 at the audited checkpoint |
| `PLAN-09` | `docs/product/nutrition-quality-expansion/09_WAVE1_CRITICAL_HIGH_RESOLUTION_PLAN.md` | Supporting issue-resolution governance plan; not an implementation contract | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `AUDIT-07`, `READINESS-08` | None | C01, C02, and H01-H11 overall closure remain open |
| `DEC-C01-10` | `docs/product/nutrition-quality-expansion/10_C01_APPROVED_PRODUCT_OWNER_DECISION.md` | Records approved C01 Product Owner direction | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09` | None | C01 technical completion open |
| `DEC-C02-11` | `docs/product/nutrition-quality-expansion/11_C02_APPROVED_PRODUCT_OWNER_DECISION.md` | Records approved C02 Product Owner direction and package structure | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10` | None | C02 package completion open |
| `DEC-H01` | `docs/product/nutrition-quality-expansion/13_H01_APPROVED_PRODUCT_OWNER_DECISION.md` | Records approved H01 Product Owner direction for cut intensity, deficit cap, and low-energy safety outcomes | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09` | Prior H01 recommendation only | H01 technical completion open |
| `DEC-H02` | `docs/product/nutrition-quality-expansion/14_H02_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Records approved H02 Product Owner and contract direction for BMI-aware protein calculation and basis disclosure | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-H01` | Prior H02 recommendation only | Exact schema types and H02 technical completion open |
| `DEC-H03` | `docs/product/nutrition-quality-expansion/H03_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Contract Direction for carbohydrate warnings, rejection, compatibility, and legacy inventory | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-H01`, `DEC-H02` | Prior H03 recommendation only | H03 technical completion and inventory open |
| `DEC-H04` | `docs/product/nutrition-quality-expansion/H04_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Lifecycle Direction for the hybrid immutable Target Plan and activation lifecycle | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10`, `DEC-H01`, `DEC-H02`, `DEC-H03` | Prior H04 recommendation only | Exact schema, timezone, API, migration, transaction, and H04 technical completion open |
| `DEC-H05` | `docs/product/nutrition-quality-expansion/H05_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Registry Direction for the canonical 16-nutrient Backend Registry and compatibility semantics | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-H04` | Prior H05 recommendation only | Exact types, endpoint, cache, migration, UX, implementation, and H05 verification open |
| `DEC-H06` | `docs/product/nutrition-quality-expansion/H06_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Food-Group Direction for normalized contributions, traits, serving rules, and coverage semantics | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10`, `DEC-H05` | Prior H06 recommendation only | Exact schema, API, migration, Arabic UI, implementation, and H06 verification open |
| `DEC-H07` | `docs/product/nutrition-quality-expansion/H07_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Source/NOVA Direction for controlled sources, derived reliability, ingredients, NOVA, and historical interpretation | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10`, `DEC-H05`, `DEC-H06` | Prior H07 recommendation only | Exact schema, API errors, caching, UI transitions, migration, implementation, and H07 verification open |
| `DEC-H08` | `docs/product/nutrition-quality-expansion/H08_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Snapshot Direction for Snapshot v2, relational ownership, Target Plan binding, compatibility, and rollout semantics | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07` | Prior H08 recommendation only | Exact physical fields, JSON schema, endpoint envelopes, migration, rollout, UX, implementation, and H08 verification open |
| `ADR-DIR-H09` | `docs/product/nutrition-quality-expansion/H09_APPROVED_ARCHITECTURE_MIGRATION_DIRECTION.md` | Approved Architecture/Migration Direction for Alembic authority, ordered rollout, fail-closed ownership migration, compatibility, and rollback | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-C01-10`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08` | Prior H09 recommendation only | Exact physical schema, revisions, provisioning implementation, CI commands, migration evidence, and H09 verification open |
| `ADR-DIR-H10` | `docs/product/nutrition-quality-expansion/H10_APPROVED_RULE_VERSIONING_DIRECTION.md` | Approved Architecture/Rule-Versioning Direction for Backend rule ownership, independent versions, manifest integrity, Registry exposure, and historical interpretation | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09` | Prior H10 recommendation only | Exact modules, physical fields, API envelope, caching, implementation, migration, and H10 verification open |
| `DEC-H11` | `docs/product/nutrition-quality-expansion/H11_APPROVED_PRODUCT_OWNER_DIRECTION.md` | Approved Product/Truthful-Aggregation Direction for null, zero, coverage, target evaluation, and Frontend authority | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `PLAN-09`, `DEC-H05`, `DEC-H08`, `ADR-DIR-H10` | Prior H11 recommendation only | Exact API schema, Backend implementation, Arabic UI, compatibility, and H11 verification open |
| `CHECKPOINT-DD` | `docs/product/nutrition-quality-expansion/DECISION_DIRECTION_CHECKPOINT_REPORT.md` | Validates the merged C01, C02, and H01-H11 decision-direction checkpoint; not an implementation contract | Draft | Pending | `b9869dfe0a1dc26190aaa6478f2114da82a0793e` | Pending | Pending | Pending | `PDR-V1.1`, `AUDIT-07`, `READINESS-08`, `PLAN-09`, all direction records | None | Architecture artifact review and complete freeze package remain open |

The decisions and directions recorded in artifacts 10, 11, the H01 through H08 and H11 decision records, `ADR-DIR-H09`, and `ADR-DIR-H10` are merged governance evidence pinned to the Governance Decision Direction Commit. They remain `Draft` freeze records because the formal technical contracts, named approvers, approval dates, and Final Freeze Package Commit remain pending. Pinning does not by itself make an artifact `Approved` or `Frozen`.

### Artifact Naming And Reserved Identifiers

Numeric artifact identifiers `13` through `21` are reserved for the formal modular Wave 1 freeze package listed below. Supporting direction records use independent stable Artifact IDs such as `DEC-H01` through `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, and `DEC-H11`, even when an existing filename contains a numeric prefix. Existing direction files are not renamed by this index, and they do not substitute for the formal freeze artifacts.

## 4. Required Freeze Artifacts

Artifact 13 is formally approved as Architecture and Security direction and pinned to PR #3 merge revision `c7c48746715d24238acd70cd4eea137bf0f87cfd`. It is not Frozen. Artifact 14 documentation authoring may begin. Artifacts 14-21 do not exist and remain `Not Created`.

| Artifact ID | Exact path | Purpose | Status | Owner | Approver | Approval date | Version | Pinned commit/revision | Dependencies | Supersedes | Blocking issues | Required for implementation start | Required for Wave 1 sign-off |
|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|
| `W1-ADR-13` | `docs/product/nutrition-quality-expansion/13_WAVE1_ARCHITECTURE_SECURITY_ADRS.md` | Architecture, security, Principal ownership, rule authority, and system-boundary ADRs | Approved | Architecture / Security | Product Owner / Architecture / Security | `2026-07-16` | `1.0` | `c7c48746715d24238acd70cd4eea137bf0f87cfd` | `DEC-C01-10`, `DEC-C02-11`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11` | None | Product Owner decisions: 0; Critical review findings: 0; High review findings: 0; approved and pinned; review evidence: `docs/product/nutrition-quality-expansion/13A_WAVE1_ARCHITECTURE_SECURITY_REVIEW.md` | Yes | Yes |
| `W1-DATA-14` | `docs/product/nutrition-quality-expansion/14_WAVE1_PHYSICAL_DATA_MODEL.md` | Exact tables, fields, types, constraints, ownership, versions, and legacy semantics | Approved | Engineering / Data | Engineering / Data | `2026-07-16` | `1.0` | `afa3a9bb220a7798920d7edc1b0949da15f2d7fe` | `W1-ADR-13`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`; governing decisions | None | Critical 0; High 0; Product decisions 0; review `14A_WAVE1_PHYSICAL_DATA_MODEL_REVIEW.md` | Yes | Yes |
| `W1-API-15` | `docs/product/nutrition-quality-expansion/15_WAVE1_API_CONTRACTS.md` | Requests, responses, errors, nulls, idempotency, ownership, and compatibility | Approved | API / Architecture | API / Architecture | `2026-07-16` | `1.0` | `400366b39abb73bb2e2d2ba82c79c1cd524d6e67` | `W1-ADR-13`, `W1-DATA-14`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11` | None | Critical 0; High 0; Product decisions 0; review `15A_WAVE1_API_CONTRACTS_REVIEW.md` | Yes | Yes |
| `W1-MIG-16` | `docs/product/nutrition-quality-expansion/16_WAVE1_MIGRATION_ROLLBACK_PLAN.md` | Expand-Migrate-Contract, rollback, realistic rehearsal, and legacy protection | Approved | Engineering / Data / Operations | Engineering / Data / Operations | `2026-07-16` | `1.0` | `ead5de21fe1153126f6c19c9f7aeba6a732ace89` | `W1-ADR-13`, `W1-DATA-14`, `W1-API-15`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10` | None | Critical 0; High 0; Product decisions 0; review `16A_WAVE1_MIGRATION_ROLLBACK_REVIEW.md` | Yes | Yes |
| `W1-BAQA-17` | `docs/product/nutrition-quality-expansion/17_WAVE1_USER_STORIES_ACCEPTANCE_CRITERIA.md` | Testable user stories and positive/negative acceptance criteria | Approved | Product / BA / UX | Product / BA / UX | `2026-07-16` | `1.0` | `ffde6f597750b18e85d861c36d3dfad105d36f0e` | `PDR-V1.1`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11`, `W1-ADR-13` through `W1-MIG-16` | None | Critical 0; High 0; Product decisions 0; review `17A_WAVE1_USER_STORIES_ACCEPTANCE_REVIEW.md` | Yes | Yes |
| `W1-GOLDEN-18` | `docs/product/nutrition-quality-expansion/18_WAVE1_GOLDEN_CALCULATIONS.md` | Fixed calculation, target, boundary, warning, rejection, null, and legacy scenarios | Approved | Engineering / QA | Engineering / QA | `2026-07-16` | `1.0` | `e714b4c374166a27a8aa1b40ab4b851ce0b92a9d` | `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H10`, `DEC-H11`, `W1-API-15`, `W1-BAQA-17` | None | Critical 0; High 0; Product decisions 0; review `18A_WAVE1_GOLDEN_CALCULATIONS_REVIEW.md` | Yes | Yes |
| `W1-UI-19` | `docs/product/nutrition-quality-expansion/19_WAVE1_UI_STATE_MATRIX.md` | Loading, empty, partial, unknown, legacy, error, keyboard, RTL, responsive, and accessibility states | Not Created | Pending | Pending | Pending | Pending | Pending | `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11`, `W1-API-15`, `W1-BAQA-17` | None | H01-H11 | Yes | Yes |
| `W1-VERIFY-20` | `docs/product/nutrition-quality-expansion/20_WAVE1_VERIFICATION_REGRESSION_PLAN.md` | Focused, migration, security, compatibility, baseline regression, and release evidence | Not Created | Pending | Pending | Pending | Pending | Pending | `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11`, `W1-ADR-13` through `W1-UI-19` | None | C01; C02; H01-H11 | Yes | Yes |
| `W1-TRACE-21` | `docs/product/nutrition-quality-expansion/21_WAVE1_TRACEABILITY_MATRIX.md` | Decision-to-contract-to-story-to-test-to-closure traceability | Not Created | Pending | Pending | Pending | Pending | Pending | `PDR-V1.1`, `DEC-C01-10`, `DEC-C02-11`, `DEC-H01`, `DEC-H02`, `DEC-H03`, `DEC-H04`, `DEC-H05`, `DEC-H06`, `DEC-H07`, `DEC-H08`, `ADR-DIR-H09`, `ADR-DIR-H10`, `DEC-H11`, `W1-ADR-13` through `W1-VERIFY-20` | None | C01; C02; H01-H11 | Yes | Yes |

### Artifact 13 Blocking-Decision State

```text
ADR-010 Product Owner decision: Resolved
Authoritative Diary calendar timezone: Asia/Riyadh
Product Owner decisions remaining for Artifact 13: 0
Artifact 13 version: 1.0
Artifact 13 status: Approved — Architecture and Security
Product Owner approval: Approved
Architecture approval: Approved
Security approval: Approved
Approval date: 2026-07-16
Review evidence: docs/product/nutrition-quality-expansion/13A_WAVE1_ARCHITECTURE_SECURITY_REVIEW.md
Critical review findings: 0
High review findings: 0
Pinned commit/revision: c7c48746715d24238acd70cd4eea137bf0f87cfd
Artifact 13 frozen: No
Artifact 14 authoring: Yes, documentation drafting only
Implementation authorization: No
Artifacts 14 through 21: Not Created
```

## 5. Current Issue Tracking

### Critical issues

#### C01 - Authenticated ownership cannot be safely migrated

```text
Product Owner decision approved.
Architecture, contracts, migration design, implementation, and
verification remain open.
Overall status: Open.
```

#### C02 - The formal Wave 1 freeze package does not exist

```text
Product Owner decision approved.
Freeze artifacts, approvals, pinned revisions, and final readiness
recheck remain open.
Overall status: Open.
```

#### H01 - Cut intensity, 750 kcal cap, and low-energy safety outcomes are absent

```text
Product Owner decision approved.
Persistence, deficit-cap, and low-energy activation behavior approved.
Architecture, schema, API, migration, UX, implementation, verification,
and traceability remain open.
Overall status: Open.
```

#### H02 - BMI-aware adjusted protein calculation and basis disclosure are absent

```text
Product Owner and contract direction approved.
Nested protein_calculation API direction and compatibility behavior approved.
Exact physical schema types and Architecture, Data, API, UX,
implementation, verification, and traceability approvals remain open.
Overall status: Open.
```

#### H03 - Zero or negative carbohydrate allocation is silently clamped

```text
Product and contract direction approved.
Shared warning collection, typed rejection, compatibility, and legacy
inventory direction approved.
Technical contracts, inventory, implementation, verification, and
traceability remain open.
Overall status: Open.
```

#### H04 - Immutable Target Plan model and lifecycle are not frozen

```text
Product and lifecycle behavior approved.
Hybrid architecture, calendar-date effectiveness, activation,
idempotency, atomicity, and legacy behavior approved.
Exact physical schema, timezone/date contract, API, migration,
transaction, implementation, verification, and traceability remain open.
Overall status: Open.
```

#### H05 - Nutrient registry is incomplete and duplicated

```text
Product and Registry ownership semantics approved.
Canonical 16-nutrient Backend Registry, runtime API, versioning,
exact-field, and legacy ambiguity direction approved.
Physical types, endpoint schema, compatibility, caching, migration,
UX, implementation, verification, and traceability remain open.
Related dependencies: H04, H08, H10, and H11.
Overall status: Open.
```

#### H06 - Food-group registry, contributions, and traits do not exist

```text
Product, Registry, group, contribution, trait, serving, and coverage
semantics approved.
Normalized Principal-scoped persistence and controlled compatibility
direction approved.
Physical schema, API, migration, Arabic UI, implementation,
verification, and traceability remain open.
Related dependencies: C01, H05, H08, H09, and H10.
Overall status: Open.
```

#### H07 - Controlled source reliability, ingredients, and NOVA do not exist

```text
Product and source/NOVA contract direction approved.
Controlled source vocabulary, Backend-derived reliability, ingredients,
manual reviewed NOVA, migration defaults, historical version preservation,
and separation of quality dimensions approved.
Physical schema, API errors, caching, UI transitions, migration,
implementation, verification, and traceability remain open.
Related dependencies: C01, H05, H06, H08, H09, and H10.
Overall status: Open.
```

#### H08 - Snapshot v2 and Target Plan binding do not exist

```text
Product and Snapshot contract direction approved.
Versioned JSONB, relational Principal and Target Plan linkage, per-unit
values, immutable binding, v1 compatibility, integrity errors, and
reader-before-writer rollout semantics approved.
Exact physical fields, JSON schema, endpoint envelopes, migration,
rollout, UX, implementation, verification, and traceability remain open.
Direct dependencies: C01 and H04 through H07.
Related downstream dependencies: H09, H10, and H11.
Overall status: Open.
```

#### H09 - Wave 1 migration and rollback are unfrozen; schema authority is ambiguous

```text
Architecture and migration direction approved.
Alembic runtime authority, immutable baseline revisions, explicit
fail-closed Principal provisioning, ordered additive migration,
reader-before-writer rollout, and compatible rollback approved.
Exact physical schema, revision files, provisioning implementation,
CI commands, migration evidence, verification, and traceability remain open.
Direct migration dependencies: C01 and H04 through H08.
Versioning dependency: H10.
Overall status: Open.
```

#### H10 - Independent rule versions and one Backend-owned rules package do not exist

```text
Architecture and rule-versioning direction approved.
Backend rule ownership, independent initial versions, semantic bump
policy, immutable released versions, deterministic manifest integrity,
Registry exposure, and historical interpretation approved.
Exact module paths, physical fields, API envelope, caching,
implementation, migration, verification, and traceability remain open.
Direct dependencies: H04 through H09.
Downstream truthful aggregation dependency: H11.
Overall status: Open.
```

#### H11 - All-unknown nutrient data is displayed as numeric zero

```text
Product and truthful-aggregation direction approved.
Backend authority, null/known-zero distinctions, coverage states,
partial asymmetric target evaluation, historical target resolution,
and Frontend rendering boundary approved.
Exact API schema, Backend implementation, Arabic UI, compatibility,
verification, and traceability remain open.
Direct dependencies: H05, H08, and H10.
Overall status: Open.
```

### High unresolved issues

The following statuses are copied from the authoritative ordering in documents 08 and 09. This index does not resolve or reclassify them.

| ID | Exact title | Current status |
|---|---|---|
| `H01` | Cut intensity, 750 kcal cap, and 800/1200 safety outcomes are absent | Open - product decision resolved; technical work open |
| `H02` | BMI-aware adjusted protein calculation and basis disclosure are absent | Open - product and contract direction resolved; technical work open |
| `H03` | Zero/negative carbs are silently clamped | Open - product and contract direction resolved; technical work open |
| `H04` | Immutable Target Plan schema, activation, history, and effective-range rules are not frozen | Open - product and lifecycle direction resolved; technical work open |
| `H05` | Nutrient registry is incomplete, duplicated, and lacks four exact semantic fields | Open - product and Registry direction resolved; technical work open |
| `H06` | Food-group registry, contributions, traits, and validation do not exist | Open - product and Food-group direction resolved; technical work open |
| `H07` | Controlled source reliability, ingredients, and NOVA do not exist | Open - product and source/NOVA direction resolved; technical work open |
| `H08` | Snapshot v2/version compatibility and Target Plan binding do not exist | Open - product and Snapshot direction resolved; technical work open |
| `H09` | Wave 1 migration/rollback is unfrozen and runtime `create_all` weakens Alembic authority | Open - architecture and migration direction resolved; technical work open |
| `H10` | Independent rule versions and Backend-owned rules package do not exist | Open - architecture and rule-versioning direction resolved; technical work open |
| `H11` | All-unknown nutrient UI currently presents false zero | Open - product and truthful-aggregation direction resolved; technical work open |

## 6. Wave 1 Scope Boundary

Wave 1 includes only the approved Nutrition & Data Foundation delta from `PD-004`, including governed calculation policy, registries, nullable data, Food classification/contributions, source/ingredients/NOVA foundations, Snapshot v2, Target Plan Versions, rule versioning, additive contracts, migration/compatibility design, and golden characterization evidence.

### Explicitly excluded later-wave and deferred scope

- Progress UI.
- Seven-day Nutrition Pattern Analysis.
- Weekly recommendations and priorities.
- Behavior goals.
- Weight, waist, blood pressure, and activity tracking.
- Sleep tracking.
- Laboratory tests.
- Medications and supplements.
- Clinical nutrition modes.
- Full recipe engine.
- Barcode scanning.
- OCR.
- Direct gram/ml Diary logging.
- Offline personal-data storage and synchronization.
- Multiple Profiles.
- Profile switching.
- Public registration.
- Shared or public Foods.
- AI nutrition decision-making.
- Unified Health Score.
- Unrelated UI redesigns.

### Baseline assets that must not regress

- Existing implemented Foods routes and behavior.
- Existing Diary routes, meal behavior, serving-only logging, and frozen snapshots.
- Existing Add Food flow.
- Existing Profile behavior outside an explicitly approved Wave 1 delta.
- Existing registered API routes and backward-compatible consumers.
- Online-only runtime.
- Food per-100 source of truth and serving display.
- Permanent Food deletion with snapshot-safe Diary history.
- Existing regression suites and meaningful coverage.

## 7. Freeze Conditions

This Freeze Index may become `Frozen` only when:

1. All required artifacts exist.
2. All required artifacts have an approved status.
3. Every artifact has an owner and approver.
4. Every approved artifact has an approval date.
5. Every artifact is pinned to an exact commit or revision.
6. All active Wave 1 decisions are traceable.
7. Exact schema delta is approved.
8. Exact migration and rollback design is approved.
9. Exact API contracts are approved.
10. User stories and acceptance criteria are approved.
11. Golden calculations are approved.
12. UI state coverage is approved.
13. Verification and regression coverage are approved.
14. Critical issues equal zero.
15. High unresolved issues equal zero.
16. Final readiness recheck reports `Ready to Build`.
17. Deferred scope remains excluded.
18. The Final Freeze Package Commit is recorded.

If any condition becomes false after freeze, change control under `PD-001` applies and implementation authorization must be reassessed.

## 8. Current Declaration

```text
Current verdict: Not Ready to Build
Current freeze status: Draft — Not Frozen
Implementation authorization: No
```
