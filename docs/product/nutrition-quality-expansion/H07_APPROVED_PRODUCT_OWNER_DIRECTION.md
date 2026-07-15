# H07 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H07` |
| Issue ID | `H07` |
| Severity | High |
| Title | Controlled source reliability, ingredients, and NOVA do not exist |
| Product/source/NOVA direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H07 product/contract blocker only. It does not authorize implementation and does not close H07.

## 2. Approved Nutrition-Source Contract

Food stores `nutrition_source_type`, `nutrition_source_name`, and `nutrition_source_reference`.

The approved `nutrition_source_type` values are exactly:

```text
laboratory_analysis
official_food_database
official_product_label
manufacturer_website
official_restaurant
calculated_recipe
manual_estimate
multiple_sources
unknown
```

- `nutrition_source_type` is required for newly created or edited Foods; `unknown` is explicitly permitted.
- The user chooses source type but cannot choose source reliability.
- `nutrition_source_name` is required when source type is not `unknown`; `nutrition_source_reference` is optional.
- Source type is not inferred from Food name, brand, URL, ingredients, free-text legacy source, or nutrient values.

## 3. Approved Source-Reliability Contract

| Value | Arabic meaning |
|---|---|
| `high` | مرتفعة |
| `medium` | متوسطة |
| `low` | محدودة |
| `mixed` | متفاوتة |
| `unknown` | غير معروفة |

The approved mapping is:

| Nutrition source type | Source reliability |
|---|---|
| `laboratory_analysis` | `high` |
| `official_food_database` | `high` |
| `official_product_label` | `high` |
| `manufacturer_website` | `high` |
| `official_restaurant` | `medium` |
| `calculated_recipe` | `medium` |
| `manual_estimate` | `low` |
| `multiple_sources` | `mixed` |
| `unknown` | `unknown` |

- The Backend derives reliability from controlled source type. Food does not store it as a user-editable authoritative value.
- `multiple_sources` does not become a numeric average or automatically become high reliability.
- Reliability describes provenance; it is neither a nutrient-accuracy guarantee nor a Food-health rating.
- No combined numeric reliability or trust score is created.
- Current Food reliability may reflect current rules; historical Diary snapshots retain resolved reliability and the rules version from logging time.
- Reliability may be derived at response time rather than persisted on Food, subject to the formal technical contracts.

## 4. Approved Ingredients Contract

Food supports `ingredients_text`, `ingredients_source_type`, `ingredients_source_name`, and `ingredients_source_reference`.

The approved `ingredients_source_type` values are exactly:

```text
official_product_label
manufacturer_website
official_food_database
official_restaurant
calculated_recipe
manual_entry
multiple_sources
unknown
```

- `ingredients_text` is optional.
- When text is present, source type is required, with `unknown` allowed.
- Source name is required when source type is not `unknown`; source reference is optional.
- Ingredients are transparency and classification data and must not be presented as proof of danger.
- No ingredient hazard score is introduced. Allergies and unwanted-ingredient features remain deferred.
- Ingredients are not inferred from Food name, brand, macros, or legacy source text.

## 5. Approved NOVA Contract

`nova_classification` supports exactly `1`, `2`, `3`, `4`, and `unknown`.

`nova_review_status` supports exactly `unreviewed` and `reviewed`.

- NOVA is never inferred from macronutrients.
- Automated classification and suggestions are deferred from Wave 1; no `suggested`, `pending_review`, or automated-review state is introduced.
- The authoritative Wave 1 classification is manually selected and reviewed by the user.
- Selecting and saving a NOVA value marks it reviewed.
- The user may select `unknown`, which may still be reviewed.
- Legacy Foods begin as `nova_classification = unknown` and `nova_review_status = unreviewed`.
- `unknown + reviewed` means review occurred but confident classification was not possible.
- This NOVA-specific state does not introduce a general Food review workflow.

## 6. Rule Versioning

Use independent semantic versions equivalent to `source_reliability_rules_version` and `nova_rules_version`.

