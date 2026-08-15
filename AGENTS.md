# Contributor and agent rules

These rules apply to the whole repository. Read the [documentation authority map](docs/README.md) before implementation.

## Authority order

1. Current approved V2 and nutrition product/architecture decisions linked from the authority map.
2. Unsuperseded BA product decisions and exact approved Arabic copy.
3. Current executable contracts: schemas, migrations, lockfiles, tests, and CI.
4. Implementation, QA, audit, and UI/UX reports as supporting evidence.
5. Explicitly superseded documents as history only.

If two current approved artifacts conflict, stop and obtain a recorded Product Owner decision. Do not resolve product ambiguity through code, tests, or convenience.

## Branch and scope discipline

- Start from the explicitly approved base and work on the task's named branch.
- Inspect the existing worktree before editing and preserve unrelated changes.
- Modify only authorized files and behavior. Report scope expansion before making it.
- Treat plans as task records, not source authority. Product code changes and administrative plan updates belong in their established separate workflows.
- Do not force-push, bypass branch protection, weaken a gate, or hide a failure.

## Product and API boundaries

- The backend is authoritative for authentication, authorization, Principal ownership, validation, persistence, nutrition calculations, and API schemas.
- The frontend must consume generated OpenAPI contracts at its API boundary and map them deliberately into frontend domain models.
- Arabic-first RTL behavior, exact approved Arabic error text, accessibility, responsive behavior, and focus behavior are acceptance requirements. Consult the BA copy and current approved UI/UX evidence; do not invent replacement wording when exact copy is governed.
- Private Profile, Diary, Target Plan, and account data remain Principal-scoped. Food catalog visibility and mutation permissions follow the current V2 authorization matrix.
- Personal nutrition reads and writes are online-only. The PWA is a static shell; do not add API caching, IndexedDB authority, mutation queues, or sync behavior.

## Dependencies and generated contracts

- Install Python dependencies from the committed hash-locked files with `--require-hashes`.
- Install frontend dependencies with `npm ci`.
- Do not hand-edit generated OpenAPI artifacts. Regenerate them from the backend schema and verify a clean diff.
- Do not add an unlocked install path, audit bypass, broad version update, or new package source without explicit scope and review.

## Database and environment safety

- Use only an explicitly identified disposable loopback PostgreSQL database for development migrations, preflight, and tests.
- Never point automated tests at shared development, staging, hosted Supabase, or production data.
- Confirm the target before any command that can alter schema or rows. Do not run `alembic upgrade`, `downgrade`, or `stamp` against production without explicit release authorization.
- Do not edit frozen historical migrations. Add a reviewed forward migration when a schema change is authorized.
- Environment files and credentials stay local and ignored. Document variable names and placeholders only.
- Never print database URLs, bearer tokens, service-role credentials, cookies, or private keys. Frontend `NEXT_PUBLIC_` variables must contain public browser-safe values only.

## Required verification

Match the gates in [CI](.github/workflows/ci.yml) for the affected scope. At minimum preserve:

- backend Ruff, pytest, lock reproducibility, dependency audit, migration-head/model-drift, preflight, offline SQL, and container-runtime checks;
- frontend clean install, full and production audits, generated-contract drift, ESLint, Vitest/architecture tests, TypeScript, and production build;
- applicable Playwright, Linux visual, PWA static-shell, StrictMode, provider acceptance, and mandatory cleanup gates;
- `git diff --check` and an exact changed-file scope review.

Tests must use synthetic fixtures and disposable services. Do not add hidden retries, ignored failures, arbitrary sleeps, broad lint exclusions, or test-only behavior that makes a gate pass without proving its objective.

## Production boundary

No commit, PR, CI result, branch configuration, or migration file proves production deployment. Do not deploy, redeploy, restart, migrate, edit environment configuration, or mutate production data without explicit authorization for that exact action and revision. Follow the [release and rollback runbook](docs/product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md), verify the running revision through authoritative platform evidence, and use only safe non-mutating smoke checks unless broader verification is separately authorized.
