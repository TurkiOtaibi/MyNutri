# Wave 1 Readiness Recheck

## 1. Audit Identity

| Item | Verified value |
|---|---|
| Branch | `main` |
| Audited HEAD | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` |
| HEAD subject | `docs: complete nutrition quality decision register v1.1` |
| Remote comparison | Local `main` equals `origin/main` |
| Baseline merge | `3ecd460 Merge PR #1: checkpoint online-only Foods and Diary experience` |
| Baseline implementation | `d6caf0a feat(v1): checkpoint online-only foods and diary experience` |
| Governing register | `PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md` |
| Register integrity | 30 unique decisions, `PD-000` through `PD-029`; no missing, duplicate, or unexpected decision IDs |
| Audit date | 2026-07-15 |

The earlier provisional versions of documents 07 and 08 are discarded. This report is derived from the complete register at the audited HEAD and from current code, migrations, routes, services, UI, and executable tests.

## 2. Readiness Verdict

**Verdict: Not Ready to Build Wave 1.**

The current product baseline is real, merged, and reproducible. The governing register is also complete. Those two former blockers are resolved. The complete register, however, proves that Wave 1 is substantially larger than the provisional six-nutrient stabilization described by the old report.

Current gate state:

| Gate | Result |
|---|---|
| All formal decisions reconciled | Passed in document 07 |
| Reproducible baseline | Passed |
| Complete governing register | Passed |
| Critical unresolved issues | **2** |
| High unresolved issues | **11** |
| Exact schema frozen and approved | Failed |
| Migration and rollback plan approved | Failed |
| API contracts approved | Failed |
| Stories and acceptance criteria complete | Failed |
| Golden calculations and state matrices complete | Failed |

`PD-029` permits `Ready to Build` only with Critical = 0 and High = 0 and with the contracts above approved. This audit therefore cannot return `Conditionally Ready` or `Ready to Build`.

## 3. Reproducible Implemented Baseline

### Architecture and runtime

- FastAPI, SQLModel, PostgreSQL, Alembic, and Next.js.
- Online-only personal-data runtime; no registered sync API and no IndexedDB/Dexie source of truth.
- Single shared bearer-token guard, but not an authenticated user-subject ownership model.
- Existing startup still invokes `SQLModel.metadata.create_all`; Alembic is present but is not the sole schema authority at runtime.

### Migrations and data model

- Linear committed chain: `0001_initial.py -> 0002_foods_v1_per_basis.py -> 0003_diary_meal_type.py`.
- Profile stores sex, birth date, height, weight, activity, goal, protein factor, and fat ratio.
- Food stores per-100g/per-100ml nutrition, default unit data, core macros, and many nullable nutrients.
- Diary Entry stores date, Food reference, serving quantity, meal type, and an unversioned JSON/JSONB nutrition snapshot.
- Food hard deletion leaves Diary history readable through the snapshot.

### Product behavior

- Foods list/details/create/edit/delete, serving calculations, search/filter/sort/pagination, and optional nutrients.
- Diary Gregorian Sunday-first navigation, four meal sections, serving quantity logging, meal movement, quantity edit, hard delete, frozen snapshot totals, and current nutrition details UI.
- Add Food two-state search/configuration sheet with meal preselection and duplicate-submit protection.
- Profile server preview/save, dirty-state handling, sex-aware fat defaults, customizable protein/fat settings, and current targets UI.
- Arabic-first RTL UI and Western numeral formatting in the redesigned surfaces.

### Current calculation behavior

- Backend Mifflin-St Jeor implementation exists.
- Current activity factors and goal factors exist.
- Protein default is `1.2`, but calculation uses actual weight only.
- Male/female fat defaults are represented in current Profile behavior.
- Carbohydrate calories are derived as the remainder, but a negative remainder is silently clamped to zero and returned with `carb_clamped`.

### Current nutrient behavior

- Backend and frontend each contain an independently editable six-item nutrient registry.
- The current six items are fiber, sodium, saturated fat, added sugar, potassium, and cholesterol.
- Only fiber currently has a numeric target in that provisional registry.
- Current Food storage contains 12 of the 16 exact `PD-009` fields.
- Diary snapshot creation and quantity scaling preserve known values, explicit zero, and null for currently supported fields.
- Current Diary additional-nutrient UI can present an all-unknown aggregate as numeric zero, contrary to `PD-013`.

