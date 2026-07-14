# Foods Batch 001 Import Report

Date: 2026-07-10
Dataset: `mynutri_foods_batch_001.json`
Declared records: 15

## 1. Target Database

- Database: `mynutri_dev`
- Database engine: local PostgreSQL only
- Alembic revision: `0002_foods_v1_per_basis` (head)
- Food count before import: 0
- Food count after import and test cleanup: 14
- Production databases used: none

The importer calls `SELECT current_database()` and refuses to run unless the result is exactly `mynutri_dev`.

## 2. Files Changed

- `backend/scripts/__init__.py`
- `backend/scripts/import_foods_batch_001.py`
- `backend/tests/test_foods_batch_import.py`
- `docs/implementation/09_FOODS_BATCH_001_IMPORT_REPORT.md`

No model, migration, API, BA, QA, archive, offline/sync, or product behavior file was changed.

## 3. Schema-Field Mapping

| Transport field | Current myNutri field | Transformation |
|---|---|---|
| `name` | `name` | Existing schema trims and collapses whitespace. |
| `nutrition_basis_amount=100`, `nutrition_basis_unit=g` | `nutrition_basis` | Mapped to `per_100g`; other basis inputs are rejected. |
| `calories` | `calories` | Preserved; no macro-derived replacement. |
| `protein_g` | `protein_g` | Direct mapping. |
| `carbohydrates_g` | `carb_g` | Renamed only. |
| `fat_g` | `fat_g` | Direct mapping. |
| `fiber_g` | `fiber_g` | Missing/null remains null; explicit zero remains zero. |
| `total_sugar_g` | `sugar_g` | Renamed to the current total-sugar field. |
| `added_sugar_g` | `added_sugar_g` | Direct mapping. |
| `saturated_fat_g` | `saturated_fat_g` | Direct mapping. |
| `trans_fat_g` | `trans_fat_g` | Direct mapping. |
| `sodium_mg` | `sodium_mg` | Direct mapping. |
| `cholesterol_mg` | `cholesterol_mg` | Direct mapping. |
| `potassium_mg` | `potassium_mg` | Direct mapping. |
| `calcium_mg` | `calcium_mg` | Direct mapping. |
| `iron_mg` | `iron_mg` | Direct mapping. |
| Remaining supported mineral/vitamin keys | Matching current fields | Direct mapping when present; otherwise null. |
| `default_unit_name` | `default_unit_type` | Arabic label mapped through the approved enum table below. |
| `default_unit_amount` | `unit_amount` | Direct numeric mapping. |
| `default_unit_base` | `unit_basis` | `g` in this batch. |
| `notes` | `notes` | Data-quality prefix added before source notes. |
| `data_source` | `data_source` | Preserved. |
| `data_quality` | `notes` prefix | Preserved using an explicit Arabic quality classification. |

`brand` and `category` are null because the transport records do not provide dedicated values. Brand-like text embedded in Food names was not guessed into separate fields.

## 4. Transformations Performed

- All accepted records use `nutrition_basis=per_100g`.
- Transport `carbohydrates_g` became `carb_g`.
- Transport `total_sugar_g` became `sugar_g`; `total_sugars_g` was not introduced.
- Missing properties and explicit nulls remained null.
- Explicit source zeros remained zero.
- Data quality was prefixed to notes and never discarded.
- Existing schema normalization handled surrounding/repeated whitespace.
- Printed calories were not changed when they differed from macro-derived energy.
- No raw SQL insert or validation bypass was used.

## 5. Unit-Name Mapping

| Arabic input | Internal enum | Result |
|---|---|---|
| `حصة` | `serving` | Accepted |
| `شريحة` | `slice` | Accepted |
| `حبة` | `piece` | Accepted |
| `قطعة` | `piece` | Accepted |
| `علبة` | None | Blocked; current enum has no package/container unit |

Decision Needed for `زبادي كامل الدسم - المراعي`: either add `container` as a future product change or explicitly approve mapping `علبة` to `serving`. The importer did not make this decision silently.

## 6. Data-Quality Mapping

| Transport quality | Arabic notes prefix |
|---|---|
| `label_direct` | `جودة البيانات: مباشرة من الملصق` |
| `label_derived` | `جودة البيانات: مشتقة من الملصق` |
| `label_derived_corrected` | `جودة البيانات: مشتقة من الملصق بعد تصحيح` |
| `label_derived_user_corrected` | `جودة البيانات: مشتقة من الملصق مع تصحيحات المستخدم` |
| `estimated` | `جودة البيانات: تقديرية` |
| `standard_estimate` | `جودة البيانات: تقدير قياسي` |

