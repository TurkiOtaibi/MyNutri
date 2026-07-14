# Foods Field Coverage Final Recheck

Status: Report-only QA recheck
Date: 2026-07-10
Application code changed: No
BA files changed: No
Automated tests implemented: No

## 1. Overall Verdict

Verdict: **Partially Ready - not yet field-complete**

The CSV contains 152 executable test-case rows with 152 unique IDs. The cleanup successfully added calories decimal coverage, optional-nutrient decimal coverage, optional text language/max scenarios, and invalid `nutrition_basis` scenarios.

The final baseline is not fully ready because nine rows contain literal question-mark placeholders (`???` / `????`) instead of executable Arabic test data or exact Arabic expected messages. This directly affects the requested exact-copy and Arabic-language checks. A separate explicit whitespace-only `food_name` rejection case is also absent.

Confidence: High. The findings come from direct CSV parsing and comparison with the current BA field dictionary, validation rules, error-message catalog, acceptance criteria, and D-024/D-025/D-026 decisions.

## 2. Mechanical Integrity

| Check | Result | Evidence |
|---|---:|---|
| CSV rows | 152 | Parsed with PowerShell `Import-Csv` |
| Unique test IDs | 152 | No duplicate IDs found |
| Blank test IDs | 0 | Direct CSV check |
| Blank Steps cells | 0 | Direct CSV check |
| Blank Expected Result cells | 0 | Direct CSV check |
| Generic review/TODO rows | 0 | No `TBD`, `TODO`, `review scope`, `verify it works`, or `check behavior` text found |
| Rows containing literal repeated `?` placeholders | 9 | `FOOD-TC-069`, `073`, `074`, `147`, `148`, `149`, `150`, `151`, `152` |

## 3. Field Coverage Status

The requested `food_name` field maps to the BA/API field `name` and the UI label Food name.

| Field group | Status | Evidence / remaining issue |
|---|---|---|
| `food_name` / `name` | Partial | Positive Arabic/English/mixed display, blank, trim, max, and above-max coverage exists. No explicit whitespace-only value such as three spaces is submitted and rejected after trim. |
| `brand` | Partial | Blank, English, max, above-max, symbols, and RTL intent are covered, but Arabic and mixed fixtures and the exact max error are literal `?` placeholders in `FOOD-TC-073` and `147`. |
| `category` | Partial | Blank, English, max, above-max, symbols, and RTL intent are covered, but Arabic and mixed fixtures and the exact max error are literal `?` placeholders in `FOOD-TC-074` and `148`. |
| `nutrition_basis` | Partial | Positive `per_100g`/`per_100ml`, blank, and tampered `per_serving` rejection exist. The exact Arabic invalid-option result is corrupted in `FOOD-TC-069` and `151`; it should assert `اختر قيمة صحيحة.`. |
| Core nutrition: `calories`, `protein_g`, `carb_g`, `fat_g` | Covered | Required/blank, zero/min, max, above max, negative, invalid numeric, and valid decimal coverage exists. `FOOD-TC-143` explicitly covers decimal calories. |
| Default unit: `default_unit_type`, `unit_amount`, `unit_basis` | Covered | Required/blank, allowed enum values, tampered enum values, numeric boundaries, decimal amount, and Arabic error assertions exist. |
| Optional gram nutrients | Covered with one weak redundant row | `fiber_g`, `sugar_g`, `added_sugar_g`, `saturated_fat_g`, and `trans_fat_g` have blank, zero, max, above-max, negative, decimal, and applicable cross-field coverage. `FOOD-TC-152` has corrupted Arabic copy, but field-specific exact messages also exist in `FOOD-TC-076` to `080` and `094` to `099`. |
| Optional minerals | Covered | `sodium_mg`, `cholesterol_mg`, `potassium_mg`, `calcium_mg`, `iron_mg`, `magnesium_mg`, and `zinc_mg` have blank, zero, max, above-max, negative, decimal, and Arabic error coverage. |
| Optional vitamins | Covered with one weak redundant row | `vitamin_d_mcg`, `vitamin_b12_mcg`, `vitamin_c_mg`, `vitamin_a_mcg`, `folate_mcg`, and `vitamin_k_mcg` have blank, zero, max, above-max, negative, decimal, and Arabic error coverage. The Vitamin D text in `FOOD-TC-152` is corrupted, but `FOOD-TC-088` independently covers its exact generic D-026 errors. |
| `notes` | Partial | Blank, safe rendering, 500/501 boundaries, preservation, and language intent exist. `FOOD-TC-149` uses labels such as “Arabic notes” rather than concrete Arabic values and contains a corrupted exact max error. |
| `data_source` | Partial | Blank, URL-like text, 120/121 boundaries, preservation, and language intent exist. Arabic/mixed fixtures and the exact max error are corrupted in `FOOD-TC-150`. |

Summary: **25 of 31 fields are adequately covered; 6 are partial** (`food_name`, `brand`, `category`, `nutrition_basis`, `notes`, and `data_source`). No field is completely missing positive coverage.

## 4. Required and Numeric Validation

### Required fields

Blank/required coverage exists for:

- Food name (`FOOD-TC-048`)
- Nutrition basis (`FOOD-TC-049`)
- Calories, protein, carbs, and fat (`FOOD-TC-050` to `053`)
- Default unit type, unit amount, and unit basis (`FOOD-TC-054` to `056`)

