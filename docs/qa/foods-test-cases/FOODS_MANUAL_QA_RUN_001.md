# Foods v1 Formal Manual QA Run 001

Run ID: `FOODS-MQA-001`
Status: Automation run recorded - defects and manual confirmations pending
Prepared: 2026-07-10
Scope: Foods v1 formal Manual QA execution
Source test suite: `docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv`
Total cases: 153 (`P0`: 85, `P1`: 60, `P2`: 8)

> This is an execution record, not a replacement for the CSV. Execute the Preconditions, Test Data, Steps, and Expected Result from the source CSV for each referenced Test Case ID.

## 1. Test Environment

| Item | Required value | Execution value / evidence |
|---|---|---|
| Environment | Local development only; no production systems or data |  |
| Operating system | Windows 10 or approved target device OS |  |
| Backend | FastAPI/SQLModel running against local PostgreSQL |  |
| Frontend | Next.js development or production build |  |
| PostgreSQL | 16.14 local service |  |
| Alembic revision | `0002_foods_v1_per_basis` |  |
| Browser matrix | Desktop Chrome latest; Desktop Safari latest; iPhone Safari latest two iOS versions; Android Chrome latest two major versions |  |
| Viewports | 360px, 390px, 430px, 768px, desktop |  |
| Build/commit under test | Record exact SHA or build identifier; do not use an unrecorded working tree |  |
| Tester | Name and date |  |

Safari and iPhone coverage requires a supported Apple device, simulator, or approved remote-device service. Record unavailable platforms as Blocked rather than Pass.

## 2. Database Used

| Item | Value |
|---|---|
| Database | `mynutri_dev` |
| Host | `localhost:5432` |
| Database user | Local development PostgreSQL user; obtain password securely and do not record it here |
| PostgreSQL version | 16.14 |
| Alembic version | `0002_foods_v1_per_basis` |
| Initial rehearsal state | Migration passed; rehearsal artifacts removed; Food and Diary smoke rows cleaned |

Use only the local development database. Before execution, confirm that the database is safe to modify and record retained seed data in the Notes field.

## 3. App URLs

| Surface | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Foods list | `http://localhost:3000/foods` |
| Add Food | `http://localhost:3000/foods/new` |
| Food details | `http://localhost:3000/foods/{id}` |
| Edit Food | `http://localhost:3000/foods/{id}/edit` |
| Backend API | `http://localhost:8000` |
| API documentation | `http://localhost:8000/docs` |

## 4. Execution Prerequisites

- PostgreSQL local service is running and `mynutri_dev` is reachable.
- `DATABASE_URL` is set only in the local execution environment and points to `mynutri_dev`; do not place credentials in this document.
- `python -m alembic current` reports `0002_foods_v1_per_basis`.
- Backend starts successfully from `backend` using `uvicorn app.main:app --reload` and responds on port 8000.
- Frontend dependencies are installed; frontend starts using `npm run dev` and responds on port 3000.
- `NEXT_PUBLIC_API_URL`, when set, points to `http://localhost:8000`.
- A supported authorization/session configuration is available for normal and unauthorized scenarios.
- Browser developer tools or an approved request-interception proxy is available for 401, 404, 422, 5xx, timeout, stale-item, and tampered-payload scenarios.
- Required mobile, tablet, desktop, RTL, mixed-text, Safari, and Android environments are available.
- A screen reader and keyboard-only workflow are available for accessibility cases.
- Defect tracker project and severity rules are available; every failed test receives a Bug ID before sign-off.
- Start from known catalog data. Create test data through the documented steps; do not use production data.
- Capture screenshots, API payloads, response codes, console errors, and database evidence when relevant.

### Result Rules

- Pass: every expected result is observed with no material deviation.
- Fail: at least one expected result is not met. Record the actual result and Bug ID.
- Blocked: the case cannot be executed because of an environment, dependency, device, or upstream defect. Record the blocker and owner.
- Manual Required: the automated portion passed, but a real-device visual, browser-matrix, or assistive-technology check remains.
- Mark exactly one of Pass, Fail, Blocked, or Manual Required for every row.
- Do not mark a case Pass based only on code inspection or a prior automated result.

## 5. Execution Summary

| Priority | Planned | Pass | Fail | Blocked | Manual Required | Not Run |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 85 | 83 | 0 | 0 | 2 | 0 |
| P1 | 60 | 43 | 2 | 0 | 15 | 0 |
| P2 | 8 | 3 | 4 | 0 | 1 | 0 |
| Total | 153 | 129 | 6 | 0 | 18 | 0 |

## 6. P0 Execution - Complete Before P1/P2

