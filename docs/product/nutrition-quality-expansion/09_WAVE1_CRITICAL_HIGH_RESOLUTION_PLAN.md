# Wave 1 Critical And High Issue Resolution Plan

## 1. Purpose And Evidence Boundary

This package resolves planning ownership for the 2 Critical and 11 High findings identified by the strict Wave 1 recheck. It does not implement them.

It uses only:

- `PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md`;
- `07_PRODUCT_DECISION_RECONCILIATION.md`;
- `08_WAVE1_READINESS_RECHECK.md`;
- repository code, migrations, routes, schemas, services, UI, and tests at audited HEAD `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f`.

No product code, migration, test, or governing document is changed by this plan.

## 2. Resolution States

Every issue has two possible closure milestones. They must not be conflated.

### Design-resolved

The governing product choice, architecture, data model, API contract, migration design, stories, acceptance criteria, and verification cases are approved. The issue is no longer an unresolved assumption and may become a scoped implementation backlog item.

### Implemented and verified

The approved design is implemented, migrations are rehearsed where applicable, focused and regression tests pass, compatibility is proven, and documentation matches the delivered behavior.

`Ready to Build` requires every pre-implementation decision and contract blocker to be design-resolved. Wave 1 completion requires every implementation and verification condition in this plan to be satisfied.

## 3. Resolution-Class Matrix

Legend: `Y` = required, `N` = not required for this issue, `C` = conditional on the selected design or supplied by a dependency.

| Issue | Product decision | Data contract | API contract | Migration design | Architecture decision | Stories / AC | Implementation | Test / verification | Documentation reconciliation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C01 Ownership identity | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| C02 Formal freeze package | N | Y | Y | Y | Y | Y | C | Y | Y |
| H01 Cut policy | C | Y | Y | Y | C | Y | Y | Y | Y |
| H02 Adjusted protein basis | N | Y | Y | C | N | Y | Y | Y | Y |
| H03 Invalid carbohydrate allocation | N | N | Y | N | N | Y | Y | Y | Y |
| H04 Target Plans | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| H05 Nutrient registry | N | Y | Y | Y | Y | Y | Y | Y | Y |
| H06 Food groups and contributions | C | Y | Y | Y | Y | Y | Y | Y | Y |
| H07 Reliability, ingredients, NOVA | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| H08 Snapshot v2 | N | Y | Y | C | Y | Y | Y | Y | Y |
| H09 Migration and schema authority | N | C | C | Y | Y | N | Y | Y | Y |
| H10 Rule ownership and versioning | N | Y | Y | C | Y | C | Y | Y | Y |
| H11 All-unknown false zero | N | Y | Y | N | C | Y | Y | Y | Y |

The matrix demonstrates why these findings are not 13 undifferentiated coding tasks. C02 is mainly governance. C01, H04, H06, H07, H09, and H10 require decisions or designs before implementation. H02 and H03 have frozen product rules and primarily require faithful contracts, implementation, and proof.

## 4. Required Ownership Groups

### 4.1 Decisions the product owner must approve first

1. **C01:** ownership principal and single-user bootstrap behavior, jointly with Architecture and Security.
2. **H01:** where the selected cut intensity persists and the user-visible behavior for blocked versus caution results. The numeric thresholds are already frozen and must not be reopened.
3. **H04:** Target Plan activation semantics, effective-date behavior, current-versus-proposed confirmation, and treatment of the first plan.
4. **H06:** unresolved machine semantics for primary category, contribution overlap, grain equivalents, qualifying dairy subtypes, and any group-rule edge case not directly executable from `PD-010`/`PD-011`.
5. **H07:** source-reliability levels and mapping, ingredients-source vocabulary, and the reviewed NOVA suggestion workflow.
6. Approve final Arabic safety and recovery copy through BA/UX without changing the governing calculation rules.

The product owner does not need to reapprove Mifflin-St Jeor, activity factors, cut percentages, BMI formula, nutrient targets, or the zero/negative carbohydrate rejection. Those are already governed.

### 4.2 Contracts and designs BA and Architecture must define

- C01 ownership ADR, owner-scoped data model, non-enumerating authorization contract, and legacy-row assignment.
- H01-H03 calculation input/output/error contract and golden examples.
- H04 immutable Target Plan schema, lifecycle, API, and effective-date rules.
- H05/H10 one Backend-owned registry and independent version model.
- H06/H07 Food classification, contribution, trait, source, reliability, ingredient, and NOVA contracts.
- H08 Snapshot v1/v2 discriminated contract and Target Plan binding.
- H09 expand-migrate-contract and rollback plan, plus Alembic runtime authority.
- H11 nullable Diary aggregation and coverage contract.
- C02 traceability package tying all contracts to stories, acceptance criteria, golden calculations, states, and tests.

### 4.3 Implementation work that starts only after freeze

- Owner principal, owner columns, scoped services, and authorization tests.
- Backend calculation-policy changes for H01-H03.
- Target Plan persistence and endpoints.
- Full registry/rule package and exact nutrient fields.
- Food contribution/trait/source/NOVA persistence and APIs.
- Snapshot v2 writer and compatible readers.
- Nullable Diary day aggregation and false-zero UI correction.
- Additive frontend integration without redesigning unrelated Foods, Diary, Profile, or Add Food behavior.

### 4.4 Verification and documentation work

- Requirement-level golden calculations, boundary cases, null/zero, ownership, compatibility, and migration tests.
- Full existing Profile, Diary, Add Food, Foods, Backend, typecheck, build, lint, and migration regressions.
- Disposable PostgreSQL fresh/populated/rollback/re-upgrade rehearsal.
- OpenAPI examples, error catalog, state matrices, and traceability to `PD-*` decisions.
- Reconcile historical architecture/implementation documents only after behavior is verified; do not edit the governing register to match an implementation shortcut.