## 4. Remaining Local Changes

At audit start there were no tracked application changes. The only audit outputs are the newly regenerated untracked documents:

- `docs/product/nutrition-quality-expansion/07_PRODUCT_DECISION_RECONCILIATION.md`
- `docs/product/nutrition-quality-expansion/08_WAVE1_READINESS_RECHECK.md`

The pre-existing untracked `frontend/debug-diary.png` is unrelated, remains untouched, and is not audit evidence.

No implementation, migration, test, BA/QA, or configuration file was modified.

## 5. Full Wave 1 Scope From The Register

Wave 1 is the data-and-rules foundation for later user experiences. It includes all of the following:

1. Energy policy with cut intensities of 15%, 20%, and 25%, a 750 kcal/day maximum automatic deficit, a block below 800 kcal/day, and strong caution from 800 through 1200 kcal/day.
2. Protein calculation using actual weight below BMI 30 and the approved adjusted-weight formula at BMI 30 or above.
3. Sex-aware fat defaults, custom-value preservation, carbohydrate remainder warnings, and structured rejection of zero/negative carbohydrate allocation.
4. Immutable Target Plan Versions with effective dates, inputs, outputs, additional targets, cut intensity, protein basis, custom settings, and rule versions.
5. The complete 16-nutrient registry and all fixed, sex-based, age-based, and calorie-derived target rules in `PD-009`.
6. The complete food-group registry, serving/equivalent rules, goals, exclusions, weekly rules, and classification coverage in `PD-010`.
7. Food primary category, simple/composite kind, quantitative group contributions, analytical traits, and known/estimated/unknown group-data status.
8. Ingredients, ingredient source, NOVA classification, and a user-reviewed classification model.
9. Separate nutrition completeness, source reliability, Diary nutrient coverage, and food-group coverage semantics.
10. Diary Snapshot v2 with Food identity, all nutrients, group contributions, traits, NOVA, source/reliability, completeness, and independent rule/schema versions.
11. Owner binding for all user-created records, with Backend-derived session identity and non-leaking authorization failures.
12. Expand-Migrate-Contract delivery, v1/v2 compatibility, realistic disposable PostgreSQL rehearsal, and rollback compatibility.
13. Additive Backend-authoritative APIs, stable errors, null semantics, and idempotency for harmful duplicate mutations.
14. Independent nutrition registry, calculation engine, food-group rules, analysis rules, and snapshot schema versions in one Backend-owned rules package.
15. Golden calculations, null/zero cases, legacy compatibility, migration, API, security, and regression evidence required by `PD-029`.

Not part of Wave 1 implementation:

- Day completion/status UI and workflows are Wave 2.
- Pattern analysis, priorities, weekly goals, and Analysis Snapshots are Wave 3.
- Progress measurements, milestones, and four-week review execution are Wave 4.
- Direct gram/ml Diary logging remains explicitly deferred.

## 6. Capability Versus Required Delta

| Capability | Current baseline | Wave 1 delta |
|---|---|---|
| Energy calculation | Mifflin, activity, fixed goal factors | Cut-intensity selection, cap, block/caution bands, structured outputs |
| Protein | Configurable `protein_per_kg`, default 1.2 | BMI-aware calculation weight, basis disclosure, plan persistence |
| Fat/carbs | Sex-aware defaults and remainder calculation | Low-carb warnings and reject non-positive allocation; remove clamp |
| Targets | Current derived response and preview | Immutable current/history/proposed Target Plans and activation |
| Nutrients | Six duplicated definitions; 12 exact stored fields | Complete 16-key registry, all approved targets/types, exact DFE/RAE semantics |
| Food organization | Free-text `category` | Freeze primary-category representation and add kind/status |
| Food groups | None | Registry, quantitative contributions, traits, validation, coverage |
| Source reliability | Free-text `data_source` only | Controlled source type and Backend-derived reliability |
| Ingredients/NOVA | None | Ingredients text/source, NOVA 1-4/unknown, reviewed classification |
| Completeness/coverage | Partial UI and six-field logic | Complete registry semantics and all-unknown unavailable behavior |
| Diary snapshots | Immutable flat v1 JSON | Versioned v2 writer/reader plus v1 compatibility |
| Ownership | Shared token; globally queried rows | Authenticated subject and owner checks on every operation |
| Rules | Python/TypeScript duplication, no versions | Backend-owned package and independent persisted versions |
| Migration discipline | Committed 0001-0003; `create_all` startup | Approved expand/migrate/contract plan and Alembic authority |

