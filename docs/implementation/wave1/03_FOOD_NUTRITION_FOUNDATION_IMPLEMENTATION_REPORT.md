# Wave 1 Stage 03 Food Nutrition Foundation Implementation Report

## 1. Stage Identity and Scope

| Field | Value |
|---|---|
| Report ID | `W1-IMPL-03` |
| Stage | `03 - Food nutrition foundation` |
| Branch | `impl/wave1-03-food-nutrition-foundation` |
| Worktree | `C:\Users\DELTA\Desktop\MyNutri-wave1-03` |
| Base SHA | `76f7ac8a1b03179cfb4266409932c1c72ff00ece` |
| Implementation commit | Pending |
| Pull request | Pending |
| Report date | `2026-07-16` |

This stage implements the frozen Food nutrient, classification, source, ingredients, and NOVA foundation. It does not create Target Plans, Snapshot v2, aggregation, direct gram/ml logging, recipes, AI classification, or later-wave analysis.

## 2. Frozen Authorities

- H05, H06, H07, H09, and H10.
- ADR-001, ADR-003, ADR-004, and ADR-007.
- Artifacts 14, 15, 16, 17, 19, 20, and 21.
- Stories `US-W1-FOOD-001` through `US-W1-FOOD-004` and applicable security/legacy criteria.

## 3. Data Model and Migrations

Two additive revisions follow the frozen boundary:

| Revision | Purpose | Rollback boundary |
|---|---|---|
| `0007_food_quality_expand` | Controlled Food fields, four exact nullable nutrients, source, ingredients, NOVA, checks, and indexes | Downgrade fails if Wave 1 data would be lost |
| `0008_food_groups_expand` | Principal-scoped normalized contribution and trait tables plus concurrency-safe total enforcement | Downgrade fails while child data exists |

Revisions `0001` through `0003` remain byte-for-byte immutable. Existing Foods receive truthful `unknown`/`unreviewed` compatibility states, null exact fields, and no inferred category, group, trait, source, ingredients, NOVA, or versions. Existing `category`, `data_source`, `folate_mcg`, and `vitamin_a_mcg` remain readable.

The four new exact fields use nullable `numeric(10,3)`:

- `selenium_mcg`;
- `iodine_mcg`;
- `folate_dfe_mcg`;
- `vitamin_a_rae_mcg`.

## 4. Food Groups and Traits

`food_group_contribution` enforces owner-consistent composite foreign keys, one row per Food/group, `0 < amount <= 100`, approved keys/statuses, and version storage. A deferred PostgreSQL constraint trigger uses a transaction advisory lock by Food ID and rejects concurrent totals above 100. Partial totals remain valid and no remainder is fabricated.

`food_analytical_trait` stores the eleven approved independent traits with owner-consistent cascade and one row per Food/trait. Traits do not enter contribution totals. Create/update replaces the complete submitted child sets atomically.

## 5. Source, Ingredients, and NOVA

- The API accepts controlled nutrition source type/name/reference and derives reliability in the Backend.
- Client-supplied reliability and rule versions are rejected.
- `multiple_sources` resolves to `mixed`; no numeric trust score exists.
- Ingredient text and controlled source metadata follow the required-name transitions.
- NOVA accepts only `1`, `2`, `3`, `4`, or `unknown`; an explicit selection becomes `reviewed`.
- No inference, AI suggestion, general review workflow, or historical reinterpretation is introduced.

The runtime Registry now supplies Arabic display metadata for primary categories, groups, subtypes, traits, source types, ingredient-source types, reliability, and NOVA. This completes the existing Backend-authority boundary without changing governed keys, rule meanings, or initial independent versions. The pre-release canonical manifest lock is updated to:

```text
36385964adf831058b988d6f0cc3098e234531fc71bdf1e7c44abb9e6cd3391d
```

## 6. API and Frontend

Existing owner-scoped Food routes remain additive. Responses expose nested source/reliability, ingredients, NOVA, complete contributions, traits, and legacy ambiguous nutrient metadata. New public Food creation requires an explicit controlled primary category, `simple`/`composite` kind, and nutrition source type; `unknown` remains a truthful explicit source value. Internal legacy/import compatibility can retain `food_kind=unknown` without presenting it as a normal new-Food choice.

