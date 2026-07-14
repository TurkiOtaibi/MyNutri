# Foods Final Decision QA Audit

Audit status: report only.
Application code changed: No.
BA files changed: No.
Existing QA audit files changed: No.
Test cases changed: No.

## 1. Overall Verdict

Verdict: Partially Ready
Readiness score: 8/10

The BA package mostly reflects the latest Foods page decisions D-024, D-025, and D-026. The current Food feature map, field dictionary, validation matrix, product decisions, acceptance criteria, requirements gaps, and implementation plan now clearly define:

- Add Food as a standalone page.
- Permanent Food hard delete, not archive/inactive.
- Per 100g/per 100ml nutrition source of truth.
- Default unit metadata.
- No `is_active`, no `archived_at`, no Active/Archived filters.
- Optional nutrients collapsed by default.
- D-026 optional nutrient max ranges and cross-field validation.
- Diary snapshot safety after Food hard delete.
- Online-only v1 behavior.

The package is not fully ready because a few BA artifacts still contain stale legacy wording that can mislead implementation or test generation, and some Food capabilities are covered only by legacy stories instead of current D-024/D-026 user stories.

Implementation planning can continue, but QA test cases must be regenerated or updated before execution.

## 2. Scope and Evidence Inventory

Food features reviewed: 11
Current Food user stories reviewed: 7
Legacy Food user stories reviewed for conflict risk: 8
Primary BA files reviewed:

- `docs/ba/01_FEATURE_MAP.md`
- `docs/ba/04_FIELD_DICTIONARY.md`
- `docs/ba/05_VALIDATION_RULES.md`
- `docs/ba/06_ERROR_MESSAGES.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `docs/ba/10_TRACEABILITY_MATRIX.md`
- `docs/ba/11_REQUIREMENTS_GAPS.md`
- `docs/ba/12_OPEN_QUESTIONS.md`
- `docs/ba/13_PRODUCT_DECISIONS.md`
- `docs/implementation/01_V1_ALIGNMENT_IMPLEMENTATION_PLAN.md`

Current code evidence reviewed:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/food.py`
- `backend/app/services/diary.py`
- `backend/app/api/routes/foods.py`
- `frontend/app/foods/page.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/lib/db.ts`
- `frontend/public/service-worker.js`
- `backend/tests/test_diary_snapshot.py`

## 3. Feature Coverage Audit

| Feature ID | Feature | BA coverage status | Notes |
|---|---|---|---|
| F-017 | Foods list | Fully covered | Current story and acceptance criteria cover desktop columns, mobile cards, no archive filters, long names, and deleted Food absence. |
| F-018 | Food search | Partially covered | Feature map and acceptance criteria mention search/no-results, but current `US-FOOD-*` section has no non-legacy search story. |
| F-019 | Standalone Food create | Fully covered | `US-FOOD-NAV-001` and `US-FOOD-CRUD-001` cover `/foods/new`, grouped sections, no delete action, pending submit, and network failure behavior. |
| F-020 | Food edit | Partially covered | Feature map and acceptance criteria cover `/foods/:id/edit`, but there is no current non-legacy `US-FOOD-CRUD-002` story for edit. |
| F-021 | Food details | Fully covered | `US-FOOD-HAPPY-003` covers dedicated detail page, full Food name, optional nutrients, read failure. |
| F-022 | Food permanent delete | Fully covered | `US-FOOD-CRUD-003` covers confirmation, cancel, permanent delete, failed delete, duplicate submit, snapshot after delete. |
| F-023 | No Food archive state | Mostly covered | Current BA decisions and criteria are clear. Some stale legacy wording remains elsewhere and must be cleaned before test regeneration. |
| F-024 | Duplicate food prevention | Fully covered | `US-FOOD-VALIDATION-003` covers D-025 key and deleted Foods not blocking duplicates. |
| F-025 | Net carbs and optional nutrient validation | Mostly covered | D-026 ranges and cross-field rules are defined, but `sugar_g` field mapping is inconsistent in the field dictionary. |
| F-026 | Default unit metadata | Fully covered | Field dictionary and create story define `default_unit_type`, `unit_amount`, `unit_basis`. |
| F-027 | Food state handling | Partially covered | Acceptance criteria cover loading/empty/no-results/read-failure, but current stories rely on `LEGACY-US-FOOD-STATE-001`. |

Coverage result: 8 fully covered, 3 partially covered, 0 missing.

## 4. Critical BA Issues

Critical BA issues count: 0

No current BA issue blocks implementation planning outright. The remaining issues are High or Medium cleanup items. Current code has critical implementation gaps, but those are documented as implementation alignment items and should not lower BA readiness by themselves.

## 5. High BA Issues