The three required estimate records remain visibly marked:

- `شاورما عربي مع تغميسة ثوم`: تقديرية
- `بطاطس مقلية - حبة واحدة`: تقديرية
- `بيض مسلوق`: تقدير قياسي

## 7. Validation Results

Dry-run result before insertion:

- Valid: 14
- Existing duplicates: 0
- Batch-internal duplicates: 0
- Failed schema/range/cross-field validation: 0
- Blocked mapping decisions: 1 (`علبة`)

Every accepted record passed `FoodCreate` validation, including required fields, enum values, D-026 ranges, non-negative constraints, unit amount, and all applicable cross-field rules. Twenty-three independent note-derived default-unit checks passed within a tolerance of 0.06.

PostgreSQL verification after insertion:

- Stored rows matched mapped payloads: 14/14
- Search checks: 14/14
- Default-unit recalculations: 14/14
- Optional-nutrient row checks: 14/14
- Arabic name checks: 14/14
- Estimate marking checks: 3/3
- Blocked yogurt absent: yes

## 8. Default-Unit Calculation Results

Core values below are `calories / protein_g / carb_g / fat_g` for one default unit. All optional nutrients were calculated with the same `per-100 × unit_amount / 100` formula and verified without modifying source values.

| Food | Unit | Calculated core unit values | Independent checks |
|---|---|---|---|
| زبدة الفول السوداني - المواسم | `serving 16 g` | `100.5008 / 4 / 3.5008 / 8` | Calculated; no independent unit totals supplied |
| زبدة الفول السوداني الطبيعية - Regano | `serving 16 g` | `102.24 / 4.8 / 2.88 / 7.84` | Calculated; no independent unit totals supplied |
| كيتو كوكيز بالشوكولاتة - KEO | `serving 15 g` | `79.9995 / 1.9995 / 1.9995 / 7.9995` | 2/2 passed |
| توست البر - لوزين | `slice 30 g` | `77.001 / 3 / 14.001 / 0.999` | 1/1 passed |
| بسكويت رونديتاس بالشوكولاتة الداكنة بدون سكر - Gullón | `piece 6.2 g` | `31.7998 / 0.4402 / 4.0002 / 1.5599` | 1/1 passed |
| ويفر كابريس محشو بالشوكولاتة - Papadopoulos | `piece 5.8 g` | `28.0001 / 0.4101 / 3.9399 / 1.1003` | 1/1 passed |
| بسكويت أوريو ميني - Oreo Minis | `piece 3.22 g` | `15.5449 / 0.1111 / 2.3316 / 0.6662` | 1/1 passed |
| بسكويت الشوفان بالشوكولاتة الداكنة بدون سكر - Gullón Oaty | `piece 14 g` | `69.0004 / 1.1004 / 9.5004 / 3.0996` | 1/1 passed |
| بسكويت رقائق الشوكولاتة بدون سكر - Gullón Chip Choc | `piece 19 g` | `95.9994 / 1.1001 / 12.9998 / 4.5999` | 1/1 passed |
| بسكويت مغطى بالشوكولاتة الداكنة بدون سكر مضاف - Gullón Choc Tablet | `piece 12.5 g` | `63.5 / 0.85 / 8.5 / 3` | 1/1 passed |
| زبادي كامل الدسم - المراعي | `علبة 170 g` | Not imported | Blocked mapping decision |
| شرائح جبنة برجر كاملة الدسم - المراعي | `slice 20 g` | `56 / 3 / 1 / 5` | 2/2 passed |
| شاورما عربي مع تغميسة ثوم | `piece 57 g` | `179.0028 / 8.4987 / 13.2012 / 10.1973` | 4/4 passed |
| بطاطس مقلية - حبة واحدة | `piece 4 g` | `13 / 0.15 / 1.6 / 0.65` | 4/4 passed |
| بيض مسلوق | `piece 50 g` | `78 / 6.3 / 0.6 / 5.3` | 4/4 passed |

## 9. Record Results