### 1. Navigation and page structure - P0 (3)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 001 | `FOOD-TC-001` | Navigation - happy path - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Manually executed visually in the browser. Foods list opened at `/foods`; Add Food opened at `/foods/new`; Food details and Edit opened on their expected dynamic routes. |  | Manual result reported by the user: Pass. Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-001] @p0 navigates list, add, details, and edit routes; artifacts: frontend/test-results/foods-results.json. |
| 002 | `FOOD-TC-002` | UI guard - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Manually executed visually on `/foods/new`. Save, Cancel, and Back actions were available, and no Delete action appeared on the new-Food page. |  | Manual result reported by the user: Pass. Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-002] @p0 add page has save/cancel/back and no delete; artifacts: frontend/test-results/foods-results.json. |
| 003 | `FOOD-TC-003` | UI layout - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Manually executed visually on `/foods`. The Foods list loaded as a browsing/search surface and did not render the large Add Food form inline. |  | Manual result reported by the user: Pass. Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-003] @p0 list page does not contain the Add Food form; artifacts: frontend/test-results/foods-results.json. |

### 2. Food creation - P0 (6)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 004 | `FOOD-TC-036` | Create - happy path - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-036] @p0 creates a valid per_100g Food; artifacts: frontend/test-results/foods-results.json. |
| 005 | `FOOD-TC-037` | Create - happy path - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-037] @p0 creates a valid per_100ml Food; artifacts: frontend/test-results/foods-results.json. |
| 006 | `FOOD-TC-040` | Optional fields - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-040] @p0 blank optional nutrients do not block save; artifacts: frontend/test-results/foods-results.json. |
| 007 | `FOOD-TC-041` | Duplicate submit - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-041] @p0 duplicate click submits one create request; artifacts: frontend/test-results/foods-results.json. |
| 008 | `FOOD-TC-043` | API validation failure - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-043] @p0 structured API field error maps to the Food name; artifacts: frontend/test-results/foods-results.json. |
| 009 | `FOOD-TC-047` | Scope guard - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-047] @p0 source of truth is per-100 and no legacy serving fields appear; artifacts: frontend/test-results/foods-results.json. |

### 3. Field validation - P0 (25)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 010 | `FOOD-TC-048` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-048] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 011 | `FOOD-TC-049` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-049] @p0 API rejects missing nutrition_basis with Arabic field error; artifacts: frontend/test-results/foods-results.json. |
| 012 | `FOOD-TC-050` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-050] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 013 | `FOOD-TC-051` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-051] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 014 | `FOOD-TC-052` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-052] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 015 | `FOOD-TC-053` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-053] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 016 | `FOOD-TC-054` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-054] @p0 API rejects missing default_unit_type with Arabic field error; artifacts: frontend/test-results/foods-results.json. |
| 017 | `FOOD-TC-055` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-055] @p0 required field shows associated Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 018 | `FOOD-TC-056` | Field validation - required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-056] @p0 API rejects missing unit_basis with Arabic field error; artifacts: frontend/test-results/foods-results.json. |
| 019 | `FOOD-TC-058` | Field validation - normalization - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-058] @p0 trims and collapses Food name whitespace; artifacts: frontend/test-results/foods-results.json. |
| 020 | `FOOD-TC-060` | Security/privacy - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-060] @p0 script-like text never executes; artifacts: frontend/test-results/foods-results.json. |
| 021 | `FOOD-TC-061` | Field validation - numeric boundary - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-061] @p0 accepts calories zero and max boundaries; artifacts: frontend/test-results/foods-results.json. |
| 022 | `FOOD-TC-062` | Field validation - invalid number - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-062] @p0 rejects calories negative, malformed, and above max; artifacts: frontend/test-results/foods-results.json. |
| 023 | `FOOD-TC-063` | Field validation - numeric boundary - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-063] @p0 accepts protein_g zero and max boundaries; artifacts: frontend/test-results/foods-results.json. |
| 024 | `FOOD-TC-064` | Field validation - invalid number - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-064] @p0 rejects protein_g negative, malformed, and above max; artifacts: frontend/test-results/foods-results.json. |
| 025 | `FOOD-TC-065` | Field validation - numeric boundary - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-065] @p0 accepts carb_g zero and max boundaries; artifacts: frontend/test-results/foods-results.json. |
| 026 | `FOOD-TC-066` | Field validation - invalid number - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-066] @p0 rejects carb_g negative, malformed, and above max; artifacts: frontend/test-results/foods-results.json. |
| 027 | `FOOD-TC-067` | Field validation - numeric boundary - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-067] @p0 accepts fat_g zero and max boundaries; artifacts: frontend/test-results/foods-results.json. |
| 028 | `FOOD-TC-068` | Field validation - invalid number - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-068] @p0 rejects fat_g negative, malformed, and above max; artifacts: frontend/test-results/foods-results.json. |
| 029 | `FOOD-TC-069` | Field validation - enum tamper - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-069] @p0 rejects tampered nutrition_basis; artifacts: frontend/test-results/foods-results.json. |
| 030 | `FOOD-TC-070` | Field validation - enum - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-070] @p0 rejects tampered default_unit_type; artifacts: frontend/test-results/foods-results.json. |
| 031 | `FOOD-TC-071` | Field validation - numeric boundary - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-071] @p0 validates unit amount boundaries and decimal; artifacts: frontend/test-results/foods-results.json. |
| 032 | `FOOD-TC-072` | Field validation - enum - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-072] @p0 rejects tampered unit_basis; artifacts: frontend/test-results/foods-results.json. |
| 033 | `FOOD-TC-151` | Field validation - tampered select option - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-151] @p0 rejects tampered nutrition_basis; artifacts: frontend/test-results/foods-results.json. |
| 034 | `FOOD-TC-153` | Field validation - whitespace-only required - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-153] @p0 whitespace-only Food name is rejected with Arabic error; artifacts: frontend/test-results/foods-results.json. |

