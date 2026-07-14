# V2 QA Remediation Summary

This file records the BA remediation applied after the fresh QA audit under `docs/qa/user-story-audit-v2/`.

Application code changed: No.
QA audit files changed: No.
Implementation tasks created: No.

## Remediation Outcome

| Metric | Result |
|---|---:|
| Critical BA issues in v2 audit | 0 |
| High BA issues in v2 audit | 2 |
| High BA issues resolved in BA | 2 |
| Product decisions added | 3 |
| New decisions | D-021, D-022, D-023; latest Food decisions D-024, D-025, and D-026 added after this v2 remediation |
| User stories after remediation | 40 |
| Features after remediation | 45 |
| Remaining product open questions | 0 |
| Remaining BA gaps from v2 audit | 0 |
| Remaining implementation alignment items | 19 |

## Latest Food Decision Update - D-024/D-025

After the v2 remediation, Product changed the Food page scope. The following updates supersede the earlier archive-oriented remediation:

| Decision | Current requirement | Prior content superseded | Status |
|---|---|---|---|
| D-024 | Add Food is a standalone page at `/foods/new`; Food detail is `/foods/:id`; Food edit is `/foods/:id/edit`; `/foods` remains a browse/search/list page. | Inline or same-page large Add Food form assumptions. | Applied to BA package. |
| D-025 | Food deletion is permanent hard delete with confirmation. | Archive-only delete, `is_active`, `archived_at`, archived status, Active/Archived filters. | Applied to BA package. |
| D-025 | Food nutrition source of truth is per 100g/per 100ml. | Serving-based nutrition source-of-truth and `serving_grams` field assumptions. | Applied to BA package. |
| D-025 | Optional nutrients are supported, optional, and collapsed by default. | Smaller optional nutrient scope. | Applied to BA package. |
| D-025 | Diary snapshot must remain readable after Food deletion. | Snapshot-after-archive wording. | Applied to BA package. |
| D-026 | Optional nutrient max ranges and cross-field rules are defined. | Previously unresolved optional nutrient max ranges. | Applied to BA package. |

QA impact:
- Existing test cases generated before D-024/D-025 are impacted and must be rewritten before execution.
- Replace Food archive tests with permanent-delete confirmation, no-archive-UI, duplicate-after-delete, and snapshot-after-delete tests.
- Add tests for standalone Add/Edit routes, per-100g/per-100ml fields, default unit fields, optional nutrients, mobile cards, and long-name RTL behavior.
- Add D-026 tests for optional nutrient blank values, zero values, negative values, above-maximum values, and cross-field validation.

## Foods Final Decision Audit Cleanup

The cleanup after `docs/qa/foods-final-decision-audit/00_FOODS_FINAL_DECISION_AUDIT.md` resolved the remaining Foods BA gaps:

| Audit gap | Cleanup applied | Status |
|---|---|---|
| Current Food search story missing | Added current `US-FOOD-HAPPY-002` and matching acceptance criteria for search, no-results, network failure, mobile, and RTL behavior. | Resolved in BA |
| Current Food state-handling story missing | Added current `US-FOOD-STATE-001` for loading, empty, no-results, read-failure, retry, mobile, and RTL behavior. | Resolved in BA |
| Current Food edit story missing | Added current `US-FOOD-CRUD-002` for standalone edit page, prefill, validation, duplicate blocking, stale Food, API failure, and snapshot integrity. | Resolved in BA |
| `sugar_g` mapping incomplete | Clarified that `sugar_g` is total sugar, `added_sugar_g` is added sugar, both are optional per 100g/per 100ml, and `total_sugars_g` is legacy/current-code naming. | Resolved in BA |
| Stale archive/serving wording | Replaced active/archive and `serving_grams` current-v1 wording with permanent-delete, current catalog, per-100g/per-100ml, and default-unit terminology. | Resolved in BA |

