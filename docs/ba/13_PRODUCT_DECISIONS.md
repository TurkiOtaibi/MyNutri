# Product Decisions

## PD-001 - Offline-First Removed From v1

Decision: Offline-first is removed from v1.

Status: Approved for v1.

Rationale:

myNutri is a personal-use nutrition system. v1 should prioritize simplicity, reliability, understandable error handling, and easier implementation over offline-first complexity. Offline queueing, cache staleness, sync rejection, and conflict handling add product and QA cost that is not required for the first usable online version.

Impact:

- Remove or defer offline cache behavior as a v1 product requirement.
- Remove or defer IndexedDB local data stores as a v1 source of truth.
- Remove or defer offline mutation queue behavior.
- Remove or defer sync push/pull behavior.
- Remove or defer pending sync states.
- Remove or defer conflict handling.
- Remove or defer stale cache behavior.
- Remove or defer offline Profile, Food, and Diary writes.
- Keep normal online API behavior.
- Keep mobile-first responsive web behavior.
- Keep Arabic RTL support.
- Keep clear network/API error handling.
- Optional installable shell may remain only if it does not imply offline personal data writes or cached personal nutrition data as source of truth.

Required v1 behavior:

- The app requires an internet connection to load fresh personal nutrition data.
- If the backend/API is unreachable, show a clear connection error.
- Invalid data must not be saved.
- No changes should be queued offline.
- No local cached personal nutrition data should be treated as source of truth.
- Profile, Food, and Diary changes are saved only after a successful API response.
- User-entered form data should remain available after a connection failure so the user can retry.

QA impact:

- Replace offline/sync v1 test expectations with online network-error tests.
- Test API-unreachable states for Profile, Foods, Diary day view, Weekly Summary, create/update/delete flows, and auth failure.
- Test that failed writes do not create local queued mutations.
- Test that invalid data is not saved locally or remotely.
- Keep existing sync tests only as future-scope regression evidence if Engineering decides to preserve sync code outside v1.

Implementation impact:

- Remove, disable, or defer IndexedDB cache behavior for personal nutrition data in v1.
- Remove, disable, or defer sync queue behavior in v1.
- Remove, disable, or defer `/sync` UI usage in v1.
- Ensure Profile, Food, and Diary mutation UI updates only after successful API responses.
- Ensure API validation errors and connection errors are clearly separated in the UI.
- If a service worker remains, restrict its v1 purpose to installable shell/static asset support and do not use it to make stale personal nutrition data appear current.

Evidence / affected files:

- Current offline/sync code evidence: `frontend/lib/db.ts`, `frontend/components/SyncStatus.tsx`, `backend/app/api/routes/sync.py`, `backend/tests/test_sync.py`.
- BA files updated for this decision: `docs/ba/00_EXECUTIVE_SUMMARY.md`, `01_FEATURE_MAP.md`, `02_ENTITY_RESOURCE_INVENTORY.md`, `03_CRUD_PERMISSIONS_MATRIX.md`, `04_FIELD_DICTIONARY.md`, `05_VALIDATION_RULES.md`, `06_ERROR_MESSAGES.md`, `07_USER_STORIES.md`, `08_NEGATIVE_SCENARIOS.md`, `09_ACCEPTANCE_CRITERIA.md`, `10_TRACEABILITY_MATRIX.md`, `11_REQUIREMENTS_GAPS.md`, `12_OPEN_QUESTIONS.md`.

Open follow-up:

- Decide whether the current service worker should remain for shell assets only or be removed for v1.
- Decide how existing IndexedDB and sync code should be removed, disabled, hidden, or preserved behind future-scope flags.
