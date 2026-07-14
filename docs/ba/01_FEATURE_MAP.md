# Feature Map

Status values:
- Confirmed: directly implemented or documented.
- Required / needs alignment: v1 requirement is now decided, but current code does not fully match.
- Future Scope: intentionally excluded from v1.
- Open Decision: still requires product or engineering decision.

## App Shell, Navigation, RTL, Mobile, and Installable Shell

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-001 | App shell and RTL layout | Render Arabic-first pages with RTL document direction and app navigation. | Confirmed | `frontend/app/layout.tsx`, `Providers.tsx`, `AppNav.tsx` | D-015 |
| F-002 | Home route redirect | Redirect `/` to `/diary`. | Confirmed | `frontend/app/page.tsx` | N/A |
| F-003 | Top navigation | Navigate between Diary, Foods, and Profile. | Confirmed | `frontend/components/AppNav.tsx` | D-015 |
| F-004 | Optional installable shell | Provide standalone installable app shell without offline personal data. | Required / needs alignment | `manifest.json`, `InstallPrompt.tsx` | D-002 |
| F-005 | Service worker shell scope | Cache static shell assets only; do not cache personal nutrition data. Removal is recommended if shell-only behavior is confusing. | Required / current code needs alignment | `frontend/public/service-worker.js` | D-002 |
| F-006 | Mobile responsive support matrix | Support 360, 390, 430, 768, and desktop widths across required browsers. | Required / needs QA verification | `frontend/app/globals.css` | D-015 |

## Auth and Infrastructure

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-007 | Single-user token auth | Require bearer token for protected API routes unless token is empty. | Confirmed | `backend/app/core/auth.py` | D-013 |
| F-008 | Health endpoint | Return API health status and support online-only failure triage. | Confirmed | `backend/app/api/routes/health.py` | N/A |
| F-009 | Environment config | Configure API name, database URL, CORS origins, and token through environment settings without committing real secrets. | Confirmed | `backend/app/core/config.py`, `backend/app/main.py`, `frontend/lib/api.ts`, `.env.example` | D-013 |

## Profile and Targets

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-010 | Read profile | Fetch saved profile, show missing profile state when no profile exists, or show exact read-failure copy when API cannot load fresh data. | Confirmed / needs error UI | `backend/app/api/routes/profile.py`, `frontend/lib/api.ts` | D-013, D-022 |
| F-011 | Upsert profile | Save profile only after successful API response; no local queue; prevent duplicate submits and preserve visible input on failure. | Required / current code needs alignment | `ProfilePage.tsx`, `profile.py` | D-001, D-013, D-023 |
| F-012 | Profile validation bounds | Enforce age 10-100, no future birth date, height 100-250 cm, weight 20-300 kg, protein/kg 1.0-3.0, fat 15%-40%. | Required / current code needs alignment | `backend/app/schemas.py`, `ProfilePage.tsx` | D-009, D-012 |
| F-013 | Live target preview | Preview target calories/macros while editing profile. | Confirmed / needs validation alignment | `backend/app/api/routes/profile.py`, `ProfilePage.tsx` | D-009, D-012 |
| F-014 | Calc engine | Calculate BMR, TDEE, goal calories, macros, and carb clamp flag. | Confirmed | `backend/app/services/calc.py`, `backend/tests/test_calc.py` | D-009 |
| F-015 | Target display | Show target calories and macros on Profile and Diary. | Confirmed | `TargetStrip.tsx`, `ProfilePage.tsx`, `DiaryPage.tsx` | N/A |
| F-016 | Multiple people/profiles | Track multiple people and person-scoped diary. | Future Scope / out of v1 | No `person` table; no `person_id` on diary entries | D-016 |

