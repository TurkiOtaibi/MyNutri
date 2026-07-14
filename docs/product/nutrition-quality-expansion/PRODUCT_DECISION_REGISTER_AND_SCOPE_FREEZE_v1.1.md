# myNutri Product Decision Register & Expansion Scope Freeze

**Version:** 1.1  
**Status:** Approved governing source for baseline reconciliation; Wave 1 is not yet frozen or Ready to Build  
**Document type:** Brownfield expansion / delta register  
**Project:** myNutri  
**Target expansion:** Nutrition Quality & Progress  
**Implemented baseline:** Existing operational product; do not rebuild from scratch  
**Current audited main checkpoint:** `3ecd4605790102fd67e64ee09b40faac74fc1e42`  

> myNutri and NutriPlan are separate projects. Their scope, entities, decisions, and requirements must never be mixed.

---

## How to use this register

This is the governing product source for reconciling the existing myNutri implementation with the approved Nutrition Quality & Progress expansion.

The current code, migrations, APIs, and tests are evidence of implementation. This document is the authority for product intent and expansion scope.

When sources conflict, use this precedence:

1. This register.
2. Frozen scope for the active wave.
3. Approved data/API contracts and acceptance criteria.
4. Current implementation evidence.
5. BA/QA reports.
6. Historical Architecture/System Plan documents and prior conversations.

Historical requirements explicitly superseded here must not be reintroduced.

---

# PD-000 — Implemented baseline and expansion boundary

**Status:** Approved

myNutri is an already developed brownfield product with an implemented Frontend, Backend, PostgreSQL database, Alembic migrations, calculation engine, Foods, Diary, Profile, Add Food, and automated regression coverage.

This expansion must preserve the implemented baseline. It does not authorize a greenfield rewrite.

Codex must classify each requirement as one of:

```text
Implemented and verified
Implemented but uncommitted
Partially implemented
New required delta
Superseded historical requirement
Deferred
No change required
```

The expansion must not:

- rebuild stable modules without evidence and an approved reason;
- replace working APIs unnecessarily;
- weaken existing tests;
- alter historical Diary nutrition silently;
- redesign unrelated routes;
- reintroduce offline personal-data storage, Dexie sync, mutation queues, or multiple profiles.

The following historical directions are superseded for this release:

- offline-first personal-data architecture;
- Dexie as a nutrition-data source of truth;
- `/sync` and offline mutation queues;
- multiple tracked profiles;
- serving-only Food source of truth;
- meal type deferred;
- micronutrients excluded from the product;
- archive/inactive Food lifecycle.

`Ready to Build: No` applies only to the named expansion wave, not to the existing product.

---

# PD-001 — Governance and change control

**Status:** Approved

Lifecycle:

```text
Draft → Under Review → Approved → Frozen → Superseded
```

A wave becomes Ready to Build only when:

```text
Critical issues: 0
High unresolved issues: 0
Verdict: Ready to Build
```

After freeze:

- Critical security, privacy, safety, or data-integrity changes may enter immediately.
- High-impact changes require a formal Change Decision.
- Medium/Low ideas move to backlog unless explicitly approved.

No broad implementation starts from chat text alone.

---

# PD-002 — Product definition and boundaries

**Status:** Approved

myNutri is a personal Arabic-first nutrition and health-progress tracker that helps the user understand their eating pattern, targets, and trends and choose practical improvements.

Primary job:

> When I record my food and progress, I want to understand whether my overall pattern is improving and what practical change matters most next.

Principles:

- truth before false precision;
- patterns before isolated days;
- explanation before recommendation;
- improvement without blame;
- Backend rules are authoritative;
- history is not silently reinterpreted;
- no unified Health Score;
- data quality is separate from nutrition quality.

myNutri is not a medical diagnosis/treatment system, clinical nutrition platform, multi-client dietitian product, or substitute for a clinician.

Approved claim direction:

> Supports better food-quality awareness, sustainable habits, and health-related lifestyle improvement.

---

# PD-003 — Navigation and information architecture

**Status:** Approved

Approved main tabs:

```text
اليوميات
الأطعمة
التقدم
الملف
```

## Diary — اليوميات

Contains date navigation, meal sections, entries, calories/macros, additional nutrient details, day status, and a contextual link to Nutrition Pattern Analysis.

## Foods — الأطعمة

