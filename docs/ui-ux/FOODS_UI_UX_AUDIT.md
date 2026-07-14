# Foods UI/UX Audit

Date: 2026-07-10
Scope: `/foods`, `/foods/new`, `/foods/:id`, `/foods/:id/edit`
Method: live application review at 1440px, 768px, 430px, 390px, and 360px widths; code inspection; keyboard interaction check of the delete dialog. The catalog contained 14 foods during the review.

## 1. Overall UX Verdict

**Verdict: Usable, but not yet polished enough for low-friction daily use.**

The Foods experience has the correct product structure: a dedicated list, standalone create/edit pages, mobile cards, a collapsed optional-nutrient section, permanent-delete confirmation, Arabic RTL, and online-only error handling. The primary workflows are available and understandable.

The current implementation still has important interaction defects. The sticky form action bar can cover form controls, the delete dialog does not contain keyboard focus, read failures have no recovery action, and the details page gives equal space to useful values and absent optional values. The visual system is consistent but overly sparse on desktop and overly tall on mobile.

**UX score: 6/10**

## 2. Critical Issues

No Critical issue was found. The main create, read, edit, and delete routes are usable, and no observed defect makes the primary Foods workflow impossible.

## 3. High-Priority Issues

| ID | Issue | Evidence | Impact | Recommendation |
|---|---|---|---|---|
| UX-F01 | The sticky Save/Cancel/Delete bar covers form content. | `.form-actions-sticky` is fixed to the viewport bottom without reserved document space ([globals.css](../../frontend/app/globals.css)); live checks at 768px and 1440px showed it intersecting the carb and fat controls. Mobile screenshots also show it floating over section content. | Users can lose visual context, miss labels/errors, or struggle when the software keyboard is open. | Reserve space equal to the action bar, keep it inside the form flow on wide screens, and use a safe-area-aware bottom dock only on small screens. Never allow it to overlap the focused field or its error. |
| UX-F02 | The delete dialog is not keyboard-modal and initially focuses the destructive action. | Focus is sent to Confirm in [FoodDeleteDialog.tsx](../../frontend/components/FoodDeleteDialog.tsx), but there is no focus trap. Pressing Tab moved focus out of the dialog and into the page behind it. | Keyboard and assistive-technology users can operate obscured content; default focus increases accidental-delete risk. | Focus Cancel initially, trap Tab/Shift+Tab inside the dialog, make the rest of the page inert, retain Escape behavior, and restore focus to the invoking control. |
| UX-F03 | Loading and read-failure states are weak and sometimes misleading. | The list always renders `foods.length`, so loading/failure can show `0 عنصر`; loading is plain text, and list/detail/edit errors provide no Retry action ([FoodsPage.tsx](../../frontend/components/FoodsPage.tsx), [FoodDetailsPage.tsx](../../frontend/components/FoodDetailsPage.tsx), [FoodFormPage.tsx](../../frontend/components/FoodFormPage.tsx)). | A connection failure looks like an empty catalog and forces manual navigation or reload. This was visible in the supplied phone screenshot. | Show the count only after success, distinguish loading/error/empty/no-results visually, provide Retry, preserve the search query, and use a compact skeleton to prevent layout shift. |
| UX-F04 | Default-unit and nutrition-basis concepts are not sufficiently explained at the point of input. | The form separates one basis select into a full panel, then asks for `الوحدة الافتراضية`, `مقدار الوحدة`, and `أساس الوحدة` without an equation or example tied to current selections ([FoodFormPage.tsx](../../frontend/components/FoodFormPage.tsx)). | Users can enter `100` as a serving count or confuse source nutrition with the logging unit, creating believable but incorrect data. | Use a two-option segmented control for `لكل 100 جم` / `لكل 100 مل`; show a live sentence such as `1 شريحة = 30 جم`; add one short helper line stating that nutrition remains per 100g/100ml. |
| UX-F05 | Food details are dominated by missing optional values. | All 18 optional nutrients render even when absent, each as `-` ([FoodDetailsPage.tsx](../../frontend/components/FoodDetailsPage.tsx)). On mobile this creates a very long section with little information. | Scanning is slow, relevant nutrients are buried, and the page feels unfinished. | Show only provided optional nutrients. If none exist, show one concise empty message. Group populated values by fats, carbohydrates, minerals, and vitamins. |
| UX-F06 | Validation recovery is incomplete. | Field errors are associated with inputs, but submit does not focus or scroll to the first invalid field. The general error appears above a long form, while the relevant field can be several screens away ([FoodFormPage.tsx](../../frontend/components/FoodFormPage.tsx)). | On mobile, users may see that validation failed without knowing where to recover. Optional-section errors can be especially distant. | On failed submit, open the relevant collapsed section, focus the first invalid field, scroll it above the action dock, and announce a concise error summary with the error count. |
| UX-F07 | Core keyboard/touch navigation does not meet a robust mobile baseline. | Buttons and icon controls use 40px minimums; no global `:focus-visible` treatment exists; nested Foods routes do not keep the Foods nav item active because active matching is exact; no `aria-current` is set ([globals.css](../../frontend/app/globals.css), [AppNav.tsx](../../frontend/components/AppNav.tsx)). | Touch accuracy is reduced, keyboard position is hard to see, and users lose route context on Add/Details/Edit. | Use at least 44px touch targets, add visible focus styles, mark `/foods/**` as active, and expose `aria-current="page"` on the active navigation item. |

