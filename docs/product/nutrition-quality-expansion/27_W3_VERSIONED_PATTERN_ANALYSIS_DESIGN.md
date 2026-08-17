# PLAN 032 — Versioned Nutrition Pattern Analysis design

**Status:** Approved — frozen for implementation; implementation requires separate path authorization

**Design version:** `1.0`

**Analysis contract version:** `1`

**First active analysis rules version:** `w3-analysis-1.0.0`

**Repository baseline:** `b44549291ccd950f12742467bbbe3a69ff455626`

**Upstream authority:** PLAN 031 merge `de736c6cb681c652fb17244cebad64f62665f487`

**Downstream compatibility authority:** frozen PLAN 033 at this baseline
**Approval provenance:** Codex discipline-specific assessments performed under explicit Project Owner authorization; not eight independently submitted named human reviews

## 1. Decision and boundary

PLAN 032 owns deterministic, Backend-authoritative Nutrition Pattern Analysis between immutable Diary/Target/Registry evidence and downstream consumers. It owns analysis-window construction, metric-specific coverage, versioned calculations, immutable revisions, contributor facts, stale/supersession lifecycle, and the exact `WeeklyPriorityAnalysisInputV1` projection consumed by PLAN 033.

It does not own Diary completion, Target Plan calculation, Registry definitions, the PLAN 033 selector, behavior goals, notification delivery, diagnosis, treatment, supplement advice, or a unified score.

The mandatory separation is:

1. Diary entry snapshots remain immutable raw nutrition/classification facts.
2. PLAN 031 remains sole authority for day state, version, completion evidence, and the captured Diary calendar.
3. Target Plans remain sole authority for effective targets and safety outcomes by Diary date.
4. PLAN 032 builds two evidence windows and calculated pattern facts.
5. PLAN 032 persists immutable analysis revisions and source references.
6. PLAN 032 projects a closed downstream document; PLAN 033 never reads raw Diary rows or recalculates analysis.

**NO UNIFIED NUTRITION SCORE.** No scalar, grade, badge, or ranking may combine unrelated metrics into a health score.

## 2. Mapped repository authorities

| Concern | Existing authority | PLAN 032 use |
| --- | --- | --- |
| Principal | `PrincipalContext` and owner-bound models | derive `principal_ref`; never accept it from a client |
| Calendar | `backend/app/core/calendar.py` | capture once per new evaluation |
| Day evidence | PLAN 031 `DiaryDayStatus` and history | consume status/version/count/completed time unchanged |
| Entry facts | immutable `DiaryEntry.nutrition_snapshot` plus schema version | read version-dispatched values; never use mutable Food rows to reinterpret history |
| Targets | versioned `TargetPlan`, transition snapshot, date resolver | resolve each date using the one captured date and preserve exact references |
| Nutrients/groups/NOVA | Backend Registry and immutable snapshot fields | stable keys, units, participation, contribution and classification facts |
| Rule versions | `backend/app/nutrition_rules/versions.py` and canonical manifest | activate and dispatch `analysis_rules_version` only after implementation authorization |
| Priorities | frozen PLAN 033 | downstream consumer only; separate rules/copy versions |

The existing Sunday-aligned `WeekSummary` is presentation data and is not an analysis input or persistence format.

### 2.1 Approved decision reconciliation

| Authority | Frozen PLAN 032 resolution |
| --- | --- |
| `PD-016` | Rolling seven-day analysis, immediately previous comparison, four complete days, metric coverage, contributors and no unified score are made exact in sections 3–7. |
| `PD-019` | Auditable finalized snapshots, immutable revisions, stale/supersession and original-rule replay are frozen in sections 8–9 and 13. |
| `PD-025` | The Backend alone calculates and persists analysis; additive owner-only APIs expose stable null/error/idempotency semantics; the client supplies no nutrition facts. |
| `PD-026` | Registry, calculation, group, source-reliability, NOVA, snapshot and analysis identities remain independent; no umbrella version substitutes for them. |
| `H10` | PLAN 032 activates the previously reserved analysis slot as `w3-analysis-1.0.0`, uses exact version dispatch and immutable manifest semantics, and never assigns versions retroactively. |

## 3. Calendar and window contract

### 3.1 One snapshot

For a new evaluation, the Backend calls `diary_calendar_authority()` exactly once before reading evidence or acquiring analysis locks. The returned `current_diary_date` is `as_of_diary_date`; timezone is the literal `Asia/Riyadh`.

Idempotent replay is checked before a new calendar capture. A completed matching replay returns the originally stored response and calendar binding.

All downstream reads, target resolution, window dates, revision identity, status checks, and response fields use the captured date:

```text
period_end            = as_of_diary_date
period_start          = period_end - 6 days
previous_period_end   = period_start - 1 day
previous_period_start = previous_period_end - 6 days
```

Both arrays contain seven unique consecutive dates in ascending order. They are contiguous and never overlap. Sunday alignment is prohibited.

If Riyadh midnight occurs during computation, the request keeps its captured date. The next non-replay request captures the new date and therefore addresses another logical analysis series. Replay always returns the original date/window even after rollover.

### 3.2 Logical identity

`source_analysis_id` is a server UUID identifying `(principal_id, as_of_diary_date, interface_version=1)`. The database enforces this tuple as unique. It is stable across revisions of that captured-date analysis and is opaque outside the Backend.

