# V2 Food Taxonomy

## Food Category

The API field is `food_category_key`; the Arabic UI label is `فئة الطعام`.

Stable categories:

`vegetables`, `fruits`, `legumes`, `grains_starches`, `baked_goods`,
`nuts_seeds`, `seafood`, `dairy_fortified_alternatives`, `eggs`, `poultry`,
`red_meat`, `processed_meat`, `added_oils_fats`, `sweets`,
`sugar_sweetened_beverages`, `unsweetened_beverages`, `herbs_spices`,
`mixed_dish`, and `other`.

The former free-text compatibility `category` column is removed from new API,
UI, and storage after its value is preserved in migration audit evidence.
`whole_grains` and `refined_grains` are not top-level categories.

## Structured Details

- `grain_type`: `whole`, `refined`, `mixed`, `grain_free`, or `unknown`.
- `baked_good_type`: `arabic_bread`, `toast`, `rolls_wraps`, `burger_bun`,
  `flatbread`, `pastries`, `cake`, `biscuits_cookies`, or `other`.
- `grain_starch_type`: `rice`, `pasta`, `oats`, `breakfast_cereal`, `bulgur`,
  `quinoa`, `flour`, or `other`.

`baked_goods` requires `baked_good_type` and `grain_type`.
`grains_starches` requires `grain_starch_type` and `grain_type`.
The three detail fields are null for unrelated categories.

## Registry

Taxonomy semantic changes require `nutrition_registry_version=2.0.0` and
`registry_schema_version=2`. Historical records retain their stored versions.
The Food Group rules and nutrient formulas are unchanged unless their manifest
content demonstrably changes.

## Migration

Old whole/refined categories map to `grains_starches` with the corresponding
`grain_type`. Ambiguous likely baked records are marked review-required and are
not guessed. A dry-run tool emits deterministic JSON/CSV proposals; only an
explicit reviewed mapping is applied.
