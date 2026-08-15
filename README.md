# myNutri

myNutri is an Arabic-first, RTL, online nutrition application. The current system uses a Next.js frontend, a FastAPI backend, PostgreSQL, Supabase authentication, Principal-scoped private data, role-aware administration, and a shared Food catalog.

Start with the [documentation authority map](docs/README.md). The old system plan, architecture document, and Claude prompts are historical archives, not implementation instructions.

## Prerequisites

- Python 3.12
- Node.js 24 with the npm version bundled for the committed lockfile
- Docker with Compose
- PostgreSQL 16, normally the disposable local Compose database

## Locked setup

Do not use an unlocked `pip install` or `npm install`. Backend inputs are hash-locked by Plan 027, and frontend inputs are locked by `package-lock.json`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Set-Location backend
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
Set-Location ..\frontend
npm ci
Set-Location ..
```

On a POSIX shell, activate the same environment with `source .venv/bin/activate`; all other commands are unchanged apart from path separators.

## Local environment

Copy [`.env.example`](.env.example) to an ignored local environment file and provide values appropriate to the local environment. The repository example contains placeholders and development defaults only. Never commit credentials or paste production values into documentation, logs, test fixtures, or frontend variables.

Backend variable names:

- `DATABASE_URL`
- `ENVIRONMENT`
- `SUPABASE_URL`
- `SUPABASE_JWT_AUDIENCE`
- `SUPABASE_JWKS_TIMEOUT_SECONDS`
- `SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS`
- `SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS`
- `SUPABASE_JWKS_NEGATIVE_CACHE_TTL_SECONDS`
- `SUPABASE_JWKS_NEGATIVE_CACHE_MAX_ENTRIES`
- `SUPABASE_JWKS_MAX_KEYS`
- `SUPABASE_JWT_KID_MAX_LENGTH`
- `SUPABASE_SERVICE_ROLE_KEY` for explicitly authorized server-side administrative tools only
- `ALLOWED_ORIGINS`
- `CALENDAR_TIMEZONE`
- `SNAPSHOT_V3_WRITER_ENABLED`

Frontend public variable names:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Never expose a service-role key or database credential through a `NEXT_PUBLIC_` variable. Do not configure the removed shared-token path.

## Start the local stack

Start the repository's local PostgreSQL and backend containers:

```powershell
docker compose up --build db api
```

In another shell, start the frontend:

```powershell
Set-Location frontend
npm run dev
```

The frontend expects Supabase email/password authentication. Requests are authorized by the backend from the bearer token's Principal and role; a branch name, local database row, or frontend route guard is not an authorization boundary. See the [auth and role model](docs/product/v2/02_AUTH_AND_ROLE_MODEL.md) and [authorization matrix](docs/product/v2/03_AUTHORIZATION_MATRIX.md).

## Database and migrations

Alembic revisions live in `backend/alembic/versions`. Inspect and test migrations only against a database explicitly created for local testing:

```powershell
Set-Location backend
python -m alembic heads
python -m alembic current
python -m alembic upgrade head
python -m alembic check
python -m alembic upgrade head --sql
```

`upgrade head` mutates its target. Before running it, verify that `DATABASE_URL` names the disposable loopback database. Never use a staging, hosted Supabase, or production URL for routine development or CI parity. Do not use `alembic stamp`, edit the migration ledger, or run a production migration without explicit deployment authorization.

CI and E2E use short-lived PostgreSQL databases populated only with synthetic fixtures. Tests must not point at a shared developer, staging, or production database. Provider acceptance uses an isolated local Supabase stack and removes its containers, volumes, network, logs, and browser state afterward.

## Quality gates

Run these commands from the repository root unless a block changes directory. They mirror the locked per-layer gates that CI uses.

Backend:

```powershell
Set-Location backend
python -m pip check
python -m pip_audit --require-hashes -r requirements.lock
python -m pip_audit --require-hashes -r requirements-dev.lock
ruff check .
pytest
alembic heads
alembic check
alembic upgrade head --sql
```

Frontend contract, audit, lint, test, and build gates:

```powershell
python -m pip install --require-hashes -r backend/requirements.lock
Set-Location frontend
npm ci
npm audit
npm run generate:api
git diff --exit-code -- openapi.json lib/generated/openapi.ts
npm run lint
npm run test:unit
npm run typecheck
npm audit --omit=dev
npm run build
```

CI additionally runs the complete Playwright suite, critical Linux visual regression, static-shell PWA isolation, development StrictMode smoke, real-provider password-recovery acceptance with mandatory cleanup, backend image build/runtime checks, and migration/preflight checks. The workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) is the exact gate definition.

The principal browser gates are:

```powershell
Set-Location frontend
npm run test:e2e -- --project=foods-chromium
npm run test:visual
npx playwright test e2e/pwa-shell.spec.ts --project=pwa-chromium
```

Run them only with the disposable E2E services and synthetic Principal fixtures described by CI. The provider-acceptance job has additional isolated Supabase and cleanup orchestration; use the workflow verbatim instead of pointing it at any hosted provider.

## Online-only and PWA boundary

Personal nutrition data is online-only. The service worker may cache the installable static shell and same-origin static assets, but it must not cache API data, queue writes, or make stale personal data appear current. Failed writes remain visible as failures and are never represented as saved locally.

## Releases and rollback

Repository validation never authorizes production mutation. Use the [V2 release and rollback runbook](docs/product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md) for approved release order, migration preflight, smoke checks, and rollback boundaries. Deployment, restart, environment changes, migrations, and production data changes always require explicit authorization.