Remaining impact:
- Current code and previously generated QA test cases still need implementation/test alignment to the cleaned BA package.
- No Food archive/inactive behavior is a v1 requirement.
- Serving/default unit metadata is for logging and display convenience; Food nutrition source of truth remains per 100g/per 100ml.

## Fixes Applied

| V2 audit issue | Severity | BA fix applied | Updated files | Status | Remaining risk |
|---|---|---|---|---|---|
| Gram-mode Diary API/storage contract ambiguous | High | Added D-021 and propagated exact create/edit payloads, mode-specific `quantity`, snapshot structure, `serving_multiplier`, `calculated_totals`, and aggregation rules. | `01`, `02`, `03`, `04`, `05`, `07`, `08`, `09`, `10`, `11`, `13`, `14` | Resolved in BA | Current code still needs implementation alignment. |
| Exact Arabic read-failure copy missing | High | Added D-022 and exact messages for Profile, Foods list, Food detail, Diary day, Weekly summary, and general reads. | `01`, `05`, `06`, `07`, `08`, `09`, `10`, `11`, `13`, `14` | Resolved in BA | Current UI/cached fallback behavior may still need alignment. |
| Vague acceptance criteria wording | Medium | Replaced vague phrases with objectively testable behavior for validation, failed writes, target preview, focus behavior, status regions, and API errors. | `04`, `05`, `06`, `07`, `08`, `09`, `13` | Resolved in BA | None in BA. |
| Stale item and duplicate-submit edge criteria missing | Medium | Added D-023, stale Food/Diary messages, one-request pending-submit behavior, retry behavior, and minimum a11y behavior. | `05`, `06`, `07`, `08`, `09`, `10`, `11`, `13`, `14` | Resolved in BA | Current UI/API implementation likely needs alignment. |
| Offline page/metadata and cached-read fallback traceability missing | Medium | Added Future Scope/alignment coverage for offline page, service worker API caching, IndexedDB cached reads, and cached-read fallbacks. | `01`, `02`, `03`, `08`, `09`, `10`, `11`, `14` | Resolved in BA | Current code still contains offline/sync artifacts. |
| Health/config traceability weak | Low | Added `US-INFRA-READ-001`, `US-CONFIG-SEC-001`, and traceability rows. | `07`, `09`, `10` | Resolved in BA | None in BA. |
| QA test data matrix missing | Low | Added QA test data acceptance criterion and test gap for boundary/stale/duplicate-submit/gram/read-failure data. | `07`, `09`, `10`, `11` | Resolved in BA | Test cases still need to be written later. |

## Decisions Added

| Decision | Summary | Status |
|---|---|---|
| D-021 | Diary entries use explicit `log_mode` with one mode-specific `quantity`; snapshots store Food identity, nutrition basis, nutrition values at logging time, default-unit data used for calculation, mode, logged quantity, and calculated totals. | Applied |
| D-022 | Exact Arabic read-failure copy is defined for each major read surface. | Applied |
| D-023 | Stale item handling, duplicate-submit prevention, retry behavior, and minimum accessibility behavior are defined. | Applied |

## Remaining Implementation Alignment Items

These are code alignment items, not unresolved BA gaps:

1. Failed Profile, Food, and Diary writes currently use local queue/cached behavior.
2. Service worker, offline page/metadata, sync route, sync status UI, and cached-read fallbacks still exist in code.
3. Food archive fields and archive-only delete are superseded by D-025; current implementation still needs D-025 confirmation/copy and snapshot-after-delete verification.
4. Duplicate current-catalog Food blocking and D-026 optional nutrient validation are not implemented.
5. Diary gram mode, `log_mode`, D-021 snapshot structure, and quantity-only edit UI are not implemented.
6. Exact D-022 read-failure copy is not verified in UI.
7. D-023 duplicate-submit, stale item, retry, focus, live-region, and dialog behaviors require implementation alignment.

## Readiness

BA readiness after remediation: Ready, target 9/10 or higher.
Implementation planning can start: Yes, from a BA standpoint.
QA test case generation can start: Yes, from a BA standpoint.
