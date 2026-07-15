# Complete Product Decision Reconciliation

## 1. Audit Record

| Item | Verified value |
|---|---|
| Audited branch | `main` |
| Audited HEAD | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` |
| HEAD subject | `docs: complete nutrition quality decision register v1.1` |
| Baseline merge | `3ecd460 Merge PR #1: checkpoint online-only Foods and Diary experience` |
| Baseline implementation | `d6caf0a feat(v1): checkpoint online-only foods and diary experience` |
| Governing register | `PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md` |
| Formal decisions found | 30 unique IDs: `PD-000` through `PD-029` |
| Missing or duplicate IDs | None |
| Audit date | 2026-07-15 |

The register at current HEAD explicitly supersedes the incomplete earlier copy. The previous provisional versions of documents 07 and 08 are discarded and are not evidence for this reconciliation.

The working tree had no tracked implementation changes at audit start. The prior draft reports and `frontend/debug-diary.png` were untracked. The debug image remains unrelated and untouched.

## 2. Evidence And Classification Method

Product intent is taken from the complete register. Implementation status is based on current models, migrations, schemas, routes, services, UI, and executable tests. Historical reports are corroborating evidence only.

| Classification | Meaning |
|---|---|
| Implemented and verified | Present on current `main` with code/migration and test evidence |
| Implemented but uncommitted | Present only in tracked local changes; none found |
| Partially implemented | A material subset exists but the complete decision is not satisfied |
| New required delta | The capability does not exist sufficiently in the baseline |
| Superseded historical requirement | The complete register explicitly replaces the old requirement |
| Deferred | Approved for a later wave or explicitly outside this expansion |
| No change required | A governing rule is already in force and needs no current product change |

## 3. Decision-By-Decision Reconciliation

### PD-000 - Implemented baseline and expansion boundary

- **Exact governing requirement:** "preserve the implemented baseline"; no greenfield rewrite, offline personal-data store, multiple profiles, silent history reinterpretation, or reintroduced archive/inactive lifecycle.
- **Current implementation evidence:** `main` contains FastAPI, Next.js, PostgreSQL/Alembic, Foods, Diary, Profile, Add Food, online-only behavior, per-100 Food source values, meal types, hard delete, snapshots, and regression suites.
- **Classification:** Implemented and verified.
- **Exact remaining delta:** Preserve these contracts while adding the expansion. Do not restore dead sync behavior or direct gram/ml logging.
- **Schema impact:** None for the decision itself.
- **Migration impact:** Existing `0001 -> 0002 -> 0003` is the baseline chain and must not be recreated.
- **API impact:** Existing CRUD and serving-only Diary contracts remain compatibility assets.
- **Test impact:** All current Foods, Diary, Add Food, Profile, snapshot, online-only, RTL, and accessibility regressions remain mandatory.
- **Severity:** None.
- **Closure evidence:** Current baseline commit remains reproducible and its Backend suite passes `42 passed, 1 skipped` at audited HEAD.

### PD-001 - Document authority and change control

- **Exact governing requirement:** the complete register is the single product authority; Ready to Build requires Critical 0 and High 0.
- **Current implementation evidence:** the complete 30-decision register is committed at current HEAD.
- **Classification:** No change required.
- **Exact remaining delta:** Apply formal change control and PD-029; do not treat earlier BA/QA reports as higher authority.
- **Schema impact:** None.
- **Migration impact:** None.
- **API impact:** None.
- **Test impact:** Gate evidence must be tied to the exact implementation HEAD.
- **Severity:** Governance gate.
- **Closure evidence:** A future readiness report records zero open Critical/High findings and approved contracts.

### PD-002 - Product definition and boundaries

