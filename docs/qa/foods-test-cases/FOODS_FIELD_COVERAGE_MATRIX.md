# Foods Field Coverage Matrix

Status: Report-only QA audit
Source reviewed: `docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv`
CSV test cases reviewed: 142
Application code changed: No
BA files changed: No

## 1. Overall Verdict

Verdict: Partially field-complete

The Foods CSV has strong coverage for required fields, core numeric ranges, dropdown/select validation, duplicate handling, cross-field nutrition rules, and Arabic field-level errors for the main failure paths.

It is not fully field-complete because several fields lack explicit per-field coverage for every requested dimension:

- Optional text fields do not consistently cover English input and mixed Arabic/English input.
- Optional text field Arabic error-message checks are inconsistent or generic.
- `calories` does not have an explicit decimal-value test.
- Optional nutrient fields do not have explicit decimal-value tests.
- `nutrition_basis` has an invalid/tampered option test, but the expected exact Arabic invalid-option message is not stated.

## 2. Legend

- Yes: Explicitly covered by one or more CSV test cases.
- Partial: Covered generally, but one or more requested details are weak, generic, or not field-specific.
- No: No clear field-specific coverage found.
- N/A: Not applicable to this field type.

## 3. Field Coverage Matrix

| Field | Positive valid test | Required/blank test if required | Blank allowed test if optional | Negative number test | Zero value test | Min boundary test | Max boundary test | Above max test | Decimal value test | Invalid/tampered option test | Arabic input test | English input test | Mixed Arabic/English input test | Cross-field validation test | Arabic error message check | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `food_name` | Yes: FOOD-TC-036, 037 | Yes: FOOD-TC-048 | N/A | N/A | N/A | N/A | Yes: FOOD-TC-059 | Yes: FOOD-TC-059 | N/A | N/A | Yes: FOOD-TC-057 | Yes: FOOD-TC-037, 058 | Yes: FOOD-TC-009, 016, 130 | Yes: duplicate key in FOOD-TC-101, 102 | Yes: FOOD-TC-048, 059, 101 | Fully covered |
| `brand` | Yes: FOOD-TC-073 | N/A | Yes: FOOD-TC-073 | N/A | N/A | N/A | Yes: FOOD-TC-073 | Yes: FOOD-TC-073 | N/A | N/A | Yes: FOOD-TC-073 | Partial: valid text implied, not explicit | No | N/A | Yes: max error in FOOD-TC-073 | Partially covered |
| `category` | Yes: FOOD-TC-074 | N/A | Yes: FOOD-TC-074 | N/A | N/A | N/A | Partial: over-limit covered, exact max not explicit | Yes: FOOD-TC-074 | N/A | N/A | Yes: FOOD-TC-074 | Partial: valid text implied, not explicit | No | N/A | Partial: rejected, exact Arabic copy not stated | Partially covered |
| `nutrition_basis` | Yes: FOOD-TC-036, 037, 069 | Yes: FOOD-TC-049 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-069 | N/A | N/A | N/A | Yes: duplicate key in FOOD-TC-101 | Partial: required error exact; invalid-option Arabic copy not stated in FOOD-TC-069 | Partially covered |
| `calories` | Yes: FOOD-TC-036, 037 | Yes: FOOD-TC-050 | N/A | Yes: FOOD-TC-062 | Yes: FOOD-TC-061 | Yes: FOOD-TC-061 | Yes: FOOD-TC-061 | Yes: FOOD-TC-062 | No explicit decimal calories test | N/A | N/A | N/A | N/A | Yes: Diary snapshot/edit impact in FOOD-TC-115 | Yes: FOOD-TC-050, 062 | Partially covered |
| `protein_g` | Yes: FOOD-TC-036, 037 | Yes: FOOD-TC-051 | N/A | Yes: FOOD-TC-064 | Yes: FOOD-TC-063 | Yes: FOOD-TC-063 | Yes: FOOD-TC-063 | Yes: FOOD-TC-064 | Yes: FOOD-TC-036, 037 | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-051, 064 | Fully covered |
| `carb_g` | Yes: FOOD-TC-036, 037 | Yes: FOOD-TC-052 | N/A | Yes: FOOD-TC-066 | Yes: FOOD-TC-065 | Yes: FOOD-TC-065 | Yes: FOOD-TC-065 | Yes: FOOD-TC-066 | Yes: FOOD-TC-037 | N/A | N/A | N/A | N/A | Yes: `fiber_g <= carb_g` in FOOD-TC-094 | Yes: FOOD-TC-052, 066, 094 | Fully covered |
| `fat_g` | Yes: FOOD-TC-036, 037 | Yes: FOOD-TC-053 | N/A | Yes: FOOD-TC-068 | Yes: FOOD-TC-067 | Yes: FOOD-TC-067 | Yes: FOOD-TC-067 | Yes: FOOD-TC-068 | Yes: FOOD-TC-036, 037 | N/A | N/A | N/A | N/A | Yes: FOOD-TC-097, 098, 099 | Yes: FOOD-TC-053, 068, 097, 098, 099 | Fully covered |
| `default_unit_type` | Yes: FOOD-TC-070 | Yes: FOOD-TC-054 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-070 | N/A | N/A | N/A | Yes: duplicate key in FOOD-TC-101 | Yes: FOOD-TC-054, 070 | Fully covered |
| `unit_amount` | Yes: FOOD-TC-071 | Yes: FOOD-TC-055 | N/A | Yes: FOOD-TC-071 | Yes: FOOD-TC-071 | Yes: FOOD-TC-071 | Yes: FOOD-TC-071 | Yes: FOOD-TC-071 | Yes: FOOD-TC-071 | N/A | N/A | N/A | N/A | Yes: duplicate key in FOOD-TC-101 | Yes: FOOD-TC-055, 071 | Fully covered |
| `unit_basis` | Yes: FOOD-TC-072 | Yes: FOOD-TC-056 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-072 | N/A | N/A | N/A | Yes: duplicate key in FOOD-TC-101 | Yes: FOOD-TC-056, 072 | Fully covered |
| `fiber_g` | Yes: FOOD-TC-076 | N/A | Yes: FOOD-TC-076 | Yes: FOOD-TC-076 | Yes: FOOD-TC-076 | Yes: FOOD-TC-076 | Yes: FOOD-TC-076 | Yes: FOOD-TC-076 | No explicit decimal test | N/A | N/A | N/A | N/A | Yes: FOOD-TC-094, 117 | Yes: FOOD-TC-076, 094 | Partially covered |
| `sugar_g` | Yes: FOOD-TC-077, 142 | N/A | Yes: FOOD-TC-077 | Yes: FOOD-TC-077 | Yes: FOOD-TC-077 | Yes: FOOD-TC-077 | Yes: FOOD-TC-077 | Yes: FOOD-TC-077 | No explicit decimal test | N/A | N/A | N/A | N/A | Yes: FOOD-TC-095, 096 | Yes: FOOD-TC-077, 095 | Partially covered |
| `added_sugar_g` | Yes: FOOD-TC-078, 096, 142 | N/A | Yes: FOOD-TC-078 | Yes: FOOD-TC-078 | Yes: FOOD-TC-078 | Yes: FOOD-TC-078 | Yes: FOOD-TC-078 | Yes: FOOD-TC-078 | No explicit decimal test | N/A | N/A | N/A | N/A | Yes: FOOD-TC-095, 096 | Yes: FOOD-TC-078, 095 | Partially covered |
| `saturated_fat_g` | Yes: FOOD-TC-079 | N/A | Yes: FOOD-TC-079 | Yes: FOOD-TC-079 | Yes: FOOD-TC-079 | Yes: FOOD-TC-079 | Yes: FOOD-TC-079 | Yes: FOOD-TC-079 | No explicit decimal test | N/A | N/A | N/A | N/A | Yes: FOOD-TC-097, 099 | Yes: FOOD-TC-079, 097, 099 | Partially covered |
| `trans_fat_g` | Yes: FOOD-TC-080 | N/A | Yes: FOOD-TC-080 | Yes: FOOD-TC-080 | Yes: FOOD-TC-080 | Yes: FOOD-TC-080 | Yes: FOOD-TC-080 | Yes: FOOD-TC-080 | No explicit decimal test | N/A | N/A | N/A | N/A | Yes: FOOD-TC-098, 099 | Yes: FOOD-TC-080, 098, 099 | Partially covered |
| `sodium_mg` | Yes: FOOD-TC-082 | N/A | Yes: FOOD-TC-082 | Yes: FOOD-TC-082 | Yes: FOOD-TC-082 | Yes: FOOD-TC-082 | Yes: FOOD-TC-082 | Yes: FOOD-TC-082, 100 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-082, 100 | Partially covered |
| `cholesterol_mg` | Yes: FOOD-TC-081 | N/A | Yes: FOOD-TC-081 | Yes: FOOD-TC-081 | Yes: FOOD-TC-081 | Yes: FOOD-TC-081 | Yes: FOOD-TC-081 | Yes: FOOD-TC-081 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-081 | Partially covered |
| `potassium_mg` | Yes: FOOD-TC-083 | N/A | Yes: FOOD-TC-083 | Yes: FOOD-TC-083 | Yes: FOOD-TC-083 | Yes: FOOD-TC-083 | Yes: FOOD-TC-083 | Yes: FOOD-TC-083 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-083 | Partially covered |
| `calcium_mg` | Yes: FOOD-TC-084 | N/A | Yes: FOOD-TC-084 | Yes: FOOD-TC-084 | Yes: FOOD-TC-084 | Yes: FOOD-TC-084 | Yes: FOOD-TC-084 | Yes: FOOD-TC-084 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-084 | Partially covered |
| `iron_mg` | Yes: FOOD-TC-085 | N/A | Yes: FOOD-TC-085 | Yes: FOOD-TC-085 | Yes: FOOD-TC-085 | Yes: FOOD-TC-085 | Yes: FOOD-TC-085 | Yes: FOOD-TC-085 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-085 | Partially covered |
| `magnesium_mg` | Yes: FOOD-TC-086 | N/A | Yes: FOOD-TC-086 | Yes: FOOD-TC-086 | Yes: FOOD-TC-086 | Yes: FOOD-TC-086 | Yes: FOOD-TC-086 | Yes: FOOD-TC-086 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-086 | Partially covered |
| `zinc_mg` | Yes: FOOD-TC-087 | N/A | Yes: FOOD-TC-087 | Yes: FOOD-TC-087 | Yes: FOOD-TC-087 | Yes: FOOD-TC-087 | Yes: FOOD-TC-087 | Yes: FOOD-TC-087 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-087 | Partially covered |
| `vitamin_d_mcg` | Yes: FOOD-TC-088 | N/A | Yes: FOOD-TC-088 | Yes: FOOD-TC-088 | Yes: FOOD-TC-088 | Yes: FOOD-TC-088 | Yes: FOOD-TC-088 | Yes: FOOD-TC-088 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-088 | Partially covered |
| `vitamin_b12_mcg` | Yes: FOOD-TC-089 | N/A | Yes: FOOD-TC-089 | Yes: FOOD-TC-089 | Yes: FOOD-TC-089 | Yes: FOOD-TC-089 | Yes: FOOD-TC-089 | Yes: FOOD-TC-089 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-089 | Partially covered |
| `vitamin_c_mg` | Yes: FOOD-TC-090 | N/A | Yes: FOOD-TC-090 | Yes: FOOD-TC-090 | Yes: FOOD-TC-090 | Yes: FOOD-TC-090 | Yes: FOOD-TC-090 | Yes: FOOD-TC-090 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-090 | Partially covered |
| `vitamin_a_mcg` | Yes: FOOD-TC-091 | N/A | Yes: FOOD-TC-091 | Yes: FOOD-TC-091 | Yes: FOOD-TC-091 | Yes: FOOD-TC-091 | Yes: FOOD-TC-091 | Yes: FOOD-TC-091 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-091 | Partially covered |
| `folate_mcg` | Yes: FOOD-TC-092 | N/A | Yes: FOOD-TC-092 | Yes: FOOD-TC-092 | Yes: FOOD-TC-092 | Yes: FOOD-TC-092 | Yes: FOOD-TC-092 | Yes: FOOD-TC-092 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-092 | Partially covered |
| `vitamin_k_mcg` | Yes: FOOD-TC-093 | N/A | Yes: FOOD-TC-093 | Yes: FOOD-TC-093 | Yes: FOOD-TC-093 | Yes: FOOD-TC-093 | Yes: FOOD-TC-093 | Yes: FOOD-TC-093 | No explicit decimal test | N/A | N/A | N/A | N/A | N/A | Yes: FOOD-TC-093 | Partially covered |
| `notes` | Yes: FOOD-TC-075 | N/A | Yes: FOOD-TC-075 | N/A | N/A | N/A | Partial: over-limit covered, exact max not explicit | Yes: FOOD-TC-075 | N/A | N/A | Partial: valid text implied, not explicit | Partial: valid text implied, not explicit | No | N/A | Partial: rejected, exact Arabic copy not stated | Partially covered |
| `data_source` | Yes: FOOD-TC-075 | N/A | Yes: FOOD-TC-075 | N/A | N/A | N/A | Partial: over-limit covered, exact max not explicit | Yes: FOOD-TC-075 | N/A | N/A | Partial: valid text implied, not explicit | Partial: valid text implied, not explicit | No | N/A | Partial: rejected, exact Arabic copy not stated | Partially covered |

