# Wave 3 Weekly Priority and Behavior Goal Design Contract

**PLAN 033 Design version:** 1.1 (H2 trackability-gated refreeze candidate)

**Amendment reason:** H2 semantic-observability correction discovered during formal implementation review.

**Version disposition:** `w3-priority-1.0.0` and `w3-priority-ar-1.0.0` are withdrawn pre-release. They were never accepted on `main`, migrated to a shared database, deployed, or activated. Design 1.1 supports only `weekly_priority_rules_version="w3-priority-1.1.0"` and `weekly_priority_copy_version="w3-priority-ar-1.1.0"`; there is no alias, fallback, or historical dispatch obligation for either withdrawn version. Public `schema_version=1` remains the first authoritative release candidate because no PLAN 033 public schema has shipped.

## 0. Design 1.1 H2 amendment

### 0.1 Priority validity and goal trackability

All 23 priority rules and all 28 action keys remain valid and retain their selector tier, severity, coverage, persistence, taxonomy order, conflicts, cap, safety, target, stale, and supersession semantics. Trackability is evaluated only after a valid action is selected and never changes rank. A selected main or secondary may therefore be `informational_only`.

`PriorityV1.goal_trackability` is the required closed enum `trackable|informational_only`. `PriorityV1.goal_unavailable_reason` is the closed enum `action_not_observable|null`. `trackable` requires a null reason; `informational_only` requires `action_not_observable`. No default or free-form reason exists.

`informational_only` means only that current persisted `WeeklyPriorityAnalysisInputV1` evidence cannot truthfully verify the desired behavior. It does not mean low confidence, invalid or unsafe advice, unavailable evidence, failure, or zero progress. The exact governed Arabic explanation under `w3-priority-ar-1.1.0` is:

> هذه الأولوية إرشادية حاليًا؛ لا يمكن تتبع تنفيذ هذه الخطوة تلقائيًا من بيانات اليوميات.

No informational-only action creates an offered/deferred/hidden/disabled goal, progress document, reminder namespace, goal command/idempotency row, completion, repeat, or reduce flow. The priority and its existing action copy remain visible. The UI shows neither a disabled Start Goal button nor a progress bar or percentage.

### 0.2 Closed 28-action catalog

| Rule | Mode | Action key | Trackability | Reason |
| --- | --- | --- | --- | --- |
| sodium_overage | replace | replace_high_sodium_choice | informational_only | action_not_observable |
| added_sugar_overage | replace | replace_added_sugar_choice | informational_only | action_not_observable |
| saturated_fat_overage | replace | replace_saturated_fat_choice | informational_only | action_not_observable |
| trans_fat_overage | replace | replace_trans_fat_choice | trackable | null |
| processed_meat_frequency | replace | replace_processed_meat_choice | trackable | null |
| sugary_drink_frequency | replace | replace_sugary_drink_choice | informational_only | action_not_observable |
| fruit_vegetable_gap | add | add_fruit_or_vegetable | trackable | null |
| fruit_vegetable_gap | replace | replace_with_fruit_or_vegetable | trackable | null |
| legumes_gap | add | add_legumes | trackable | null |
| legumes_gap | replace | replace_with_legumes | trackable | null |
| whole_grain_share_gap | replace | replace_with_whole_grain | informational_only | action_not_observable |
| nuts_seeds_gap | add | add_nuts_or_seeds | informational_only | action_not_observable |
| nuts_seeds_gap | replace | replace_with_nuts_or_seeds | informational_only | action_not_observable |
| seafood_gap | replace | replace_with_seafood | trackable | null |
| dairy_alternative_gap | add | add_dairy_or_fortified_alternative | trackable | null |
| dairy_alternative_gap | replace | replace_with_dairy_or_fortified_alternative | trackable | null |
| fiber_gap | add | add_fiber_source | informational_only | action_not_observable |
| fiber_gap | replace | replace_with_fiber_source | informational_only | action_not_observable |
| potassium_gap | review | review_food_sources_potassium | informational_only | action_not_observable |
| calcium_gap | review | review_food_sources_calcium | informational_only | action_not_observable |
| iron_gap | review | review_food_sources_iron | informational_only | action_not_observable |
| magnesium_gap | review | review_food_sources_magnesium | informational_only | action_not_observable |
| zinc_gap | review | review_food_sources_zinc | informational_only | action_not_observable |
| selenium_gap | review | review_food_sources_selenium | informational_only | action_not_observable |
| vitamin_b12_gap | review | review_food_sources_vitamin_b12 | informational_only | action_not_observable |
| folate_dfe_gap | review | review_food_sources_folate_dfe | informational_only | action_not_observable |
| vitamin_a_rae_gap | review | review_food_sources_vitamin_a_rae | informational_only | action_not_observable |
| iodine_gap | review | review_food_sources_iodine | informational_only | action_not_observable |

The split is exactly 9 trackable and 19 informational-only.

### 0.3 Closed producer-backed predicates

Predicates use only persisted `WeeklyPriorityAnalysisInputV1.days`. A date participates only inside the goal window and optional scheduled mask, with `logging_status=complete` and `analysis_eligible=true`. Partial/unregistered dates and unknown facts never qualify. One date contributes at most once.

| Action(s) | Exact date predicate |
| --- | --- |
| replace_trans_fat_choice | Non-empty date; `nutrient:trans_fat_g` (`g/day`) is `explicit_zero`, value 0, `exact`, total entries >0, and known entries equal total entries. |
| replace_processed_meat_choice | Date-local `protein:source_diversity_count` is known and >0. Its closed sources are legumes, nuts/seeds, seafood, eggs, poultry, red meat, and dairy/fortified alternatives; processed meat is excluded. |
| add_fruit_or_vegetable; replace_with_fruit_or_vegetable | Date-local `group:fruit_vegetable_g_per_day` is known and >0. |
| add_legumes; replace_with_legumes | Date-local `group:legumes_servings_per_period` is known and >0. Although named per-period, each day projection is calculated solely from that date's immutable entries. |
| replace_with_seafood | Date-local `group:seafood_servings_per_period` is known and >0 under the same per-day projection rule. |
| add_dairy_or_fortified_alternative; replace_with_dairy_or_fortified_alternative | Date-local `group:dairy_fortified_servings_per_day` is known and >0; PLAN 032 owns subtype serving and calcium-fortification rules. |

Add and replacement variants share the desired-category appearance predicate but retain distinct action identities and replacement-over-addition selection. No approximate predicate exists for the 19 informational actions: reduction/target status does not prove replacement; period share does not prove date-local appearance; unqualified nuts, `fiber_g>0`, and micronutrient ingestion do not prove the approved behavior or owner review. Tier-3 review actions remain informational without self-report/checkbox.

### 0.4 API, lifecycle, history, and shadow consequences

A goal offer requires a selected, fresh, supported, safe, trackable current main plus all existing eligibility rules. For an informational-only main with no earlier valid tracked goal, `GET /progress/behavior-goals/current` returns `goal=null`, the structured current priority, and `goal_unavailable_reason=action_not_observable`. Silent null and fake zero progress are forbidden.

Offer, accept, edit, defer, goal rejection, progress, completion, pause/resume, reminders, repeat, and reduce are not applicable because no goal exists. Recommendation-level rejection/suppression remains unchanged. An accepted tracked goal is never rewritten by a later informational recommendation; it follows existing stale/supersession and change/end rules. Repeat/reduce additionally require a trackable matching current main, otherwise no successor is created.

Every immutable recommendation stores rules/copy versions, action key/mode, trackability/reason, stored Arabic action and informational copy, and producer interface/rules/source/Registry versions. Historical rendering uses stored values; future producer evidence never retroactively changes them.