Remaining gap: add an explicit whitespace-only Food name case. Leading/trailing normalization in `FOOD-TC-058` does not prove that a value containing only spaces is rejected after trimming.

### Numeric fields

- Core numeric min/zero/max/negative/above-max coverage: Present.
- Optional nutrient blank/zero/max/negative/above-max coverage: Present for every D-026 field in `FOOD-TC-076` to `093`.
- Calories decimal coverage: Present in `FOOD-TC-143`.
- Optional nutrient decimal coverage: Present in `FOOD-TC-144` to `146`.
- Unit amount decimal and invalid boundary coverage: Present in `FOOD-TC-071`.

Test-data note: grouped optional-nutrient boundary cases should use compatible core values when executed, such as `carb_g >= fiber_g` and `fat_g >= saturated_fat_g/trans_fat_g`, so the intended range rule is isolated from cross-field failures.

## 5. Cross-Field Validation

| Rule | Status | Test cases |
|---|---|---|
| `fiber_g <= carb_g` | Covered | `FOOD-TC-094`; valid compatible decimals in `144` |
| `added_sugar_g <= sugar_g` when both are provided | Covered | `FOOD-TC-095`; blank `sugar_g` allowed in `096`; valid decimals in `144` |
| `saturated_fat_g <= fat_g` | Covered | `FOOD-TC-097`; valid decimals in `144` |
| `trans_fat_g <= fat_g` | Covered | `FOOD-TC-098`; valid decimals in `144` |
| `saturated_fat_g + trans_fat_g <= fat_g` | Covered | `FOOD-TC-099`; valid decimals in `144` |

All five required rejection rules include the approved Arabic cross-field messages in their primary cases.

## 6. Arabic and Exact-Copy Findings

The following rows are not suitable as final executable Arabic-copy tests because the CSV contains literal question marks:

| Test case | Issue |
|---|---|
| `FOOD-TC-069` | Invalid `nutrition_basis` Arabic message is `???? ???? ?????` instead of `اختر قيمة صحيحة.` |
| `FOOD-TC-073` | Arabic/mixed brand fixtures and exact above-max Arabic error are corrupted. |
| `FOOD-TC-074` | Arabic/mixed category fixtures and exact above-max Arabic error are corrupted. |
| `FOOD-TC-147` | Arabic and mixed brand fixtures are corrupted. |
| `FOOD-TC-148` | Arabic and mixed category fixtures are corrupted. |
| `FOOD-TC-149` | No concrete Arabic/mixed Notes fixture; exact above-max Arabic error is corrupted. |
| `FOOD-TC-150` | Arabic/mixed data-source fixtures and exact above-max Arabic error are corrupted. |
| `FOOD-TC-151` | Exact invalid-option Arabic message is corrupted. |
| `FOOD-TC-152` | Fiber and Vitamin D Arabic API messages are corrupted. Coverage is duplicated by valid field-range rows, but this API-mapping row itself is not executable as an exact-copy check. |

The intended generic above-max message is `القيمة أعلى من الحد المسموح.`. Optional nutrient range messages remain correctly represented in `FOOD-TC-076` to `093`.

## 7. Legacy-Scope Assumptions

Status: Pass.

- Archive/inactive terms occur only in executable absence checks (`FOOD-TC-012`, `125`, `141`). They do not reintroduce archive behavior.
- `is_active` and `archived_at` occur only as fields that must not exist in v1 UI/behavior.
- Offline terms occur only in online-only failure tests proving no local source of truth, local write, or deferred queue.
- `per_serving` occurs only as an invalid/tampered `nutrition_basis` value.
- `FOOD-TC-047` explicitly confirms that nutrition source of truth is per 100g/per 100ml and the default unit is only for logging/display convenience.

## 8. Executability Assessment

No blank-step, blank-result, checklist-only, or duplicate-ID rows remain. Most cases are executable using their Preconditions, Test Data, Steps, and Expected Result together.

However, the nine rows listed in Section 6 fail the “no vague or non-executable rows” gate for exact Arabic verification because a tester cannot derive the required Arabic input or expected copy from `?` placeholders. `FOOD-TC-149` also uses abstract values (“Arabic notes”, “mixed Arabic/English notes”) instead of concrete fixtures.

## 9. Remaining Gaps

1. Replace literal question-mark placeholders with UTF-8 Arabic fixtures and exact Arabic expected messages in the nine affected rows.
2. Add or refine one explicit whitespace-only Food name rejection case, for example `name = "   "`, asserting the approved required-name Arabic message and no persisted Food.
3. Make compatible core values explicit in grouped optional-nutrient max tests to isolate each field's boundary rule.

These are test-documentation gaps only. They do not reopen BA decisions and do not indicate an application-code defect.

## 10. Final Readiness

| Readiness area | Decision |
|---|---|
| Broad Foods manual QA | May start for unaffected cases |
| Formal field-complete Manual QA baseline | **Not ready** until the nine corrupted rows and whitespace-only name gap are fixed |
| Automation planning | **Partially ready**; unaffected cases can be planned, but affected Arabic-copy cases must be corrected before automation |
| Field-complete verdict | **No** |

Recommended next step: correct the nine UTF-8/Arabic rows and add the explicit whitespace-only Food name case, then rerun this compact mechanical recheck. No BA or application changes are required.
