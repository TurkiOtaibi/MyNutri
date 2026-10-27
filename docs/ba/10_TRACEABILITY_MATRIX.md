# Current requirements traceability

## Approved requirements and current delivery boundary

CURRENT in #111: the browser uses internal username/password login, opaque bearer sessions, forced initial-password change, and own-password change in Profile. Only the session token is persisted in localStorage; passwords stay in memory and no auth cookies are used. Reload during an initial-password change requires re-authentication. Forgotten/reset-password browser flows are absent; forgotten passwords go to the Admin. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; an internal password hash takes precedence and rejects JWT admission with `INTERNAL_LOGIN_REQUIRED`. Internal password changes/resets never update Supabase. Admin username-based creation and management UI is CURRENT in #112: new users have internal credentials only, with no email or provider call. Legacy backend email/provider lifecycle support and clearly marked email fallback for existing accounts remain until #113/#114; provider/email removal (#113) and destructive cutover (#114) remain APPROVED TARGET. No existing account migration or cutover is performed. This describes repository implementation, not deployment. (Product Owner decisions of 17 and 27 October 2026; issues #110/#111/#112; BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054; BR-AUT-001/003/004/005/007/008/010/011/012/017, BR-PRF-024–026, BR-USM-030/033.)

| Target requirement | Authority / BRD codes | Planned implementation / proof |
|---|---|---|
| Internal username/password; no Supabase Auth/email/MFA/self-service recovery | V2 02; AUT/USM final decisions; BR-AUT-001/003/012, BR-USM-022/036 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112; provider removal pending #113 |
| Backend minimum length 8 and initial-password-only forced change | V2 02; BR-AUT-004/007/008, BR-USM-023 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Five-failure lock, user reset-unlock, Admin 30-minute unlock, success clears counter | V2 02; BR-AUT-011, BR-USM-030; final lock decision | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Current-password-verified self-change revokes other devices; Admin reset revokes all | V2 02; BR-PRF-024–026, BR-USM-030/033 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Delete test accounts/private data, preserve Foods, server-side single-Admin create/reset command | V2 06/07; AUT/USM/FOD cutover decisions, related BR-USM-027/043; issue #100 command requirement | #114 cutover pending; Admin command CURRENT #110 (27 October 2026) |