Shadow reporting separately counts selected recommendations, selected trackable mains, and selected informational-only mains. An eligible evaluation remains a valid supported/safe selector evaluation regardless of trackability. The launch gate remains >=28 consecutive shadow days and >=1,000 eligible evaluations; subdivisions neither lower nor replace that denominator. Informational recommendations never count as goal offers.

Additional producer evidence may increase future coverage only through a separate PLAN 032 lifecycle. No `WeeklyPriorityAnalysisInputV2` or `w3-analysis-1.2.0` is reserved or activated here.

**Status:** Frozen for implementation — design gate complete; no implementation or launch performed
**Decisions:** PD-017, PD-018, PD-027
**Design version:** 1.0-frozen
**Repository baseline:** `de736c6cb681c652fb17244cebad64f62665f487`
**Dependency:** Plan 031 is frozen and implemented at the repository baseline
**Authority:** Backend deterministic rules; AI and Frontend are never decision authorities

## 1. Purpose, boundary, and invariants

This frozen contract defines a closed Backend-owned weekly priority selector and an optional owner-controlled behavior-goal lifecycle. The design artifact itself adds no routes, models, UI, reminders, notifications, or runtime behavior.

Invariants:

1. A result contains zero or one main priority and zero or one justified secondary priority.
2. The selector is deterministic for the same versioned input. Runtime copy is limited to approved versioned templates. AI rephrasing is not authorized; every copy change requires the affected approvals and a copy-version bump.
3. Priority order is limit/minimize repeated overage, actionable positive gap, then persistent micronutrient gap.
4. Missing evidence is never zero. Only PLAN 031 `complete` days are analysis evidence; `partial` and `unregistered` are excluded. An explicitly empty complete day is valid zero-intake evidence.
5. A priority cannot override Profile/Target Plan safety, a Registry exclusion, or insufficient/stale evidence.
6. The Frontend renders the structured result and sends owner actions; it does not reconstruct or alter the decision.
7. At most one owner-bound primary goal is active. Progress is derived from Diary evidence, never a manual success checkbox.
8. Rejection suppresses an equivalent offer until new evidence exists. Reminders remain capped and optional.
9. There is no diagnosis, treatment, unified score, XP, points, punitive streak, or reward for under-eating.

## 2. Baseline evidence and closed analysis input interface

### 2.1 Mapped authorities

| Concern | Baseline authority | Required Wave 3 input |
| --- | --- | --- |
| Owner | authenticated `PrincipalContext` | opaque `principal_id` internal only; never accepted from client |
| Diary calendar | Backend `Asia/Riyadh` calendar | one captured `as_of_diary_date` per evaluation |
| Day evidence | PLAN 031 daily/weekly projection | date, `logging_status`, `logging_status_version`, `entry_count`, `analysis_eligible`, `completed_at` |
| Nutrition facts | immutable Diary snapshots and aggregation | metric values, known/total counts, coverage, qualifiers, contributor references |
| Targets/safety | effective Target Plan and Profile calculation | target values/types, target-plan ID/version, `safety_outcome`, goal mode, energy relation |
| Taxonomy | Backend Registry | nutrient/group/NOVA/trait keys and independent version fields |
| Rules | `backend/app/nutrition_rules/versions.py` | non-null recommendation/analysis version only after implementation approval |
| Notifications | none implemented | goal preference and delivery receipt only in a later authorized implementation |

The historical baseline had `analysis_rules_version=null` and `analysis_rules_status=reserved_for_wave_3`. PLAN 032 Design 1.1 now supplies persisted `WeeklyPriorityAnalysisInputV1.interface_version=1` under `w3-analysis-1.1.0`; this contract does not alter PLAN 032.

### 2.2 `WeeklyPriorityAnalysisInputV1`

The future analysis owner must provide this closed immutable document to the selector. Plan 032 may choose its internal storage, but must emit this interface exactly.

| Field | Type | Rule |
| --- | --- | --- |
| `interface_version` | literal `1` | reject unknown versions |
| `principal_ref` | opaque UUID | Backend-populated; excluded from client payload/logs |
| `period_start`, `period_end` | ISO date | rolling seven dates ending at captured date |
| `previous_period_start`, `previous_period_end` | ISO date | immediately preceding seven dates |
| `as_of_diary_date` | ISO date | one PLAN 031 calendar snapshot |
| `calendar_timezone` | literal `Asia/Riyadh` | no browser-derived calendar |
| `generated_at` | UTC datetime | freshness reference, not a ranking tie-breaker |
| `source_analysis_id`, `source_analysis_revision` | UUID, integer >= 1 | immutable evidence reference |
| `analysis_rules_version` | non-empty string | version used to aggregate inputs |
| `nutrition_registry_version`, `food_group_rules_version`, `nova_rules_version`, `snapshot_schema_versions` | string/string/string/sorted non-empty list | independent source versions |
| `target_plan_refs` | sorted array | IDs, effective date ranges, calculation version, safety outcome; no raw Profile inputs |
| `days` | exactly seven sorted records | PLAN 031 fields plus metric facts; dates unique and consecutive |
| `previous_period` | exactly seven sorted records | same evidence semantics |
| `metric_facts` | sorted unique records by `metric_key` | current/previous value, target, target type, direction, complete-day count, coverage, persistence, contributor refs |
| `safety_flags` | sorted unique enum list | closed exclusions described below |

Input validation fails closed with `no_priority` reason `invalid_analysis_input` when dates, versions, ordering, uniqueness, finite values, source references, or coverage bounds are invalid. A source analysis older than 36 hours relative to the captured Diary date boundary is stale. A source revision superseded before selection is `superseded_analysis`. Either condition yields no priorities and no goal offer until recomputation.

Coverage is metric-specific: `known_entry_count / total_entry_count * 100` across complete non-empty days. The structured current-period interface contains exactly seven unique, sorted, consecutive Diary dates. A complete empty day adds an analysis day and exact zero but no unknown entry to the coverage denominator. A complete non-empty day with a finite known metric contributes its value; a complete non-empty day whose metric is unknown contributes no numeric value and is excluded from the numeric average denominator while its unknown entries reduce coverage. `partial` and `unregistered` values are excluded entirely. For every complete day, `0 <= known_metric_entry_count <= entry_count`. `complete_day_count` must be at least four. Strong evidence requires coverage >= 75%; 50–74.99% can be displayed only as limited analysis and cannot enter the selector; below 50% is unavailable. Consequently every selected priority uses coverage >= 75%.

Privacy and failure rules:

- Evidence references contain opaque entry/snapshot IDs and aggregate numeric facts, never Food free text, ingredients, notes, email, token, idempotency key, or raw Profile fields.
- Cross-Principal references fail closed and are security-audited without exposing the other record.
- Unsupported versions, non-finite numbers, inconsistent targets, and unavailable registries yield no recommendation; the Frontend receives a stable reason, not partial invented output.
- Deterministic serialization sorts maps by key and arrays by their declared stable key; timestamps never affect ranking.

## 3. Closed priority vocabulary and selector

### 3.1 Priority keys

No implementation may accept an arbitrary key. The version-1 vocabulary and stable taxonomy order are:

| Order | Tier | Priority key | Evidence dimension | Approved practical action key |
| ---: | --- | --- | --- | --- |
| 10 | limit | `sodium_overage` | sodium maximum | `replace_high_sodium_choice` |
| 20 | limit | `added_sugar_overage` | added-sugar maximum | `replace_added_sugar_choice` |
| 30 | limit | `saturated_fat_overage` | saturated-fat maximum | `replace_saturated_fat_choice` |
| 40 | limit | `trans_fat_overage` | trans-fat strict maximum | `replace_trans_fat_choice` |
| 50 | limit | `processed_meat_frequency` | processed-meat minimize occurrences | `replace_processed_meat_choice` |
| 60 | limit | `sugary_drink_frequency` | sugar-sweetened-beverage occurrences | `replace_sugary_drink_choice` |
| 110 | positive | `fruit_vegetable_gap` | combined grams/day | `replace_with_fruit_or_vegetable` or `add_fruit_or_vegetable` |
| 120 | positive | `legumes_gap` | weekly servings | `replace_with_legumes` or `add_legumes` |
| 130 | positive | `whole_grain_share_gap` | known-grain share | `replace_with_whole_grain` |
| 140 | positive | `nuts_seeds_gap` | weekly servings | `replace_with_nuts_or_seeds` or `add_nuts_or_seeds` |
| 150 | positive | `seafood_gap` | weekly servings | `replace_with_seafood` |
| 160 | positive | `dairy_alternative_gap` | daily servings | `replace_with_dairy_or_fortified_alternative` or `add_dairy_or_fortified_alternative` |
| 170 | positive | `fiber_gap` | fiber minimum | `replace_with_fiber_source` or `add_fiber_source` |
| 210–300 | micronutrient | `potassium_gap`, `calcium_gap`, `iron_gap`, `magnesium_gap`, `zinc_gap`, `selenium_gap`, `vitamin_b12_gap`, `folate_dfe_gap`, `vitamin_a_rae_gap`, `iodine_gap` | matching Registry target | `review_food_sources_<metric>` |

`monitor_only` metrics, calories alone, cholesterol, unknown Registry keys, and inferred medical conditions are never priority candidates. A changed vocabulary requires a rules-version bump, Registry mapping, exclusion/conflict entry, Arabic copy, golden row, and Safety approval.

### 3.2 Exact eligibility and severity

All comparisons use decimal arithmetic and round half-even to six decimals only after computing the raw ratio.

- Common gate: valid/fresh current analysis; at least four complete days; metric coverage >= 75%; finite value and target; actionable key; no safety exclusion.
- Limit numeric: the metric exceeds its upper/maximum by >= 10% on at least two distinct complete days. `severity=(current_average-upper)/upper`.
- Limit frequency: processed meat or sugar-sweetened beverages occur on at least two distinct complete days. `severity=occurrence_days/complete_days`.
- Positive: the current value is <= 80% of its positive target. `severity=(target-current)/target`. A target of zero or missing target is invalid.
- Micronutrient: the positive rule also holds independently in the current and previous rolling periods, both periods have at least four complete days and >=75% metric coverage, and persistence is therefore two weeks. Severity is the smaller of the two gap ratios.
- Known zero follows the same arithmetic. Missing, partial, or unregistered evidence never creates a candidate.

Confidence is `strong` for selected candidates because the selector excludes lower coverage. The payload may report limited analysis separately, but it cannot label that result a priority.

### 3.3 Ordered selection and cap

Deterministic Backend pseudocode:

```text
validate input and versions; on failure return none(reason)
build candidates only from the closed vocabulary
apply common and tier-specific eligibility
if calories_relation == above_target:
  discard action_mode=add candidates
  retain their closed replacement variants when evidence is otherwise identical
sort by (tier 1/2/3, severity DESC, coverage DESC, taxonomy_order ASC, rule_key ASC)
main = first candidate, else none(no_eligible_priority)
secondary = first remaining candidate satisfying every secondary rule, else null
return immutable structured result with at most main + secondary
```

Secondary justification is derived, never supplied by a candidate or client. The Backend admits the first remaining candidate only when every rule is true: `severity >= 0.25`; distinct conflict group and evidence dimension; no direct conflict; distinct action key; strong evidence; and no addition while calories are above target. A secondary never exists without a main. The cap is applied after conflict resolution and cannot be configured upward.

### 3.4 Conflict and exclusion matrix

| Pair/condition | Result |
| --- | --- |
| Same evidence dimension or same conflict group | keep higher-ranked only |
| `added_sugar_overage` with `sugary_drink_frequency` sourced by same beverages | keep `added_sugar_overage`; disclose excluded duplicate |
| `saturated_fat_overage` with a dairy or meat addition action | suppress addition; replacement action only |
| `sodium_overage` with processed-meat evidence | main by normal rank; the other may be secondary only with distinct contributors/actions |
| Fruit/vegetable and fiber gaps with same top contributors | keep larger normalized severity; taxonomy order resolves exact tie |
| Any positive addition while calories are above target | use closed replacement variant; if none, exclude |
| Micronutrient against limit priority | micronutrient may be secondary only if persistent and its food-source action does not worsen the limit |
| Safety flag `very_low_energy_blocked`, active clinical exclusion, incompatible target, unsupported version, stale/superseded analysis | no priority and no goal offer |
| All candidates below gates | explicit `none` with reason `no_eligible_priority` |

Excluded alternatives are stored as `{rule_key, reason_code}` sorted by rule key. Allowed reason codes are `lower_rank`, `duplicate_evidence`, `action_conflict`, `addition_replaced`, `insufficient_coverage`, `insufficient_persistence`, and `safety_exclusion`; excluded raw health data is not stored.

## 4. Versioned result, copy, and historical reconstruction

### 4.1 Versions and immutable result

The frozen independent versions are:

- `weekly_priority_rules_version="w3-priority-1.1.0"` for eligibility, severity, ordering, conflicts, and cap;
- `weekly_priority_copy_version="w3-priority-ar-1.1.0"` for Arabic titles, reasons, actions, and safety copy;
- input `analysis_rules_version` supplied by the Plan 032 analysis authority;
- existing Registry, group, NOVA, calculation, Target Plan, and snapshot versions retained independently.

`WeeklyPriorityResultV1` is an immutable Backend response and persistence payload:

```text
schema_version=1
recommendation_id, principal-bound analysis_ref/revision
period_start, period_end, generated_at, expires_at
status = selected | none | stale | superseded | safety_suppressed
rules_version, copy_version, all source version fields
main: PriorityV1 | null
secondary: PriorityV1 | null
excluded_alternatives: sorted [{rule_key, reason_code}]
none_reason: closed enum | null
```

Each `PriorityV1` contains `rule_key`, `rank` (`main|secondary`), `category`, `title_ar`, `reason_ar`, `confidence="strong"`, `coverage_percent`, `complete_day_count`, `action_key`, `action_ar`, `action_mode`, required `goal_trackability`, required `goal_unavailable_reason`, `rules_version`, `copy_version`, sorted `facts_used`, sorted opaque `evidence_refs`, and sorted conflict decisions. `facts_used` uses typed `{metric_key,value,unit,target,comparison,period}` records; no free-form client facts are accepted.

`none_reason` is exactly `invalid_analysis_input | insufficient_complete_days | insufficient_coverage | no_eligible_priority | stale_analysis | superseded_analysis | safety_exclusion | unsupported_version | rejected_goal_suppression`.

The Frontend renders the response. It may format locale-safe numbers from the typed facts, but cannot re-rank, synthesize a missing secondary, change action mode, remove safety qualifiers, or recompute confidence. Unknown schema/rule/copy versions render a neutral unavailable state and request refresh.

### 4.2 Closed Arabic copy catalog

