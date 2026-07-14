# Traceability Audit

Sources:
- `docs/ba/10_TRACEABILITY_MATRIX.md`
- `docs/ba/01_FEATURE_MAP.md`
- Current codebase

## Overall Traceability Verdict

Traceability is mostly good. Major v1 requirements map to user stories, acceptance criteria sections, validation rules, code areas, and test types.

Remaining traceability gaps are small but important:
- Health endpoint and environment config are in the feature map but not traced to stories.
- Offline page and metadata copy still promise offline/sync behavior but are not explicitly listed as implementation alignment evidence.
- Current cached-read fallbacks are not separated from write-queue alignment items.
- Gram-mode API/storage contract cannot be fully traced because it is not final.

## Traceability Findings

| Finding | Severity | Evidence | Issue | Recommended fix |
|---|---|---|---|---|
| TR-001 | High | `04_FIELD_DICTIONARY.md`, `10_TRACEABILITY_MATRIX.md`, `backend/app/schemas.py`, `frontend/lib/types.ts` | Gram-mode Diary contract is not traceable to final schema/API fields. | Add decision and trace rows for serving-mode and gram-mode payloads. |
| TR-002 | Medium | `frontend/app/offline/page.tsx`, `frontend/app/layout.tsx`, `11_REQUIREMENTS_GAPS.md` | Offline/sync user-facing copy exists in code but is not called out in BA alignment items. | Add these files as implementation alignment evidence. |
| TR-003 | Medium | `frontend/components/ProfilePage.tsx`, `FoodsPage.tsx`, `DiaryPage.tsx`, `frontend/lib/db.ts` | Cached read fallbacks are not individually listed as online-read alignment issues. | Add read-cache fallback alignment row. |
| TR-004 | Low | `backend/app/api/routes/health.py`, `01_FEATURE_MAP.md` | Health endpoint has no user story/trace row. | Add technical story or mark no user story required. |
| TR-005 | Low | `backend/app/core/config.py`, `01_FEATURE_MAP.md` | Environment config has no user story/trace row. | Add technical story or mark no user story required. |

## Evidence Confidence

| Area | Confidence | Reason |
|---|---|---|
| Offline/sync current-code contradictions | High | Direct evidence in `db.ts`, `SyncStatus.tsx`, `/sync`, service worker, offline page. |
| Food archive code gap | High | Food model/migration lacks `is_active` and `archived_at`; service hard deletes. |
| Duplicate food code gap | High | No service/schema/DB check found. |
| Gram Diary code gap | High | Current schemas/types only expose serving `quantity`. |
| BA decision closure | High | D-001 through D-020 are present; open questions list says none. |

## Traceability Matrix Summary

| Requirement group | Traceability quality | Notes |
|---|---|---|
| Product decisions | Strong | D-001 through D-020 linked across BA files. |
| Feature map to stories | Good | Most features mapped; infra features need cleanup. |
| Fields to validation | Good | Field dictionary and validation rules align well. |
| Stories to acceptance criteria | Good | Most stories have Given/When/Then. |
| Stories to tests | Medium | Test type guidance exists, but concrete test data matrix is missing. |
| Code alignment evidence | Medium | Main gaps documented; offline page/metadata and cached reads need added evidence. |