High-priority issue count: **7**

## 4. Medium and Low Issues

### Medium

1. **Desktop table density is poorly balanced.** Ten columns fit only because labels, values, and default-unit text wrap. At tablet widths the 900px minimum table requires horizontal scrolling. Switch to cards or a reduced-column responsive table before 900px, not only below 640px.
2. **Destructive actions dominate the list.** A red delete button repeats in every row/card. Keep View/Edit visible and move Delete into a compact overflow menu, or visually mute Delete until intent is expressed.
3. **Mobile food cards are unnecessarily tall.** The global mobile rule turns the four macro values into one column. Preserve a stable 2x2 macro grid and align numeric values consistently.
4. **Search lacks recovery and efficiency controls.** There is no clear button, no explicit retry after failure, and no action in the no-results state to clear the query. Requests are initiated for every keystroke.
5. **Optional nutrients are not subdivided.** Opening the section exposes 18 fields in one uninterrupted grid. Use small semantic groups: fats/sugars, minerals, vitamins.
6. **Mixed-direction units are visually inconsistent.** Visible labels and values mix Arabic with `g`, `mg`, and `mcg` without explicit direction isolation. Use Arabic display units (`جم`, `ملجم`, `مكجم`) or wrap numeric-unit tokens in `bdi dir="ltr"`.
7. **The list table lacks semantic support.** It has no caption and header cells do not declare `scope="col"`. This weakens screen-reader navigation.
8. **Status feedback has weak semantics.** Delete errors on list/details can be announced as `status` rather than `alert`, and success/error notes share the same neutral visual style.
9. **Edit initialization remains sensitive to query refetches.** The effect copies every new query result into form state ([FoodFormPage.tsx](../../frontend/components/FoodFormPage.tsx)). A background refetch can overwrite unsaved edits. Initialize once or guard against replacing a dirty form.

### Low

1. Brand, category, notes, source, and nutrients show repeated `-` placeholders instead of suppressing irrelevant rows.
2. Text fields have maximum lengths but no character counters near the limit.
3. The generic system font is readable but does not provide a deliberate Arabic typographic hierarchy; weights look heavier than necessary in dense details.
4. The Add CTA and page title sit at opposite desktop edges, weakening their relationship. Keep the CTA within the heading action area but closer to the title block.

## 5. Route-by-Route Findings

### `/foods`

**What works**

- Add Food is a clear standalone-page CTA.
- Search is labeled and uses an accessible name.
- Desktop table and mobile cards are intentionally different.
- Long names clamp to two lines in list/card contexts.
- View, Edit, and Delete icon controls have accessible names.
- Empty and no-results states are distinct.

**Issues**

- The count reports zero before a successful response.
- Loading/error states have no Retry control; no-results has no Clear Search action.
- Search, count, and results occupy a large framed panel with excess whitespace on desktop.
- The table is crowded and becomes horizontally scrollable on tablet.
- Food names are not the primary detail link; users must target a small Eye icon.
- Repeated red Delete controls create visual noise and accidental-action anxiety.
- Mobile macro values stack vertically instead of forming a compact scan pattern.
- No sorting is available. For the current personal catalog this is not a blocker; add only a simple name/recent sort if catalog growth proves a need.
- Category/brand filters should not be added until those fields are populated consistently and the user has a demonstrated retrieval problem.

### `/foods/new`

**What works**

- The route is standalone and the form is divided into meaningful sections.
- Required core fields are marked.
- Optional nutrients are collapsed by default.
- Save is protected against duplicate submission and shows a saving label.
- API and field errors preserve entered values.

**Issues**

