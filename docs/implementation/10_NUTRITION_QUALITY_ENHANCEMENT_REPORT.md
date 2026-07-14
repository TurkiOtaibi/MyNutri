# Nutrition Quality Enhancement Report

## Summary

Implemented the focused nutrition-quality enhancement across Profile targets, Food Details, Diary meal summaries, Diary daily nutritional details, and immutable Diary snapshots. The implementation preserves server-side target calculation, Food per-100 source data, serving display, and online-only behavior.

## Files Changed For This Enhancement

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/profile.py`
- `backend/app/services/nutrients.py`
- `backend/tests/test_nutrition_quality.py`
- `frontend/app/globals.css`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/DiaryPage.tsx`
- `frontend/components/FoodDetailsPage.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/nutrients.ts`
- `frontend/e2e/profile/profile.spec.ts`
- `frontend/e2e/diary/diary-final-polish.spec.ts`
- `frontend/e2e/diary/diary-final-polish-visual.spec.ts`
- `frontend/e2e/diary/quantity-refinement.spec.ts`
- `frontend/e2e/nutrition-quality.spec.ts`
- `frontend/e2e/nutrition-quality-visual.spec.ts`

The worktree already contained substantial uncommitted, intertwined work before this task. No unrelated files were intentionally modified for this enhancement.

## Macro Defaults

- New Profile protein default: `1.2 g/kg` for both sexes.
- New Profile fat default: male `0.25`; female `0.30`.
- Existing persisted profiles are not rewritten. Legacy values remain until the user explicitly saves or restores defaults.
- Restore Defaults is sex-aware.
- Changing sex updates fat only when the draft still equals the previous sex default. Custom fat values are preserved.
- The Profile UI continues converting API ratios to percentages.
- Mifflin-St Jeor, activity factors, goal factors, calorie calculations, carbohydrate remainder logic, and server rounding remain unchanged.
- Preview and save continue using the same backend calculation service.

## Additional Nutrient Registry

A centralized registry defines stable keys, Arabic labels, units, precision, order, target type, source, and UI participation.

| Nutrient | Type | Numeric target |
|---|---|---:|
| Fiber | Minimum | 30 g |
| Sodium | Maximum | Unconfigured |
| Saturated fat | Maximum | Unconfigured |
| Added sugar | Maximum | Unconfigured |
| Potassium | Minimum | Unconfigured |
| Cholesterol | Monitor only | None |

Only fiber received a newly approved numeric target. Sodium, saturated fat, added sugar, and potassium still require explicit product decisions before numeric progress can be shown.

## API And Migration

- Additive, backward-compatible change: `TargetResponse.additional_targets` exposes nutrient target metadata.
- No new endpoint was required.
- No migration was added. Existing Food and Diary snapshot structures already contain nullable fields for all six nutrients.
- No database values were backfilled or overwritten.

## Diary

- Macro progress uses an RTL-safe track and fill, truthful ARIA percentages, a minimum visual marker for tiny positive values, 100% clamping, and amber over-target state.
- Populated meal headers show snapshot-derived calories, protein, carbs, and fat.
- Empty meals continue to omit zero totals.
- Daily Summary includes `عرض التفاصيل الغذائية`.
- The nutritional-details sheet shows the six tracked nutrients, configured target behavior, tracking-only states, and per-nutrient coverage.
- Coverage formula: entries with a known snapshot value divided by total entries. Explicit zero is known; null is unknown.
- Incomplete totals are labeled `على الأقل` and accompanied by a data-coverage explanation.
- Overall coverage is the average of the six per-nutrient coverage percentages for a non-empty day.

## Snapshot Compatibility

- Existing snapshots already preserve all supported nutrient values as nullable fields.
- Quantity edits scale known values and retain unknown values as null.
- Meal moves do not recreate snapshots.
- Food edits or deletion do not mutate historical Diary values.
- Legacy entries without a nutrient remain unknown, never zero.

## Food Details

- Added a compact additional-nutrient section for the current serving.
- Explicit zero displays as zero; missing values display `غير متوفر`.
- Fiber can show contribution to the configured daily target; unconfigured nutrients do not show fabricated percentages.
- Added Food Details-only `اكتمال البيانات الغذائية`.
- Formula: available tracked nutrition fields divided by all tracked fields. Current scope is 4 core fields plus 6 registry nutrients.
- Core and additional completeness are displayed separately.
- Explicit zero counts as available. Null/undefined counts as unavailable.
- Expanded details list only missing supported nutrients.
- No provenance migration was added; estimated-value labeling remains limited by currently available source metadata.

## Profile

- Added a compact `أهداف غذائية إضافية` section.
- Fiber shows `30 جم يوميًا` and `حد أدنى`.
- Cholesterol shows `متابعة فقط`.
- Unconfigured targets explicitly state that no default target is configured.

## Verification

- `python -m pytest -q`: **42 passed, 1 skipped**.
- `python -m pytest tests/test_nutrition_quality.py tests/test_calc.py tests/test_diary_snapshot.py -q`: **14 passed**.
- `python -m ruff check .`: **passed**.
- `npm run typecheck`: **passed**.
- `npm run build`: **passed**.
- `npx playwright test --project=foods-chromium`: **245 passed**.
- Focused nutrition-quality Playwright: **3 passed**.
- Visual screenshot specs: **4 passed**.
- `git diff --check`: **passed** (line-ending warnings only).
- Frontend lint: no separate lint script is defined; TypeScript and production build completed successfully.

## Screenshots

Stored under `docs/ui-ux/screenshots/nutrition-quality/`:

1. `01-profile-additional-targets-390.png`
2. `02-profile-macro-defaults-390.png`
3. `03-diary-meal-macros-390.png`
4. `04-diary-nutrition-details-390.png`
5. `05-diary-coverage-notice.png`
6. `06-food-completeness-compact-390.png`
7. `07-food-completeness-expanded-390.png`
8. `08-food-details-nutrients-320.png`

## Remaining Limitations

- Numeric targets for sodium, saturated fat, added sugar, and potassium remain unconfigured pending product decisions.
- Existing provenance fields do not identify estimation at individual nutrient-field level.
- Real iPhone Safari and Android Chrome testing remains pending, including dynamic browser bars, physical safe areas, touch scrolling, and sheet drag behavior.
- No production release, commit, merge, or push was performed.
