# Foods v1 Automation Run 001

Run ID: `FOODS-AUTO-001`
Date: 2026-07-10
Environment: local only; frontend `http://127.0.0.1:3000`, backend `http://127.0.0.1:8000`, PostgreSQL `mynutri_dev`
Source baseline: `FOODS_TEST_CASES_REGENERATED.csv`

## 1. Playwright Setup Status

- Playwright Test `1.61.1` and Chromium are installed in `frontend`.
- Tests refuse non-local frontend or API hosts.
- The final run used the successful production Next.js build because the Turbopack dev server did not hydrate client components in this environment and its HMR WebSocket failed.
- Service workers are blocked in the Playwright context. Online-only behavior is tested directly through API interception and IndexedDB assertions.
- One worker is used to keep PostgreSQL setup and cleanup deterministic.
- Trace, screenshot, and video are retained on failure.

## 2. Test Files Created

- `frontend/e2e/foods/helpers.ts`
- `frontend/e2e/foods/navigation.spec.ts`
- `frontend/e2e/foods/create.spec.ts`
- `frontend/e2e/foods/validation.spec.ts`
- `frontend/e2e/foods/optional-nutrients.spec.ts`
- `frontend/e2e/foods/duplicate.spec.ts`
- `frontend/e2e/foods/list-search-states.spec.ts`
- `frontend/e2e/foods/details-edit.spec.ts`
- `frontend/e2e/foods/delete.spec.ts`
- `frontend/e2e/foods/snapshot.spec.ts`
- `frontend/e2e/foods/mobile-rtl-a11y.spec.ts`
- `frontend/e2e/foods/online-only.spec.ts`

## 3. Coverage and Execution Summary

| Metric | Count |
|---|---:|
| CSV test cases mapped | 153 |
| Fully automated CSV cases | 135 |
| Partially automated CSV cases | 18 |
| Manual-only or unmapped cases | 0 |
| Runnable Playwright tests | 151 |
| Playwright tests executed | 151 |
| Passed Playwright tests | 145 |
| Failed Playwright tests | 6 |
| Blocked Playwright tests | 0 |
| CSV cases with automated Pass | 129 |
| CSV cases with automated Fail | 6 |
| CSV cases still requiring manual confirmation | 18 |

Two Playwright tests each cover two tightly related CSV IDs: `FOOD-TC-030`/`031` and `FOOD-TC-032`/`131`. This accounts for 151 runnable tests mapping all 153 CSV cases.

## 4. Bugs Found

| Bug ID | Test case | Priority | Expected | Actual | Evidence |
|---|---|---|---|---|---|
| `BUG-FOODS-AUTO-001` | `FOOD-TC-124` | P1 | Repeated confirmation sends one DELETE request. | A double-click sent two DELETE requests before the pending state disabled the action. | `frontend/test-results/foods-delete-Food-permanen-bcf05-rm-sends-one-delete-request-foods-chromium/` |
| `BUG-FOODS-AUTO-002` | `FOOD-TC-059` | P1 | Food name above 120 characters returns `422` with Arabic field error. | API accepted 121 characters and returned `201`. | `frontend/test-results/foods-validation-Food-fiel-1515a--enforces-Food-name-max-120-foods-chromium/` |
| `BUG-FOODS-AUTO-003` | `FOOD-TC-073` | P2 | Brand above 80 characters returns `422`. | API accepted 81 characters and returned `201`. | `frontend/test-results/foods-validation-Food-fiel-b8357-and-language-and-max-length-foods-chromium/` |
| `BUG-FOODS-AUTO-004` | `FOOD-TC-074` | P2 | Category above 80 characters returns `422`. | API accepted 81 characters and returned `201`. | `frontend/test-results/foods-validation-Food-fiel-79aec-ory-language-and-max-length-foods-chromium/` |
| `BUG-FOODS-AUTO-005` | `FOOD-TC-149` | P2 | Notes above 500 characters returns `422`. | API accepted 501 characters and returned `201`. | `frontend/test-results/foods-validation-Food-fiel-55a75-tes-language-and-max-length-foods-chromium/` |
| `BUG-FOODS-AUTO-006` | `FOOD-TC-150` | P2 | Data source above 120 characters returns `422`. | API accepted 121 characters and returned `201`. | `frontend/test-results/foods-validation-Food-fiel-98145-rce-language-and-max-length-foods-chromium/` |

No application code was changed to resolve these defects. Product fixes require explicit approval followed by targeted retest.

## 5. Verification Commands

| Command | Result |
|---|---|
| `npm run typecheck` | Pass |
| `npm run build` | Pass; all Foods routes built |
| `npx playwright test e2e/foods` | 145 passed, 6 failed, 151 executed |
| `pytest -q` | 18 passed, 1 skipped; sync test remains Future Scope |
| `ruff check .` | Pass |

## 6. Artifacts

- JSON report: `frontend/test-results/foods-results.json`
- HTML report: `frontend/playwright-report/index.html`
- Failure screenshots, videos, traces, and error contexts: `frontend/test-results/`
- Per-case mapping: `docs/qa/foods-test-cases/FOODS_AUTOMATION_MAPPING.md`

Generated artifacts are ignored by Git and remain local.

## 7. Remaining Manual Checks

Eighteen cases are partially automated. Playwright executed deterministic DOM, API, RTL, viewport, keyboard, focus, and accessible-name assertions, but formal sign-off still requires the applicable human checks:

- Real iPhone Safari and desktop Safari behavior.
- Real Android Chrome behavior.
- Visual readability at 360px, 390px, 430px, 768px, and desktop widths.
- Mixed Arabic/English text quality and long-name visual truncation.
- Screen-reader announcement quality and end-to-end keyboard usability.
- Perceived loading, empty, no-results, and error-state usability.
- Large-catalog usability beyond structural rendering and search assertions.

## 8. Recommendation

Do not treat the Foods baseline as fully passing. Review and approve fixes for the six documented product defects, rerun the failed tests, then execute the 18 manual-confirmation cases across the required browser/device matrix.