Contains Food CRUD, per-100g/per-100ml source data, servings, nutrients, category, group contributions, analytical traits, ingredients, NOVA, source reliability, and nutrition-data completeness.

## Progress — التقدم

Approved routes:

```text
/progress
/progress/nutrition
/progress/weight
/progress/waist
/progress/blood-pressure
/progress/activity
/progress/calorie-review
```

The main Progress page is a compact executive summary, not a dense dashboard.

## Profile — الملف

Contains body data, activity, goal, cut intensity, macro settings, target preview, current targets, additional nutrient targets, and calculation explanation.

The four tabs must remain usable at 320px without horizontal scrolling.

---

# PD-004 — Expansion waves

**Status:** Approved

Every requirement must be tagged:

```text
PRESERVE
MODIFY
ADD
DEFER
REMOVE
```

## Wave 1 — Nutrition & Data Foundation

Includes:

- revised macro and deficit policy;
- central versioned nutrient and food-group registries;
- approved additional nutrient targets;
- source type and derived reliability;
- ingredients and NOVA foundations;
- simple/composite Food model and quantitative food-group contributions;
- nullable nutrient semantics;
- Diary Snapshot v2 foundation;
- Target Plan Versions;
- rule versioning;
- additive data/API contracts;
- migrations only where the current schema does not already support the decision.

## Wave 2 — Foods & Diary Experience

Includes:

- new Foods/Profile/Diary UI for approved fields and targets;
- completeness and source reliability in Food Details;
- additional nutrient Daily Details and coverage;
- meal macros;
- day logging status;
- no false zero rendering.

## Wave 3 — Nutrition Pattern Analysis

Includes:

- rolling seven-day analysis;
- minimum complete-day and coverage rules;
- food-group and nutrient pattern analysis;
- NOVA analysis;
- contributors;
- deterministic weekly priorities;
- optional weekly behavior goals;
- previous-period comparisons;
- Analysis Snapshots and shadow-mode validation.

## Wave 4 — Health Progress

Includes:

- weight history and seven-day average;
- waist circumference;
- blood pressure;
- physical activity;
- four-week calorie-target review;
- calm health milestones.

A later wave does not start until the current wave passes its gate.

---

# PD-005 — Energy and cut-deficit policy

**Status:** Approved

- Preserve Mifflin–St Jeor as the calculation basis.
- Preserve Backend as the only authoritative calculation implementation.
- Cut options:

| Option | Deficit |
|---|---:|
| خفيف | 15% |
| عادي | 20% — default |
| قوي | 25% |

- Automatic deficit is capped at 750 kcal/day.
- Show resulting calories before save.
- Very-low or implausible output must follow Backend safety validation and cannot be silently accepted.
- These options are not promises of an exact weight-loss rate.

---

# PD-006 — Protein calculation weight basis

**Status:** Approved

Default protein factor:

```text
1.2 g/kg of calculation weight
```

When BMI < 30:

```text
calculation_weight = actual_weight
```

When BMI ≥ 30:

```text
reference_weight = 25 × height_m²
adjusted_weight = reference_weight + 0.33 × (actual_weight − reference_weight)
calculation_weight = adjusted_weight
```

The same default factor applies to men and women. The user may customize grams/kg. The UI must explain the weight basis used. Clinical exceptions are deferred.

---

# PD-007 — Fat and carbohydrate allocation

**Status:** Approved

Default fat percentage:

- men: 25% of target calories;
- women: 30% of target calories.

These are myNutri product defaults inside the adult reference range, not a claim that every man or woman physiologically requires that exact value.

Custom fat values are preserved. Sex changes update fat only when the prior value is still default-controlled. Restore Defaults returns to the sex-aware default.

Carbohydrates receive remaining calories:

```text
carb_calories = target_calories − protein_calories − fat_calories
carb_target_g = carb_calories ÷ 4
```

Rules:

- below 130 g: calm reference warning;
- below 100 g: stronger warning;
- zero or negative calculated carbohydrate allocation is invalid;
- preview and save must reject it with a structured `invalid_macro_allocation` error;
- `carb_clamped` may remain temporarily for backward compatibility but must never be silently presented as a valid target.

The formula must not be reproduced in TypeScript.

---

# PD-008 — Target recalculation and historical plans

**Status:** Approved

