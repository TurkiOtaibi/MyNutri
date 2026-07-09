# Requirements Gaps

## Critical / High Gaps

| ID | Gap | Severity | Impact | Evidence | Recommended decision |
|---|---|---|---|---|---|
| GAP-001 | Canonical requirements were previously missing under `docs/ba` | High | Teams lacked a single BA source of truth | Previous QA audit; now this package | Treat `docs/ba` as canonical after review |
| GAP-002 | Current code is single-profile, while some planning context references multiple people/profiles | High | Future stories may assume missing data model | `models.Profile`; no `person_id` | Decide whether multi-person is v1 or future |
| GAP-003 | Food delete has no confirmation | High | Accidental food loss | `FoodsPage` delete button calls mutation directly | Add confirmation requirement |
| GAP-004 | Used-food archive/inactive lifecycle missing | High | Used foods can be hard deleted from catalog | No archive field; hard delete service | Add lifecycle field and usage-aware behavior |
| GAP-005 | Food validation and network errors are not clearly displayed | High | Invalid data or failed saves may appear saved because current code can queue locally | Mutation `onError` queues locally | Show validation/connection errors and do not save or queue in v1 |
| GAP-006 | Required food numeric fields default to `0` | High | Missing nutrition can be saved as zero | `emptyFood` defaults | Use empty draft state and field errors |
| GAP-007 | Exact duplicate food handling missing | High | Catalog clutter and wrong selection | No uniqueness/check | Define normalized duplicate rule |
| GAP-008 | Negative net carbs possible | High | Invalid nutrition display | `net_carbs = carb - fiber`; no guard | Enforce `fiber_g <= carb_g` |
| GAP-009 | Gram-based diary logging missing | Medium/High | Weighed foods cannot be logged accurately | No Diary grams field/API | Decide if required before serious use |
| GAP-010 | Custom Arabic field-level errors missing | High | UX and QA cannot verify recovery behavior | No error components/copy | Define Arabic error message matrix |

## Medium Gaps

| ID | Gap | Impact | Recommended fix |
|---|---|---|---|
| GAP-011 | `serving_grams=0` UI/backend mismatch | Confusing save failure | Align UI min with backend `> 0` |
| GAP-012 | Diary delete has no confirmation | Accidental entry deletion | Add confirmation or undo decision |
| GAP-013 | Backend diary update API has no UI story | Hidden behavior may drift | Decide if edit diary entry is in scope |
| GAP-014 | Profile future birth date not ruled out | Incorrect age/targets possible | Define date bounds |
| GAP-015 | Diary future date policy missing | Users can log future meals without decision | Define allowed date range |
| GAP-016 | Offline/sync code exists but is removed from v1 scope | Current behavior can conflict with online-only requirements | Remove, disable, or defer sync queue behavior for v1 |
| GAP-017 | Local cached personal data must not be source of truth | Stale personal data may be shown as current | Ensure v1 loads fresh API data or shows connection errors |
| GAP-018 | Loading/empty/error/no-results states inconsistent | User confusion | Define state-specific UX for each page |
| GAP-019 | Accessibility criteria incomplete | Screen reader/keyboard gaps | Define a11y acceptance criteria |
| GAP-020 | Mobile safe-area and fixed-widget overlap unclear | Mobile discomfort around install/connection UI | Define mobile safe-area behavior |
| GAP-021 | No max text/numeric values | DB errors or unrealistic data possible | Add practical limits |
| GAP-022 | No pagination/large catalog behavior | Performance risk with large personal catalog | Decide threshold/pagination/search-only behavior |

## Test Gaps

| ID | Gap | Current test evidence | Recommended tests |
|---|---|---|---|
| GAP-023 | No direct profile API validation tests | `test_calc.py` only covers calc | API tests for profile GET/PUT/preview |
| GAP-024 | No direct food CRUD/search tests | Existing sync test covers food indirectly but sync is Future Scope | Food API create/list/search/update/delete/validation/network errors |
| GAP-025 | No diary API CRUD validation tests | Snapshot unit test | Diary create/list/week/delete/update API tests |
| GAP-026 | No auth tests | None | Token/no-token tests for protected routers |
| GAP-027 | No frontend component/E2E tests | None | Playwright for main flows |
| GAP-028 | No mobile/RTL visual tests | None | Responsive screenshots and long text cases |
| GAP-029 | No accessibility tests | None | Keyboard, accessible names, error semantics |
| GAP-030 | No online network-error/install-shell tests | None | API unreachable, no local save/queue, optional install shell tests |

## Suggested but Not Confirmed Features

Do not implement without product confirmation:

- Multi-person profiles.
- Brand/category/source fields for foods.
- Recipes.
- Barcode scanning.
- Public food database import.
- Per-100g nutrition mode.
- Meal type.
- Weight trend tracking.
- Historical target snapshots.
- Full admin/user role model.
- Offline-first cache, queued mutations, sync push/pull, pending sync states, stale cache handling, and conflict resolution.