- **Exact governing requirement:** truth before false precision, null is not zero, Backend rules are authoritative, history is versioned, and completeness is not nutrition quality.
- **Current implementation evidence:** Backend owns current target and snapshot calculations; UI is Arabic-first; no unified Health Score exists. Food Details separates completeness copy from health claims.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Correct the all-unknown Diary presentation, add versioned plans/snapshots/rules, and formalize source reliability without combining it with completeness.
- **Schema impact:** Indirect through Target Plans, Snapshot v2, Food source/classification, and ownership.
- **Migration impact:** Preserve nulls and legacy history.
- **API impact:** Null-aware and versioned responses; no client-authoritative calculations.
- **Test impact:** Null versus known-zero, no false precision, and historical non-reinterpretation scenarios.
- **Severity:** High.
- **Closure evidence:** Formal contracts and tests prove all-unknown values remain unavailable and historical outputs retain their original versions.

### PD-003 - Navigation and information architecture

- **Exact governing requirement:** four main tabs: Diary, Foods, Progress, Profile; approved Progress detail routes; 320px usability.
- **Current implementation evidence:** `frontend/components/AppNav.tsx` exposes Diary, Foods, and Profile only. No `/progress` route exists.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Preserve the three current tabs in Waves 1-2; add Progress and its detail routes in Waves 3-4. Do not redesign global navigation during Wave 1 foundation work.
- **Schema impact:** None in Wave 1.
- **Migration impact:** None in Wave 1.
- **API impact:** Later Progress APIs only.
- **Test impact:** Later four-tab 320px and route tests.
- **Severity:** Deferred for Wave 1.
- **Closure evidence:** Wave 4 navigation acceptance proves all four tabs and routes without horizontal overflow.

### PD-004 - Expansion waves and scope sequencing

- **Exact governing requirement:** Wave 1 is Nutrition & Data Foundation; Wave 2 is Foods/Diary UI; Wave 3 is analysis; Wave 4 is health progress; later waves must not be implemented early without a dependency.
- **Current implementation evidence:** the brownfield baseline already contains some Wave 2 UI, including meal macros, six-nutrient details, and completeness.
- **Classification:** No change required.
- **Exact remaining delta:** Grandfather the approved baseline under PD-000, but scope all new work by the complete wave list. Day status is Wave 2, not a Wave 1 migration requirement.
- **Schema impact:** Defined by active Wave 1 decisions only.
- **Migration impact:** Do not add later-wave tables in the Wave 1 migration.
- **API impact:** Freeze only Wave 1 contracts now.
- **Test impact:** Separate active-wave gates from later-wave tests.
- **Severity:** Governance gate.
- **Closure evidence:** Every implementation item carries PRESERVE/MODIFY/ADD/DEFER/REMOVE and a wave assignment.

### PD-005 - Energy and cut-deficit policy

- **Exact governing requirement:** server-side Mifflin-St Jeor; 15%, 20%, or 25% cut; automatic deficit cap 750 kcal/day; block below 800 kcal/day; strong caution at 800-1200 kcal/day.
- **Current implementation evidence:** `backend/app/services/calc.py` uses Mifflin-St Jeor and `Goal.cut: 0.8`; there is no cut-intensity input, 750 cap, or 800/1200 safety state.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Add selected cut intensity, cap logic, preview metadata, blocked/caution results, and safe Arabic presentation while preserving current activity factors.
- **Schema impact:** Add cut intensity to persisted Profile/Target Plan state; Target Plans store the resolved deficit and outputs.
- **Migration impact:** Existing cut users must retain equivalent 20% behavior without overwriting custom macro settings.
- **API impact:** Extend Profile preview/save with cut intensity, safety status, warnings, and stable error codes.
- **Test impact:** Golden 15/20/25, 750-cap, 799/800/1200 boundaries, preview/save equality, and unchanged activity factors.
- **Severity:** High safety gap.
- **Closure evidence:** Server golden tests and UI/API acceptance prove unsafe output cannot be saved.

### PD-006 - Protein calculation weight basis

