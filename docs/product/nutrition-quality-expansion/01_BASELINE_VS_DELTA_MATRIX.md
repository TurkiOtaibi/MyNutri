# myNutri Baseline Versus Delta Matrix

Audit date: 2026-07-14

## 1. Classification Legend

| Classification | Meaning in this audit |
|---|---|
| Implemented and verified | Present in a reproducible baseline and supported by current automated evidence |
| Implemented but uncommitted | Present in the worktree and supported by evidence, but absent from `HEAD` |
| Partially implemented | Some required behavior exists; a material rule, integration, or verification is missing |
| New required delta | Not implemented and required for Wave 1 completion |
| Superseded historical requirement | An older requirement is explicitly or demonstrably replaced by a later decision |
| Deferred | Intentionally outside Wave 1 or awaiting a product decision |
| No change required | Existing implementation already supports the requirement without Wave 1 modification |

Because the named v1.1 decision register is unavailable, the Nutrition Quality matrix is provisional. The evidence column is authoritative; the label can be reconciled when the register is supplied.

## 2. Existing Product Decision Matrix

| Decision | Classification | Actual evidence | Exact remaining delta or disposition |
|---|---|---|---|
| D-001 Online-only; no IndexedDB/sync writes | Implemented but uncommitted | `/sync`, `frontend/lib/db.ts`, and `SyncStatus` are deleted; current router excludes sync; online-only E2E asserts no IndexedDB | Commit the removal and retain failed-write tests |
| D-002 Shell-only service worker | Partially implemented | Service worker allowlists page-shell routes and does not intercept API origins; no personal-data IndexedDB exists | Add explicit service-worker/offline runtime verification; physical PWA behavior remains unverified |
| D-003 Earlier archive delete lifecycle | Superseded historical requirement | Decision record explicitly supersedes it with D-025 | Do not revive archive behavior |
| D-004 Archive fields | Superseded historical requirement | No `is_active`/`archived_at`; D-025 supersedes | No schema/UI delta |
| D-005 Archived Food duplicate behavior | Superseded historical requirement | Hard-deleted rows are absent; duplicate service checks current rows | Govern through D-006/D-025 |
| D-006 Exact Food duplicate key | Implemented but uncommitted | `duplicate_key()` normalizes name, basis, unit type, amount, unit basis; tests cover duplicate and recreate-after-delete | Commit service/tests |
| D-007 Gram Diary logging required | Partially implemented | Per-100 source and snapshot math can support it, but API/UI only accept serving quantity | Explicitly outside current nutrition Wave 1; reconcile conflict with later “gram mode deferred” direction |
| D-008 No future Diary dates | Implemented but uncommitted | Backend validator rejects future dates; frontend disables future days; Playwright coverage exists | Commit implementation/tests |
| D-009 Profile age 10-100 | Partially implemented | Frontend rejects future date only; backend accepts any date | Add server and client 10-100 validation or formally supersede the decision |
| D-010 Quantity-only Diary edit | Superseded historical requirement | Current later meal-grouping implementation permits quantity plus meal type; Food/date/snapshot remain immutable | Formalize the later scope in the missing/current decision register |
| D-011 Exact Arabic validation | Partially implemented | Foods and Diary have structured Arabic field errors; Profile maps visible fields | Reconcile remaining exact-copy/range cases and add API/UI assertions for all Profile errors |
| D-012 Practical max values | Partially implemented | Food and Diary limits are mostly enforced; Profile height/weight only require `>0`; fat schema is 20-30% while D-012 says 15-40%; unit amount permits values below 1 | Resolve the approved ranges, then align schema/UI/tests |
| D-013 Shared API error mapping | Partially implemented | Shared `ApiError` exists; Foods field mapping is strong; page-specific state handling exists | Uniform 401/404/stale/unknown-422 behavior and cross-module tests remain incomplete |
| D-014 Food delete confirmation pattern | Superseded historical requirement | Superseded in part by D-025; current accessible hard-delete dialog exists | Govern through D-025 |
| D-015 Mobile/browser matrix | Partially implemented | Playwright covers 320/360/390/430 and desktop in several suites | Real iPhone Safari, Android Chrome, keyboard, browser bars, and safe areas remain pending |
| D-016 Single-profile v1 | No change required | One Profile resource/model; no profile switcher/ownership | Preserve |
| D-017 No Profile delete/reset | No change required | Only GET/PUT/preview routes exist | Preserve |
| D-018 Diary delete confirmation | Implemented but uncommitted | Dialog, safe cancel, API-confirmed delete, pending guard, total refresh | Commit implementation/tests |
| D-019 `serving_grams` Food source | Superseded historical requirement | Migration `0002` removes legacy fields and creates per-basis/default-unit fields | Preserve compatibility only in legacy snapshot schema |
| D-020 Long Food names | Implemented but uncommitted | Two-line list handling, full detail display, bidi markup, responsive tests | Commit implementation/tests; physical device QA pending |
| D-021 Explicit serving/gram `log_mode` | Partially implemented | Snapshot schema retains legacy `log_mode`, but create API has no `log_mode`; UI is serving-only | Defer outside Wave 1 and obtain a governing decision on gram/ml behavior |
| D-022 Exact read-failure copy | Partially implemented | Foods copies match; Profile uses `تعذر تحميل بياناتك`; Diary uses `تعذر تحميل بيانات هذا اليوم` | Determine whether newer UX copy supersedes D-022; otherwise restore exact approved text |
| D-023 Stale/retry/duplicate/a11y | Partially implemented | Pending locks, retry, input preservation, dialog focus, and live states exist | Add deterministic stale Food/Diary tests and uniform stale Arabic mapping |
| D-024 Standalone Food create/edit routes | Implemented but uncommitted | `/foods/new`, details, edit routes; no inline list form | Commit routes/components/tests |
| D-025 Hard delete, per-100 Food model, snapshots | Implemented but uncommitted | Migration/model/API/UI/tests implement hard delete, per-basis data, nullable FK, frozen snapshots | Commit `0002`, source, and regression tests |
| D-026 Optional nutrient ranges/cross-field rules | Implemented but uncommitted | Backend/frontend validation includes all listed fields and cross-field Arabic errors | Commit source/tests; preserve null versus zero |