A new rules version is required when changing a controlled source type, source-to-reliability mapping, reliability meaning, NOVA values or interpretation, or historical interpretation requirements. Registry packaging and serialization remain for formal Architecture, API, Rule Versioning, and Verification approval.

## 7. Approved API Contract Direction

Food create and update accept:

- `nutrition_source_type`;
- `nutrition_source_name`;
- `nutrition_source_reference`;
- `ingredients_text`;
- `ingredients_source_type`;
- `ingredients_source_name`;
- `ingredients_source_reference`;
- `nova_classification`;
- `nova_review_status` according to approved server transitions.

The client must not submit authoritative `source_reliability`.

Food responses expose a structure equivalent to:

```text
nutrition_source:
  type
  name
  reference
  reliability
  reliability_rules_version

ingredients:
  text
  source_type
  source_name
  source_reference

nova:
  classification
  review_status
  rules_version
```

The Backend derives source reliability. Exact request transitions, null behavior, stable errors, and compatibility envelopes require API and BA/UX approval.

## 8. Diary Snapshot v2

Diary Snapshot v2 preserves:

- `nutrition_source_type`;
- `nutrition_source_name`;
- `nutrition_source_reference`;
- resolved `source_reliability`;
- `source_reliability_rules_version`;
- `nova_classification`;
- `nova_review_status`;
- `nova_rules_version`.

Full ingredients text is not required in Snapshot v2. Editing a Food source or NOVA later, or changing reliability rules, does not alter or reinterpret an old snapshot. Historical values use stored rules versions. The formal document schema remains subject to H08 and the Physical Data Model and API Contracts artifacts.

## 9. Migration And Legacy Compatibility

Existing free-text `data_source` remains readable as deprecated compatibility data. Migration assigns:

```text
nutrition_source_type = unknown
derived reliability = unknown
ingredients_text = null
nova_classification = unknown
nova_review_status = unreviewed
```

- Legacy source text is not parsed to infer source type.
- A URL does not imply `manufacturer_website`.
- NOVA is not inferred from ingredients, macros, name, or category.
- Legacy `data_source` is not deleted or rewritten.
- Manual review may populate controlled fields, and editing must not silently delete legacy text.

## 10. Separation Of Quality Dimensions

Nutrition-data completeness, source reliability, NOVA classification, food-group classification, and nutrient adequacy remain independent. They must not be combined into a unified Health Score, Food Quality Score, or numeric Trust Score.

## 11. Deferred Scope

This decision does not introduce automated or AI NOVA suggestions, a general Food review workflow, ingredient hazard scoring, allergens, unwanted-ingredient tracking, nutrient-level provenance, a full recipe engine, OCR, barcode scanning, Nutrition Pattern Analysis UI, Progress UI, direct gram/ml Diary logging, or unrelated Food redesign.

## 12. Compatibility And Baseline Preservation

Current Foods, Diary, Add Food, and Profile behavior remains baseline where compatible. This direction does not authorize a broad rewrite, historical reinterpretation, offline personal-data storage, or unrelated behavior changes.

Exact physical schema, API errors, caching, UI transitions, migration, implementation, and verification remain open for assigned technical approvals.

## 13. Status

```text
Artifact ID: DEC-H07
Selected source direction: Store controlled source type and derive reliability
Reliability authority: Backend
Reliability levels: high, medium, low, mixed, unknown
User-editable reliability: Prohibited
Ingredients source vocabulary: Approved
NOVA baseline: Manual reviewed classification
Automated NOVA suggestions: Deferred
General Food review workflow: Deferred
Legacy source inference: Prohibited
Historical snapshot reinterpretation: Prohibited
Product/contract blocker: Resolved
Architecture, Security, Data, API, Migration, UX, implementation, and verification: Still open
H07 overall status: Open
```

H07 remains open until the direction is represented in approved, pinned freeze contracts, implemented, migrated, verified, traced, and accepted by a final readiness recheck.
