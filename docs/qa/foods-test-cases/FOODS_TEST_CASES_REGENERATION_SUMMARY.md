# Foods Test Cases Regeneration Summary

Generated from the approved Foods BA documentation and the final cleanup recheck gate, then cleaned up based on docs/qa/foods-test-cases/FOODS_TEST_CASES_AUDIT.md and field-completion findings in docs/qa/foods-test-cases/FOODS_FIELD_COVERAGE_MATRIX.md.

## Scope

- Module: Foods
- Source of truth: docs/ba/ and docs/qa/foods-final-decision-audit/01_FOODS_CLEANUP_RECHECK.md
- Product scope: online-only v1
- Excluded from v1 assertions: archive/inactive Food behavior, is_active, archived_at, Active/Archived filters, serving-based nutrition as source of truth, offline write queue, sync/pending states, and cached personal data as source of truth.

## Output

- CSV: docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv
- Total test cases: 153
- Foods user stories covered: 10 of 10
- Missing Foods user stories: None
- Cleanup status: weak/vague rows refined; non-executable scope-review row converted; total_sugars_g legacy mapping coverage added; field-level gaps closed for calories decimal input, optional nutrient decimals, optional text language/max/error specificity, nutrition_basis tamper error copy, and optional nutrient field-error mapping.

## Count By Feature

| Feature | Test cases |
|---|---:|
| Duplicate food handling | 5 |
| Food accessibility and online-only behavior | 6 |
| Food creation | 12 |
| Food deletion | 10 |
| Food details | 7 |
| Food editing | 12 |
| Food field validation | 36 |
| Food listing | 10 |
| Food navigation and page structure | 7 |
| Food search | 10 |
| Food state handling | 9 |
| Optional nutrient validation | 29 |

## Count By Priority

| Priority | Test cases |
|---|---:|
| P0 | 85 |
| P1 | 60 |
| P2 | 8 |

## User Story Coverage

| User Story ID | Name | Test cases | Status |
|---|---|---:|---|
| US-FOOD-CRUD-001 | Create Food on Standalone Page | 50 | Covered |
| US-FOOD-CRUD-002 | Edit Food on Standalone Page | 12 | Covered |
| US-FOOD-CRUD-003 | Permanently Delete Food With Confirmation | 10 | Covered |
| US-FOOD-HAPPY-001 | Browse Current Food Catalog | 12 | Covered |
| US-FOOD-HAPPY-002 | Search Current Food Catalog | 10 | Covered |
| US-FOOD-HAPPY-003 | View Food Details | 7 | Covered |
| US-FOOD-NAV-001 | Use Standalone Food Pages | 7 | Covered |
| US-FOOD-STATE-001 | Show Food Loading, Empty, No-Results, and Read-Failure States | 10 | Covered |
| US-FOOD-VALIDATION-003 | Block Current Catalog Duplicate Food | 5 | Covered |
| US-FOOD-VALIDATION-004 | Validate Optional Nutrient Ranges | 30 | Covered |

## Coverage Notes

- Every approved Foods user story has test coverage.
- Field validation coverage includes required fields, optional fields, numeric min/max boundaries, decimal numeric values, invalid formats, Arabic text, English text, mixed Arabic/English text for text fields, whitespace normalization, duplicate/conflict behavior, D-026 optional nutrient ranges, optional nutrient decimal values, exact Arabic error messages, and the total_sugars_g legacy/current-code mapping rule.
- Search coverage includes exact/partial terms, Arabic text, whitespace trimming, no-results, deleted Food exclusion, mobile usability, and read-failure behavior.
- Delete coverage reflects D-025 permanent hard delete only; archive/inactive behavior is intentionally tested only as absent from v1.
- Nutrition coverage reflects per 100g/per 100ml source of truth; default unit is tested only as logging/display convenience.
- Online-only coverage verifies no offline write queue, no saved-locally messaging, and no cached personal Food data as source of truth.
- Accessibility coverage focuses on forms, field errors, icon actions, state messages, and confirmation dialogs.
- Field-completion cleanup added FOOD-TC-143 through FOOD-TC-153 and refined FOOD-TC-069, FOOD-TC-073, FOOD-TC-074, and FOOD-TC-075. The final pass corrected nine rows containing corrupted Arabic placeholders and added explicit whitespace-only Food name rejection coverage.

## Remaining Notes

- Sorting, pagination, advanced filtering, restore/undo delete, and archived status behavior are not approved v1 Foods requirements.
- Current implementation may still differ from the BA package; those mismatches should be handled as implementation alignment work, not BA gaps.