### 4. Optional nutrient validation - P0 (5)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 035 | `FOOD-TC-094` | Cross-field validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-094] @p0 rejects fiber greater than carbs; artifacts: frontend/test-results/foods-results.json. |
| 036 | `FOOD-TC-095` | Cross-field validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-095] @p0 rejects added sugar greater than total sugar; artifacts: frontend/test-results/foods-results.json. |
| 037 | `FOOD-TC-097` | Cross-field validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-097] @p0 rejects saturated fat greater than fat; artifacts: frontend/test-results/foods-results.json. |
| 038 | `FOOD-TC-098` | Cross-field validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-098] @p0 rejects trans fat greater than fat; artifacts: frontend/test-results/foods-results.json. |
| 039 | `FOOD-TC-099` | Cross-field validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-099] @p0 rejects saturated plus trans fat greater than total fat; artifacts: frontend/test-results/foods-results.json. |

### 5. Duplicate handling - P0 (4)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 040 | `FOOD-TC-101` | Duplicate validation - Block Current Catalog Duplicate Food | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/duplicate.spec.ts - [FOOD-TC-101] @p0 blocks exact duplicate and shows Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 041 | `FOOD-TC-102` | Duplicate validation - Block Current Catalog Duplicate Food | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/duplicate.spec.ts - [FOOD-TC-102] @p0 normalizes spaces and English case for duplicate key; artifacts: frontend/test-results/foods-results.json. |
| 042 | `FOOD-TC-104` | Data lifecycle - Block Current Catalog Duplicate Food | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/duplicate.spec.ts - [FOOD-TC-104] @p0 deleted Food can be created again; artifacts: frontend/test-results/foods-results.json. |
| 043 | `FOOD-TC-105` | Edit validation - Block Current Catalog Duplicate Food | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/duplicate.spec.ts - [FOOD-TC-105] @p0 edit cannot collide with another Food; artifacts: frontend/test-results/foods-results.json. |

### 6. Food listing, search, and states - P0 (12)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 044 | `FOOD-TC-008` | List display - desktop - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-008] @p0 desktop table shows approved columns; artifacts: frontend/test-results/foods-results.json. |
| 045 | `FOOD-TC-012` | Scope guard - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-012] @p0 list has no archive/status UI; artifacts: frontend/test-results/foods-results.json. |
| 046 | `FOOD-TC-013` | Data lifecycle - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-013] @p0 hard-deleted Food is absent from list; artifacts: frontend/test-results/foods-results.json. |
| 047 | `FOOD-TC-014` | CRUD action access - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-014] @p0 saved Food exposes View, Edit, and Delete actions; artifacts: frontend/test-results/foods-results.json. |
| 048 | `FOOD-TC-015` | Diary integration - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-015] @p0 current Food appears in future Diary selection; artifacts: frontend/test-results/foods-results.json. |
| 049 | `FOOD-TC-017` | Search - happy path - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-017] @p0 search finds matching current Food; artifacts: frontend/test-results/foods-results.json. |
| 050 | `FOOD-TC-018` | Search - happy path - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-018] @p0 search finds matching current Food; artifacts: frontend/test-results/foods-results.json. |
| 051 | `FOOD-TC-020` | RTL search - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-020] @p0 search finds matching current Food; artifacts: frontend/test-results/foods-results.json. |
| 052 | `FOOD-TC-022` | No-results state - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-022] @p0 no-results state is shown; artifacts: frontend/test-results/foods-results.json. |
| 053 | `FOOD-TC-024` | Data lifecycle - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-024] @p0 deleted Food is absent from search; artifacts: frontend/test-results/foods-results.json. |
| 054 | `FOOD-TC-027` | Loading state - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-027] @p0 loading state is visible while Foods request is pending; artifacts: frontend/test-results/foods-results.json. |
| 055 | `FOOD-TC-028` | Empty state - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-028] @p0 empty catalog state links to Add Food; artifacts: frontend/test-results/foods-results.json. |