## 4. Day and source-evidence contract

### 4.1 Day eligibility

| PLAN 031 projection | Analysis behavior |
| --- | --- |
| `complete`, zero entries | eligible exact-zero day; counts toward complete-day minimum; contributes no entry to coverage denominator |
| `complete`, one or more entries | eligible; metric values and coverage come only from immutable supported snapshots |
| `partial` | excluded completely; never zero |
| `unregistered` | excluded completely; never zero |
| reopened from complete | excluded from new evaluation immediately; existing revision remains immutable and receives a stale event |
| future date | never eligible even if malformed persisted data claims completion; fail closed |

The analyzer validates `analysis_eligible == (logging_status == "complete")`, non-negative entry counts, and status version consistency. A contradiction yields analysis result `unavailable` with `invalid_day_evidence` and writes no successful revision.

Eligibility is evaluated from the captured source bundle for every computation. Finalization stores those exact day versions. Replay reads the stored revision; it does not reevaluate current day status.

### 4.2 Late and corrected evidence

- Entry creation/edit/delete is already prohibited while a day is complete. The owner must reopen first.
- Reopen appends `day_reopened` stale evidence for every current revision referencing that day.
- Re-completing the day creates a new PLAN 031 day version. The next authorized evaluation may create a new analysis revision.
- A newly effective Target Plan, corrected supported snapshot, Registry/rule upgrade, or accepted upstream correction never edits an old analysis document.
- Historical recomputation uses the original `analysis_rules_version`; it creates a successor revision only when the canonical source input changes.

Unsupported snapshot versions, malformed/non-finite values, inconsistent target ownership, or an unavailable required rule package fail closed. No partial successful revision is persisted.

For v1, every participating fact across both periods must resolve under one identical Nutrition Registry version, one food-group rules version, and one NOVA rules version. Mixed versions cannot be represented truthfully by frozen PLAN 033's singular top-level fields, so they fail the evaluation with `incompatible_source_versions`; supported mixed snapshot schema versions are the sole exception because the downstream contract carries their sorted list and exact readers canonicalize each immutable snapshot. A later rules version may add an approved cross-version normalization, but v1 never assumes compatibility.

## 5. Metric coverage and numeric semantics

### 5.1 Period evidence counts

For one metric and one seven-day period:

```text
complete_day_count = count(day.status == complete)
total_entry_count  = sum(day.entry_count for complete non-empty days)
known_entry_count  = count(entries on complete days with a finite known value for this metric)
numeric_day_count  = count(complete empty days) + count(complete non-empty days with >=1 known metric entry)
```

`partial` and `unregistered` days appear in the seven-day array but contribute to none of these counts.

Coverage is:

```text
if complete_day_count == 0:                    coverage = null
else if total_entry_count == 0:                coverage = 100.000000
else:                                          coverage = round6(known_entry_count / total_entry_count * 100)
```

An explicit numeric zero is known and participates in numerator and arithmetic. `null`, absent, unsupported, or non-finite is unknown and never becomes zero.

Period confidence is exactly:

| Condition | Confidence | Selector eligibility |
| --- | --- | --- |
| complete days >=4 and coverage >=75 | `strong` | eligible subject to target/safety rules |
| complete days >=4 and 50 <= coverage <75 | `limited` | display only |
| otherwise | `unavailable` | omitted from selection |

Coverage is metric-specific. There is no blanket weekly coverage value that substitutes for it.

### 5.2 Numeric aggregation

For additive daily metrics, each complete empty day contributes day value `0`. A complete non-empty day contributes the sum of its known finite entry values when at least one value is known; a day with no known value is absent from the numeric average. Then:

```text
daily_average = round6(sum(numeric day values) / numeric_day_count)
```

When `0 < known_entry_count < total_entry_count`, `amount_qualifier="at_least"`; at 100% coverage or an empty-only period it is `exact`; with no numeric day it is `unavailable`.

Weekly servings, gram totals, occurrence-day counts, diversity counts, and shares use their explicitly named formulas below rather than a daily-average denominator.

### 5.3 Target compatibility

Target-dependent status requires one semantically identical target type/unit/value or lower/upper pair on every numeric day in that period. Multiple Target Plan IDs are allowed only when the resolved target document is identical. Otherwise the raw metric may be returned as `observed`, but target status is `target_incompatible` and `safety_flags` includes `incompatible_target`; PLAN 033 cannot select it.

Legacy-unversioned or absent target sources may provide display-only raw facts. They never create target-relative eligibility. A `very_low_energy_blocked` or `specialist_review_required` source suppresses target-relative analysis and adds the matching safety flag.

## 6. Exact v1 metric registry

Every ID below is closed for `w3-analysis-1.0.0`. Unknown IDs fail validation. All arithmetic uses unrounded source values and rounds only published facts to six decimal places using decimal half-even.

### 6.1 Daily averages

