# myNutri Product Decision Register & Expansion Scope Freeze

**Version:** 1.1
**Status:** Approved governing source for baseline reconciliation; Wave 1 is not yet frozen or Ready to Build
**Document type:** Brownfield expansion / delta register
**Project:** myNutri
**Target expansion:** Nutrition Quality & Progress
**Implemented baseline:** Existing operational product; do not rebuild from scratch
**Supersedes:** The incomplete 42-line copy previously stored at this path

> myNutri and NutriPlan are separate projects. Their scope, entities, decisions, and requirements must never be mixed.

---

# How to use this register

This is the governing product source for reconciling the existing myNutri implementation with the approved Nutrition Quality & Progress expansion.

The current code, migrations, APIs, and tests are evidence of implementation. This register is the authority for product intent and expansion scope.

When sources conflict, use this precedence:

1. This register.
2. Frozen scope for the active wave.
3. Approved data/API contracts and acceptance criteria.
4. Current implementation evidence.
5. BA/QA reports.
6. Historical Architecture/System Plan documents and prior conversations.

Historical requirements explicitly superseded here must not be reintroduced.

Each requirement must be classified during reconciliation as:

```text
PRESERVE — implemented behavior that must not regress
MODIFY   — implemented behavior intentionally changed
ADD      — new capability
DEFER    — outside the active wave
REMOVE   — implemented behavior intentionally removed
```

Readiness statements in this register apply to the named expansion wave, not to the already developed myNutri product.

---

# PD-000 — Implemented baseline and expansion boundary

**Status:** Approved

myNutri is an already developed brownfield product with an implemented Frontend, Backend, PostgreSQL database, Alembic migrations, calculation engine, Foods, Diary, Profile, Add Food, and automated regression coverage.

This expansion must preserve the implemented baseline. It does not authorize a greenfield rewrite.

The implementation must not:

- rebuild stable modules without a demonstrated need;
- reintroduce offline personal-data storage, Dexie, mutation queues, or sync;
- reintroduce multiple profiles;
- replace stable APIs unnecessarily;
- weaken existing regression coverage;
- reinterpret historical Diary data silently;
- redesign unrelated routes;
- assume old Architecture/System Plan decisions are still active.

The following old assumptions are superseded:

- offline-first personal-data architecture;
- multiple tracked people/profiles;
- serving-based Food nutrition as the source of truth;
- meal type deferred;
- micronutrients entirely excluded;
- archive/inactive Food lifecycle where current hard-delete behavior is the approved baseline.

Direct gram/ml Diary logging remains deferred in this expansion unless a later formal decision changes it.

---

# PD-001 — Document authority and change control

**Status:** Approved

This register is the single product authority for the Nutrition Quality & Progress expansion.

After a wave is frozen:

- Critical security, safety, or data-integrity changes may enter immediately.
- High-impact scope changes require a formal Change Decision.
- Medium/Low improvements go to the backlog unless explicitly approved.
- A good idea alone does not reopen frozen scope.

A wave can be declared Ready to Build only when:

```text
Critical issues: 0
High unresolved issues: 0
Verdict: Ready to Build
```

---

# PD-002 — Product definition and boundaries

**Status:** Approved

myNutri is a personal Arabic-first nutrition and health-progress product that helps the user record food, understand dietary patterns, follow targets, and make gradual practical improvements.

Primary job:

> When I record my food and progress, I want to understand whether my overall pattern is improving and what practical change matters most next.

Product principles:

1. Truth before false precision.
2. Missing data is never treated as zero.
3. Patterns matter more than one isolated day.
4. Recommendations must be explainable.
5. Improvement language must remain neutral and non-punitive.
6. Backend rules are authoritative.
7. Historical data is versioned and not silently reinterpreted.
8. There is no unified Health Score.
9. Data quality is separate from nutrition quality.

myNutri is not:

- a diagnosis or treatment system;
- a replacement for a physician or dietitian;
- a clinical platform for pregnancy, kidney disease, bariatric care, eating disorders, or similar cases;
- a supplement, medication, or laboratory tracker in this release;
- a full recipe-management system;
- an AI system that independently changes nutritional targets;
- a product that labels a single Food simply healthy/unhealthy;
- a product that promises disease prevention or longer life.

Approved claim direction:

> myNutri supports food-quality awareness, sustainable habits, and health-related lifestyle improvement.

