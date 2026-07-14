# myNutri v1 Alignment Implementation Plan

Planning status: technical plan only.
Application code changed: No.
Migrations created: No.
Features implemented: No.

## Latest Food Page Decision Update - D-024/D-026

This implementation plan was originally written against archive/inactive and serving-based Food assumptions. D-024, D-025, and D-026 supersede those assumptions for v1.

Current Food implementation direction:
- Add Food must be a standalone page at `/foods/new`.
- Food details route is `/foods/:id`.
- Food edit route is `/foods/:id/edit`.
- `/foods` must remain focused on browsing, searching, viewing, editing, and deleting Foods; it must not contain a large inline Add Food form.
- Food deletion is permanent hard delete with confirmation, not archive/inactive.
- Do not add `is_active`.
- Do not add `archived_at`.
- Do not show Archived status, Status column, Archived filter, or Active/Archived filter.
- Food nutrition source of truth is per 100g/per 100ml.
- Required Food model/API fields now include `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`.
- Optional basic fields now include `brand`, `category`, `notes`, and `data_source`.
- Optional nutrients are supported but optional and collapsed by default.
- Optional nutrient max ranges and cross-field rules are defined by D-026.
- Diary snapshots must remain readable after Food deletion and preserve Food name, nutrition basis, nutrition values, logged quantity, log mode, and calculated totals.

Planning impact:
- All rows below that recommend Food archive lifecycle, `is_active`, `archived_at`, archive APIs, active/archive filters, or archive tests are superseded by D-025.
- All rows below that rely on `serving_grams` as the Food source-of-truth are superseded by the D-025 per-100g/per-100ml plus default-unit model.
- Existing QA test cases generated before D-024/D-026 are impacted and should be updated before execution.
- This section is planning-only; no migrations or application code are created by this update.

## 1. Executive Summary

The finalized BA package defines myNutri v1 as an online-only personal nutrition system. The current codebase is a working FastAPI + SQLModel backend and Next.js frontend, but several current behaviors still reflect the earlier offline-first direction.

Before v1 can match the finalized BA package and the 101-case QA baseline, the implementation must:

- Remove or disable v1 offline write behavior, local mutation queues, sync push/pull, pending sync states, and cached personal data as source of truth.
- Add standalone Food routes/pages for `/foods/new`, `/foods/:id`, and `/foods/:id/edit`.
- Keep Food deletion as permanent hard delete, but add confirmation, Arabic permanent-delete copy, duplicate-submit protection, and snapshot-after-delete verification.
- Replace archive/inactive Food requirements with no `is_active`, no `archived_at`, and no Active/Archived filters.
- Replace serving-based Food source-of-truth with per-100g/per-100ml nutrition plus default-unit fields.
- Block current-catalog duplicate Foods using normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`.
- Enforce v1 validation ranges and D-026 optional nutrient cross-field rules, including `fiber_g <= carb_g`, `added_sugar_g <= sugar_g`, and saturated/trans fat consistency.
- Add Diary `log_mode` and gram logging using Food nutrition basis/default-unit calculation.
- Implement the D-021 Diary snapshot contract.
- Restrict Diary edit to mode-specific quantity only.
- Add Food permanent-delete and Diary delete confirmation dialogs.
- Block future Diary dates.
- Add Arabic validation, read-failure, stale-item, and API error handling.
- Prevent duplicate submits and handle stale item states without local mutation.
- Improve mobile RTL, long food-name handling, and accessibility for forms, dialogs, icon buttons, errors, and live regions.
- Replace or quarantine sync/offline tests and add v1 API/component/E2E/a11y/mobile coverage mapped to the 101 QA test cases.

Implementation can start, but it should not be done as one large batch. The safest first phase is disabling offline/sync v1 behavior, because it prevents data loss/confusion and simplifies every later flow.

## 2. Current Code vs BA Requirements

| Area | Current code behavior | BA requirement | Gap | Severity | Recommended implementation approach | Files likely affected | Related user stories | Related test case IDs |
|---|---|---|---|---|---|---|---|---|
| Offline writes | Failed Profile/Food/Diary writes queue mutations and may mutate IndexedDB. | Writes succeed only after successful API response; no local queue or saved-later copy. | Local mutations and queued sync are v1-invalid. | Critical | Remove write fallback mutation paths; keep visible form input; show Arabic write error; require explicit retry. | `frontend/components/ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts` | `US-NETWORK-WRITE-001`, `US-FUTURE-OFFLINE-001` | `TC-PROFILE-003`, `TC-FOOD-009`, `TC-DIARY-013`, `TC-DIARY-017`, `TC-NET-002`, `TC-UX-002` |
| Cached read fallback | Profile/Foods/Diary/Week fall back to IndexedDB/offline computed state on API failure. | Fresh API data or clear read-failure state; cached personal data is not source of truth. | Cached data can appear current. | Critical | Remove cached personal-data fallback from v1 reads; show exact Arabic read-failure copy and retry path. | `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts` | `US-NETWORK-READ-001`, `US-NETWORK-READ-COPY-001` | `TC-PROFILE-005`, `TC-FOOD-006`, `TC-DIARY-002`, `TC-WEEK-003`, `TC-NET-001` |
| Sync API | `/sync/pull` and `/sync/push` are mounted and `test_sync.py` validates them. | Sync push/pull and pending sync states are Future Scope only. | v1 exposes non-v1 API. | High | Unmount sync router for v1 or guard behind non-v1 flag; quarantine sync tests as Future Scope. | `backend/app/api/router.py`, `backend/app/api/routes/sync.py`, `backend/tests/test_sync.py` | `US-FUTURE-OFFLINE-001` | `TC-FUTURE-001`, `TC-NET-002`, `TC-PWA-001` |
| Sync UI | `SyncStatus` shows pending/syncing/offline states and flushes queue. | No pending sync state or sync-later UX in v1. | User-facing v1 contradiction. | High | Remove `SyncStatus` from `Providers` for v1; remove flush queue calls from UI. | `frontend/components/Providers.tsx`, `SyncStatus.tsx`, `frontend/lib/db.ts` | `US-FUTURE-OFFLINE-001` | `TC-FUTURE-001`, `TC-NET-002` |
| Service worker | Caches all successful GET responses, including API responses if same scope. | Static shell only; no personal API data cache as source of truth. | Personal data cache risk. | High | Restrict service worker to static shell asset allowlist, skip API requests, or remove service worker for v1 if confusing. | `frontend/public/service-worker.js`, `frontend/components/Providers.tsx`, `frontend/app/offline/page.tsx` | `US-SHELL-SCOPE-001`, `US-FUTURE-OFFLINE-001` | `TC-SHELL-002`, `TC-PWA-001`, `TC-NET-001` |
| Offline page metadata | Offline page says local data can be used and changes sync later; metadata says app works offline. | Online-only v1; no offline writes or sync-later copy. | User-facing copy contradicts v1. | High | Rewrite offline page and metadata to connection-error/shell-only copy, or remove offline route from shell. | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx`, `frontend/public/manifest.json` | `US-SHELL-HAPPY-001`, `US-SHELL-SCOPE-001` | `TC-SHELL-001`, `TC-PWA-001` |
| Food schema model | Current Food model lacks D-025 per-100g/per-100ml and default-unit fields. | Food nutrition source of truth is per 100g/per 100ml; no archive fields. | Required schema mismatch. | Critical | Plan schema/API changes for `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`, optional basics, and optional nutrients. Do not add `is_active`/`archived_at`. | `backend/app/models.py`, `schemas.py`, Alembic migration later | `US-FOOD-CRUD-001`, `US-FOOD-CRUD-002` | Update Food QA cases before execution. |
| Food delete | Backend hard deletes Food; frontend calls delete immediately. | Delete is permanent hard delete but requires confirmation and permanent-delete copy. | Confirmation, copy, pending state, and snapshot verification missing. | Critical | Keep hard-delete lifecycle; add confirmation dialog, one pending request, API failure handling, and snapshot-after-delete regression coverage. | `backend/app/services/food.py`, `api/routes/foods.py`, Food pages/components | `US-FOOD-CRUD-003` | Update Food delete QA cases before execution. |
| Deleted Food exclusion | `list_foods` returns existing Foods; hard-deleted Foods are absent by deletion. | Deleted Foods must not appear in list/search/future Diary selection; no active/archive filtering. | Need verify UI/API behavior after delete. | High | Ensure delete removes Food from catalog and Diary picker reloads current catalog; no Active/Archived filters. | `services/food.py`, `routes/foods.py`, `DiaryPage.tsx`, Food pages/components | `US-FOOD-HAPPY-001`, `US-DIARY-VALIDATION-001` | Update Food list/Diary picker QA cases. |
| Duplicate Food blocking | No duplicate check. | Block current-catalog duplicates by normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`; deleted Foods do not block. | Duplicate catalog entries possible. | High | Add normalization helper, service-level check, 422 response; consider DB support after schema decision. | `services/food.py`, `schemas.py`, migration later | `US-FOOD-VALIDATION-003` | Update duplicate QA cases. |
| Net carbs and optional nutrients | `net_carbs` can become negative; no full D-026 optional nutrient max/cross-field validation. | Negative net carbs invalid; D-026 optional nutrient values are optional when blank but validated when provided. | Invalid nutrition accepted. | High | Add Pydantic validators, service guards, and frontend field validation for D-026; clamp is not acceptable for Food values. | `backend/app/schemas.py`, `services/food.py`, Food form components | `US-FOOD-VALIDATION-002`, `US-FOOD-VALIDATION-004` | Existing Food validation cases need D-026 updates before execution. |
| Profile validation | Backend uses `height/weight > 0`, protein 1.6-2.2, fat 0.20-0.30; frontend inputs match old ranges. | Height 100-250, weight 20-300, protein 1.0-3.0, fat 0.15-0.40, age 10-100, no future birth date. | Validation mismatch. | High | Align backend Pydantic validators and frontend min/max; add age validation. | `schemas.py`, `ProfilePage.tsx`, `services/calc.py` tests | `US-PROFILE-VALIDATION-001` | `TC-PROFILE-006`, `TC-PROFILE-007`, `TC-PROFILE-008`, `TC-PROFILE-010`, `TC-PROFILE-011` |
| Food validation ranges | Backend only enforces non-negative and min length; frontend only native min. | v1 max ranges, trim/max text, nutrition basis, default-unit fields, and D-026 optional nutrient ranges. | Invalid values can save. | High | Add Pydantic validators and frontend form validation; keep Arabic messages in UI. | `schemas.py`, Food form components | `US-FOOD-VALIDATION-001`, `US-FOOD-VALIDATION-004` | Food validation QA cases need D-026 boundary and cross-field coverage before execution. |
| Diary `log_mode` | `DiaryEntryCreate` has only `quantity`; snapshot assumes servings multiplier. | Create payload `{ entry_date, food_id, log_mode, quantity }`; `quantity` means servings or grams by mode. | Gram logging impossible. | Critical | Add `LogMode` enum/model field/schema field; update create response and frontend types. | `models.py`, `schemas.py`, `services/diary.py`, `frontend/lib/types.ts`, `api.ts`, `DiaryPage.tsx` | `US-DIARY-GRAM-001`, `US-DIARY-GRAM-CONTRACT-001` | `TC-DIARY-003`, `TC-DIARY-005`, `TC-DIARY-007`, `TC-DIARY-019`, `TC-DIARY-020` |
| Gram logging | No grams mode UI/API. | Gram mode enabled only when Food nutrition basis/default-unit data supports unambiguous gram calculation; totals are proportional to per-100g/per-100ml values. | Required v1 feature missing. | High | Add segmented control/radio for default-unit/servings vs grams; disable or error when gram calculation is ambiguous; calculate server-side from snapshot data. | `DiaryPage.tsx`, `services/diary.py`, `schemas.py` | `US-DIARY-GRAM-001` | `TC-DIARY-005`, `TC-DIARY-006`, `TC-DIARY-019` |
| D-021 snapshot | Snapshot stores older serving-oriented food fields only; totals calculated on response from quantity. | Snapshot stores Food identity, nutrition basis, nutrition values at logging time, default-unit data used for calculation, `log_mode`, `logged_quantity`, and `calculated_totals`. | Contract incomplete. | Critical | Extend snapshot schema and creation helper; preserve old entries through compatibility if needed. | `services/diary.py`, `schemas.py`, `aggregation.py`, tests | `US-DIARY-GRAM-CONTRACT-001`, `US-DIARY-INTEGRITY-001` | `TC-DIARY-007`, `TC-DIARY-008`, `TC-DIARY-014`, `TC-FOOD-017` |
| Diary edit | Backend update allows date and food changes; frontend has no edit UI. | v1 edit quantity only; no food/date/log_mode/snapshot edits. | API too broad and UI missing. | High | Restrict update schema/service to quantity only; add minimal edit UI for quantity by original mode. | `schemas.py`, `services/diary.py`, `api/routes/diary.py`, `api.ts`, `DiaryPage.tsx` | `US-DIARY-EDIT-001` | `TC-DIARY-011`, `TC-DIARY-012`, `TC-DIARY-013`, `TC-DIARY-018` |
| Diary delete | Frontend deletes immediately; no confirmation. | Confirmation with food name/date; cancel no change; confirm only after API success. | Accidental loss risk. | High | Add accessible confirmation dialog and pending state; keep backend hard delete for Diary entry after confirmation. | `DiaryPage.tsx`, possibly shared dialog component | `US-DIARY-CRUD-002` | `TC-DIARY-015`, `TC-DIARY-016`, `TC-DIARY-017`, `TC-DIARY-022` |
| Future Diary dates | UI date input allows future; backend accepts future. | Today or past only. | Future planning out of v1. | High | Add backend validator and frontend `max=today`; block future entries and edits. | `schemas.py`, `DiaryPage.tsx`, `dates.ts` | `US-DIARY-VALIDATION-001` | `TC-DIARY-009` |
| API error mapping | `apiFetch` throws raw detail; UI often catches all errors and uses cached fallback or generic notes. | 401/404/422/network/5xx mapped to Arabic field/page/form errors. | User sees wrong or misleading behavior. | High | Add shared frontend error mapper, typed validation error handling, exact read-failure messages, and no fallback mutation. | `frontend/lib/api.ts`, new error helper, all pages | `US-ERROR-MAPPING-001`, `US-NETWORK-READ-COPY-001` | `TC-ERR-001`, `TC-ERR-002`, read/write failure cases |
| Arabic validation messages | Current Arabic text is present but mojibake in files and not field-level; relies on browser validation. | Exact Arabic messages for validation/read/API/stale/confirmation. | Field UX and encoding need alignment. | High | Centralize Arabic strings, ensure files are UTF-8, render field errors manually instead of relying on native validation. | `labels.ts` or new `messages.ts`, `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx` | `US-A11Y-001`, `US-ERROR-MAPPING-001` | `TC-PROFILE-010`, `TC-FOOD-010`, `TC-DIARY-020`, `TC-ERR-001` |
| Duplicate submit | Some submit buttons disable during pending; delete buttons and confirmation flows do not yet exist. | Pending writes send exactly one request; retry after failure explicit. | Partial. | Medium | Disable submit/confirm during pending, show Arabic duplicate-submit/pending status, preserve form input. | `ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx` | `US-UX-STATUS-001` | `TC-UX-001`, `TC-UX-002`, `TC-FOOD-030`, `TC-DIARY-022` |
| Stale item handling | 404 detail strings exist but not mapped to stale Food/Diary Arabic messages. | Stale Food/Diary states show exact Arabic messages and do not mutate locally. | Partial. | High | Map 404/409/422 stale responses by operation; validate current server Food at submit; preserve state. | Backend services/routes, `api.ts`, pages | `US-FOOD-EDGE-001`, `US-DIARY-CRUD-002` | `TC-FOOD-022`, `TC-FOOD-023`, `TC-DIARY-018`, `TC-DIARY-021` |
| Mobile/RTL/long names | RTL shell exists; long names use `overflow-wrap:anywhere`; no two-line clamp; some fixed grids scroll. | No horizontal scroll except intentional week grid; long Food names two-line in list, full in details/edit; safe-area and mixed RTL readable. | Needs polish. | Medium | Add line clamp for list names, full detail names, safe-area padding, touch target checks, RTL icon review. | `globals.css`, `FoodsPage.tsx`, `DiaryPage.tsx`, `AppNav.tsx` | `US-MOBILE-001` | `TC-MOBILE-001` to `TC-MOBILE-005`, `TC-MOBILE-004` |
| Accessibility | Some titles and role status exist; icon buttons use `title`, no structured field errors/dialog focus. | Accessible names, `aria-describedby`, `aria-invalid`, live regions, keyboard dialogs, first invalid focus. | Needs implementation. | High | Add accessible dialog component, field error component, aria-live status regions, icon `aria-label`s, focus management. | UI components, page forms, `ProgressBar.tsx` | `US-A11Y-001` | `TC-A11Y-001` to `TC-A11Y-006` |
| Automated tests | Backend has calc/snapshot/sync tests only; no frontend tests. | v1 tests for validation, permanent delete, duplicate, gram mode, online errors, mobile/RTL/a11y. | Coverage incomplete. | High | Add backend unit/API tests, frontend component tests, Playwright E2E, a11y and visual checks. | `backend/tests`, new frontend test setup, Playwright config | `US-QA-001` | All 101 test cases |

## 3. Implementation Phases

### Phase 1 - Disable Offline/Sync v1 Behavior

Goal:
Make the application online-only before changing domain behavior. Failed reads show errors; failed writes do not mutate local state, do not queue, and do not say they will sync later.

Files likely affected:
- `frontend/lib/db.ts`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/components/DiaryPage.tsx`
- `frontend/components/Providers.tsx`
- `frontend/components/SyncStatus.tsx`
- `frontend/public/service-worker.js`
- `frontend/app/offline/page.tsx`
- `frontend/app/layout.tsx`
- `backend/app/api/router.py`
- `backend/app/api/routes/sync.py`
- `backend/tests/test_sync.py`