| Stable ID(s) | Unit | Source | Target/direction |
| --- | --- | --- | --- |
| `energy:calories_kcal_per_day` | `kcal/day` | scaled snapshot calories | effective Target Plan calories; range/maximum direction |
| `macro:protein_g_per_day`, `macro:carb_g_per_day`, `macro:fat_g_per_day` | `g/day` | scaled snapshot macros | effective Target Plan value/range |
| `nutrient:fiber_g`, `nutrient:added_sugar_g`, `nutrient:saturated_fat_g`, `nutrient:trans_fat_g`, `nutrient:sodium_mg`, `nutrient:potassium_mg`, `nutrient:cholesterol_mg`, `nutrient:calcium_mg`, `nutrient:iron_mg`, `nutrient:magnesium_mg`, `nutrient:zinc_mg`, `nutrient:selenium_mcg`, `nutrient:vitamin_b12_mcg`, `nutrient:folate_dfe_mcg`, `nutrient:vitamin_a_rae_mcg`, `nutrient:iodine_mcg` | Registry unit per day | matching supported snapshot field | exact effective Target Plan/Registry target; cholesterol is `monitor_only` |

Daily status is `below_target | at_target | within_target | above_target | observed | unavailable`. Exact equality is `at_target`. For minimum/recommended/adequate, below is adverse direction and at/above is within target. For maximum, above is adverse and at/below is within target. A range uses its closed endpoints.

### 6.2 Food-pattern metrics

Snapshot group contribution is scaled to the logged basis before these formulas.

| Stable ID | Value/unit | Exact formula | Target/direction |
| --- | --- | --- | --- |
| `group:fruit_vegetable_g_per_day` | g/day | average daily sum of eligible vegetable plus fruit contributions, excluding `starchy_root`; fruit-liquid contribution is capped at 150 ml-equivalent per date | 400 g/day minimum |
| `group:legumes_servings_per_period` | servings/7d | sum eligible legume contribution / 80 g | 3 minimum |
| `group:whole_grain_share_percent` | percent | `whole_known_g/(whole_known_g+refined_known_g)*100`; null when denominator zero | 50% minimum |
| `group:nuts_seeds_servings_per_period` | servings/7d | sum eligible contribution / 30 g; extracted oils excluded | 5 minimum |
| `group:seafood_servings_per_period` | servings/7d | sum eligible seafood contribution / 100 g | 2 minimum |
| `group:omega3_seafood_servings_per_period` | servings/7d | seafood contribution carrying `omega3_rich_seafood` / 100 g | 1 minimum |
| `group:dairy_fortified_servings_per_day` | servings/day | daily sum of each eligible subtype contribution divided by its Registry serving; fortified plant alternative requires the frozen trait/calcium rule | 2/day minimum |
| `group:red_meat_g_per_period` | g/7d | sum eligible red-meat contribution; processed poultry is excluded and classified as processed meat | 500 g maximum; 350 g is descriptive near-limit only |
| `group:processed_meat_occurrence_days` | days/7d | distinct complete dates with positive processed-meat contribution | `minimize`; no fabricated safe target |
| `group:sugar_sweetened_beverage_occurrence_days` | days/7d | distinct complete dates with positive sugar-sweetened-beverage contribution | `minimize`; no fabricated safe target |
| `group:sweets_occurrence_days` | days/7d | distinct complete dates with positive sweets contribution | `minimize`; display only in v1 |
| `protein:source_diversity_count` | sources/7d | count distinct keys among `legumes,nuts_seeds,seafood,eggs,poultry,red_meat,dairy_fortified_alternatives` with positive eligible contribution | `monitor_only`; no score or target |

For group metrics, an entry is known only when its supported snapshot contains valid group contribution data. Unknown group classification lowers that metric's entry coverage and contributes neither amount nor zero.

### 6.3 NOVA metrics

| Stable ID | Exact formula | Semantics |
| --- | --- | --- |
| `nova:nova4_calorie_share_percent` | `known_nova4_calories / calories_from_entries_with_reviewed_nova_1_to_4 * 100`; when known classified calories are exactly zero, value is zero | descriptive minimize pattern; no safe threshold |
| `nova:nova4_occurrence_days` | distinct complete dates containing positive calories from a reviewed NOVA 4 entry | descriptive minimize frequency |

Only reviewed classifications `1..4` are known. `unknown` or unreviewed lowers NOVA metric coverage. NOVA is never inferred from macros or ingredients.

### 6.4 Occurrence and contributor rules

One date contributes at most one to an occurrence-day metric. Serving and amount facts retain fractional values. Negative source facts are invalid.

A contributor is an opaque immutable Diary entry snapshot reference, never a mutable Food record or Food name. Each record contains `source_ref`, `diary_date`, `contribution_value`, `unit`, `source_version`, and relation `supports_observed_value`.

Return at most five contributors per period, sorted by:

1. absolute contribution descending;
2. Diary date ascending;
3. opaque UUID lowercase lexical ascending.

For occurrence metrics, select at most one entry per occurrence date: greatest positive contribution, then UUID lexical order. Unknown entries are never contributors. Contributor telemetry excludes the references entirely.

## 7. Comparison and persistence

### 7.1 Comparability

Both periods must have at least four complete days and metric coverage >=50. An improvement/worsening classification additionally requires both coverage values >=75 and absolute coverage difference <=10 percentage points.

If the source semantic versions differ, the metric unit changes, target semantics differ, or either period is stale/unsafe, comparison status is `not_comparable`. Raw current and previous facts remain separately visible when safe.

