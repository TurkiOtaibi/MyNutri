# Wave 1 Golden Calculations

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-GOLDEN-18` |
| Version | `1.1` |
| Status | `Approved — Engineering and QA` |
| Owner | Engineering / QA |
| Approver | Engineering / QA |
| Approval date | `2026-07-16` |
| Review | `18A_WAVE1_GOLDEN_CALCULATIONS_REVIEW.md` |
| Change review | `W1-CD-01A_LEGACY_TARGET_TRANSITION_IMPACT_REVIEW.md` |
| Critical / High / Product decisions | `0 / 0 / 0` |
| Pinned revision | `9d4911d2c8c55cfc02ad1ddfe891e8e9833fc1cf` |
| Versions | calculation `2.0.0`; Registry `1.0.0`; group/reliability/NOVA `1.0.0`; Snapshot `2` |
| Implementation authorization | `No` |

## 1. Numeric Policy

Use decimal-safe arithmetic. Do not round intermediate values. Mifflin BMR and TDEE retain full precision; final calories use existing nearest-integer policy; final macro targets use one decimal. BMI branch uses unrounded BMI. Carbohydrate warning classification uses final rounded grams, but raw calories <=0 are invalid. Age is age on Target Plan effective date in `Asia/Riyadh`.

## 2. Energy and Macro Scenarios

### `W1-GC-001` — Mifflin maintain baseline

Input: male, age 30, 80 kg, 180 cm, moderate `1.55`, maintain. BMR=`10×80+6.25×180−5×30+5=1780`. TDEE=`2759.00`. Final calories=`2759`. No deficit. BMI=`24.691358...`; actual basis. Protein `80×1.2=96.0g`. Male fat `2759×0.25÷9=76.638...→76.6g`. Carbs `(2759−384−689.75)÷4=421.3125→421.3g`. Safety normal; no carb warning.

### `W1-GC-002` — Cut intensities and cap

For TDEE `2500`: 15% request/applied `375`, target `2125`; 20% `500`, target `2000`; 25% `625`, target `1875`. For TDEE `4000` at 25%: requested `1000`, applied `750`, cap true, target `3250`. For non-cut goal applied deficit is zero regardless of stored preference.

### `W1-GC-003` — Safety boundaries

Final `1201`: normal/can activate. Final `1200` and `800`: `specialist_review_required`, cannot activate. Final `799`: `very_low_energy_blocked`, cannot activate. Preview returns each result; activation returns stable blocked error. Rounding occurs before classification: raw `1200.49→1200` blocked; exact tie `1200.50→1200` under the existing half-even policy and remains blocked; raw `1200.51→1201` is normal.

### `W1-GC-004` — BMI below/exact/above 30

At 180 cm, BMI reference boundary weight=`30×1.8²=97.2kg`.

- `97.199kg`: BMI `29.999691...`, actual basis, calculation weight `97.199`.
- `97.200kg`: BMI exactly `30`, reference=`25×3.24=81.0`, adjusted=`81+0.33×16.2=86.346kg`.
- `100kg`: BMI `30.864197...`, adjusted=`81+0.33×19=87.27kg`.

At factor 1.2, exact-boundary protein=`103.6152→103.6g`; above=`104.724→104.7g`. Reference weight is never described as ideal/goal weight.

### `W1-GC-005` — Female high-BMI regression

Input female, 115kg, 170cm, final calories 1655, factor 1.2, fat 30%. BMI=`39.792387...`; reference=`72.25`; adjusted=`72.25+0.33×42.75=86.3575`; protein=`103.629→103.6g`; fat=`1655×0.30÷9=55.1666...→55.2g`; carb calories=`1655−414.516−496.5=743.984`; carbs=`185.996→186.0g`. This intentionally supersedes actual-weight protein expectations from pre-H02 history.

### `W1-GC-006` — Fat defaults/custom

At 2000 calories: male 25%=`55.6g`; female 30%=`66.7g`. Custom 27%=`60.0g`. Sex change changes 25→30 only when the normalized value equals prior male default; custom 27 remains 27. Restore returns 25 male/30 female and protein factor 1.2 as draft only.

### `W1-GC-007` — Carbohydrate boundaries

Use final calories `2000`; select protein/fat allocations yielding raw grams:

- `130.04→130.0`: valid, no warning.
- `129.95→130.0`: valid, no warning because visible rounded value is 130.0.
- `129.94→129.9`: valid, `CARBOHYDRATE_BELOW_GENERAL_REFERENCE` info.
- `100.00→100.0`: calm warning.
- `99.95→100.0`: calm warning.
- `99.94→99.9`: `CARBOHYDRATE_VERY_LOW` warning.
- raw `0.01g→0.0g`: invalid because final rounded target is zero.
- raw calories `0` or negative: `NON_POSITIVE_CARBOHYDRATE_ALLOCATION` 422.

Successful responses always have `carb_clamped=false`.

## 3. Nutrient Target Scenarios

| ID | Input | Exact resolved output |
|---|---|---|
| `W1-GC-008` | any adult | fiber minimum `30g` |
| `W1-GC-009` | 2000 kcal | added sugar max `50.0g`; saturated fat max `22.2g`; trans fat max `2.2g` (strict less-than semantics retained in descriptor) |
| `W1-GC-010` | any adult | sodium max `<2000mg`; cholesterol monitor-only/no number |
| `W1-GC-011` | male/female | potassium adequate `3400/2600mg`; zinc `11/8mg`; vitamin A RAE `900/700mcg` |
| `W1-GC-012` | age/sex | calcium: 19-50 `1000mg`; male 51-70 `1000`; female 51-70 `1200`; >70 `1200` |
| `W1-GC-013` | age/sex | iron male `8mg`; female 19-50 `18`; female 51+ `8` |
| `W1-GC-014` | age/sex | magnesium male 19-30 `400`, 31+ `420`; female 19-30 `310`, 31+ `320mg` |
| `W1-GC-015` | any adult | selenium `55mcg`; B12 `2.4mcg`; folate `400mcg DFE`; iodine `150mcg` |

Age transitions occur on effective date: female age 50 gets calcium 1000/iron18; on 51st birthday gets calcium1200/iron8 in a newly activated plan only. Existing plans remain immutable.

## 4. Group and Serving Scenarios

| ID | Logged known contributions | Output |
|---|---|---|
| `W1-GC-016` | vegetables 240g + fruit 160g | 3 vegetable +2 fruit servings; combined 400g target met |
| `W1-GC-017` | liquid fruit 300ml | 2 raw servings but capped at 1 counted fruit serving/day |
| `W1-GC-018` | dried fruit 45g | 1.5 fruit servings |
| `W1-GC-019` | whole grain 60g, refined 40g | whole share `60%`, target met; unknown grain excluded and coverage shown |
| `W1-GC-020` | legumes 200g/week | `2.5` servings, below 3 |
| `W1-GC-021` | nuts/seeds 150g/week | `5` servings, target met; oil excluded |
| `W1-GC-022` | seafood 200g with 100g omega3 trait | 2 servings; omega3 serving requirement met |
| `W1-GC-023` | fortified alternative 250ml, calcium 99mg/100ml | 0 dairy servings; at 100mg plus fortified trait =1 serving |
| `W1-GC-024` | red meat 350/500/501g week | near-limit at 350 and 500; above at 501 |

Contribution set `60+40=100` valid; `60+30=90` valid partial/reviewed complete depending status; `60+41=101` rejected; zero row rejected. Traits never add contribution or serving.

## 5. Snapshot and Coverage Scenarios

### `W1-GC-025` — Captured-unit scaling

Snapshot v2 captured unit fiber `2.5g`, sodium null, trans fat `0`. Quantity `3`: fiber `7.5`, sodium null, trans fat `0`. Changing quantity to `2` yields `5.0/null/0` without snapshot mutation. Meal move changes no value.

### `W1-GC-026` — Coverage states

Four valid entries with fiber `[5,0,null,3]`: known count 3, total 4, amount `8`, coverage `75%`, partial/at_least. `[null,null]`: amount null, `0%`, all_unknown/unavailable. Empty day: amount/coverage null/no_entries. `[0,0]`: amount 0, coverage100%, complete/exact.

### `W1-GC-027` — Partial evaluation

Fiber known minimum 32/target30 with partial coverage => `met_at_least`; 20 => indeterminate, no remaining. Sodium known 2100/max2000 => `exceeded_at_least`; 1500 => indeterminate, no available. Range known above upper => `above_range_at_least`; otherwise indeterminate.

### `W1-GC-028` — Mixed v1/v2 and integrity

Valid v1 absent nutrient counts unknown; valid v2 zero counts known. Both normalize into one aggregate. Unknown schema or malformed v1/v2 returns integrity error and no day/week numeric totals; current Food is never read to repair.

## 6. Target Plan, Idempotency, and Date Scenarios

| ID | Scenario | Result |
|---|---|---|
| `W1-GC-029` | new Profile/no source activates 2026-07-16 Riyadh | effective_from 2026-07-16; eligible same-day no-source entries bind; snapshots unchanged |
| `W1-GC-030` | legacy Profile activates same day | effective_from 2026-07-17; current entries remain legacy |
| `W1-GC-031` | replace pending before effective | old audit status superseded-before-effective; one new pending |
| `W1-GC-032` | same key/same payload | original result replayed, one plan |
| `W1-GC-033` | same key/different payload | 409, no change |
| `W1-GC-034` | concurrent different keys | one commits; other conflict; no overlap/partial Profile update |
| `W1-GC-035` | Riyadh 23:59:59 to 00:00 | current/next Diary date changes at Riyadh midnight regardless of host/browser UTC |

## 6A. W1-CD-01 Legacy Transition Scenarios

Common existing legacy input: male, birth `1996-01-01`, height `180.00`, weight `63.30`, moderate, cut, protein `1.20`, fat `0.25`, cut intensity `0.200`; pre-update resolved target is the exact Backend result `2000 kcal`, `76.0 g` protein, `299.0 g` carbohydrate, `55.6 g` fat, with its exact 16 resolved additional targets. Proposed input changes weight to `70.00` and cut intensity to `0.150`; the new plan output is recalculated by engine `2.0.0` and stored without intermediate rounding.

| ID | Exact event | Required output |
|---|---|---|
| `W1-GC-036` | Existing legacy activation `2026-07-16T12:00:00+03:00` | one snapshot dated `2026-07-16`; captured target exactly `2000/76.0/299.0/55.6`; Profile immediately `70.00/0.150`; scheduled plan effective `2026-07-17` |
| `W1-GC-037` | Resolve `2026-07-16` before and after commit | identical `2000/76.0/299.0/55.6`; after commit detail `legacy_transition_snapshot` |
| `W1-GC-038` | Resolve `2026-07-17` | effective new Target Plan result and detail `effective_target_plan` |
| `W1-GC-039` | Resolve `2026-07-15` after transition | `targets=null`, provenance `no_target_source`, detail `no_preserved_target_source` |
| `W1-GC-040` | New Profile/no prior source activates current date | current-date active plan; transition snapshot row count `0` |
| `W1-GC-041` | Replace pending plan on `2026-07-16` | original snapshot JSON hash unchanged; old pending superseded; exactly one new pending |
| `W1-GC-042` | two concurrent first activations | exactly one snapshot; one scheduled plan; one commit and one stable conflict; no overlap |
| `W1-GC-043` | failure after snapshot insert before commit | snapshot `0`; Profile unchanged; plan `0`; no completed idempotency result |
| `W1-GC-044` | `2026-07-16T23:59:59+03:00` then `2026-07-17T00:00:00+03:00` | transition date follows Riyadh date at each instant; host/browser timezone has no effect |
| `W1-GC-045` | same key/same canonical payload | original `201` body replayed; one snapshot and plan |
| `W1-GC-046` | same key/different payload | `409 IDEMPOTENCY_KEY_REUSED`; snapshot/Profile/plan unchanged |

All numeric equality is equality of persisted authoritative values, not display-text approximation. Unknown additional targets remain null and known zero remains zero.

## 7. Version Assertions

New plan: calculation `2.0.0`, Registry `1.0.0`, plan document schema per Artifact 14. New snapshot: schema2 and Registry/group/reliability/NOVA `1.0.0`. Legacy v1 and pre-plan records remain null/unversioned. Changing current rules cannot change any expected historical output above.