### 4.5 Issues that can be combined safely

| Resolution package | Issues | Safe combined scope | Required separation |
|---|---|---|---|
| Calculation policy | H01, H02, H03 | One Backend calculation contract and golden scenario set | Keep cut safety, protein basis, and carb rejection as independently testable rules |
| Target history | H04, H08 | Target Plan identity can be bound into Snapshot v2 design | Do not combine migration deployment with all feature code in one change |
| Registry and versions | H05, H10 | One Backend-owned rule package and versioned registry API | Preserve independent version identifiers; do not use one umbrella version only |
| Food classification | H06, H07 | Shared Food expansion schema/API and classification workflow | Keep completeness, reliability, NOVA, groups, and traits as separate dimensions |
| Data honesty | H05, H08, H11 | One nullable nutrient/snapshot/aggregate contract | Ship the H11 rendering correction as a narrow reviewable behavior change |
| Migration governance | C01, H04-H10 | One expand-migrate-contract program and rehearsal | Use multiple additive migrations/PRs; never create one broad rewrite migration |

C02 cannot be combined away. It is the formal gate proving all packages are frozen and traceable. C01 must remain an independently reviewed security boundary.

## 5. Critical Issue Resolution

### C01 - Authenticated ownership cannot be safely migrated

- **Severity:** Critical.
- **Governing decisions:** `PD-023`, `PD-024`, `PD-025`, `PD-029`.
- **Exact problem:** The current request guard validates one configured bearer token but returns no authenticated subject. Profile, Food, and Diary Entry have no owner field, and services query records globally. The system therefore cannot prove owner scoping or safely backfill an owner for existing rows.
- **Why it blocks Wave 1:** Target Plans, contributions, traits, and Snapshot v2 would create additional unowned personal records. Adding those tables before fixing identity would multiply the privacy and migration defect.
- **Repository evidence:** `backend/app/core/auth.py:8` returns `None` after token validation; `backend/app/models.py:66`, `:86`, and `:137` define Profile, Food, and Diary Entry without ownership; list/get services use unscoped global queries; routers attach only `Depends(require_single_user)`.
- **Dependencies:** Product/Security ownership decision; authentication provider or stable singleton principal; C02; H04; H06-H09.

#### Viable alternatives

**Option A - Local principal table keyed by authenticated provider subject**

- Advantages: referential integrity; token rotation does not change ownership; future-compatible without adding multiple Profile behavior; one owner FK pattern across all entities.
- Risks: requires principal bootstrap, provider-subject mapping, and an explicit legacy-row migration.

**Option B - Direct immutable owner-subject string on every owned table**

- Advantages: fewer tables and a smaller initial migration.
- Risks: duplicated external identity, provider coupling, weaker referential integrity, harder subject migration, and repeated indexing/storage.

**Option C - Server-configured singleton principal derived from the validated token configuration**

- Advantages: smallest operational change for the current single-user product; no frontend owner input.
- Risks: must remain stable across token rotation and environments; can become an implicit global owner again unless represented explicitly in the schema and session context.

- **Recommended option:** Option A. Use a durable local principal keyed by the session's authenticated subject, with one Profile per principal. A server-provisioned singleton principal may bootstrap the current deployment, but it must be explicit and stable rather than inferred from the token value.
- **Recommended resolution:** Approve the Option A ownership ADR first, then deliver principal provisioning, owner-scoped expansion, deterministic legacy assignment, and two-owner proof as an isolated security package.

#### Acceptance conditions for closure

1. An approved ADR identifies the identity provider, subject type, token-rotation behavior, and principal bootstrap.
2. Every user-created Wave 1 entity has an owner FK or equally enforceable owner relation.
3. Backend derives owner identity from session context; API payloads do not accept authoritative owner IDs.
4. Every list/read/update/delete is owner-scoped and unauthorized IDs do not reveal record existence.
5. Existing rows receive one deterministic owner only after the owner principal is known; no heuristic backfill.
6. Unique/index constraints are owner-aware, including the single Profile rule.
7. Two-owner integration tests cover all CRUD and snapshot-after-Food-delete behavior.
8. Fresh and populated PostgreSQL migration rehearsals pass.

- **Code changes required:** Yes, after ADR/schema/API approval.
- **Closure timing:** ADR, data contract, API contract, and migration design are required before any Wave 1 schema implementation. Implementation and security proof are required before Wave 1 sign-off.

### C02 - The formal Wave 1 freeze package does not exist

- **Severity:** Critical.
- **Governing decisions:** `PD-001`, `PD-004`, `PD-029`.
- **Exact problem:** The complete register defines product decisions, but the exact physical schema, API payloads and errors, rollback plan, stories, acceptance criteria, state matrix, and golden calculations are not approved as a linked build package.
- **Why it blocks Wave 1:** Engineers would have to choose unresolved storage, identity, compatibility, and interaction behavior while coding. That would mix product decisions with implementation and make review against a stable contract impossible.
- **Repository evidence:** Documents 07 and 08 identify open physical-schema and API choices; no current routes or models implement the new contracts; the current tests encode provisional six-nutrient and carb-clamp behavior that conflicts with the complete register.
- **Dependencies:** Design-resolution of C01 and H01-H11; approved contract artifacts; exact traceability.

#### Viable alternatives

**Option A - One monolithic Wave 1 specification**

- Advantages: one approval surface and one apparent source.
- Risks: hard to review, easy to create internal contradictions, and encourages one broad implementation change.

**Option B - Linked, versioned freeze artifacts with one traceability index**

- Advantages: schema, API, migration, BA/QA, and golden calculations can be independently reviewed while remaining tied to decisions and one exact HEAD.
- Risks: requires disciplined version references and change control.