- Review targets every four weeks.
- Use seven-day average weight with at least four measurements.
- Do not react to one weight reading.
- Preserve selected cut intensity.
- Do not prompt when the calculated difference is below approximately 50 kcal.
- Show current and proposed targets and the reason.
- Apply only after user approval.
- Store immutable Target Plan Versions with effective dates and rule versions.
- Historical days retain the target plan active at their date.

Profile validation reconciliation for this expansion:

- this release does not introduce new age/height/weight range requirements;
- preserve current Backend validation unless a later formal decision changes it;
- historical D-009/D-012 range proposals are superseded for this expansion;
- exact Arabic read-error wording is not frozen; meaning, clarity, and accessibility are authoritative.

---

# PD-009 — Additional nutrient registry

**Status:** Approved

Supported target types:

```text
minimum
maximum
adequate
recommended
range
monitor_only
minimize
```

Approved targets:

| Nutrient | Type | Target |
|---|---|---|
| Fiber | Minimum | 30 g/day |
| Added sugar | Maximum | 10% of calories |
| Saturated fat | Maximum | 10% of calories |
| Trans fat | Maximum | less than 1% of calories |
| Sodium | Maximum | less than 2000 mg/day |
| Potassium | Adequate | Men 3400 mg; Women 2600 mg |
| Cholesterol | Monitor only | No numeric target |
| Zinc | Recommended | Men 11 mg; Women 8 mg |
| Selenium | Recommended | 55 mcg |
| Vitamin B12 | Recommended | 2.4 mcg |
| Folate | Recommended | 400 mcg DFE |
| Vitamin A | Recommended | Men 900 mcg RAE; Women 700 mcg RAE |
| Iodine | Recommended | 150 mcg |

Calcium:

| Group | Target |
|---|---:|
| Adults 19–50 | 1000 mg |
| Men 51–70 | 1000 mg |
| Women 51–70 | 1200 mg |
| Adults >70 | 1200 mg |

Iron:

| Group | Target |
|---|---:|
| Adult men | 8 mg |
| Women 19–50 | 18 mg |
| Women ≥51 | 8 mg |

Magnesium:

| Group | Target |
|---|---:|
| Men 19–30 | 400 mg |
| Men ≥31 | 420 mg |
| Women 19–30 | 310 mg |
| Women ≥31 | 320 mg |

Calorie-derived limits:

```text
added_sugar_g = calories × 10% ÷ 4
saturated_fat_g = calories × 10% ÷ 9
trans_fat_g = calories × 1% ÷ 9
```

Fiber 30 g is a myNutri quality target; the general reference may be shown as 25 g. Exceeding fiber target is not a warning.

Deferred nutrients include Vitamin D, C, E, K, B1, B2, B3, B6, phosphorus, copper, choline, omega-3 targets, and water/fluids.

---

# PD-010 — Food-group registry and serving rules

**Status:** Approved

Approved positive targets:

| Group | Operational serving | Target |
|---|---:|---|
| Vegetables | 80 g | Shared with fruit: 400 g/day |
| Fruit | 80 g | Shared with vegetables: 400 g/day |
| Dried fruit | 30 g | One fruit serving |
| Whole grains | Grain equivalent | At least 50% of known grain servings |
| Legumes | 80 g cooked / ½ cup | 3 servings/week |
| Nuts and seeds | 30 g | 5 servings/week |
| Seafood | 100 g edible portion | 2 servings/week |
| Omega-3-rich seafood | Trait | At least 1 seafood serving/week |
| Dairy/fortified alternatives | By subtype | 2 servings/day |

Dairy references:

- milk/laban/kefir: 250 ml;
- yogurt: approximately 170–200 g;
- hard cheese: 30 g;
- cottage cheese/ricotta: 120 g;
- calcium-fortified alternative: 250 ml.

Rules:

- vegetables and fruit are displayed separately plus combined total;
- 100% juice/smoothie contributes at most one fruit serving/day;
- starchy roots do not count toward the 400 g target;
- legumes are separate;
- plant alternatives count only when calcium fortification data are known;
- butter, ghee, cream, and ice cream do not satisfy dairy.

Monitor-only groups:

- eggs;
- poultry;
- added oils/fats;
- unsweetened beverages;
- herbs/spices.

Red meat:

- 100 g cooked edible portion is the operational serving;
- no minimum;
- maximum 500 g/week;
- 350–500 g is near the limit;
- above 500 g is over the limit.

Minimize groups:

- processed meat;
- sweets;
- sugar-sweetened beverages;
- NOVA 4 Foods.

No numeric “safe allowance” is created for minimize groups.