## 7. Exact Schema Delta To Freeze

The following semantic delta is required. Physical names and types that the register does not specify must be approved before implementation rather than invented during coding.

### 7.1 Ownership

- Add a Backend-derived owner identity to Profile, Food, Diary Entry, Target Plan, food-group contributions, traits, and all later user-created expansion records.
- Add owner-scoped indexes and uniqueness constraints.
- Do not accept an authoritative `user_id` from the frontend.
- **Open schema decision:** authenticated subject type/source and safe backfill for current single-profile rows. This blocks the migration freeze.

### 7.2 Profile and Target Plans

- Persist selected cut intensity so it can survive preview/save and be copied into an immutable plan.
- Add an immutable Target Plan entity containing:
  - owner/profile reference;
  - effective start/end or active-range representation;
  - complete calculation inputs;
  - calorie and macro outputs;
  - approved additional-nutrient targets;
  - goal and cut intensity;
  - protein calculation basis and calculation weight;
  - custom settings;
  - independent calculation/registry/rules versions;
  - creation/approval metadata.
- Prevent in-place mutation of historical plans.
- **Open schema decision:** exact activation/effective-range constraints and whether the selected cut intensity also remains on Profile.

### 7.3 Food nutrients

Existing exact `PD-009` fields: `fiber_g`, `added_sugar_g`, `saturated_fat_g`, `trans_fat_g`, `sodium_mg`, `potassium_mg`, `cholesterol_mg`, `calcium_mg`, `iron_mg`, `magnesium_mg`, `zinc_mg`, and `vitamin_b12_mcg`.

Required new nullable exact-semantic fields:

- `selenium_mcg`
- `iodine_mcg`
- `folate_dfe_mcg`
- `vitamin_a_rae_mcg`

Current `folate_mcg` and `vitamin_a_mcg` are compatibility fields. They must not be silently relabeled or copied into DFE/RAE fields without proven source semantics.

### 7.4 Food classification and provenance

- Add controlled Food kind: `simple` or `composite`.
- Add group-data status: `known`, `estimated`, or `unknown`.
- Add controlled source type and derive reliability in Backend rules.
- Add ingredients text and ingredients source.
- Add NOVA: `1`, `2`, `3`, `4`, or `unknown`.
- Decide whether current free-text `category` is retained as the approved primary category or is migrated to a controlled representation; the register does not define a category-key registry.

### 7.5 Food-group contributions and traits

The minimum relational design consistent with the required validations is:

- A Food group-contribution child entity with Food, group key, amount per Food basis, and provenance/status where required.
- Unique Food plus group-key constraint.
- Non-negative amount constraint.
- Backend transaction validation that non-overlapping contribution totals do not exceed 100 per basis.
- A Food analytical-trait association with a unique Food plus trait-key constraint.

The normalized design is a recommendation, not yet an approved physical freeze. A JSON alternative would need equivalent uniqueness, query, constraint, migration, and versioning proof.

### 7.6 Diary Snapshot v2

- The existing JSONB snapshot can carry v2 without duplicating every snapshot value into columns.
- Snapshot v2 must contain all fields required by `PD-014`, including its schema and rule versions.
- Preserve Snapshot v1 unchanged and readable.
- Add an owner to Diary Entry.
- Persist or embed the active Target Plan identity/version required to bind historical targets; exact placement must be frozen.
- No historical v1 snapshot rewrite and no unknown-to-zero backfill.

### 7.7 Registry persistence