| Priority key | Title | Measured-reason pattern | Practical action |
| --- | --- | --- | --- |
| `sodium_overage` | `تقليل الصوديوم` | `تجاوز متوسط الصوديوم الحد المرجعي في يومين مكتملين أو أكثر.` | `استبدل خيارًا مرتفع الصوديوم بخيار أقل صوديومًا هذا الأسبوع.` |
| `added_sugar_overage` | `تقليل السكر المضاف` | `تجاوز متوسط السكر المضاف الحد المحدد في يومين مكتملين أو أكثر.` | `استبدل خيارًا يحتوي على سكر مضاف بخيار غير محلى.` |
| `saturated_fat_overage` | `تقليل الدهون المشبعة` | `تجاوز متوسط الدهون المشبعة الحد المحدد في يومين مكتملين أو أكثر.` | `استبدل مصدرًا مرتفع الدهون المشبعة بمصدر دهون غير مشبعة.` |
| `trans_fat_overage` | `تقليل الدهون المتحولة` | `تجاوزت الدهون المتحولة الحد المحدد في يومين مكتملين أو أكثر.` | `استبدل الخيار المحتوي على دهون متحولة بخيار لا يحتوي عليها.` |
| `processed_meat_frequency` | `تقليل تكرار اللحوم المصنعة` | `ظهرت اللحوم المصنعة في يومين مكتملين أو أكثر خلال الفترة.` | `استبدل إحدى مرات تناول اللحوم المصنعة بمصدر بروتين آخر.` |
| `sugary_drink_frequency` | `تقليل المشروبات المحلاة` | `ظهرت المشروبات المحلاة بالسكر في يومين مكتملين أو أكثر خلال الفترة.` | `استبدل مشروبًا محلى بالماء أو مشروب غير محلى.` |
| `fruit_vegetable_gap` | `زيادة الخضروات والفواكه` | `كان المتوسط المسجل أقل من 80٪ من الهدف.` | `أضف أو استبدل خيارًا في وجبة واحدة بخضروات أو فاكهة.` |
| `legumes_gap` | `زيادة البقوليات` | `كان عدد حصص البقوليات أقل من 80٪ من الهدف الأسبوعي.` | `أضف أو استبدل مصدر بروتين في وجبة واحدة بالبقوليات.` |
| `whole_grain_share_gap` | `زيادة الحبوب الكاملة` | `كانت حصة الحبوب الكاملة أقل من 80٪ من الهدف ضمن الحبوب المعروفة.` | `استبدل خيارًا من الحبوب المكررة بخيار من الحبوب الكاملة.` |
| `nuts_seeds_gap` | `زيادة المكسرات والبذور` | `كان عدد الحصص المسجلة أقل من 80٪ من الهدف الأسبوعي.` | `أضف حصة مناسبة أو استبدل وجبة خفيفة بمكسرات أو بذور غير مملحة.` |
| `seafood_gap` | `زيادة المأكولات البحرية` | `كان عدد حصص المأكولات البحرية أقل من 80٪ من الهدف الأسبوعي.` | `استبدل مصدر بروتين في وجبة واحدة بمأكولات بحرية.` |
| `dairy_alternative_gap` | `زيادة الألبان أو البدائل المدعمة` | `كان المتوسط المسجل أقل من 80٪ من الهدف اليومي.` | `أضف أو استبدل خيارًا بمنتج ألبان أو بديل مدعم مناسب.` |
| `fiber_gap` | `زيادة الألياف` | `كان متوسط الألياف أقل من 80٪ من الهدف.` | `أضف أو استبدل خيارًا بمصدر غني بالألياف.` |
| any closed micronutrient gap | `مراجعة مصادر {اسم العنصر}` | `ظل متوسط {اسم العنصر} أقل من 80٪ من الهدف خلال فترتين مع تغطية قوية.` | `راجع الأطعمة المسجلة الغنية بـ{اسم العنصر} واختر مصدرًا مناسبًا؛ لا تبدأ مكملاً بناءً على هذه النتيجة.` |

When calories are above target, the Backend selects the replacement sentence and never the addition clause. None/stale/safety copy is exact:

- no eligible: `لا توجد أولوية واضحة هذا الأسبوع بناءً على البيانات المكتملة.`
- insufficient: `أكمل تسجيل أربعة أيام على الأقل مع بيانات كافية لاقتراح أولوية أسبوعية.`
- stale/superseded: `تغيّرت بيانات اليوميات. حدّث التحليل قبل عرض أولوية.`
- safety suppressed: `لا يمكن اقتراح أولوية آمنة من هذه البيانات. راجع إعدادات أهدافك أو مختصًا مؤهلًا عند الحاجة.`
- evidence disclosure: `بُني هذا الاقتراح على الأيام المكتملة والتغطية المتاحة، وليس على الأيام غير المكتملة.`

These are the approved final templates. A copy-only correction still requires affected review, bumps `copy_version`, and never silently rewrites stored historical wording.

### 4.3 Freshness, supersession, retention, and replay

- A recommendation expires at the next successful analysis revision, at the end of its rolling period plus 36 hours, or when a referenced complete day is reopened/edited—whichever occurs first.
- Stale/superseded results remain readable in history but cannot create a new offer or goal. They carry their original versions and `superseded_by_id` where applicable.
- Historical explanation renders stored `PriorityV1` facts and copy snapshots, not today's Registry, targets, or rules. Replay verification may load the exact supported rules version; absence of old executable rules never mutates the stored result.
- Recommendation/evidence records are retained for 24 months after period end, then deleted unless referenced by a retained goal. A referenced minimal result is retained until 24 months after the goal archives. Operational logs retain only opaque IDs/result codes for 90 days.
- Owner deletion removes future offers and goal records under the approved account/record-deletion workflow. Aggregate shadow metrics contain no Principal or evidence IDs and cannot reconstruct a person.
- Regeneration under a newer rules version creates a new revision linked to the old result. It never overwrites rank, facts, wording, or action on the old result.

## 5. Owner-bound behavior-goal lifecycle

### 5.1 State and ownership model

Persisted state is exactly `offered | deferred | active | paused | incomplete | rejected | completed | ended | archived`. An offer is generated only from the current non-stale main priority. The secondary is informational and cannot independently become a concurrent goal. A partial unique constraint permits at most one `active` or `paused` primary goal per Principal.

The editable behavior contract is a bounded action plan, not a nutrient target: `action_key`, `weekly_target_count` integer 1–7, `scheduled_day_mask` optional unique weekdays, and `owner_note` optional 0–280 characters. Edit cannot change the evidence metric, direction, safety exclusions, priority key, or rules version. The Backend validates action-key-specific count bounds. Free text is never used for selector/progress logic.

Every command requires authenticated ownership, `Idempotency-Key`, and `expected_version`. Same Principal/operation/key/request hash replays the exact stored response. Key reuse with different content returns `409 IDEMPOTENCY_KEY_REUSED`; stale version returns `409 GOAL_VERSION_CONFLICT`; another primary returns `409 PRIMARY_GOAL_EXISTS`. Cross-owner IDs return `404 RESOURCE_NOT_FOUND`.

### 5.2 Closed transition and result matrix