- **Exact governing requirement:** default 1.2 g/kg; actual weight below BMI 30; adjusted weight at BMI 30 or above using the approved formula.
- **Current implementation evidence:** default is 1.2, but `calc.py` always multiplies `weight_kg`; the current 115 kg female test expects 138 g from actual weight.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Implement BMI boundary, reference weight, adjusted calculation weight, custom factor preservation, and explanatory response/UI metadata.
- **Schema impact:** No new body fields; Target Plan stores calculation-weight value and basis.
- **Migration impact:** No historical target backfill; first plan uses the new rule at activation.
- **API impact:** Preview/save return actual/adjusted basis and calculation weight from Backend.
- **Test impact:** BMI 29.99/30 boundaries, approved formula, both sexes, custom factors, and replacement of the obsolete 115 kg expectation.
- **Severity:** High target-accuracy gap.
- **Closure evidence:** Golden scenarios match the approved formula and TypeScript contains no duplicate calculation.

### PD-007 - Fat and carbohydrate allocation

- **Exact governing requirement:** sex-aware 25%/30% fat defaults; custom preservation; remaining-calorie carbs; warnings below 130/100 g; zero/negative carbs are invalid, never silently clamped.
- **Current implementation evidence:** Profile implements sex-aware defaults and custom preservation. `calc.py` sets `carb_clamped` and returns `max(carb_cal, 0) / 4` as a successful target.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Add warning levels and a structured server error for invalid allocation in preview and save. Retain `carb_clamped` only as temporary compatibility metadata, not success.
- **Schema impact:** Target Plan stores resolved fat settings and valid outputs; no separate carb input.
- **Migration impact:** Preserve existing custom fat percentages.
- **API impact:** Stable invalid-allocation code plus warning metadata.
- **Test impact:** <130, <100, zero, negative, sex-change default-control, restore-default, and preview/save parity.
- **Severity:** High safety and correctness gap.
- **Closure evidence:** No request can persist a zero/negative allocation as an ordinary successful plan.

### PD-008 - Target recalculation and historical Target Plans

- **Exact governing requirement:** immutable Target Plan Versions with effective ranges, inputs, outputs, additional targets, cut intensity, calculation weight, settings, and versions; historical days use the plan active then.
- **Current implementation evidence:** Profile preview/save calculates only the current Profile on demand. There is no Target Plan model, history, approval, or effective-date resolution.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Wave 1 adds immutable plan storage and preview/current/history/activation contracts. The four-week measurement-driven review UI executes in Wave 4.
- **Schema impact:** New owner-bound `target_plan_version` table and active/effective constraints.
- **Migration impact:** First plan starts at activation; prior plans are not invented.
- **API impact:** Add preview metadata, current/history reads, and idempotent user-confirmed activation.
- **Test impact:** Immutability, effective ordering, no fabricated history, activation idempotency, current-vs-proposed, and historical date resolution.
- **Severity:** High data-history gap.
- **Closure evidence:** A historical day resolves the original immutable plan after later Profile changes.

### PD-009 - Additional nutrient registry

- **Exact governing requirement:** 16 exact nullable nutrient keys, seven target types, all listed fixed/sex/age/calorie-derived targets, known zero valid, unknown null.
- **Current implementation evidence:** Food has exact columns for 12 keys. It lacks `selenium_mcg`, `folate_dfe_mcg`, `vitamin_a_rae_mcg`, and `iodine_mcg`; legacy `folate_mcg` and `vitamin_a_mcg` do not prove DFE/RAE semantics. Backend and frontend duplicate a six-item registry with four target types and only fiber numeric.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Create one Backend-owned complete registry; add the four exact nullable fields; implement every approved target and comparator; retain deferred nutrients without targets.
- **Schema impact:** Add nullable selenium, iodine, folate DFE, and vitamin A RAE fields. Preserve legacy generic fields during compatibility.
- **Migration impact:** Do not copy generic folate/vitamin A values into DFE/RAE without proven source semantics; never backfill unknown as zero.
- **API impact:** Add authoritative versioned registry metadata and the exact fields to additive Food/Diary/Target Plan contracts.
- **Test impact:** All 16 keys, seven target types, age/sex boundaries, calorie-derived limits, exclusive-limit semantics, known zero/null, and deferred-target absence.
- **Severity:** High foundation gap.
- **Closure evidence:** One registry contract drives Backend and frontend; the obsolete six-item/fiber-only test is removed by replacement acceptance coverage.