- A database registry table is not required by the register if versioned Backend code/config provides the authoritative contract.
- Rule versions that produced Target Plans and snapshots must be persisted on those records.
- Analysis version persistence is required when Analysis Snapshots arrive in Wave 3, not as a Wave 1 analysis table.

## 8. Exact Migration Delta

Do not edit or squash `0001`, `0002`, or `0003`.

The Wave 1 migration sequence must be additive and may be split into reviewable revisions:

1. **Expand ownership and Profile/Target Plan structure** after the authenticated-subject decision is approved.
2. **Expand Food** with exact nullable nutrients, classification, source, ingredients, and NOVA fields.
3. **Create contribution and trait structures** with indexes and uniqueness constraints.
4. **Deploy compatible readers** for legacy Foods, Snapshot v1, and Snapshot v2.
5. **Enable the v2 writer and plan activation** only after compatible code is deployed.
6. **Contract later**, only after compatibility evidence; do not remove legacy `folate_mcg`, `vitamin_a_mcg`, `category`, `data_source`, or Snapshot v1 support in the initial Wave 1 migration.

Migration rules:

- Preserve all new nutrition/classification/provenance fields as null/unknown for legacy records.
- Do not infer food groups, source type, reliability, ingredients, NOVA, DFE, or RAE.
- Do not create historical Target Plans before the first explicit activation.
- Do not rewrite historical snapshots from the current Food row.
- Document downgrade behavior and the compatibility window.
- Rehearse fresh upgrade, populated upgrade, rollback-compatible application behavior, and re-upgrade on disposable PostgreSQL with realistic copied data.
- Make Alembic the authoritative deployment path; document or remove the production role of startup `create_all` before migration approval.

The migration is **not ready to author** because ownership backfill, Target Plan activation constraints, Food category representation, and contribution persistence are not yet approved.

## 9. Exact API Delta

Existing routes remain baseline assets and must be extended additively.

### Wave 1 capabilities required

1. **Nutrition Registry contract**
   - Complete nutrient definitions, food groups, traits, target rules, Arabic display metadata where approved, and independent rule versions.
   - Frontend consumes this contract instead of owning a duplicate editable registry.

2. **Profile preview/save**
   - Accept approved cut intensity.
   - Return deficit cap/caution/block outcomes, calculation-weight basis, adjusted weight where applicable, all nutrient targets, warnings, and applicable versions.
   - Preview and save must produce identical calculations for identical input.
   - Reject non-positive carbohydrate allocation with a stable structured error.

3. **Target Plans**
   - Preview/proposed, current, history, and explicit activation/confirmation capabilities.
   - Idempotency for activation and duplicate mutations.
   - Never mutate historical plans.

4. **Food create/read/update**
   - Add exact nutrient, kind, group status, source type, derived reliability, ingredients, NOVA, contribution, and trait fields.
   - Keep current Food consumers working.
   - Backend validates contributions and derives reliability.

5. **Diary create/read/update**
   - Frontend continues sending Food/date/meal/quantity inputs only.
   - Backend creates Snapshot v2 and scales known values while preserving null.
   - Readers discriminate v1/v2 and expose nullable data without false zero.
   - Meal movement preserves the existing snapshot.

6. **Ownership and errors**
   - All access is owner-scoped from session identity.
   - Unauthorized and nonexistent records must not leak distinguishable existence details.
   - Stable machine-readable error codes with Arabic UI mapping.

### Not Wave 1 API work

- Day completion/status mutation is Wave 2.
- Analysis, contributors, Analysis Snapshots, and weekly goals are Wave 3.
- Measurements, milestones, and four-week review interaction are Wave 4.
- Direct gram/ml logging remains deferred.

Exact paths, payload schemas, error-code catalog, pagination, and idempotency-key behavior are not frozen by the register. They must be approved in an API contract before implementation.

## 10. Registry And Versioning Delta

Create one Backend-owned/versioned rules package containing at least:

- `nutrients`
- `food_groups`
- `macro_policy`
- `deficit_policy`
- `analysis_policy`
- `source_reliability`
- `nova_definitions`
- `versioning`

The nutrient registry must include all 16 exact keys, seven approved target types, target-source semantics, units, precision, ordering, completeness/coverage participation, and all fixed/sex/age/calorie-derived target rules.

