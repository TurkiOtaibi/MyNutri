# Wave 1 Traceability Matrix

Audit date: 2026-07-14

## 1. Traceability Rules

- **Current evidence** means actual source/schema/test evidence, not a report claim.
- **Preserve** identifies regression coverage that must remain.
- **Required test** is the minimum additional characterization/acceptance evidence for Wave 1.
- Provisional IDs are used because the named v1.1 register is unavailable.

## 2. Profile And Calculation Traceability

| ID | Requirement | Current source evidence | Existing test evidence | Classification | Required test/delta |
|---|---|---|---|---|---|
| NQ-P01 | Protein default 1.2 both sexes | `models.py`, `schemas.py`, `ProfilePage.tsx` | `test_new_profile_defaults_are_sex_compatible` | Implemented but uncommitted | API create/preview/save for male and female |
| NQ-P02 | Male fat 25%, female 30% | Pydantic before-validator; frontend constants | Backend default test; Profile restore E2E | Implemented but uncommitted | Omitted-value API test and saved-response test |
| NQ-P03 | Existing saved legacy values stay unchanged | No data migration; GET maps persisted values | Indirect Profile E2E | Partially implemented | Explicit DB/service test with 1.8 and female 0.25 |
| NQ-P04 | Custom protein/fat remain customizable | Profile advanced inputs; PUT payload | Profile ratio/restore tests | Implemented but uncommitted | Custom values survive sex switch and save |
| NQ-P05 | Sex switch changes only previous default fat | Normalized comparison in `ProfilePage` | No focused two-branch assertion | Partially implemented | Previous-default switches; custom value preserved |
| NQ-P06 | Restore Defaults is sex-aware and draft-only | Profile restore dialog/action | Profile E2E | Implemented but uncommitted | Assert no PUT before save for both sexes |
| NQ-P07 | Preview and save share server engine | `preview_targets()` and `to_profile_response()` call same service | Preview/direct test; Profile E2E | Implemented but uncommitted | Same payload POST preview then PUT equals macro results |
| NQ-P08 | Mifflin/activity/goal unchanged | `calc.py` constants/formula | `test_calc.py`, factor assertions | Implemented and verified | Preserve all calc tests |
| NQ-P09 | Carbs receive remaining calories | `calc.py` lines 54-60 | Formula test | Implemented and verified | Add sanity scenario exact rounded output |
| NQ-P10 | Negative carbs not silent | `carb_clamped` returned but not surfaced | Clamp test only checks nonnegative | Partially implemented | Approved reject/warning API and UI assertion |
| NQ-P11 | Explanation states grams/kg, fat %, remaining carbs | Current copy is generic | Profile sheet existence only | Partially implemented | Exact user-facing content test |
| NQ-P12 | Fiber 30 g minimum in Profile | Additional targets API/UI | Backend registry test; broad UI test | Implemented but uncommitted | Contract test from shared registry through API/UI |
| NQ-P13 | Cholesterol monitor-only; four targets unconfigured | Registry/API/Profile rows | Broad UI and backend registry tests | Implemented but uncommitted | Per-row no-fabricated-number assertions |

## 3. Food And Completeness Traceability

| ID | Requirement | Current source evidence | Existing test evidence | Classification | Required test/delta |
|---|---|---|---|---|---|
| NQ-F01 | Six priority nutrients available in Food schema | Food model/schema/migration `0002` | Foods optional nutrient tests | Implemented but uncommitted | Preserve boundary/null tests |
| NQ-F02 | Details show serving-adjusted nutrient values | Food Details uses serving multiplier and registry | Broad nutrition E2E | Implemented but uncommitted | Assert each six field and rounding |
| NQ-F03 | Fiber target contribution only when configured | Food Details percentage condition | Visual evidence only | Partially implemented | Fiber percent; no percent for four unconfigured/monitor-only |
| NQ-F04 | Missing displays `غير متوفر` | Value null branch | Nutrition E2E | Implemented but uncommitted | One assertion per null/zero class |
| NQ-F05 | Explicit zero displays zero | `nutrientValue()` recognizes finite zero | Nutrition E2E | Implemented but uncommitted | Direct zero assertion in Details |
| NQ-F06 | Completeness only in Food Details | Component placement | List absence assertion | Implemented but uncommitted | Add absence checks in Add Food, Diary search, Diary rows |
| NQ-F07 | Core completeness | Four core values checked with null-safe condition | No focused threshold test | Partially implemented | Unit/component tests for 0-4 availability |
| NQ-F08 | Additional completeness | Six registry values checked | Broad missing-list test | Partially implemented | Exact numerator/denominator and zero-known tests |
| NQ-F09 | Overall completeness and status thresholds | Food Details calculation/status function | No focused threshold matrix | Partially implemented | 49/50/74/75/89/90/100 boundary tests |
| NQ-F10 | Expanded list shows supported missing only | Registry-filtered missing list | Broad E2E | Implemented but uncommitted | Assert no unrelated metadata/unsupported nutrient |
| NQ-F11 | Estimated values count if provenance exists | No field-level provenance model | None | Deferred | No migration; document current limitation |