### PD-010 - Food-group registry and serving rules

- **Exact governing requirement:** the listed 18 groups plus operational serving rules, daily/weekly targets, caps, monitor/minimize behavior, and coverage.
- **Current implementation evidence:** no Backend food-group registry, serving rules, group targets, or group aggregation exists.
- **Classification:** New required delta.
- **Exact remaining delta:** Add a versioned Backend registry for all groups, traits, conversions, cadence, caps, and target semantics.
- **Schema impact:** Registry may remain versioned code/config; Food quantitative contributions require persistent child data under PD-011.
- **Migration impact:** No automatic group classification of existing Foods.
- **API impact:** Registry response and additive Food contribution fields.
- **Test impact:** Each serving conversion, juice cap, roots exclusion, whole-grain coverage, dairy qualification, red-meat bands, and monitor/minimize behavior.
- **Severity:** High foundation gap.
- **Closure evidence:** Golden group scenarios produce deterministic results from stored contributions without category inference.

### PD-011 - Food classification and quantitative group contributions

- **Exact governing requirement:** primary category, simple/composite kind, multiple quantitative contributions per 100 basis, traits, known/estimated/unknown status, uniqueness, nonnegative values, and non-overlapping total <=100.
- **Current implementation evidence:** Food has a free-text `category` and per-100 basis only. There is no kind, contribution, trait, or group-data status.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Add approved category keys, kind, status, normalized contributions, traits, and service validation. Category must remain organizational.
- **Schema impact:** Add nullable primary-category key, Food kind, group-data status, owner-bound contribution rows with unique `(food_id, group_key)`, and owner-bound trait rows.
- **Migration impact:** Preserve free-text category for compatibility; do not infer new classification from it.
- **API impact:** Add contribution/trait request and response shapes with server validation.
- **Test impact:** Duplicate key, negative amount, <=100 boundary, partial totals, traits not counted, composite manual entry, and category non-analysis.
- **Severity:** High foundation gap.
- **Closure evidence:** A composite Food persists validated contributions and analysis inputs independently of category.

### PD-012 - NOVA and ingredients

- **Exact governing requirement:** reviewed NOVA 1/2/3/4/unknown, ingredients text/source, no macro-only inference, and no fabricated safe threshold.
- **Current implementation evidence:** Food has notes and a generic `data_source`; no ingredients or NOVA fields/contracts exist.
- **Classification:** New required delta.
- **Exact remaining delta:** Add nullable ingredients metadata and reviewed NOVA classification using Backend definitions.
- **Schema impact:** Add `ingredients_text`, `ingredients_source`, and nullable/reviewed `nova_class`.
- **Migration impact:** Existing rows remain unknown; no guessing.
- **API impact:** Additive Food fields and authoritative NOVA definitions in registry metadata.
- **Test impact:** Allowed values, unknown/null compatibility, no macro inference, review requirement, and separation from completeness/reliability.
- **Severity:** High foundation gap.
- **Closure evidence:** Existing Foods remain unknown until reviewed and new values round-trip without affecting nutrient calculations.

### PD-013 - Completeness, source reliability, and Diary coverage