Username identity is 3–32 ASCII English letters, digits, `.`, `_`, or `-`, with a unique lowercase normalized value. Passwords use standard-library scrypt with a random per-password salt; sessions use opaque random bearer tokens in the Authorization header, store only SHA-256 token hashes on the backend, and use no cookies; the browser persists only the raw session token in localStorage (#111). The Product Owner approved the 30-day sliding inactivity expiry for #111 on 27 October 2026. Existing accounts retain null internal credentials unless the explicitly authorized existing-Admin attach command is run. These details replace the former “to be decided in issue #110” placeholders. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## CURRENT executable coverage


Status: supporting map. Exact executable coverage lives in tests and CI.

| Requirement | Product authority | Runtime owner | Primary proof |
|---|---|---|---|
| Internal browser sessions, transitional backend Supabase identity, and Principal isolation | V2 `02`, `03`, `11` | auth dependencies, Principal-scoped services/FKs | principal security and provider-acceptance tests |
| Admin read-only monitoring and sole sex-correction exception | V2 `03`, `11`; 17 October 2026, BR-PRF-006, BR-USM-032/034/061 | `/admin/users*` reads and `PUT /admin/accounts/{principal_id}/profile/sex` | `test_admin_sex_correction.py`, `admin-sex-correction.spec.ts` |
| One global Food catalog and `/foods` UI | V2 `04` | Food routes/service and Foods pages | Food API, E2E, architecture tests |
| Admin-only Food mutation | V2 `03`, `04` | `require_admin`, Food service locks | authorization/security tests |
| Permanent Food delete and Diary cascade | V2 `04`, `11` | PostgreSQL CASCADE and Food delete transaction | Food concurrency/migration tests |
| Food taxonomy and validation | V2 `05`, `12` | Registry, schemas, DB constraints | Registry/Food tests and manifest lock |
| Profile input ownership | V2 `01`, `11` | Profile model/service | Profile and Principal tests |
| Immutable date-effective Target Plans | V2 `09`, `11` | Target Plan service, constraints, triggers | Target Plan and PostgreSQL tests |
| No-plan null behavior | V2 `09`, `11` | target resolver and API schemas | Target Plan/Diary aggregation tests |
| Diary CRUD and measurement capture | V2 `01`, `11` | Diary routes/service/model | Diary API, aggregation, concurrency E2E |
| Nutrition formulas and safety | V2 `12` | nutrition rules calculation/policies | calculation, profile, golden/E2E tests |
| Registry integrity and preview binding | V2 `12` | manifest/Registry/Profile/Target Plan services | Registry API and Target Plan tests |
| Release, cutover, recovery | V2 `06`, `07` | Alembic, deployment mechanism, CI | migration/preflight/offline SQL/container gates |
| Arabic/RTL/mobile/a11y | this BA package | Next.js components/styles | Playwright, visual, axe, RTL, StrictMode tests |
| Approved Labs catalog/package resource | V2 `01`, `11` | `app.labs` catalog/loader | golden keys/membership, integrity, package tests and docs validator |
| Exact interpretation/current-rule history | V2 `01`, `11` | Labs numbers/interpretation/read projection | boundary, conversion, age-zone and registry-substitution tests |
| Private Labs facts/migration/durable receipts | V2 `06`, `11` | LabResult, idempotency, Alembic | PostgreSQL preservation, constraint, privilege and downgrade tests |
| Owner CRUD/admin read-only/404 privacy | V2 `03`, `11` | Labs services/routes/admin reads | transaction, concurrency, service/HTTP/security tests |
| Profile sex/DOB guards and shared locking | V2 `01`, `11` | Profile constraints/TargetPlan and Labs services | demographic regression and PostgreSQL race tests |
| Eight Labs operations/generated contracts | V2 `11` | FastAPI/OpenAPI/generated TypeScript | contract drift, API tests and docs-validator negative fixtures |
| Labs six views/navigation/chart/history | V2 `01`, `11`; BA `07` | frontend Labs components/pages | unit, functional Playwright and Linux visual gates |
| Labs accessibility/mobile/session privacy | V2 `01`, `03`, `11`; BA `07` | Labs UI/query/session boundaries | axe, keyboard, viewport, held-response and dev StrictMode gates |
| Labs static-shell isolation/nutrition independence | V2 `01`, `11` | service worker/query/domain architecture | PWA successful-write/cache/storage/offline tests and domain regressions |

The canonical test inventory and partition completeness are measured by `.github/workflows/ci.yml`; documentation does not hard-code collection totals.


CURRENT backend proof for #110: `test_internal_credentials.py` covers format/hash validation; `test_internal_auth.py` covers login/locks, forced change, session revocation/expiry, internal-over-JWT precedence, separate credentials, Admin command and migration round-trip. Browser login, forced initial change and own-password change are implemented in #111; Admin username-management UI is CURRENT in #112; provider removal/cutover remains pending #113/#114 (BR-USM-005/006/013/014/022/023/025/036/038/042/054). Browser coverage is in internal-session unit tests and authentication/Profile Playwright tests. Tests prove repository behavior, not deployment. (17/27 October 2026; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

CURRENT #112 acceptance: username creation is atomic and provider-free; duplicate normalized usernames and conflicting idempotency replays are rejected. Username is immutable, search is literal/case-insensitive, lock filter/badge and last-login dates are exposed, reset signs out all sessions and unlocks, and username-confirmed deletion scrubs the tombstone while preserving Food attribution and permitting username reuse. Legacy account email fallback and provider sagas remain pending #113/#114; no migration/cutover is performed. Authority: BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054, final USM decision table (17 October 2026), and [PO decision (27 October 2026)](https://github.com/TurkiOtaibi/MyNutri/issues/112#issuecomment-6437936388).