- **Recommended option:** Option B. Use one freeze index that pins approved ADRs, data dictionary, OpenAPI examples, migration/rollback plan, stories/acceptance criteria, golden scenarios, UI states, and regression matrix.
- **Recommended resolution:** Produce and formally approve the linked freeze package, then rerun readiness before authorizing implementation.

#### Acceptance conditions for closure

1. Every active Wave 1 decision has an approved contract or explicit no-change statement.
2. Physical schema and ownership constraints are exact, not semantic placeholders.
3. API requests, responses, null semantics, stable errors, idempotency, and compatibility examples are frozen.
4. Expand/migrate/contract and rollback plans are approved.
5. Stories and acceptance criteria cover loading, empty, partial, unknown, legacy, error, keyboard, RTL, responsive, and authorization states.
6. Golden calculations cover every safety and target boundary.
7. Every Critical/High issue is design-resolved and mapped to implementation/tests.
8. A readiness recheck against one exact HEAD returns Critical 0 and High unresolved 0.

- **Code changes required:** Not to produce the freeze package. Final issue completion depends on later code/test delivery by the linked implementation items.
- **Closure timing:** Required before implementation begins.

## 6. High Issue Resolution

### H01 - Cut intensity and calorie-safety outcomes are absent

- **Severity:** High.
- **Governing decisions:** `PD-005`, `PD-008`, `PD-022`, `PD-025`, `PD-026`.
- **Exact problem:** The Backend applies a fixed `Goal.cut: 0.8`. There is no selected 15/20/25 intensity, 750 kcal deficit cap, under-800 block, 800-1200 caution state, or persisted resolved deficit.
- **Why it blocks Wave 1:** The current target engine can return results that do not satisfy the approved safety policy, and Target Plans cannot reproduce the user's selected cut policy.
- **Repository evidence:** `backend/app/services/calc.py:14-18` defines a fixed goal factor; `calculate_targets` has no cut-intensity input or safety result; Profile schemas/models have no cut-intensity field.
- **Dependencies:** C01, C02, H04, H10; approved safety copy and API error/warning catalog.

#### Real design alternatives

**Option A - Persist cut preference on Profile and copy the resolved input/output into each Target Plan**

- Advantages: preserves the user's current preference and immutable history; preview/save behavior is straightforward.
- Risks: Profile and active plan can diverge unless activation is transactional.

**Option B - Store cut intensity only as an input on the current/immutable Target Plan**

- Advantages: one authoritative target-state record.
- Risks: Profile editing needs plan-aware draft behavior; no independent preference before first activation.

- **Recommended option:** Option A, with one transactional save/activation service that updates Profile preference and creates the immutable plan together. Existing cut Profiles map to the approved 20% default without changing unrelated custom macro settings.
- **Recommended resolution:** Freeze the cut input/output/error contract and persisted preference model, then implement all safety rules in the shared Backend preview/save path.

#### Acceptance conditions for closure

1. Preview and save accept only approved cut intensities and default to 20% for legacy/current cut state.
2. Automatic deficit is capped at 750 kcal/day.
3. Result below 800 is a stable Backend block and cannot be saved/activated.
4. Results from 800 through 1200 return a strong, non-technical caution state.
5. Preview exposes resolved calories, deficit amount/percentage, cap application, and safety state before save.
6. Identical preview/save input yields identical output and warnings.
7. Mifflin and current activity factors remain unchanged.
8. Golden boundary tests include 799/800/1200 and capped/uncapped scenarios.

- **Code changes required:** Yes.
- **Closure timing:** Persistence and API decisions before implementation; implementation and golden proof before Wave 1 sign-off.

### H02 - BMI-aware adjusted protein calculation is absent

- **Severity:** High.
- **Governing decisions:** `PD-006`, `PD-008`, `PD-025`, `PD-026`.
- **Exact problem:** The Backend always calculates protein from actual weight. It does not compute BMI, reference weight, adjusted weight, or disclose the calculation basis.
- **Why it blocks Wave 1:** Target accuracy and reproducibility differ materially for BMI >= 30, and a Target Plan cannot explain or reproduce its protein result.
- **Repository evidence:** `backend/app/services/calc.py:54` multiplies `protein_per_kg` by `weight_kg`; current tests explicitly expect actual-weight behavior for the 115 kg scenario.
- **Dependencies:** C02, H04, H10; H01/H03 shared calculation contract.
- **Viable alternatives:** None at product level. The formula and BMI boundary are frozen by `PD-006`; substituting ideal weight, target weight, or another coefficient is not viable without a formal change decision.
- **Recommended option:** Use the exact governed actual/adjusted-weight formula; do not introduce an alternative weight basis.
- **Recommended resolution:** Implement one Backend calculation helper returning actual or adjusted calculation weight, basis, BMI, and protein target. Persist the basis and calculation weight in the Target Plan and return them in preview/save.

#### Acceptance conditions for closure

1. BMI below 30 uses actual weight.
2. BMI at or above 30 uses the exact reference/adjusted formula in `PD-006`.
3. Boundary tests cover values immediately below, at, and above BMI 30.
4. Custom grams/kg is preserved and applied to calculation weight.
5. Preview/save expose user-readable basis metadata without a TypeScript formula duplicate.
6. Target Plan persists factor, basis, calculation weight, and calculation-engine version.
7. Existing obsolete actual-weight golden expectations are replaced with governed results, not weakened.

- **Code changes required:** Yes.
- **Closure timing:** Data/API contract before implementation; code and golden tests before Wave 1 sign-off.

### H03 - Zero or negative carbohydrate allocation is silently clamped