| Food name | Status | Reason | Created ID / stable identifier |
|---|---|---|---|
| زبدة الفول السوداني - المواسم | Inserted | Validated and created through Food service | `ef84e60e-d3d0-4271-a1ae-f66b21691c30` |
| زبدة الفول السوداني الطبيعية - Regano | Inserted | Validated and created through Food service | `6d77216b-993c-406f-9476-a0495bbf2990` |
| كيتو كوكيز بالشوكولاتة - KEO | Inserted | Validated and created through Food service | `73905766-ed49-4ff2-a04f-45cf05964953` |
| توست البر - لوزين | Inserted | Validated and created through Food service | `da673dc2-3a65-42d4-bacd-0e6740526c4d` |
| بسكويت رونديتاس بالشوكولاتة الداكنة بدون سكر - Gullón | Inserted | Validated and created through Food service | `db64bbd1-2c2d-4376-a2dc-d7fa3a4083b5` |
| ويفر كابريس محشو بالشوكولاتة - Papadopoulos | Inserted | Validated and created through Food service | `f3ae7f67-6918-4508-931d-c1050758f112` |
| بسكويت أوريو ميني - Oreo Minis | Inserted | Validated and created through Food service | `a2b79cc7-458f-463a-8239-dd616c5ad3b4` |
| بسكويت الشوفان بالشوكولاتة الداكنة بدون سكر - Gullón Oaty | Inserted | Validated and created through Food service | `90ad2ff5-014a-4293-8d7b-d5eef0171fc3` |
| بسكويت رقائق الشوكولاتة بدون سكر - Gullón Chip Choc | Inserted | Validated and created through Food service | `6b071a20-22ca-437a-8a2b-93c85dbd5b6d` |
| بسكويت مغطى بالشوكولاتة الداكنة بدون سكر مضاف - Gullón Choc Tablet | Inserted | Validated and created through Food service | `9be5d6d4-c6c0-4d1b-b4bb-873299e84aac` |
| زبادي كامل الدسم - المراعي | Blocked by mapping decision | `علبة` is unsupported; no silent conversion | Duplicate key if approved later: normalized name + `per_100g` + chosen unit + `170` + `g` |
| شرائح جبنة برجر كاملة الدسم - المراعي | Inserted | Validated and created through Food service | `20f41722-dbee-41c6-af84-cab353efa7aa` |
| شاورما عربي مع تغميسة ثوم | Inserted | Validated, estimate marking preserved | `dafd11e6-97aa-4205-9bf1-53c7cb2e7dc6` |
| بطاطس مقلية - حبة واحدة | Inserted | Validated, estimate marking preserved | `23fa8c05-8d04-4790-88fb-f6fde9061cf5` |
| بيض مسلوق | Inserted | Validated, standard-estimate marking preserved | `643a28c6-0063-4a53-b0d6-5cde8588240f` |

## 10. Duplicate Decisions

The importer uses the current Food service duplicate key:

1. normalized name using trim, whitespace collapse, and `casefold`
2. nutrition basis
3. default unit type
4. unit amount rounded to four decimals
5. unit basis

Initial dry run found no existing or in-batch duplicate. No looser name-only duplicate rule was introduced. The blocked yogurt was not inserted and therefore does not block future creation.

## 11. Idempotency Re-run

The same apply command was executed a second time:

- Inserted: 0
- Skipped as duplicate: 14
- Duplicate results linked to existing stable IDs: 14
- Blocked decision: 1
- Catalog count after rerun: 14

## 12. Tests and Outcomes

| Check | Outcome |
|---|---|
| Importer + targeted backend Food tests | 24 passed |
| Full backend suite | 28 passed, 1 Future-Scope sync test skipped |
| Importer idempotency test | Passed |
| Import null/zero and unit mapping tests | Passed |
| PostgreSQL schema and row smoke verification | 14/14 passed |
| Ruff | Passed |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| Playwright navigation/list/search/state smoke on production build | 34 passed |
| Direct imported Arabic search/detail/estimate check | Passed |

An initial smoke attempt against a long-running Turbopack dev process remained in server-rendered loading states and failed 24 API-dependent cases. The same unchanged tests passed 34/34 against the clean production build; this was an environment hydration issue and did not alter import data or application code.

## 13. Remaining Risks and Decisions

- Product decision required for `علبة`: add `container` or explicitly map to `serving`.
- Until that decision is made, the yogurt remains intentionally absent.
- Source values are stored in two-decimal PostgreSQL numeric columns. Current source values fit this precision; calculated unit values are reporting calculations, not stored duplicate columns.
- Label-derived and estimated accuracy remains dependent on the source information, which is why quality prefixes were preserved.

## 14. Safety Confirmation

- No archive/inactive behavior was added.
- No `is_active`, `archived_at`, status filter, or workflow was added.
- No offline/sync behavior was added.
- No production database was used.
- No validation rule was weakened or bypassed.
- No raw SQL data insertion was used.
- Permanent hard-delete behavior was unchanged.
- No commit was created.
