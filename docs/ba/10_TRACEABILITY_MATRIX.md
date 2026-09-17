# Current requirements traceability

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

The canonical test inventory and partition completeness are measured by `.github/workflows/ci.yml`; documentation does not hard-code collection totals.
