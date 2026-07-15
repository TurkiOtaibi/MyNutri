# H06 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H06` |
| Issue ID | `H06` |
| Severity | High |
| Title | Food-group registry, contributions, and traits do not exist |
| Product/food-group direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H06 product/contract blocker only. It does not authorize implementation and does not close H06.

## 2. Approved Persistence And Registry Direction

Use normalized Principal-scoped relational child tables for Food-group contributions and Food analytical traits. The Backend owns one versioned Food Group and Analytical Trait Registry.

The existing free-text `category` remains a compatibility field and is not an analysis input.

## 3. Approved Primary Category

Add controlled `primary_category_key` with exactly these values:

```text
vegetables
fruits
legumes
whole_grains
refined_grains
nuts_seeds
seafood
dairy_fortified_alternatives
eggs
poultry
red_meat
processed_meat
added_oils_fats
sweets
sugar_sweetened_beverages
unsweetened_beverages
herbs_spices
mixed_dish
other
```

It is used for organization, filtering, and display only. It does not create a contribution or directly drive nutrition analysis. No legacy free-text category is converted automatically. New or reviewed Foods use the controlled key; `other` is valid; legacy category remains readable during compatibility and deprecation.

## 4. Approved Food Kind And Group Data States

User-facing Food kinds are `simple` and `composite`. Internal `unknown` is allowed only for unreviewed legacy records and is not a normal new-Food choice after rollout.

`group_data_status` values:

- `known`: confirmed contribution classification.
- `estimated`: one or more values are estimates.
- `unknown`: no usable contribution classification.

`group_data_completeness` values:

- `complete`: all relevant contributions were reviewed, even when total is below 100.
- `partial`: usable information exists but some remains unknown.
- `unknown`: completeness cannot be established.

A Food may be `known + complete` with no contribution rows when review confirms no tracked Food-group contribution.

## 5. Approved Contribution Model

Each contribution contains Food identity, stable group key, nullable subtype where required, `amount_per_100_basis`, certainty/status metadata, `food_group_rules_version`, and C01 ownership/audit metadata.

- Amount uses the Food nutrition basis.
- Per-100g Foods use grams; per-100ml Foods use millilitres.
- The client cannot provide a conflicting independent unit.
- Amount is greater than zero and no greater than 100.
- Zero-value rows are not persisted.
- One Food has at most one row per group key.
- Rows are Principal/Food scoped.
- Mutually exclusive totals cannot exceed 100.
- Totals below 100 are valid.
- Remainder is not assigned automatically to `other`.
- Migration infers nothing from name, legacy category, brand, macros, NOVA, or ingredients.

Exact names, key types, precision, cascades, indexes, and update transaction require Architecture, Security, Engineering/Data, API, and QA approval.

## 6. Approved Default Overlap Policy

Contributions are mutually exclusive by default. Cross-cutting properties use traits.

| Food example | Approved representation |
|---|---|
| Salmon | Seafood contribution plus `omega3_rich_seafood` trait |
| Sweetened yogurt | Dairy contribution plus `sweetened` trait |
| Processed turkey slices | Processed-meat contribution; no positive poultry contribution |
| Peanuts | Nuts/seeds contribution; no legumes contribution |
| Nut oil | Added-oils/fats contribution; no nuts/seeds contribution |
| 100% fruit juice/smoothie | Fruits contribution plus `fruit_liquid_100_percent`; no unsweetened-beverages contribution |
| Potato/starchy root | No vegetables contribution plus `starchy_root` trait |

Later overlap exceptions require an explicit versioned Registry rule and tests.

## 7. Approved Analytical Traits

Initial keys are exactly:

```text
sweetened
non_nutritive_sweetened
processed
omega3_rich_seafood
calcium_fortified
unsaturated_fat_source
smoked
salted
fruit_liquid_100_percent
dried_fruit
starchy_root
```

Traits are separate from contributions, unique per Food/key, excluded from contribution totals, never create duplicate servings, and version through `food_group_rules_version` or the approved related Registry version. Future automated suggestions require explicit review. Wave 1 adds no AI classification.

## 8. Approved Serving And Target Rules

### Vegetables and fruit

- Combined target `400 g/day`; display separately and combined.
- Vegetable and fresh/whole fruit serving: `80 g`.
- Dried fruit serving: `30 g`.
- 100% fruit liquid serving: `150 ml`, capped at one fruit serving/day.
- Legumes are separate; potatoes/starchy roots do not count as vegetables.