| Prior state | Event | Next state | Required reason/timestamp | API result | UI result |
| --- | --- | --- | --- | --- | --- |
| none + current main | Backend `offer` | `offered` v1 | `offered_at`, recommendation ID | current GET includes offer | neutral card; no implied acceptance |
| `offered`/`deferred`, no other primary | owner `accept` | `active` | `accepted_at`, period bounds | `accepted` | announce active; focus goal heading |
| `offered`/`deferred`, another active/paused primary | owner `accept` or offered `edit` | unchanged | no timestamp/history | `409 PRIMARY_GOAL_EXISTS` | retain offer and focus conflict alert |
| `offered` | owner `edit` | `active` | validated edit + `accepted_at` | `edited_and_accepted` | show confirmed bounded plan |
| `active` | owner `edit` | `active` | append revision, `changed_at` | `edited` | preserve progress recomputation notice |
| `offered` | owner `defer` | `deferred` | `deferred_until` = next Diary date, max period end | `deferred` | hide prompt until date; show reversible state |
| `offered` | owner `reject` | `rejected` | reason enum + `rejected_at` | `rejected` | neutral acknowledgement; no repeat |
| `deferred` | owner `reject` | `rejected` | reason enum + `rejected_at` | `rejected` | neutral acknowledgement; no repeat |
| `active` | owner `change` | `active` | new current eligible priority/action, reason, `changed_at` | `changed` | show old goal in history and new terms |
| `active` | owner `pause` | `paused` | reason + `paused_at` | `paused` | progress retained; reminders suppressed |
| `paused` | owner `resume` | `active` | `resumed_at` | `resumed` | resume derivation; no catch-up reminder |
| `active` | Backend `complete` | `completed` | derived progress reached target + `completed_at` | read returns completed | neutral completion; no reward/streak |
| `completed` before finalization | Backend `evidence_reopened` | `active` | clear completion; append evidence revision | `evidence_reopened` | neutral recomputation notice |
| ended window in `active`/`paused`, target not reached | Backend `finalize_incomplete` | `incomplete` | freeze final progress revision + `reviewed_at` | read returns incomplete | show repeat/reduce/change/end review |
| `incomplete`, no successor | owner `end` | `ended` | append reason + `ended_at`; retain frozen evidence | `ended` | close review without a new week |
| `active`/`paused` | owner `end` | `ended` | reason + `ended_at` | `ended` | neutral end; offer alternatives next analysis only |
| `rejected`/`completed`/`ended` | retention `archive` | `archived` | `archived_at` | history only | read-only history |

`reject_reason` and `end_reason` are optional closed enums `not_relevant | too_difficult | prefer_other | pause_tracking | other`; `other` may accompany the bounded private note. `change_reason` is `owner_requested | evidence_superseded`. Completion is not a client command and cannot be forced by a checkbox.

Invalid transitions return `409 GOAL_STATE_CONFLICT` and the current safe projection without mutation. Each successful transition increments version once, writes one history row, and uses a Backend UTC timestamp. Replay, invalid transition, and stale commands do not append history. Concurrent commands serialize on the Principal then goal row; the first valid writer wins and the other receives the current version.

### 5.3 API projection per state

Proposed additive endpoints, all under owner authentication:

- `GET /progress/weekly-priorities/current` returns `WeeklyPriorityResultV1`;
- `GET /progress/behavior-goals/current` returns the current tracked goal or explicit `null` plus source/current priority and closed `goal_unavailable_reason`; an informational-only main returns `action_not_observable`;
- `GET /progress/behavior-goals/history?cursor=&limit=20` returns bounded newest-first incomplete/completed/rejected/ended/archived projections;
- `POST /progress/behavior-goals/{goal_id}/commands` accepts the closed event union and returns `BehaviorGoalResponseV1`;
- no Admin mutation route; a bounded Admin monitoring projection may expose state/version/timestamps but not notes, evidence facts, rejection reason, or reminder content.

Every `BehaviorGoalResponseV1` contains `schema_version`, opaque goal ID, state, version, action key, bounded target, period, source recommendation/rule/copy versions, Diary-derived progress status, relevant timestamps, allowed next actions, and calendar snapshot. Each state has exactly these allowed actions:

| State | Allowed owner actions |
| --- | --- |
| `offered` | accept, edit, defer, reject |
| `deferred` | accept, reject |
| `active` | edit, change, pause, end |
| `paused` | resume, end |
| `incomplete` | repeat, reduce, change, end |
| `rejected`, `completed`, `ended`, `archived` | none |

### 5.4 Goal lifecycle Arabic and accessibility

| State/action | Exact approved copy |
| --- | --- |
| offer heading | `هل ترغب في تحويل الأولوية إلى هدف أسبوعي؟` |
| accept | `بدء الهدف` |
| edit | `تعديل الخطوة` |
| defer | `ذكّرني لاحقًا داخل التطبيق` |
| reject | `ليس مناسبًا الآن` |
| active | `هدفك الأسبوعي نشط` |
| paused | `الهدف متوقف مؤقتًا` |
| resume | `استئناف الهدف` |
| change | `تغيير الهدف` |
| end | `إنهاء الهدف` |
| completed | `اكتملت الخطوة وفق الأيام المسجلة.` |
| insufficient | `لا تكفي الأيام المكتملة لتحديد التقدم.` |
| ended | `تم إنهاء الهدف دون حكم على النتيجة.` |
| repeat | `تكرار الهدف لأسبوع جديد` |
| reduce | `تخفيف الخطوة للأسبوع الجديد` |
| repeat success | `بدأ أسبوع جديد للهدف مع الاحتفاظ بنتيجة الأسبوع السابق.` |
| repeat unavailable | `لا يمكن تكرار هذا الهدف الآن. راجع أولوية الأسبوع الحالية.` |

Cards use a heading plus text/icon state, never color alone. Dialogs trap focus; Escape cancels. Success focuses the goal heading and uses one polite live announcement. Errors focus the alert/retry action. Numeric progress uses `<bdi>`. At 320, 360, 390, and 430 px actions wrap without horizontal scroll and retain 44×44 CSS-pixel targets. RTL reading order, reduced motion, screen-reader names, loading skeleton with `aria-busy`, initial `role=alert`, and stale-last-known labeling are mandatory.

### 5.5 Deterministic end-of-week repeat

At end-of-window finalization, an `active` or `paused` goal that is not achieved transitions once to `incomplete`; this system transition freezes the prior window's final progress/evidence/history before any owner choice. Repeat is available only from that frozen `incomplete` state with progress `not_yet_reached` or `insufficient_evidence`. An achieved, offered, deferred, active, paused, rejected, completed, ended, or archived goal cannot repeat. A current fresh `selected` weekly-priority result must name the same `rule_key` as its main priority, with the same rules version, compatible action key, and `goal_trackability=trackable`. A matching secondary never authorizes repeat and repeat never changes the main/secondary cap or selector order. A stale, none, safety-suppressed, different-main, changed-rules, or incompatible-action result offers `change` or `end`, not repeat.

Repeat is one atomic Backend command, never an overwrite:

1. authenticate the Principal, validate the client command shape, compute its stable canonical hash, and lock/read the `(principal_id, operation, source_goal_id, idempotency_key)` ledger entry;
2. when that ledger entry exists, replay its stored status, headers, and response if the stable hash matches, or return `IDEMPOTENCY_KEY_REUSED` if the stable client content differs; do this before reading the calendar, recommendation, or allocating an ID;
3. only for a new ledger entry, capture one authoritative Backend Diary date and lock Principal, source goal, and current recommendation;
4. verify `expected_version`, frozen incomplete state, ended window, current-main binding, absence of an existing successor, and absence of another primary;
5. leave every column and history row of the old goal unchanged;
6. create a distinct `behavior_goal` row with a new server UUID, `root_goal_id` copied from the source, `previous_goal_id=source.id`, `sequence_number=source.sequence_number+1`, `state=active`, and version `1`;
7. bind the new row to the captured date and current recommendation ID, preserve the source rule/action/target for `repeat_mode=same`, append only the new goal's `repeated_from_previous_window` activation history, store the complete idempotency result binding, and commit once.

The old goal retains its `incomplete` state, identity, version, window, progress/evidence revision, reminders, terms, timestamps, and full history byte-for-byte. The new goal starts with progress zero, no reminder deliveries, and a new window. `new_window_start=max(captured_current_diary_date, source.window_end + 1 day)` and `new_window_end=new_window_start + 6 days` in `Asia/Riyadh`; windows never overlap and no skipped date is backfilled. Repeating after a delay starts on the captured request date. The current recommendation is evidence for eligibility, not permission to rewrite the prior result.

