# Open Questions

The decisions D-001 through D-026 are resolved and must not remain open. This file keeps only unresolved questions outside those decisions.

## Resolved Questions

| Former question | Status | Decision |
|---|---|---|
| How should IndexedDB/sync be handled for v1? | Resolved | D-001 |
| Should service worker stay or be removed? | Resolved with conditional rule | D-002 |
| Should foods hard delete or archive? | Resolved | D-003 |
| Which archive fields should be used? | Resolved | D-004 |
| Should archived foods block duplicates? | Resolved | D-005 |
| What is the exact duplicate key? | Resolved | D-006 |
| Is gram logging required in v1? | Resolved | D-007 |
| Should future diary dates be allowed? | Resolved | D-008 |
| Should future birth dates be blocked and what are age bounds? | Resolved | D-009 |
| Should diary edit be exposed? | Resolved | D-010 |
| What Arabic validation messages should be used? | Resolved | D-011 |
| What max values should be enforced? | Resolved | D-012 |
| What API error mapping should be shared? | Resolved | D-013 |
| What food delete confirmation pattern should be used? | Resolved | D-014 |
| Which browsers/devices are in scope? | Resolved | D-015 |
| Is multi-person/profile support in v1 or Future Scope? | Resolved | D-016 |
| Should profile deletion/reset be supported in v1? | Resolved | D-017 |
| Should diary delete require confirmation? | Resolved | D-018 |
| Should API naming remain `serving_grams` while UI says serving weight/grams? | Resolved | D-019 |
| Should long food names wrap, truncate, or expand? | Resolved | D-020 |
| What exact Diary API/storage contract should gram mode use? | Resolved | D-021 |
| What exact Arabic copy should read failures use? | Resolved | D-022 |
| How should stale items, duplicate submits, retries, and minimum accessibility behavior work? | Resolved | D-023 |
| Should Add Food be inline on `/foods` or a standalone page? | Resolved | D-024 |
| Should Food deletion be archive/inactive or permanent hard delete? | Resolved | D-025 |
| Should Food nutrition values be source-of-truth per serving or per 100g/per 100ml? | Resolved | D-025 |
| Should v1 use Food `is_active`, `archived_at`, archived status, or Active/Archived filters? | Resolved | D-025 |
| What max ranges and cross-field rules should optional Food nutrients use? | Resolved | D-026 |
| How should `sugar_g`, `added_sugar_g`, and legacy `total_sugars_g` map in v1? | Resolved | D-026 |

## Remaining Product Questions

| ID | Question | Owner | Priority | Why it matters | Current recommendation |
|---|---|---|---|---|---|
| None | No remaining v1 product questions after D-001 through D-026. | N/A | N/A | N/A | N/A |

## Resolved Scope Boundaries

The following are not v1 open questions:
- Offline-first behavior.
- Offline writes.
- Sync queue/push/pull.
- Pending sync status.
- Conflict handling.
- Stale cache behavior.
- Sync rejection.
- Future meal planning.
- Brand in duplicate checks.
- Multi-profile support and profile switching.
- Profile reset/delete.
- Diary delete confirmation.
- Serving grams API naming.
- Long food name display behavior.
- Diary gram-mode API/storage contract.
- Exact page-specific Arabic read-failure copy.
- Stale item handling, duplicate-submit prevention, retry behavior, and minimum accessibility behavior.
- Standalone Add Food page structure.
- Permanent Food hard-delete lifecycle.
- Food per-100g/per-100ml source-of-truth model.
- Food archive/inactive state and filters.
- Optional nutrient max ranges and cross-field validation.
- Sugar field mapping: `sugar_g` is total sugar, `added_sugar_g` is added sugar, and `total_sugars_g` is legacy/current-code naming.