### 7. Food details - P0 (1)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 056 | `FOOD-TC-128` | Details - happy path - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-128] @p0 details show full core, optional, and metadata values; artifacts: frontend/test-results/foods-results.json. |

### 8. Food editing - P0 (4)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 057 | `FOOD-TC-106` | Edit - happy path - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-106] @p0 edit form loads current values; artifacts: frontend/test-results/foods-results.json. |
| 058 | `FOOD-TC-107` | Edit - happy path - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-107] @p0 valid edit saves and appears in details; artifacts: frontend/test-results/foods-results.json. |
| 059 | `FOOD-TC-109` | Edit validation - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-109] @p0 invalid edit is blocked and persisted Food is unchanged; artifacts: frontend/test-results/foods-results.json. |
| 060 | `FOOD-TC-115` | Diary integration - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-115] @p0 old Diary snapshot does not change after Food edit; artifacts: frontend/test-results/foods-results.json. |

### 9. Food deletion - P0 (5)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 061 | `FOOD-TC-118` | Delete confirmation - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-118] @p0 confirmation dialog shows Food name and permanent wording; artifacts: frontend/test-results/foods-results.json. |
| 062 | `FOOD-TC-119` | Delete cancel - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-119] @p0 cancel closes dialog and keeps Food; artifacts: frontend/test-results/foods-results.json. |
| 063 | `FOOD-TC-120` | Delete - happy path - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-120] @p0 confirm permanently deletes Food; artifacts: frontend/test-results/foods-results.json. |
| 064 | `FOOD-TC-121` | Diary integration - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-121] @p0 deleted Food disappears from future Diary selection; artifacts: frontend/test-results/foods-results.json. |
| 065 | `FOOD-TC-125` | Scope guard - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-125] @p0 delete uses no archive/inactive state; artifacts: frontend/test-results/foods-results.json. |

### 10. Diary snapshot safety after Food deletion - P0 (1)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 066 | `FOOD-TC-122` | Data integrity - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/snapshot.spec.ts - [FOOD-TC-122] @p0 historical Diary entry survives Food hard delete; artifacts: frontend/test-results/foods-results.json. |

### 11. Mobile and RTL - P0 (1)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 067 | `FOOD-TC-009` | List display - mobile - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-009] @p0 @mobile mobile uses cards with core Food values; artifacts: frontend/test-results/foods-results.json. |

### 12. Accessibility basics - P0 (1)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 068 | `FOOD-TC-126` | Accessibility - Permanently Delete Food With Confirmation | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-126] @p0 @a11y dialog supports focus, Escape, and focus restoration; artifacts: frontend/test-results/foods-results.json. |

### 13. Online-only and API failure behavior - P0 (17)

| Run Seq | Test Case ID | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
| 069 | `FOOD-TC-007` | Permission/access - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-007] @p0 unauthorized Foods read exposes no catalog data; artifacts: frontend/test-results/foods-results.json. |
| 070 | `FOOD-TC-025` | Network/API failure - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-025] @p0 search read failure shows Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 071 | `FOOD-TC-030` | Read failure - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry; artifacts: frontend/test-results/foods-results.json. |
| 072 | `FOOD-TC-032` | Read failure - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-032][FOOD-TC-131] @p0 detail read failure shows exact Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 073 | `FOOD-TC-033` | Read failure - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-033] @p0 edit read failure prevents editable form; artifacts: frontend/test-results/foods-results.json. |
| 074 | `FOOD-TC-042` | Network/API failure - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-042] @p0 network failure preserves the draft and creates no Food; artifacts: frontend/test-results/foods-results.json. |
| 075 | `FOOD-TC-045` | Permission/access - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-045] @p0 unauthorized create is not treated as saved; artifacts: frontend/test-results/foods-results.json. |
| 076 | `FOOD-TC-110` | Network/API failure - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-110] @p0 failed edit preserves input; artifacts: frontend/test-results/foods-results.json. |
| 077 | `FOOD-TC-111` | Permission/access - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-111] @p0 unauthorized edit is rejected; artifacts: frontend/test-results/foods-results.json. |
| 078 | `FOOD-TC-112` | Stale item edge - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-112] @p0 stale deleted Food cannot be edited; artifacts: frontend/test-results/foods-results.json. |
| 079 | `FOOD-TC-123` | Network/API failure - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-123] @p0 failed delete keeps Food and queues nothing; artifacts: frontend/test-results/foods-results.json. |
| 080 | `FOOD-TC-127` | Permission/access - Permanently Delete Food With Confirmation | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-127] @p0 unauthorized delete leaves Food unchanged; artifacts: frontend/test-results/foods-results.json. |
| 081 | `FOOD-TC-131` | Network/API failure - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-032][FOOD-TC-131] @p0 detail read failure shows exact Arabic error; artifacts: frontend/test-results/foods-results.json. |
| 082 | `FOOD-TC-132` | Stale item edge - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-132] @p0 deleted detail route shows not-found/read error; artifacts: frontend/test-results/foods-results.json. |
| 083 | `FOOD-TC-134` | Permission/access - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-134] @p0 unauthorized detail exposes no Food data; artifacts: frontend/test-results/foods-results.json. |
| 084 | `FOOD-TC-137` | Online-only scope - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/online-only.spec.ts - [FOOD-TC-137] @p0 API read failure does not use local personal data; artifacts: frontend/test-results/foods-results.json. |
| 085 | `FOOD-TC-138` | Online-only scope - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/online-only.spec.ts - [FOOD-TC-138] @p0 failed write is not saved or queued offline; artifacts: frontend/test-results/foods-results.json. |