---

# PD-003 — Navigation and information architecture

**Status:** Approved

The main tabs are:

```text
اليوميات
الأطعمة
التقدم
الملف
```

No additional main tab may be introduced in this release without a formal change decision.

## اليوميات

Includes date navigation, calories, macros, meal sections, Add/Edit/Delete Diary entries, meal totals, additional nutrient details, day status, and a contextual link to nutrition analysis.

## الأطعمة

Includes Food list/search, create/edit/detail/delete, per-100g/per-100ml nutrition source, serving display, approved nutrients, primary category, simple/composite type, food-group contributions, analytical traits, ingredients, NOVA, source, reliability, and completeness.

## التقدم

Includes Nutrition Pattern Analysis, weekly priority, weight, waist, blood pressure, activity, comparisons, weekly goals, milestones, and four-week calorie review.

Approved detail routes:

```text
/progress
/progress/nutrition
/progress/weight
/progress/waist
/progress/blood-pressure
/progress/activity
/progress/calorie-review
```

## الملف

Includes personal calculation inputs, goal, activity, cut intensity, macro settings, target preview, current targets, additional nutrient targets, and calculation explanation.

The four main tabs must remain usable at 320px without horizontal scrolling.

---

# PD-004 — Expansion waves and scope sequencing

**Status:** Approved

The expansion is delivered in four waves on top of the current product.

## Wave 1 — Nutrition & Data Foundation

Includes:

- revised calorie/macro policy;
- central nutrient registry;
- central food-group registry;
- source reliability registry;
- NOVA definitions;
- nullable approved nutrient data;
- source and ingredients metadata;
- Food simple/composite classification;
- quantitative food-group contributions;
- Diary Snapshot v2;
- Target Plan Versions;
- rule versioning;
- additive API/data contracts;
- migration and compatibility planning;
- golden calculations and characterization tests.

## Wave 2 — Foods & Diary Experience

Includes UI entry/display of approved nutrients, food groups, traits, source, reliability, ingredients, NOVA, completeness, Diary coverage, additional nutrient details, meal macros, and day status.

## Wave 3 — Nutrition Pattern Analysis

Includes rolling seven-day analysis, data sufficiency, food-group analysis, nutrient analysis, NOVA, protein diversity, contributor drill-down, weekly priorities, behavior goals, comparisons, and Analysis Snapshots.

## Wave 4 — Health Progress

Includes historical weight, waist, blood pressure, activity, four-week calorie review, and calm health milestones.

A later wave must not be implemented during an earlier wave unless required as a documented dependency.

---

# PD-005 — Energy and cut-deficit policy

**Status:** Approved

Continue using the server-side Mifflin–St Jeor calculation and the current approved activity-factor model.

When goal = cut, offer:

| Option | Deficit |
|---|---:|
| خفيف | 15% |
| عادي | 20% — default/recommended |
| قوي | 25% |

Rules:

- automatic deficit may not exceed 750 kcal/day;
- resulting calories are shown before save;
- under 800 kcal/day is blocked in normal product mode;
- 800–1200 kcal/day requires a strong caution and specialist-review language;
- the selected percentage is not presented as a guaranteed weight-loss rate;
- backend remains authoritative.

Existing Profile validation ranges not explicitly changed by this register remain governed by the current approved baseline. They are not a Wave 1 product gap merely because an older document contains different ranges.

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

When BMI >= 30:

```text
reference_weight = 25 × height_m²
adjusted_weight = reference_weight + 0.33 × (actual_weight − reference_weight)
calculation_weight = adjusted_weight
```

Then:

```text
protein_target_g = calculation_weight × protein_per_kg
```

Rules:

- same default factor for men and women;
- user may customize grams/kg;
- UI explains the weight basis used;
- custom existing values are preserved;
- clinical exceptions are deferred.

---

# PD-007 — Fat and carbohydrate allocation

**Status:** Approved

Approved default fat percentages:

- men: 25% of target calories;
- women: 30% of target calories.

These are product defaults within the adult reference range, not a claim that every person physiologically requires that exact percentage.

Rules:

- custom fat percentage is preserved;
- changing sex updates fat only when the current value is still controlled by the prior default;
- Restore Defaults returns to the sex-aware default;
- Preview and Save must use the same backend calculation.

Carbohydrates receive the remaining calories:

```text
carb_calories = target_calories − protein_calories − fat_calories
carb_target_g = carb_calories ÷ 4
```

Warnings:

- below 130 g: calm general-reference warning;
- below 100 g: stronger warning.

A zero or negative resulting carbohydrate allocation is invalid. Preview and Save must reject it through a structured server-authoritative error. Silent clamping to an ordinary valid zero-carb target is not approved.

---

# PD-008 — Target recalculation and historical Target Plans

**Status:** Approved

Review calorie targets every four weeks.

Rules:

- use a seven-day average weight;
- require at least four weight measurements in that period;
- never recalculate from one reading;
- preserve the selected cut intensity;
- do not prompt when the calculated difference is below approximately 50 kcal;
- show current versus proposed calories/macros and the reason;
- apply only after user confirmation;
- historical days retain the Target Plan active at that time.

Target Plan Versions are immutable and store:

- effective date range;
- calculation inputs;
- calories and macros;
- approved additional nutrient targets;
- goal and deficit intensity;
- protein basis and calculation weight;
- custom settings;
- calculation and registry versions.

---

# PD-009 — Additional nutrient registry

**Status:** Approved

The approved Wave 1 registry contains these nutrients as nullable values:

```text
fiber_g
added_sugar_g
saturated_fat_g
trans_fat_g
sodium_mg
potassium_mg
cholesterol_mg
calcium_mg
iron_mg
magnesium_mg
zinc_mg
selenium_mcg
vitamin_b12_mcg
folate_dfe_mcg
vitamin_a_rae_mcg
iodine_mcg
```

Known zero is valid. Unknown is null.

Approved target types:

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
| Fiber | minimum | 30 g/day |
| Added sugar | maximum | 10% of target calories |
| Saturated fat | maximum | 10% of target calories |
| Trans fat | maximum | less than 1% of target calories |
| Sodium | maximum | less than 2000 mg/day |
| Potassium | adequate | Men 3400 mg; Women 2600 mg |
| Cholesterol | monitor_only | no numeric target |
| Calcium | recommended | age/sex table below |
| Iron | recommended | age/sex table below |
| Magnesium | recommended | age/sex table below |
| Zinc | recommended | Men 11 mg; Women 8 mg |
| Selenium | recommended | 55 mcg/day |
| Vitamin B12 | recommended | 2.4 mcg/day |
| Folate | recommended | 400 mcg DFE/day |
| Vitamin A | recommended | Men 900 mcg RAE; Women 700 mcg RAE |
| Iodine | recommended | 150 mcg/day |

Calcium:

- age 19–50: 1000 mg;
- men 51–70: 1000 mg;
- women 51–70: 1200 mg;
- over 70: 1200 mg.

Iron:

- adult men: 8 mg;
- women 19–50: 18 mg;
- women 51+: 8 mg.

Magnesium:

- men 19–30: 400 mg;
- men 31+: 420 mg;
- women 19–30: 310 mg;
- women 31+: 320 mg.

Calorie-derived limits:

```text
added_sugar_limit_g = target_calories × 0.10 ÷ 4
saturated_fat_limit_g = target_calories × 0.10 ÷ 9
trans_fat_limit_g = target_calories × 0.01 ÷ 9
```

The 30 g fiber value is an approved myNutri food-quality target, not an exact clinical prescription. Exceeding it is not a warning.

Deferred nutrients:

- Vitamin D, C, E, K;
- B1, B2, B3, B6;
- phosphorus, copper, choline;
- omega-3 targets;
- water/fluid targets.

---

# PD-010 — Food-group registry and serving rules

**Status:** Approved

The approved groups include:

- vegetables;
- fruits;
- legumes;
- whole grains;
- refined grains;
- nuts and seeds;
- fish and seafood;
- dairy and fortified alternatives;
- eggs;
- poultry;
- red meat;
- processed meat;
- oils and added fats;
- sweets;
- sugar-sweetened beverages;
- unsweetened beverages;
- herbs and spices;
- other.

Approved goals:

## Vegetables and fruit

- combined target: 400 g/day;
- display vegetables and fruit separately plus combined total;
- operational serving: 80 g;
- dried fruit: 30 g = one serving;
- 100% juice/smoothie may contribute no more than one fruit serving/day;
- potatoes and starchy roots do not count;
- legumes are separate.

## Whole grains