### 7.2 Material change

For target-bearing metrics:

```text
minimum adverse distance = max(1 - value/compatible_target_value, 0)
maximum adverse distance = max(value/compatible_target_value - 1, 0)
range adverse distance   = 0 inside the closed range, otherwise distance to nearest bound / that bound
normalized_delta         = round6(current_adverse_distance - previous_adverse_distance)
material                 = abs(normalized_delta) >= 0.10
```

For ranges, distance outside the nearest bound divided by that non-zero bound is the normalized value; inside range is zero. Target zero is invalid.

`improved` means the normalized adverse distance decreased by at least `0.10`; `worsened` means it increased by at least `0.10`; otherwise `no_material_change`. Equality at exactly `0.10` is material.

Monitor-only and minimize-without-target metrics never claim health improvement. They emit raw difference and `descriptive_increase | descriptive_decrease | no_material_change`; material thresholds are exactly one occurrence/source for integer metrics and five percentage points for NOVA calorie share. Daily cholesterol is always `descriptive_change` unless exactly equal.

No formula divides by the previous observed value; zero therefore cannot create an undefined percentage change.

### 7.3 Persistence

`persistence.kind` is `same_direction_two_period`. `qualifies=true` only when all are true:

1. both periods independently have >=4 complete days and coverage >=75;
2. both use compatible source/rule/unit/target semantics;
3. both finite values have the same directional status (`below_target` for positive gaps or `above_target` for maximum overages), or both frequency values meet the same closed occurrence predicate;
4. for positive nutrient/group gaps, each period value is <=80% of its target;
5. for numeric limit overage facts, each period value is > its maximum;
6. neither period nor source bundle has a safety/stale flag.

Severity may differ. A boundary value of exactly 80% qualifies as a gap; exactly the maximum does not qualify as overage. Missing previous evidence, target changes, rule incompatibility, or a superseded revision yields `qualifies=false` with an exact reason enum.

This persistence fact is evidence only. PLAN 033 retains authority for whether a persistent fact becomes a priority.

## 8. Analysis lifecycle and revision identity

### 8.1 Immutable series and revisions

An analysis series is owner-bound `(principal_id, as_of_diary_date, interface_version=1)` and owns stable `source_analysis_id`.

Each successful computation creates an immutable finalized revision document with revision integer starting at 1. Revision uniqueness is `(source_analysis_id, revision)`. The current pointer is mutable metadata on the series; the revision content is not.

Canonical `source_input_hash` is SHA-256 over sorted UTF-8 JSON containing:

- interface and analysis rules versions;
- captured date/windows/timezone;
- every PLAN 031 day status/version/count;
- every referenced immutable snapshot ID/schema/version and participating facts;
- every Target Plan reference and effective resolved target/safety fact;
- Registry/group/NOVA version bundle.

It excludes generated timestamps, database row IDs allocated for the revision, request IDs, and idempotency keys.

Canonical `content_hash` covers the complete stored analysis result plus `source_input_hash`, excluding server timestamps and lifecycle pointers.

### 8.2 Replay/no-op/new revision

| Condition | Result |
| --- | --- |
| same idempotency key and canonical command hash | exact stored HTTP response; no reads of current calendar/evidence |
| same series, same input hash, same rules version | return current revision as `no_change`; no row/event |
| same series, changed source input under supported original rules | create next revision, append supersession event, advance pointer once |
| captured date changed | another analysis series, revision 1 |
| rule version intentionally upgraded | create next revision under new version; preserve old revision |
| unsupported original version requested | fail `UNSUPPORTED_ANALYSIS_RULE_VERSION`; no mutation |

`generated_at` and `finalized_at` are Backend UTC timestamps. They do not affect deterministic calculation or no-op detection.

A completed evaluation idempotency record is retained for exactly seven days after `completed_at`; during that interval replay is byte-for-byte status/body/safe-header identical. The record is inserted only in the same successful commit as its revision/no-op response, so a rolled-back evaluation leaves no completed replay. After expiry, key reuse is a new command, but the source-input uniqueness rule still prevents a duplicate revision.

### 8.3 Stale and superseded state

Revision documents are immutable. Stale/superseded lifecycle is append-only in revision events:

- `day_reopened`;
- `day_version_changed`;
- `target_source_changed`;
- `source_snapshot_corrected`;
- `source_version_unsupported`;
- `superseded_by_revision`.

The projection derives `current | stale | superseded`. Marking stale appends an event and never updates the document. Creating a successor appends a supersession event and atomically moves the series pointer. A stale revision remains readable.

## 9. Original-version replay

Every revision stores:

- `analysis_rules_version`;
- Registry, calculation, group, source-reliability, NOVA and snapshot schema versions;
- Target Plan IDs, calculation document schema version and calculation/Registry versions;
- every PLAN 031 day version;
- canonical source input and content hashes.

`w3-analysis-1.0.0` is the first active analysis package. Dispatch is exact by version; there is no fallback to current rules. Semantic changes that can change a result require a new minor or major version under H10. Patch changes cannot affect output.

Historical read returns the stored finalized document after hash verification. Historical recomputation loads the exact original analysis package and compatible readers for every claimed source version. If any package/reader is unavailable, return `UNSUPPORTED_HISTORICAL_VERSION` and preserve the revision unchanged. A current Registry or Target Plan never reinterprets old evidence.