- **Severity:** High.
- **Governing decisions:** `PD-007`, `PD-022`, `PD-025`, `PD-029`.
- **Exact problem:** `calculate_targets` sets `carb_clamped` and returns `max(carb_cal, 0) / 4` as a normal successful target. Low-carbohydrate warning bands are also absent.
- **Why it blocks Wave 1:** The API represents an invalid configuration as a valid zero-carb plan, violating the explicit safety and truthfulness rule.
- **Repository evidence:** `backend/app/services/calc.py:58-60`; `backend/app/schemas.py:39`; `backend/tests/test_calc.py:39` currently asserts clamping.
- **Dependencies:** C02; H01/H02 shared calculation contract; stable API error mapping.
- **Viable alternatives:** None for zero/negative allocation. `PD-007` requires rejection. Warning presentation below 130 and below 100 may vary visually, but severity and Backend result must remain explicit.
- **Recommended option:** Use a structured Backend rejection for non-positive allocation and typed warning metadata for valid low-carbohydrate results.
- **Recommended resolution:** Replace successful clamp behavior with a typed calculation-domain error translated to a stable API error. Return warning metadata for valid results below 130 and stronger metadata below 100.

#### Acceptance conditions for closure

1. Positive carbohydrate allocation returns the exact remaining-calorie calculation.
2. Valid targets below 130 and below 100 return distinct warning levels.
3. Zero and negative allocations fail preview and save with one stable machine code and Arabic display mapping.
4. Invalid output cannot create or activate a Target Plan.
5. No ordinary response reports zero carbs with `carb_clamped=true` as success.
6. Preview and save share the same domain validation.
7. Tests cover positive, warning, zero, negative, malformed, and duplicate-submit paths.

- **Code changes required:** Yes.
- **Closure timing:** API/error acceptance criteria before implementation; code and tests before Wave 1 sign-off.

### H04 - Immutable Target Plan model and lifecycle are not frozen

- **Severity:** High.
- **Governing decisions:** `PD-008`, `PD-023`, `PD-024`, `PD-025`, `PD-026`, `PD-029`.
- **Exact problem:** Current Profile preview/save calculates only current targets. No immutable plan, current/history query, activation, effective range, or historical-day binding exists.
- **Why it blocks Wave 1:** Target history, Snapshot v2, rule reproducibility, and later four-week review all depend on a stable plan identity and lifecycle.
- **Repository evidence:** No Target Plan model/schema/service/route is registered; `backend/app/api/router.py:6-9` registers only health, profile, foods, and diary; current `TargetResponse` has no plan identity/version.
- **Dependencies:** C01, C02, H01-H03, H05, H08-H10.

#### Viable alternatives

**Option A - Fully normalized immutable target columns**

- Advantages: strong constraints and direct querying.
- Risks: schema churn whenever additional target structures evolve; many columns and joins.

**Option B - JSONB-only immutable calculation document**

- Advantages: flexible versioned payload and simple preservation.
- Risks: weak relational constraints for owner/effective range/current plan and harder indexed queries.

**Option C - Hybrid immutable plan**

- Store owner, identity, effective dates, status/current relation, and independent versions as constrained columns; store a versioned validated inputs/outputs/additional-target document.
- Advantages: relational lifecycle integrity plus forward-compatible calculation payload.
- Risks: requires strict Pydantic/JSON schema validation and disciplined version readers.

- **Recommended option:** Option C.
- **Recommended resolution:** Approve the hybrid immutable Target Plan schema and lifecycle, then implement preview/current/history/activation with transactional idempotency and historical date binding.

#### Acceptance conditions for closure

1. Product/BA approve first-plan, proposed-plan, confirmation, activation, and effective-date semantics.
2. The physical schema enforces ownership, immutability, ordering, and at most one active plan for an effective instant.
3. A plan stores every item required by `PD-008` plus independent versions from `PD-026`.
4. Existing users receive no invented historical plans; the first plan starts only at explicit activation.
5. Preview is non-persisting; activation is explicit and idempotent.
6. Current/history APIs are additive and owner-scoped.
7. Historical Diary dates resolve the plan active for that date after later Profile changes.
8. Concurrency tests prove duplicate activation cannot create overlapping active plans.

- **Code changes required:** Yes.
- **Closure timing:** Product lifecycle, schema, API, and migration design before implementation; implementation/compatibility proof before Wave 1 sign-off.

### H05 - Nutrient registry is incomplete and duplicated

- **Severity:** High.
- **Governing decisions:** `PD-002`, `PD-009`, `PD-013`, `PD-014`, `PD-024`, `PD-025`, `PD-026`.
- **Exact problem:** Backend and frontend independently define six nutrients, four target types, and only one numeric target. Food lacks four exact semantic fields: selenium, iodine, folate DFE, and vitamin A RAE.
- **Why it blocks Wave 1:** Targets, completeness, snapshots, and UI can drift. Generic folate/vitamin A fields cannot safely satisfy the governed DFE/RAE meanings.
- **Repository evidence:** `backend/app/services/nutrients.py` and `frontend/lib/nutrients.ts` duplicate definitions; `backend/app/models.py:107-124` lacks the four exact fields and contains generic `folate_mcg`/`vitamin_a_mcg`; current tests enforce only the provisional six-item registry.
- **Dependencies:** C01/C02, H04, H08-H10.

#### Viable alternatives

**Option A - Runtime Backend registry endpoint**

- Advantages: one live authority; version can accompany every response; frontend cannot silently diverge.
- Risks: requires loading/error/cache behavior and compatibility policy.

**Option B - Backend-owned versioned registry source with generated frontend artifact**

- Advantages: no runtime registry request and compile-time frontend metadata.
- Risks: generated artifacts can become stale unless CI proves regeneration; still creates a checked-in derivative.

