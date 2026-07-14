# myNutri Profile & Targets Redesign Report

## Executive Summary

The `/profile` route was redesigned as a compact Arabic-first settings experience. Editable profile data, server-calculated current targets, and unsaved target preview are visually and semantically separated. Diary, Foods, Add Food, global navigation, calculation formulas, persistence, authentication, and online-only behavior were not changed.

## Files Changed

- `frontend/components/ProfilePage.tsx`
- `frontend/app/globals.css`
- `frontend/e2e/profile/profile.spec.ts`
- `frontend/e2e/profile/profile-visual.spec.ts`
- `docs/ui-ux/screenshots/profile-targets-redesign/*`
- `docs/ui-ux/PROFILE_TARGETS_REDESIGN_REPORT.md`

## Component And Route Structure

- Route remains `/profile` and continues rendering `ProfilePage`.
- The page now contains a semantic header, body-data settings card, activity card, goal card, advanced accordion, current-target card, expected-target preview, save action bar, and reusable Profile bottom sheets.
- Selection sheets cover sex, activity, goal, calculation explanation, defaults confirmation, and unsaved-navigation confirmation.
- No global header or tab component was changed.

## UI And UX Improvements

- Header copy is now `بياناتك وأهدافك` and `حدّث بياناتك لنحسب احتياجك اليومي.` Technical server/formula wording was removed from the primary header.
- `بيانات الجسم` is one settings card containing exactly sex, Gregorian birth date, height, and weight.
- Birth date uses Arabic month names, Gregorian calendar, and Western numerals while preserving ISO storage.
- Height and weight use decimal-friendly text inputs with fixed `سم` and `كجم` suffixes and no native number spinners.
- Sex, activity, and goal use accessible bottom-sheet radio choices instead of visible native selects.
- Activity and goal retain their existing internal enum values and server factors.
- Advanced options are closed by default and use a clean accordion without dashed borders.
- `protein_per_kg` is displayed in `جم/كجم`.
- `fat_pct` is shown as a human percentage. The UI converts `25` to API ratio `0.25` and converts the confirmed response back to `25`.
- Restore defaults uses the existing schema defaults, `1.8` and `0.25`, and changes draft state only until save.
- One unified target card replaces four large metric tiles. Calories are primary; protein, carbs, and fat share one compact row.
- The calculation explanation contains Mifflin-St Jeor in user-facing context only.
- Initial loading uses local card skeletons; read failure does not expose fabricated editable values.

## API Behavior

### Before

- `GET /profile` loaded the saved profile and calculated targets.
- `PUT /profile` saved a profile and returned confirmed calculated targets.
- `POST /profile/preview` already accepted `ProfileUpsert`, reused `calculate_targets`, and performed no database write.

### After

- The same three contracts are used unchanged.
- No endpoint, request field, response field, enum, schema, or migration was added.
- Preview requests are debounced by 400ms, are skipped while the draft is invalid, and stale responses are ignored by a sequence guard.
- The server response remains authoritative after save.

## Calculation Source Of Truth

- No Mifflin-St Jeor, activity-factor, goal-factor, macro, or rounding formula was added to TypeScript.
- Current and preview targets come only from the backend calculation service.
- Calculation-engine tests remain green.

## Validation

- Client validation reflects the currently implemented API schema: positive height and weight, protein `1.6-2.2`, and fat ratio `0.20-0.30` displayed as `20-30%`.
- Birth date must be a valid non-future Gregorian date.
- Errors are field-level, use Arabic copy, set `aria-invalid`, and are connected with `aria-describedby`.
- Save is not requested while known client errors exist; focus moves to the first invalid field.
- Backend Pydantic field locations map to the corresponding visible Arabic field errors.

## Dirty State And Saving

- Draft values are normalized numerically before comparison with the last confirmed server state.
- Formatting-only changes do not create dirty state, and reverting values clears it.
- Opening sheets, opening the accordion, and focusing inputs do not make the page dirty.
- The safe-area-aware save bar appears only while dirty, preserves input on failure, prevents duplicate requests, and disappears only after a confirmed server response.
- Save success updates the React Query profile cache, current targets, saved baseline, and draft without a page reload.

## Navigation Protection

- Same-origin in-app link clicks are captured only while dirty and show `تجاهل التغييرات؟`.
- `متابعة التعديل` preserves draft state; `تجاهل التغييرات` performs the requested navigation.
- Standard `beforeunload` protection covers refresh/close behavior supported by the browser.
- No custom history implementation was added.

## Accessibility And Responsive Verification

- Verified at 320, 360, 390, and 430px without horizontal document overflow.
- Primary interactive rows and options retain at least 44px targets.
- Bottom sheets provide dialog naming, focus trap, Escape support, selected radio state, and focus restoration.
- Errors are associated with fields; blank Profile alert regions are not rendered.
- Reduced-motion mode disables sheet, accordion, save-bar, preview, and skeleton motion.
- Current target values are read-only and contain no input or progressbar controls.

## Tests And Results

- `npx playwright test e2e/profile --project=foods-chromium --reporter=line`: **13 passed**.
- `npx playwright test e2e/diary --project=foods-chromium --reporter=line`: **61 passed**.
- `npx playwright test e2e/foods --project=foods-chromium --reporter=line`: **165 passed**.
- `python -m pytest -q`: **37 passed, 1 skipped**, with one third-party deprecation warning.
- `python -m pytest tests/test_calc.py -q`: **3 passed**.
- `python -m ruff check .`: **passed**.
- `npm run typecheck`: **passed**.
- `npm run build`: **passed**; all 8 routes generated successfully.
- `git diff --check`: **passed**; line-ending conversion warnings only.
- No frontend lint script exists in `package.json`; TypeScript and production build were used as the frontend static gates.

## Screenshots

Directory: `docs/ui-ux/screenshots/profile-targets-redesign/`

- `01-profile-loaded-390.png`
- `02-body-data-card-390.png`
- `03-sex-sheet-390.png`
- `04-activity-sheet-390.png`
- `05-goal-sheet-390.png`
- `06-advanced-closed-390.png`
- `07-advanced-open-390.png`
- `08-dirty-save-bar-390.png`
- `09-validation-error-390.png`
- `10-saving-state-390.png`
- `11-save-failure-retry-390.png`
- `12-successful-saved-state-390.png`
- `13-unified-current-targets-390.png`
- `14-expected-target-preview-390.png`
- `15-calculation-explanation-390.png`
- `16-initial-loading-390.png`
- `17-initial-load-error-390.png`
- `18-viewport-320.png`
- `19-viewport-390.png`
- `20-viewport-430.png`
- `21-keyboard-sized-viewport-390.png`
- `22-unsaved-navigation-confirmation-390.png`

## Confirmations And Limitations

- No migration was added.
- No API contract was changed.
- No client-side target calculation engine was added.
- Diary, Add Food, and Foods regression suites remain green.
- No offline storage, synchronization, multi-profile behavior, or new dependencies were introduced.
- Real iPhone Safari and Android Chrome testing remains pending.
- Real keyboard, dynamic browser bars, safe areas, touch scrolling, and bottom-sheet dragging were not claimed as physically verified.
- No commit, merge, push, tag, or release was created.