Every package/reader version referenced by a retained revision remains available for that revision's full retention period. Removing a referenced version is prohibited until all dependent revisions have passed approved retention/deletion; inability to dispatch still fails closed and never falls back.

PLAN 032 owns `analysis_rules_version`. PLAN 033 separately owns `weekly_priority_rules_version` and `weekly_priority_copy_version`; none substitutes for another.

## 10. Exact `WeeklyPriorityAnalysisInputV1`

The projection is immutable, `extra=forbid`, finite-number checked, and canonicalized with object keys sorted and every array sorted by its declared key.

```text
WeeklyPriorityAnalysisInputV1 {
  interface_version: 1
  principal_ref: UUID                         # authenticated Principal.id; opaque, server-populated, never client input/log field
  source_analysis_id: UUID
  source_analysis_revision: integer >= 1
  generated_at: UTC datetime
  as_of_diary_date: ISO date
  calendar_timezone: "Asia/Riyadh"
  period_start: ISO date
  period_end: ISO date
  previous_period_start: ISO date
  previous_period_end: ISO date
  analysis_rules_version: non-empty string
  nutrition_registry_version: non-empty string
  food_group_rules_version: non-empty string
  nova_rules_version: non-empty string
  snapshot_schema_versions: sorted unique integer[]
  target_plan_refs: TargetPlanAnalysisRefV1[]  # unique by id; sort effective_from, id
  days: AnalysisDayFactV1[7]                   # current dates ascending
  previous_period: AnalysisDayFactV1[7]        # previous dates ascending
  metric_facts: AnalysisMetricFactV1[]         # metric_key ascending
  safety_flags: AnalysisSafetyFlag[]            # lexical ascending, unique
}
```

`TargetPlanAnalysisRefV1` contains exactly `id:UUID`, `effective_from:date`, `effective_to:date|null`, `calculation_document_schema_version:integer>=1`, `calculation_engine_version:non-empty string`, `nutrition_registry_version:non-empty string`, `safety_outcome:normal|specialist_review_required|very_low_energy_blocked`, and `target_document_hash:64-character lowercase SHA-256 hex`. Raw Profile inputs are prohibited.

The closed projection intentionally does not add top-level calculation-engine or source-reliability fields that frozen PLAN 033 did not declare. PLAN 032 retains those identities in its internal revision source-version bundle; calculation identity also remains in each exact Target Plan reference. This preserves original-version replay without violating PLAN 033's `extra=forbid` input.

`principal_ref` is exactly the authenticated owner-bound `Principal.id` UUID already used in Backend ownership checks. It is opaque (not email/provider subject), derived only by the Backend, excluded from request bodies and operational logs, and must equal the Principal owning the analysis series, every day, Target Plan and evidence reference.

`AnalysisDayFactV1` contains exactly `date:date`, `logging_status:unregistered|partial|complete`, `logging_status_version:integer>=0`, `entry_count:integer>=0`, `analysis_eligible:boolean`, `completed_at:UTC datetime|null`, `snapshot_schema_versions:sorted unique integer[]`, and `metric_values:AnalysisDayMetricValueV1[]` sorted by `metric_key`. Partial/unregistered `metric_values` is empty. Each metric value contains exactly `metric_key:closed v1 string`, `value:finite decimal|null`, `value_state:known|explicit_zero|unknown`, `known_entry_count:integer>=0`, `total_entry_count:integer>=0`, `amount_qualifier:exact|at_least|unavailable`, and `unit:closed metric unit`. `explicit_zero` requires value `0`; `unknown` requires null; known counts cannot exceed totals.

`AnalysisMetricFactV1` contains:

```text
metric_key, metric_kind, unit, aggregation, direction,
target {type,value?,lower?,upper?,source_plan_ids[]} | null,
current PeriodMetricEvidenceV1,
previous PeriodMetricEvidenceV1,
comparison AnalysisComparisonV1,
persistence AnalysisPersistenceV1,
contributors {current[],previous[]}
```

Its exact enums are `metric_kind=daily_average|period_total|occurrence_days|share_percent|diversity_count|calorie_share`; `aggregation=average_numeric_days|sum_period|distinct_positive_dates|ratio_percent|distinct_source_count`; and `direction=minimum|maximum|range|minimize|monitor_only`. Target is null only for `minimize|monitor_only`; otherwise it contains exactly `type:minimum|maximum|range`, finite `value` for minimum/maximum or finite `lower,upper` with `lower<=upper` for range, and sorted unique UUID `source_plan_ids`.

`PeriodMetricEvidenceV1` contains exactly `value:finite decimal|null`, `value_state:known|explicit_zero|unknown`, `amount_qualifier:exact|at_least|unavailable`, `complete_day_count:integer 0..7`, `numeric_day_count:integer 0..complete_day_count`, `known_entry_count:integer>=0`, `total_entry_count:integer>=0`, `coverage_percent:decimal 0..100|null`, `confidence:strong|limited|unavailable`, `status:below_target|at_target|within_target|above_target|observed|target_incompatible|unavailable`, and sorted `evidence_refs:OpaqueEvidenceRefV1[]`. An evidence ref contains exactly `source_ref:UUID`, `diary_date:date`, `source_version:non-empty string`, and no Food/Profile text.