### P0 Gate

Do not begin P1/P2 execution until every P0 case is Pass, or each remaining P0 Fail/Blocked result has an explicit QA Lead and Product Owner disposition. Critical or High unresolved P0 defects force No-Go.

## 7. P1/P2 Execution - Start After P0 Gate

### 1. Navigation and page structure - P1/P2 (2 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 086 | `FOOD-TC-004` | P1 | Edit page structure - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-004] @p1 edit reuses grouped Add Food structure; artifacts: frontend/test-results/foods-results.json. |
| 087 | `FOOD-TC-006` | P1 | Navigation - cancel - Use Standalone Food Pages | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-006] @p1 cancel returns without saving; artifacts: frontend/test-results/foods-results.json. |

### 2. Food creation - P1/P2 (2 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 088 | `FOOD-TC-038` | P1 | Form UX - Create Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-038] @p1 form has the approved grouped sections; artifacts: frontend/test-results/foods-results.json. |
| 089 | `FOOD-TC-039` | P1 | Form UX - Create Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-039] @p1 optional nutrients are collapsed by default; artifacts: frontend/test-results/foods-results.json. |

### 3. Field validation - P1/P2 (4 P1, 7 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 090 | `FOOD-TC-057` | P1 | Field validation - characters - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-057] @p1 accepts an Arabic Food name; artifacts: frontend/test-results/foods-results.json. |
| 091 | `FOOD-TC-059` | P1 | Field validation - max length - Create Food on Standalone Page | [ ] | [x] | [ ] | [ ] | API returned 201 for a 121-character Food name; expected 422. | BUG-FOODS-AUTO-002 | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-059] @p1 enforces Food name max 120; artifacts: frontend/test-results/foods-results.json. |
| 092 | `FOOD-TC-142` | P1 | Legacy field mapping - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-142] @p1 sugar_g is total sugar and legacy field is not user-facing; artifacts: frontend/test-results/foods-results.json. |
| 093 | `FOOD-TC-143` | P1 | Field validation - decimal number - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-143] @p1 accepts decimal calories; artifacts: frontend/test-results/foods-results.json. |
| 094 | `FOOD-TC-073` | P2 | Field validation - optional text - Create Food on Standalone Page | [ ] | [x] | [ ] | [ ] | API returned 201 for an 81-character brand; expected 422. | BUG-FOODS-AUTO-003 | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-073] @p2 validates brand language and max length; artifacts: frontend/test-results/foods-results.json. |
| 095 | `FOOD-TC-074` | P2 | Field validation - optional text - Create Food on Standalone Page | [ ] | [x] | [ ] | [ ] | API returned 201 for an 81-character category; expected 422. | BUG-FOODS-AUTO-004 | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-074] @p2 validates category language and max length; artifacts: frontend/test-results/foods-results.json. |
| 096 | `FOOD-TC-075` | P2 | Field validation - optional text base behavior - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-075] @p2 blank optional text is allowed and HTML stays inert; artifacts: frontend/test-results/foods-results.json. |
| 097 | `FOOD-TC-147` | P2 | Field validation - optional text language - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-147] @p2 brand accepts Arabic, English, mixed text, and punctuation; artifacts: frontend/test-results/foods-results.json. |
| 098 | `FOOD-TC-148` | P2 | Field validation - optional text language - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-148] @p2 category accepts Arabic, English, mixed text, and punctuation; artifacts: frontend/test-results/foods-results.json. |
| 099 | `FOOD-TC-149` | P2 | Field validation - optional text max - Create Food on Standalone Page | [ ] | [x] | [ ] | [ ] | API returned 201 for 501-character notes; expected 422. | BUG-FOODS-AUTO-005 | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-149] @p2 validates notes language and max length; artifacts: frontend/test-results/foods-results.json. |
| 100 | `FOOD-TC-150` | P2 | Field validation - optional text max - Create Food on Standalone Page | [ ] | [x] | [ ] | [ ] | API returned 201 for a 121-character data source; expected 422. | BUG-FOODS-AUTO-006 | Automation: frontend/e2e/foods/validation.spec.ts - [FOOD-TC-150] @p2 validates data_source language and max length; artifacts: frontend/test-results/foods-results.json. |

