# Diary Gregorian Meal Sections Report

## 1. Executive Summary

The Diary now uses a single compact Gregorian week navigator, Western numerals, four collapsible meal sections, meal-aware Add Food actions, and quantity-and-meal editing. Existing serving calculations, target calculations, frozen snapshots, Sunday-start weeks, future-date blocking, Food hard-delete safety, authentication, and online-only behavior remain unchanged.

## 2. Files Changed

### Backend

- `backend/alembic/versions/0003_diary_meal_type.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/api/routes/diary.py`
- `backend/app/services/diary.py`
- `backend/app/services/diary_validation_errors.py`
- `backend/tests/test_diary_snapshot.py`

### Frontend

- `frontend/components/DiaryPage.tsx`
- `frontend/app/globals.css`
- `frontend/lib/api.ts`
- `frontend/lib/dates.ts`
- `frontend/lib/types.ts`
- `frontend/next.config.mjs`
- `frontend/e2e/foods/helpers.ts`
- `frontend/e2e/foods/list-search-states.spec.ts`
- `frontend/e2e/foods/details-edit.spec.ts`
- `frontend/e2e/diary/diary.spec.ts`
- `frontend/e2e/diary/diary-visual.spec.ts`
- `frontend/e2e/diary/quantity-refinement.spec.ts`
- `frontend/e2e/diary/meal-sections.spec.ts`
- `frontend/e2e/diary/meal-sections-visual.spec.ts`

### Documentation and Evidence

- `docs/ui-ux/DIARY_GREGORIAN_MEAL_SECTIONS_REPORT.md`
- `docs/ui-ux/screenshots/diary-meal-sections/*.png` (17 screenshots)

## 3. Database Migration

Migration `0003_diary_meal_type` adds the PostgreSQL enum `meal_type_enum` and a non-null `diary_entry.meal_type` column. Existing rows receive `unspecified`; the server default is removed after backfill.

Local PostgreSQL rehearsal against `mynutri_dev`:

- Downgrade target: `0002_foods_v1_per_basis`
- Upgrade target: `0003_diary_meal_type (head)`
- Entry count before/after: `1 / 1`
- Snapshot aggregate MD5 before/after: `a9a484deff119c9f05dbb1e4fe079535` / identical
- Existing non-`unspecified` rows after rehearsal: `0`

## 4. Meal-Type API Contract

Supported values are `breakfast`, `lunch`, `dinner`, `snack`, and backward-compatible `unspecified`. Create requests may omit the field and default to `unspecified`. The current UI always submits one of the four standard values. Update requests may change only quantity and meal type; omitted meal type preserves the current value for older clients. Invalid values return structured HTTP 422 details with field `meal_type`, code `invalid_meal_type`, and Arabic message `اختر قسم وجبة صحيحًا.`

## 5. Gregorian and Western Numeral Formatting

Diary dates use a deterministic ISO-to-Gregorian formatter with fixed Arabic weekday/month labels and Western digits. This avoids Node/Safari ICU and bidi-character differences that can otherwise cause hydration mismatches. Quantities, calories, macros, and percentages use Western digits and `.` decimals. Numeric expressions use bidi isolation in the RTL page.

## 6. Compact Week Strip

The separate date navigator and large weekly cards were replaced by one compact surface containing the full selected date, Gregorian date input, Today action, previous/next week controls, and seven compact Sunday-first day tabs. Future days and future-week navigation remain disabled. Selected state uses border, background, typography, progress, `aria-selected`, and `aria-current`.

## 7. Daily Summary Redesign

One summary card presents consumed calories first, target second, remaining calories beneath, one calorie progress bar, and compact protein/carbohydrate/fat rows. Progress bars clamp visually while numeric over-target values remain available.

## 8. Meal Accordion Behavior

The Diary always renders compact Breakfast, Lunch, Dinner, and Snack headers with item counts, calorie subtotals, icons, Add actions, and `aria-expanded`. Empty sections are collapsed and compact. The first populated standard section opens initially. Multiple sections may remain open. A fifth `غير مصنف` section appears only when legacy entries exist.

## 9. Entry-Row Design