## 4. Diary Snapshot And Meal Traceability

| ID | Requirement | Current source evidence | Existing test evidence | Classification | Required test/delta |
|---|---|---|---|---|---|
| NQ-D01 | Snapshot captures supported nullable nutrients | `DETAIL_FIELDS`, `make_snapshot()` | Known-zero/null test | Implemented and verified | Assert all six keys at API create |
| NQ-D02 | Food edits do not mutate old nutrient snapshots | Snapshot stored JSONB; reads use snapshot | Core snapshot tests | Partially verified | Additional-nutrient Food edit regression |
| NQ-D03 | Food delete preserves historical nutrient snapshots | nullable FK + JSONB | Foods snapshot tests | Partially verified | Additional-nutrient hard-delete assertion |
| NQ-D04 | Quantity edit scales known, preserves unknown | `totals_from_snapshot()`, `update_entry()` | Focused service test | Implemented and verified | API PUT test with zero/null/positive fields |
| NQ-D05 | Meal move preserves snapshot | Update changes only meal type and calculated totals | No dedicated nutrient assertion | Partially implemented | Compare snapshot source fields before/after move |
| NQ-D06 | Populated meal shows count/calories/macros | Meal section sums entry totals | Broad nutrition E2E | Implemented but uncommitted | Add/edit/move/delete immediate update tests |
| NQ-D07 | Empty meal hides zero totals/macros | Empty metadata branch | Diary suites | Implemented but uncommitted | Explicit absence assertion |
| NQ-D08 | Macro progress visible/RTL/clamped/truthful | `MacroProgress`, logical CSS | Final polish tests | Implemented but uncommitted | Preserve 0/1/9/22/100/over tests |

## 5. Diary Nutritional Details And Coverage Traceability

| ID | Requirement | Current source evidence | Existing test evidence | Classification | Required test/delta |
|---|---|---|---|---|---|
| NQ-N01 | Daily Summary action opens details | Diary action/modal | Broad nutrition E2E | Implemented but uncommitted | Focus return/Escape/safe-area assertions |
| NQ-N02 | Six nutrients in approved order | Registry mapping | Broad E2E | Implemented but uncommitted | Exact order assertion from shared contract |
| NQ-N03 | Minimum target behavior | Generic row logic; fiber configured | No below/achieved/above matrix | Partially implemented | Fiber remaining, achieved, above-no-warning |
| NQ-N04 | Maximum behavior | Generic row logic | No configured target in product | Deferred | Unit-test helper with synthetic config; no product number |
| NQ-N05 | Range behavior | Generic types supported | No configured target or test | Deferred | Pure helper test only if range remains in contract |
| NQ-N06 | Monitor-only behavior | Cholesterol row suppresses progress | Broad UI text only | Implemented but uncommitted | Explicit no progress/percentage assertion |
| NQ-N07 | Unconfigured target has no fabricated progress | Null target suppresses progress | Profile broad test; Diary not focused | Implemented but uncommitted | Sodium/potassium row assertions |
| NQ-N08 | Per-nutrient coverage formula | Known count / entry count | Broad one-entry test | Partially implemented | Mixed 0/null/positive multi-entry cases |
| NQ-N09 | Known zero counts as known | Numeric finite check | One backend/UI scenario | Implemented but uncommitted | Multi-entry coverage exact percentage |
| NQ-N10 | All unknown remains unknown | Backend aggregate is null; frontend amount starts at zero | Existing test expects `على الأقل` | Partially implemented | Fix and assert `غير متوفر`, no fake progress |
| NQ-N11 | Partial known total labeled `على الأقل` | Coverage branch | Broad sodium scenario with all unknown only | Partially implemented | One known + one null exact sum/coverage/copy |
| NQ-N12 | Overall coverage is average of six | Arithmetic mean in Diary | No exact mixed matrix | Partially implemented | Exact six-nutrient fixture calculation |
| NQ-N13 | Empty day has no fake zero rows | Empty modal branch | Diary empty tests, not nutrient sheet | Partially implemented | Open details on empty day and assert calm empty state |
| NQ-N14 | Data coverage is not a health score | Coverage notice copy | Visual screenshot | Implemented but uncommitted | Text and absence-of-score assertion |
| NQ-N15 | Loading/failure/retry | Sheet uses already-loaded day data; day error blocks valid content | Day load retry tests | No change required | Document no separate request; preserve day error tests |

