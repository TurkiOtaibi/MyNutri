# Negative Scenario Audit

Source files:
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- Current frontend/backend code.

Overall negative scenario verdict: Partially Ready.

The BA package identifies the right negative scenario categories, but many are still marked Decision Needed, Missing, or current-code-not-aligned.

## Negative Scenario Coverage Summary

| Area | Coverage status | Main issue |
|---|---|---|
| Auth and permissions | Partial | API 401 exists, but UI behavior is missing. |
| Profile validation | Partial | Backend validation exists; future birth date and Arabic messages missing. |
| Food validation | Partial | Many invalid values identified; exact field rules and messages incomplete. |
| Food delete/archive | Not ready | Confirmation, archive model, used-food check, and active filtering missing. |
| Diary create/delete | Partial | Quantity validation exists; network failures and delete confirmation weak. |
| Weekly summary | Partial | Week normalization covered; timezone and network errors unresolved. |
| Online network errors | Partial | Required by BA, but too broad and contradicted by current code. |
| Future offline/sync | Covered as Future Scope | Correctly excluded from v1, but code still exposes it. |
| Mobile/RTL/a11y | Partial | Identified but not precise enough for full test cases. |

## Critical and High Negative Gaps

| ID | Scenario | Severity | Evidence | Gap | Required improvement |
|---|---|---|---|---|---|
| NEG-001 | API unreachable during Profile save | Critical | `ProfilePage.tsx` queues failed save | BA says do not queue; code queues | Add page-specific no-queue story and implementation follow-up. |
| NEG-002 | API unreachable during Food create/edit/delete | Critical | `FoodsPage.tsx` local IndexedDB and `queueMutation` on error | Failed writes can appear locally saved/deleted | Split create/edit/delete write-failure stories. |
| NEG-003 | API unreachable during Diary add/delete | Critical | `DiaryPage.tsx` local diary mutation and queue on error | Diary can change locally after failed API call | Add no-local-entry/no-local-delete criteria. |
| NEG-004 | Server validation rejects write | High | `apiFetch` throws, page handlers use broad `onError` | Invalid data can be queued locally | Require 422 field mapping and no local persistence. |
| NEG-005 | Food delete tapped accidentally | High | `FoodsPage` delete button calls mutation directly | No confirmation or undo | Add confirmation story with cancel behavior. |
| NEG-006 | Delete food used in Diary | High | No archive field; hard delete service | Used food cannot be lifecycle-managed | Define archive/inactive behavior. |
| NEG-007 | Exact duplicate food | High | No service/DB check | Catalog duplicates likely | Resolve duplicate key and archived-food rule. |
| NEG-008 | `fiber_g > carb_g` | High | No validation; net carbs can be negative | Nutrition data becomes invalid | Enforce in frontend/backend with field error. |
| NEG-009 | Gram logging without serving weight | High | `US-DIARY-GRAM-001`; no UI/API | Expected error behavior is not implementable | Define gram mode and disabled/error state. |
| NEG-010 | Future diary date | High | Open question | Users may log future meals without product intent | Decide policy and add criteria. |
| NEG-011 | Auth failure in UI | High | API auth exists; UI state missing | User sees generic failure or stale UI | Add 401-specific UI story. |
| NEG-012 | Service worker returns cached data | High | `service-worker.js` caches GET responses | May conflict with online-only source of truth | Restrict or remove SW behavior for v1. |

## Missing Negative Paths by Feature

| Feature | Missing negative paths |
|---|---|
| Profile | Future birth date, unrealistic height/weight, preview API failure, 401, 422 field mapping, API timeout/5xx. |
| Food create/edit | Whitespace-only text, too-long text, invalid characters if disallowed, blank numeric fields, extreme values, duplicate on edit, `fiber_g > carb_g`, server 422 mapping, network failure with preserved draft. |
| Food delete/archive | Cancel confirmation, used-food archive, unused hard delete, failure during archive/delete, archived food hidden from Diary, archived food duplicate checks. |
| Diary create | Missing food, deleted food, invalid quantity blank/non-number/extreme, future date, API down, 401/404/422/5xx. |
| Diary delete | Confirmation/undo decision, API down, item already deleted, stale list recovery. |
| Weekly summary | API down, timezone boundary, missing profile targets, very large entry list. |
| App shell/PWA | Service worker cache scope, offline navigation messaging, no stale personal data as current. |

## Future Scope Handling

Offline cache, IndexedDB source-of-truth behavior, offline mutation queue, sync push/pull, pending sync states, stale cache behavior, conflict handling, offline writes, and sync rejection handling are correctly marked Future Scope in BA docs.

Remaining issue:
Current code still implements or exposes these behaviors. QA must treat this as a v1 contradiction, not as accepted functionality.