- at least 50% of known grain equivalents are whole grain;
- mixed Foods are split using actual contributions;
- unknown grain type stays unknown;
- show classification coverage.

## Legumes

- 80 g cooked or 1/2 cup = one serving;
- minimum 3 servings/week;
- fractional servings accumulate.

## Nuts and seeds

- 30 g = one serving;
- minimum 5 servings/week;
- peanuts count nutritionally;
- nut oils do not count as nuts/seeds servings.

## Seafood

- 100 g edible/drained weight = one serving;
- minimum 2 servings/week;
- at least one serving/week should be omega-3-rich through a separate trait.

## Dairy and fortified alternatives

- minimum 2 servings/day;
- milk/laban/kefir: 250 ml;
- yogurt: approximately 170–200 g;
- hard cheese: 30 g;
- cottage cheese/ricotta: 120 g;
- fortified plant alternative: 250 ml with known calcium fortification;
- butter, ghee, cream, and ice cream do not complete the dairy target.

## Eggs

- one large whole egg is approximately 50 g;
- monitor only; no minimum;
- distinguish whole egg from egg whites.

## Poultry

- 100 g cooked edible meat = one operational serving;
- monitor only; no minimum;
- processed poultry is processed meat for pattern analysis.

## Red meat

- 100 g cooked edible meat = one serving;
- no minimum;
- weekly maximum 500 g;
- 350–500 g = near limit;
- above 500 g = over limit.

## Processed meat

- minimize;
- no numeric safe allowance;
- show grams and frequency.

## Oils and added fats

- monitor only;
- track amount and source;
- nuts, fish, and avocado do not count as added oil.

## Sweets and sugar-sweetened beverages

- minimize;
- no numeric safe allowance;
- show amount and frequency;
- 100% juice is not classified as a sugar-sweetened beverage, but its fruit contribution is capped.

Unsweetened beverages and herbs/spices are monitor only.

---

# PD-011 — Food classification and quantitative group contributions

**Status:** Approved

Each Food has:

1. one primary category for organization;
2. Food kind: simple or composite;
3. multiple quantitative food-group contributions per 100 g or 100 ml;
4. separate analytical traits;
5. group-data status: known, estimated, or unknown.

Primary category does not directly drive analysis. Quantitative contributions drive analysis.

Composite Foods do not require a full recipe engine in this release. Contributions are entered manually.

Validation:

- contribution amount is non-negative;
- one Food has at most one row per group key;
- total non-overlapping contributions may not exceed 100 g or 100 ml per basis;
- total may be lower than 100;
- analytical traits do not add to the contribution sum.

Approved traits include, where supported:

- sweetened;
- unsweetened;
- processed;
- omega-3-rich seafood;
- calcium-fortified;
- unsaturated-fat source;
- smoked/salted when analytically useful.

Traits must not create duplicate servings.

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

Rules:

- NOVA is not inferred from macros alone;
- ingredients and source support classification;
- system suggestions require user review;
- NOVA 4 is a minimize dimension without a fabricated safe threshold;
- Food Details shows NOVA;
- seven-day analysis may show percentage of recorded calories from NOVA 4, frequency, top contributors, and classification coverage;
- NOVA remains separate from nutrient quality, food groups, completeness, and source reliability.

Foods support ingredients text and ingredients source.

Ingredients are used for transparency and classification, not to declare ingredients dangerous.

---

# PD-013 — Completeness, source reliability, and Diary coverage

**Status:** Approved

These are separate dimensions and must never be combined into one score.

## Food nutrition completeness

Answers: how many supported nutrition values are present?

Display only in Food Details, not Foods list, Add Food search, Diary rows, or Diary search results.

Suggested status bands:

| Percentage | Status |
|---:|---|
| 90–100% | مكتملة جدًا |
| 75–89% | جيدة |
| 50–74% | جزئية |
| below 50% | محدودة |

Known zero counts as present. Null counts as missing.

## Source reliability

Approved source types:

- laboratory analysis;
- official food database;
- official product label;
- official manufacturer website;
- official restaurant information;
- calculated recipe/Food;
- manual estimate;
- multiple sources;
- unknown.

The user selects source type. Backend derives reliability; the user does not directly choose a reliability rating.

## Diary nutrient coverage

Initial method:

```text
entries with a known value ÷ total Diary entries × 100
```

Known explicit zero counts as known. Null counts as unknown.