The food-group registry must encode the approved keys, serving equivalents, daily/weekly/monitor/minimize rules, caps, exclusions, and traits without using the primary category as analysis truth.

Track independently:

- `nutrition_registry_version`
- `calculation_engine_version`
- `food_group_rules_version`
- `analysis_rules_version`
- `snapshot_schema_version`

Frontend labels and behavior may be cached as response data for rendering, but must not remain an independently editable authority.

Open contract decisions before freeze:

- controlled source-type-to-reliability mapping and reliability levels;
- exact machine representation of less-than limits for sodium and trans fat;
- grain-equivalent and dairy-subtype representation;
- exact category representation;
- Target Plan activation/idempotency contract;
- ownership subject/provider and migration backfill;
- physical persistence of contributions and traits;
- which version owns source-reliability and NOVA changes when independent versions are bumped.

## 11. Existing Regression Suites To Preserve

### Backend

- Calculation/Mifflin/activity/goal/default/custom behavior.
- Profile preview/save validation.
- Food schema, service, API, duplicate, pagination, import, and hard-delete behavior.
- Diary create/edit/move/delete and snapshot/hard-delete history.
- Current nutrition-quality and null/zero tests.
- Alembic chain and PostgreSQL rehearsal.

### Frontend

- Profile functional/visual/preview/save/dirty-state coverage.
- Diary functional, visual, meal, snapshot, nutrition-detail, and RTL coverage.
- Add Food search/configuration/quantity/error/accessibility coverage.
- Full Foods baseline, including details and serving calculations.
- Online-only/no-sync/no-IndexedDB assertions.

### Quality gates

- Backend pytest and Ruff.
- Frontend TypeScript typecheck and production build.
- Available frontend lint gate or explicit documented absence.
- Full relevant Playwright projects.
- Fresh and populated PostgreSQL migration rehearsal.
- `git diff --check`.

## 12. New Requirement-Level Tests

### Calculations and Target Plans

- Cut 15/20/25, default 20, 750 kcal cap, under-800 block, and 800-1200 caution.
- BMI boundary below/at 30 and the exact adjusted-weight formula.
- Existing custom protein/fat preservation and sex-aware default transitions.
- Carb warnings below 130 and 100; zero/negative rejection in preview and save.
- Preview/save golden equality, rounding, stable error codes, and stale preview handling.
- Immutable plan activation, effective ranges, current/history, idempotency, and historical-day plan binding.

### Nutrient registry

- All 16 keys, exact units/semantics, seven target types, ordering, and versions.
- Every fixed, sex, age, and calorie-derived target boundary.
- Less-than limit semantics.
- Known zero versus null through model, API, snapshot, coverage, and UI.
- Frontend consumption of the Backend contract and absence of duplicate authority.

### Food classification, source, and NOVA

- Simple/composite, group status, controlled source type, derived reliability, ingredients, NOVA, and user-reviewed suggestions.
- Contribution non-negative, uniqueness, total at/below/above 100, partial totals, and unknown coverage.
- Trait uniqueness and no duplicate serving contribution.
- All food-group serving rules, exclusions, caps, weekly accumulation, and classification coverage.
- No automatic historical guessing during migration.

### Snapshot v2 and compatibility

- v2 captures every required field and all independent versions.
- v1 remains readable and is never backfilled from current Food.
- Quantity edit scales known values and preserves null.
- Meal movement preserves the same snapshot.
- Food edit/delete cannot mutate history.
- All-unknown is unavailable; partial known totals are marked as minimum confirmed amounts.

### Ownership and security

- Every list/detail/create/update/delete is owner-scoped.
- Cross-owner IDs are denied without existence leakage.
- Frontend user ID is ignored/rejected as authority.
- Normal requests do not require Service Role.
- Snapshot survives owner-authorized Food deletion.

### Migration and contracts

- Fresh, realistic populated, rollback-compatible, and re-upgrade scenarios.
- Legacy null preservation, no inferred classifications, v1/v2 coexistence, and no invented historical plans.
- Additive old-client/new-server and new-client/compatible-server contract tests.
- Duplicate mutation/idempotency and stable error payload tests.