---

# PD-011 — Food classification and quantitative contributions

**Status:** Approved

Each Food has:

1. one primary category for organization;
2. `simple` or `composite` Food type;
3. quantitative food-group contributions per 100 g or 100 ml;
4. separate analytical traits;
5. contribution certainty/status: known, estimated, or unknown.

Primary category does not directly drive analysis. Quantitative contributions do.

For composite Foods:

- full recipe engine is deferred;
- contributions are entered manually;
- non-overlapping contribution totals cannot exceed the 100 g/100 ml basis;
- totals may be below 100;
- traits do not add to contribution totals.

Approved category set includes vegetables, fruit, legumes, whole grains, refined grains, nuts/seeds, seafood, dairy/fortified alternatives, eggs, poultry, red meat, processed meat, oils/added fats, sweets, sugar-sweetened drinks, unsweetened drinks, herbs/spices, and other.

Direct gram/ml Diary logging remains deferred. Existing serving-based Diary input is preserved in Waves 1–2.

---

# PD-012 — NOVA and ingredients

**Status:** Approved

NOVA values:

```text
1
2
3
4
unknown
```

- NOVA is not inferred from macros alone.
- Ingredients and source information support classification.
- System suggestions require user review.
- NOVA 4 is “minimize,” without an invented safe threshold.
- Analysis may show percentage of recorded calories, frequency, largest contributors, and classification coverage.
- NOVA remains separate from nutrient quality, food groups, and source reliability.

Foods support ingredients text and ingredients source. Ingredients are used for transparency, not danger labeling.

---

# PD-013 — Completeness, source reliability, and coverage

**Status:** Approved

These are separate concepts.

## Food nutrition completeness

Answers how many supported nutrient values exist. Displayed in Food Details only.

Suggested status bands:

| Completion | Status |
|---:|---|
| 90–100% | مكتملة جدًا |
| 75–89% | جيدة |
| 50–74% | جزئية |
| <50% | محدودة |

## Source reliability

Approved source types:

- laboratory analysis;
- official food database;
- official product label;
- official manufacturer website;
- official restaurant information;
- calculated Food;
- manual estimate;
- multiple sources;
- unknown.

The user selects source type; Backend derives reliability. Reliability is not a user-selected rating.

## Diary nutrient coverage

Initial method:

```text
entries with a known value ÷ total Diary entries × 100
```

- explicit zero is known;
- `null` is unknown;
- when no entry has a known value, aggregate amount remains `null` and UI shows `غير متوفر`;
- partial known totals use `على الأقل`;
- coverage is not adequacy.

Completeness and reliability must not be combined into one score.

---

# PD-014 — Diary Snapshot v2

**Status:** Approved

New Diary entries use a structured, versioned Snapshot v2 containing:

- Food identity at logging time;
- calories and macros;
- approved additional nutrients, preserving `null`;
- food-group contributions;
- analytical traits;
- NOVA;
- source type and derived reliability;
- completeness state;
- relevant rule versions;
- snapshot schema version.

Rules:

- quantity editing scales known values and preserves `null`;
- meal moves preserve the same snapshot;
- source Food edits/deletion never mutate historical Diary data;
- Backend reads legacy Snapshot v1 and new Snapshot v2;
- no historical enrichment from current Food data.

---

# PD-015 — Day logging status

**Status:** Approved

Statuses:

```text
unregistered
partial
complete
```

- Adding one Food does not automatically mark the day complete.
- User explicitly confirms completion.
- An empty day can be explicitly completed.
- Partial/unregistered days are never treated as zero-intake days.
- Strong weekly analysis requires complete days.

---

# PD-016 — Nutrition Pattern Analysis

**Status:** Approved

- rolling last seven days;
- previous seven days for comparison;
- minimum four complete days for strong analysis;
- adequate metric-specific coverage is required.

Approved section order:

1. Weekly priority.
2. Data sufficiency/confidence.
3. Food-group pattern.
4. Daily nutrient pattern.
5. Elements to limit.
6. Protein-source diversity.
7. NOVA pattern.
8. Previous-period comparison.
9. Contributors.

Comparison uses daily averages, not raw totals. Both periods require sufficient complete days and comparable coverage. Missing days never become zero.

Each result can expose contributing Foods and unknown entries.

---

# PD-017 — Weekly priority engine

**Status:** Approved

Maximum output:

- one main priority;
- one secondary priority when justified.

