# Diary Quantity and UX Refinement Report

## 1. Executive Summary

The existing myNutri Diary redesign was refined for clearer daily progress, denser mobile use, safer Add Food placement, and fast multi-serving logging. The page remains Arabic-first, RTL, online-only, Sunday-start, and serving-based.

The refinement introduces one reusable serving quantity stepper for Add and Edit, live deterministic nutrition preview, clearer calorie and macro wording, stronger Food-result differentiation, and a non-overlapping Add Food action beside the Daily Log heading.

## 2. Root UI/UX Issues Addressed

- Removed the fixed mobile CTA that covered visible Diary content.
- Replaced competing consumed/target/remaining numbers with one readable calorie expression.
- Corrected numeric and unit presentation for RTL macro expressions.
- Made date navigation one cohesive header control.
- Added an explicit mobile week-strip scroll cue and stronger selected state.
- Added brand context and two-line Food names to Diary rows.
- Turned the Add Food sheet into a visible two-step flow.
- Replaced the native number input with a decimal-friendly quantity stepper.
- Reused the same stepper and preview for quantity-only editing.

## 3. Files Changed

### Application

- `frontend/components/DiaryPage.tsx`
- `frontend/app/globals.css`

No backend model, schema, service, formula, migration, or database column changed in this refinement.

### Automated and Visual Verification

- `frontend/e2e/diary/diary.spec.ts`
- `frontend/e2e/diary/quantity-refinement.spec.ts`
- `frontend/e2e/diary/diary-visual.spec.ts`
- `docs/ui-ux/screenshots/diary-quantity-refinement/*`

## 4. Mobile CTA Fix

The fixed bottom CTA was removed because a persistent overlay can cover content at intermediate scroll positions even when end padding is present.

- Populated days show one compact Add Food action beside `سجل اليوم`.
- Empty days show one Add Food action inside the empty state.
- The background Add action is removed while the Add sheet is open.
- No CTA overlays Diary entries, actions, errors, or validation messages.
- Bottom safe-area padding remains for the page and modal footer.

## 5. Daily Summary Redesign

The calorie hierarchy is now:

```text
210 من 1706 سعرة
المتبقي: 1496 سعرة
```

Empty days use the same structure with zero consumed. Over-target days replace remaining copy with a textual exceeded amount. Progress width remains bounded.

## 6. Macro RTL Formatting

Each macro displays:

```text
البروتين
5.8 من 147.6 جم
[progress]
4%
```

Numeric fragments use bidi isolation and explicit LTR number direction inside the RTL expression. The Arabic label and unit retain the correct reading order.

## 7. Weekly Strip Improvements

- Selected day uses border, tinted background, stronger type, `aria-current`, and a bottom marker.
- Selected day automatically scrolls into view.
- Mobile uses horizontal scroll snapping and explicit scroll padding.
- `مرر لرؤية بقية الأسبوع` communicates the intentional horizontal interaction.
- Desktop still shows all seven Sunday-start days.
- The week strip creates no horizontal page overflow.

## 8. Daily Entry Improvements

- Food names are limited to two lines in the list and use `dir="auto"`.
- Brand is shown separately when present.
- Quantity, default unit, equivalent weight, and calories remain the primary entry details.
- Macros use bidi-isolated compact values.
- The three-dot Edit Quantity/Delete menu remains unchanged functionally.
- Rows remain dense and avoid nested metric cards.

## 9. Add Food Sheet Redesign

The sheet now communicates two steps:

1. Select Food.
2. Set quantity.

Search results show Food name, brand/category where available, default serving, and calories per serving. Selected Food uses a border, background, check icon, and `aria-pressed="true"`.

The Save action is not shown before Food selection; the footer instead explains `اختر طعامًا للمتابعة`. Search loading, no-results, API error, and Retry behavior remain available.

## 10. Quantity Stepper Behavior

The reusable stepper provides:

- 44px-plus Minus and Plus controls.
- Arabic accessible names: `تقليل الكمية` and `زيادة الكمية`.
- A prominent editable decimal value and current default-unit label.
- Predictable 0.5 button increments.
- Manual values such as `0.5`, `1.5`, and `2.25`.
- Decimal mobile keyboard through `inputmode="decimal"`.
- Minimum `0.01` and maximum `50` serving validation.
- Disabled Minus at the minimum and disabled Plus at the maximum.
- Rejection of blank, zero, negative, invalid text, NaN-like input, and above-maximum values.
- `type="button"` controls that never submit the form.
- Stable quantity state across search rerenders and API failures.

