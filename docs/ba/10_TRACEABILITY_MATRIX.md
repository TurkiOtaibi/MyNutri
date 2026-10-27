# Current requirements traceability

## APPROVED TARGET traceability — no implementation claim

All rows in this table cite the Product Owner decisions of **17 October 2026**. The current proof table below remains evidence for the CURRENT Supabase/email implementation only; it does not prove these target requirements. Issue #100 changes documentation, not runtime coverage or the completion counts in #99.

| Target requirement | Authority / BRD codes | Planned implementation / proof |
|---|---|---|
| Internal username/password; no Supabase Auth/email/MFA/self-service recovery | V2 02; AUT/USM final decisions; BR-AUT-001/003/012, BR-USM-022/036 | #110–#113, pending |
| Backend minimum length 8 and initial-password-only forced change | V2 02; BR-AUT-004/007/008, BR-USM-023 | #110–#112, pending |
| Five-failure lock, user reset-unlock, Admin 30-minute unlock, success clears counter | V2 02; BR-AUT-011, BR-USM-030; final lock decision | #110–#112, pending |
| Current-password-verified self-change revokes other devices; Admin reset revokes all | V2 02; BR-PRF-024–026, BR-USM-030/033 | #110–#112, pending |
| Sole Admin Profile-write exception: correct sex; other private monitoring read-only | V2 03/11; BR-PRF-006, BR-USM-032/061/067/074 | #109, pending |
| Delete test accounts/private data, preserve Foods, server-side single-Admin create/reset command | V2 06/07; AUT/USM/FOD cutover decisions, related BR-USM-027/043; issue #100 command requirement | #114, pending; operational design #110 |

Username format and unspecified session/credential design are **to be decided in issue #110**, not inferred from current provider behavior. (17 October 2026 decisions; BR-AUT-001/011/017, BR-USM-022/025/036.)

## CURRENT executable coverage


Status: supporting map. Exact executable coverage lives in tests and CI.

| Requirement | Product authority | Runtime owner | Primary proof |
|---|---|---|---|
| Supabase identity and Principal isolation | V2 `02`, `03`, `11` | auth dependencies, Principal-scoped services/FKs | principal security and provider-acceptance tests |
| Admin read-only monitoring | V2 `03`, `11` | `/admin/users*` routes | Admin/security E2E and Backend tests |
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
