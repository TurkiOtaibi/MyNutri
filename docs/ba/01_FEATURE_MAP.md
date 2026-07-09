# Feature Map

Status values:

- Confirmed: directly implemented or documented.
- Inferred: likely from multiple code signals.
- Missing: expected or planned but not present.
- Recommended: useful improvement, not confirmed as current behavior.
- Open Question: needs product or engineering decision.

## App Shell, Navigation, RTL, and Optional Installable Shell

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-001 | App shell and RTL layout | Render all pages under Arabic `lang` and RTL `dir`; provide global providers and navigation | Confirmed | `frontend/app/layout.tsx`, `frontend/components/Providers.tsx`, `frontend/components/AppNav.tsx` | High |
| F-002 | Home route redirect | Redirect `/` to `/diary` | Confirmed | `frontend/app/page.tsx` | High |
| F-003 | Top navigation | Navigate between Diary, Foods, and Profile | Confirmed | `frontend/components/AppNav.tsx` | High |
| F-004 | Optional installable shell | Provide standalone app metadata and install prompt without treating offline personal data as a source of truth | Confirmed code / v1 allowed | `frontend/public/manifest.json`, `frontend/components/InstallPrompt.tsx` | High |
| F-005 | Offline-first shell/data behavior | Cache shell/data and support offline navigation as a product feature | Future Scope / out of v1 | `frontend/public/service-worker.js`, `frontend/app/offline/page.tsx`; product decision in `13_PRODUCT_DECISIONS.md` | High |
| F-006 | Responsive layout | Collapse grids for tablet/mobile breakpoints | Confirmed | `frontend/app/globals.css` | High |

## Auth and Infrastructure

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-007 | Single-user token auth | Require bearer token for protected API routes unless token is empty | Confirmed | `backend/app/core/auth.py`, route dependencies | High |
| F-008 | Health endpoint | Return API health status | Confirmed | `backend/app/api/routes/health.py` | High |
| F-009 | CORS and environment config | Configure API name, database URL, origins, and token via env | Confirmed | `backend/app/core/config.py`, `backend/app/main.py` | High |

## Profile and Targets

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-010 | Read profile | Fetch saved profile or return 404 when missing | Confirmed | `backend/app/api/routes/profile.py`, `frontend/lib/api.ts` | High |
| F-011 | Upsert profile | Create or update the single profile row | Confirmed | `backend/app/services/profile.py`, `frontend/components/ProfilePage.tsx` | High |
| F-012 | Live target preview | Preview targets while form changes | Confirmed | `backend/app/api/routes/profile.py`, `frontend/components/ProfilePage.tsx` | High |
| F-013 | Calc engine | Calculate BMR, TDEE, goal calories, protein, fat, carbs, carb clamp flag | Confirmed | `backend/app/services/calc.py`, `backend/tests/test_calc.py` | High |
| F-014 | Target display | Show target calories and macros | Confirmed | `frontend/components/TargetStrip.tsx`, `frontend/components/ProfilePage.tsx`, `frontend/components/DiaryPage.tsx` | High |
| F-015 | Multiple people/profiles | Track multiple people and person-scoped diary | Missing | No `person` table; no `person_id` on diary entries | High |

## Food Catalog

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-016 | Food list | Show saved foods with name, serving, calories, macros, net carbs | Confirmed | `frontend/components/FoodsPage.tsx`, `backend/app/api/routes/foods.py` | High |
| F-017 | Food search | Search by food name through the online API; show a connection error if API data cannot load | Confirmed / v1 requires error handling alignment | `backend/app/services/food.py`, `frontend/components/FoodsPage.tsx` | High |
| F-018 | Food create | Add food with required core nutrients and optional detail nutrients | Confirmed | `backend/app/api/routes/foods.py`, `frontend/components/FoodsPage.tsx` | High |
| F-019 | Food edit | Load food into form and update it | Confirmed | `frontend/components/FoodsPage.tsx`, `backend/app/services/food.py` | High |
| F-020 | Food details | Toggle inline detail nutrients | Confirmed | `frontend/components/FoodsPage.tsx` | High |
| F-021 | Food delete | Delete food from catalog | Confirmed but risky | `backend/app/services/food.py`, `frontend/components/FoodsPage.tsx` | High |
| F-022 | Food archive/inactive lifecycle | Archive used foods instead of hard delete | Missing / documented planned | `docs/FOODS_PAGE_FEATURES.md`; no DB field | High |
| F-023 | Net carbs | Compute response field as carbs minus fiber | Confirmed | `backend/app/services/food.py`, `frontend/lib/db.ts` | High |
| F-024 | Duplicate food prevention | Block exact duplicates | Missing / documented planned | `docs/FOODS_PAGE_FEATURES.md`; no constraint/service check | High |
| F-025 | Gram metadata | Store optional grams per serving | Confirmed | `backend/app/models.py`, `frontend/components/FoodsPage.tsx` | High |

## Diary and Weekly Tracking

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-026 | Diary day view | Show entries for selected date | Confirmed | `backend/app/api/routes/diary.py`, `frontend/components/DiaryPage.tsx` | High |
| F-027 | Add diary entry by servings | Log selected food and serving quantity | Confirmed | `backend/app/services/diary.py`, `frontend/components/DiaryPage.tsx` | High |
| F-028 | Delete diary entry | Remove a diary entry | Confirmed | `backend/app/api/routes/diary.py`, `frontend/components/DiaryPage.tsx` | High |
| F-029 | Update diary entry API | Update entry date, food, or quantity via API | Confirmed backend only | `backend/app/api/routes/diary.py`, no edit UI | High |
| F-030 | Nutrition snapshot | Freeze per-serving food values at log time | Confirmed | `backend/app/services/diary.py`, `backend/tests/test_diary_snapshot.py` | High |
| F-031 | Weekly summary | Aggregate Sunday-to-Saturday totals and targets | Confirmed | `backend/app/services/aggregation.py`, `frontend/components/DiaryPage.tsx` | High |
| F-032 | Gram-based diary logging | Log by grams when serving grams exists | Missing / documented planned | `docs/FOODS_PAGE_FEATURES.md`, no Diary UI/API field | High |

## Online Data Access, Future Offline/Sync, and Tests

| ID | Feature | Capability | Status | Evidence | Confidence |
|---|---|---|---|---|---|
| F-033 | Online API reads | Load Profile, Foods, Diary, and Week data from the backend API for v1 | Required / partially aligned | `frontend/lib/api.ts`, backend routers | High |
| F-034 | Online API writes | Save Profile, Food, and Diary changes only after successful API response | Required / current code not aligned because it can queue offline writes | `frontend/lib/api.ts`, page mutation handlers | High |
| F-035 | Connection error handling | Show clear connection/API-unreachable errors and preserve unsaved form input without queueing | Required / missing | `frontend/lib/api.ts`, page components | High |
| F-036 | IndexedDB cache and offline mutation queue | Cache personal nutrition data and queue writes offline | Future Scope / out of v1 | `frontend/lib/db.ts`, product decision in `13_PRODUCT_DECISIONS.md` | High |
| F-037 | Sync push/pull and pending sync states | Replay queued changes, pull server state, show pending/syncing status, handle conflicts | Future Scope / out of v1 | `backend/app/api/routes/sync.py`, `frontend/components/SyncStatus.tsx` | High |
| F-038 | Backend tests | Test calc, snapshot, and online API behavior; sync tests become future-scope coverage | Partial | `backend/tests` | High |