### Finding FFD-HIGH-001

Severity: High
Category: Story Coverage
Feature: Food search and Food state handling
Affected features: F-018, F-027
Affected stories: `LEGACY-US-FOOD-HAPPY-002`, `LEGACY-US-FOOD-STATE-001`
Evidence:
- `docs/ba/01_FEATURE_MAP.md` lists F-018 and F-027 as current v1 features.
- `docs/ba/07_USER_STORIES.md` has current Food stories only for navigation, browse, create, duplicate, optional nutrients, delete, and details.
- Search and state stories exist only as `LEGACY-US-FOOD-HAPPY-002` and `LEGACY-US-FOOD-STATE-001`.

Issue:
Current Food search, loading, empty, no-results, read-failure, and retry behavior are not represented by current non-legacy stories.

Why it matters:
Developers and QA may treat the legacy story section as either authoritative or obsolete. This weakens traceability for F-018 and F-027.

Recommended fix:
Add current stories:
- `US-FOOD-HAPPY-002 - Search Current Food Catalog`
- `US-FOOD-STATE-001 - Show Food Loading, Empty, No-Results, and Read-Failure States`

### Finding FFD-HIGH-002

Severity: High
Category: Story Coverage
Feature: Food edit
Affected feature: F-020
Affected story: `LEGACY-US-FOOD-CRUD-002`
Evidence:
- `docs/ba/01_FEATURE_MAP.md` defines Food edit on `/foods/:id/edit`.
- `docs/ba/09_ACCEPTANCE_CRITERIA.md` includes edit acceptance criteria.
- `docs/ba/07_USER_STORIES.md` does not include a current `US-FOOD-CRUD-002`; edit exists only in the legacy section.

Issue:
Current edit requirements are scattered across navigation/create/acceptance criteria and legacy story content.

Why it matters:
Food edit is a core CRUD operation. It needs its own current story covering prefill, editable fields, validation, duplicate handling, stale Food, API/network failure, snapshot integrity, and delete availability.

Recommended fix:
Add `US-FOOD-CRUD-002 - Edit Food on Standalone Page`.

### Finding FFD-HIGH-003

Severity: High
Category: Field Dictionary / D-026 Consistency
Feature: Optional nutrient validation
Affected fields: `sugar_g`, `total_sugars_g`, `added_sugar_g`
Evidence:
- `docs/ba/05_VALIDATION_RULES.md` defines `sugar_g` as the D-026 field for sugar.
- `docs/ba/04_FIELD_DICTIONARY.md` marks `total_sugars_g` as legacy/current-code and says the D-025 field name is `sugar_g`, but the current table does not include a dedicated current row for `sugar_g`.
- D-026 cross-field rule requires `added_sugar_g <= sugar_g`.

Issue:
The BA defines validation against `sugar_g`, but the current field dictionary does not fully map `sugar_g` as a first-class v1 DB/API field.

Why it matters:
Implementation may keep `total_sugars_g`, introduce `sugar_g`, or support both without a clear contract. QA cannot reliably assert the API payload field for sugar.

Recommended fix:
Add a current `sugar_g` field row to the field dictionary and explicitly state whether `total_sugars_g` is retired, migrated, or response-compatible only.

### Finding FFD-HIGH-004

Severity: High
Category: Error Message Consistency
Feature: Duplicate Food / Food delete
Affected file: `docs/ba/06_ERROR_MESSAGES.md`
Evidence:
- `docs/ba/06_ERROR_MESSAGES.md` still includes `Duplicate active food` and associates the duplicate error with food name, serving label, and serving grams.
- The same file still includes `Food archive success`.
- D-025 removes archive/inactive behavior and D-025 duplicate key uses `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`.

Issue:
The error message matrix still contains stale archive and serving-based duplicate wording.

Why it matters:
The error message matrix is likely to drive UI copy and QA assertions. Stale labels can reintroduce serving-based or archive-based behavior.

Recommended fix:
Rename and remap:
- `Duplicate active food` -> `Duplicate current catalog Food`
- Associated fields -> `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`
- Remove or supersede `Food archive success`; replace with permanent delete success if a success message is required.

## 6. Medium BA Issues

### Finding FFD-MED-001

Severity: Medium
Category: Traceability
Feature: Diary gram logging / Food source-of-truth
Evidence:
- `docs/ba/10_TRACEABILITY_MATRIX.md` still says Diary gram create requires `serving_grams`.
- `docs/ba/09_ACCEPTANCE_CRITERIA.md` legacy criteria still include selected Food with/without `serving_grams`.
- D-025 supersedes `serving_grams` as Food source-of-truth.

Issue:
Some Diary traceability and criteria still mention `serving_grams` as if it controls gram mode.

