# Traceability Matrix

| Feature | Entity/resource | CRUD/action | Actor | User story | Fields | Validation/permissions | Code evidence | Test evidence | Confidence | Gap |
|---|---|---|---|---|---|---|---|---|---|---|
| App shell RTL | App shell | Read/navigation | User | `US-APP-HAPPY-001` | N/A | RTL/lang | `frontend/app/layout.tsx`, `AppNav.tsx` | Missing E2E | High | No visual/mobile tests |
| Single-user auth | Protected APIs | Access | System/user | `US-AUTH-PERM-001` | Authorization header | Bearer token | `backend/app/core/auth.py` | Missing auth tests | High | Unauthorized UI missing |
| Optional installable shell | App shell | Install/open | User/system | `US-SHELL-HAPPY-001` | N/A | Online data remains source of truth | `manifest.json`, `InstallPrompt.tsx`, `service-worker.js` | Missing install/network tests | High | Offline data behavior must be disabled/deferred |
| Profile upsert | Profile | Create/update/read | User | `US-PROFILE-HAPPY-001` | Profile fields | Token, schema rules | `profile.py`, `ProfilePage.tsx`, `profile.py service` | Missing route/UI tests | High | Custom errors missing |
| Profile validation | Profile | Validate | User/system | `US-PROFILE-VALIDATION-001` | height, weight, protein, fat | Pydantic ranges | `backend/app/schemas.py` | Missing validation tests | High | Birth-date policy missing |
| Target preview | TargetResponse | Calculate | User/system | `US-TARGET-HAPPY-001` | profile inputs | Calc formulas | `calc.py`, `ProfilePage.tsx` | `test_calc.py` | High | UI tests missing |
| Food list | Food | Read list | User | `US-FOOD-HAPPY-001` | summary fields | Token | `foods.py`, `FoodsPage.tsx` | Missing direct tests | High | Loading/no-results weak |
| Food search | Food | Read list query | User | `US-FOOD-HAPPY-002` | `name`, `q` | Token; connection error on API failure | `food.py`, `api.ts` | Missing tests | High | Locale/search/network behavior untested |
| Food create | Food | Create | User | `US-FOOD-CRUD-001` | all FoodInput | Schema, token, no offline queue in v1 | `foods.py`, `FoodsPage.tsx` | Missing direct tests | High | Duplicate/custom/network errors missing |
| Food validation | Food | Validate | User/system | `US-FOOD-VALIDATION-001` | food fields | Pydantic/ge/min_length | `schemas.py`, `FoodsPage.tsx` | Missing direct tests | High | Empty numeric and whitespace gaps |
| Net carbs | Food | Compute/validate | System | `US-FOOD-VALIDATION-002` | carb, fiber | Missing `fiber <= carb` | `food.py`, `db.ts` | Snapshot test partial | High | Negative net carbs possible |
| Duplicate food | Food | Validate create/update | User/system | `US-FOOD-VALIDATION-003` | name, serving, grams | Missing | Root Foods docs | Missing tests | High | No implementation |
| Food edit | Food | Update | User | `US-FOOD-CRUD-002` | editable food fields | Schema/token; no offline queue in v1 | `foods.py`, `food.py`, `FoodsPage.tsx` | Missing direct tests | High | Error UX weak |
| Food delete/archive | Food | Delete/archive | User | `US-FOOD-CRUD-003` | food id, archive status | Token; no confirm/archive | `food.py`, `FoodsPage.tsx` | Missing tests | High | Major safety gap |
| Food details | Food | Read detail | User | `US-FOOD-HAPPY-003` | optional nutrients | N/A | `FoodsPage.tsx` | Missing UI tests | High | No timestamp/usage display |
| Diary day | DiaryEntry | Read list | User | `US-DIARY-HAPPY-001` | entry_date | Token | `diary.py`, `DiaryPage.tsx` | Missing direct tests | High | No pagination |
| Diary create | DiaryEntry | Create | User | `US-DIARY-CRUD-001` | date, food_id, quantity | quantity > 0, food exists, no offline queue in v1 | `diary.py`, `DiaryPage.tsx` | Snapshot test partial | High | Gram mode and network-error tests missing |
| Diary validation | DiaryEntry | Validate | User/system | `US-DIARY-VALIDATION-001` | quantity, food_id | Pydantic/service | `schemas.py`, `diary.py` | Missing validation tests | High | Custom errors missing |
| Diary snapshot | NutritionSnapshot | Create/read | System | `US-DIARY-INTEGRITY-001` | snapshot fields | System-generated | `services/diary.py` | `test_diary_snapshot.py` | High | Snapshot schema versioning missing |
| Diary delete | DiaryEntry | Delete | User | `US-DIARY-CRUD-002` | entry id | Token | `DiaryPage.tsx`, `diary.py` | Missing tests | High | No confirmation |
| Weekly summary | WeekSummary | Read aggregate | User/system | `US-DIARY-HAPPY-002` | dates, totals | Token | `aggregation.py`, `DiaryPage.tsx` | Missing direct tests | High | Timezone edge cases |
| Gram logging | DiaryEntry/Food | Create by grams | User | `US-DIARY-GRAM-001` | grams, serving_grams | Missing | Root Foods docs | Missing | High | Not implemented |
| Online network errors | Profile/Food/Diary | Read/write failure | User/system | `US-NETWORK-ERROR-001` | all v1 form fields | Show error; no local save/queue | `api.ts`, page mutation handlers | Missing network-error tests | High | Current code needs alignment |
| Future offline cache/sync | SyncOperation/QueuedMutation | Future local queue/sync | System | `US-FUTURE-OFFLINE-001` | mutation/cache fields | Future Scope only | `sync.py`, `db.ts`, `SyncStatus.tsx` | Existing `test_sync.py` is future-scope evidence | High | Out of v1 |
| Accessibility | UI controls | Use | User | `US-A11Y-001` | labels/buttons/errors | Partial | Components | Missing a11y tests | Medium | Icon/button/error a11y incomplete |
| Mobile UX | UI layout | Use | User | `US-MOBILE-001` | all form fields | Responsive CSS | `globals.css` | Missing visual tests | High | Safe area/bottom overlap |
| Tests | Test suite | Verify | PO/QA | `US-QA-001` | N/A | Online API, validation, connection errors | `backend/tests` | Existing partial; sync tests future-scope | High | UI/API/network coverage missing |