## 11. Live Nutrition Preview

The preview updates immediately from the existing serving calculation:

```text
serving nutrition × quantity
```

It shows total quantity, equivalent g/ml amount, calories, protein, carbs, and fat. Calories are rounded to a whole number; macros use at most one decimal without unnecessary trailing zeros.

No derived nutrition columns are stored. Successful Diary creation continues to let the backend freeze the Food values, logged quantity, and calculated totals in the nutrition snapshot.

## 12. Edit Quantity Behavior

- Edit opens with the existing quantity.
- The same stepper and preview are reused.
- Preview scales from the frozen entry snapshot totals, not the current Food record.
- Food, date, and nutrition snapshot values are not editable.
- Successful edit refreshes day and week totals.
- Failed edit preserves the entered quantity.

## 13. Accessibility Improvements

- Dialog/sheet role, name, focus trap, Escape behavior, and focus restoration are preserved.
- Focus restoration now targets the newly rendered Add trigger rather than a disconnected fixed-button node.
- Quantity input has an exact accessible label.
- Plus/Minus have distinct Arabic accessible names.
- Invalid quantity uses `aria-invalid` and `aria-describedby`.
- Food selection uses `aria-pressed` and a visible check icon.
- Preview and save status use live-region semantics.
- Week selection remains programmatically exposed.

## 14. Responsive Verification

Automated checks cover:

- 360px
- 390px
- 430px
- 768px
- 1024px
- 1440px

Verified behavior includes no horizontal page overflow, fully visible selected week day, no CTA overlap, scrollable sheet results, safe footer placement, readable mixed-language names, and understandable summary expressions.

## 15. Tests Added or Updated

New/refined Playwright coverage includes:

- Stepper visibility after Food selection.
- Selected result visual and accessible state.
- Plus/Minus behavior and no accidental submit.
- Decimal entry and quantity persistence.
- Zero, negative, invalid text, and above-max rejection.
- Equivalent weight and macro/calorie preview.
- Save enablement and failed-save preservation.
- Inline Add action and absence of content overlap.
- Summary and macro RTL wording.
- Quantity-only edit stepper and frozen-snapshot preview.
- Week selected-day visibility and overflow.
- Twelve refined visual states with temporary fixtures.

## 16. Exact Test Results

- Full Diary Playwright suite: **26 passed**.
- Relevant Foods Playwright regression: **18 passed**.
- Targeted backend Diary tests: **3 passed**.
- Full backend suite: **33 passed, 1 skipped**.
- Frontend TypeScript: **passed**.
- Frontend production build: **passed**.
- Ruff: **passed**.

The skipped backend test remains the existing Future Scope sync test. The existing Starlette/httpx deprecation warning remains unrelated.

## 17. Screenshot Paths

All screenshots are under `docs/ui-ux/screenshots/diary-quantity-refinement/`.

### Mobile 390px

- `diary-mobile-empty-390.png`
- `diary-mobile-populated-390.png`
- `diary-mobile-add-search-390.png`
- `diary-mobile-food-selected-390.png`
- `diary-mobile-quantity-2-390.png`
- `diary-mobile-quantity-1.5-390.png`
- `diary-mobile-long-name-390.png`
- `diary-mobile-edit-quantity-390.png`

### Desktop 1440px

- `diary-desktop-empty-1440.png`
- `diary-desktop-populated-1440.png`
- `diary-desktop-add-stepper-1440.png`
- `diary-desktop-edit-quantity-1440.png`

All temporary E2E Diary and Food fixtures were removed after capture.

## 18. Remaining Risks

1. Physical iPhone Safari and Android Chrome testing remains necessary for real virtual-keyboard and browser-toolbar behavior.
2. VoiceOver and TalkBack should manually verify the custom stepper and Food-result announcements.
3. Food search displays the first eight API matches; pagination within the Add sheet remains outside this refinement.
4. Cancel closes directly without a secondary discard prompt. The form preserves data only while open; a future prompt may be useful if users frequently close populated drafts accidentally.

## 19. Explicitly Deferred Features

- Gram-mode logging and `log_mode` UI.
- Direct milliliter logging mode.
- Meal time and breakfast/lunch/dinner/snack categories.
- Food images.
- Statistics or new navigation areas.
- Offline cache, IndexedDB, queues, sync, and pending-sync UI.