The Arabic-first Food form consumes runtime Registry metadata, blocks Registry-dependent writes when metadata is unavailable or incompatible, and supports the exact nutrients, controlled classification, complete contribution replacement, traits, source/reliability, ingredients, and NOVA. Food details distinguish exact DFE/RAE values from deprecated ambiguous legacy values. Existing list, serving, edit, delete, RTL, and mobile behavior remains intact.

The Food form does not expose the ambiguous legacy `folate_mcg` or `vitamin_a_mcg` fields for new entry or editing. Existing values remain preserved through compatibility payloads and are displayed read-only with the approved legacy meaning; exact replacement uses `folate_dfe_mcg` and `vitamin_a_rae_mcg`.

## 7. Files Changed

Backend implementation:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/api/routes/foods.py`
- `backend/app/services/food.py`
- `backend/app/services/food_validation_errors.py`
- `backend/app/nutrition_rules/manifest.py`
- `backend/app/nutrition_rules/registry.py`
- `backend/app/nutrition_rules/rules_manifest.lock.json`
- `backend/scripts/import_foods_batch_001.py`
- `backend/alembic/versions/0007_food_quality_expand.py`
- `backend/alembic/versions/0008_food_groups_expand.py`

Frontend implementation:

- `frontend/lib/types.ts`
- `frontend/lib/food.ts`
- `frontend/components/FoodFormPage.tsx`
- `frontend/components/FoodDetailsPage.tsx`
- `frontend/app/globals.css`

Tests and evidence:

- `backend/tests/test_foods.py`
- `backend/tests/test_principal_migrations.py`
- `backend/tests/test_principal_security.py`
- `backend/tests/test_rules_registry_api.py`
- `frontend/e2e/foods/helpers.ts`
- `frontend/e2e/foods/serving-first.spec.ts`
- `frontend/e2e/foods/stability.spec.ts`
- `frontend/e2e/foods/wave1-quality.spec.ts`
- this report and the implementation register.

## 8. Validation Results

| Gate | Result | Evidence |
|---|---|---|
| Ruff | Passed | All checks passed |
| Backend non-migration suite | Passed | 94 passed; one expected Future Scope skip |
| PostgreSQL migration suite | Passed | 5 passed, including fresh/populated and concurrency rehearsal |
| Alembic upgrade | Passed | Fresh `0001` through `0008` |
| Alembic model drift | Passed | No new upgrade operations detected |
| Frontend typecheck | Passed | Exit 0 |
| Frontend production build | Passed | 8 routes generated |
| Food Playwright regression | Passed | 168 passed, 0 failed, 0 skipped |
| Full Playwright regression | Passed | 249 passed, 0 failed, 0 skipped |
| `git diff --check` | Passed | No whitespace errors |

The first Food E2E run exposed test-database contamination: the migration concurrency fixture left a deliberately classified child attached to a Food whose status remained legacy `unknown`, causing truthful response validation to reject list reads. The fixture now uses a coherent state and deletes its data. The same run exposed an implicit `output` status role and a legacy-category label collision; both accessibility defects were corrected. The repeated Food suite passed `168/168`.

The first complete regression attempts also exposed the already documented retained-fixture prerequisite and a hydration race in date-input tests. The disposable database was supplied with the characterized 2000-calorie Profile and recent non-E2E Food, canonical repository ports `3000/8000` were used for route interception, and affected date tests now wait for React hydration before filling the controlled date input. A later reset attempted to update a missing retained Food without checking the affected-row count; that invalid setup produced `248/249` with the Add Food sheet truthfully showing an empty Food list. After creating the required local seed through the public API, the failed test passed in isolation and the repeated complete suite passed `249/249`. Generated visual evidence was restored and excluded from the stage diff.

## 9. Security Review

- All Food and child reads/writes are scoped through typed Principal context.
- Food create, update, delete, duplicate detection, and complete child-set replacement serialize on the owning Principal row so concurrent requests cannot bypass namespace invariants.
- Child ownership is enforced in both service predicates and composite database foreign keys.
- Cross-owner Food IDs retain non-enumerating behavior.
- Clients cannot submit owner IDs, reliability, or rule versions.
- Registry metadata exposes no credentials or Principal data.
- Hard delete removes child metadata but preserves immutable Diary snapshot content.

## 10. Data and Migration Review

- Fresh upgrade, populated `0003` upgrade, explicit Principal provisioning, row reconciliation, null preservation, known-zero preservation, and no-inference behavior are executable PostgreSQL evidence.
- The deferred total trigger passed a two-transaction race where `60 + 50` was attempted; exactly one commit succeeded and persisted total remained at most 100.
- Model-versus-migration drift is zero.
- No production database was used.

## 11. Legacy Compatibility

- Existing Food fields and route purposes remain available.
- Generic folate/vitamin A values remain stored and displayed only as legacy ambiguous data.
- Generic fields never populate exact DFE/RAE values or completeness.
- Existing Diary snapshots survive Food deletion and are not enriched or rewritten.
- Legacy free-text category/source are retained and clearly identified as compatibility data.

## 12. Rollback Behavior

Application rollback must remain schema-compatible. Schema downgrade is allowed only before new data exists; both revisions fail clearly when downgrade would discard Wave 1 Food data. No legacy field or reader is removed.

## 13. Traceability

Covered: H05-H07 and H09-H10; Artifact 14 Food/child structures; Artifact 15 Food contracts; Artifact 16 revisions `0007`/`0008`; Artifact 17 Food stories; Artifact 19 Food form/detail/loading/error/mobile states; Artifact 20 migration, isolation, validation, hard-delete, Registry, and responsive gates.

## 14. Independent Strict Review

| Category | Result |
|---|---|
| Product behavior | Matches frozen Food, Registry, source, ingredients, and NOVA semantics |
| Architecture | Backend remains Registry/rule authority; normalized child boundary preserved |
| Security | Principal isolation and non-authoritative-field rejection preserved |
| Data integrity | Exact null/zero semantics and concurrent total enforcement passed |
| Migration safety | Additive, no-inference, populated rehearsal, and lossy-downgrade guard passed |
| API compatibility | Existing routes/fields retained; additions are nested/additive |
| Scope containment | No Target Plan, Snapshot v2, aggregation, recipe, AI, or later-wave feature |

### Findings

| Severity | Finding | Disposition |
|---|---|---|
| Critical | None | N/A |
| High (unresolved) | None | N/A |
| High (resolved during review) | Ambiguous legacy folate/vitamin A fields remained editable in the Food form | Removed from editable UI; compatibility persistence and read-only legacy disclosure retained; exact DFE/RAE controls tested |
| Medium | Registry lacked Arabic presentation metadata for Food dimensions | Added to Backend manifest; pre-release lock updated |
| Medium | Migration concurrency fixture polluted subsequent E2E state | Fixture now coherent and self-cleaning |
| Medium | Existing E2E date fill could run before React hydration | Test synchronization added; no Diary behavior changed |
| Medium | Concurrent Food namespace mutations could race duplicate and complete child-set checks | Principal-scoped transaction lock added to create, update, and delete |
| Medium | Update payloads could silently ignore an unknown top-level authority field | `FoodUpdate` now rejects extra fields; client reliability rejection is covered |
| Low | Estimated group status without an estimated contribution was internally inconsistent | Stable validation rejection and regression coverage added |
| Low | Existing Starlette TestClient deprecation warning | Dependency-maintenance risk retained |

## 15. Residual Risks

- Physical iPhone Safari and Android Chrome evidence remains a Stage 08 production-release gate.
- Snapshot v2 historical preservation of the new Food dimensions remains Stage 05 scope.
- Weekly food-group analysis remains deferred and is not implemented.

## 16. Stage Verdict

```text
Food schema and API contract: Implemented
Migration rehearsal: Passed
Food E2E regression: Passed 168/168
Full regression: Passed 249/249
Critical findings: 0
High findings: 0
Frozen-contract deviations: 0
Later-wave features introduced: 0
Stage verdict: Ready to Merge
```