## 4. Fields Fully Covered

Fields that meet all applicable requested coverage dimensions in the CSV:

- `food_name`
- `protein_g`
- `carb_g`
- `fat_g`
- `default_unit_type`
- `unit_amount`
- `unit_basis`

## 5. Fields Partially Covered

Fields with useful coverage but at least one missing or weak requested dimension:

- `brand`
- `category`
- `nutrition_basis`
- `calories`
- `fiber_g`
- `sugar_g`
- `added_sugar_g`
- `saturated_fat_g`
- `trans_fat_g`
- `sodium_mg`
- `cholesterol_mg`
- `potassium_mg`
- `calcium_mg`
- `iron_mg`
- `magnesium_mg`
- `zinc_mg`
- `vitamin_d_mcg`
- `vitamin_b12_mcg`
- `vitamin_c_mg`
- `vitamin_a_mcg`
- `folate_mcg`
- `vitamin_k_mcg`
- `notes`
- `data_source`

## 6. Fields Missing Positive Tests

No field is completely missing positive coverage.

Weak positive coverage:

- `brand`: English and mixed Arabic/English values are not explicit.
- `category`: English and mixed Arabic/English values are not explicit.
- `notes`: Arabic, English, and mixed Arabic/English values are not explicit.
- `data_source`: Arabic, English, and mixed Arabic/English values are not explicit.