Priority order:

1. repeated exceedance of limit-type dimensions;
2. largest positive food-group/nutrient gap;
3. micronutrients only with strong coverage and persistent evidence.

Operational coverage guidance:

- 75%+ may support a strong priority;
- 50–74% supports limited-confidence messaging;
- below 50% is excluded from priority selection.

Every priority stores:

- rule key and version;
- measured reason;
- input facts;
- coverage/confidence;
- excluded alternatives;
- one practical action;
- explanation of why it appeared.

The engine is deterministic and Backend-owned. AI may help phrase text later but must not choose targets or calculate priority.

Shadow mode, golden scenarios, conflict tests, and manual review are required before launch.

---

# PD-018 — Weekly behavior goals

**Status:** Approved

A weekly priority may be accepted as an optional behavior goal.

- one primary active goal by default;
- user may accept, edit, defer, reject, or end;
- progress is derived from Diary data;
- no manual success checkbox as the source of truth;
- no XP, points, streak punishment, or shame;
- incomplete data prevents false success/failure claims;
- rejected goals are not immediately repeated without new evidence.

Neutral follow-up options include repeat, reduce scope, choose another goal, or end.

---

# PD-019 — Analysis snapshot lifecycle

**Status:** Approved

Live analysis updates as Diary changes.

Finalized Analysis Snapshots store:

- period;
- generated time;
- complete/partial/unregistered counts;
- coverage;
- aggregated results;
- priorities;
- registry and analysis-rule versions;
- revision number.

A historical Diary edit marks affected analyses stale and creates a new revision using the original analysis-rule version. Previous revisions remain auditable. History is never silently reinterpreted.

---

# PD-020 — Progress and health measurements

**Status:** Approved

## Weight

- timestamped history;
- seven-day average when at least four measurements exist;
- four-week trend;
- no target change from one reading.

## Waist

- optional history;
- four- and eight-week trends;
- standardized measurement guidance;
- no diagnosis or automatic calorie change.

## Blood pressure

- systolic and diastolic;
- pulse optional;
- history and averages;
- no diagnosis or automatic target change.

## Activity

- steps;
- resistance exercise;
- aerobic exercise;
- active days/week;
- seven- and thirty-day trends;
- no automatic daily calorie adjustment.

## Calorie review

Every four weeks, using seven-day average weight and user approval. The system shows current target, proposed target, and reason. It does not prompt for approximately <50 kcal differences.

---

# PD-021 — Health milestones

**Status:** Approved

Use calm health milestones, not gamification.

Examples include sustained fiber/food-group improvement, activity consistency, completed weekly behavior goals, and meaningful weight/waist progress.

No milestone for lowest calories, largest deficit, longest fasting, or fastest weight loss. Historical achievements are not removed after later regression.

---

# PD-022 — Behavioral safety

**Status:** Approved

The system must:

- use neutral language;
- avoid “failure,” shame, and punishment;
- focus on trends, not one day;
- avoid celebrating under-eating;
- avoid automatic harsher goals;
- avoid compensatory exercise or meal-skipping advice;
- warn about unsafe/invalid low-intake configurations;
- support simplified presentation of sensitive numbers where designed.

Exact wording is not globally frozen unless specified in an acceptance criterion. Meaning, clarity, Arabic quality, and accessibility are authoritative.

---

# PD-023 — Ownership and security

**Status:** Approved

All personal records are scoped to the authenticated user.

- Backend derives identity from authentication context.
- Frontend does not send an authoritative `user_id`.
- Every read/update/delete verifies ownership.
- Normal user operations do not use Service Role.
- Unauthorized existence is not leaked.
- Food deletion does not delete historical Diary snapshots.

Comprehensive export and delete-all-data are deferred. Existing individual delete actions remain.

---

# PD-024 — Migration strategy

**Status:** Approved

Use:

```text
Expand → Migrate → Contract
```

Rules:

- inspect the current schema first;
- create only the exact expansion delta;
- additive nullable fields first;
- no unknown value is backfilled with zero;
- preserve legacy Foods and Diary;
- old entries remain Snapshot v1;
- new entries may use Snapshot v2;
- no automatic Food-group/NOVA/source guessing;
- first Target Plan Version begins at activation; prior targets are not invented;
- Backend supports compatible versions during rollout;
- rollback remains possible.

Migration rehearsal must run on a disposable realistic PostgreSQL copy. Existing migrations are baseline assets and must not be recreated unnecessarily.