Backend changes:
- Unmount `/sync` router for v1 or gate it behind an explicit future-scope flag that is off by default.
- Stop treating `test_sync.py` as a v1 acceptance test; move/quarantine it or mark future-scope in test suite naming.
- Keep normal protected APIs and health endpoint.

Frontend changes:
- Remove `queueMutation`, `flushQueuedMutations`, `addLocalDiaryEntry`, `buildOfflineWeek`, and cached read fallback calls from v1 page flows.
- Remove `SyncStatus` from `Providers`.
- Replace cached read fallback with exact Arabic read-failure messages.
- Replace failed write fallback with exact Arabic write error and preserved visible form input.
- Restrict service worker to static assets only, skip API requests, or remove service worker registration for v1.
- Rewrite offline page and metadata so they do not imply local data access or sync.

Database/migration changes:
- None in this phase.

Tests required:
- API/router smoke test that `/sync` is absent or disabled in v1 configuration.
- Frontend tests for no offline queued mutation after failed Profile/Food/Diary writes.
- Service worker static review or E2E showing no personal API cache source of truth.

Related manual QA test cases:
- `TC-SHELL-001`, `TC-SHELL-002`, `TC-PWA-001`, `TC-FUTURE-001`, `TC-NET-001`, `TC-NET-002`, `TC-PROFILE-003`, `TC-FOOD-009`, `TC-DIARY-013`, `TC-DIARY-017`, `TC-UX-002`

Risks:
- Removing IndexedDB fallback may expose missing loading/error UX.
- Existing code may import `db.ts` helpers from multiple pages; remove usage carefully.
- If service worker cache names change, stale old service workers may need cleanup logic.

Definition of Done:
- No v1 UI shows pending sync, syncing, saved locally, or will sync later.
- Failed writes preserve visible input and show `طھط¹ط°ط± ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ط®ط§ط¯ظ…. ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ.`
- Failed reads show exact page-level read error copy.
- Personal Profile/Food/Diary/Week data is not served as source of truth from IndexedDB/cache after fresh API failure.
- `/sync` is not part of v1 runtime behavior.

### Phase 2 - Backend Data Model and API Alignment

Goal:
Align backend persistence and contracts with v1 domain rules before frontend UI depends on them.

