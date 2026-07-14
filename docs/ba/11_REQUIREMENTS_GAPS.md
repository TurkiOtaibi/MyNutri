# Requirements Gaps

This file now separates resolved product decision gaps from remaining implementation alignment and QA coverage gaps.

## Current Food Decision Update - D-024/D-025

The latest Food page decisions supersede older BA gaps that required Food archive/inactive behavior, `is_active`, `archived_at`, Active/Archived filters, `serving_label`, or `serving_grams` as Food source-of-truth fields.

Resolved by D-024/D-025:
- Add Food page structure is decided: `/foods/new` is required and `/foods` must not contain a large inline Add Food form.
- Food details route is `/foods/:id`.
- Food edit route is `/foods/:id/edit`.
- Food deletion is permanent hard delete with confirmation, not archive/inactive.
- Deleted Foods disappear from list/search/future Diary selection.
- Deleted Foods do not block duplicate creation.
- Food nutrition source of truth is per 100g/per 100ml.
- Default unit fields are required: `default_unit_type`, `unit_amount`, `unit_basis`.
- Optional nutrients are supported and collapsed by default.
- Optional nutrient validation ranges and cross-field rules are resolved by D-026.

Current Food implementation alignment items:

| ID | Alignment item | Severity | Evidence | Required v1 alignment |
|---|---|---|---|---|
| ALIGN-FOOD-D024-001 | Foods list currently needs verification/rework to remove large inline Add Food form and support standalone Add route. | High | `FoodsPage.tsx`, frontend routes | Add `/foods/new`; keep `/foods` focused on browse/search/list/actions. |
| ALIGN-FOOD-D024-002 | Food details/edit dedicated routes need implementation or verification. | High | Frontend routes/components | Add `/foods/:id` and `/foods/:id/edit`; edit reuses Add Food structure. |
| ALIGN-FOOD-D025-001 | Current Food model/API uses serving-based assumptions and lacks D-025 fields. | Critical | `models.Food`, schemas, Food form/API | Add per-100g/per-100ml `nutrition_basis`, default-unit fields, brand/category/notes/data_source, and optional nutrient fields after planning/migration approval. |
| ALIGN-FOOD-D025-002 | Food hard delete currently lacks required confirmation/copy/duplicate-submit safeguards. | Critical | `services/food.py`, `FoodsPage.tsx` | Keep permanent delete lifecycle but add D-025 confirmation, Arabic copy, online-only behavior, and one-request pending state. |
| ALIGN-FOOD-D025-003 | Existing Diary snapshot may not preserve enough Food data after Food deletion. | Critical | `nutrition_snapshot`, Diary display/aggregation | Snapshot must preserve Food name, nutrition basis, nutrition values, logged quantity, log mode, and calculated totals. |
| ALIGN-FOOD-D025-004 | Duplicate check must use current-catalog D-025 key. | High | No duplicate service/schema/DB check | Normalize `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`; ignore deleted Foods. |
| ALIGN-FOOD-D025-005 | Older archive/inactive implementation and QA assumptions must stay out of execution. | High | Current code/test cases may still reflect older assumptions; current BA wording has been cleaned or marked superseded. | Do not add `is_active`, `archived_at`, archived status, restore, or Active/Archived filters for v1. Regenerate Food QA cases from current BA. |
| ALIGN-FOOD-D026-001 | Optional nutrient D-026 ranges and cross-field rules are not implemented. | High | Current schemas/forms do not include all D-026 fields/rules | Implement numeric `>= 0`, per-field max, `fiber_g <= carb_g`, `added_sugar_g <= sugar_g`, and saturated/trans fat cross-field rules after planning. |
| ALIGN-FOOD-D026-002 | Current code naming uses `total_sugars_g` while current BA uses `sugar_g` for total sugar. | Medium | Current Food schema/model/type evidence | Implement a clear API/storage mapping: `sugar_g` is total sugar, `added_sugar_g` is added sugar, and `total_sugars_g` is legacy/current-code naming only. |

## Resolved Product Decision Gaps