- **Exact governing requirement:** completeness, reliability, and coverage stay separate; known zero is present; all-unknown Diary amount is unavailable; source type is user-selected and reliability Backend-derived.
- **Current implementation evidence:** Food Details computes four core plus six additional fields. `data_source` is free text. Diary coverage initializes amount to zero and renders `0 ... at least` when `known == 0`.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Wave 1 freezes source types/reliability mapping and complete nullable semantics. Wave 2 expands UI completeness/coverage and fixes all-unknown rendering.
- **Schema impact:** Add Food `source_type`; derived reliability is not user-editable. Snapshot v2 stores source/reliability/completeness at logging time.
- **Migration impact:** Do not infer source type from existing text. Keep legacy `data_source` as detail/provenance.
- **API impact:** Return source type, derived reliability, completeness metadata, and nullable aggregates with coverage.
- **Test impact:** 20-field core-plus-approved completeness, zero/null, all-unknown, partial “at least,” reliability mapping, and group coverage sufficiency.
- **Severity:** High foundation contract; open Wave 2 rendering defect.
- **Closure evidence:** Backend contract returns null when no value is known and frontend suppresses target progress/status for that case.

### PD-014 - Diary Snapshot v2

- **Exact governing requirement:** new Backend-created versioned snapshots include identity, core and all approved nullable nutrients, groups, traits, NOVA, source/reliability, completeness, and rule versions; v1 remains readable and immutable.
- **Current implementation evidence:** current flat JSON snapshot preserves identity, current nutrients, nulls, quantity, and totals; edit/move/delete safety is tested. It has no schema version, group, trait, NOVA, reliability, completeness, or rule-version envelope.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Define a v1/v2 discriminated reader and v2 writer. Never enrich old v1 rows from current Food data.
- **Schema impact:** Existing JSONB column can hold v2; optionally add a nullable Target Plan FK only if the approved contract does not embed the plan identity.
- **Migration impact:** No v1 rewrite; deploy compatible readers before v2 writers.
- **API impact:** Return discriminated v1/v2 snapshots while keeping current entry inputs Food/date/meal/quantity only.
- **Test impact:** v1 fixtures, v2 shape, all version fields, null scaling, known zero, meal move, Food edit/delete, and client-authority rejection.
- **Severity:** High historical-integrity gap.
- **Closure evidence:** Old v1 and new v2 entries coexist through upgrade, rollback window, edits, and Food deletion.

### PD-015 - Day logging status

- **Exact governing requirement:** `unregistered`, `partial`, and explicit `complete`; empty complete allowed; incomplete days are not zero.
- **Current implementation evidence:** no day-status model, API, or UI exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 2 adds explicit day status using Wave 1 ownership/version foundations.
- **Schema impact:** Later Wave 2 day-status persistence.
- **Migration impact:** None in Wave 1.
- **API impact:** Later day status read/mutation.
- **Test impact:** Later transitions, empty completion, and non-zero semantics.
- **Severity:** Deferred for Wave 1.
- **Closure evidence:** Wave 2 freeze and acceptance tests.

### PD-016 - Nutrition Pattern Analysis

- **Exact governing requirement:** rolling seven-day analysis, previous-period comparison, four complete days, metric coverage, contributors, and no unified score.
- **Current implementation evidence:** no analysis model, service, API, or Progress route exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 3, built from Wave 1 snapshots/registries and Wave 2 status/coverage.
- **Schema impact:** Later Analysis Snapshot work under PD-019.
- **Migration impact:** None in Wave 1.
- **API impact:** Later analysis/current/contributors.
- **Test impact:** Later sufficiency, coverage, comparison, and missing-day tests.
- **Severity:** Deferred.
- **Closure evidence:** Wave 3 scope freeze.

### PD-017 - Weekly priority engine

- **Exact governing requirement:** deterministic maximum one main and one justified secondary priority, with reason, confidence, coverage, action, version, facts, and conflict resolution.
- **Current implementation evidence:** no recommendation or priority engine exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 3.
- **Schema impact:** Later analysis/priority snapshot data.
- **Migration impact:** None in Wave 1.
- **API impact:** Later analysis priority response.
- **Test impact:** Later deterministic conflict and eligibility scenarios.
- **Severity:** Deferred.
- **Closure evidence:** PD-027 launch gate in Wave 3.

### PD-018 - Weekly behavior goals