---

# PD-025 — API and Backend source of truth

**Status:** Approved

Existing APIs are the baseline and should be extended additively.

Approved API domains include:

- `GET /nutrition/registry`;
- additive Food nutrition/source/group fields;
- Backend-created Diary snapshots;
- day status;
- target preview/current/history;
- analysis/current/contributors/snapshots;
- weekly behavior goals;
- standard structured error contract.

Frontend must not calculate BMR, TDEE, deficit, adjusted protein weight, macro targets, nutrient targets, analysis confidence, or weekly priority.

Important mutations should support idempotency where duplicate submission is possible.

---

# PD-026 — Rule versioning

**Status:** Approved

Track independently:

```text
nutrition_registry_version
calculation_engine_version
food_group_rules_version
analysis_rules_version
snapshot_schema_version
```

An umbrella `product_nutrition_rules_version` may also be exposed.

Target plans, Diary snapshots, and Analysis Snapshots store the versions that produced them.

---

# PD-027 — Recommendation validation

**Status:** Approved

Every recommendation rule defines eligibility, exclusions, complete-day minimum, coverage minimum, priority category, Arabic templates, practical actions, and version.

Release requirements:

- unit tests;
- golden scenarios;
- missing-data tests;
- conflict tests;
- behavioral-safety review;
- shadow mode;
- manual review of realistic scenarios;
- full regression.

No recommendation is displayed merely because a single nutrient value is low on one incomplete day.

---

# PD-028 — Success metrics

**Status:** Approved

Measure value, not clicks.

Approved metrics include:

- complete-day rate;
- nutrient-data coverage;
- Food-group classification coverage;
- fiber and food-group pattern improvement;
- reduction in processed-meat and sugary-drink frequency;
- optional weekly goals accepted/completed;
- user understanding of target calculations;
- correction rate of unrealistic targets;
- sustained use without punitive behavior;
- weight/waist trend when relevant.

App opens and screen views are not primary health-value metrics.

---

# PD-029 — Readiness and scope freeze

**Status:** Approved

A wave is Ready to Build only when:

- its exact PRESERVE/MODIFY/ADD/DEFER/REMOVE matrix is complete;
- Critical = 0;
- High unresolved = 0;
- data model, API, migrations, rollback, and compatibility are approved;
- user stories and acceptance criteria are complete;
- calculation golden scenarios are fixed;
- loading, empty, error, partial, legacy, RTL, keyboard, and responsive states are defined;
- regression and physical-device status are explicit.

Readiness states:

```text
Not Ready
Conditionally Ready
Ready to Build
```

Only the active wave is frozen. Later-wave detail may remain approved product direction without being implementation-ready.

---

# Explicitly deferred from the current expansion release

- sleep;
- laboratory tests;
- medications and supplements;
- pregnancy, breastfeeding, kidney disease, bariatric, eating-disorder, and other clinical modes;
- deferred nutrients listed in PD-009;
- full recipe/ingredient calculation engine;
- barcode scanning;
- OCR and label import;
- broad Food import;
- allergies and unwanted-ingredient workflows;
- vegetarian/vegan/gluten-free/halal labels;
- full preparation-method taxonomy;
- Food review workflow;
- Food edit history;
- comprehensive data export;
- delete-all-data action;
- offline sync;
- multiple profiles;
- direct gram/ml Diary logging in Waves 1–2;
- AI nutrition decision-making;
- unified Health Score.

---

# Current governance status

```text
Existing product baseline: Implemented and checkpointed on main
Expansion register: Available and authoritative for reconciliation
Wave 1 baseline/delta audit: Must be rerun against current main and this register
Formal BA audit: Pending
Formal QA audit: Pending
Wave 1 migration/API freeze: Pending exact delta audit
Wave 1 Ready to Build: No
Existing product status: Not reclassified by this expansion readiness state
```

Required next action:

1. Reconcile every `PD-*` decision against current main.
2. Reclassify prior provisional `NQ-*` audit entries under the formal IDs.
3. Reassess all previous Critical/High issues as resolved, partially resolved, open, superseded, or reclassified.
4. Produce `07_PRODUCT_DECISION_RECONCILIATION.md`.
5. Produce `08_WAVE1_READINESS_RECHECK.md`.
6. Do not implement until the recheck defines the exact Wave 1 delta and returns the appropriate verdict.