Files likely affected:
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/food.py`
- `backend/app/services/diary.py`
- `backend/app/services/aggregation.py`
- `backend/app/api/routes/foods.py`
- `backend/app/api/routes/diary.py`
- `backend/app/api/routes/profile.py`
- Alembic migration files later
- `backend/tests/*`

Backend changes:
- Do not add Food `is_active` or `archived_at`; plan D-025 fields instead.
- Keep permanent Food hard delete, but add D-025 confirmation/copy and snapshot verification.
- Ensure hard-deleted Foods are absent from list/search and future Diary selection.
- Add duplicate current-catalog Food check using normalized `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`.
- Add Food validation: text trim/max, numeric max ranges, nutrition basis/default-unit rules, and D-026 optional nutrient max/cross-field rules.
- Enforce `fiber_g <= carb_g`, `added_sugar_g <= sugar_g`, `saturated_fat_g <= fat_g`, `trans_fat_g <= fat_g`, and `saturated_fat_g + trans_fat_g <= fat_g` when the related values are provided.
- Add Profile validation: age 10-100, no future birth date, v1 numeric ranges.
- Add Diary `log_mode` enum and mode-aware quantity validation.
- Add future date blocking for Diary create/update.
- Add D-021 snapshot contract.
- Restrict Diary update payload to quantity only.
- Return predictable 401/404/422/5xx responses that frontend can map.

Frontend changes:
- Update `frontend/lib/types.ts` to match response shape only after backend contract is finalized.
- Update `frontend/lib/api.ts` request payload types for `log_mode` and quantity-only edit.

Database/migration changes:
- Planned in Section 4; do not create migrations in this planning step.

Tests required:
- Backend unit tests for normalization, duplicate blocking, net carbs, snapshot contract, gram multiplier, profile age/ranges.
- API tests for create/edit/permanent-delete/list current Foods, Diary create/edit/delete, validation errors, and auth.

Related manual QA test cases:
- Backend/API-heavy set: `TC-AUTH-001`, `TC-AUTH-002`, `TC-AUTH-003`, `TC-INFRA-001`, `TC-CONFIG-001`, `TC-PROFILE-006` to `TC-PROFILE-011`, `TC-FOOD-011` to `TC-FOOD-015`, `TC-FOOD-020`, `TC-FOOD-028`, `TC-FOOD-029`, `TC-DIARY-003` to `TC-DIARY-009`, `TC-DIARY-019`, `TC-DIARY-020`, `TC-ERR-001`, `TC-ERR-002`

Risks:
- Snapshot contract changes may need backward compatibility for existing entries.
- Food permanent delete can affect historical Diary display if snapshots are incomplete.
- Duplicate checks must normalize D-025 identity fields consistently.

Definition of Done:
- Backend accepts only v1-valid payloads.
- Backend does not add archive/inactive Food behavior; confirmed Food delete remains permanent hard delete.
- Backend can create serving and gram Diary entries with D-021 snapshot.
- Backend update Diary only changes quantity.
- Backend weekly/day summaries use snapshot calculated totals.

### Phase 3 - Foods Page Alignment

Goal:
Make Foods page match v1 catalog behavior and backend contracts.

Files likely affected:
- `frontend/components/FoodsPage.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/lib/labels.ts` or new `frontend/lib/messages.ts`
- `frontend/app/globals.css`

Backend changes:
- Phase 2 Food APIs must be available.

Frontend changes:
- Show loading, empty, no-results, exact read-failure, validation, stale, and server-error states.
- Add client-side validation matching backend ranges where practical.
- Show exact Arabic field errors.
- Preserve draft on write failure.
- Add permanent-delete confirmation dialog with Food name and Arabic copy.
- Disable repeated submit/confirm while pending.
- Ensure deleted Foods are absent from list/search/future Diary selection after successful delete.
- Show duplicate current-catalog Food error from API.
- Show D-026 optional nutrient field-level errors from API or frontend validation.
- Add current default-unit labels for `Default unit`, `Unit amount`, and `Unit basis`.
- Two-line truncate long Food names in lists/cards; show full name in details/edit.
- Add accessible names for icon buttons and details toggle.

Database/migration changes:
- None in this phase beyond Phase 2.

Tests required:
- Component tests for Food form validation and errors.
- E2E tests for browse/search/create/detail/edit/permanent-delete/duplicate/no-results.
- Accessibility tests for icon buttons, field errors, and permanent-delete dialog.
- Visual/mobile tests for long Food names.

Related manual QA test cases:
- `TC-FOOD-001` through `TC-FOOD-030`, `TC-SEC-001`, `TC-PERF-001`, `TC-MOBILE-004`, `TC-A11Y-001`, `TC-A11Y-002`, `TC-A11Y-003`, `TC-A11Y-004`, `TC-A11Y-005`

Risks:
- Native browser validation may conflict with custom Arabic errors.
- Duplicate/stale API errors need consistent response shape.
- Food form may become visually dense; optional nutrient section must remain accessible.

Definition of Done:
- Foods page passes all Food-related manual cases.
- No Food write failure creates local data or queued mutation.
- Permanent-delete confirmation is keyboard accessible and safe.
- Current-catalog duplicate checks and D-026 optional nutrient rules are enforced end to end.

### Phase 4 - Diary Page Alignment

Goal:
Align Diary logging, aggregation, editing, delete behavior, and gram mode with v1.

Files likely affected:
- `frontend/components/DiaryPage.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/lib/dates.ts`
- `frontend/app/globals.css`
- Backend Diary files from Phase 2

Backend changes:
- Phase 2 Diary API contract must be complete.

Frontend changes:
- Add `log_mode` segmented control/radio: servings vs grams.
- Quantity field label and validation changes by mode.
- Disable gram mode or show Arabic error when selected Food basis/unit data cannot support an unambiguous gram calculation.
- Send `{ entry_date, food_id, log_mode, quantity }`.
- Block future dates in UI with `max=today` and custom error state.
- Add minimal edit UI for quantity only.
- Add delete confirmation with food name/date.
- Preserve input after failures and show Arabic errors.
- Handle stale Food and stale Diary errors.
- Disable duplicate submit/confirm while pending.
- Ensure day/week totals use API snapshot totals and refresh after successful writes.

Database/migration changes:
- None beyond Phase 2.

Tests required:
- API and E2E tests for default-unit/gram create, unsupported gram calculation, future date block, edit quantity only, delete confirmation, stale item, duplicate submit.
- Regression tests for snapshot integrity after Food edit/delete.

Related manual QA test cases:
- `TC-DIARY-001` through `TC-DIARY-022`, `TC-WEEK-001` to `TC-WEEK-003`, `TC-FOOD-017`, `TC-DIARY-014`, `TC-PROFILE-012`

Risks:
- D-021 snapshot shape must be kept stable before UI and tests are implemented.
- Existing diary entries may lack `log_mode`; compatibility or migration defaults must be planned.
- Edit UI must not accidentally allow Food/date/mode changes.

Definition of Done:
- Diary supports servings and grams with correct server-calculated totals.
- Gram mode enforces D-025 nutrition-basis/default-unit calculation support.
- Future dates are blocked.
- Edit is quantity-only by original mode.
- Delete is confirmed and online-only.
- Snapshot integrity passes after Food edits/deletion.

### Phase 5 - Profile and Validation Alignment

Goal:
Align Profile, target preview, and validation behavior with BA and shared Arabic error handling.

Files likely affected:
- `backend/app/schemas.py`
- `backend/app/services/calc.py`
- `backend/tests/test_calc.py`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/TargetStrip.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/messages.ts` or `labels.ts`

Backend changes:
- Add Profile validators for age, birth date, height, weight, protein/kg, fat percentage.
- Keep calc engine output with `carb_clamped`.
- Ensure 422 errors expose enough detail to map known fields.

Frontend changes:
- Align input min/max values and date max.
- Add field-level errors with Arabic copy.
- Do not treat target preview as reliable when inputs are invalid.
- Preserve input on write failure and do not queue.
- Verify no Profile reset/delete UI.
- Show target values on Diary after successful Profile save.

Database/migration changes:
- None expected for Profile.

Tests required:
- Profile validation component/API tests.
- Calc unit tests including `carb_clamped`.
- E2E for save success/failure and target display.

Related manual QA test cases:
- `TC-PROFILE-001` through `TC-PROFILE-012`, `TC-TARGET-001` to `TC-TARGET-003`, `TC-DIARY-001`, `TC-WEEK-001`

Risks:
- Browser date inputs behave differently across mobile browsers.
- Advanced fields inside `<details>` need first-invalid focus behavior.

Definition of Done:
- Profile validations match v1 ranges exactly.
- Exact Arabic messages appear for required/invalid/min/max/date/enum failures.
- Failed Profile save remains unsaved and preserves input.
- Diary target display updates from saved Profile.

### Phase 6 - Arabic Errors, UX, Mobile, RTL, and Accessibility

Goal:
Apply cross-cutting UI quality requirements consistently across Profile, Foods, Diary, app shell, dialogs, and status states.

Files likely affected:
- `frontend/lib/api.ts`
- `frontend/lib/messages.ts` or `labels.ts`
- `frontend/components/*`
- `frontend/app/globals.css`
- `frontend/app/layout.tsx`
- `frontend/public/manifest.json`

Backend changes:
- Return consistent status codes and validation details; no need for backend Arabic copy if frontend maps errors, unless backend owns localized error payloads.

Frontend changes:
- Shared Arabic message map for field, read, write, API, stale, success, confirmation, loading, empty, no-results.
- Shared field error rendering with `aria-invalid` and `aria-describedby`.
- Shared confirmation dialog with keyboard focus trap/restore.
- `aria-label` on icon-only controls.
- `role=status`/`aria-live` for async states.
- Long Food name list clamp and full display in details/edit.
- Mobile safe-area padding, no horizontal scroll, 44px touch targets.
- RTL icon direction and mixed Arabic/English readability review.
- Confirm `ProgressBar` has meaningful accessible labeling.

Database/migration changes:
- None.

Tests required:
- Component/a11y tests for field errors, dialogs, live regions, icon buttons.
- Playwright mobile viewport checks at 360, 390, 430, 768, desktop.
- Visual regression for long names and RTL mixed text.

Related manual QA test cases:
- `TC-APP-001`, `TC-APP-002`, `TC-ERR-001`, `TC-ERR-002`, `TC-A11Y-001` to `TC-A11Y-006`, `TC-MOBILE-001` to `TC-MOBILE-005`, `TC-SEC-001`, `TC-PERF-001`

Risks:
- Current files show mojibake in Arabic strings; ensure UTF-8 source encoding and actual browser output are correct.
- Accessibility is difficult to retrofit if form components remain ad hoc.

Definition of Done:
- Arabic messages match BA.
- Forms and dialogs are keyboard and screen-reader usable.
- Required mobile viewports have no blocking layout issues.
- Long and mixed-direction strings remain readable.

### Phase 7 - Automated Test Coverage

Goal:
Convert the 101 QA test cases into appropriate automated and manual suites after implementation slices land.

Files likely affected:
- `backend/tests/*`
- New frontend test configuration and test files
- Playwright or equivalent E2E configuration
- CI workflow files if present

Backend changes:
- Add test fixtures for DB/session isolation.
- Add API tests for auth, validation, Food permanent-delete/duplicate/default-unit/net carbs, Diary `log_mode`, snapshots, future dates, edit/delete.

Frontend changes:
- Add component tests for forms/dialogs/error states.
- Add E2E tests for full flows.
- Add accessibility and visual checks where practical.

Database/migration changes:
- Test database setup must apply migrations rather than relying only on `create_all` where possible.

Tests required:
- See Section 7.

Related manual QA test cases:
- All 101 cases in `docs/qa/test-cases/USER_STORY_TEST_CASES.csv`.

Risks:
- Building all tests before backend contracts settle will create churn.
- PWA/mobile/a11y/performance cases need some manual or specialized tooling.

Definition of Done:
- Core backend tests pass.
- Key E2E flows pass.
- Manual-only cases are documented separately.
- Future-scope sync tests are not part of v1 acceptance.

## 4. Database and Migration Plan

### Current D-024/D-026 Food Schema Direction

Do not create migrations yet. When implementation starts, replace the older archive/serving-based Food migration plan with this current direction:

| Table | Change | Type | Notes |
|---|---|---|---|
| `food` | Add `nutrition_basis` | enum/string | Allowed values: `per_100g`, `per_100ml`. Required. |
| `food` | Add `default_unit_type` | enum/string | `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon`. Required. |
| `food` | Add `unit_amount` | numeric | Required; amount of `unit_basis` represented by one default unit. |
| `food` | Add `unit_basis` | enum/string | `g`, `ml`. Required. |
| `food` | Add optional basics | text nullable | `brand`, `category`, `notes`, `data_source`. |
| `food` | Add optional micronutrients | numeric nullable | Potassium, calcium, iron, magnesium, zinc, vitamin D mcg, vitamin B12 mcg, vitamin C mg, vitamin A mcg, folate mcg, vitamin K mcg. |
| `food` | Add D-026 validation | schema/service validation | Optional nutrients are nullable; provided values must pass per-field max and cross-field rules. |
| `food` | Do not add archive fields | N/A | `is_active` and `archived_at` are not v1 requirements. |
| `diary_entry.nutrition_snapshot` | Extend snapshot content | JSON | Preserve Food name, nutrition basis, nutrition values, logged quantity, log mode, and calculated totals so history survives Food deletion. |

Do not create migrations yet. Plan the migration after Phase 2 contract design is accepted.

Required schema changes:

| Table | Change | Type | Default/backfill | Notes |
|---|---|---|---|---|
| `food` | D-025 Food source-of-truth fields | enum/string/numeric/text | Requires explicit migration/backfill plan | `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`, optional basics, optional nutrients. |
| `food` | Duplicate support | optional functional index or service-level check | N/A | Service-level check is simpler. A DB constraint is safer but harder with normalization of the D-025 duplicate key. Deleted Foods do not exist and do not block duplicates. |
| `food` | Optional nutrient validation | schema/service rules | N/A | D-026 rules are validation logic, not archive fields. No `is_active` or `archived_at`. |
| `diary_entry` | Add `log_mode` | enum/string, not null | Existing rows default to `servings` | Values: `servings`, `grams`. |
| `diary_entry` | Keep `quantity` | numeric | Existing meaning remains servings for backfilled rows | In v1, meaning depends on `log_mode`; no separate persisted `grams` field required. |
| `diary_entry` | Extend `nutrition_snapshot` JSON | JSONB | Existing snapshots can be interpreted as serving-mode legacy snapshots or migrated in place | New snapshots include D-021 fields. |

Migration sequencing:

1. Add nullable/with-default columns in a migration.
2. Backfill existing Foods into D-025 per-100g/per-100ml/default-unit structure using an explicit data conversion rule accepted before migration.
3. Backfill existing Diary rows to `log_mode='servings'`.
4. Optionally enrich existing snapshots with `log_mode='servings'`, `logged_quantity=quantity`, default-unit calculation context where available, and `calculated_totals`.
5. Add not-null constraint/default where needed.
6. Add duplicate-support indexes only if the implementation chooses DB-backed duplicate enforcement.

Decision points before migration:

- Whether `log_mode` should be PostgreSQL enum or string with check constraint. Recommendation: string/check or Python enum mapped to SQL enum; choose based on migration tolerance.
- Whether duplicate blocking is service-only or backed by DB. Recommendation for v1: service-level normalization check plus tests; DB unique can be added later if collisions become a real risk.
- Whether old snapshots are migrated or handled by compatibility code. Recommendation: compatibility code plus optional migration enrichment.
- How to convert existing serving-based Food rows into the D-025 per-100g/per-100ml source-of-truth model. Recommendation: explicit one-time migration decision before implementation starts.

## 5. API Contract Changes

### Current Food API Contract Direction - D-024/D-026

Food create/update request fields:
- Required: `name`, `nutrition_basis`, `calories`, `protein_g`, `carb_g`, `fat_g`, `default_unit_type`, `unit_amount`, `unit_basis`.
- Optional: `brand`, `category`, `notes`, `data_source`, optional nutrient fields.
- `nutrition_basis` allowed values: `per_100g`, `per_100ml`.
- `default_unit_type` allowed values: `g`, `ml`, `cup`, `slice`, `piece`, `scoop`, `serving`, `tablespoon`, `teaspoon`.
- `unit_basis` allowed values: `g`, `ml`.
- Optional nutrients are nullable. If provided, they must satisfy D-026 numeric, maximum, and cross-field validation.
- Sugar mapping: `sugar_g` is total sugar; `added_sugar_g` is added sugar; `total_sugars_g` is legacy/current-code naming only and should not be the current v1 API source-of-truth unless an explicit compatibility layer maps it.

Food delete:
- Keep `DELETE /foods/{food_id}` as permanent hard delete unless implementation planning chooses another REST shape.
- API success removes the Food from the catalog.
- API failure must not be represented as local deletion.
- The frontend confirmation dialog is required before calling delete.

Food list/detail:
- `GET /foods` returns current catalog Foods only because deleted Foods no longer exist.
- `GET /foods/{id}` returns 404/not-found for deleted or missing Foods.
- No archive status fields are returned as v1 requirements.

Duplicate response:
- Current-catalog duplicate create/edit returns validation error mapped to the Arabic duplicate message.
- Deleted Foods cannot block duplicate creation.

D-026 validation response:
- Negative optional nutrient values return 422 and map to `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.`
- Above-maximum optional nutrient values return 422 and map to `القيمة الغذائية الإضافية أعلى من الحد المسموح.`
- `fiber_g > carb_g` returns 422 and maps to `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.`
- `added_sugar_g > sugar_g` when both values are provided returns 422 and maps to `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.`
- `added_sugar_g` with blank `sugar_g` is allowed when `added_sugar_g` is otherwise valid.
- `saturated_fat_g > fat_g` returns 422 and maps to `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- `trans_fat_g > fat_g` returns 422 and maps to `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.`
- `saturated_fat_g + trans_fat_g > fat_g` when all values are provided returns 422 and maps to `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.`

### Food list/detail

Current:
- `GET /foods?q=...` returns all Foods.
- Food response lacks D-025 per-100g/per-100ml fields and several optional nutrients.

Required:
- Default `GET /foods` returns current catalog Foods ordered by name.
- `q` searches current catalog Foods by name.
- Food response does not include `is_active` or `archived_at` as v1 requirements.
- Permanently deleted Foods are absent from list/search and future Diary selection.
- `GET /foods/{id}` returns 404/not-found for deleted Foods.

### Food create

Required payload:
- Same Food fields, with v1 validation.
- D-025 Food fields required: `nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`.
- Trim and normalize text for validation/duplicate check.

Required behavior:
- Current-catalog duplicate returns 422 with duplicate field/form detail.
- Deleted Food records do not block duplicate creation because they no longer exist.
- D-026 optional nutrient validation failures return 422 with field-level errors.

### Food edit

Required behavior:
- Edits existing current-catalog Foods only.
- Same validation and duplicate rules as create.
- Historical Diary snapshots unchanged.
- If Food is deleted before edit submit, return stale/not-found response mapped to Arabic stale Food message.

### Food hard delete - D-025

Endpoint option:
- Keep `DELETE /foods/{food_id}` for minimal frontend/API churn. v1 DELETE means permanent hard delete after frontend confirmation.

Required behavior:
- Permanently remove the Food record from the catalog.
- Do not set `is_active`.
- Do not set `archived_at`.
- Existing Diary entries remain unchanged and readable through snapshots.
- Repeated delete on an already-deleted Food returns 404/stale for UI clarity.

### Diary create

Required payload:

```json
{
  "entry_date": "2026-07-09",
  "food_id": "uuid",
  "log_mode": "servings",
  "quantity": 1.5
}
```

For gram mode:

```json
{
  "entry_date": "2026-07-09",
  "food_id": "uuid",
  "log_mode": "grams",
  "quantity": 150
}
```

Required behavior:
- `entry_date` today or past only.
- `food_id` must identify a current catalog Food.
- `log_mode='servings'`: quantity 0.01-50 default units/servings; totals are calculated from the Food default unit and nutrition basis.
- `log_mode='grams'`: quantity 1-5000; totals are calculated from Food nutrition basis and gram amount. For `per_100g`, multiplier = quantity / 100.
- Snapshot freezes:
  - Food identity.
  - `log_mode`.
  - `logged_quantity`.
  - Nutrition basis and nutrition values at logging time.
  - Default unit data used for calculation.
  - `calculated_totals`.

### Diary edit

Required payload:

```json
{
  "quantity": 2
}
```

Required behavior:
- Quantity only.
- Existing entry `log_mode` determines validation range and multiplier.
- Cannot change Food.
- Cannot change date.
- Cannot change `log_mode`.
- Cannot edit frozen snapshot nutrition values.
- Recalculate mode-specific multipliers and `calculated_totals` from the frozen snapshot contract.

### Diary delete

Backend:
- Existing `DELETE /diary/{entry_id}` can remain hard delete for Diary entry after frontend confirmation.

Frontend:
- Confirmation required before API call.
- Failed delete leaves entry and totals unchanged.

### Profile save

Required behavior:
- Online-only update after successful API response.
- Validate age 10-100 and no future birth date.
- Validate v1 ranges.
- No reset/delete in v1.

### Error responses

Backend should use status codes consistently:

| Status | Meaning | Frontend mapping |
|---|---|---|
| 401 | Unauthorized | `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` |
| 404 | Missing/stale item | Item not found or stale Arabic message by operation. |
| 422 | Validation error | Field-level Arabic errors where possible; otherwise form-level 422 copy. |
| Timeout/network | No response | Connection/read/write message; no local save. |
| 5xx | Server failure | `ط­ط¯ط« ط®ط·ط£ ظپظٹ ط§ظ„ط®ط§ط¯ظ…. ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` |

## 6. Frontend UX Changes

### Current Food UX Direction - D-024/D-026

Required Food UX changes:
- `/foods` is list/search/browse only, with View/Edit/Delete actions.
- `/foods/new` is a standalone Add Food page.
- `/foods/:id` is a standalone Food detail page.
- `/foods/:id/edit` is a standalone Edit Food page reusing the Add Food grouped form.
- Add Food page sections: Basic food information, Nutrition basis, Core nutrition values, Default unit, Optional nutrients, Notes and data source.
- Optional nutrients are collapsed by default.
- Optional nutrients are optional when blank; provided values show D-026 Arabic field-level errors for invalid ranges or cross-field conflicts.
- Add Food has no delete action.
- Food details/edit may expose delete.
- Food delete dialog uses permanent-delete copy, shows Food name, supports cancel/Escape, and is keyboard accessible.
- Desktop Food list columns: Food name, Brand, Category, Nutrition basis, Default unit, Calories, Protein, Carbs, Fat, Actions.
- Mobile Food cards: Food name, Nutrition basis, Default unit, Calories, Protein, Carbs, Fat.
- Do not show optional micronutrients in the main list/card.
- Do not show Status column, Archived filter, or Active/Archived filter.
- Long Food names clamp to two lines in list/cards and show full in detail/edit.

Required UI changes:

| UI area | Required change | Files likely affected | Key QA cases |
|---|---|---|---|
| Food delete | Add confirmation dialog showing Food name, permanent-delete explanation, cancel/confirm, keyboard support. | Food detail/edit pages, shared dialog | Update Food delete QA cases before execution. |
| Diary delete | Add confirmation dialog showing Food name and date, cancel/confirm, totals refresh after API success. | `DiaryPage.tsx`, shared dialog | `TC-DIARY-015`, `TC-DIARY-016`, `TC-DIARY-022` |
| Diary gram mode | Add segmented/radio control for servings/grams; dynamic label/range. | `DiaryPage.tsx`, `types.ts` | `TC-DIARY-005`, `TC-DIARY-006`, `TC-DIARY-019` |
| Unsupported gram calculation | Disable gram mode or show Arabic error when Food basis/unit data cannot support gram calculation. | `DiaryPage.tsx` | Update Diary gram QA cases before execution. |
| Arabic validation | Field-level errors under fields; form-level errors near actions. | All forms | Profile/Food/Diary validation cases |
| Optional nutrient validation | Open the collapsed Optional nutrients section and focus the first invalid optional nutrient field when D-026 validation fails. | Food add/edit pages | D-026 Food validation cases to add/update before execution |
| Read-failure messages | Exact Arabic page/section errors for Profile, Foods, Food detail, Diary day, Week. | All pages | `TC-PROFILE-005`, `TC-FOOD-006`, `TC-FOOD-025`, `TC-DIARY-002`, `TC-WEEK-003` |
| Loading/empty/no-results | Distinct states and copy. | `FoodsPage.tsx`, `DiaryPage.tsx`, `ProfilePage.tsx` | `TC-FOOD-004`, `TC-FOOD-005`, `TC-DIARY-010`, `TC-WEEK-002` |
| Duplicate submit | Disable submit/confirm while pending; one request only; preserve input on failure. | All mutation flows | `TC-UX-001`, `TC-UX-002`, `TC-FOOD-030`, `TC-DIARY-022` |
| Stale item | Map stale Food/Diary errors to exact Arabic messages; do not locally mutate. | `api.ts`, pages | `TC-FOOD-022`, `TC-FOOD-023`, `TC-DIARY-018`, `TC-DIARY-021` |
| Mobile RTL | No horizontal scroll, 44px controls, safe-area/bottom nav spacing, long names clamp. | `globals.css`, components | `TC-MOBILE-001` to `TC-MOBILE-005` |
| Accessibility | `aria-label`, `aria-invalid`, `aria-describedby`, focus first invalid, dialog focus trap/restore, live regions. | Shared form/dialog/status components | `TC-A11Y-001` to `TC-A11Y-006` |

## 7. Test Plan

### Current Food QA Impact - D-024/D-026

Existing QA test cases generated before D-024/D-026 are impacted. Before execution, update Food-related tests to:
- Remove archive/inactive expectations.
- Remove `is_active` and `archived_at` expectations.
- Remove Active/Archived filter expectations.
- Replace archive tests with permanent hard-delete confirmation, cancel, success, API failure, duplicate-submit, and snapshot-after-delete tests.
- Add standalone route tests for `/foods`, `/foods/new`, `/foods/:id`, and `/foods/:id/edit`.
- Add per-100g/per-100ml nutrition basis tests.
- Add default unit field tests.
- Add optional nutrients collapsed-section tests.
- Add D-026 optional nutrient boundary and cross-field validation tests.
- Add current-catalog duplicate-key tests.
- Add duplicate-after-delete allowed test.
- Add mobile card/list long-name RTL tests.

The 101 QA test cases should be split by test level. Some cases intentionally remain manual or partial because they require device validation, accessibility tooling, service-worker inspection, controlled stale fixtures, or performance measurement.

### Manual QA first-pass cases

Use these before full automation to validate end-to-end product feel and scope:

- App/shell/navigation: `TC-APP-001`, `TC-APP-002`, `TC-SHELL-001`, `TC-PWA-001`
- Foods daily use: `TC-FOOD-001`, `TC-FOOD-003`, `TC-FOOD-004`, `TC-FOOD-005`, `TC-FOOD-007`, `TC-FOOD-016`, `TC-FOOD-018`, `TC-FOOD-019`, `TC-FOOD-024`
- Diary daily use: `TC-DIARY-001`, `TC-DIARY-003`, `TC-DIARY-005`, `TC-DIARY-011`, `TC-DIARY-012`, `TC-DIARY-015`, `TC-DIARY-016`, `TC-WEEK-001`, `TC-WEEK-002`
- Mobile/RTL/a11y smoke: `TC-MOBILE-001` to `TC-MOBILE-005`, `TC-A11Y-001` to `TC-A11Y-006`
- Governance: `TC-QA-001`

### Backend unit/API tests

Recommended automated backend coverage:

- Auth/config/health: `TC-AUTH-001`, `TC-AUTH-002`, `TC-AUTH-003`, `TC-INFRA-001`, `TC-CONFIG-001`
- Profile validation/targets: `TC-PROFILE-006` to `TC-PROFILE-011`, `TC-TARGET-001`, `TC-TARGET-003`
- Food validation/permanent-delete/duplicate: `TC-FOOD-011`, `TC-FOOD-012`, `TC-FOOD-013`, `TC-FOOD-014`, `TC-FOOD-015`, `TC-FOOD-020`, `TC-FOOD-026`, `TC-FOOD-028`, `TC-FOOD-029`
- Diary API/snapshot: `TC-DIARY-003`, `TC-DIARY-004`, `TC-DIARY-005`, `TC-DIARY-006`, `TC-DIARY-007`, `TC-DIARY-008`, `TC-DIARY-009`, `TC-DIARY-019`, `TC-DIARY-020`
- Error mapping status setup: `TC-ERR-001`, `TC-ERR-002`

### Frontend component tests

Recommended component coverage:

- Profile form validation and messages: `TC-PROFILE-010`, `TC-PROFILE-011`, `TC-PROFILE-008`
- Food form validation: `TC-FOOD-010`, `TC-FOOD-011`, `TC-FOOD-012`, `TC-FOOD-013`, `TC-FOOD-026`, `TC-FOOD-027`, `TC-FOOD-029`
- Confirmation dialogs: `TC-FOOD-018`, `TC-FOOD-019`, `TC-DIARY-015`, `TC-DIARY-016`, `TC-A11Y-004`
- Diary mode controls: `TC-DIARY-005`, `TC-DIARY-006`, `TC-DIARY-011`, `TC-DIARY-012`, `TC-DIARY-019`
- A11y field/status behavior: `TC-A11Y-001`, `TC-A11Y-002`, `TC-A11Y-003`, `TC-A11Y-005`

### E2E tests

Recommended Playwright or equivalent:

- Online-only no queue: `TC-PROFILE-003`, `TC-FOOD-009`, `TC-DIARY-013`, `TC-DIARY-017`, `TC-NET-001`, `TC-NET-002`, `TC-FUTURE-001`
- Food flows: `TC-FOOD-001` to `TC-FOOD-030`
- Diary flows: `TC-DIARY-001` to `TC-DIARY-022`
- Weekly summary: `TC-WEEK-001` to `TC-WEEK-003`
- Duplicate submit/retry: `TC-UX-001`, `TC-UX-002`, `TC-FOOD-030`, `TC-DIARY-022`
- Read/write/API errors: all `TC-ERR-*`, `TC-NET-*`, page read-failure cases

### Mobile/RTL checks

- Required viewport matrix: `TC-MOBILE-001`
- Touch/keyboard: `TC-MOBILE-002`
- Mixed Arabic/English: `TC-MOBILE-003`
- Long Food names: `TC-MOBILE-004`
- Safe-area/bottom nav: `TC-MOBILE-005`

### Accessibility checks

- Icon names: `TC-A11Y-001`
- Field errors: `TC-A11Y-002`
- Collapsed/optional error visibility: `TC-A11Y-003`
- Dialog keyboard/focus: `TC-A11Y-004`
- Live status regions: `TC-A11Y-005`
- RTL direction/focus/contrast: `TC-A11Y-006`

### Regression tests

High-value regression set:

- Snapshot integrity: `TC-FOOD-017`, `TC-DIARY-008`, `TC-DIARY-014`
- Food hard delete lifecycle: `TC-FOOD-002`, `TC-FOOD-018`, `TC-FOOD-020`, `TC-DIARY-014`
- Gram logging: `TC-DIARY-005`, `TC-DIARY-006`, `TC-DIARY-007`, `TC-DIARY-019`
- Online-only behavior: `TC-NET-001`, `TC-NET-002`, `TC-SHELL-002`, `TC-FUTURE-001`
- Validation: `TC-PROFILE-006` to `TC-PROFILE-011`, `TC-FOOD-010` to `TC-FOOD-015`, `TC-DIARY-004`, `TC-DIARY-009`, `TC-DIARY-019`, `TC-DIARY-020`

## 8. Risk Register

### Current Food Risks - D-024/D-026

| Risk | Impact | Mitigation | Owner area |
|---|---|---|---|
| Historical archive/inactive notes are retained only as superseded context. | Developers may misread legacy context as current scope. | Treat D-024/D-026 sections as controlling; do not add archive fields or filters. | Product / Backend / Frontend |
| Current tests still expect archive behavior. | QA may fail correct hard-delete implementation. | Rewrite Food test cases before execution. | QA |
| Hard delete without snapshot completeness can break historical Diary display. | Data/history readability regression. | Implement snapshot display independent of Food record before or with delete confirmation work. | Backend / Frontend |
| Per-100g/per-100ml model changes Food schema and Diary calculations. | Migration/API/UI churn. | Implement in a dedicated schema/API phase before UI polish. | Backend |
| D-026 optional nutrient validation is incomplete or inconsistent between frontend and backend. | Invalid nutrition details can save, or valid optional blanks can be blocked. | Implement backend as source of truth, mirror frontend checks, and test blank/zero/min/max/above-max/cross-field cases. | Backend / Frontend / QA |
| Standalone routes affect existing FoodsPage component assumptions. | Navigation/regression risk. | Split list/add/detail/edit routes incrementally with E2E navigation tests. | Frontend |

| Risk | Impact | Mitigation | Owner area |
|---|---|---|---|
| Offline queue remains active in one flow | User believes unsaved local data is real; v1 scope violation. | Phase 1 removes queue usage first; add no-queue E2E tests. | Frontend |
| Service worker caches API data | Stale/private data may appear as current. | Skip API requests in service worker; clear old caches; test with offline reload. | Frontend |
| Food hard delete with incomplete snapshot | Historical Diary entries may lose Food identity/totals after Food deletion. | Complete D-025 snapshot contract before or with delete work; add snapshot-after-delete regression tests. | Backend / Frontend |
| Food schema migration mishandles existing Foods | Existing catalog values may map incorrectly to per-100g/per-100ml/default-unit fields. | Plan explicit migration/backfill rules before creating migrations; validate with seed data. | Backend / Product |
| Duplicate Food normalization inconsistent UI/backend | Duplicate entries bypass backend or are blocked unexpectedly. | Centralize backend normalization; frontend only pre-checks as helper. | Backend |
| D-021 snapshot shape churns mid-implementation | Diary UI/tests break and totals become inconsistent. | Finalize backend contract before frontend Diary changes. | Backend |
| Existing Diary rows lack `log_mode` | Old entries may fail response validation. | Backfill `servings`; add compatibility for legacy snapshots. | Backend |
| Frontend relies on native validation | Arabic field messages and a11y expectations fail. | Implement controlled validation/error components. | Frontend |
| Stale item scenarios are hard to reproduce | QA cannot reliably verify concurrency behavior. | Add deterministic API test fixtures or two-client E2E helpers. | QA/Backend |
| Arabic strings remain mojibake in source | UI appears broken or test assertions fail. | Ensure UTF-8 files and central message module; verify rendered Arabic in browser. | Frontend |
| Removing sync tests lowers test count but improves v1 relevance | CI may look weaker initially. | Replace with online-only no-queue tests in same phase. | QA |
| Mobile/a11y fixes happen late | Layout/dialog choices may need rework. | Introduce shared dialog/field components early in UI phases. | Frontend |

## 9. Recommended Implementation Order

Current Food-related order after D-024/D-026:

1. Keep Phase 1 focused on disabling online-only conflicts: no offline writes, no sync queue, no cached personal data as source of truth.
2. Before Food UI work, revise backend Food schema/API planning to use per-100g/per-100ml nutrition and default-unit fields. Do not add archive fields.
3. Implement Food snapshot independence for Diary history so old entries remain readable after Food deletion.
4. Implement Food permanent-delete confirmation and hard-delete API/UI behavior.
5. Split Food frontend into `/foods`, `/foods/new`, `/foods/:id`, and `/foods/:id/edit`.
6. Add duplicate current-catalog validation using the D-025 key.
7. Add D-026 optional nutrient boundary and cross-field validation.
8. Update QA test cases before manual execution or automation planning.

Do not implement everything in one batch. Use this order:

1. Phase 1 - Disable Offline/Sync v1 Behavior.
   - Removes the biggest product contradiction and data-integrity risk.
   - Simplifies all later error-handling work.

2. Phase 2A - Backend validation and D-025 Food schema/API.
   - Add planned migration, permanent Food hard delete, duplicate check, and D-026 Food validation.

3. Phase 3 - Foods Page Alignment.
   - Connect Food UI to permanent-delete/duplicate/validation API and confirmation dialog.

4. Phase 2B - Backend Diary contract.
   - Add `log_mode`, gram calculations, D-021 snapshot, future date block, quantity-only update.

5. Phase 4 - Diary Page Alignment.
   - Add serving/gram controls, edit quantity, delete confirmation, stale/error handling.

6. Phase 5 - Profile and Validation Alignment.
   - Align Profile ranges/messages and target display; can partly happen earlier, but avoid mixing with schema-heavy Diary work.

7. Phase 6 - Cross-cutting Arabic UX, mobile, RTL, and accessibility hardening.
   - Some shared components can start earlier, but final pass should happen after major flows exist.

8. Phase 7 - Automated Test Coverage.
   - Add tests with each phase, then run full 101-case mapping as final readiness gate.

Suggested slice policy:

- Each phase should include backend tests or frontend tests for the behavior it changes.
- Each phase should run a small manual smoke set before moving to the next phase.
- Do not revive offline/sync behavior during implementation unless product scope changes.

## 10. Final Recommendation

Implementation can start.

Recommended first phase:
Phase 1 - Disable Offline/Sync v1 Behavior.

What should not be touched yet:

- Do not create migrations until the D-025 Food schema and Diary `log_mode` schema details are accepted.
- Do not implement multi-profile/person switching.
- Do not implement Profile reset/delete.
- Do not implement recipes, barcode scanning, brand/category/source fields, or public food database import.
- Do not preserve offline write queue, pending sync, or sync push/pull as v1 behavior.

What must be verified after each phase:

- No v1 scope regression into offline-first behavior.
- Related API contracts match BA and `USER_STORY_TEST_CASES.csv`.
- Arabic messages render correctly and are not mojibake in browser.
- Failed writes never mutate local state or queue.
- Stale/duplicate-submit behavior does not create duplicate records or data loss.
- A targeted subset of the 101 QA cases passes before moving to the next phase.

Final release gate:

- All 101 QA test cases are either passed, intentionally manual-passed, or documented with a product-approved exception.
- All Future Scope offline/sync artifacts are disabled, removed from v1 runtime, or clearly non-authoritative static shell behavior only.
