# User Story Quality Audit

Source: `docs/ba/07_USER_STORIES.md`

Stories reviewed: 33

## Overall Quality

Most stories are clear, valuable, and linked to evidence. The BA package is substantially better than a raw extraction: stories distinguish implemented behavior from required v1 behavior and tie major rules to product decisions D-001 through D-020.

Quality issues are concentrated in a small number of stories where acceptance criteria are still too broad or depend on another document without an observable minimum.

## Weak or Risky Stories

| Story ID | Issue | Severity | Why it matters | Recommended fix |
|---|---|---|---|---|
| `US-DIARY-GRAM-001` | Gram-mode API/storage contract is not final. | High | QA cannot write final API/E2E tests for grams, edit mode, and snapshot without exact payload and persisted fields. | Add decision/criteria defining `log_mode`, serving quantity, gram quantity, stored quantity, and snapshot behavior. |
| `US-NETWORK-READ-001` | Read-failure Arabic copy is not exact. | High | Exact message assertions cannot be written; write-failure message is misleading for reads. | Add exact read-error copy to `06_ERROR_MESSAGES.md` and reference it here. |
| `US-A11Y-001` | Uses "where practical" for focus/status behavior. | Medium | QA needs a minimum expected behavior for invalid fields and async status. | Replace with minimum: first invalid field receives focus unless inside collapsed/inactive section; status region uses `role=status` or equivalent. |
| `US-QA-001` | Too broad for a single testability story. | Medium | It does not map test data, boundaries, or minimum suites. | Split into API, frontend E2E/component, accessibility, and visual regression coverage stories or add a QA matrix. |
| `US-FOOD-STATE-001` | One criterion says "no-results copy is shown" instead of exact copy. | Low | Minor inconsistency because exact copy is elsewhere. | Use the exact no-results message or reference `06_ERROR_MESSAGES.md`. |
| `US-TARGET-HAPPY-001` | "after a short delay" is not measurable. | Low | Component tests need a debounce expectation or "eventually" behavior. | Define debounce threshold if required, or remove timing. |
| `US-ERROR-MAPPING-001` | Uses general API mapping for several flows. | Low | Acceptable for BA, but final QA benefits from flow-specific examples. | Add examples for Profile read, Food save, Diary delete, and Weekly read. |

## Duplicate Stories

No harmful duplicate stories found.

Some overlap is intentional:
- Online-only write behavior appears in CRUD stories and `US-NETWORK-WRITE-001`.
- Accessibility appears in destructive-dialog stories and `US-A11Y-001`.
- Validation appears in field stories and acceptance criteria.

## Missing Story Proposals

These are BA story or acceptance-criteria proposals, not implementation tasks.

### US-INFRA-READ-001 - Check API Health

Feature: Health endpoint
Type: Technical / Read
Priority: P2
Status: Missing
Evidence: `docs/ba/01_FEATURE_MAP.md`, `backend/app/api/routes/health.py`

User story:
As the system operator, I want a public health endpoint, so that basic API availability can be checked without accessing personal nutrition data.

Acceptance criteria:
- Given `/health` is requested
  When the API is running
  Then it returns a successful health response without requiring a personal data token.

### US-CONFIG-SEC-001 - Configure Environment Safely

Feature: Environment config
Type: Security / Configuration
Priority: P2
Status: Missing
Evidence: `docs/ba/01_FEATURE_MAP.md`, `backend/app/core/config.py`

User story:
As the system owner, I want API URL, token, database URL, and CORS origins configured through environment settings, so that personal deployment settings are not hard-coded into product behavior.

Acceptance criteria:
- Given v1 is deployed
  When environment variables are provided
  Then backend/frontend use configured values without exposing secrets in committed code.

### US-PROFILE-STATE-001 - Handle Missing Profile State

Feature: Read profile
Type: Empty State / Read
Priority: P1
Status: Missing
Evidence: `docs/ba/06_ERROR_MESSAGES.md`, `docs/ba/09_ACCEPTANCE_CRITERIA.md`, `backend/app/api/routes/profile.py`

User story:
As a user, I want a clear missing-profile state, so that I know to enter profile data before relying on targets.

Acceptance criteria:
- Given `/profile` returns 404 because no profile exists
  When Profile or Diary loads target-dependent content
  Then the UI shows the missing-profile message and does not show stale targets as current.

### US-NETWORK-READ-COPY-001 - Show Exact Read Failure Message

Feature: Online API reads
Type: Error Handling
Priority: P0
Status: Missing
Evidence: `docs/ba/06_ERROR_MESSAGES.md`, `docs/ba/07_USER_STORIES.md`

User story:
As a user, I want read failures to use accurate Arabic copy, so that I understand data did not load rather than thinking a save failed.

Acceptance criteria:
- Given Profile, Foods, Diary, or Week data cannot be loaded
  When the API read fails due to timeout/network/server error
  Then the UI shows the exact Arabic read-failure message defined in `06_ERROR_MESSAGES.md`.

### US-DIARY-GRAM-CONTRACT-001 - Define Gram Mode Data Contract

Feature: Diary gram logging
Type: Data Contract / Calculation
Priority: P0
Status: Missing
Evidence: `docs/ba/04_FIELD_DICTIONARY.md`, `docs/ba/07_USER_STORIES.md`, `backend/app/schemas.py`, `frontend/lib/types.ts`

User story:
As Engineering and QA, we need a final gram-mode Diary data contract, so that create, edit, totals, and snapshot tests all use the same payload and persisted fields.

Acceptance criteria:
- Given a user logs by servings
  When the request is sent
  Then the payload and persisted fields match the serving-mode contract.
- Given a user logs by grams
  When the request is sent
  Then the payload and persisted fields match the gram-mode contract and preserve mode-specific quantity.

### US-FOOD-EDGE-001 - Handle Stale Food Edit or Archive

Feature: Food edit/archive
Type: Edge / Error Handling
Priority: P1
Status: Missing
Evidence: Food archive and active-only requirements

User story:
As a user, I want stale food edit/archive attempts to fail safely, so that hidden or already-archived foods are not accidentally changed.

Acceptance criteria:
- Given a food becomes archived or unavailable after I opened edit
  When I try to save or archive it
  Then the UI shows a not-found/refresh-required error and no local change is saved.

### US-UX-STATUS-001 - Prevent Duplicate Submits

Feature: Form submission states
Type: UX / Edge
Priority: P1
Status: Missing
Evidence: online-only write behavior, current mutation buttons

User story:
As a user, I want submit controls to prevent duplicate writes while a request is pending, so that rapid taps do not create duplicate saves or deletes.

Acceptance criteria:
- Given a Profile, Food, or Diary write is pending
  When I tap the same action repeatedly
  Then only one request is submitted and the UI shows a pending state until the response returns.