### 4. Optional nutrient validation - P1/P2 (24 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 101 | `FOOD-TC-076` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-076] @p1 validates optional fiber_g blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 102 | `FOOD-TC-077` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-077] @p1 validates optional sugar_g blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 103 | `FOOD-TC-078` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-078] @p1 validates optional added_sugar_g blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 104 | `FOOD-TC-079` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-079] @p1 validates optional saturated_fat_g blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 105 | `FOOD-TC-080` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-080] @p1 validates optional trans_fat_g blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 106 | `FOOD-TC-081` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-081] @p1 validates optional cholesterol_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 107 | `FOOD-TC-082` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-082] @p1 validates optional sodium_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 108 | `FOOD-TC-083` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-083] @p1 validates optional potassium_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 109 | `FOOD-TC-084` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-084] @p1 validates optional calcium_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 110 | `FOOD-TC-085` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-085] @p1 validates optional iron_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 111 | `FOOD-TC-086` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-086] @p1 validates optional magnesium_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 112 | `FOOD-TC-087` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-087] @p1 validates optional zinc_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 113 | `FOOD-TC-088` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-088] @p1 validates optional vitamin_d_mcg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 114 | `FOOD-TC-089` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-089] @p1 validates optional vitamin_b12_mcg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 115 | `FOOD-TC-090` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-090] @p1 validates optional vitamin_c_mg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 116 | `FOOD-TC-091` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-091] @p1 validates optional vitamin_a_mcg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 117 | `FOOD-TC-092` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-092] @p1 validates optional folate_mcg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 118 | `FOOD-TC-093` | P1 | Field validation - optional nutrient - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-093] @p1 validates optional vitamin_k_mcg blank, zero, max, negative, and above max; artifacts: frontend/test-results/foods-results.json. |
| 119 | `FOOD-TC-096` | P1 | Cross-field edge - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-096] @p1 permits added sugar when total sugar is blank; artifacts: frontend/test-results/foods-results.json. |
| 120 | `FOOD-TC-100` | P1 | UX validation - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-100] @p1 invalid optional nutrient opens section and associates error; artifacts: frontend/test-results/foods-results.json. |
| 121 | `FOOD-TC-144` | P1 | Field validation - optional nutrient decimals - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-144] @p1 accepts decimal gram nutrients; artifacts: frontend/test-results/foods-results.json. |
| 122 | `FOOD-TC-145` | P1 | Field validation - optional mineral decimals - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-145] @p1 accepts decimal minerals; artifacts: frontend/test-results/foods-results.json. |
| 123 | `FOOD-TC-146` | P1 | Field validation - optional vitamin decimals - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-146] @p1 accepts decimal vitamins; artifacts: frontend/test-results/foods-results.json. |
| 124 | `FOOD-TC-152` | P1 | Field validation - API error mapping - Validate Optional Nutrient Ranges | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/optional-nutrients.spec.ts - [FOOD-TC-152] @p1 structured optional nutrient errors identify the field; artifacts: frontend/test-results/foods-results.json. |

### 5. Duplicate handling - P1/P2 (1 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 125 | `FOOD-TC-103` | P1 | Duplicate validation - Block Current Catalog Duplicate Food | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/duplicate.spec.ts - [FOOD-TC-103] @p1 brand and category do not change duplicate identity; artifacts: frontend/test-results/foods-results.json. |

### 6. Food listing, search, and states - P1/P2 (7 P1, 1 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 126 | `FOOD-TC-010` | P1 | List content - Browse Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-010] @p1 main list omits optional micronutrients; artifacts: frontend/test-results/foods-results.json. |
| 127 | `FOOD-TC-016` | P1 | RTL display - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-016] @p1 mixed Arabic/English list text remains RTL-readable; artifacts: frontend/test-results/foods-results.json. |
| 128 | `FOOD-TC-019` | P1 | Search edge - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-019] @p1 search finds matching current Food; artifacts: frontend/test-results/foods-results.json. |
| 129 | `FOOD-TC-021` | P1 | Search normalization - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-021] @p1 search trims whitespace; artifacts: frontend/test-results/foods-results.json. |
| 130 | `FOOD-TC-023` | P1 | Search reset - Search Current Food Catalog | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-023] @p1 clearing search restores full catalog; artifacts: frontend/test-results/foods-results.json. |
| 131 | `FOOD-TC-029` | P1 | State distinction - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-029] @p1 no-results differs from empty catalog state; artifacts: frontend/test-results/foods-results.json. |
| 132 | `FOOD-TC-141` | P1 | Unsupported filters absence - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-141] @p1 unsupported archive/sort/filter controls are absent; artifacts: frontend/test-results/foods-results.json. |
| 133 | `FOOD-TC-140` | P2 | Performance-risk - Create Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-140] @p2 renders a 200-Food catalog without broken layout; artifacts: frontend/test-results/foods-results.json. |