- **Recommended option:** Option A for values/metadata, with frontend types generated from OpenAPI. A cached registry response is acceptable; an independently editable TypeScript definition list is not.
- **Recommended resolution:** Freeze one complete versioned Backend registry contract, add only the four missing exact nullable fields, and migrate consumers away from the provisional frontend authority.

#### Acceptance conditions for closure

1. One Backend package defines all 16 exact keys, units, precision, order, participation, seven target types, sources, and versions.
2. Every fixed, sex, age, and calorie-derived target in `PD-009` is executable and golden-tested.
3. The four missing exact nullable fields are added without populating legacy unknowns.
4. Generic folate/vitamin A are preserved as compatibility fields and never silently converted to DFE/RAE.
5. Known zero round-trips as zero; unknown round-trips as null.
6. Frontend renders authoritative registry metadata and has no editable duplicate.
7. Deferred nutrients receive no fabricated target.
8. Registry contract and migrations are backward compatible.

- **Code changes required:** Yes.
- **Closure timing:** Registry/data/API/version contract before implementation; migration, implementation, and full target tests before Wave 1 sign-off.

### H06 - Food-group registry, contributions, and traits do not exist

- **Severity:** High.
- **Governing decisions:** `PD-010`, `PD-011`, `PD-013`, `PD-014`, `PD-024`, `PD-025`, `PD-026`.
- **Exact problem:** The repository has only a free-text Food category. It has no governed group registry, simple/composite kind, quantitative per-basis contributions, analytical traits, group-data status, group coverage, or required validation.
- **Why it blocks Wave 1:** Snapshot v2 and future analysis cannot derive truthful group intake from category or current Food rows. Implementing later analysis without quantitative frozen inputs would force guessing.
- **Repository evidence:** `backend/app/models.py:92` stores only `category`; Food schemas/services contain no contribution, trait, kind, or group-data contract; no group registry exists.
- **Dependencies:** C01/C02, H08-H10; product clarification of executable edge semantics.

#### Viable alternatives

**Option A - Normalized contribution and trait child tables**

- Advantages: DB uniqueness/indexing, queryable contributions, explicit ownership, and straightforward validation.
- Risks: more joins and additive migration objects.

**Option B - Versioned JSONB contribution document on Food**

- Advantages: smaller table count and flexible payload.
- Risks: uniqueness/total constraints move entirely to service code, harder analytics/indexing, and more difficult partial updates.

- **Recommended option:** Option A. Keep the registry in Backend code/config; persist Food-specific contributions and traits relationally.
- **Recommended resolution:** Approve the normalized contribution/trait schema and executable group rules, then implement additive Food contracts without inferring classifications for legacy Foods.

#### Acceptance conditions for closure

1. Product/BA freeze exact group keys, units, cadence, caps, exclusions, and unresolved grain/dairy/overlap semantics without expanding deferred scope.
2. Food kind and group-data status are controlled values.
3. One Food has at most one contribution per group key.
4. Amounts are non-negative; non-overlapping total is <=100 per Food basis; partial total is allowed.
5. Traits are unique and do not add to contribution totals or duplicate servings.
6. Primary category remains organizational and is not analysis input.
7. Existing Foods remain unknown; migration does not infer groups from category/name.
8. Registry and Food APIs are versioned/additive and all governed serving rules have golden tests.

- **Code changes required:** Yes.
- **Closure timing:** Product edge decisions and physical/API contract before implementation; implementation, migration, and golden group tests before Wave 1 sign-off.

### H07 - Controlled source reliability, ingredients, and NOVA do not exist

- **Severity:** High.
- **Governing decisions:** `PD-012`, `PD-013`, `PD-014`, `PD-024`, `PD-025`, `PD-026`.
- **Exact problem:** Food has free-text `data_source` only. There is no controlled source type, Backend-derived reliability, ingredients text/source, NOVA value, or reviewed suggestion state.
- **Why it blocks Wave 1:** Snapshot v2 requires these values at logging time. Reliability, completeness, NOVA, and nutrient quality cannot be safely separated without explicit source and classification contracts.
- **Repository evidence:** `backend/app/models.py:126` stores generic `data_source`; no source/reliability/NOVA/ingredients model, schema, service, route, or registry definition exists.
- **Dependencies:** C01/C02, H05/H06, H08-H10.

#### Viable alternatives

**Option A - Store source type, derive reliability live, snapshot the derived result**

- Advantages: avoids editable/duplicated Food reliability; rule changes are versioned; snapshot preserves historical interpretation.
- Risks: current Food display may change after a reliability-rule update unless version context is shown.

**Option B - Persist both source type and derived reliability on Food**

- Advantages: fast reads and stable Food display.
- Risks: redundant derived state can drift and would require recomputation/migration when rules change.

- **Recommended option:** Option A. Store user-selected source type and ingredients provenance; derive Food reliability through versioned Backend rules; persist source type, derived reliability, and rule version in Snapshot v2.
- **Recommended resolution:** Freeze the source/reliability/NOVA mappings and review states, then add nullable Food fields and Backend derivation while preserving legacy unknowns.

#### Acceptance conditions for closure

1. Product owner approves reliability levels, exact source-type mapping, ingredients-source values, and reviewed NOVA workflow.
2. User cannot directly set reliability.
3. NOVA allows only 1/2/3/4/unknown and is never inferred from macros alone.
4. Any system suggestion remains uncommitted until user review; if suggestions are deferred, manual reviewed classification remains explicit.
5. Ingredients are transparency/classification data, not hazard claims.
6. Existing rows remain unknown and retain free-text `data_source`; no heuristic migration.
7. Completeness, reliability, NOVA, and group classification remain separate response dimensions.
8. Snapshot v2 stores the historical source/reliability/NOVA values and applicable versions.

- **Code changes required:** Yes.
- **Closure timing:** Mapping and review decisions before implementation; persistence/API/rules/tests before Wave 1 sign-off.

