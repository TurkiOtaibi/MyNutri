# Wave 1 Stage 02 Rules, Registry, and Calculations Implementation Report

## 1. Stage Identity and Scope

| Field | Value |
|---|---|
| Report ID | `W1-IMPL-02` |
| Stage | `02 - Rules, Registry, and calculation engine v2` |
| Branch | `impl/wave1-02-rules-registry-calculations` |
| Worktree | `C:\Users\DELTA\Desktop\MyNutri-wave1-02` |
| Base SHA | `eb0abc5324818a32046d8256e016c9d398a50b1b` |
| Implementation commit | Pending |
| Pull request | Pending |
| Report date | `2026-07-16` |

This stage implements the Backend-owned Wave 1 nutrition rules package, runtime Registry, and calculation engine `2.0.0`. It does not add Food persistence fields, Target Plans, Snapshot v2, or later-wave analysis.

## 2. Frozen Authorities

- H01, H02, H03, H05, and H10.
- ADR-004 and ADR-007.
- Artifacts 14, 15, 18, 20, and 21.
- PD-005 through PD-007 and PD-009.

## 3. Rules Package

The new `app.nutrition_rules` package is the single typed, declarative Backend authority for:

- independent initial versions;
- Mifflin, activity, goal, deficit, safety, protein, fat, and carbohydrate policy;
- all 16 approved nutrient definitions and resolved target rules;
- food-group, serving, subtype, overlap, cap, and exclusion metadata;
- analytical trait keys;
- source-to-reliability mapping and reliability labels;
- ingredient-source vocabulary;
- NOVA values and review states;
- Registry and Snapshot schema versions;
- inactive Wave 3 analysis version state.

Modules are import-side-effect-free and calculations are pure. Rules are not database-editable and no Python source is exposed by the API.

## 4. Version and Manifest Integrity

| Version | Value |
|---|---|
| Nutrition Registry | `1.0.0` |
| Calculation engine | `2.0.0` |
| Food-group rules | `1.0.0` |
| Source-reliability rules | `1.0.0` |
| NOVA rules | `1.0.0` |
| Registry schema | `1` |
| Snapshot schema | `2` |
| Analysis rules | `null`, `reserved_for_wave_3` |

Canonical UTF-8 JSON serialization sorts keys and removes insignificant whitespace. SHA-256 is deterministic and is locked with the exact independent version bundle in `rules_manifest.lock.json`.

```text
rules_manifest_hash: 6fe76d3ca2d2f582a40ee9c7d1acf7e222a5f8b51661d3730d878e56b4fa2f6f
```

The manifest covers semantic calculation descriptors, nutrient rules, groups, traits, source mapping, NOVA, and all active/reserved versions. CI fails when current governed content differs from the released lock.

## 5. Calculation Engine v2

### Energy and Safety

- Uses decimal-safe Mifflin and existing activity factors.
- Supports cut intensities 15%, 20%, and 25%, with 20% default.
- Applies requested deficit, then the 750 kcal cap, then half-even final-calorie rounding.
- Applies safety to the final rounded target for every goal.
- Returns `normal`, `specialist_review_required`, or `very_low_energy_blocked` with `can_activate`.

### Protein

- Uses unrounded Backend BMI for the `<30` versus `>=30` branch.
- Uses actual weight below 30 and the approved reference-plus-33%-excess adjusted weight at or above 30.
- Does not round intermediate values; final protein is one decimal, half-even.
- Returns the complete nested `protein_calculation` provenance and approved Arabic explanation.

### Fat and Carbohydrate

- Uses the authoritative final calorie target and existing sex/custom fat percentage.
- Allocates carbohydrate from final calories minus raw protein and fat calories.
- Classifies warnings from final one-decimal carbohydrate grams.
- Returns calm `CARBOHYDRATE_BELOW_GENERAL_REFERENCE` for `100-<130g` and stronger `CARBOHYDRATE_VERY_LOW` below `100g`.
- Rejects non-positive raw calories or final rounded grams with `422 NON_POSITIVE_CARBOHYDRATE_ALLOCATION` on `macro_allocation`.
- Successful responses always retain deprecated `carb_clamped=false`; no successful true state exists.

### Nutrient Targets

The Backend resolves all 16 PD-009 targets using final calories, captured sex, and calculation-date age. Known target values use Registry display precision, while calculation remains decimal-safe.

## 6. API and Frontend

- Added authenticated `GET /nutrition/registry`.
- Added deterministic `ETag`, `If-None-Match` `304`, and `Cache-Control: private, max-age=300, must-revalidate`.
- Expanded Profile Preview additively with deficit, cap, safety, protein provenance, warnings, versions, and all resolved nutrients.
- Preserved existing `target_calories`, macro fields, and `carb_clamped` compatibility.
- Added exact domain-error envelope for non-positive carbohydrate Preview results.
- Replaced the independent Frontend nutrient target registry with Backend response mapping.
- Food Details obtains labels/order/coverage participation from the runtime Registry and exposes explicit loading, retry, and unavailable states without fallback rules.
- TypeScript contains contract types and Arabic presentation-unit localization only; it contains no target values or formulas.

## 7. Files Changed

Backend:

- `backend/app/nutrition_rules/`
- `backend/app/api/routes/nutrition.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/profile.py`
- `backend/app/schemas.py`
- `backend/app/services/calc.py`
- `backend/app/services/nutrients.py`
- `backend/app/services/profile.py`
- `backend/pyproject.toml`

Frontend:

- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/lib/nutrients.ts`
- `frontend/components/DiaryPage.tsx`
- `frontend/components/FoodDetailsPage.tsx`
- `frontend/e2e/nutrition-quality.spec.ts`

Tests and evidence:

- `backend/tests/test_calc.py`
- `backend/tests/test_nutrition_quality.py`
- `backend/tests/test_rules_registry_api.py`
- `docs/implementation/wave1/01_PRINCIPAL_OWNERSHIP_IMPLEMENTATION_REPORT.md`
- `docs/implementation/wave1/02_RULES_REGISTRY_CALCULATIONS_IMPLEMENTATION_REPORT.md`
- `docs/implementation/wave1/WAVE1_IMPLEMENTATION_REGISTER.md`

## 8. Validation Results

| Gate | Result | Evidence |
|---|---|---|
| Ruff | Passed | All checks passed |
| Backend full suite | Passed | 86 passed, 1 expected Future Scope skip |
| Artifact 18 Stage 02 golden scenarios | Passed | `W1-GC-001` through `W1-GC-015`, 100% |
| Decimal/BMI boundary tests | Passed | Below, exactly, and above BMI 30 |
| Safety boundary tests | Passed | 1201, 1200, 800, 799 and half-even edges |
| Carb boundary/error tests | Passed | 130, 100, positive-near-zero, zero, negative |
| Registry versions/metadata | Passed | 16 nutrients, 7 target types, source/NOVA/group metadata |
| Manifest determinism/lock | Passed | Exact SHA and version bundle |
| Registry auth/cache | Passed | Principal auth, ETag, 304, Cache-Control |
| Alembic model drift | Passed | No new upgrade operations; head remains `0006` |
| Frontend typecheck | Passed | Exit 0 |
| Frontend production build | Passed | 8 routes generated |
| Frontend production audit | Passed | 0 vulnerabilities |
| Full Playwright regression | Passed | 245 passed, 0 failed, 0 skipped |
| `git diff --check` | Passed | No whitespace errors |

The first complete E2E run passed 241 and failed four. One was a non-deterministic retained fixture; three exposed Arabic unit localization, duplicate Food-detail presentation, and an obsolete six-nutrient expectation. The UI boundary and frozen test expectation were corrected, a deterministic local fixture was supplied, focused suites passed, and the final complete run passed 245/245. Generated screenshots and runtime results were restored/excluded.

## 9. Independent Strict Review

### Product and Architecture

- Calculation order, boundaries, warnings, target values, versions, and Arabic meanings match frozen H01-H03/H05/H10.
- No Profile preference persistence or Target Plan lifecycle was pulled forward from Stage 04.
- No Food schema or migration was added before Stage 03.
- Analysis remains inactive and no deferred nutrient became governed.

### Security and Compatibility

- Registry requires typed authenticated Principal context.
- Registry contains public rule metadata only and no owner data, credentials, or Python source.
- Profile Preview remains non-persisting and does not accept authoritative outputs or versions.
- Existing top-level targets and Frontend flows remain compatible.

### Findings

| Severity | Finding | Disposition |
|---|---|---|
| Critical | None | N/A |
| High | None | N/A |
| Medium | Initial manifest omitted semantic calculation descriptors | Added complete calculation policy to canonical manifest and lock |
| Medium | Static Frontend nutrient targets remained authoritative | Removed; runtime Backend metadata now drives governed nutrient definitions |
| Medium | Initial E2E exposed unit/duplicate/obsolete expectation issues | Corrected; final 245/245 passed |
| Low | Existing Starlette TestClient deprecation warning | Retained as dependency-maintenance risk |

## 10. Migration, Legacy, and Rollback

- No model or migration change occurs in this stage.
- Existing Profile rows remain legacy/unversioned; no current version is backfilled.
- Existing Food and Snapshot data is not reinterpreted or rewritten.
- Rollback removes only additive API/Frontend capability and must not label historical records with v2 versions.
- Stage 03 and Stage 04 own physical persistence and writer enablement.

## 11. Traceability and Residual Risk

Covered: H01, H02, H03, H05, H10; ADR-004, ADR-007; PD-005, PD-006, PD-007, PD-009; API Registry/Profile Preview; Golden `W1-GC-001` through `W1-GC-015`; applicable Artifact 20 gates.

Residual non-blocking work is deliberately assigned to later stages:

- Stage 03: exact Food persistence and complete Food UI contracts.
- Stage 04: Profile cut-preference persistence, activation safety rejection, and immutable Target Plan version storage.
- Stage 05: Snapshot v2 version storage.
- Stage 06: Backend-authoritative Diary aggregation.
- Stage 07/08: complete Registry incompatible-state UX and release evidence.

## 12. Stage Verdict

```text
Golden scenarios passed: 100%
Registry manifest/version checks: Passed
Frontend formula duplication introduced: No
Critical findings: 0
High findings: 0
Frozen-contract deviations: 0
Later-wave features introduced: 0
Stage verdict: Ready to Merge
```

The Stage 02 commit, PR, CI result, reviewed head, and merge SHA remain Pending until their lifecycle steps complete.