## 7. Fields Missing Negative Tests

Missing or weak negative coverage:

- `nutrition_basis`: invalid/tampered value exists in FOOD-TC-069, but the expected exact Arabic invalid-option message is not stated.
- `category`: over-limit rejection exists, but exact boundary and Arabic error copy are weak.
- `notes`: over-limit rejection exists, but exact boundary and Arabic error copy are weak.
- `data_source`: over-limit rejection exists, but exact boundary and Arabic error copy are weak.

All required fields have blank/required negative tests.

All numeric fields have negative-number tests, except non-numeric text/select fields where this is not applicable.

## 8. Fields Missing Boundary Tests

Missing or weak boundary coverage:

- `category`: exact max boundary is not explicit.
- `notes`: exact max boundary is not explicit.
- `data_source`: exact max boundary is not explicit.

Decimal boundary/value coverage gaps:

- `calories`: no explicit decimal-value test.
- Optional nutrients: no explicit decimal-value tests for:
  - `fiber_g`
  - `sugar_g`
  - `added_sugar_g`
  - `saturated_fat_g`
  - `trans_fat_g`
  - `sodium_mg`
  - `cholesterol_mg`
  - `potassium_mg`
  - `calcium_mg`
  - `iron_mg`
  - `magnesium_mg`
  - `zinc_mg`
  - `vitamin_d_mcg`
  - `vitamin_b12_mcg`
  - `vitamin_c_mg`
  - `vitamin_a_mcg`
  - `folate_mcg`
  - `vitamin_k_mcg`