### 7. Food details - P1/P2 (3 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 134 | `FOOD-TC-129` | P1 | Details edge - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-129] @p1 details handle blank optional nutrients without errors; artifacts: frontend/test-results/foods-results.json. |
| 135 | `FOOD-TC-130` | P1 | Details UI - View Food Details | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-130] @p1 long full name is visible on details; artifacts: frontend/test-results/foods-results.json. |
| 136 | `FOOD-TC-133` | P1 | Details actions - View Food Details | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-133] @p1 details expose Edit and Delete actions; artifacts: frontend/test-results/foods-results.json. |

### 8. Food editing - P1/P2 (3 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 137 | `FOOD-TC-108` | P1 | Edit edge - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-108] @p1 unchanged edit remains valid; artifacts: frontend/test-results/foods-results.json. |
| 138 | `FOOD-TC-114` | P1 | Edit cancel - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-114] @p1 cancel edit persists no changes; artifacts: frontend/test-results/foods-results.json. |
| 139 | `FOOD-TC-117` | P1 | Edit validation - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-117] @p1 cross-field-invalid edit is blocked; artifacts: frontend/test-results/foods-results.json. |

### 9. Food deletion - P1/P2 (1 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 140 | `FOOD-TC-124` | P1 | Duplicate submit - Permanently Delete Food With Confirmation | [ ] | [x] | [ ] | [ ] | Double-clicking permanent delete sent two DELETE requests; expected one. | BUG-FOODS-AUTO-001 | Automation: frontend/e2e/foods/delete.spec.ts - [FOOD-TC-124] @p1 repeated confirm sends one delete request; artifacts: frontend/test-results/foods-results.json. |

### 11. Mobile and RTL - P1/P2 (7 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 141 | `FOOD-TC-005` | P1 | Mobile UX - Use Standalone Food Pages | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/navigation.spec.ts - [FOOD-TC-005] @p1 @mobile standalone pages fit a 360px viewport; artifacts: frontend/test-results/foods-results.json. |
| 142 | `FOOD-TC-011` | P1 | Mobile/RTL edge - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-011] @p1 @mobile long names clamp to two lines without overflow; artifacts: frontend/test-results/foods-results.json. |
| 143 | `FOOD-TC-026` | P1 | Mobile UX - Search Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-026] @p1 @mobile search remains usable at 360px; artifacts: frontend/test-results/foods-results.json. |
| 144 | `FOOD-TC-034` | P1 | Mobile UX - Show Food Loading, Empty, No-Results, and Read-Failure States | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-034] @p1 @mobile state messages do not overflow; artifacts: frontend/test-results/foods-results.json. |
| 145 | `FOOD-TC-046` | P1 | Mobile UX - Create Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-046] @p1 @mobile Add Food is usable at 390px; artifacts: frontend/test-results/foods-results.json. |
| 146 | `FOOD-TC-116` | P1 | Mobile/RTL - Edit Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-116] @p1 @mobile edit supports RTL mixed text without overflow; artifacts: frontend/test-results/foods-results.json. |
| 147 | `FOOD-TC-139` | P1 | Mobile/responsive - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/mobile-rtl-a11y.spec.ts - [FOOD-TC-139] @p1 @mobile required viewport matrix has no horizontal page overflow; artifacts: frontend/test-results/foods-results.json. |

### 12. Accessibility basics - P1/P2 (3 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 148 | `FOOD-TC-035` | P1 | Accessibility - Show Food Loading, Empty, No-Results, and Read-Failure States | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-035] @p1 @a11y read failure is exposed as an alert; artifacts: frontend/test-results/foods-results.json. |
| 149 | `FOOD-TC-135` | P1 | Accessibility - Create Food on Standalone Page | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/mobile-rtl-a11y.spec.ts - [FOOD-TC-135] @p1 @a11y field errors are associated with invalid inputs; artifacts: frontend/test-results/foods-results.json. |
| 150 | `FOOD-TC-136` | P1 | Accessibility - Browse Current Food Catalog | [ ] | [ ] | [ ] | [x] | Automated assertions passed; formal visual/device/accessibility confirmation remains. |  | Automation: frontend/e2e/foods/mobile-rtl-a11y.spec.ts - [FOOD-TC-136] @p1 @a11y icon actions have contextual accessible names; artifacts: frontend/test-results/foods-results.json. |

### 13. Online-only and API failure behavior - P1/P2 (3 P1, 0 P2)