When coverage is incomplete, the amount is shown as `على الأقل`.

When no entry has a known value, the amount is `غير متوفر`, not numeric zero, and target progress/status is suppressed.

Coverage is not nutrient adequacy.

## Food-group coverage

Food-group analysis must report the share of logged Foods with usable group contribution data and must not issue strong conclusions when coverage is insufficient.

---

# PD-014 — Diary Snapshot v2

**Status:** Approved

New Diary entries use a versioned Snapshot v2 containing:

- Food identity at logging time;
- calories and macros;
- all approved additional nutrients as number or null;
- food-group contributions;
- analytical traits;
- NOVA;
- source type and derived reliability;
- completeness state;
- registry/rule versions;
- snapshot schema version.

Rules:

- quantity editing scales known values and preserves null;
- meal movement preserves the same snapshot;
- Food edit/delete cannot change old Diary snapshots;
- existing Snapshot v1 data remains readable;
- no historical backfill from the current Food row;
- backend creates snapshots; frontend does not submit authoritative nutrient totals.

---

# PD-015 — Day logging status

**Status:** Approved

Statuses:

```text
unregistered
partial
complete
```

Rules:

- one Food entry does not automatically make a day complete;
- the user explicitly marks a day complete;
- an intentionally empty day may be explicitly completed;
- partial and unregistered days are never treated as zero-intake days;
- strong seven-day analysis uses completed days.

---

# PD-016 — Nutrition Pattern Analysis

**Status:** Approved

Analysis window:

- rolling last seven days;
- previous seven days for comparison;
- not a fixed calendar week.

Strong analysis requires:

- at least four complete days;
- sufficient coverage for the metric being analyzed.

Page order:

1. weekly priority;
2. data sufficiency and confidence;
3. food groups;
4. daily nutrients;
5. elements to limit;
6. protein-source diversity;
7. NOVA pattern;
8. previous-period comparison;
9. contributors.

Rules:

- no unified Health Score;
- compare daily averages, not raw totals;
- each comparison period needs at least four complete days;
- missing days never become zero;
- material coverage differences may block improvement claims;
- each metric can expose top contributors and unknown entries.

Suggested recommendation eligibility by metric coverage:

- 75% or higher: eligible for strong priority;
- 50–74%: limited-confidence result;
- below 50%: excluded from strong priority.

---

# PD-017 — Weekly priority engine

**Status:** Approved

Maximum output:

- one main priority;
- one secondary priority only when justified.

Priority order:

1. repeated overages of limit/minimize dimensions;
2. largest actionable positive gap;
3. micronutrients only with strong coverage and persistent evidence, normally across at least two weeks.

Every priority stores/displays:

- rule key;
- title;
- measured reason;
- confidence;
- coverage;
- one practical action;
- rule version;
- facts used;
- excluded alternatives or conflict resolution where relevant.

The engine must avoid contradictory or duplicative recommendations and prefer replacement over simple addition where calories are already high.

Recommendation decisions are deterministic. AI may be used later only for phrasing, never for targets, eligibility, or calculation.

---

# PD-018 — Weekly behavior goals

**Status:** Approved

A weekly priority may become an optional behavior goal.

Rules:

- one primary active goal by default;
- user can accept, edit, defer, reject, change, or end it;
- progress is derived from Diary data, not a manual success checkbox;
- no XP, points, punishment, or lost streaks;
- insufficient data prevents false success/failure claims;
- rejected goals are not immediately repeated without new evidence;
- if incomplete, use neutral wording and offer repeat, reduce, change, or end.

Reminder policy:

- at most one contextual midweek reminder when there is no progress;
- one end-of-week review;
- external notifications remain optional.

---

# PD-019 — Analysis snapshots and lifecycle

**Status:** Approved

Current analysis is live and updates as Diary data changes.

Finalized Analysis Snapshots store:

- analysis period;
- generated time;
- complete/partial/missing day counts;
- metric coverage;
- aggregated results;
- priorities;
- analysis-rule version;
- registry versions;
- revision number.

When historical Diary data changes:

- affected snapshots are marked stale;
- recomputation uses the original applicable rule version;
- a new revision is created;
- the previous revision remains auditable;
- history is not silently reinterpreted with newer rules.

---

# PD-020 — Progress tab and health measurements

**Status:** Approved

## Weight