- The sticky action bar obscures controls and competes with the mobile keyboard.
- A single nutrition-basis select consumes an entire panel but still does not explain the decision well.
- Default-unit fields are technically correct but conceptually ambiguous without a live equation.
- Optional metadata fields are not explicitly labeled optional.
- Numeric fields have no visible ranges or concise helper text for unusual units.
- Long-form validation does not take the user to the first error.
- Back and Cancel are both present but their distinction is not meaningful; use one consistent secondary exit in the main action area while preserving browser Back.
- The form has no dirty-state protection. Do not add draft persistence by default, but consider a lightweight leave confirmation only after confirming it is needed for accidental navigation.

### `/foods/:id`

**What works**

- Full food name is visible.
- Core nutrition is separated from metadata and optional nutrition.
- Edit and Delete actions are prominent and deletion remains confirmed.
- Notes and source preserve Arabic/English content and wrap without horizontal overflow.

**Issues**

- The first metadata panel is visually large and sparse on desktop.
- Five core metrics use a two-column grid, leaving an imbalanced final tile.
- Calories do not receive stronger hierarchy than secondary macros.
- Every missing optional nutrient is rendered, producing a very long mobile page.
- Brand/category/source rows with no value add noise.
- The page does not show a concise nutrition summary for the default unit; the user must mentally convert from per-100 values.
- Loading replaces the full page with one text block, and failure has no Retry action.

### `/foods/:id/edit`

**What works**

- It reuses the Add structure, reducing learning cost.
- Existing data loads into the correct sections.
- Delete is absent from Add and available in Edit.
- Full food names remain editable and readable.

**Issues**

- All Add-form issues remain, plus three competing actions in the sticky bar.
- Delete sits close to Save/Cancel; separation should be stronger because it is not part of the normal edit completion path.
- Query refetch can theoretically replace dirty form state.
- Loading/error states remove route context and have no Retry.

## 6. Mobile-Specific Findings

1. No horizontal page overflow was detected at 360px, 390px, or 430px.
2. The mobile cards are readable, but their one-column macro layout makes the list excessively long.
3. The two-row sticky header consumes substantial vertical space on long forms. A compact mobile app bar or bottom primary navigation would improve usable height, but any change must remain consistent across the whole app shell.
4. The sticky form actions cover content and do not account for keyboard occlusion beyond a basic safe-area bottom offset.
5. The 40px buttons fall below the practical 44px touch-target baseline.
6. Mobile details become very long because absent micronutrients remain visible.
7. The active Foods navigation state disappears on nested Foods routes.
8. Safe-area handling is incomplete at the top of the sticky app header and around the bottom action surface.
9. Mixed Arabic/English names wrap acceptably, but Latin brand fragments should use direction isolation to prevent punctuation and hyphens from moving unpredictably.
10. At 768px, the desktop table still appears and requires horizontal scrolling; use the card layout or a reduced table at tablet width.

## 7. Accessibility Findings

### High

- Delete dialog focus escapes to the page behind it.
- Destructive Confirm receives initial focus instead of Cancel.
- Links/buttons/summary controls lack a consistent visible `:focus-visible` state.
- Touch targets are 40px rather than at least 44px.
- Validation does not focus the first invalid field.

### Medium

- Active navigation lacks `aria-current` and fails for nested routes.
- Table headers lack explicit column scope and the table lacks a caption.
- Loading messages do not consistently use `role="status"` and `aria-live`.
- Delete/network errors are not consistently announced as alerts.
- The dialog should make background content inert while open.
- The native optional-section summary is keyboard-operable, but its focus treatment is not visible.

### Positive evidence

- Root document uses `lang="ar"` and `dir="rtl"`.
- Form controls have labels.
- Field errors use `aria-invalid` and `aria-describedby`.
- Icon-only list actions have accessible names.
- The dialog has `role="dialog"`, `aria-modal`, title, description, Escape handling, and focus restoration intent.

## 8. Quick Wins

1. Hide the food count until the query succeeds.
2. Add Retry to list/detail/edit read errors and Clear Search to no-results.
3. Make food names clickable links to details.
4. Keep mobile macros in a 2x2 grid.
5. Hide optional detail rows with null values.
6. Add `:focus-visible` styles and increase controls to 44px.
7. Mark nested `/foods/**` routes active and add `aria-current`.
8. Focus Cancel first and trap focus in the delete dialog.
9. Add bottom padding equal to the sticky action bar and keyboard-safe scrolling.
10. Isolate mixed-direction numeric units and Latin brand text with `bdi`.

## 9. Structural Improvements