### H08 - Snapshot v2 and Target Plan binding do not exist

- **Severity:** High.
- **Governing decisions:** `PD-008`, `PD-013`, `PD-014`, `PD-023`, `PD-024`, `PD-025`, `PD-026`.
- **Exact problem:** Current snapshots are flat, unversioned JSON. They preserve present nutrients but lack group contributions, traits, NOVA, source/reliability, completeness, Target Plan identity, and independent rule versions.
- **Why it blocks Wave 1:** New Diary records cannot preserve the governed state at logging time, and old records could be accidentally reinterpreted using current Food/rules.
- **Repository evidence:** `backend/app/services/diary.py:39-63` creates the flat snapshot; `backend/app/models.py:151` has one JSON/JSONB field; update scales the existing snapshot, which is a useful baseline, but no v1/v2 discriminator exists.
- **Dependencies:** C01/C02, H04-H07, H09/H10.

#### Viable alternatives

**Option A - Versioned JSONB envelope in the current column plus constrained owner/plan linkage**

- Advantages: preserves current immutable-snapshot architecture, supports nullable/extensible values, and avoids a historical rewrite.
- Risks: requires strict versioned validators/readers and deliberate query/index strategy.

**Option B - Normalize all snapshot nutrients, groups, traits, and provenance**

- Advantages: strongly queryable and constrainable.
- Risks: large schema/migration surface, many joins, and unnecessary rewrite pressure on immutable legacy JSON.

- **Recommended option:** Option A. Add a discriminated v2 envelope, keep v1 reader support, and store owner/Target Plan identity as constrained columns or an equivalently validated immutable link.
- **Recommended resolution:** Approve and deploy compatible v1/v2 readers before enabling the Backend v2 writer; prove mixed-history behavior before any contract step.

#### Acceptance conditions for closure

1. Contract distinguishes Snapshot v1 and v2 unambiguously.
2. Backend alone constructs v2 from Food, active Target Plan, and versioned rules.
3. V2 contains every field required by `PD-014`, preserving number/null semantics.
4. Quantity edit scales known values and preserves null; meal movement keeps the same snapshot.
5. Food edit/delete and later rule changes cannot alter old snapshots.
6. V1 remains readable through deployment and rollback compatibility windows and is never enriched from current Food.
7. API rejects/ignores client-authoritative nutrient totals.
8. Mixed v1/v2 day aggregation and historical plan tests pass.

- **Code changes required:** Yes.
- **Closure timing:** Snapshot/plan/version contract before implementation; writer/readers, compatibility, and history proof before Wave 1 sign-off.

### H09 - Wave 1 migration and rollback are unfrozen; schema authority is ambiguous

- **Severity:** High.
- **Governing decisions:** `PD-024`, `PD-029` and the schema-bearing requirements in `PD-008`, `PD-009`, `PD-011`, `PD-012`, `PD-014`, `PD-023`, `PD-026`.
- **Exact problem:** Baseline migrations 0001-0003 are committed, but no Wave 1 expand/migrate/contract plan exists. Application startup still calls `SQLModel.metadata.create_all`, which can hide migration drift and weakens Alembic as deployment authority.
- **Why it blocks Wave 1:** Ownership, plans, exact nutrients, contributions, source/NOVA, and versions cannot be safely deployed or rolled back without an ordered compatibility plan.
- **Repository evidence:** `backend/app/db/session.py:12-15` calls `SQLModel.metadata.create_all`; committed migrations stop at `0003_diary_meal_type`; no Wave 1 revisions exist.
- **Dependencies:** C01/C02 and approved schemas for H04-H08/H10.

#### Viable alternatives

**Option A - Alembic is the sole application/runtime schema authority**

- Advantages: deterministic deployment, visible drift, and reproducible upgrade/rollback.
- Risks: local developer bootstrap must explicitly run migrations.

**Option B - Permit `create_all` only in isolated tests or an explicit disposable-development mode**

- Advantages: convenient ephemeral tests.
- Risks: configuration mistakes can reintroduce runtime drift; generated schema may differ from migration history.

- **Recommended option:** Alembic-only for application runtime and deployed environments. Metadata `create_all` may remain inside isolated unit-test fixtures that never represent migration proof.
- **Recommended resolution:** Freeze a staged additive migration sequence and rollback window, remove runtime schema bypass, and rehearse every path on disposable PostgreSQL before release approval.

#### Acceptance conditions for closure

1. Approved migration inventory maps every added/changed object to its owning requirement.
2. Revisions are additive, nullable-first, ordered, and independently reviewable; 0001-0003 remain unchanged.
3. Ownership backfill uses the approved principal only.
4. No unknown nutrient, group, source, NOVA, DFE/RAE, snapshot, or Target Plan history is invented.
5. Compatible readers deploy before v2 writers; contract removal waits for evidence.
6. Downgrade/rollback-compatible application behavior and data preservation are documented.
7. Runtime schema creation cannot bypass Alembic.
8. Fresh, populated, rollback, and re-upgrade rehearsals pass on disposable PostgreSQL with realistic data.

- **Code changes required:** Yes, for migration revisions and runtime schema policy, after design approval.
- **Closure timing:** Complete migration/rollback design before schema implementation; executable rehearsal before Wave 1 sign-off.

### H10 - Independent rule versions and one Backend-owned rules package do not exist

