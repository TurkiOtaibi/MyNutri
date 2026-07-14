# Foods Test Cases Audit

Audit status: report only.
Application code changed: No.
BA files changed: No.
CSV rewritten: No.
Automated tests implemented: No.

## 1. Overall Verdict

Verdict: Partially Ready
Quality score: 8/10

The regenerated Foods test suite has strong breadth: all approved Foods user stories are covered, all test IDs are unique, the CSV has the required 20-column structure, and the suite is aligned with the current v1 direction: D-024 standalone Food pages, D-025 permanent hard delete, D-026 optional nutrient validation, per 100g/per 100ml source of truth, online-only behavior, Arabic/RTL, mobile, and accessibility basics.

It is not fully Ready because 9 cases contain weak or flexible wording, 1 case is a non-executable scope review rather than a test case, and several Arabic/error-copy and legacy sugar-mapping checks need more exact assertions before formal manual QA execution or automation planning.

## 2. Audit Metrics

| Metric | Result |
|---|---:|
| Test cases reviewed | 141 |
| CSV columns | 20 |
| Unique test IDs | 141 |
| Duplicate test IDs | 0 |
| Duplicate scenario signatures | 0 |
| Foods user stories covered | 10 of 10 |
| Feature groups covered | 12 |
| Duplicate cases count | 0 |
| Weak or vague cases count | 9 |
| Active outdated requirement references count | 0 |
| Intentional scope-guard references to old requirements | 4 |
| Missing / insufficiently specific coverage areas | 5 |

## 3. Alignment With Final Foods Decisions

| Requirement | Audit result | Evidence |
|---|---|---|
| D-024 Add Food as standalone page | Covered | `FOOD-TC-001` to `FOOD-TC-007`; Add page, details route, edit route, no inline large form, no delete on Add page. |
| D-025 permanent Food hard delete | Covered | `FOOD-TC-119` to `FOOD-TC-128`; confirmation, cancel, confirm, catalog removal, future Diary selection removal, snapshot preservation. |
| D-026 optional nutrient ranges | Covered | `FOOD-TC-076` to `FOOD-TC-100`; optional blank behavior, min/max, cross-field rules. |
| Per 100g/per 100ml source of truth | Covered | `FOOD-TC-036`, `FOOD-TC-037`, `FOOD-TC-047`, core field validation cases. |
| No archive/inactive v1 behavior | Covered as absence/scope guard | `FOOD-TC-012`, `FOOD-TC-125`, `FOOD-TC-141`. These do not reintroduce archive behavior; they assert absence. |
| No `is_active` / `archived_at` | Covered as absence/scope guard | `FOOD-TC-012`, `FOOD-TC-125`. |
| No Active/Archived filters | Covered as absence/scope guard | `FOOD-TC-012`, `FOOD-TC-125`, `FOOD-TC-141`. |
| Deleted Foods disappear from future Diary selection | Covered | `FOOD-TC-013`, `FOOD-TC-122`. |
| Diary snapshot remains safe after Food hard delete | Covered | `FOOD-TC-123`; also supported by edit snapshot case `FOOD-TC-115`. |
| Optional nutrients collapsed by default | Covered | `FOOD-TC-039`. |
| `sugar_g` / `added_sugar_g` mapping | Partially covered | `FOOD-TC-094`, `FOOD-TC-095`; missing explicit `total_sugars_g` legacy/current-code naming check. |
| `fiber_g <= carb_g` | Covered | `FOOD-TC-093`. |
| `added_sugar_g <= sugar_g` only when both provided | Covered | `FOOD-TC-094`, `FOOD-TC-095`. |
| `saturated_fat_g + trans_fat_g <= fat_g` | Covered | `FOOD-TC-098`. |
| Online-only behavior | Covered | `FOOD-TC-025`, `FOOD-TC-042`, `FOOD-TC-110`, `FOOD-TC-137`, `FOOD-TC-138`. |
| Arabic validation and error messages | Partially covered | Many cases assert Arabic messages, but several API/read/delete-dialog cases should assert exact copy. |
| Mobile RTL behavior | Covered | `FOOD-TC-005`, `FOOD-TC-009`, `FOOD-TC-017`, `FOOD-TC-026`, `FOOD-TC-034`, `FOOD-TC-116`, `FOOD-TC-139`. |
| Accessibility for forms, dialogs, buttons, errors | Covered, with minor specificity gaps | `FOOD-TC-027`, `FOOD-TC-126`, `FOOD-TC-136`, `FOOD-TC-137`; default accessibility column is too generic across many rows. |