Entries retain compact name, brand, serving quantity, equivalent weight, calories, macros, and a three-dot action menu. No Food images were added. Mixed Arabic/English names use automatic text direction and retain the existing two-line list clamp.

## 10. Add Food Section Flow

Each meal header opens the existing Add Food sheet with that meal preselected. Global Add requires an explicit meal selection. The searchable Food picker, serving details, Arabic/English search, errors, Retry behavior, and online-only submission remain intact.

## 11. Quantity and Preview Behavior

The existing 0.01-50 serving stepper and deterministic serving calculation remain unchanged. Plus/minus, decimal input, equivalent weight, and live calorie/protein/carbohydrate/fat preview continue to use the existing shared calculation path.

## 12. Edit and Move Behavior

Edit now permits quantity and meal type only. Food, entry date, and frozen snapshot fields are not exposed or mutable. Moving an entry refreshes meal subtotals, daily totals, and weekly totals after successful API response.

## 13. Success and Error Messages

Success status is rendered only after query invalidation completes and auto-dismisses after 3.8 seconds. API failures keep the dialog and entered values. Empty alert containers were not introduced. The existing Arabic online-only failure message remains unchanged.

## 14. Accessibility Changes

- Meal headers are buttons with `aria-expanded`.
- Week days use tab semantics and `aria-selected`.
- Meal selector uses a radiogroup with explicit checked state.
- Icon-only section Add controls have contextual Arabic names.
- Existing modal focus trap, Escape handling, focus restoration, field error associations, live previews, and 44px controls remain in use.

## 15. Responsive Verification

Automated viewport checks cover 360, 390, 430, 768, 1024, and 1440px. The compact seven-day grid does not create page overflow. Mobile meal headers remain single-row and the sheet retains safe-area-aware sticky actions. Desktop retains the entries-first two-column composition with the summary side column.

## 16. Tests Added or Updated

- Backend coverage for default meal type, invalid meal type, structured Arabic errors, quantity-and-meal updates, and snapshot immutability.
- Playwright coverage for Gregorian/Western formatting, seven-day accessibility, four meal sections, legacy conditional display, section preselection, global selection requirement, API compatibility, and moving entries.
- Visual fixture coverage for all required mobile and desktop states.
- Foods Diary-picker regression updated to the current searchable picker.
- Food Details alert assertion scoped to application content so Next.js development tooling is not treated as a product alert.

## 17. Exact Test Results

- Full Diary Playwright: **34 passed** in 2.2 minutes, including an explicit server/client hydration-mismatch check.
- Full Foods Playwright: **165 passed** in 6.8 minutes.
- Backend pytest: **36 passed, 1 skipped**, with one existing Starlette/httpx deprecation warning.
- Frontend TypeScript: **passed**.
- Frontend production build: **passed**.
- Ruff: **passed**.
- `git diff --check`: **passed** for current unstaged implementation changes.
- Migration downgrade/upgrade rehearsal: **passed** on local PostgreSQL `mynutri_dev`.

The previously staged repository documentation still has inherited trailing whitespace detected by `git diff --cached --check`; this predates this implementation and no commit was created.

## 18. Screenshot Paths

All 17 screenshots are under `docs/ui-ux/screenshots/diary-meal-sections/`:

- Mobile: empty, populated, Breakfast expanded, multiple expanded, Breakfast Add, global Add, quantity stepper, edit, legacy unspecified, success toast, and long mixed-language name.
- Desktop: empty, populated, two-column layout, Add dialog, edit dialog, and expanded meal sections.

## 19. Remaining Risks

- Physical-device QA remains pending for iPhone Safari and Android Chrome, especially date-input behavior, virtual keyboard/sheet interaction, safe areas, VoiceOver/TalkBack, and compact seven-cell readability.
- Existing staged documentation whitespace must be cleaned before any future checkpoint commit can pass `git diff --cached --check`.

## 20. Explicitly Deferred Features

- Gram-mode Diary logging
- Meal times
- Meal-specific nutrition targets
- Food images or uploads
- Drag-and-drop between meal sections
- Offline writes, sync queues, and cached personal data as source of truth
