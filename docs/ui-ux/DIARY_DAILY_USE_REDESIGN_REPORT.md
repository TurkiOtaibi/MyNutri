# Diary Daily-Use Redesign Report

## 1. Executive Summary

The `/diary` route has been redesigned as a compact Arabic-first daily nutrition workspace. The page now prioritizes date navigation, the Sunday-start week, one combined progress summary, the daily Food log, and a focused Add Food interaction.

The redesign preserves the existing target formulas, weekly aggregation, online-only runtime, authentication, Food integration, and frozen nutrition snapshots. It adds no Food images, meal categories, navigation areas, offline queues, or database columns.

## 2. Files Changed

### Application

- `frontend/components/DiaryPage.tsx`
- `frontend/app/globals.css`
- `frontend/lib/api.ts`
- `frontend/lib/dates.ts`
- `backend/app/schemas.py`
- `backend/app/services/diary.py`

### Tests and Visual Verification

- `backend/tests/test_diary_snapshot.py`
- `frontend/e2e/diary/diary.spec.ts`
- `frontend/e2e/diary/diary-visual.spec.ts`
- `frontend/e2e/foods/helpers.ts`
- `frontend/e2e/foods/snapshot.spec.ts`
- `docs/ui-ux/screenshots/diary-redesign/*`

No migration was created or changed.

## 3. Current Problems Addressed

- Replaced separated week arrows and numeric date input with one compact navigator and readable Arabic date.
- Removed the large standalone Daily Goals section and repeated metric blocks.
- Replaced the permanently visible Add form with a focused modal/sheet.
- Made the daily log the main desktop content and removed large zero-value entry cards.
- Replaced immediate Diary deletion with accessible confirmation.
- Added quantity-only editing without Food, date, or snapshot editing.
- Added distinct loading, empty, weekly error, daily error, Food search no-results, and write-error states.
- Added Retry actions and prevented failed writes from clearing entered data.
- Blocked future Diary dates in the UI and API.

## 4. Mobile Redesign

The mobile order is:

1. Page title
2. Compact date navigator
3. Horizontally scrollable week strip
4. One compact progress summary
5. Daily entries or one empty state
6. Safe-area-aware Add Food action

The progress card uses one calorie summary and three compact macro columns with horizontal progress bars. The week strip scrolls independently with snap behavior and keeps the selected day visible. Verified widths are 360, 390, 430, and 768 pixels with no horizontal page overflow.

## 5. Desktop Redesign

Desktop uses the available width through:

- Title and Add Food action in one header.
- Centered compact date navigation.
- Full seven-day week strip.
- Main two-column workspace.
- Larger daily log column.
- Sticky progress summary side column.

Verified widths are 1024 and 1440 pixels with no horizontal page overflow.

## 6. Date and Week Navigation Changes

- Previous and next now change one day, not an entire week.
- A readable Arabic Gregorian date is displayed.
- The native date picker remains available inside the compact control.
- A Today action appears when another date is selected.
- The next-day action is disabled on today.
- Date input uses today as its maximum.
- Backend create validation rejects future dates with Arabic copy.
- The week still starts on Sunday and is derived from the selected date.
- Future week days are visible for context but disabled.

## 7. Daily Summary Changes

One component now shows:

- Consumed calories.
- Remaining calories or an explicit over-target message.
- Daily calorie target.
- Calorie progress.
- Protein, carbs, and fat consumed/target values.
- Macro percentages and safe over-target progress behavior.

Progress width remains bounded and over-target state includes text, not color alone.

## 8. Daily Entries Redesign

Each compact row shows:

- Frozen Food name from the nutrition snapshot.
- Logged serving quantity and calculated base amount.
- Calculated calories.
- Compact protein, carbs, and fat totals.
- Three-dot actions menu.

The actions menu supports quantity-only edit and delete. It closes with Escape or outside interaction. Mixed Arabic/English names use automatic bidi direction and wrap without creating page overflow.

Quantity edits now recalculate and freeze `logged_quantity` and `calculated_totals` from the existing snapshot. Food identity, entry date, nutrition basis, and snapshot nutrition values remain unchanged.

## 9. Add Entry Flow

- Mobile uses a bottom-aligned accessible sheet.
- Desktop uses a centered accessible dialog.
- Food selection uses API-backed name search rather than a long select.
- Results show Food name, default serving, and calories per default serving.
- Arabic, English, and mixed-language Food names are supported through the existing search API.
- Quantity uses the current working serving contract.
- A deterministic live preview shows calories, protein, carbs, and fat.
- Save is disabled while pending and duplicate submit is ignored.
- A failed request preserves Food selection, search, and quantity.
- No failed write is queued or saved locally.