`AnalysisComparisonV1` contains exactly `status:improved|worsened|no_material_change|descriptive_increase|descriptive_decrease|descriptive_change|not_comparable`, `reason` from the closed comparison enum below, `difference:finite decimal|null`, and `normalized_adverse_delta:finite decimal|null`. `AnalysisPersistenceV1` contains exactly `kind:"same_direction_two_period"`, `qualifies:boolean`, and one closed reason below. Contributors contain exactly `source_ref:UUID`, `diary_date:date`, `contribution_value:finite non-negative decimal`, `unit:closed metric unit`, `source_version:non-empty string`, and `relation:"supports_observed_value"`; arrays are capped at five and use the ordering in section 6.4.

Comparison reasons are the closed enum `comparable | insufficient_complete_days | insufficient_coverage | limited_coverage | coverage_mismatch | target_incompatible | version_incompatible | invalid_target | stale_evidence | unavailable_value`. Persistence reasons are `qualified | current_not_qualifying | previous_not_qualifying | insufficient_complete_days | insufficient_coverage | target_changed | version_incompatible | stale_evidence | missing_previous`.

Safety flags are exactly:

```text
incompatible_target
incompatible_source_versions
invalid_day_evidence
missing_target
non_finite_source_fact
profile_specialist_review_required
stale_evidence
unsupported_analysis_rules
unsupported_food_group_rules
unsupported_nova_rules
unsupported_registry
unsupported_snapshot_schema
very_low_energy_blocked
```

Invalid ordering, dates, uniqueness, versions, bounds, hashes, finite checks, or source ownership makes the projection unavailable. PLAN 033 must not reconstruct, repair, or partially accept it.

## 11. API contract

All routes require owner authentication and derive Principal from the bearer identity.

| Method/path | Request | Success | Concurrency/idempotency |
| --- | --- | --- | --- |
| `GET /progress/nutrition-analysis/current` | none | `200 NutritionPatternAnalysisResponseV1`; `404 ANALYSIS_NOT_FOUND` before first evaluation | ETag `"analysis-{id}-r{revision}"`; no mutation |
| `GET /progress/nutrition-analysis/history?cursor=&limit=20` | cursor, limit 1–100 | newest-first bounded `NutritionPatternAnalysisHistoryPageV1` | stable `(as_of_date DESC,id DESC)` cursor |
| `GET /progress/nutrition-analysis/{analysis_id}/revisions/{revision}` | path | exact immutable `NutritionPatternAnalysisResponseV1` | cross-owner/unknown is identical `404 RESOURCE_NOT_FOUND` |
| `POST /progress/nutrition-analysis/evaluate` | `AnalysisEvaluateCommandV1 {expected_current_revision:int|null}`, `Idempotency-Key`, required `If-Match` | `201` new revision or `200` no-change/replay | one captured date for new execution; exact replay; stale precondition is 409 |
| `GET /admin/nutrition-analysis/monitoring?iso_week=` | bounded ISO week | aggregate counts/status/version/latency bands only | Admin GET-only; no owner facts or command route |

`NutritionPatternAnalysisResponseV1` contains exactly `source_analysis_id:UUID`, `source_analysis_revision:integer>=1`, `lifecycle_status:current|stale|superseded`, `stale_reasons:sorted unique event enum[]`, `as_of_diary_date:date`, `period_start:date`, `period_end:date`, `previous_period_start:date`, `previous_period_end:date`, `complete_day_count:integer 0..7`, `previous_complete_day_count:integer 0..7`, `metric_summaries:AnalysisMetricFactV1[]`, `source_versions:AnalysisSourceVersionBundleV1`, `priority_input:WeeklyPriorityAnalysisInputV1`, `generated_at:UTC datetime`, `finalized_at:UTC datetime`, and `etag:string`. It excludes raw Profile inputs, Food names, notes, ingredients, idempotency keys, and provider data.

`AnalysisSourceVersionBundleV1` contains exactly the internal versions enumerated in section 9 and their content hashes. `NutritionPatternAnalysisHistoryPageV1` contains exactly `items:NutritionPatternAnalysisHistoryItemV1[]`, `next_cursor:string|null`; each item contains identity/revision, lifecycle status, as-of date, both period bounds, analysis rules version, complete-day counts, generated/finalized timestamps and ETag, but no metric/evidence values. The current and exact-revision endpoints return `NutritionPatternAnalysisResponseV1`; evaluation returns the same schema plus HTTP result semantics from the route table. Admin monitoring contains only `iso_week`, total/status/version/complete-day-band/coverage-band/stale-reason/latency-band counts, all non-negative integers.

For evaluation, `If-Match` is exactly `"analysis-none"` when `expected_current_revision=null`, otherwise it is the current ETag `"analysis-{source_analysis_id}-r{expected_current_revision}"`. Header/body disagreement is `400 INVALID_ANALYSIS_PRECONDITION`; a well-formed but stale value is `409 ANALYSIS_VERSION_CONFLICT`. A completed exact idempotent replay is returned before current-state precondition evaluation, so an ambiguous retry remains stable after another revision exists.

Stable errors:

| HTTP | Code | Meaning |
| ---: | --- | --- |
| 400 | `INVALID_IDEMPOTENCY_KEY` | malformed command key |
| 400 | `INVALID_ANALYSIS_PRECONDITION` | missing/malformed `If-Match` or header/body disagreement |
| 404 | `ANALYSIS_NOT_FOUND` | current owner has no analysis |
| 404 | `RESOURCE_NOT_FOUND` | unknown/cross-owner exact identity |
| 409 | `ANALYSIS_VERSION_CONFLICT` | expected current revision changed |
| 409 | `IDEMPOTENCY_KEY_REUSED` | same key, different canonical command |
| 409 | `ANALYSIS_SOURCE_CHANGED` | locked source differs from validated bundle; retry as new command |
| 409 | `ANALYSIS_RETRY_REQUIRED` | PostgreSQL serialization/deadlock aborted the whole transaction; retry same command/key |
| 422 | `INSUFFICIENT_ANALYSIS_EVIDENCE` | no successful revision; safe availability detail |
| 422 | `UNSUPPORTED_ANALYSIS_RULE_VERSION` | exact rules package unavailable |
| 422 | `UNSUPPORTED_HISTORICAL_VERSION` | original source reader/package unavailable |
| 422 | `INVALID_ANALYSIS_SOURCE` | malformed/inconsistent/non-finite source bundle |
| 500 | `ANALYSIS_EVALUATION_FAILED` | generic request-ID envelope; no source facts |

Errors use approved neutral Arabic display messages in the API copy catalog; they never disclose another Principal's record existence.

## 12. Privacy, security, safety, and UX

- Every table and query is Principal-bound; owner IDs never come from payloads.
- Cross-owner UUIDs return the same 404 as absent UUIDs.
- Admin sees aggregate bands only: evaluation count/status, rules version, complete-day band, coverage band, stale reason, and latency band.
- Operational logs contain request ID, opaque Principal/analysis ID, revision, result/error code, version and latency bucket. They exclude metric values, targets, evidence IDs, Food/Profile content, Diary dates finer than ISO week, contributor IDs, and idempotency keys.
- Contributor responses use opaque snapshot references and numeric contribution only; Food names, notes and ingredients are absent.
- Analysis describes recorded patterns, never diagnosis, treatment, disease risk, medication or supplement direction.
- Missing/unsafe/unsupported inputs produce neutral unavailable states and suppress downstream priority eligibility.
- The exact Arabic copy catalog is: heading `تحليل نمط التغذية`; loading `جارٍ تحليل نمط التغذية`; insufficient evidence `التحليل غير متاح لعدم كفاية الأيام المكتملة`; limited evidence `البيانات محدودة لهذا العنصر`; stale revision `تغيرت بعض البيانات منذ هذه النسخة`; unsupported replay `تعذر فتح هذه النسخة بإصدارها الأصلي`; generic retryable failure `تعذر تحديث التحليل. حاول مرة أخرى`; evaluate action `تحديث التحليل`; history heading `سجل تحليلات نمط التغذية`. Copy changes require a separately versioned approved catalog; implementations may not improvise clinical or judgmental wording.
- UI uses headings plus text/icons, not color alone; charts require a table/text alternative. Loading uses `aria-busy`; initial failures use `role=alert`; stale status is named. Focus moves to the analysis heading on successful refresh and to the alert/retry control on error. Dates/numbers use `<bdi>`. RTL, reduced motion, 320/360/390/430px layouts and 44x44 targets are mandatory.

## 13. PostgreSQL persistence and migration design

One additive migration after the implementation-time Alembic head creates:

### `nutrition_analysis`

Logical series: `id`, `principal_id`, `as_of_diary_date`, `calendar_timezone`, `interface_version`, nullable current revision ID/number, timestamps. Unique `(principal_id,as_of_diary_date,interface_version)`; owner composite identity; timezone check.

### `nutrition_analysis_revision`

Immutable revision: series/owner, positive revision, both windows, rules/version bundle, source input hash, content hash, complete/partial/unregistered counts, result status/reason, canonical analysis document JSON, generated/finalized UTC timestamps, nullable supersedes revision ID. Unique `(analysis_id,revision)`, unique `(analysis_id,source_input_hash,analysis_rules_version)`, finite/bounded JSON schema checks, exact seven-day date checks, owner composite FKs.

### `nutrition_analysis_evidence_ref`

Immutable references: revision/owner, period enum, Diary date, day version, entry/snapshot opaque ID, snapshot schema version, metric key, source version, finite value/null state, unit. Unique evidence identity; index `(principal_id,diary_date DESC)`; no Food text/Profile inputs.

### `nutrition_analysis_revision_event`

Append-only lifecycle: revision/owner, event enum, optional successor revision, reason, source day version, occurred UTC time, request ID. Unique event identity prevents duplicate stale/supersession events. No metric facts.

### `nutrition_analysis_command_idempotency`

Principal, operation, HMAC key digest, canonical command hash, captured date, analysis/revision binding, committed status/safe headers/response and timestamp. Unique `(principal_id,operation,key_digest)`. Raw keys are never persisted/logged.

Indexes support current owner/date, newest history, exact revision, stale-event lookup, evidence by date, and command replay. FKs use `ON DELETE RESTRICT` until the approved deletion workflow removes the graph.

