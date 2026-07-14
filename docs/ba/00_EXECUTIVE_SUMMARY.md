# BA Executive Summary

Mode: requirements update from confirmed product decisions D-001 through D-026.

Scope:
- myNutri v1 online-only personal nutrition system.
- Existing BA package under `docs/ba/`.
- QA audit evidence under `docs/qa/user-story-audit/` and `docs/qa/user-story-audit-v2/`.
- Current implementation evidence from backend and frontend code.

Application code changed: No.
QA audit files changed: No.

## Product Scope

myNutri v1 is an Arabic-first RTL, mobile-first, online-only personal nutrition tracker. It supports:
- One personal profile in the current v1 scope.
- Daily target calculation.
- A shared current Food catalog.
- Diary logging by servings or grams.
- Weekly summary.
- Online API reads and writes only.
- Clear Arabic validation, network, and server error messages.
- Food creation on a standalone mobile-first page.
- Food deletion by permanent hard delete with confirmation.
- Food nutrition values stored per 100g or per 100ml, with a default logging unit.

Offline-first behavior is out of scope for v1. IndexedDB, offline mutation queues, sync push/pull, pending sync states, conflict handling, stale cache behavior, offline writes, and sync rejection handling are Future Scope only.

## Confirmed Product Decisions Applied

| Decision | Summary | BA status |
|---|---|---|
| D-001 | Remove offline write behavior from v1. | Applied |
| D-002 | Service worker may cache static shell assets only; removal recommended if confusing. | Applied |
| D-003 | Superseded by D-025; do not use archive/inactive Food delete in v1. | Superseded |
| D-004 | Superseded by D-025; do not use `is_active` or `archived_at` in v1. | Superseded |
| D-005 | Superseded by D-025; deleted Foods do not exist and do not block duplicates. | Superseded |
| D-006 | Duplicate key is current-catalog normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`. | Applied |
| D-007 | Gram-based Diary logging is required in v1. | Applied |
| D-008 | Future Diary dates are blocked. | Applied |
| D-009 | Birth date cannot be future; age must be 10-100. | Applied |
| D-010 | Minimal Diary edit is quantity-only. | Applied |
| D-011 | Exact Arabic validation/error messages are required. | Applied |
| D-012 | Practical v1 validation ranges are defined. | Applied |
| D-013 | Shared API error mapping is defined. | Applied |
| D-014 | Superseded by D-025 for Food; Food permanent delete uses confirmation dialog. | Superseded |
| D-015 | Mobile/browser support matrix is defined. | Applied |
| D-016 | Multi-profile support is Future Scope; v1 uses one Profile model. | Applied |
| D-017 | Profile reset/delete is out of scope for v1. | Applied |
| D-018 | Diary entry delete requires confirmation. | Applied |
| D-019 | Superseded by D-024/D-025 for Food catalog modeling; use default-unit fields. | Superseded |
| D-020 | Long food names use two-line truncation in lists and full display in detail/edit. | Applied |
| D-021 | Final Diary `log_mode` and mode-specific `quantity` API/storage contract is defined. | Applied |
| D-022 | Exact Arabic read-failure copy is defined for Profile, Foods, Food detail, Diary day, Weekly, and general reads. | Applied |
| D-023 | Stale item, duplicate-submit, retry, and minimum accessibility behavior is defined. | Applied |
| D-024 | Add Food is a standalone page with `/foods/new`, details at `/foods/:id`, and edit at `/foods/:id/edit`. | Applied |
| D-025 | Food deletion is permanent hard delete; no archive/inactive status or filters in v1. | Applied |
| D-026 | Optional nutrient max ranges and cross-field validation rules are defined. | Applied |

## Product Areas

1. App shell, RTL, mobile layout, and optional installable shell.
2. Single-user token authentication and API access.
3. Profile and target calculation.
4. Food catalog, standalone Add/Edit pages, per-100g/per-100ml nutrition, and permanent delete lifecycle.
5. Diary logging by servings or grams.
6. Weekly summary.
7. Online API error handling.
8. Accessibility and Arabic validation.
9. QA and testability coverage.
10. Future offline/sync scope.

## Entities and Resources

| Entity/resource | v1 status | Notes |
|---|---|---|
| Profile | Confirmed / needs validation alignment | Single profile, online save only. |
| TargetResponse | Confirmed | Calculated from Profile; not stored. |
| Food | Confirmed / needs data-model, duplicate, standalone-page, and delete-confirmation alignment | Nutrition source of truth is per 100g/per 100ml; delete is permanent hard delete. |
| DiaryEntry | Confirmed / needs gram and quantity-edit alignment | Snapshot integrity remains required after Food edit/delete. |
| NutritionSnapshot | Confirmed / needs gram/default-unit calculation definition | Freezes nutrition at logging time and must remain readable after Food deletion. |
| WeekSummary | Confirmed | Sunday-to-Saturday aggregation. |
| SyncOperation / QueuedMutation | Future Scope | Not a v1 requirement. |
| Service worker | Constrained v1 shell only | Must not cache personal nutrition data. |

## Requirements Counts

| Package area | Count |
|---|---:|
| Features documented | 45 |
| User stories documented | 40 |
| Product decisions documented | 26 |
| Remaining product open questions | 0 |
| Implementation alignment items | 19 |
| Field/validation implementation gaps | 12 |

## QA Audit Remediation

The fresh v2 QA audit found 0 Critical and 2 High BA issues, plus supporting BA cleanup items. This update resolves the requirement-decision side of those findings:
- Online-only write behavior is now explicit.
- Food delete lifecycle is now permanent hard delete with confirmation.
- Add Food standalone page routes and structure are decided.
- Food data model is now per 100g/per 100ml with default unit fields.
- Optional nutrient max ranges and cross-field validation rules are defined.
- Duplicate rules are decided.
- Negative net carbs validation is decided.
- Gram logging is required and specified.
- Future diary dates are blocked.
- Profile date/age bounds are defined.
- Arabic messages are defined.
- Mobile/browser support matrix is defined.
- Exact Diary gram-mode API/storage contract is defined.
- Exact read-failure Arabic copy is defined.
- Stale item, duplicate-submit, retry, and minimum accessibility behavior are defined.
- Offline/cached-read artifacts are documented as Future Scope or implementation alignment, not v1 requirements.

Remaining work is implementation alignment and QA verification, not product decision discovery.

## Implementation Alignment Warning

Current code still contradicts several v1 BA decisions:
- `frontend/components/ProfilePage.tsx` queues failed profile saves.
- `frontend/components/FoodsPage.tsx` queues failed food saves/deletes and writes local IndexedDB.
- `frontend/components/DiaryPage.tsx` queues failed diary add/delete operations.
- `frontend/lib/db.ts` contains IndexedDB cache and mutation queue behavior.
- `frontend/components/SyncStatus.tsx` exposes sync/pending status.
- `backend/app/api/routes/sync.py` and `backend/tests/test_sync.py` are future-scope evidence.
- `frontend/public/service-worker.js` caches fetched GET responses.
- Offline page/metadata and cached-read fallback behavior may imply offline data behavior.
- Food archive fields are no longer v1 requirements; old archive references are superseded by D-025.
- Current Food model/schema still uses serving-based fields and lacks the D-025 per-100g/per-100ml default-unit model.
- Current Foods UI uses list-page form behavior and lacks standalone `/foods/new`, `/foods/:id`, and `/foods/:id/edit` pages.
- Current Food delete hard deletes but needs confirmation, permanent-delete copy, and snapshot-after-delete verification.
- Gram Diary logging and quantity-only edit UI are missing.
- D-021 Diary `log_mode` storage/API contract is missing.
- Diary entry delete confirmation may be missing.
- Duplicate-submit, stale item, retry, and minimum accessibility behavior need implementation alignment.
- Food `serving_grams` assumptions are superseded by D-025 default-unit requirements.
- Long food name two-line truncation needs implementation/verification.

These are not v1 requirements; they are implementation alignment items to address after BA approval.

## Readiness

BA readiness for another QA audit: Ready.

Implementation planning readiness: Ready from a BA standpoint. Current code contradictions remain implementation alignment items, not unresolved BA decisions.

QA test case generation readiness: Existing QA test cases must be updated before execution because Food archive/inactive and serving-based Food assumptions are superseded by D-024/D-025.