## Food Catalog

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-017 | Foods list | Browse the current Food catalog on `/foods`; desktop uses columns for name, brand, category, nutrition basis, default unit, calories, protein, carbs, fat, and actions; mobile uses cards. No status column or archive filters. | Required / current code needs alignment | `FoodsPage.tsx`, `foods.py` | D-024, D-025 |
| F-018 | Food search | Search current catalog foods by name through online API and show no-results/read-failure states. Deleted foods are not returned. | Required / current code needs state alignment | `food.py`, `FoodsPage.tsx` | D-013, D-022, D-025 |
| F-019 | Standalone Food create | Add Food on `/foods/new` using grouped sections: basic info, nutrition basis, core nutrition, default unit, collapsed optional nutrients, notes/data source. | Required / current code needs route/form alignment | `foods.py`, `FoodsPage.tsx` | D-024, D-025 |
| F-020 | Food edit | Edit Food on `/foods/:id/edit` using the Add Food structure in edit mode; historical diary snapshots do not change; stale food edits are rejected. | Required / current code needs route, duplicate, stale, and error alignment | `FoodsPage.tsx`, `food.py` | D-006, D-013, D-023, D-024, D-025 |
| F-021 | Food details | View Food details on `/foods/:id`, including full long Food name and optional nutrients; show exact read-failure copy if fresh details cannot load. | Required / current code needs route/read-error alignment | `FoodsPage.tsx` | D-022, D-024, D-025 |
| F-022 | Food permanent delete | Delete Food permanently after confirmation that shows the Food name and permanent-delete warning; deleted foods disappear from list/search/future Diary selection. | Required / current code needs confirmation/snapshot alignment | `food.py`, `FoodsPage.tsx` | D-025, D-013, D-023 |
| F-023 | No Food archive state | Do not use `is_active`, `archived_at`, archived status, status column, or Active/Archived filters in v1. | Required / supersedes earlier BA archive model | BA D-025 | D-003, D-004, D-005, D-025 |
| F-024 | Duplicate food prevention | Block current-catalog duplicates by normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`. Deleted foods do not block duplicate creation. | Required / missing in current code | No duplicate check | D-006, D-025 |
| F-025 | Net carbs and optional nutrient validation | Compute net carbs as carbs minus optional fiber; block `fiber_g > carb_g`; enforce D-026 optional nutrient ranges and cross-field rules. | Required / current code needs alignment | `services/food.py`, `schemas.py` | D-011, D-012, D-025, D-026 |
| F-026 | Default unit metadata | Store how the user usually logs the Food through `default_unit_type`, `unit_amount`, and `unit_basis`; nutrition remains per 100g/per 100ml. | Required / missing in current code | `models.Food`, `FoodsPage.tsx` | D-024, D-025 |
| F-027 | Food state handling | Loading, empty catalog, no-results, exact read-failure copy, validation error, D-026 optional nutrient errors, stale item, duplicate-submit, and server/network error states. | Required / partial | `FoodsPage.tsx`, BA decisions | D-013, D-022, D-023, D-024, D-025, D-026 |

## Diary and Weekly Tracking

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-028 | Diary day view | Show entries for selected date and exact read-failure copy if fresh day data cannot load. | Confirmed / needs read-error alignment | `DiaryPage.tsx`, `diary.py` | D-013, D-022 |
| F-029 | Add diary entry by servings | Log selected food with `{ entry_date, food_id, log_mode: "servings", quantity }`, where quantity is 0.01-50 servings. | Confirmed / needs range/log_mode alignment | `DiaryPage.tsx`, `diary.py` | D-012, D-013, D-021 |
| F-030 | Add diary entry by grams | Log selected food with `{ entry_date, food_id, log_mode: "grams", quantity }`, where quantity is 1-5000 grams; nutrition is calculated from the Food nutrition basis and logged gram amount. | Required / missing in current code | No current Diary grams field/API | D-007, D-012, D-021, D-025 |
| F-031 | Diary quantity edit | Edit only `{ quantity }` for the original mode; food/date/log_mode/per-serving snapshot values are immutable. | Required / current code needs alignment | Backend update supports more; UI lacks edit | D-010, D-021, D-023 |
| F-032 | Delete diary entry | Confirm deletion, then remove a diary entry online only after successful API response; reject stale entry deletes and repeated confirms. | Confirmed / needs confirmation and error alignment | `DiaryPage.tsx`, `diary.py` | D-001, D-013, D-018, D-023 |
| F-033 | Future date block | Block diary entries and edits for future dates. | Required / missing in current code | `DiaryEntryCreate` accepts date | D-008 |
| F-034 | Nutrition snapshot | Freeze Food name, nutrition basis, nutrition values, log mode, logged quantity, and calculated totals at logging time so history remains readable after Food edit or deletion. | Confirmed / needs D-025 snapshot extension | `services/diary.py`, `test_diary_snapshot.py` | D-007, D-021, D-025 |
| F-035 | Weekly summary | Aggregate Sunday-to-Saturday totals and targets from snapshot calculated totals; show exact read-failure copy when fresh summary cannot load. | Confirmed / needs read-error alignment | `aggregation.py`, `DiaryPage.tsx` | D-008, D-013, D-022 |

## Online Data, Errors, Accessibility, and Tests

| ID | Feature | Capability | Status | Evidence | Decisions |
|---|---|---|---|---|---|
| F-036 | Online API reads | Load Profile, Foods, Diary, and Week data from backend API; show exact read-failure copy; do not treat cached personal data as source of truth. | Required / current code needs alignment | `frontend/lib/api.ts`, page queries, `frontend/lib/db.ts`, `service-worker.js` | D-001, D-013, D-022 |
| F-037 | Online API writes | Save Profile, Food, and Diary changes only after successful API response; do not queue failed writes; prevent duplicate submits and support retry. | Required / current code needs alignment | Page mutation handlers | D-001, D-013, D-023 |
| F-038 | API error mapping | Map 401, 404, 422, timeout/network, 5xx, stale item, and duplicate-submit states to clear UI behavior. | Required / current code needs alignment | `api.ts`, BA decisions | D-013, D-022, D-023 |
| F-039 | Arabic validation messages | Use exact Arabic field/form messages. | Required / current code needs alignment | `docs/ba/06_ERROR_MESSAGES.md` | D-011 |
| F-040 | Accessibility basics | Accessible names, field error associations, first invalid field focus, collapsed-section expansion, dialog accessibility, and live status regions. | Required / current code needs alignment | UI components | D-011, D-014, D-015, D-023 |
| F-041 | Mobile/RTL quality | No horizontal scrolling, usable touch targets, keyboard-safe forms, readable mixed Arabic/English text, and two-line food-name truncation in lists/cards. | Required / needs QA verification | `globals.css`, components | D-015, D-020 |
| F-042 | Backend and frontend tests | Test calc, snapshot, CRUD, validation, online errors, read-failure copy, duplicate-submit, stale items, mobile, RTL, and accessibility. | Required / partial | `backend/tests` | D-011, D-013, D-015, D-021, D-022, D-023 |
| F-043 | IndexedDB cache and offline mutation queue | Cache personal nutrition data and queue writes offline. | Future Scope / out of v1 | `frontend/lib/db.ts` | D-001 |
| F-044 | Sync push/pull and pending sync states | Replay queued changes, pull server state, show pending/syncing status, handle conflicts. | Future Scope / out of v1 | `sync.py`, `SyncStatus.tsx` | D-001 |
| F-045 | Offline page/metadata and cached-read fallbacks | Existing offline/cached-read artifacts must not define v1 behavior and must be Future Scope or implementation alignment only. | Future Scope / implementation alignment | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx`, `frontend/lib/db.ts`, `service-worker.js` | D-001, D-002, D-022 |