## 4. Duplicate And Outdated Reference Review

Duplicate test IDs: 0.
Duplicate scenario signatures: 0.

No test case asserts archive/inactive behavior as a v1 product feature. The following old-requirement references are intentional negative/scope-guard checks:

| Test case ID | Reference type | Audit result |
|---|---|---|
| `FOOD-TC-012` | No Status/Archived/Active filter, `is_active`, `archived_at` | Valid v1 absence check. |
| `FOOD-TC-047` | No serving-based nutrition source of truth | Valid v1 absence check. |
| `FOOD-TC-125` | No archive/inactive/delete-restore behavior | Valid v1 absence check. |
| `FOOD-TC-141` | No undocumented sorting/filtering or Active/Archived filter tests | Valid intent, but should be moved out of CSV because it is not an executable test case. |

Active outdated requirement references count: 0.

## 5. Weak Or Vague Cases

| Test case ID | Issue | Severity | Why it matters | Recommended fix |
|---|---|---|---|---|
| `FOOD-TC-004` | Expected result says "clearly in edit mode" without defining observable signals. | Low | Manual testers may interpret this differently. | State exact checks: route is `/foods/:id/edit`, form is prefilled, title/action copy indicates edit, Add-only delete restriction does not apply. |
| `FOOD-TC-018` | Expected result says "according to documented search behavior." | Medium | It does not define the actual partial-match expectation. | Replace with explicit expectation: matching Food names containing the query are shown; non-matching names are hidden; Arabic/English terms remain readable. |
| `FOOD-TC-030` | Expected result says retry is available "if documented." | Medium | Final BA recheck says read failure includes retry path; this should not be conditional. | Require retry/reload path and exact Foods-list failure copy. |
| `FOOD-TC-070` | Steps say "Save with each allowed type as applicable." | Low | Test data is parameterized but not concrete enough for execution. | Convert to explicit parameterized rows or list all unit types in the steps. |
| `FOOD-TC-100` | Expected result allows two alternatives: error visible or section opens/focuses. | Medium | Automation needs one deterministic expected state. | Require invalid optional section to expand and focus/announce the invalid field. |
| `FOOD-TC-108` | Expected result allows implementation-dependent unchanged-submit behavior. | Medium | It is not a single testable outcome. | Define expected behavior or convert to exploratory note. Preferred: submit is disabled until changes, or save is idempotent with no data mutation, but not both in one case. |
| `FOOD-TC-113` | Expected result says "according to API contract." | Medium | The expected error/result is not fully testable from the row. | Use exact stale/refresh-required Arabic message and require no silent overwrite. |
| `FOOD-TC-140` | Preconditions depend on "if test data supports it." | Low | The case may be skipped without a concrete data requirement. | Define exact large-catalog seed requirement or move to exploratory/performance checklist. |
| `FOOD-TC-141` | Scope review row, not an executable product test. | Medium | CSV is meant for test cases; this row is audit metadata. | Move to summary/report notes or rewrite as executable UI absence checks already covered by `FOOD-TC-012` and `FOOD-TC-125`. |

Weak or vague cases count: 9.

## 6. Missing Or Insufficiently Specific Coverage Areas

