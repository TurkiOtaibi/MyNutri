# Traceability Matrix

This matrix maps major v1 requirements to user stories, acceptance criteria, field/validation rules, code areas affected, and recommended test types.

Current Food traceability note:
- D-024 and D-025 supersede older Food rows that mention archive/inactive state, `is_active`, `archived_at`, Active/Archived filters, or `serving_grams` as Food source-of-truth.
- Legacy rows are retained for historical evidence, but the current rows below control Food v1 implementation planning.

| Requirement / feature | Story IDs | Acceptance criteria section | Field/validation rule | Code area affected | Recommended test type | Current alignment |
|---|---|---|---|---|---|---|
| Standalone Food pages | `US-FOOD-NAV-001`, `US-FOOD-CRUD-001`, `US-FOOD-CRUD-002`, `US-FOOD-HAPPY-003` | Current Food Page Acceptance Criteria - Food Routes and Page Structure | Routes `/foods`, `/foods/new`, `/foods/:id`, `/foods/:id/edit`; no large inline Add Food form | Frontend routing, Food page/components | E2E, component, mobile visual | Missing/needs route alignment |
| Current Food list/table/cards | `US-FOOD-HAPPY-001` | Current Food Page Acceptance Criteria - Food List | Current catalog only; desktop columns; mobile cards; no status/archive filters | `FoodsPage.tsx`, API list response | E2E, visual/mobile | Needs D-024/D-025 alignment |
| Food per-100g/per-100ml model | `US-FOOD-CRUD-001`, `US-FOOD-CRUD-002` | Current Food Page Acceptance Criteria - Food Create and Edit | `nutrition_basis`, core nutrients per 100g/per 100ml | Food model/schema/API/form | API, component, E2E | Missing |
| Default unit model | `US-FOOD-CRUD-001`, `US-FOOD-CRUD-002` | Current Food Page Acceptance Criteria - Food Create and Edit | `default_unit_type`, `unit_amount`, `unit_basis` | Food model/schema/API/form, Diary logging calculations | API, component, unit | Missing |
| Optional nutrients collapsed section | `US-FOOD-CRUD-001`, `US-A11Y-001` | Current Food Page Acceptance Criteria - Food Create and Edit | Optional nutrients are optional; invalid provided values fail; collapsed section opens for first invalid field | Food form/components | Component, a11y, E2E | Partial/missing micronutrient fields |
| Optional nutrient validation ranges | `US-FOOD-VALIDATION-004`, `US-FOOD-VALIDATION-002`, `US-A11Y-001` | Current Food Page Acceptance Criteria - Food Create and Edit | D-026 ranges and cross-field rules: optional blank allowed; `sugar_g` = total sugar; `added_sugar_g` = added sugar; entered values numeric `>= 0`; max per nutrient; `fiber_g <= carb_g`; `added_sugar_g <= sugar_g` only when both are provided; saturated/trans fat rules | Food schema/API validation, Food form/components, error mapping | API, unit, component, E2E, a11y | Missing in current code |
| Permanent Food delete | `US-FOOD-CRUD-003` | Current Food Page Acceptance Criteria - Food Permanent Delete | Confirmation shows Food name and permanent-delete copy; hard delete after API success | Food service/API, Food detail/edit UI dialog | API, E2E, a11y | Backend hard delete exists; confirmation/copy missing |
| No Food archive state | `US-FOOD-CRUD-003`, `US-FOOD-HAPPY-001` | Current Food Page Acceptance Criteria - Food Permanent Delete and Food List | No `is_active`, no `archived_at`, no Archived status, no Active/Archived filters | Food model/schema/UI/API docs | Requirements review, E2E visual | Earlier BA/code plan superseded |
| Duplicate current Food blocking | `US-FOOD-VALIDATION-003` | Current Food Page Acceptance Criteria - Food Create and Edit | Normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`; deleted Foods ignored | Food service/model validation | API, unit, component, E2E | Missing |
| Diary snapshot after Food delete | `US-FOOD-CRUD-003`, `US-DIARY-INTEGRITY-001` | Current Food Page Acceptance Criteria - Diary Snapshot After Food Delete | Snapshot stores Food name, nutrition basis, nutrition values, logged quantity, log mode, calculated totals | Diary service/model/snapshot display | Unit, API, E2E regression | Current snapshot may depend on Food references/serving data |
| Arabic RTL app shell | `US-APP-HAPPY-001` | App Shell, RTL, and Mobile | N/A | `frontend/app/layout.tsx`, `AppNav.tsx`, `globals.css` | E2E, visual RTL | Mostly aligned |
| Health endpoint | `US-INFRA-READ-001` | Health and Configuration | Health response | `backend/app/api/routes/health.py` | API smoke | Aligned |
| Environment config and safe API access | `US-CONFIG-SEC-001` | Health and Configuration | API URL/token config; no committed secrets | `backend/app/core/config.py`, `frontend/lib/api.ts`, `.env.example` | Config review, API auth | Mostly aligned |
| Single-user token auth and 401 UI | `US-AUTH-PERM-001`, `US-ERROR-MAPPING-001` | Auth, Online Network and API Errors | 401 mapping | `backend/app/core/auth.py`, API client, page error UI | API, E2E | API aligned; UI needs alignment |
| Optional installable shell | `US-SHELL-HAPPY-001`, `US-SHELL-SCOPE-001` | Optional Installable Shell and Service Worker | Static shell only | `manifest.json`, `InstallPrompt.tsx`, `service-worker.js` | E2E, PWA/manual | SW needs alignment |
| Offline page/metadata and cached-read fallback scope | `US-SHELL-SCOPE-001`, `US-FUTURE-OFFLINE-001`, `US-NETWORK-READ-001` | Optional Installable Shell and Service Worker, Future Scope | Cached personal data is not source of truth | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx`, `frontend/lib/db.ts`, `service-worker.js` | Requirements review, E2E network failure | Implementation alignment item only |
| Online-only writes | `US-NETWORK-WRITE-001`, `US-UX-STATUS-001`, Profile/Food/Diary CRUD stories | Online Network and API Errors, Duplicate Submit and Retry | No local save or queue; one pending request | `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts` | E2E, component, integration | Current code contradicts |
| Online-only reads with exact failure copy | `US-NETWORK-READ-001`, `US-NETWORK-READ-COPY-001` | Online Network and API Errors, Diary Day and Weekly Summary Reads, Food Catalog Read and Search, Profile | Page-specific read messages from D-022 | API client, page queries, service worker, cached read paths | E2E, integration, component | Needs alignment |
| Single-profile v1 scope | `US-PROFILE-SCOPE-001` | Profile | One personal Profile model; multi-profile Future Scope | Profile model/routes/pages | Requirements review, E2E scope check | Aligned with current model |
| Missing Profile state | `US-PROFILE-STATE-001` | Profile | Missing profile copy | `ProfilePage.tsx`, `profile.py` | Component, E2E | Needs UI verification |
| Profile edit-only lifecycle | `US-PROFILE-SCOPE-001`, `US-PROFILE-HAPPY-001` | Profile | Profile reset/delete out of v1 | `ProfilePage.tsx`, `profile.py` | Requirements review, E2E profile update | Aligned if no reset/delete UI added |
| Profile save | `US-PROFILE-HAPPY-001` | Profile | Profile fields | `profile.py`, `ProfilePage.tsx` | API, E2E | Save exists; fallback conflicts |
| Profile validation | `US-PROFILE-VALIDATION-001` | Profile | Age 10-100; height/weight/protein/fat ranges | `schemas.py`, `ProfilePage.tsx` | API, component | Needs alignment |
| Target calculation | `US-TARGET-HAPPY-001` | Target Calculation | Valid profile input | `calc.py`, `ProfilePage.tsx` | Unit, API, component | Calc aligned; validation needs alignment |
| Current Food list | `US-FOOD-HAPPY-001` | Food Catalog Read and Search | Current catalog only; no archive/inactive state | `FoodsPage.tsx`, `foods.py`, model/schema | API, E2E | Basic list exists; D-025 fields/routes need alignment |
| Food search | `US-FOOD-HAPPY-002`, `US-FOOD-STATE-001` | Food Catalog Read and Search | Current catalog only | `food.py`, `FoodsPage.tsx` | API, E2E | Basic search exists; states need alignment |
| Food loading/empty/no-results/error states | `US-FOOD-STATE-001`, `US-NETWORK-READ-COPY-001` | Food Catalog Read and Search | Exact state copy | `FoodsPage.tsx`, API client | Component, E2E | Needs alignment |
| Food create | `US-FOOD-CRUD-001` | Food Create and Edit | Food field dictionary | `foods.py`, `schemas.py`, `FoodsPage.tsx` | API, component, E2E | Create exists; validation gaps |
| Default-unit field naming | `US-FOOD-CRUD-001`, `US-DIARY-GRAM-001` | Food Create and Edit, Diary Create by Grams | UI labels `Default unit`, `Unit amount`, `Unit basis`; API fields `default_unit_type`, `unit_amount`, `unit_basis` | Food form, schema, API payloads | Component, API contract | Missing/needs D-025 alignment |
| Food edit | `US-FOOD-CRUD-002` | Food Create and Edit | Duplicate and field rules | `foods.py`, `food.py`, `FoodsPage.tsx` | API, component, E2E | Edit exists; validation/error gaps |
| Food stale-record handling | `US-FOOD-EDGE-001`, `US-FOOD-CRUD-002`, `US-FOOD-CRUD-003` | Food Permanent Delete and Stale Food Handling | Stale Food messages | Food service/API, Food edit/delete UI, Diary create flow | API, E2E | Needs alignment |
| Food field validation | `US-FOOD-VALIDATION-001` | Food Field Validation | v1 food ranges | `schemas.py`, frontend form | API, component | Needs alignment |
| Negative net carbs | `US-FOOD-VALIDATION-002` | Food Field Validation | `fiber_g <= carb_g` | `schemas.py`, `food.py` | API, unit, component | Missing |
| Duplicate current-catalog food blocking | `US-FOOD-VALIDATION-003` | Food Create and Edit | normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis` | food service/model/index or validation | API, component | Missing |
| Food permanent hard delete | `US-FOOD-CRUD-003` | Food Permanent Delete and Stale Food Handling | Confirmation, permanent catalog deletion, snapshot history intact; no `is_active`/`archived_at` | Food service/API/UI | API, E2E, a11y | Current hard delete exists; confirmation/copy/snapshot verification need alignment |
| Food details | `US-FOOD-HAPPY-003`, `US-NETWORK-READ-COPY-001` | Food Catalog Read and Search | Optional nutrient display; detail read failure | `FoodsPage.tsx` | Component, E2E | Mostly aligned; read error needs alignment |
| Diary day read | `US-DIARY-HAPPY-001`, `US-NETWORK-READ-COPY-001` | Diary Day and Weekly Summary Reads | `entry_date`; day read failure copy | `DiaryPage.tsx`, `diary.py` | API, E2E | Basic aligned; read error needs alignment |
| Diary serving create | `US-DIARY-CRUD-001`, `US-DIARY-GRAM-CONTRACT-001` | Diary Create by Servings | `{ entry_date, food_id, log_mode: "servings", quantity }`; quantity 0.01-50 | `DiaryPage.tsx`, `diary.py`, schema | API, E2E | Needs range/date/log_mode alignment |
| Diary gram create | `US-DIARY-GRAM-001`, `US-DIARY-GRAM-CONTRACT-001` | Diary Create by Grams and Quantity Mode Contract | `{ entry_date, food_id, log_mode: "grams", quantity }`; grams 1-5000; Food nutrition basis/default-unit data must support an unambiguous gram calculation | Diary UI/API/service/snapshot | API, unit, E2E | Missing |
| Diary quantity mode storage contract | `US-DIARY-GRAM-CONTRACT-001` | Diary Create by Grams and Quantity Mode Contract | `log_mode`, mode-specific `quantity`, `serving_multiplier`, `nutrition_snapshot.calculated_totals` | `schemas.py`, `models.py`, `services/diary.py`, routes | API contract, unit, integration | Missing |
| Diary validation | `US-DIARY-VALIDATION-001` | Diary Date, Edit, Delete, and Snapshot | date and quantity rules | schema, Diary UI | API, component | Needs alignment |
| Diary quantity edit | `US-DIARY-EDIT-001`, `US-DIARY-GRAM-CONTRACT-001` | Diary Date, Edit, Delete, and Snapshot | payload `{ quantity }`; immutable mode/food/date/per-serving snapshot | `PUT /diary/{id}`, Diary UI/service | API, E2E | Backend broad; UI missing |
| Diary snapshot integrity | `US-DIARY-INTEGRITY-001`, `US-DIARY-GRAM-CONTRACT-001` | Diary Create by Grams and Quantity Mode Contract, Diary Date/Edit/Delete/Snapshot | snapshot immutable; aggregation uses `calculated_totals` | `services/diary.py`, tests | Unit, API | Serving snapshot aligned; gram extension needed |
| Diary delete confirmation and online-only delete | `US-DIARY-CRUD-002`, `US-UX-STATUS-001` | Diary Date, Edit, Delete, and Snapshot | confirmation shows food name/date; no local queue | `DiaryPage.tsx`, `diary.py` | E2E, API, a11y | Delete exists; confirmation/fallback needs alignment |
| Weekly summary | `US-DIARY-HAPPY-002`, `US-NETWORK-READ-COPY-001` | Diary Day and Weekly Summary Reads | Sunday-Saturday; weekly read failure copy | `aggregation.py`, `DiaryPage.tsx` | API, E2E | Basic aligned; error tests missing |
| Shared API error mapping | `US-ERROR-MAPPING-001` | Online Network and API Errors | 401/404/422/network/5xx | API client and page error UI | Component, E2E | Needs alignment |
| Arabic validation messages | Validation stories, `US-A11Y-001` | All validation sections | Exact Arabic copy | all forms | Component, E2E, a11y | Needs alignment |
| Duplicate submit and retry | `US-UX-STATUS-001` | Duplicate Submit and Retry | one pending request; retry current visible input | Profile/Food/Diary forms and dialogs | Component, E2E | Needs alignment |
| Mobile/browser support and long food names | `US-MOBILE-001` | App Shell, RTL, and Mobile | viewport matrix; two-line food-list truncation; full name in detail/edit | CSS/components | Visual regression, manual device | Needs verification |
| Accessibility | `US-A11Y-001` | Accessibility | field errors, dialog focus, accessible names, live regions | UI components/forms/dialog | a11y, E2E | Needs alignment |
| QA test data matrix | `US-QA-001` | QA Test Data | Boundary/stale/duplicate/network data | backend/frontend tests | Test design review | BA added; tests missing |
| Tests | `US-QA-001` | All sections | v1 requirement coverage | backend/frontend tests | Unit/API/E2E/a11y/visual | Partial |
| Future offline/sync | `US-FUTURE-OFFLINE-001` | Future Scope: Offline and Sync | excluded from v1 | `db.ts`, `sync.py`, `SyncStatus.tsx`, offline page, service worker | Future-scope tests only | Active code remains |

## Test Type Guidance

| Test type | Use for |
|---|---|
| Unit | Calc formulas, snapshot math, net carbs, normalization helpers. |
| API/integration | Auth, health, Profile/Food/Diary CRUD, validation, Food permanent delete, duplicate, gram calculation, stale items. |
| Component | Form validation, Arabic messages, read/write error states, dialog behavior, duplicate-submit state. |
| E2E | Primary user flows, network failures, no local queue, Food permanent delete, Diary delete, gram logging, retry after failure. |
| Accessibility | Icon buttons, form errors, status announcements, Food permanent-delete and Diary delete dialog focus. |
| Visual/mobile | Required viewport matrix, RTL/mixed text, touch target, keyboard behavior, long food names. |
