# Foods Serving-First Redesign Report

## 1. Summary

The Foods list and Food Details experience now uses the default unit as the primary daily-use nutrition view while preserving per-100g/per-100ml values as the database source of truth. The redesign keeps the Arabic-first RTL layout and existing teal myNutri identity, adds no food imagery, and introduces no archive, offline, or sync behavior.

The list is compact and serving-first on mobile and desktop. Details lead with the default serving, then expose a complete nutrition view that can switch between the serving and the stored per-100 basis.

## 2. Files Changed

### Backend

- `backend/app/api/routes/foods.py`
- `backend/app/schemas.py`
- `backend/app/services/food.py`
- `backend/tests/test_foods.py`

### Frontend

- `frontend/app/globals.css`
- `frontend/components/AppNav.tsx`
- `frontend/components/FoodDeleteDialog.tsx`
- `frontend/components/FoodDetailsPage.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/lib/api.ts`
- `frontend/lib/food.ts`
- `frontend/lib/types.ts`

### Playwright

- `frontend/e2e/foods/serving-first.spec.ts`
- Existing Foods specs were aligned with the new list actions, states, and responsive structure.

No Food database columns or migrations were added for derived serving nutrition.

## 3. Serving Calculation Implementation

`frontend/lib/food.ts` is the shared calculation and formatting boundary.

```text
serving value = stored per-100 value * unit_amount / 100
```

- Calories display as the nearest whole number.
- Protein, carbs, and fat display with at most one decimal and no unnecessary trailing zero.
- Detailed nutrients display with at most two decimals.
- Optional `null` values remain unavailable and are not converted to zero.
- Explicit zero values remain visible.
- Invalid or unavailable calculations produce an unavailable display rather than a fabricated value.

## 4. Foods List Redesign

- The list page no longer presents per-100 nutrition as its primary values.
- Mobile uses compact cards with a two-line food name, secondary brand/category text, default-serving badge, and a four-column nutrient row.
- The full card opens Food Details.
- A three-dot menu contains Edit and Delete without triggering the card link.
- Permanent deletion still uses the existing confirmation dialog.
- Loading skeletons, empty catalog, no-results, retryable API error, loading-more, and end-of-results states are present.
- No archive/inactive controls or offline/sync status appears.

At 390px, the first viewport exposes approximately three to four useful cards without horizontal overflow.

## 5. Food Details Redesign

- The full food name, brand, category, default serving, Edit, and Delete are shown in the header.
- Default-serving calories and macros are the first prominent data section.
- A segmented mode switches the complete nutrient view between the default serving and the stored per-100g/per-100ml basis.
- Nutrients are grouped into core values, sugars and fats, minerals, and vitamins.
- Unavailable optional values are omitted; explicit zero values remain visible.
- Metadata uses readable rows for basis, unit definition, notes, source, and timestamps.
- Historical source data remains unchanged; no derived serving nutrition is persisted.

## 6. Search, Filter, and Sort Changes

- Name search supports Arabic, English, and mixed-language content.
- Search includes a clear control and resets pagination.
- Categories come from the existing free-text `category` field.
- Blank categories are represented as `غير مصنف`.
- Mobile uses horizontally scrollable category chips; desktop uses a compact select.
- Sorting supports name, recently added, serving calories, and serving protein.
- Search, category, and sorting can be combined.

## 7. Pagination Implementation

The Foods list API accepts the backward-compatible query parameters:

- `search`
- `category`
- `sort`
- `page`
- `page_size`

Paged requests return items, total count, page metadata, available categories, and uncategorized count. Existing consumers that call the legacy list endpoint without pagination parameters still receive the existing array response, preserving Diary Food selection behavior.

- Desktop uses numbered Previous/Page/Next pagination.
- Mobile loads 20 items initially and appends the next page through `عرض المزيد`.
- Search, category, and sort changes reset to page 1.

## 8. Mobile Behavior

- Compact cards replace the dense table below the responsive breakpoint.
- Category chips remain on one horizontally scrollable line.
- Food names are clamped to two lines in cards and shown fully in Details.
- Mixed Arabic/English content uses bidi-safe direction handling.
- Nutrient values remain in a compact four-column row at 390px.
- The verified mobile screenshots have no horizontal page overflow.

## 9. Desktop Behavior

- Desktop uses a dense table with Food, Category, Default serving, serving Calories, Protein, Carbs, Fat, and Actions.
- Brand appears as secondary text in the Food column.
- Optional nutrients are intentionally excluded from the list and remain available in Details.
- The layout remains readable at 1440px without oversized rows or action-button clusters.

## 10. Accessibility Changes

- Interactive targets use a minimum 44px size.
- Focus-visible styling is applied consistently.
- Cards, food names, filters, sorting, pagination, and load-more controls have accessible interaction semantics.
- Three-dot buttons have Arabic accessible names.
- The action menu supports keyboard focus, Escape, and outside dismissal.
- The delete dialog traps focus, supports Escape, initializes focus safely, and restores focus when closed.
- Color is not the only method used to communicate actions or nutrient meaning.

## 11. Tests Added or Updated

Backend tests cover:

- Legacy list compatibility and paginated response metadata.
- Combined search and category filtering, including uncategorized foods.
- Sorting by derived serving calories and protein.

Playwright coverage includes:

- Serving values and required rounding on mobile cards.
- Serving and per-100 modes in Details.
- Optional nutrient null-versus-zero behavior.
- Combined search and category filtering.
- Serving-calorie sorting.
- Desktop pagination and mobile Load More.
- Card navigation and three-dot Edit/Delete actions.
- RTL, mixed-language names, responsive overflow, existing CRUD, snapshot safety, and online-only behavior.

## 12. Test Results

- Backend full suite: **31 passed, 1 skipped**.
- Backend Ruff: **passed**.
- Frontend TypeScript check: **passed**.
- Frontend production build: **passed**.
- Foods Playwright coverage: **165 passed across all 13 Foods spec files**.
- Browser screenshots: no page errors and no horizontal overflow at the verified mobile and desktop viewports.

One combined Playwright invocation exceeded the command time budget before producing a final summary. The complete set was then run in bounded spec groups; every Foods test passed in those final runs.

## 13. Screenshot Locations

- `docs/ui-ux/screenshots/foods-serving-first/foods-list-mobile-390.png`
- `docs/ui-ux/screenshots/foods-serving-first/food-details-mobile-390.png`
- `docs/ui-ux/screenshots/foods-serving-first/foods-list-desktop-1440.png`
- `docs/ui-ux/screenshots/foods-serving-first/food-details-desktop-1440.png`

## 14. Remaining Risks

1. Category remains free text. Spelling, whitespace, or case variants can appear as separate filter values until category normalization is defined.
2. Database collation can affect the exact ordering of mixed Arabic and Latin names.
3. The conditional legacy/paged list response is intentional for compatibility; new API consumers must request pagination and use the paged envelope.
4. Physical iPhone Safari and Android Chrome checks remain recommended for touch menus, browser safe areas, and mixed-language rendering.
5. Add/Edit page restructuring was outside this request. Only shared visual consistency, focus, and touch-target behavior changed there.

The redesign is ready for focused manual visual QA and device verification. No production data, archive fields, offline queues, or sync behavior were introduced.