### State, responsive, and accessibility matrices

- Loading, empty, partial, all-unknown, legacy, error/retry, keyboard, RTL, and 320/360/390/430 layouts.
- Truthful progress semantics and no blank alert regions.
- These Wave 2 UI tests may be implemented with the Wave 2 surface, but their data contracts must be fixed in Wave 1.

## 13. Previous Issue Reassessment

| Previous issue | State | Recheck conclusion |
|---|---|---|
| C01 - Baseline reproducibility | Resolved | Baseline and migrations 0001-0003 are committed on `main` |
| C02 - Governing register unavailable/incomplete | Resolved | Complete register is committed and contains PD-000 through PD-029 |
| H01 - Duplicate nutrient registries | Still open | Python and TypeScript remain independent six-item authorities |
| H02 - All-unknown Diary nutrients displayed as zero | Reclassified and still open | Backend null handling is partial; current Wave 2 rendering violates PD-013 and must not define the Wave 1 contract |
| H03 - Silent `carb_clamped` behavior | Still open | PD-007 explicitly requires structured rejection |
| H04 - Incomplete requirement-level coverage | Reclassified and still open | Missing coverage now spans the complete Wave 1 register, not six nutrients |
| H05 - Migration-chain reproducibility | Resolved for baseline; new work open | 0001-0003 are committed; the Wave 1 expand/migrate/contract package is not designed or approved |

## 14. Remaining Critical Issues

### C01 - Authenticated ownership cannot be safely migrated

The current guard validates a shared token but produces no user subject, and current tables are globally queried. `PD-023` requires all user-created records to be owner-bound. The identity source, subject type, uniqueness rules, and existing-row backfill are not approved.

**Closure:** approved authentication/ownership ADR, owner-scoped schema and API contract, migration/backfill plan, and cross-owner security tests.

### C02 - The formal Wave 1 freeze package does not exist

The complete register supplies product decisions, but the exact physical schema, API payloads/errors, migration/rollback, user stories, acceptance criteria, state matrices, and golden calculations required by `PD-029` are not approved.

**Closure:** approved linked artifacts with Critical 0 and High 0 on an exact HEAD.

## 15. Remaining High Issues

| ID | High issue | Closure evidence |
|---|---|---|
| H01 | Cut intensity, 750 kcal cap, and 800/1200 safety outcomes are absent | Golden Backend tests plus preview/save contract |
| H02 | BMI-aware adjusted protein calculation and basis disclosure are absent | Boundary/golden tests and persisted plan basis |
| H03 | Zero/negative carbs are silently clamped | Stable rejection in preview/save and UI mapping |
| H04 | Immutable Target Plan schema, activation, history, and effective-range rules are not frozen | Approved schema/API/migration and lifecycle tests |
| H05 | Nutrient registry is incomplete, duplicated, and lacks four exact semantic fields | One 16-key Backend contract, migration, and target tests |
| H06 | Food-group registry, contributions, traits, and validation do not exist | Approved storage/contract plus complete group golden tests |
| H07 | Controlled source reliability, ingredients, and NOVA do not exist | Mapping/contract/migration and review-flow tests |
| H08 | Snapshot v2/version compatibility and Target Plan binding do not exist | Compatible reader/writer, version fields, and history tests |
| H09 | Wave 1 migration/rollback is unfrozen and runtime `create_all` weakens Alembic authority | Approved rehearsal on disposable PostgreSQL and deployment policy |
| H10 | Independent rule versions and Backend-owned rules package do not exist | Persisted versions and reproducibility tests |
| H11 | All-unknown nutrient UI currently presents false zero | Null-aware aggregate/render tests and no target status when unknown |

## 16. Medium And Low Issues

### Medium

1. Historical architecture and system-plan documents still describe offline/Dexie/sync and other superseded behavior.
2. Current Wave 2 nutrition UI was built around a provisional six-item registry and will need compatible expansion after the Wave 1 contract freezes.
3. Exact Profile field ranges and final Arabic error/caution copy not changed by the register remain governed by the baseline; any proposed changes require a separate decision rather than inference.
4. Current Food `category`, `data_source`, `folate_mcg`, and `vitamin_a_mcg` semantics need explicit compatibility mapping, not silent reinterpretation.
5. Physical-device verification remains pending for real iPhone Safari and Android Chrome; browser emulation is not equivalent.
6. No explicit frontend lint script is evident as an independent quality gate.