`repeat_mode=reduce` uses the same new-row transaction but requires an owner-selected `weekly_target_count` that is an integer >=1 and strictly lower than the source target while preserving rule/action/direction. It returns `reduced_and_repeated`. The review's `change` action opens the current main offer; it does not command or mutate the incomplete source, and ordinary offer acceptance creates the new goal under the current priority. The review's `end` command changes only lifecycle state to `ended`, appends `ended_at`/reason, preserves the frozen evidence snapshot, and creates no successor. Principal serialization plus unique `(principal_id, previous_goal_id)` makes repeat/reduce mutually exclusive successor choices: the first committed successor wins without changing the source version. If an ordinary current offer is accepted first, repeat/reduce returns `PRIMARY_GOAL_EXISTS`; if repeat/reduce wins first, offer acceptance returns the same conflict. If end wins first, later repeat/reduce returns `GOAL_STATE_CONFLICT`; if a successor wins first, end returns `GOAL_VERSION_CONFLICT` because a successor already exists.

The exact API command is `POST /progress/behavior-goals/{source_goal_id}/commands` with `{event:"repeat", repeat_mode:"same|reduce", expected_version, weekly_target_count?}` plus `Idempotency-Key`. Operation name is `behavior_goal_repeat`. The canonical request identity/hash is exactly Principal, operation, source goal ID, `event`, `repeat_mode`, `expected_version`, and requested reduced target (null for same). The client cannot send the authoritative Diary date, recommendation ID, or new goal ID. Those are server-owned first-execution bindings and are excluded from request identity. Success returns `BehaviorGoalRepeatResponseV1` containing `result=repeated|reduced_and_repeated`, immutable `previous_goal`, new `goal`, current recommendation/rule/copy versions, and calendar snapshot. It also returns `ETag: "goal-1"` for the new row.

The idempotency ledger stores the stable hash and the first execution's captured Diary date, recommendation binding, allocated goal ID, committed status/headers, and exact response. Same Principal/key/hash replays that exact first response with `Idempotent-Replayed: true`, creating no row/history/reminder even after a Diary-date rollover or recommendation refresh. Same key with different stable client content returns `409 IDEMPOTENCY_KEY_REUSED`. A stale source version or an already-created successor from a concurrent command returns `409 GOAL_VERSION_CONFLICT`; an ineligible source state returns `409 GOAL_STATE_CONFLICT`; another primary returns `409 PRIMARY_GOAL_EXISTS`; a current-priority mismatch returns `409 GOAL_REPEAT_PRIORITY_CONFLICT`. All conflicts leave both source and prospective successor unchanged. Cross-owner IDs remain `404`.

Successful repeat moves focus to the new goal heading and announces the exact repeat-success copy once. Replay does not repeat the live announcement. Failure retains focus in the end-week review and focuses its non-color alert. The previous-week card remains reachable in history and is labelled `الأسبوع السابق — غير مكتمل` or `الأسبوع السابق — بيانات غير كافية` from its frozen result. The new card is labelled with its full Arabic date range; `<bdi>` isolates dates.

The prior end-week review and reminder receipts remain immutable. The new goal receives a fresh reminder namespace `(new_goal_id, sequence_number)` and may receive at most its own one midweek reminder and one end-week review under section 6.3. Repeat itself sends no external notification. Audit records opaque source/new/root IDs, sequence, result code, versions, request ID, and timestamps; it excludes nutrition evidence, owner note, destination, idempotency key, and message copy.

## 6. Diary-derived progress, reminders, and rejection suppression

### 6.1 Progress window and formula

The goal window starts on the captured Diary date of acceptance/edit/change and ends on the earlier of seven Diary dates or the source priority period's review end. It never back-credits days before the owner accepted the terms. One captured Backend calendar snapshot is propagated through each evaluation.

Only the nine trackable action keys in section 0.3 map to a closed predicate over persisted PLAN 032 day facts. A qualifying occurrence is a distinct eligible complete Diary date satisfying that exact predicate. Replacement wording does not require causal proof that another item disappeared, but does require observable desired-category appearance. Informational-only actions never enter progress calculation.

```text
eligible_dates = dates in goal window where logging_status == complete
progress_count = count(distinct eligible date satisfying action predicate)
progress_percent = min(100, round_half_even(100 * progress_count / weekly_target_count))
progress_status = achieved when progress_count >= target
                | insufficient_evidence when window ended, target not reached, and complete dates < 4
                | in_progress when eligible date count > 0
                | unknown when eligible date count == 0
```

An explicitly empty complete day is eligible zero progress. `partial` and `unregistered` dates are omitted, not zero. Unknown snapshot fields cannot satisfy a predicate. Achievement takes precedence: reaching the target from qualifying complete-date evidence is `achieved` even when fewer than four dates are complete. At end of window, `insufficient_evidence` applies only when the target was not reached and fewer than four dates are complete; the UI may say the observed count but cannot claim failure. With four or more complete days, below-target is `not_yet_reached`, never failure.

Progress payload includes window, count, target, percent/null, complete/partial/unregistered counts, `as_of_diary_date`, source day versions, calculation rules version, and `last_recomputed_at`. The Backend is sole authority; the Frontend never increments optimistically.

### 6.2 Late edits, reopen, change, and finalization

- An entry mutation on a reopened day invalidates the prior computation. The day contributes nothing until explicitly completed again.
- Before `period_end + 36 hours`, recomputation may move progress up or down. If achieved evidence disappears, system event `evidence_reopened` moves `completed -> active`, clears `completed_at`, increments version, and records history without blame.
- Re-completing the day recomputes against its new PLAN 031 day version. If the target is reached again, Backend `complete` creates a new completion history event.
- At `period_end + 36 hours`, the end-week review revision is finalized. Later Diary changes create a superseding historical progress revision and `historical_evidence_changed`; they never send another reminder or rewrite the prior audit row.
- Owner `change` ends the prior terms as a goal revision and starts new terms at count zero from the change date. No old occurrence is carried into the new target.
- Owner `end` or `pause` preserves the last derived progress. Resume recomputes current evidence; it does not manufacture catch-up progress.
- Source analysis supersession does not silently change an accepted goal. It marks the source link superseded and allows owner `change` or `end`; unsafe supersession pauses reminders immediately.

### 6.3 Reminder policy

External notifications default off and require an explicit owner preference. In-app reminders use the same caps; disabling reminders affects delivery, not goal state.

| Reminder | Exact eligibility | Cap and copy |
| --- | --- | --- |
| contextual midweek | active; fourth Diary date of window or later; progress exactly 0; at least two complete dates; not stale/unsafe; not opted out; not sent | at most one: `لم يظهر تقدم في الهدف ضمن الأيام المكتملة. يمكنك تقليل الخطوة أو تغييرها أو إنهاء الهدف.` |
| end-of-week review | active or paused; window ended; final or insufficient-evidence projection available; not already sent | exactly one in-app review card: `راجع هدف الأسبوع وفق الأيام المكتملة. يمكنك تقليله أو تغييره أو إنهاؤه.` |

No reminder is sent for an informational-only priority, unknown progress, deferred/rejected/completed/ended/archived goals, during pause, or after a source safety exclusion. Quiet hours are 21:00–09:00 `Asia/Riyadh`; eligible external delivery is deferred to 09:00 without creating another reminder row. There are no retries that can exceed the cap: a unique `(goal_id, reminder_type, goal_revision)` delivery row and idempotent provider key enforce once-only delivery. Provider failure records a privacy-safe result and does not extend the period or punish the owner.

### 6.4 Rejected-offer suppression