## 6. Architecture And Contract Traceability

| ID | Requirement | Current source evidence | Existing test evidence | Classification | Required test/delta |
|---|---|---|---|---|---|
| NQ-A01 | One central nutrient registry | Two parallel registry files | Equality not contract-tested | Partially implemented | One shared source and generated/loaded identity test |
| NQ-A02 | Target types minimum/maximum/range/monitor-only | Python/TS literal unions | Registry test covers minimum/monitor only | Partially implemented | Schema/contract tests for all enum values |
| NQ-A03 | Target sources fixed/calculated/reference/manual/clinical | Python/TS unions | None | Partially implemented | Schema validation test |
| NQ-A04 | Only fiber gets new numeric target | Both registries/API | Backend registry test | Implemented but uncommitted | Preserve; assert four null targets and cholesterol null |
| NQ-A05 | No client target formulas | Profile uses server preview/save | Profile E2E | Implemented but uncommitted | Preserve no-formula architecture review/test boundary |
| NQ-A06 | No new nutrition migration | Existing nullable columns/JSONB | Migration report only | No change required | Rehearse existing chain; assert no backfill |
| NQ-A07 | API additions backward compatible | Optional/default `additional_targets` | No old-client schema test | Partially implemented | Deserialize response without field and with field |
| NQ-A08 | Online-only | API fetch no-store; no Dexie/sync | Foods online-only E2E | Implemented but uncommitted | Preserve all failed-write/no-queue tests |

## 7. Existing Tests That Must Be Preserved

### Backend

- `backend/tests/test_calc.py`
- `backend/tests/test_diary_snapshot.py`
- `backend/tests/test_foods.py`
- `backend/tests/test_foods_batch_import.py`
- `backend/tests/test_nutrition_quality.py`
- Disabled future-scope sync marker in `backend/tests/test_sync.py`

### Frontend

- Entire `frontend/e2e/foods/` suite.
- Entire `frontend/e2e/diary/` suite.
- Entire `frontend/e2e/profile/` suite.
- `frontend/e2e/nutrition-quality.spec.ts`.
- `frontend/e2e/nutrition-quality-visual.spec.ts`.

### Build/quality

- Frontend typecheck.
- Frontend production build.
- Ruff.
- `git diff --check`.

## 8. New Required Test Packages

1. `backend/tests/test_nutrient_registry_contract.py`: one-source registry, order, metadata, only-fiber numeric target.
2. Extend `backend/tests/test_nutrition_quality.py`: legacy Profile values, preview/save equivalence, explicit negative-carb outcome.
3. Extend `backend/tests/test_diary_snapshot.py`: all six nutrients across create/edit/move/Food edit/Food delete.
4. Frontend pure/unit coverage for completeness and daily nutrient aggregation, or focused Playwright fixtures if no unit runner is introduced.
5. Extend Profile Playwright: sex-default/custom preservation and exact calculation explanation.
6. Extend Diary Playwright: null-only, known-zero, partial coverage, overall coverage, target-type states, and mutation updates.
7. Extend Food Details Playwright: all six values, zero/null, thresholds, missing list, and absence outside Details.
8. Responsive/a11y coverage at 320/360/390/430 for the nutritional-details sheet.

## 9. Traceability Verdict

The expansion has broad end-to-end presence but insufficient requirement-level proof. The highest-value tests are the null/zero coverage matrix, the shared registry contract, and snapshot-preservation mutation paths. Those must precede final Wave 1 completion status.