- **Severity:** High.
- **Governing decisions:** `PD-009`, `PD-010`, `PD-012`, `PD-014`, `PD-025`, `PD-026`.
- **Exact problem:** Nutrient metadata is duplicated between Python and TypeScript, no required version identifiers exist, and there is no Backend package covering all governed policy areas.
- **Why it blocks Wave 1:** A Target Plan or Snapshot cannot prove which nutrient, calculation, group, source, NOVA, or snapshot rules produced it. Later rule changes would silently reinterpret history.
- **Repository evidence:** `backend/app/services/nutrients.py` and `frontend/lib/nutrients.ts` are independent; no `nutrition_registry_version`, `calculation_engine_version`, `food_group_rules_version`, `analysis_rules_version`, or `snapshot_schema_version` is present in models/schemas/snapshots.
- **Dependencies:** C02, H04-H08; API and persistence contracts.

#### Viable alternatives

**Option A - Typed Backend Python rule modules plus versioned registry API**

- Advantages: aligns with current stack, keeps execution and metadata together, and supports direct tests.
- Risks: requires discipline to keep definitions declarative and exportable.

**Option B - Versioned JSON/YAML rule manifests loaded by Backend and used to generate clients**

- Advantages: language-neutral and easy to diff.
- Risks: weaker compile-time domain modeling, custom validation/generation tooling, and risk of configuration becoming an unreviewed rules language.

- **Recommended option:** Option A, with declarative typed definitions, explicit independent version constants, OpenAPI-exported metadata, and generated frontend types.
- **Recommended resolution:** Establish the Backend rules package and version-bump policy before building Target Plans or Snapshot v2, then persist the applicable independent versions on both.

#### Acceptance conditions for closure

1. One Backend package owns nutrients, food groups, macro policy, deficit policy, analysis policy placeholder/version, source reliability, NOVA definitions, and versioning.
2. All five required versions exist independently; an umbrella version cannot replace them.
3. Target Plans and Snapshot v2 persist applicable versions.
4. Analysis version is defined but only persisted with Analysis Snapshots in Wave 3.
5. Frontend contains no independently editable rule values.
6. Version-bump policy states which version changes for each rule category.
7. Tests prove old plan/snapshot readers retain original semantics after a version bump.

- **Code changes required:** Yes.
- **Closure timing:** Architecture/version policy and API contract before implementation; persistence and reproducibility proof before Wave 1 sign-off.

### H11 - All-unknown nutrient data is displayed as numeric zero

- **Severity:** High.
- **Governing decisions:** `PD-002`, `PD-009`, `PD-013`, `PD-014`, `PD-025`, `PD-029`.
- **Exact problem:** Diary aggregation initializes every nutrient amount to zero. When no entry has a known value, the UI can display `0` with an "at least" qualifier and target/status calculations instead of unavailable.
- **Why it blocks Wave 1:** It violates the central truth rule that unknown is not zero and could produce false minimum/maximum target conclusions.
- **Repository evidence:** `frontend/components/DiaryPage.tsx:535-547` defines `amount: number` and initializes `amount = 0`; `:575-587` derives amount, percent, target status, and progress without first suppressing the all-unknown case. Backend snapshots already preserve null for individual optional values, so this is a contract/aggregation/rendering defect rather than missing source data alone.
- **Dependencies:** H05 authoritative registry; H08 v2 contract; H10 rule metadata. The current UI defect can be covered by a narrow regression once the nullable aggregate shape is frozen.

#### Viable alternatives

**Option A - Backend day summary returns nullable amount, known count, total count, and coverage**

- Advantages: conforms to Backend-authoritative Diary summary/coverage; one implementation for all clients; simpler truthful UI.
- Risks: additive API work and compatibility handling.

**Option B - Frontend continues aggregating raw snapshots but returns `amount: null` when known count is zero**

- Advantages: smallest immediate fix.
- Risks: duplicates governed aggregation on the client and is insufficient as the final `PD-025` contract.

- **Recommended option:** Option A for Wave 1. Option B is acceptable only as a temporary narrow defect fix if it is explicitly removed when the Backend summary contract lands.
- **Recommended resolution:** Define a nullable Backend day-summary aggregate, integrate it additively, and make the current UI suppress amount/progress/status whenever no value is known.

#### Acceptance conditions for closure

1. Aggregate amount is null/unavailable when `known_count == 0`.
2. Known explicit zero produces amount zero and counts as known.
3. Partial coverage sums only known values and labels the amount as a confirmed minimum.
4. All-unknown suppresses target percentage, progress bar, remaining/available, and adequacy/limit status.
5. Empty day has no fabricated coverage percentage or zero nutrient rows.
6. Backend and frontend use the same registry key order and nullable semantics.
7. Mixed v1/v2 and multiple-entry tests cover null, known zero, partial, and complete coverage.
8. No blank alert/live-region output is introduced.

- **Code changes required:** Yes.
- **Closure timing:** Nullable aggregate/API contract before final implementation; the false-zero behavior must be fixed and verified before Wave 1 sign-off.

## 7. Final Execution Sequence

Each stage is independently reviewable. A stage may not absorb later-wave scope or unrelated redesign work.

### Stage 0 - Protect the baseline

- Pin audited baseline and governing register versions.
- Record existing regression suites and compatibility contracts.
- Declare direct gram/ml Diary logging, Day Status UI, analysis, weekly goals, Progress, health measurements, and deferred nutrients out of Wave 1 implementation.
- Deliverable: scope guard and regression inventory only.

### Stage 1 - Product-owner decision packet

- Resolve C01 identity/bootstrap direction.
- Resolve H01 cut-preference persistence and safety UX behavior without changing thresholds.
- Resolve H04 plan activation/effective-date semantics.
- Resolve H06 group edge semantics and primary-category representation.
- Resolve H07 source-reliability mapping and NOVA review workflow.
- Deliverable: approved product/change decisions; no code.

### Stage 2 - Architecture and data ADRs

- Ownership principal and owner-scoping ADR.
- Hybrid Target Plan and Snapshot v2 ADR.
- Normalized contribution/trait storage ADR.
- Backend rules/versioning ADR.
- Alembic authority and expand-migrate-contract ADR.
- Deliverable: approved ADRs and exact physical schema; no product implementation.