The lookup scope is `(principal_id, rule_key, rules_version)`, deliberately excluding `action_key`, so a new action cannot evade a same-rule rejection. The rejection record retains `rejected_action_key`, `rejected_severity`, and source analysis revision. The current deterministic candidate supplies its action key and severity for comparison. A scoped rejection remains suppressed indefinitely until all are true: a later source analysis revision exists; at least one newly completed Diary date after `rejected_at` participates; and either normalized severity increased by >=0.10 or the deterministic action key changed. Action change without both the later revision and new completed date remains suppressed. Mere passage of time, copy change, refresh, incomplete days, or another request does not qualify. A qualifying new offer is created only on the next analysis and discloses the new evidence; there is never an immediate same-request repeat.

## 7. Persistence, API errors, migration, privacy, and safety

### 7.1 Additive owner-bound schema concept

All identifiers are server UUIDs; timestamps are UTC `timestamptz`; all owner FKs are `ON DELETE RESTRICT` until the approved deletion workflow explicitly removes the graph.

#### `weekly_priority_recommendation`

| Column | Null | Constraint |
| --- | --- | --- |
| `id`, `principal_id`, `source_analysis_id` | no | PK; owner FKs; composite owner integrity |
| `source_analysis_revision`, `schema_version` | no | >=1; schema version = 1 |
| `period_start`, `period_end`, `as_of_diary_date` | no | seven-day period; end >= start; Riyadh date |
| `status`, `none_reason` | conditional | closed result/none enums; selected requires main |
| `rules_version`, `copy_version`, source versions | no | non-empty <=64 characters |
| `result_document`, `input_digest` | no | closed JSON object; SHA-256 canonical input digest, not raw input |
| `generated_at`, `expires_at` | no | expiry after generation |
| `superseded_by_id`, `superseded_at` | yes | both null or both present; same Principal |

Unique `(principal_id, source_analysis_id, source_analysis_revision, rules_version)` makes evaluation idempotent. Index `(principal_id, period_end DESC, generated_at DESC)` serves current/history. A partial unique `(principal_id) WHERE superseded_at IS NULL AND status='selected'` permits one current selected result. JSON schema checks validate cap <=2, main rank, secondary-with-main, sorted evidence refs, and absence of forbidden direct identifiers.

#### `weekly_priority_evidence_ref`

Stores `(recommendation_id, principal_id, metric_key, evidence_kind, opaque_source_id, source_version, diary_date, value, unit, coverage_percent)` with composite owner FK, finite-number checks, coverage 0–100, allowed kind enum, unique evidence identity, and index `(principal_id, diary_date DESC)`. It stores no Food text, Profile inputs, email, reason note, or notification address.

#### `behavior_goal`

Stores owner/source IDs, `root_goal_id`, nullable `previous_goal_id`, positive `sequence_number`, state/version, action key, target count, day mask, bounded private note, start/end dates, source rule/copy versions, current progress document/revision, all state timestamps including `reviewed_at` for `incomplete`, reminder preference, created/updated timestamps. Root points to the first same-owner goal; previous points to the immediately preceding same-owner sequence. Unique `(principal_id, root_goal_id, sequence_number)` and `(principal_id, previous_goal_id)` prevent duplicate/forked successors. Checks enforce the state/timestamp matrix, version >=1, target 1–7, exact non-overlapping seven-date repeat windows, note <=280, and external notifications default false. Partial unique `(principal_id) WHERE state IN ('active','paused')` enforces one primary.

#### `behavior_goal_history`

Append-only rows store goal/owner/root/previous IDs, sequence, goal version, event enum including `finalized_incomplete` and `repeated_from_previous_window`, from/to states, canonical request digest, actor type `owner|system`, reason enum, terms/progress snapshot, occurred time, request ID. Unique `(goal_id, goal_version)` prevents double history. Finalization writes the source goal's terminal incomplete evidence before an owner choice. Repeat appends only the new goal's activation event; it never appends to or changes source history. Notes and provider data are excluded.

#### `behavior_goal_command_idempotency`

Stores Principal, operation, source goal ID, an HMAC digest of the idempotency key, stable canonical client-command hash, captured Diary date, recommendation ID, allocated successor ID, committed HTTP status/safe headers/response, and committed timestamp. Unique `(principal_id, operation, source_goal_id, key_digest)` is the lookup authority. The row is inserted in the same transaction as the successor/history and retained with the referenced goal graph; it is deleted only with that graph under the approved deletion/retention workflow. Raw idempotency keys are never persisted or logged. Lookup and exact replay precede all mutable server-state reads.

#### `behavior_goal_reminder_delivery`

Stores goal/owner, goal revision, type, channel, eligibility Diary date, deferred-until, status, provider opaque receipt digest, attempts fixed at 0 or 1, and timestamps. Unique `(goal_id, goal_revision, reminder_type)` enforces caps. It stores no message body, device token, email, phone, or provider credential.

### 7.2 Migration and compatibility

The future implementation uses one additive Alembic revision after its then-current authoritative head:

1. preflight exact predecessor and required analysis/PLAN 031 owner constraints;
2. create recommendation, evidence, goal, history, and delivery tables plus closed checks/indexes;
3. create no rows and infer no historical priority, rejection, goal, progress, or consent;
4. deploy readers before/sharing release with writers; keep feature flag display off through shadow evaluation;
5. verify tables empty immediately after migration and existing Diary/Profile/Target behavior byte-for-byte unchanged.

Application rollback leaves additive tables. Downgrade fails closed when any new table contains rows and prints aggregate counts only. No migration rewrites Diary entries, status, snapshots, Target Plans, Profiles, or Registry versions.

### 7.3 Stable error catalog

| HTTP | Code | Meaning / exact Arabic message |
| ---: | --- | --- |
| 400 | `INVALID_IDEMPOTENCY_KEY` | `تعذر التحقق من الطلب. أعد المحاولة.` |
| 401 | `AUTHENTICATION_REQUIRED` | `انتهت الجلسة. سجّل الدخول للمتابعة.` |
| 404 | `RESOURCE_NOT_FOUND` | `تعذر العثور على السجل المطلوب.` |
| 409 | `GOAL_VERSION_CONFLICT` | `تغيّر الهدف. حدّث الصفحة ثم حاول مجددًا.` |
| 409 | `GOAL_STATE_CONFLICT` | `لا يتاح هذا الإجراء في حالة الهدف الحالية.` |
| 409 | `PRIMARY_GOAL_EXISTS` | `لديك هدف أساسي حالي. غيّره أو أنهه أولًا.` |
| 409 | `GOAL_REPEAT_PRIORITY_CONFLICT` | `لا تتوافق أولوية الأسبوع الحالية مع تكرار هذا الهدف.` |
| 409 | `IDEMPOTENCY_KEY_REUSED` | `تعارض الطلب مع محاولة سابقة.` |
| 422 | `GOAL_ACTION_NOT_ALLOWED` | `لا تتوافق الخطوة المختارة مع هذه الأولوية.` |
| 422 | `VALIDATION_ERROR` | `تحقق من بيانات الطلب.` plus bounded field map |
| 503 | `PRIORITY_EVIDENCE_UNAVAILABLE` | `لا تتوفر بيانات كافية وموثوقة لعرض الأولوية الآن.` |
| 500 | `GOAL_WRITE_FAILED` | `تعذر حفظ الهدف. لم تُفقد بياناتك؛ حاول مجددًا.` |

No error discloses whether another Principal owns an ID. Responses and OpenAPI use named discriminated schemas, generated into the Frontend; generic objects and handwritten transport DTOs are forbidden.

### 7.4 Safety, audit, and UX completeness