Upgrade creates empty structures only; no historical analysis is inferred or backfilled. Readers deploy before writers. Existing Diary, Target Plan and snapshot rows are unchanged.

Application rollback leaves additive tables intact. Alembic downgrade is mechanically permitted only when all five tables are empty. Otherwise it fails closed after printing aggregate row counts and never destroys analysis history. Empty downgrade drops objects in reverse dependency order.

Retention is 24 months after period end, extended while a retained PLAN 033 recommendation/goal references the revision. Deletion follows the approved owner-deletion workflow; aggregate non-identifying metrics cannot reconstruct a person.

## 14. Concurrency and transaction contract

For a new evaluation:

1. validate key shape and lookup completed Principal-scoped idempotency result;
2. capture one calendar snapshot;
3. lock Principal;
4. lock/create the analysis series for captured date;
5. validate expected current revision;
6. read and lock the fourteen PLAN 031 day-status rows in date order;
7. read immutable Diary snapshots and effective Target Plans in date/UUID order;
8. compute and validate the canonical source input/hash in memory;
9. recheck locked day/target source versions;
10. no-op on identical hash, otherwise allocate next revision;
11. insert revision/evidence/event/idempotency result and advance current pointer;
12. commit once.

PLAN 032 performs no automatic retry after any semantic, version, serialization, or deadlock conflict. A PostgreSQL serialization/deadlock abort rolls back the entire transaction and returns `409 ANALYSIS_RETRY_REQUIRED`; the caller may retry with the same idempotency key, which reruns from one new calendar capture unless an exact committed replay exists. No timeout or retry may conceal an application conflict.

Two evaluations for the same Principal/date serialize on Principal then series; one creates the revision and the other returns no-change or version conflict according to its precondition. Reopen/finalize serialize on Principal then day rows then series, preventing inverted order. A stale event racing with successor creation is appended once and linked deterministically. PostgreSQL tests, not SQLite, certify these schedules.

## 15. Shadow, observability, rollout, and rollback

PLAN 032 shadow mode may evaluate and persist revisions while its user-facing analysis remains disabled. Its correctness evidence includes status/result counts, metric availability/coverage bands, version, stale reasons, comparison class, latency bucket, deterministic mismatch count, and human-review sample disposition. It excludes owner/evidence IDs and exact values.

PLAN 032 does not own or weaken PLAN 033's launch threshold. It must expose privacy-safe aggregate evidence so PLAN 033 can later prove at least 28 consecutive days and 1,000 eligible evaluations under its own frozen selector gate.

PLAN 032 launch needs separate authorization. Immediate rollback disables new evaluation/display, preserves read-only historical revisions, leaves Diary/Target/Profile untouched, and never rewrites evidence. Any cross-owner disclosure, unknown-to-zero conversion, version fallback, history mutation, nondeterministic mismatch, or source-hash failure is a rollback trigger.

## 16. Golden, mutation, and future acceptance gates

The companion corpus freezes windows, coverage, zero/null, current/previous comparison, material thresholds, persistence, contributor ordering, version failures, immutable identities, revision behavior and downstream projection. The standard-library verifier computes results independently from the expected JSON.

Independent mutations must be rejected for:

1. wrong Riyadh window boundary;
2. Sunday-aligned substitution;
3. unknown-to-zero corruption;
4. wrong coverage denominator;
5. current/previous swap;
6. changed material threshold;
7. one-period persistence;
8. nondeterministic contributor tie order;
9. accepted unsupported version;
10. in-place finalized revision mutation.

Future implementation acceptance requires production logic replay of every golden vector, independent property/mutation tests, PostgreSQL concurrency schedules, migration upgrade/empty downgrade/populated fail-closed downgrade, exact OpenAPI, Principal isolation, query/runtime budgets, Arabic/axe/keyboard/mobile/RTL behavior, original-version replay, and deterministic generation.

## 17. Cross-plan compatibility

### PLAN 031 → PLAN 032: PASS

PLAN 032 consumes the exact PLAN 031 status vocabulary, single captured calendar, version, entry count, complete/reopen behavior and empty-complete semantics. It neither completes a day nor redefines partial/unregistered.

### PLAN 032 → PLAN 033: PASS

The projection provides every frozen PLAN 033 input field with stricter exact typing: opaque Principal, 7+7 dates, immutable source identity/revision, non-null analysis version, source versions, Target Plan references, day facts, current/previous metric evidence, coverage, persistence, contributors and sorted safety flags. PLAN 033 requires no raw Diary read or analysis recomputation.

Version ownership remains separate: PLAN 032 `analysis_rules_version`; PLAN 033 priority/copy versions.

## 18. Decision completeness and implementation boundary

There are no unresolved formulas, denominators, thresholds, lifecycle choices, identity rules, version fallbacks, migration rules, API routes, concurrency orders, privacy boundaries, or downstream fields in this v1 design.

Implementation remains unauthorized. A later read-only gate must derive exact implementation paths from this frozen design. That later scope is expected to include Backend rule/version ownership, models/schemas/services/routes, one additive migration, PostgreSQL/concurrency/migration/OpenAPI tests, committed generated frontend contracts if exposed, analysis UI/domain/tests, and architecture/CI paths only when repository discovery proves they are necessary.