### Stage 3 - API, BA, QA, and golden-contract freeze

- Freeze registry, Profile preview/save, Target Plan, Food expansion, Diary v1/v2, ownership, error, and idempotency contracts.
- Write user stories and Given/When/Then acceptance criteria.
- Freeze golden calculation, null/zero, compatibility, authorization, and UI state matrices.
- Recheck C02 and mark every High issue design-resolved or return it for decision.
- Deliverable: `Ready to Build` candidate package; no broad implementation.

### Stage 4 - Ownership expansion

- Add principal/owner schema and migration.
- Scope existing services and APIs.
- Backfill only the approved owner.
- Add two-owner security tests.
- Review independently before any new owned expansion tables.

### Stage 5 - Backend rules and calculation policy

- Introduce versioned Backend rules package.
- Implement H01-H03 and complete nutrient targets.
- Keep activity factors and Mifflin unchanged.
- Add golden tests before frontend integration.

### Stage 6 - Target Plan foundation

- Add immutable plan storage, current/history/activation, effective-date resolution, versions, and idempotency.
- Keep four-week review UI deferred to Wave 4.
- Review migration and concurrency proof independently.

### Stage 7 - Food data expansion

- Add exact nutrient fields, group contributions, traits, source type, ingredients, NOVA, and derived reliability.
- Preserve existing Food routes and per-100 source-of-truth behavior.
- Do not redesign Foods or Add Food beyond additive contract integration.

### Stage 8 - Snapshot v2 and truthful aggregation

- Deploy v1/v2 compatible readers first.
- Enable Backend v2 writer after compatibility proof.
- Bind active Target Plan/rule versions.
- Add nullable day aggregation and fix H11 in a narrow UI change.
- Preserve serving-only Diary behavior, meal sections, quantity edits, and snapshot immutability.

### Stage 9 - Migration rehearsal and compatibility gate

- Exercise fresh, populated, rollback-compatible, and re-upgrade paths on disposable PostgreSQL.
- Prove no unknown-to-zero, no guessed history, no v1 rewrite, and no unowned row.
- Confirm runtime cannot bypass Alembic.

### Stage 10 - Full verification and reconciliation

- Run all focused Wave 1 tests and every existing regression suite.
- Verify OpenAPI examples, RTL/responsive/accessibility states, legacy records, and security.
- Reconcile implementation documents with verified behavior.
- Perform the final `PD-029` readiness/completion review on the exact final head.

## 8. Change-Control Rules For Execution

1. One issue cluster per design review; do not combine all schema and UI work into one PR.
2. Product decisions are approved before their contracts; contracts are approved before code.
3. Existing API behavior changes only through additive compatibility or an approved structured-error correction.
4. Never infer owner, nutrient semantics, Food group, source type, reliability, NOVA, Target Plan history, or snapshot values during migration.
5. Keep Snapshot v1 readers until compatibility evidence permits contract work.
6. Do not weaken or delete regression tests to fit new behavior; replace obsolete expectations with governing acceptance evidence.
7. Do not reopen deferred scope through convenience implementation.
8. Do not redesign unrelated Foods, Diary, Profile, Add Food, or global navigation.
9. Every implementation change links to its issue, `PD-*` decisions, approved contract, and closure tests.
10. A failed migration, security, calculation, null/zero, or compatibility gate blocks progression.

## 9. Product-Owner Decisions Still Required

1. Authenticated principal/bootstrap and legacy single-user ownership assignment.
2. Cut-intensity preference persistence and final blocked/caution interaction copy.
3. Target Plan proposal, confirmation, activation, and effective-date semantics.
4. Primary-category representation and unresolved executable food-group edge semantics.
5. Source-reliability levels/mapping, ingredients-source vocabulary, and NOVA review workflow.

No decision is required to reopen approved numeric rules or add deferred features.

## 10. Exact Blockers Before Implementation

1. C01 ownership ADR, schema, API, and backfill design.
2. H01-H03 calculation contract and golden outcomes.
3. H04 Target Plan physical schema and lifecycle contract.
4. H05/H10 authoritative registry and independent version contract.
5. H06/H07 Food classification/provenance decisions and data contract.
6. H08 Snapshot v1/v2 and Target Plan binding contract.
7. H09 approved migration/rollback and Alembic-authority design.
8. H11 nullable aggregation contract.
9. C02 approved stories, acceptance criteria, API examples, states, regression plan, and traceability index.
10. A readiness recheck showing no unresolved Critical/High design issue.

## 11. Exact Blockers Before Wave 1 Completion

1. All approved implementations for C01 and H01-H11 delivered without unrelated behavior changes.
2. Owner isolation and non-enumeration proven end to end.
3. Calculation, targets, plans, registry, groups, reliability/NOVA, and versions proven by golden tests.
4. Snapshot v1/v2 compatibility and historical immutability proven.
5. Unknown/null/known-zero and all-unknown presentation proven across Backend and frontend.
6. Fresh/populated/rollback/re-upgrade PostgreSQL migration rehearsal passed.
7. Existing Profile, Diary, Add Food, Foods, Backend, build, typecheck, lint, accessibility, RTL, and responsive regressions passed.
8. Final documentation reflects verified behavior and no provisional claim remains.
9. Final `PD-029` review reports Critical 0 and High 0 on the exact delivered head.

## 12. Recommended Next Action

Create and approve **Stage 1: Product-owner decision packet**. Start with C01 because ownership determines every new table and migration. In parallel, BA may prepare decision-ready options for H01, H04, H06, and H07, but Architecture must not author migrations or implementation code until those choices are approved.

**Readiness verdict remains Not Ready to Build.**