### Low

1. `frontend/debug-diary.png` is an unrelated untracked artifact and should remain outside any future scoped change.
2. Historical implementation reports overstate registry centralization and unknown-value handling and should not be used as acceptance evidence.

## 17. Contradictions And Superseded Assumptions

| Historical/code assumption | Complete governing decision | Reconciliation |
|---|---|---|
| Wave 1 is six nutrients | `PD-009` defines 16 nutrients plus complete targets | Superseded |
| Fiber is the only approved numeric target | `PD-009` approves fixed, sex, age, and calorie-derived targets | Superseded |
| No Wave 1 migration is needed | Ownership, exact nutrients, Target Plans, classification, NOVA, and versions require schema work | Superseded |
| Actual weight is always the protein basis | `PD-006` requires adjusted weight at BMI >= 30 | Code contradiction |
| Negative carbs can clamp to zero | `PD-007` requires rejection | Code contradiction |
| A shared bearer token is sufficient ownership | `PD-023` requires session-derived owner scoping | Code contradiction |
| Free-text data source is source reliability | `PD-013` separates selected source type from derived reliability | Partial/contradictory |
| Generic folate/vitamin A units can serve DFE/RAE | `PD-009` requires exact DFE and RAE semantics | Unsafe assumption; no silent mapping |
| Offline-first/Dexie/sync is product direction | `PD-000` preserves online-only baseline | Superseded |
| Meal type and micronutrients are deferred | They are already baseline and registry foundation is Wave 1 | Superseded |
| Direct gram/ml Diary logging is required now | Explicit deferred scope keeps serving-only logging | Superseded/deferred |
| Day status belongs in Wave 1 UI | `PD-015` is Wave 2 | Deferred |
| Four-week review execution belongs in Wave 1 | Target Plan foundation is Wave 1; review interaction is Wave 4 | Reclassified |

## 18. Verification Evidence

### Executed during this recheck

- Register integrity: exactly 30 unique decisions, `PD-000` through `PD-029`; passed.
- Branch/HEAD/remote equality: passed.
- Backend: `python -m pytest -q` -> **42 passed, 1 skipped**; one third-party warning.
- Backend lint: `python -m ruff check .` -> passed.
- Frontend typecheck: `npm run typecheck` -> passed.

### Preserved checkpoint evidence, not rerun in this report-only audit

- Latest repository Playwright result artifact: **245 passed, 0 failed**.
- Frontend production build: passed at the verified implementation checkpoint.
- PostgreSQL migration rehearsal for committed baseline migrations: documented as passed.

This report does not convert preserved evidence into proof for the unimplemented Wave 1 delta. Every gate must be rerun on the exact future implementation head and against disposable PostgreSQL.

## 19. Closure Sequence

1. Approve the authenticated-subject and owner migration model.
2. Freeze the Backend rules registry, source-reliability mapping, independent versions, and exact target/error semantics.
3. Freeze Target Plan and Food contribution physical schemas.
4. Freeze additive API/OpenAPI contracts, idempotency, and old/new compatibility.
5. Produce Wave 1 user stories, acceptance criteria, golden calculations, and state matrix tied to PD IDs.
6. Approve expand/migrate/contract and rollback plans, including Alembic authority.
7. Reconcile Critical and High findings to zero.
8. Only then mark Wave 1 `Ready to Build` and begin implementation.

## 20. Final Recommendation

Do not begin broad Wave 1 implementation from the current documents alone. The baseline is stable enough to extend, so a greenfield rewrite is also inappropriate.

The next work should be a **contract-freeze package**, not product code: ownership/auth ADR, rules registry, exact schemas, Target Plan lifecycle, additive APIs, migration/rollback plan, golden calculations, requirement-level stories, acceptance criteria, and verification matrix. Re-run readiness after those artifacts are approved.

**Final state: Not Ready to Build Wave 1.**