| Run Seq | Test Case ID | Priority | Test reference | Pass | Fail | Blocked | Manual Required | Actual result | Bug ID | Notes |
|---:|---|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 151 | `FOOD-TC-031` | P1 | Retry behavior - Show Food Loading, Empty, No-Results, and Read-Failure States | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/list-search-states.spec.ts - [FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry; artifacts: frontend/test-results/foods-results.json. |
| 152 | `FOOD-TC-044` | P1 | API failure - Create Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/create.spec.ts - [FOOD-TC-044] @p1 server failure preserves entered data; artifacts: frontend/test-results/foods-results.json. |
| 153 | `FOOD-TC-113` | P1 | Conflict edge - Edit Food on Standalone Page | [x] | [ ] | [ ] | [ ] | Playwright execution passed against the local app and PostgreSQL-backed API. |  | Automation: frontend/e2e/foods/details-edit.spec.ts - [FOOD-TC-113] @p1 conflict response preserves edit draft; artifacts: frontend/test-results/foods-results.json. |


## 8. Defect Summary

| Bug ID | Test Case ID(s) | Severity | Summary | Status | Owner | Retest result |
|---|---|---|---|---|---|---|
| `BUG-FOODS-AUTO-001` | `FOOD-TC-124` | Medium | Repeated delete confirmation sends two DELETE requests. | Open | Frontend | Failed |
| `BUG-FOODS-AUTO-002` | `FOOD-TC-059` | High | Food name maximum length is not enforced by the API. | Open | Backend | Failed |
| `BUG-FOODS-AUTO-003` | `FOOD-TC-073` | Medium | Brand maximum length is not enforced by the API. | Open | Backend | Failed |
| `BUG-FOODS-AUTO-004` | `FOOD-TC-074` | Medium | Category maximum length is not enforced by the API. | Open | Backend | Failed |
| `BUG-FOODS-AUTO-005` | `FOOD-TC-149` | Medium | Notes maximum length is not enforced by the API. | Open | Backend | Failed |
| `BUG-FOODS-AUTO-006` | `FOOD-TC-150` | Medium | Data source maximum length is not enforced by the API. | Open | Backend | Failed |

Severity guidance: Critical includes data loss, broken primary Foods flow, privacy/security exposure, or unsafe hard deletion. High includes blocked create/edit/delete, invalid nutrition data being accepted, broken snapshot safety, or unusable required mobile/RTL behavior.

## 9. Go / No-Go Criteria

### Go

- All 153 cases have exactly one final result.
- All 85 P0 cases pass after any required retest.
- No unresolved Critical or High defects remain.
- Food create, edit, detail, search, list, and permanent delete flows pass against `mynutri_dev`.
- D-026 field boundaries and cross-field nutrition validations pass with the approved Arabic messages.
- Duplicate blocking and duplicate-submit protection pass.
- Deleted Foods disappear from list, search, and future Diary selection.
- Historical Diary entries remain readable and accurate from snapshots after Food deletion.
- Online-only read/write failures pass with no local save, offline queue, pending-sync state, or cached personal-data source of truth.
- Required mobile viewport, RTL/mixed-text, keyboard, dialog, form-error, and accessible-name checks pass or have an explicitly approved non-release-blocking exception.
- PostgreSQL migration and schema evidence remain valid for the build under test.

### No-Go

- Any P0 case remains Failed or Blocked without written disposition.
- Any Critical or High defect remains unresolved.
- Permanent delete occurs without confirmation, deletes historical Diary readability, or behaves as archive/inactive.
- Invalid nutrition data, duplicate Foods, or whitespace-only names can be saved.
- Failed writes are shown as successful, stored locally, or queued for later sync.
- Arabic validation/error copy is missing, corrupted, raw server text, or mapped to the wrong field on a core flow.
- Required Foods routes, PostgreSQL schema, API behavior, or mobile/RTL primary flows are unavailable.

## 10. Final QA Sign-Off

| Sign-off item | Value |
|---|---|
| Final execution date |  |
| Build/commit tested |  |
| Tester |  |
| QA Lead |  |
| Product Owner disposition |  |
| Total Pass |  |
| Total Fail |  |
| Total Blocked |  |
| Critical defects open |  |
| High defects open |  |
| Final decision | Go / No-Go |
| Conditions or accepted risks |  |

QA Lead signature: ____________________  Date: __________
Product Owner signature: ______________  Date: __________

## 11. Source Evidence

- `docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv`
- `docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATION_SUMMARY.md`
- `docs/qa/foods-test-cases/FOODS_FIELD_COVERAGE_FINAL_FIX_SUMMARY.md`
- `docs/implementation/03_FOODS_PAGE_UPDATE_REPORT.md`
- `docs/implementation/07_POSTGRES_MIGRATION_REHEARSAL_REPORT.md`
