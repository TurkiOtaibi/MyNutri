# QA Audit Remediation Summary

This file maps the QA audit findings under `docs/qa/user-story-audit/` and `docs/qa/user-story-audit-v2/` to the BA updates applied in this package.

## Summary

| Metric | Count |
|---|---:|
| Critical QA findings reviewed | 2 |
| Critical findings resolved in BA requirements | 2 |
| High QA findings reviewed | 9 |
| High findings resolved or partially resolved in BA requirements | 9 |
| Product decisions applied | 26 |
| Remaining implementation alignment items | 19 |
| Remaining product open questions | 0 |

## Latest Food Decision Update - D-024/D-026

The latest Food page decisions supersede prior archive/inactive remediation:

| Area | Previous remediation | Current D-024/D-026 status | Remaining risk |
|---|---|---|---|
| Food page structure | Foods list included CRUD behavior in the same page/component evidence. | Add Food is a standalone `/foods/new` page; details `/foods/:id`; edit `/foods/:id/edit`; no large inline Add Food form on `/foods`. | Current UI/routes need implementation alignment. |
| Food delete lifecycle | D-003/D-004/D-005/D-014 previously defined archive-only delete with `is_active` and `archived_at`. | Superseded. Food delete is permanent hard delete with confirmation; no archive/inactive state or filters. | BA/test artifacts and implementation plan must stop treating archive as v1. |
| Food data model | Serving-based nutrition and `serving_grams` were used as source-of-truth assumptions. | Superseded. Food nutrition source of truth is per 100g/per 100ml plus default-unit fields. | Current code/schema/test cases need alignment. |
| Diary snapshot | Snapshot protected history after Food edit/archive. | Snapshot must protect history after Food edit/delete and preserve Food name, nutrition basis, nutrition values, logged quantity, log mode, and calculated totals. | Current snapshot/display may still depend on Food records. |
| Duplicate handling | Archived Foods did not block duplicates. | Deleted Foods do not block duplicates because they no longer exist; duplicate key uses current-catalog `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`. | Duplicate service/schema missing. |
| Optional nutrient validation | Optional nutrient max ranges remained unresolved. | D-026 defines optional blank behavior, numeric `>= 0`, max values, and cross-field rules for fiber, added sugar, saturated fat, and trans fat. | Current code/schema/test cases need D-026 alignment. |

## Fresh V2 QA Audit Remediation

| V2 QA finding | Severity | Decision or fix applied | Updated BA files | Status | Remaining risk |
|---|---|---|---|---|---|
| V2-BA-HIGH-001: Gram-mode Diary API/storage contract ambiguous | High | D-021 defines `log_mode`, mode-specific `quantity`, create/edit payloads, snapshot structure, `serving_multiplier`, `calculated_totals`, and aggregation source. | `01`, `02`, `03`, `04`, `05`, `07`, `08`, `09`, `10`, `11`, `13` | Resolved in BA | Current code still lacks gram-mode API/UI and `log_mode` persistence. |
| V2-BA-HIGH-002: Exact Arabic read-failure copy missing | High | D-022 defines exact read-failure copy for Profile, Foods list, Food detail, Diary day, Weekly summary, and general reads. | `01`, `05`, `06`, `07`, `08`, `09`, `10`, `11`, `13` | Resolved in BA | Current UI may still use broad error copy or cached fallback behavior. |
| V2-BA-FIX-003: Vague acceptance criteria wording | Medium | Replaced vague phrases with concrete behavior for field errors, failed writes, target preview, focus handling, and status announcements. | `04`, `05`, `06`, `07`, `08`, `09`, `13` | Resolved in BA | Implementation must match exact copy/behavior. |
| V2-BA-FIX-004: Stale entity and duplicate-submit criteria missing | Medium | D-023 adds stale Food, stale Diary entry, duplicate-submit, pending state, retry, and focus/live-region/dialog behavior. | `05`, `06`, `07`, `08`, `09`, `10`, `11`, `13` | Resolved in BA | Current forms/dialogs need alignment. |
| V2-BA-FIX-005: Offline page/metadata and cached-read fallback traceability missing | Medium | Added feature, acceptance criteria, traceability, and alignment items for offline/cached-read artifacts as Future Scope or implementation alignment only. | `01`, `02`, `03`, `08`, `09`, `10`, `11` | Resolved in BA | Current code may still imply offline behavior. |
| V2-BA-FIX-006: Health/config traceability weak | Low | Added `US-INFRA-READ-001`, `US-CONFIG-SEC-001`, and traceability rows. | `07`, `09`, `10` | Resolved in BA | None in BA; implementation/security review still required. |
| V2-BA-FIX-007: QA test data matrix missing | Low | Added QA test data acceptance criterion and test gap row. | `07`, `09`, `10`, `11` | Resolved in BA | Actual test cases are not created yet. |

## Critical Findings

| QA finding | Severity | Decision or fix applied | Updated BA files | Status | Remaining risk |
|---|---|---|---|---|---|
| QA-US-001: Online-only scope contradiction | Critical | D-001, D-002, D-013 clarify no offline writes, no local queue, no IndexedDB source of truth, and API error behavior. | `00`, `01`, `03`, `05`, `06`, `07`, `08`, `09`, `10`, `11`, `13` | Resolved in BA / implementation alignment remains | Current code still queues failed writes and exposes sync behavior. |
| QA-US-002: Food delete lifecycle | Critical | D-025 supersedes archive-only delete. Food delete is permanent hard delete with confirmation; no `is_active`, no `archived_at`, no archive filters. | `01`, `02`, `03`, `04`, `07`, `08`, `09`, `10`, `11`, `13`, `15`, implementation plan | Resolved in BA / implementation alignment remains | Current code hard deletes but lacks required confirmation/copy and snapshot-after-delete verification. |