## 9. Recommended Missing Test Cases

Add these to make field coverage complete:

1. `FOOD-TC-NEW-001` - Calories Decimal Acceptance
   Test `calories = 123.45` with otherwise valid data. Expected: Food saves and value is displayed/stored consistently.

2. `FOOD-TC-NEW-002` - Optional Nutrients Decimal Acceptance
   Test representative decimal values for every optional nutrient field, such as `fiber_g = 2.5`, `sodium_mg = 123.45`, and `vitamin_d_mcg = 12.5`. Expected: values within min/max save successfully.

3. `FOOD-TC-NEW-003` - Brand English and Mixed Text
   Test English brand and mixed Arabic/English brand. Expected: both save, display in RTL correctly, and do not affect duplicate-key behavior.

4. `FOOD-TC-NEW-004` - Category English, Mixed Text, and Exact Max Boundary
   Test English category, mixed Arabic/English category, exact max length, and above max. Expected: valid values save; above max shows exact Arabic field-level message.

5. `FOOD-TC-NEW-005` - Notes Arabic, English, Mixed Text, and Exact Max Boundary
   Test Arabic notes, English notes, mixed notes, exact max length, and above max. Expected: valid values save safely; above max shows exact Arabic field-level message.

6. `FOOD-TC-NEW-006` - Data Source Arabic, English, Mixed Text, and Exact Max Boundary
   Test Arabic data source, English data source, mixed data source, exact max length, and above max. Expected: valid values save safely; above max shows exact Arabic field-level message.

7. `FOOD-TC-NEW-007` - Nutrition Basis Invalid Option Arabic Error
   Submit tampered `nutrition_basis = per_serving`. Expected: save is blocked with exact Arabic select-option error: `اختر قيمة صحيحة.`

8. `FOOD-TC-NEW-008` - Optional Nutrient Field-Specific API Error Mapping
   Submit one optional nutrient below min and one above max through API/request interception. Expected: response maps the explicit field name and UI shows the Arabic message under the correct field.

## 10. Is the Foods CSV Field-Complete?

No.

The CSV is strong enough for broad Foods QA execution, but it is not field-complete against the requested field-level checklist. The main missing coverage is decimal-value testing for optional numeric nutrients, explicit language-variant tests for optional text fields, and exact Arabic error-copy checks for some optional text and tampered select scenarios.