Why it matters:
This can produce wrong Diary test cases after Food model changes.

Recommended fix:
Update Diary gram rows to use `nutrition_basis`, `unit_amount`, and `unit_basis` or explicitly mark those rows as superseded historical evidence.

### Finding FFD-MED-002

Severity: Medium
Category: Test Traceability
Feature: QA test update impact
Evidence:
- `docs/ba/10_TRACEABILITY_MATRIX.md` test strategy rows still mention `archive` in API, E2E, and accessibility coverage.
- `docs/ba/07_USER_STORIES.md` and `docs/ba/09_ACCEPTANCE_CRITERIA.md` still contain generic `delete/archive` wording in non-Food cross-cutting sections.

Issue:
Test strategy language still carries archive terminology.

Why it matters:
The user explicitly asked whether QA test cases must be regenerated or updated. These stale references show they must be updated before execution.

Recommended fix:
Replace generic `archive` references with `Food permanent delete` where Food is intended, and `Diary delete` where Diary is intended.

## 7. Remaining BA Gaps

Remaining BA gaps count: 5

| Gap | Severity | Evidence | Recommended fix |
|---|---|---|---|
| Current Food search story missing | High | F-018 exists; only legacy search story exists. | Add current `US-FOOD-HAPPY-002`. |
| Current Food state-handling story missing | High | F-027 exists; only legacy state story exists. | Add current `US-FOOD-STATE-001`. |
| Current Food edit story missing | High | F-020 exists; edit only appears in legacy story and acceptance criteria. | Add current `US-FOOD-CRUD-002`. |
| `sugar_g` field mapping incomplete | High | D-026 uses `sugar_g`; field dictionary only has legacy `total_sugars_g` row. | Add current `sugar_g` row and migration/API mapping decision. |
| Error message matrix has stale duplicate/archive rows | High | `Duplicate active food`, `Food archive success`. | Update message matrix to current-catalog duplicate and hard-delete copy. |

## 8. Implementation Alignment Items

Implementation alignment items count: 11

These are code gaps, not BA contradictions.

| Item | Severity | Current code evidence | BA requirement |
|---|---|---|---|
| No standalone Food routes | Critical | Only `frontend/app/foods/page.tsx` exists; no `/foods/new`, `/foods/[id]`, `/foods/[id]/edit` routes. | D-024 standalone pages. |
| Inline Add/Edit Food form still on `/foods` | Critical | `frontend/components/FoodsPage.tsx` renders list and form together. | `/foods` must not contain large inline Add Food form. |
| Food model is serving-based | Critical | `backend/app/models.py`, `schemas.py`, `types.ts` use `serving_label`, `serving_grams`; no `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`. | D-025 per 100g/per 100ml source-of-truth plus default unit. |
| Missing optional nutrient fields | High | Current model lacks potassium, calcium, iron, magnesium, zinc, vitamin D, B12, C, A, folate, K. | D-025/D-026 optional nutrient inventory. |
| D-026 validation not implemented | High | `FoodBase` only uses `ge=0`; no max or cross-field validators. | D-026 ranges and cross-field rules. |
| Duplicate Food blocking missing | High | `create_food` and `update_food` do not normalize/check duplicates. | D-025 duplicate key. |
| Food delete lacks confirmation in UI | Critical | `FoodsPage.tsx` delete button calls `deleteMutation.mutate(food.id)` directly. | D-025 confirmation dialog. |
| Failed Food writes queue offline mutations | Critical | `FoodsPage.tsx` onError writes IndexedDB and calls `queueMutation`. | Online-only v1; no local save/queue. |
| Foods read falls back to cached IndexedDB | High | `FoodsPage.tsx` catches `listFoods` failure and returns `getCachedFoods`. | Fresh read or Arabic connection error; cached personal data not source of truth. |
| Service worker caches all successful GETs | High | `frontend/public/service-worker.js` caches any GET request. | Shell-only/static behavior; personal API data not source-of-truth. |
| Diary snapshot lacks D-025/D-021 fields | High | `make_snapshot` stores serving fields and totals are recalculated from `quantity`; no `nutrition_basis`, `log_mode`, `logged_quantity`, `calculated_totals`. | Snapshot must remain accurate after Food hard delete and preserve Food identity, basis, nutrition values, logged quantity, log mode, calculated totals. |

## 9. Old Archive/Inactive Leftovers

Archive/inactive leftover count: 6 actionable BA leftovers

Superseded archive references are acceptable when explicitly marked as historical or Future Scope. The following still create cleanup risk:

| Location | Leftover | Risk |
|---|---|---|
| `docs/ba/06_ERROR_MESSAGES.md` | `Food archive success` message remains. | Could become a QA assertion or UI copy despite D-025. |
| `docs/ba/10_TRACEABILITY_MATRIX.md` | API/integration test row mentions `archive`. | Test planning may include non-v1 archive tests. |
| `docs/ba/10_TRACEABILITY_MATRIX.md` | E2E row mentions `archive`. | Test generation may include archive flows. |
| `docs/ba/10_TRACEABILITY_MATRIX.md` | Accessibility row mentions `archive/delete dialog focus`. | Should be Food permanent-delete and Diary delete dialog focus. |
| `docs/ba/07_USER_STORIES.md` | Cross-cutting duplicate-submit/a11y stories mention `delete/archive` and `food archive`. | Generic wording can reintroduce archive terminology. |
| `docs/ba/09_ACCEPTANCE_CRITERIA.md` | Cross-cutting duplicate-submit/a11y criteria mention `delete/archive` and `food archive`. | Acceptance criteria should use permanent delete for Food. |

## 10. D-026 Validation Coverage Result

Result: Mostly covered, with one field mapping gap.

Confirmed covered:

- Optional nutrients are optional.
- Blank optional nutrients do not block saving.
- Provided optional nutrients must be numeric and `>= 0`.
- Max ranges are defined for fiber, sugar, added sugar, saturated fat, trans fat, cholesterol, sodium, potassium, calcium, iron, magnesium, zinc, vitamin D, B12, C, A, folate, and K.
- Cross-field rules are defined:
  - `fiber_g <= carb_g`
  - `added_sugar_g <= sugar_g`
  - `saturated_fat_g <= fat_g`
  - `trans_fat_g <= fat_g`
  - `saturated_fat_g + trans_fat_g <= fat_g`
- Arabic field-level errors are defined for D-026 failures.
- Collapsed optional nutrient section opens and focuses the first invalid field.

Gap:

- `sugar_g` is used in validation rules, but the current field dictionary does not fully define `sugar_g` as a current DB/API field. It marks `total_sugars_g` as legacy/current-code and says D-025 field name is `sugar_g`.

Recommended fix:

- Add `sugar_g` as a first-class current Food field in `docs/ba/04_FIELD_DICTIONARY.md`.
- Clarify whether `total_sugars_g` is removed, migrated, or supported only for backward compatibility.

## 11. Arabic Error Message Audit

Status: Partially ready.

Ready:

- D-026 optional nutrient messages are exact Arabic text.
- Network/API write and read failures are defined.
- Stale Food message exists.
- Food delete confirmation copy exists in `docs/ba/13_PRODUCT_DECISIONS.md`.

Needs cleanup:

- `docs/ba/06_ERROR_MESSAGES.md` still contains stale duplicate active/serving fields.
- `docs/ba/06_ERROR_MESSAGES.md` still contains `Food archive success`.
- Some Arabic text appears mojibake in several older rows. The BA has exact Arabic in newer D-026 and D-025 decision sections, but implementation should centralize UTF-8 Arabic strings before UI work.

## 12. Test Case Update Impact

QA test cases must be regenerated or updated before execution.

Required changes:

- Remove archive/inactive test expectations.
- Remove `is_active` and `archived_at` expectations.
- Remove Active/Archived filter tests.
- Replace archive tests with permanent hard-delete confirmation, cancel, success, failed delete, duplicate-submit, and snapshot-after-delete tests.
- Add `/foods/new`, `/foods/:id`, and `/foods/:id/edit` route tests.
- Add per 100g/per 100ml nutrition basis tests.
- Add default unit tests for `default_unit_type`, `unit_amount`, `unit_basis`.
- Add D-026 optional nutrient boundary tests.
- Add D-026 cross-field validation tests.
- Update Diary gram logging tests away from `serving_grams` source-of-truth and toward D-025 nutrition basis/default-unit logic.
- Keep online-only read/write tests; no offline write queue expectations.

## 13. Final Recommendation

Implementation planning can continue.

Before implementation starts, perform a small BA cleanup pass:

1. Add current user stories for Food search, Food edit, and Food state handling.
2. Add a current `sugar_g` field dictionary row and clarify `total_sugars_g` migration/backward compatibility.
3. Remove or supersede stale `Food archive success`, `Duplicate active food`, and serving-based duplicate message mappings.
4. Replace cross-cutting `archive/delete` wording with `Food permanent delete` and `Diary delete`.
5. Regenerate or update QA test cases from the cleaned BA package.

Readiness summary:

- BA product decisions: Mostly ready.
- Food CRUD requirements: Mostly ready.
- D-026 validation: Mostly ready.
- Archive/inactive removal: Mostly ready, with stale wording cleanup needed.
- Implementation alignment: Not implemented yet, but correctly documented as alignment work.
- QA test baseline: Must be updated before execution.