## 3. Nutrition Quality And Progress Decision Matrix

The IDs below are audit identifiers, not replacements for the missing v1.1 register.

| ID | Approved decision | Classification | Actual evidence | Exact delta |
|---|---|---|---|---|
| NQ-001 | New protein default is `1.2 g/kg` | Implemented but uncommitted | Model/schema/Profile constants and backend test use 1.2 | Commit and expand compatibility tests |
| NQ-002 | Fat default is male 25%, female 30% | Implemented but uncommitted | Sex-aware Pydantic default and Profile constants | Commit and test save/preview for both sexes |
| NQ-003 | Carbs receive remaining calories in server engine | Implemented and verified | `calculate_targets()` retains one Python implementation; calc tests verify formula | No formula change |
| NQ-004 | Negative-carb configuration must not be silently accepted | Partially implemented | Server clamps to zero and returns `carb_clamped`; UI does not explain or block it | Add an explicit validation/warning contract and tests |
| NQ-005 | Defaults remain customizable; saved legacy values are preserved | Implemented but uncommitted | No data migration/backfill; Profile displays response values; restore is draft-only | Add explicit legacy-profile and custom-value tests |
| NQ-006 | Sex change updates only an unchanged prior default | Implemented but uncommitted | `ProfilePage` compares normalized current fat with previous sex default | Add focused tests for default-switch and custom preservation |
| NQ-007 | Profile explanation describes protein, fat, and remaining carbs | Partially implemented | Sheet mentions Mifflin and general distribution | Explain grams/kg, calorie percentage, and remaining-calorie carbs explicitly |
| NQ-008 | Fat/macro progress is visible, RTL-safe, clamped, truthful | Implemented but uncommitted | `MacroProgress` uses logical RTL CSS variables, minimum marker, ARIA, clamp, amber | Preserve focused geometry/a11y tests |
| NQ-009 | Populated Diary meals show snapshot-derived calories/macros | Implemented but uncommitted | Meal headers sum `entry.totals`; empty meals omit zero metadata | Add mutation-path aggregation tests |
| NQ-010 | One centralized additional-nutrient registry | Partially implemented | Equivalent registries exist in Python and TypeScript | Replace duplicated definitions with one repository-owned contract |
| NQ-011 | Initial set is fiber, sodium, saturated fat, added sugar, potassium, cholesterol | Implemented but uncommitted | Both registries define exactly six in approved order | Centralize and contract-test the set/order |
| NQ-012 | Fiber is fixed 30 g minimum | Implemented but uncommitted | Backend/API/frontend use 30/minimum; backend test asserts it | Remove frontend hardcoded duplicate when registry is centralized |
| NQ-013 | Cholesterol is monitor-only | Implemented but uncommitted | Registry and UI use monitor-only with no artificial progress | Add explicit UI assertion |
| NQ-014 | Sodium/saturated fat/added sugar/potassium have no fabricated targets | Implemented but uncommitted | Values are `null`; Profile states no default target | Remain deferred until product supplies numeric values |
| NQ-015 | Profile lists compact additional nutrient targets | Implemented but uncommitted | Profile renders six rows and correct configured/unconfigured states | Commit; add all-row/absence-of-fabrication tests |
| NQ-016 | Food Details shows six serving-adjusted nutrients | Implemented but uncommitted | `FoodDetailsPage` renders values and fiber contribution | Source definitions from the centralized contract |
| NQ-017 | Completeness appears only in Food Details | Implemented but uncommitted | Component exists only in Food Details; Foods E2E checks absence from list | Add absence checks for Add Food and Diary search/rows |
| NQ-018 | Completeness formula distinguishes known zero and missing | Implemented but uncommitted | `nutrientValue()` returns zero as known and null as missing; UI tests cover examples | Add threshold/core/additional formula unit coverage |
| NQ-019 | Additional nutrients are frozen in Diary snapshots | Implemented and verified | Snapshot/totals include all nullable nutrients; known zero/null backend test exists | Add historical Food-edit/delete and move tests for additional nutrients |
| NQ-020 | Quantity edit scales known values and preserves unknowns | Implemented and verified | Backend snapshot service behavior and focused test | Add API-level update assertion across multiple nutrients |
| NQ-021 | Daily Summary opens nutritional-details sheet | Implemented but uncommitted | Quiet action and six-row sheet exist | Add focus restoration, Escape, and safe-area tests |
| NQ-022 | Per-nutrient coverage is known-entry count / total entries | Implemented but uncommitted | Frontend aggregation uses this formula and counts numeric zero as known | Centralize/test the aggregation helper |
| NQ-023 | All-unknown nutrient must remain unknown, not displayed as zero | Partially implemented | Backend is correct; Diary UI initializes sum to zero and shows `0 ... على الأقل` when `known=0` | Render `غير متوفر`, suppress target progress/status, retain 0 only for known zero |
| NQ-024 | Overall coverage is average supported per-nutrient coverage | Implemented but uncommitted | Diary computes arithmetic mean for non-empty days | Add exact multi-entry/mixed-known tests |
| NQ-025 | No nutrition-quality database migration unless necessary | No change required | Food columns and JSONB snapshots already support nullable values | Do not add a migration; only version existing `0002`/`0003` dependencies |

## 4. Deferred Decisions

| Item | Classification | Reason |
|---|---|---|
| Numeric sodium maximum | Deferred | No approved numeric target |
| Numeric saturated-fat maximum | Deferred | No approved numeric target |
| Numeric added-sugar maximum | Deferred | No approved numeric target |
| Numeric potassium minimum | Deferred | No approved numeric target |
| Field-level estimated/provenance marker | Deferred | Current schema has only general `data_source`/notes; no approved migration |
| Direct gram/ml Diary logging | Deferred | Current UI and API are serving-only; D-007/D-021 conflict remains unresolved |
| Physical-device sign-off | Deferred | No current real iPhone Safari or Android Chrome execution |
| Health score or Food-quality score | No change required | Explicitly excluded; completeness is data availability only |

## 5. Decision Coverage Verdict

- The implemented product is materially ahead of `HEAD` and of the old system/architecture documents.
- Most Nutrition Quality behavior exists, but the expansion is not complete because NQ-010 and NQ-023 are material gaps.
- The exact “every approved decision” assertion cannot be finalized until the named v1.1 register is available.
- No new nutrition-quality database migration is justified by the current schema.