- **Exact governing requirement:** optional user-controlled goals, one primary by default, Diary-derived progress, neutral outcomes, and limited reminders.
- **Current implementation evidence:** no weekly-goal entity/API/UI exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 3.
- **Schema impact:** Later owner-bound goal/history tables.
- **Migration impact:** None in Wave 1.
- **API impact:** Later goal lifecycle mutations.
- **Test impact:** Later accept/edit/defer/reject/end and insufficient-data behavior.
- **Severity:** Deferred.
- **Closure evidence:** Wave 3 formal contracts.

### PD-019 - Analysis snapshots and lifecycle

- **Exact governing requirement:** versioned, auditable finalized Analysis Snapshots with stale/recompute revisions using original rules.
- **Current implementation evidence:** no analysis snapshot exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 3.
- **Schema impact:** Later immutable analysis snapshot/revision storage.
- **Migration impact:** None in Wave 1.
- **API impact:** Later current/history/revision reads.
- **Test impact:** Later stale marking, original-version recompute, and audit history.
- **Severity:** Deferred.
- **Closure evidence:** Wave 3 migration/API freeze.

### PD-020 - Progress tab and health measurements

- **Exact governing requirement:** owner-bound weight, waist, blood pressure, activity, trends, and four-week calorie review under approved rules.
- **Current implementation evidence:** no Progress route or health-measurement models/APIs exist.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 4.
- **Schema impact:** Later measurement tables.
- **Migration impact:** None in Wave 1.
- **API impact:** Later Progress domains.
- **Test impact:** Later history/trend/deletion/review tests.
- **Severity:** Deferred.
- **Closure evidence:** Wave 4 scope freeze.

### PD-021 - Health milestones

- **Exact governing requirement:** calm meaningful milestones; no XP, punitive streaks, under-eating rewards, or removal after regression.
- **Current implementation evidence:** no milestone engine exists; current UI does not use gamification.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 4.
- **Schema impact:** Later immutable owner-bound milestone history.
- **Migration impact:** None in Wave 1.
- **API impact:** Later milestone reads.
- **Test impact:** Later positive/forbidden milestone scenarios.
- **Severity:** Deferred.
- **Closure evidence:** Wave 4 behavioral-safety review.

### PD-022 - Behavioral safety and user language

- **Exact governing requirement:** neutral non-punitive language, no under-eating celebration or harsher automatic goals, low-target warnings, simplified view, and planned tracking pause.
- **Current implementation evidence:** current Diary/Profile language is generally neutral and no harsher automatic goal exists. Low-calorie safety, simplified view, and pause capability are absent.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Wave 1 must cover calculation safety/copy; simplified view and pause need explicit later-wave placement before release.
- **Schema impact:** No Wave 1 schema beyond safe Target Plan state; pause may need later preference state.
- **Migration impact:** None immediately.
- **API impact:** Structured low-target warnings/errors and no automatic mutation.
- **Test impact:** Safety copy review, forbidden encouragement, low-target states, and no punitive recommendation behavior.
- **Severity:** High safety gap for active calculations.
- **Closure evidence:** Approved Arabic safety acceptance and golden blocked/caution cases.

### PD-023 - Ownership, privacy, and security

- **Exact governing requirement:** Backend derives authenticated identity; every user-created record is owner-bound; frontend cannot authoritatively send `user_id`; unauthorized existence is not leaked.
- **Current implementation evidence:** routers use a shared bearer token, but `require_single_user` returns no subject. Profile, Food, and Diary have no owner field; services query global rows.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Freeze authenticated subject/provider, ownership schema, existing-row assignment, service filters, non-enumerating errors, and two-owner tests.
- **Schema impact:** Owner identity on Profile, Food, Diary, Target Plans, contributions, and future records.
- **Migration impact:** Existing single-user rows require a safe owner backfill only after the authoritative subject is fixed.
- **API impact:** Identity from session; no client-authoritative owner; every list/read/update/delete scoped.
- **Test impact:** Two-owner isolation, unauthorized non-leakage, spoofed `user_id`, and normal-operation role tests.
- **Severity:** Critical.
- **Closure evidence:** Approved identity contract plus end-to-end ownership proof on realistic PostgreSQL.