1. **Rebuild the form action pattern:** in-flow actions on desktop; a reserved, safe-area-aware bottom dock on mobile; Delete separated from normal completion actions.
2. **Clarify nutrition input:** compact basis segmented control, live default-unit equation, and concise helper text directly below relevant controls.
3. **Progressively disclose optional nutrition:** one collapsed parent section with internal subgroups for sugars/fats, minerals, and vitamins.
4. **Make details summary-first:** identity/default unit, prominent calories/macros, only populated optional values, then notes/source and timestamps.
5. **Make browsing retrieval-first:** linked names, compact cards, a clearable search, recoverable states, and a simpler tablet layout.
6. **Create consistent state components:** Loading, Empty, No Results, Read Error, Save Error, and Success should have distinct semantics, visuals, actions, and announcements.

## 10. Recommended Redesign Direction

Use a **quiet, task-focused nutrition catalog** rather than a dashboard or decorative card system.

- Keep the first viewport focused on finding or adding a food.
- Use restrained surfaces and fewer framed blocks; reserve cards for individual mobile foods and genuine form sections.
- Make calories and the four core macros the dominant nutrition layer.
- Keep optional nutrition available but visually secondary.
- Explain data concepts at the exact control where mistakes occur.
- Prefer compact repeated patterns, stable alignment, and clear actions over extra visual decoration.
- Preserve the existing teal identity, but use neutral and danger colors more deliberately to distinguish state and risk.

## 11. Phased Implementation Plan

### Phase 1 - Interaction Safety and Accessibility

- Fix sticky-action overlap and keyboard/safe-area behavior.
- Implement a proper focus-trapped delete dialog with Cancel focused first.
- Add global focus-visible styles and 44px touch targets.
- Focus/scroll to the first invalid field.
- Correct nested Foods nav state and `aria-current`.
- Add retryable, correctly announced read/error states and hide premature counts.

**Definition of done:** no action bar covers a control/error at 360, 390, 430, 768, or desktop widths; dialog keyboard focus cannot escape; keyboard focus is always visible; failed reads are recoverable without reloading the browser.

### Phase 2 - Form Comprehension and Efficiency

- Convert nutrition basis to a compact segmented choice.
- Add a live default-unit equation and field-level helper text.
- Mark optional fields consistently.
- Subgroup optional nutrients and add character/range guidance only where useful.
- Prevent edit refetch from replacing a dirty form.

**Definition of done:** a first-time user can explain the difference between nutrition basis and default unit before saving, and validation recovery requires no manual search through the page.

### Phase 3 - Browsing and Details Information Architecture

- Make names the primary detail links.
- Compact mobile cards to a 2x2 macro layout.
- Use cards/reduced columns at tablet width.
- Reduce persistent destructive-action emphasis.
- Hide absent optional detail values and rebalance metric grids.
- Add Clear Search and concise empty/no-results actions.

**Definition of done:** common foods can be found, inspected, edited, or deleted with fewer targets and less scrolling; details show only meaningful information.

### Phase 4 - Visual Polish and Verification

- Refine Arabic typography, spacing, mixed-direction text, and state colors.
- Add table semantics, live-region verification, and visual regression coverage.
- Verify iPhone Safari and Android Chrome with software keyboards and safe areas.
- Re-run desktop, tablet, mobile, keyboard-only, and screen-reader smoke checks.

## 12. What Should Not Be Changed

- Do not merge Add Food back into `/foods`; the standalone route is correct.
- Do not change the per-100g/per-100ml source of truth.
- Do not expose serving-based nutrition as source data.
- Do not expand optional nutrients by default.
- Do not reintroduce archive/inactive states or offline/sync behavior.
- Do not weaken permanent-delete confirmation or diary snapshot safety.
- Do not replace mobile cards with a dense table.
- Do not add enterprise-grade filtering, bulk actions, permissions, approval flows, or category management for v1.
- Do not add draft persistence as a substitute for stable form behavior.
- Do not redesign Diary/Profile or the full navigation system within a Foods-only change; coordinate only the shared shell adjustments required for Foods usability.

## 13. Final Recommendation

The Foods experience can support current personal use, but implementation should not begin with visual restyling. Start with **Phase 1: Interaction Safety and Accessibility**. It addresses the only issues that can directly cause obscured input, unsafe destructive interaction, inaccessible recovery, or loss of route context.

After Phase 1, improve the form's nutrition/default-unit comprehension before optimizing list density and details presentation. Sorting and filtering should remain deferred until catalog growth demonstrates that search alone is insufficient.