| Gap | Severity | Evidence | Recommended fix |
|---|---|---|---|
| `total_sugars_g` legacy/current-code naming is not explicitly covered. | Medium | Final cleanup recheck requires `sugar_g = total sugar`, `added_sugar_g = added sugar`, and `total_sugars_g` as legacy/current-code naming only; CSV has 0 `total_sugars_g` references. | Add one test confirming current BA/API uses `sugar_g`, while `total_sugars_g` is not presented as the current v1 field except as migration/legacy handling if implementation exposes it. |
| Exact Arabic Food delete dialog copy is not asserted. | Medium | `FOOD-TC-119` checks Food name and permanent deletion text but not exact dialog title/body/buttons from `docs/ba/06_ERROR_MESSAGES.md`. | Add or refine a case to assert title, body with Food name, confirm button, cancel button, Escape/cancel behavior, and focus return. |
| Exact Arabic read-failure copy is not consistently asserted for Food detail/edit. | Medium | `FOOD-TC-031`, `FOOD-TC-032`, and `FOOD-TC-131` use generic "Arabic read-failure message" wording. | Add exact expected copy for Food detail/edit load failure from the error-message matrix. |
| API error mapping copy is partially generic. | Low | Several 401/422/5xx/network cases say Arabic error appears without exact message. | Add exact Arabic expected messages for 401, 422, 5xx, network write failure, stale Food, and duplicate submit where the BA defines exact copy. |
| Optional text max-length tests lack exact boundary data. | Low | Brand/category/notes/data-source cases say "over max" but do not list exact max values from the field dictionary. | Replace with exact boundary values: brand 80, category 80, notes 500, data source 120, and one-over-limit values. |

Missing / insufficiently specific coverage count: 5.

## 7. Quality Checks

| Check | Result | Notes |
|---|---|---|
| Unique test IDs | Passed | 141 unique IDs. |
| Correct feature mapping | Mostly passed | Feature groups are coherent. `FOOD-TC-141` should be moved to summary rather than kept as a test case. |
| Correct user story mapping | Passed | All 10 approved Foods user stories have coverage. |
| Clear title / scenario | Mostly passed | 9 cases need clearer wording. |
| Executable steps | Mostly passed | Most rows are executable; `FOOD-TC-141` is not. |
| Testable expected result | Mostly passed | Weak cases listed above need deterministic expected results. |
| Correct priority | Passed with minor note | P0/P1/P2 distribution is reasonable. `FOOD-TC-141` should not be a test case priority row. |
| No duplicate or overlapping cases | Passed | No duplicate IDs or duplicate scenario signatures found. |
| No vague "verify works" wording | Passed | No "verify works" language found. Some alternative/conditional phrasing remains. |
| No outdated archive/serving/offline assumptions | Passed | Old terms appear only as absence checks or online-only guards. |
| Boundary and negative scenario coverage | Mostly passed | Strong D-026 and core numeric coverage; optional text exact boundaries need refinement. |

## 8. Recommended Fixes

1. Rewrite the 9 weak rows listed in section 5 with deterministic expected results.
2. Move `FOOD-TC-141` out of the CSV into the summary, or rewrite it as an executable absence check.
3. Add one explicit sugar-mapping test for `total_sugars_g` as legacy/current-code naming only.
4. Add exact Arabic-copy assertions for the Food delete dialog and Food detail/edit read-failure states.
5. Replace generic optional-text "over max" data with exact boundary values from the field dictionary.
6. Replace generic coverage-column wording such as "where applicable" with row-specific notes during the next CSV refinement, especially for automation candidates.

## 9. Manual QA Readiness

Manual QA execution readiness: Partially Ready.

The suite is usable as a strong draft for manual QA, but formal execution should wait until the 9 weak rows and 5 specificity gaps are corrected. Without those corrections, testers may execute some cases inconsistently or mark implementation-dependent outcomes as pass/fail inconsistently.

## 10. Automation Planning Readiness

Automation planning readiness: Partially Ready.

Good candidates for automation already exist:
- Route/page structure.
- Create/edit/delete happy paths.
- Required/core numeric validation.
- D-026 optional nutrient validation.
- Duplicate handling.
- Search/no-results.
- Online-only write failure.
- Snapshot integrity after Food delete.

Automation blockers before conversion:
- Non-deterministic expected results in weak rows.
- Generic Arabic error expectations in several API/read-failure cases.
- Missing exact test data for optional text max-length cases.
- One non-executable scope-review row.

## 11. Recommended Next Step

Update the CSV once more with targeted cleanup only:

1. Fix the 9 weak rows.
2. Add or refine the 5 missing/specificity areas.
3. Keep all current BA decisions unchanged.
4. Do not add archive/inactive behavior, serving-based source-of-truth behavior, or offline-first behavior.

After that cleanup, the Foods test cases should be Ready for manual QA and stronger automation planning.