- Recommendations are food-pattern suggestions, not diagnoses, treatment, supplements, or automatic Target Plan changes. Micronutrient copy explicitly avoids supplement advice.
- `very_low_energy_blocked`, incompatible/missing Target Plan, unsupported rules, and any future approved clinical exclusion suppress recommendations and reminders. The selector cannot override them.
- Logs include request ID, opaque Principal ID, recommendation/goal ID, rules version, event/result code, latency bucket, and error class. They exclude facts, Food/Profile content, notes, rejection/end reason, evidence IDs, copy text, provider destination, and idempotency keys.
- Admin is GET-only and bounded. It may see aggregate state/version/period/rules/coverage band, never private notes, exact facts, evidence source IDs, rejection reasons, reminder destinations, or command endpoints.
- Evidence disclosure is adjacent to every priority and goal progress card. Loading, empty, none, stale, safety, offered, deferred, active, paused, completed, ended, insufficient, and error states use the exact neutral copy in sections 4–6.
- At 320–430 px, the main and optional secondary stack vertically; evidence disclosure follows its priority; goal actions wrap to one column at 320 px. No horizontal scroll, clipped focus ring, color-only state, auto-focused marketing prompt, or motion-dependent meaning is allowed.

## 8. Verification, shadow evaluation, and launch control

### 8.1 Golden and mutation coverage

The seeded corpus covers all prior selector/lifecycle/repeat authorities plus all 28 explicit classifications, the exact 9/19 split, informational-only offer/progress/reminder/repeat suppression, withdrawn-version rejection, and producer-shaped day facts for every trackable predicate family. Progress qualification is derived by the verifier; a supplied `qualifies` boolean is malformed and rejected. Golden fields named `_server_generated_goal_id` and `_server_state_before` remain deterministic server-output fixtures and are not API request fields.

The docs-only checker must reproduce every expected result and prove each selection has at most one main and one secondary. Future implementation tests must mutate each of these and observe failure: swap tier order; remove 75% coverage; treat partial as zero; permit one-event limit priority; remove micronutrient persistence; allow addition above calories; add a third priority; repeat a rejected goal; accept a second primary; increment progress in the client; preserve completion after reopen; reuse a source goal ID/window during repeat; overwrite prior repeat evidence; authorize repeat from a secondary; or send a second reminder.

### 8.2 Future acceptance matrix

| Area | Positive evidence | Negative/boundary evidence | Required suite |
| --- | --- | --- | --- |
| Input contract | versioned consecutive rolling periods | malformed, cross-owner, stale, unsupported, non-finite fail closed | unit + Postgres + OpenAPI |
| PLAN 031 semantics | complete and empty-complete included | partial/unregistered excluded, reopen invalidates | service + aggregation |
| Selector | tier/threshold/tie/conflict/cap match vectors | shuffled input stays identical; max two | property + golden |
| Safety | replacement and exclusions win | no diagnosis/supplement/target mutation | rule + copy review |
| History | original facts/rules/copy replay | new version never rewrites old result | Postgres revision |
| Ownership | owner reads/commands own records | cross-owner 404; spoofed Principal rejected | two-owner API |
| Goal lifecycle | every valid state event | invalid/stale/duplicate/racing commands | state + Postgres concurrency |
| Incomplete-goal repeat | frozen incomplete source plus distinct new active window | replay, concurrent successor, invalid state, ID reuse, existing-primary and secondary-priority mismatch | state oracle + Postgres transaction |
| Progress | distinct complete dates derive count | unknown/partial/late reopen/reset semantics | service + clock |
| Reminders | one eligible midweek and one end review | opt-out/quiet/pause/progress/cap suppression | scheduler + delivery uniqueness |
| Migration | fresh/populated upgrade and compatible rollback | no backfill; downgrade refuses data | Alembic PostgreSQL |
| Arabic UX | every exact state and evidence disclosure | no color-only/punitive/gamified wording | Playwright + copy oracle |
| Accessibility | keyboard/focus/live region/RTL/reduced motion | no duplicate announcements or focus loss | axe + StrictMode |
| Responsive | 320/360/390/430 layout | no overflow/clipping/sub-44px action | Linux visual |
| Architecture | generated contracts; Backend rules authority | no handwritten DTO or Frontend selector/progress | architecture test |

### 8.3 Shadow and manual review gates

Implementation starts with server evaluation and persistence behind `weekly_priorities_shadow_v1`; user payloads omit results and no goal/reminder is created. Shadow must run at least 28 consecutive days and include at least 1,000 eligible evaluations before launch review. If traffic cannot supply 1,000, the gate remains closed; Design 1.1 defines no replacement denominator, waiver, or lower threshold.

Required launch evidence:

- deterministic replay mismatch: 0;
- cap violations, third priorities, secondary-without-main: 0;
- safety exclusions displayed or offered: 0;
- cross-Principal evidence/reference incidents: 0;
- invalid/stale/unsupported inputs that do not fail closed: 0;
- golden and mutation cases: 100% pass;
- at least 100 stratified privacy-redacted scenarios manually reviewed, including every rule key and every none/safety/conflict class;
- reviewer agreement on eligibility, main rank, conflict, and copy >=95%, with 100% agreement on safety cases;
- no unresolved Blocker/Critical/High/Medium finding across all eight approval perspectives.

Distribution by rule, none reason, coverage band, complete-day count, action mode, conflict reason, and rules version is diagnostic, not a quota. A high `none` rate never justifies weakening evidence.

### 8.4 Privacy-safe observability, rollout, and rollback

Allowed aggregate metrics are evaluation count/result class, rule key, main/secondary count, selected trackable-main count, selected informational-only-main count, coverage band, latency bucket, stale/invalid reason, goal state event, progress-status band, reminder eligibility/suppression/result, version, and error code. Metrics exclude Principal/evidence IDs, exact nutrition values, Profile/Target inputs, dates finer than ISO week, notes/reasons, copy text, and notification destinations. Logs follow the 90-day policy; aggregate counters follow the approved product-metrics retention policy and cannot be joined back to a person.

After eight explicit approvals and a freeze decision, rollout still requires a separate implementation/launch authorization. Stages are internal staff, 5%, 25%, then 100%, each for at least seven days with the same zero-safety/cap/isolation gates. A server-side kill switch independently disables display, goal offers, and external delivery while preserving read-only history.

Immediate rollback triggers are any safety recommendation, cap violation, cross-owner disclosure, Frontend-authored decision, repeated rejected offer without new evidence, second active primary, reminder cap breach, historical rewrite, or deterministic mismatch. Rollback disables new display/offers/delivery, keeps Diary/Profile untouched, preserves audit history, and returns neutral unavailable copy. It never deletes evidence or rewrites a goal.

### 8.5 Checkpoint result

Steps 1–7 and the formal design review are complete. At the Project Owner's explicit authorization/request, Codex performed the eight role-based discipline assessments recorded in `28B_W3_WEEKLY_PRIORITY_AND_GOAL_APPROVAL_REPORT.md`; they are not eight independently submitted named human reviews, and no reviewer names, timestamps, signatures, or comments are inferred. Every role recorded `APPROVED` with no blocking finding, the executable evidence passed, and the exact decision is `Frozen for implementation`. Any material contract change invalidates the affected assessments and requires a versioned review before implementation continues. Launch remains a separate authorization.

## 9. Artifact authority

- `28A_W3_WEEKLY_PRIORITY_AND_GOAL_GOLDEN_VECTORS.json` is seeded design evidence.
- `tools/verify_w3_weekly_priority_vectors.py` is a standard-library oracle and must never be imported by application code.
- `28B_W3_WEEKLY_PRIORITY_AND_GOAL_APPROVAL_REPORT.md` is the only approval ledger for this frozen design.