| Former gap / QA issue | Status | Decision |
|---|---|---|
| Offline/sync behavior unclear for v1 | Resolved in requirements | D-001 |
| Service worker scope unclear | Resolved in requirements | D-002 |
| Food delete hard vs archive lifecycle unclear | Resolved in requirements; D-025 supersedes D-003 archive behavior | D-003, D-025 |
| Food archive field design unclear | Resolved in requirements; archive fields removed from v1 | D-004, D-025 |
| Archived foods in duplicate checks unclear | Resolved in requirements; no archive state in v1 | D-005, D-025 |
| Exact duplicate key unclear | Resolved in requirements using current-catalog D-025 key | D-006, D-025 |
| Gram logging v1/future unclear | Resolved in requirements | D-007 |
| Future diary date policy unclear | Resolved in requirements | D-008 |
| Birth-date/age bounds unclear | Resolved in requirements | D-009 |
| Diary edit scope unclear | Resolved in requirements | D-010 |
| Arabic validation copy missing | Resolved in requirements | D-011 |
| Practical max values missing | Resolved in requirements | D-012 |
| API error mapping unclear | Resolved in requirements | D-013 |
| Food delete confirmation pattern unclear | Resolved in requirements | D-014 |
| Mobile/browser support matrix missing | Resolved in requirements | D-015 |
| Multi-profile v1 scope unclear | Resolved in requirements | D-016 |
| Profile reset/delete scope unclear | Resolved in requirements | D-017 |
| Diary delete confirmation unclear | Resolved in requirements | D-018 |
| Serving grams API/UI naming unclear | Resolved in requirements | D-019 |
| Long food name display behavior unclear | Resolved in requirements | D-020 |
| Exact gram-mode Diary API/storage contract unclear | Resolved in requirements | D-021 |
| Exact Arabic read-failure copy missing | Resolved in requirements | D-022 |
| Stale item, duplicate-submit, retry, and minimum accessibility behavior unclear | Resolved in requirements | D-023 |
| Add Food page structure unclear | Resolved in requirements | D-024 |
| Food hard-delete vs archive latest decision unclear | Resolved in requirements | D-025 |
| Optional nutrient max ranges previously unresolved | Resolved in requirements | D-026 |

## Remaining Implementation Alignment Items

These are not open product questions. They are mismatches between updated BA requirements and current code.