## High Findings

| QA finding | Severity | Decision or fix applied | Updated BA files | Status | Remaining risk |
|---|---|---|---|---|---|
| QA-US-003: Field validation incomplete | High | D-009, D-011, D-012 define age bounds, ranges, Arabic messages, and validation placement. | `04`, `05`, `06`, `07`, `09`, `13` | Resolved in BA | Current code ranges/messages need alignment. |
| QA-US-004: Duplicate foods not testable | High | D-005 and D-006 define active-only duplicate key and normalization. | `04`, `05`, `07`, `09`, `13` | Resolved in BA | Implementation missing. |
| QA-US-005: Negative net carbs and optional nutrient consistency | High | D-011, D-012, and D-026 require `fiber_g <= carb_g`, optional nutrient max ranges, added sugar consistency, saturated/trans fat consistency, and exact Arabic errors. | `04`, `05`, `06`, `07`, `09`, `13` | Resolved in BA | Implementation missing. |
| QA-US-006: Gram logging unclear | High | D-007 requires gram logging and D-021 defines exact API/storage/snapshot contract. | `01`, `02`, `03`, `04`, `05`, `07`, `08`, `09`, `10`, `13` | Resolved in BA | UI/API implementation missing. |
| QA-US-007: Network errors too broad | High | D-013 plus D-022 and split stories `US-NETWORK-READ-001`, `US-NETWORK-READ-COPY-001`, `US-NETWORK-WRITE-001`, `US-ERROR-MAPPING-001`. | `05`, `06`, `07`, `08`, `09`, `10`, `13` | Resolved in BA | Error UI implementation missing. |
| QA-US-008: Service worker/PWA scope | High | D-002 limits service worker to static shell assets and recommends removal if confusing. | `01`, `07`, `09`, `11`, `13` | Resolved in BA | Current service worker caches GET responses. |
| QA-US-009: Diary scope | High | D-008 blocks future dates; D-010 allows quantity-only edit. | `01`, `03`, `05`, `07`, `08`, `09`, `13` | Resolved in BA | Backend update is broader; UI edit missing. |
| QA-US-010: Accessibility criteria vague | High | D-011, D-014, D-015, and D-023 define field errors, dialog focus, accessible names, first-invalid focus, collapsed-section expansion, and status/live-region behavior. | `04`, `06`, `07`, `09`, `10`, `13` | Resolved in BA | Detailed UI design still needed during implementation. |
| QA-US-011: Testability gaps | High | `US-QA-001`, traceability matrix, and test gap list updated for CRUD, validation, network, mobile, RTL, a11y. | `07`, `10`, `11` | Partially Resolved | Test files not implemented yet. |

## Final Open Question Remediation

| Former open question | Severity | Decision or fix applied | Updated BA files | Status | Remaining risk |
|---|---|---|---|---|---|
| OQ-001: Multi-person/profile support in v1 or Future Scope | High | D-016 makes multi-profile support Future Scope and keeps v1 on the current single Profile model. | `01`, `03`, `07`, `09`, `10`, `11`, `12`, `13` | Resolved | Older planning docs may still mention people/profiles and must be treated as superseded for v1. |
| OQ-002: Profile deletion/reset support | Medium | D-017 excludes profile reset/delete from v1; correction is through editing the existing profile. | `03`, `07`, `09`, `10`, `11`, `12`, `13` | Resolved | Users cannot clear profile data in one action in v1. |
| OQ-003: Diary delete confirmation | Medium | D-018 requires confirmation showing food name/date, cancel no change, confirm delete after API success. | `03`, `06`, `07`, `08`, `09`, `10`, `11`, `12`, `13` | Resolved | Current UI may need implementation alignment. |
| OQ-004: `serving_grams` API naming vs UI label | Low | D-019 is superseded by D-024/D-025 for Food modeling; current v1 uses per-100g/per-100ml plus default-unit fields. | `04`, `07`, `09`, `10`, `11`, `12`, `13` | Superseded | Current code/test artifacts may still reference `serving_grams`. |
| OQ-005: Long food name display behavior | Medium | D-020 requires two-line ellipsis in lists/cards and full name in detail/edit views. | `01`, `07`, `08`, `09`, `10`, `11`, `12`, `13` | Resolved | Current UI requires visual QA verification. |

## Remaining Implementation Alignment Items

See `docs/ba/11_REQUIREMENTS_GAPS.md` for the full list. The highest-risk items are:
1. Failed writes currently queue local mutations.
2. Current Food hard delete lacks required confirmation/copy and snapshot-after-delete verification.
3. Food archive fields are no longer v1 requirements; any archive implementation/test assumptions are superseded by D-025.
4. Gram Diary logging is missing.
5. D-021 Diary `log_mode` contract is missing.
6. Service worker, offline page/metadata, cached-read fallbacks, and sync behavior remain active or visible in code.
7. Diary delete confirmation may be missing.
8. Duplicate-submit, stale item, retry, and accessibility behaviors need alignment.
9. Long food name two-line truncation needs verification.

## Readiness After Remediation

BA ready for another QA audit: Yes.

Implementation planning can start from a BA standpoint. Planning must treat current code contradictions as implementation alignment work, not accepted behavior.

QA test case generation can start from a BA standpoint using `04_FIELD_DICTIONARY.md`, `05_VALIDATION_RULES.md`, `06_ERROR_MESSAGES.md`, `08_NEGATIVE_SCENARIOS.md`, `09_ACCEPTANCE_CRITERIA.md`, and `10_TRACEABILITY_MATRIX.md`.