### PD-024 - Migration strategy

- **Exact governing requirement:** Expand -> Migrate -> Contract; nullable first; no unknown-to-zero; v1/v2 compatibility; no guessing; realistic disposable PostgreSQL rehearsal and rollback.
- **Current implementation evidence:** `0001 -> 0002 -> 0003` is committed and separately rehearsed. No Wave 1 migration exists. App startup still calls `SQLModel.metadata.create_all`.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Freeze and rehearse the exact Wave 1 expansion after ownership and storage decisions close; ensure Alembic is deployment authority.
- **Schema impact:** All active Wave 1 additions listed in the readiness report.
- **Migration impact:** New additive revision(s), activation step, compatibility window, rollback, and no legacy reinterpretation.
- **API impact:** Old/new clients and v1/v2 readers must overlap safely.
- **Test impact:** Fresh and populated upgrade, rollback/re-upgrade, null/zero invariants, custom Profile values, and legacy snapshots.
- **Severity:** High readiness gap.
- **Closure evidence:** Approved migration plan and successful disposable-PostgreSQL rehearsal from `0001` to new head.

### PD-025 - API and backend source of truth

- **Exact governing requirement:** additive APIs; Backend owns targets, reliability, snapshots, analysis, and priorities; stable errors, nulls, idempotency, and client sends only Diary inputs.
- **Current implementation evidence:** current Profile calculations and Diary snapshots are Backend-owned; Food/Diary create accept optional client IDs for partial idempotency. No registry, Target Plan, source/group/trait, or versioned snapshot capability exists.
- **Classification:** Partially implemented.
- **Exact remaining delta:** Freeze the Wave 1 Registry, Food extensions, Target Plan, Snapshot v2, ownership, and error/idempotency contracts. Defer later capability areas by PD-004.
- **Schema impact:** Indirect through the active Wave 1 entities.
- **Migration impact:** Backward-compatible overlap.
- **API impact:** New registry capability; additive Food fields; expanded Profile preview/save; Target Plan current/history/activation; v1/v2 Diary responses.
- **Test impact:** Contract compatibility, stable error codes, stale preview, duplicate mutation, nulls, and rejection of client nutrient totals.
- **Severity:** High readiness gap.
- **Closure evidence:** Approved OpenAPI examples and old/new compatibility tests tied to exact schemas.

### PD-026 - Rule versioning

- **Exact governing requirement:** independently track nutrition registry, calculation engine, food-group rules, analysis rules, and snapshot schema versions; Backend-owned rules package; no independently editable frontend registry.
- **Current implementation evidence:** no required version constants/fields exist. Nutrient metadata is duplicated in Python and TypeScript.
- **Classification:** New required delta.
- **Exact remaining delta:** Create one Backend rules package and version contract; persist applicable versions on Target Plans and Snapshot v2. Analysis version persistence waits for Wave 3.
- **Schema impact:** Version fields in Target Plans and Snapshot v2; optional umbrella version cannot replace independent versions.
- **Migration impact:** No historical version invention; old Snapshot v1 remains explicitly legacy.
- **API impact:** Registry and target/snapshot responses expose applicable versions.
- **Test impact:** Version presence, independent bumps, old-version reading, frontend contract consumption, and no duplicate authoritative constants.
- **Severity:** High reproducibility gap.
- **Closure evidence:** A saved plan/snapshot can be reproduced from stored independent versions.

### PD-027 - Recommendation validation and launch

- **Exact governing requirement:** every recommendation rule has eligibility, exclusions, coverage, conflicts, Arabic templates, version, golden/null tests, safety review, and shadow mode.
- **Current implementation evidence:** no recommendation engine exists.
- **Classification:** Deferred.
- **Exact remaining delta:** Wave 3.
- **Schema impact:** Later analysis/recommendation records.
- **Migration impact:** None in Wave 1.
- **API impact:** Later analysis priority outputs.
- **Test impact:** Later full launch matrix.
- **Severity:** Deferred.
- **Closure evidence:** Wave 3 shadow-mode and manual-review evidence.