| ID | Alignment item | Severity | Evidence | Required v1 alignment |
|---|---|---|---|---|
| ALIGN-001 | Profile save failure queues local mutation. | Critical | `ProfilePage.tsx`, `frontend/lib/db.ts` | Failed profile save must not queue or save locally. |
| ALIGN-002 | Food save/delete failure writes local data and queues mutation. | Critical | `FoodsPage.tsx`, `frontend/lib/db.ts` | Failed food writes must not queue or save locally. |
| ALIGN-003 | Diary add/delete failure mutates local entries and queues mutation. | Critical | `DiaryPage.tsx`, `frontend/lib/db.ts` | Failed diary writes must not queue or save locally. |
| ALIGN-004 | Service worker currently caches fetched GET responses. | High | `frontend/public/service-worker.js` | Static shell assets only, or remove service worker. |
| ALIGN-005 | Sync status UI exposes pending/syncing behavior. | High | `SyncStatus.tsx`, `Providers.tsx` | Hide/remove from v1. |
| ALIGN-006 | `/sync` API remains mounted. | High | `backend/app/api/router.py`, `backend/app/api/routes/sync.py` | Future Scope only; exclude/hide/disable for v1. |
| ALIGN-007 | Superseded: Food archive fields are not v1 requirements. | Medium | Earlier BA/implementation history | Do not add `is_active` or `archived_at`; follow D-025 hard-delete lifecycle. |
| ALIGN-008 | Food hard delete lacks required confirmation and snapshot-after-delete verification. | Critical | `services/food.py`, `FoodsPage.tsx` | Keep permanent hard delete, add D-025 confirmation/copy, no local queue, and snapshot regression coverage. |
| ALIGN-009 | Deleted Foods must be absent from list/search/future Diary selection. | High | `list_foods`, `DiaryPage` food selector | Use current catalog behavior; no Active/Archived filters. |
| ALIGN-010 | Duplicate current-catalog Food blocking missing. | High | No service/schema/DB check | Enforce D-006/D-025 duplicate key. |
| ALIGN-011 | Food/Profile/Diary validation ranges do not match v1. | High | `schemas.py`, UI forms | Align D-009/D-012. |
| ALIGN-012 | Gram Diary logging missing. | High | No Diary grams UI/API | Implement D-007 behavior after planning. |
| ALIGN-013 | Diary quantity-only edit missing and backend update is broader than v1 UI scope. | High | `PUT /diary/{id}`, no edit UI | Expose quantity-only edit; constrain behavior. |
| ALIGN-014 | Diary delete confirmation is not specified in current UI evidence. | High | `DiaryPage.tsx` | Add simple confirmation showing food name/date; cancel no change; confirm after API success. |
| ALIGN-015 | `serving_grams` Food source-of-truth assumptions are superseded. | Medium | Food form / field labels | Replace Food create/edit model with D-025 default-unit fields. |
| ALIGN-016 | Long food name list truncation needs implementation/verification. | Medium | Food list/cards CSS/components | Two-line ellipsis in list/cards; full name in details/edit; no horizontal scroll or action overlap. |
| ALIGN-017 | Cached read fallbacks can present IndexedDB/offline-built personal data after API read failure. | High | `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts` | Show exact D-022 read-failure message and do not treat cached personal data as current source of truth. |
| ALIGN-018 | Offline page, metadata, and service-worker copy/behavior may still imply offline/sync support. | Medium | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx`, `frontend/public/service-worker.js` | Mark as Future Scope or replace with shell-only/network-error behavior for v1. |
| ALIGN-019 | Duplicate-submit, stale item, retry, and minimum accessibility behaviors need explicit UI/API implementation. | High | Profile/Food/Diary forms, Food delete dialog, Diary delete/edit flows | Align to D-023: one pending request, stale-record messages, retry current visible input, focus/live-region/dialog behavior. |

## Remaining Requirements Questions

All v1 product questions identified in this BA package are resolved by D-001 through D-026.

| ID | Question | Severity | Impact |
|---|---|---|---|
| None | No remaining v1 requirements questions. | N/A | N/A |

## Test Coverage Gaps

| ID | Gap | Current test evidence | Recommended test area |
|---|---|---|---|
| TEST-001 | No direct profile API validation tests. | `test_calc.py` only covers calc. | Profile GET/PUT/preview validation and errors. |
| TEST-002 | No direct current Food CRUD/search/permanent-delete tests. | Existing sync test is Future Scope. | Food create/list/search/detail/update/permanent-delete/duplicate/default-unit/net-carbs validation and snapshot-after-delete coverage. |
| TEST-003 | No diary API CRUD/gram/edit/date tests. | Snapshot unit test only. | Serving/gram create, quantity edit, future date block, delete. |
| TEST-004 | No auth tests. | None. | Protected routers 401/success. |
| TEST-005 | No frontend E2E/component tests. | None visible. | Main flows and validation copy. |
| TEST-006 | No mobile/RTL visual tests. | None visible. | D-015 viewport/device matrix. |
| TEST-007 | No accessibility tests. | None visible. | Error associations, dialog focus, icon names. |
| TEST-008 | No online network-error tests. | None visible. | API down, timeout, 401, 404, 422, 5xx, no local queue. |
| TEST-009 | No explicit QA test data matrix for stale items, duplicate submits, gram entries, and read-failure copy. | None visible. | Add test data for D-021, D-022, and D-023 coverage. |

## Future Scope

Do not implement for v1 unless product scope changes:
- Offline cache as source of truth.
- IndexedDB personal data source-of-truth behavior.
- Offline mutation queue.
- Sync push/pull.
- Pending sync states.
- Conflict handling.
- Stale cache behavior.
- Offline Profile/Food/Diary writes.
- Sync rejection handling.
- Future meal planning.
- Multi-profile support and profile switching.
- Profile reset/delete.
- Recipes, barcode scanning, public food import.
- Food archive/inactive lifecycle, `is_active`, `archived_at`, archived status, restore, and Active/Archived filters.