## 10. Loading, Empty, and Error States

- Day loading uses entry skeleton rows.
- Week loading uses an independent week skeleton.
- Empty day uses one compact message and one Add Food action.
- Day and week errors use distinct approved Arabic copy and Retry actions.
- Food search has loading, no-results, and retryable error states.
- Save and delete failures keep server state unchanged and display Arabic errors.
- Empty states are not rendered while reads are pending or failed.

## 11. Accessibility Changes

- Controls use 44px minimum touch targets.
- Existing global `:focus-visible` styling is preserved.
- Date controls, week days, menu actions, and Add controls have Arabic accessible names.
- Week days are real keyboard-operable buttons.
- Dialogs and sheets use `role="dialog"`, `aria-modal`, labelled headings, focus trap, Escape handling, safe initial focus, and focus restoration.
- Field errors use `aria-invalid` and `aria-describedby`.
- Status and error messages use live-region semantics.
- Delete confirmation starts focus on Cancel.

## 12. Tests Added or Updated

Diary Playwright coverage includes:

- Mobile information order and absence of duplicated goals.
- Previous/next/Today navigation.
- Future-date rejection.
- Sunday-start week and day selection.
- Compact empty state.
- Add sheet/dialog, Food search, serving preview, and save.
- Failed save input preservation.
- Duplicate-submit prevention.
- Quantity-only edit and totals recalculation.
- Delete cancel/confirm and totals refresh.
- Distinct read-error and Retry behavior.
- Long mixed-language names, focus behavior, and Escape.
- Responsive checks at 360, 390, 430, 768, 1024, and 1440 pixels.
- Temporary-fixture screenshot generation and cleanup.

Backend tests cover future-date rejection and recalculation of frozen totals after quantity-only edit.

Foods regressions cover serving-first display, permanent delete, future Diary selection removal, and snapshot survival after Food hard delete.

## 13. Exact Test Results

- Diary Playwright suite: **14 passed**.
- Relevant Foods Playwright regression: **18 passed**.
- Backend full suite: **33 passed, 1 skipped**.
- Targeted backend Diary tests: **3 passed**.
- Frontend TypeScript check: **passed**.
- Frontend production build: **passed**.
- Ruff: **passed**.

The one skipped backend test remains the pre-existing Future Scope sync test. A Starlette/httpx deprecation warning remains unrelated to this work.

## 14. Screenshot Paths

### Mobile 390px

- `docs/ui-ux/screenshots/diary-redesign/diary-mobile-empty-390.png`
- `docs/ui-ux/screenshots/diary-redesign/diary-mobile-populated-390.png`
- `docs/ui-ux/screenshots/diary-redesign/diary-mobile-add-entry-390.png`
- `docs/ui-ux/screenshots/diary-redesign/diary-mobile-long-name-390.png`

### Desktop 1440px

- `docs/ui-ux/screenshots/diary-redesign/diary-desktop-empty-1440.png`
- `docs/ui-ux/screenshots/diary-redesign/diary-desktop-populated-1440.png`
- `docs/ui-ux/screenshots/diary-redesign/diary-desktop-add-entry-1440.png`

All E2E Food and Diary fixtures used for screenshots were removed after capture.

## 15. Remaining Risks

1. Physical iPhone Safari and Android Chrome testing is still recommended for browser chrome, safe-area, and virtual-keyboard behavior.
2. Food search currently shows the first eight matching API results in the sheet; pagination inside the logging sheet is not included.
3. Entry action menus are custom lightweight menus and should receive manual screen-reader verification on VoiceOver and TalkBack.
4. Existing historical snapshots with incomplete legacy unit metadata fall back to their stored serving label.
5. The app-wide top navigation remains outside this Diary-only redesign and consumes noticeable vertical space on small screens.

## 16. Explicitly Deferred Features

- Gram-mode Diary logging and a persisted `log_mode` contract were not added because the current running API/model still supports serving quantity only. This remains a separate implementation-alignment item.
- Direct milliliter logging was not added.
- Meal type, meal time, breakfast/lunch/dinner/snack grouping, Food imagery, analytics/statistics, and new navigation areas were not added.
- No offline-first, IndexedDB, mutation queue, sync state, or stale-cache behavior was introduced.