### PD-028 - Product success metrics

- **Exact governing requirement:** measure completed days, coverage, food-pattern changes, goals, understanding, correction, sustainable use, and relevant trends; page views are not primary.
- **Current implementation evidence:** no formal success-metric instrumentation is visible in the current product.
- **Classification:** Deferred.
- **Exact remaining delta:** Define measurement/privacy implementation with the relevant later wave; do not add analytics opportunistically in Wave 1.
- **Schema impact:** None approved for Wave 1.
- **Migration impact:** None in Wave 1.
- **API impact:** None approved for Wave 1.
- **Test impact:** Later metric-definition validation.
- **Severity:** Deferred.
- **Closure evidence:** Approved measurement plan with privacy review.

### PD-029 - Readiness gate and formal scope freeze

- **Exact governing requirement:** all active decisions reconciled; Critical 0; High 0; approved schema, migration, rollback, API, stories, acceptance, golden calculations, states, and regression plan.
- **Current implementation evidence:** complete decision reconciliation now exists, but Critical/High items and formal BA/QA/API/migration freezes remain open.
- **Classification:** No change required.
- **Exact remaining delta:** Close every gate item listed in document 08 and rerun readiness against the exact frozen artifacts.
- **Schema impact:** Gate approval, not a schema field.
- **Migration impact:** Migration/rollback must be approved before Ready to Build.
- **API impact:** Contracts must be approved before Ready to Build.
- **Test impact:** Golden and state matrices must be complete before implementation.
- **Severity:** Blocking governance gate.
- **Closure evidence:** A later recheck reports `Ready to Build`, Critical 0, High 0, and links approved artifacts.

## 4. Previous Issue Reassessment

| Previous issue | Complete-register state | Evidence |
|---|---|---|
| C01 - Baseline reproducibility | Resolved | Baseline and migrations are merged on `main`; current HEAD only replaces the register after that checkpoint |
| C02 - Governing register unavailable/incomplete | Resolved | Current file explicitly supersedes the incomplete prior copy and contains exactly PD-000 through PD-029 |
| H01 - Duplicate nutrient registries | Still open | Python and TypeScript independently encode the six-item provisional registry; PD-009/PD-026 require one Backend contract |
| H02 - All-unknown Diary nutrient shown as zero | Reclassified and still open | Backend nullable semantics are partly correct; current Wave 2 UI still initializes and renders zero when `known == 0` |
| H03 - Silent carbohydrate clamp | Still open | `carb_clamped` still returns successful zero rather than the PD-007 structured rejection |
| H04 - Requirement-level test coverage incomplete | Reclassified and still open | The complete register expands the missing matrix to every active part of PD-005 through PD-014 and PD-022 through PD-026 |
| H05 - `0002`/`0003` absent/unreproducible | Resolved | Both are committed, linear, and have documented PostgreSQL rehearsal evidence |

H05 resolution is limited to the baseline chain. The new Wave 1 migration and rollback design remains open under PD-024.

## 5. Superseded Provisional Conclusions

- The prior 07/08 reports based on the incomplete register are discarded.
- Wave 1 is not a six-nutrient enhancement.
- Fiber is not the only approved numeric target.
- `folate_mcg` and `vitamin_a_mcg` cannot be silently treated as DFE and RAE fields.
- The current six-item registry test is not a requirement to preserve.
- “No Wave 1 migration required” is superseded by exact nutrient semantics, ownership, Target Plans, Food classification/contributions, NOVA/ingredients, and versioning.
- Day logging status remains Wave 2 despite being an approved formal decision.
- Four-week review execution remains Wave 4; Target Plan foundations are Wave 1.
- Direct gram/ml Diary logging remains deferred.