### Whole and refined grains

Grain contributions use per-100g Foods. Whole-grain share is:

```text
whole_grain_contribution /
(whole_grain_contribution + refined_grain_contribution)
```

Target is at least 50% among known grain contributions. Unknown is not assigned, and classification coverage is displayed.

### Legumes, nuts/seeds, and seafood

- Legumes: `80 g` cooked per serving; at least 3/week; fractions accumulate.
- Nuts/seeds: `30 g`; at least 5/week; peanuts count; extracted oils count as added oils/fats.
- Seafood: `100 g` edible portion; at least 2/week; at least one has `omega3_rich_seafood`; smoked/salted are traits.

### Dairy and fortified alternatives

Subtype keys and servings:

| Subtype | Serving |
|---|---:|
| `milk_laban_kefir` | 250 ml |
| `yogurt` | 200 g |
| `hard_cheese` | 30 g |
| `cottage_ricotta` | 120 g |
| `fortified_plant_alternative` | 250 ml |

Target is 2/day. A plant alternative counts only when calcium is known, at least `100 mg/100 ml`, and `calcium_fortified` is present. Sweetened dairy still counts while sugar remains separately tracked. Butter, ghee, cream, and ice cream do not satisfy the target.

### Eggs, poultry, and meat

- Egg subtypes: `whole_egg`, `egg_white`, `mixed_egg_product`; large whole egg approximately `50 g`; monitor-only.
- Poultry: `100 g` cooked edible; monitor-only; processed poultry is processed meat.
- Red meat: `100 g` reference; maximum `500 g/week`; `350-500 g` near limit; above `500 g` over limit.
- Processed meat: minimize; show grams and occasions.

### Remaining groups

- Added oils/fats, unsweetened beverages, herbs/spices: monitor-only.
- Sweets and sugar-sweetened beverages: minimize.

## 9. Approved Group Coverage

Coverage does not use primary-category presence.

- `unknown` contributes no usable coverage.
- Complete classification treats consumed amount as fully classified, including reviewed Foods with no contribution rows.
- Partial classification uses only the classified fraction represented by mutually exclusive contributions.
- Estimated data may be used but is disclosed.
- Insufficient coverage prevents strong downstream analysis under the later analysis policy.

Exact Diary formula and thresholds are frozen in later contracts without changing these meanings.

## 10. Approved Snapshot v2 Behavior

Snapshot v2 preserves `food_kind`, `primary_category_key`, group-data status and completeness, quantitative contributions, traits, and `food_group_rules_version`. Food edit/delete cannot reinterpret an existing snapshot. Snapshot v1 remains readable.

## 11. Approved Migration And Compatibility

Existing Foods retain free-text category; receive no inferred primary category; use `food_kind = unknown` or approved nullable equivalent; receive unknown status/completeness; and receive no contribution or trait rows. No legacy value is deleted or rewritten. Reviewing a legacy Food is an explicit later user action.

## 12. Deferred Scope

This direction excludes a full recipe engine, ingredient quantity calculation, AI classification, barcode/OCR, generalized import expansion, nutrient-level provenance, allergens, dietary/religious labels, preparation taxonomy, Progress or seven-day Analysis UI, direct gram/ml Diary logging, offline personal-data storage, and unrelated Foods redesign.

## 13. Approval And Work Boundaries

Product, Registry, group, contribution, trait, serving, and coverage semantics are approved. Exact physical schema, API, migration, Arabic UI, transaction mechanics, implementation, verification, and traceability remain open.

## 14. Recorded Status

```text
Artifact ID: DEC-H06
Selected persistence direction: Normalized contribution and trait tables
Registry authority: Backend
Primary category: Controlled and organizational only
Food kind: simple or composite
Legacy food kind: unknown
Group-data status: known, estimated, or unknown
Group-data completeness: complete, partial, or unknown
Default contribution overlap: Mutually exclusive
Traits create servings: No
Legacy category/name inference: Prohibited
Product/contract blocker: Resolved
Architecture, Security, Data, API, Migration, UX, implementation, and
verification: Still open
H06 overall status: Open
```

H06 remains open until formal contracts, migration, implementation, verification, and traceability are approved.
