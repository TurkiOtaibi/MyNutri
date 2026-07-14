# Diary Add Food Sheet Redesign Report

## Summary

The Diary Add Food interaction was redesigned as a focused two-state bottom sheet: search/select first, then configure and save. Nutrition calculations, serving quantity limits, meal assignment, frozen snapshots, Gregorian/Western-number formatting, and online-only writes remain unchanged.

## Files Changed

- `frontend/components/DiaryPage.tsx`
- `frontend/app/globals.css`
- `frontend/lib/api.ts`
- `frontend/e2e/diary/add-food-sheet.spec.ts`
- `frontend/e2e/diary/add-food-sheet-visual.spec.ts`
- `frontend/e2e/diary/diary.spec.ts`
- `frontend/e2e/diary/diary-visual.spec.ts`
- `frontend/e2e/diary/meal-sections.spec.ts`
- `frontend/e2e/diary/meal-sections-visual.spec.ts`
- `frontend/e2e/diary/quantity-refinement.spec.ts`
- `frontend/e2e/foods/list-search-states.spec.ts`
- `backend/app/services/food.py`
- `backend/tests/test_foods.py`
- `docs/ui-ux/screenshots/diary-add-food-sheet/*.png`

## Main UI and UX Changes

- Added a near-full-height mobile sheet with fixed header, internally scrolling content, and safe-area-aware fixed footer.
- Separated search and configuration into two exclusive states.
- Added a 275 ms debounced Food search with clear/focus behavior, compact result rows, skeletons, no-results copy, and Retry state.
- Added recent Foods derived from existing Diary history without new persistence or schema fields.
- Added a compact selected-Food summary and a `تغيير الطعام` return path that restores the query and preserves the selected meal.
- Reworked meal selection into one equal-width segmented control.
- Preserved decimal quantity entry and the 0.01-50 range in a compact circular-control stepper.
- Added a calm live nutrition preview with prominent calories and immediate macro recalculation.
- Added dynamic save labels, duplicate-submit prevention, saving/success feedback, and state-preserving API failure recovery.
- Added clean-dismiss behavior and an unsaved-change confirmation after meaningful edits.
- Added swipe-down dismissal from the drag handle while keeping the results area independently scrollable.
- Added reduced-motion behavior, accessible labels, actual-only live regions, focus restoration, and responsive checks at 320, 360, 390, and 430 px.

## Technical Decisions

- Recent Foods are computed by joining existing Diary history Food IDs with currently available Foods. Deleted Foods are intentionally omitted because no current catalog record is available.
- Search now matches Food name or brand through the existing Foods endpoint. This is a backward-compatible behavior extension; no request or response shape changed.
- No database migration or new API endpoint was introduced.
- Screenshots use a production build and reduced-motion media preference to prevent transient animation/compositor frames from contaminating visual evidence.

## Verification Results

- Focused Add Food Playwright coverage: **10 passed**.
- Diary functional Playwright suite (visual specs excluded): **42 passed**.
- Diary production visual specs: **3 passed**; focused Add Food visual capture: **1 passed**.
- Full Foods Playwright regression: **165 passed**.
- Backend pytest: **37 passed, 1 skipped**. The skipped sync test remains Future Scope.
- Frontend TypeScript: **passed** (`tsc --noEmit`).
- Frontend production build: **passed** (`next build`).
- Ruff: **passed**.
- `git diff --check`: **passed**; line-ending conversion warnings only.

## Commands Run

```text
npx playwright test e2e/diary/add-food-sheet.spec.ts --project=foods-chromium
npx playwright test e2e/diary --project=foods-chromium --grep-invert "@visual"
npx playwright test e2e/diary --project=foods-chromium --grep "@visual"
npx playwright test e2e/diary/add-food-sheet-visual.spec.ts --project=foods-chromium
npx playwright test e2e/foods --project=foods-chromium
npm run typecheck
npm run build
python -m pytest
python -m ruff check .
git diff --check
```

## Screenshot Paths

Production screenshots are under `docs/ui-ux/screenshots/diary-add-food-sheet/`:

1. `01-search-recent-390.png`
2. `02-active-search-keyboard-390.png`
3. `03-no-results-390.png`
4. `04-selected-no-meal-390.png`
5. `05-breakfast-selected-390.png`
6. `06-decimal-quantity-2.5-390.png`
7. `07-saving-state-390.png`
8. `08-save-error-390.png`
9. `09-unsaved-confirmation-390.png`
10. `10-viewport-320.png`
11. `11-viewport-390.png`
12. `12-viewport-430.png`

## Remaining Limitations

- Physical iPhone Safari and Android Chrome keyboard, home-indicator, and swipe-down behavior still require device QA.
- Recent Foods can only include Foods that still exist in the current catalog.
- Search result loading skeletons are intentionally shown only for perceptible initial requests; cached/refined queries do not flash a spinner.

No BA or approved QA CSV files were modified. No commit or push was created.