- historical timestamped measurements;
- seven-day average when at least four readings exist;
- four-week trend;
- no plan change from one reading;
- deletion recalculates trends.

## Waist circumference

- optional;
- timestamped history;
- four- and eight-week trends;
- standardized measurement instructions;
- no diagnosis or automatic calorie change.

## Blood pressure

- optional systolic and diastolic;
- pulse optional;
- history and trends;
- no diagnosis or automatic nutrition changes.

## Physical activity

- steps;
- resistance training;
- aerobic activity;
- active days/week;
- seven- and thirty-day trends;
- no daily calorie adjustment.

## Four-week calorie review

- uses seven-day average weight;
- retains chosen deficit intensity;
- ignores changes below approximately 50 kcal;
- shows current versus proposed targets and reason;
- requires user confirmation.

Sleep, laboratory tests, smoking/alcohol tracking, medications, and supplements are deferred.

---

# PD-021 — Health milestones

**Status:** Approved

Use calm, meaningful health milestones rather than gamification.

Possible milestones include:

- repeated fiber achievement;
- improved vegetables/fruit pattern;
- consistent activity;
- completed weekly behavior goals;
- sustained weight or waist progress;
- improved logging completeness.

Rules:

- no XP, levels, coins, or artificial reward economy;
- no milestone for lowest calories, longest fasting, largest deficit, or fastest loss;
- historical achievements are not removed after later regression.

---

# PD-022 — Behavioral safety and user language

**Status:** Approved

The system must:

- use neutral language;
- avoid shame and `failure` wording;
- avoid punishment for missed logging;
- avoid celebrating under-eating;
- focus on trends rather than one day;
- avoid automatic harsher goals;
- never encourage compensatory exercise or meal skipping;
- warn about implausibly low targets;
- support a simplified view that can hide precise macros/remaining calories/weight from the home surface;
- allow tracking pause as a planned safety capability.

Exact historical error-message wording is not frozen by this register unless an acceptance criterion explicitly quotes it. Clear Arabic behavior and meaning are authoritative; older exact-copy decisions may be superseded by newer approved UX copy.

Approved tone example:

```text
تجاوزت الهدف اليومي بـ 120 سعرة
يوم واحد لا يحدد اتجاهك
```

---

# PD-023 — Ownership, privacy, and security

**Status:** Approved

All user-created records are scoped to the authenticated user.

Rules:

- backend derives identity from the session;
- frontend does not send an authoritative user_id;
- every read/update/delete verifies ownership;
- normal operations do not use Service Role;
- Foods, Diary entries, target plans, measurements, analyses, and weekly goals are owner-bound;
- historical snapshots survive source Food deletion;
- error responses do not leak unauthorized record existence.

Comprehensive export and delete-all-data are deferred. Existing individual deletion behavior remains available according to the current approved baseline.

---

# PD-024 — Migration strategy

**Status:** Approved

Use:

```text
Expand → Migrate → Contract
```

Rules:

- inspect the current committed schema before proposing any migration;
- additive nullable changes first;
- never backfill unknown nutrients with zero;
- legacy Foods and Diary entries remain usable;
- Snapshot v1 and v2 compatibility is required;
- no historical group/NOVA/source guessing;
- do not invent historical Target Plan versions before activation;
- rollback compatibility must be documented;
- migrations must be rehearsed against a disposable PostgreSQL database with realistic copied data;
- do not add a migration merely because this register names a concept; use the existing schema where it correctly supports the requirement.

The audit must determine the exact migration delta from the current `main` baseline.

---

# PD-025 — API and backend source of truth

**Status:** Approved

Existing APIs are baseline assets. Extend them additively where practical.

Backend is authoritative for:

- BMR and TDEE;
- deficits;
- adjusted protein weight;
- calorie and macro targets;
- nutrient targets;
- source reliability;
- snapshots;
- analysis eligibility and confidence;
- weekly priorities.

Frontend must not duplicate these calculations.

Approved API capability areas:

1. Nutrition Registry.
2. Food nutrition/source/group/trait extensions.
3. Diary entry snapshot creation and scaling.
4. Diary day summary and coverage.
5. Day logging status.
6. Target Plan preview/current/history.
7. Nutrition Analysis and contributors.
8. Analysis Snapshots.
9. Weekly behavior goals.

Mutation rules:

- use idempotency where duplicate submission is harmful;
- stable error codes with Arabic display messages;
- missing values use null;
- contracts remain additive/backward compatible where feasible;
- frontend sends Food/date/meal/quantity inputs, while backend constructs authoritative snapshots.

Direct gram/ml Diary logging remains deferred.

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

An umbrella product nutrition rules version may also be exposed.

Snapshots, Target Plans, and Analysis Snapshots store the versions that produced them.

Rules are centralized in a backend-owned/versioned package covering:

```text
nutrients
food_groups
macro_policy
deficit_policy
analysis_policy
source_reliability
nova_definitions
versioning
```

Frontend display metadata must come from the authoritative contract rather than an independently editable duplicate registry.

---

# PD-027 — Recommendation validation and launch

**Status:** Approved

Every recommendation rule requires:

- rule key and version;
- eligibility conditions;
- exclusions;
- minimum complete days;
- minimum coverage;
- conflict behavior;
- priority category;
- Arabic templates;
- practical actions.

Release requirements:

- unit tests;
- golden scenarios;
- null versus known-zero tests;
- missing-data cases;
- conflict tests;
- behavioral-safety copy review;
- shadow/silent mode before user display;
- manual review of realistic scenarios;
- full regression.

No recommendation may be displayed as a strong conclusion when its own evidence and coverage gates are not satisfied.

---

# PD-028 — Product success metrics

**Status:** Approved

Measure value rather than raw screen visits.

Approved metrics include:

- completed-day rate;
- nutrient-data coverage;
- food-group coverage;
- fiber-target frequency;
- improvement in vegetables/fruit, legumes, whole grains, nuts, seafood, and dairy;
- reduction in processed meat and sugar-sweetened beverage frequency;
- weekly goals accepted and completed;
- user understanding of target calculation;
- correction rate of unrealistic targets;
- sustained use without punitive behavior;
- weight or waist trends where relevant.

App opens and page views are not primary product-success metrics.

---

# PD-029 — Readiness gate and formal scope freeze

**Status:** Approved

The existing myNutri baseline is implemented. This gate applies only to each expansion wave.

A wave is Ready to Build only when:

- all governing decisions for that wave are present and reconciled;
- baseline versus delta classification is complete;
- Critical issues = 0;
- High unresolved issues = 0;
- data model and exact schema delta are approved;
- migration and rollback plan are approved;
- API contracts are approved;
- user stories and acceptance criteria are complete;
- golden calculations are fixed;
- loading, empty, error, partial, legacy, keyboard, RTL, and responsive states are defined;
- verification and regression plans are approved.

Readiness states:

## Not Ready

Contradictory decisions, unresolved schema/API/calculation rules, or open Critical/High issues.

## Conditionally Ready

Foundation is sound and only documented Medium/Low gaps remain; spike/prototype work only.

## Ready to Build

Scope is frozen, contracts/tests/rollback are defined, and Critical/High unresolved issues are zero.

After freeze:

- Critical security/safety/data-integrity work may enter immediately;
- High changes require formal approval;
- other ideas go to backlog/future scope.

---

# Explicit deferred scope

The following are not part of this expansion release unless a later Change Decision adds them:

- sleep tracking;
- laboratory tests;
- medications and supplements;
- pregnancy/breastfeeding and clinical disease modes;
- full recipe and ingredient-calculation engine;
- barcode scanning;
- OCR/label import;
- general Food import expansion;
- allergies and unwanted ingredients;
- vegetarian/vegan/gluten-free/halal product labels;
- full preparation-method taxonomy;
- Food review states/workflow;
- Food edit history;
- comprehensive export;
- delete all data;
- offline personal-data storage and synchronization;
- direct gram/ml Diary logging;
- AI nutrition decisions;
- unified Health Score;
- the deferred nutrients named in PD-009.

---

# Required reconciliation output

The strict reconciliation must quote and classify every decision `PD-000` through `PD-029` and report:

```text
Current audited HEAD
Decision ID
Exact governing requirement
Current implementation evidence
Classification
Exact remaining delta
Schema impact
Migration impact
API impact
Test impact
Severity
Closure evidence
```

It must also reassess prior issues as:

```text
Resolved
Partially resolved
Still open
Superseded
Reclassified
```

The output must not claim Wave 1 readiness until all formal requirements in this complete register have been considered.

---

**End of myNutri Product Decision Register & Expansion Scope Freeze v1.1**
