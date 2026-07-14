# Superseded Historical Decisions

Audit date: 2026-07-14

## 1. Purpose

This register prevents older planning assumptions from being mistaken for current product requirements. It is based on explicit supersession in `docs/ba/13_PRODUCT_DECISIONS.md`, later approved implementation direction, and the actual current system.

The separately named v1.1 decision register is not available. Items labeled **formalization required** must be confirmed in that register rather than treated as silently settled.

## 2. Explicitly Superseded BA Decisions

| Historical decision | Superseded by | Current rule | Evidence |
|---|---|---|---|
| D-003 archive/conditional delete lifecycle | D-025 | Food deletion is permanent hard delete | Product decision text; `delete_food()` calls `session.delete`; no archive fields |
| D-004 `is_active`/`archived_at` model | D-025 | No archive/inactive state exists | Current model and PostgreSQL schema |
| D-005 archived Foods in duplicate checks | D-006/D-025 | Duplicate checks inspect current rows only; a deleted Food can be recreated | Food service and tests |
| D-014 older delete-confirmation wording | D-025 in part | Accessible confirmation for permanent deletion | `FoodDeleteDialog.tsx` and Playwright delete tests |
| D-019 `serving_grams` as Food model/source | D-024/D-025 | Per-100g/per-100ml values plus default-unit fields | Migration `0002`, model, schemas, Food UI |

## 3. Superseded System Plan Assumptions

`docs/1-SYSTEM-PLAN.md` describes an earlier product. The following statements must not drive new implementation.

| Historical assumption | Current status | Current rule/evidence |
|---|---|---|
| Offline-first PWA | Superseded | D-001 makes v1 online-only; `/sync`, Dexie, mutation queue, and SyncStatus are removed in the worktree |
| Next.js + FastAPI described as offline-first | Superseded | API/TanStack Query is the runtime source of truth; failed writes are not queued |
| Food nutrition stored per serving | Superseded | D-025 and migration `0002` use per-100g/per-100ml source data |
| `serving_label`/`serving_grams` are current Food fields | Superseded | Removed by `0002`; retained only as nullable legacy snapshot compatibility fields |
| Default protein is 1.8 g/kg | Superseded for new defaults | Current new-profile default is 1.2; existing saved values remain compatible |
| Fixed fat default is 25% for everyone | Superseded for new defaults | Male 25%, female 30% when omitted/new/restored |
| Meal type deferred to v2 | Superseded | Current migration/model/API/UI implement breakfast/lunch/dinner/snack/unspecified |
| Vitamins/minerals excluded | Superseded | Food schema includes optional minerals/vitamins; Wave 1 tracks six priority nutrients |
| Offline reads and writes are delivery phases | Superseded | Online-only v1; no local personal-data source or mutation queue |

## 4. Superseded Architecture Document Assumptions

`docs/2-ARCHITECTURE-SERVICES.md` is not an accurate current architecture description in these areas:

| Historical architecture statement | Current disposition |
|---|---|
| Frontend owns Dexie local store | Superseded; `frontend/lib/db.ts` is deleted in the worktree |
| `/sync` is a current API service | Superseded; route file deleted and router registration removed |
| Sync UI is part of the shell | Superseded; component deleted and provider no longer renders it |
| Offline mutation queue bridges Dexie and API | Superseded; writes only update UI after API success |
| Daily aggregation is mirrored from Dexie | Superseded as an offline architecture; current UI sums server-returned snapshot totals |
| Cached targets support offline operation | Superseded; Profile targets come from online API responses |
| Snapshot is per-serving-only | Superseded; snapshots carry per-basis/default-unit source plus calculated totals |

The service worker itself is not fully removed. It is restricted to same-origin shell/page paths and does not intercept backend API requests. That shell-only behavior is allowed by D-002, subject to dedicated PWA verification.

## 5. Later Direction That Needs Formal Decision Registration

These are implemented or repeatedly approved in later work, but the current BA decision file does not fully record their supersession.

| Earlier rule | Later/current rule | Audit disposition |
|---|---|---|
| D-010 quantity-only Diary edit | Quantity plus meal type can be edited; Food/date/snapshot cannot | Treat old edit scope as superseded, but add a formal decision entry |
| D-025 list presents per-100 values as primary | Foods list is serving-first while details expose serving and per-100 modes | Model rule is preserved; list presentation subclause is superseded and should be recorded |
| D-022 exact Profile/Diary read copy | Newer UX uses shorter contextual messages in Profile/Diary | Unresolved until the missing register confirms the copy change |
| Flat Diary entries | Four meal sections plus conditional legacy unspecified | Implemented through migration `0003`; formal product decision should be versioned |
| Old Profile form/default presentation | Settings-style page, server preview, sex-aware defaults | Implemented; default and preview decisions should be in the register |

## 6. Not Superseded

The following remain authoritative and must not be removed while reconciling Wave 1:

- Mifflin-St Jeor server calculation.
- Current activity factors and goal factors.
- Current rounding order.
- Food per-100g/per-100ml source of truth.
- Derived serving display rather than derived serving database columns.
- Permanent Food hard delete.
- Frozen Diary nutrition snapshots.
- Sunday-first Gregorian Diary navigation.
- Western numerals in Arabic UI.
- Single-profile, personal-use scope.
- Online-only runtime.
- No Food photos.
- No health/Food-quality score.

## 7. Unresolved, Not Superseded

The following contradictions must not be mislabeled as superseded without the missing governing source:

1. **D-007/D-021 gram logging**: the BA decision says required for v1, while multiple later UI scopes explicitly defer gram mode and current API is serving-only.
2. **D-009 age bounds**: the decision requires 10-100; current schema does not enforce it.
3. **D-012 Profile ranges**: decision values and current schema values differ.
4. **D-022 exact error copy**: current UX text differs for Profile and Diary.
5. **Negative carbohydrate handling**: current engine clamps and exposes a flag, while approved expansion language says invalid configurations must not be silently accepted.

## 8. Documentation Reconciliation Required

After product approval, update or formally supersede these documents in a separate documentation change:

- `docs/1-SYSTEM-PLAN.md`
- `docs/2-ARCHITECTURE-SERVICES.md`
- Contradictory portions of `docs/ba/13_PRODUCT_DECISIONS.md`
- Historical QA rows that still mention archive/inactive fields or gram mode as current acceptance

This audit intentionally does not edit those source documents.
