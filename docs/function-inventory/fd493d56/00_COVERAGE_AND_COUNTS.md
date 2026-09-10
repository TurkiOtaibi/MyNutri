# myNutri Project-Owned Function Inventory

## Commit verification and inventory basis

- Canonical remote `main` verified with `git ls-remote --heads origin refs/heads/main`: `fd493d56cb60b76aa0eb88c6e77ec1b60f90b1fc`.
- The local checkout is `main` at `078f780a2ef3a1891d3eb0707ca7afa0ecdf460a`, one commit ahead and 135 commits behind `origin/main` at inspection time.
- Every source location in these reports is commit-relative to `fd493d56cb60b76aa0eb88c6e77ec1b60f90b1fc`; the working tree was not checked out, reset, fetched, or modified.
- Existing local modifications and untracked files were not included because they are not part of the verified canonical `main` tree.

## Extraction method

- Python definitions, methods, nested functions, and lambdas were extracted with Python's AST from Git object contents.
- TypeScript/TSX/JavaScript functions, methods, React components, hooks, function expressions, arrow functions, and anonymous callbacks were extracted with the TypeScript compiler AST loaded read-only from the existing npm cache.
- Imports (including function-local Python imports), same-file calls, `self` methods, namespace calls, FastAPI decorators/dependencies, JSX component references, frontend API calls, DB session operations, commits, and selected external side effects were analyzed structurally.
- Direct invocation callers and lexical ownership are reported separately so enclosing components are not mislabeled as callers of deferred callbacks.
- Dynamic dispatch, dependency injection references, reflection, callback invocation by frameworks, and calls across HTTP boundaries are marked unresolved where static proof was unavailable.

## Counts

- Total included function-like definitions: **2829**.
- Scanned code files: **207**; files containing definitions: **191**; zero-definition code files: **16**.

| Section | Count |
|---|---:|
| backend | 255 |
| frontend | 775 |
| tests-backend | 445 |
| tests-frontend | 1230 |
| scripts | 55 |
| migrations | 69 |

### Counts by feature

| Section | Feature | Count |
|---|---|---:|
| backend | admin | 9 |
| backend | auth-account | 22 |
| backend | diary-analysis | 62 |
| backend | foods-nutrition | 86 |
| backend | models-validation | 4 |
| backend | platform-shared | 10 |
| backend | profile-targets | 62 |
| frontend | admin | 36 |
| frontend | auth-account | 53 |
| frontend | diary-analysis | 205 |
| frontend | foods-nutrition | 239 |
| frontend | platform-shared | 81 |
| frontend | profile-targets | 127 |
| frontend | shared-api-utilities | 14 |
| frontend | shell-pwa | 20 |
| migrations | auth-account | 8 |
| migrations | diary-analysis | 27 |
| migrations | foods-nutrition | 21 |
| migrations | platform-shared | 7 |
| migrations | profile-targets | 5 |
| migrations | shell-pwa | 1 |
| scripts | admin | 8 |
| scripts | auth-account | 19 |
| scripts | foods-nutrition | 20 |
| scripts | platform-shared | 7 |
| scripts | profile-targets | 1 |
| tests-backend | admin | 51 |
| tests-backend | auth-account | 152 |
| tests-backend | diary-analysis | 50 |
| tests-backend | foods-nutrition | 95 |
| tests-backend | platform-shared | 9 |
| tests-backend | profile-targets | 88 |
| tests-frontend | admin | 58 |
| tests-frontend | auth-account | 306 |
| tests-frontend | diary-analysis | 232 |
| tests-frontend | foods-nutrition | 333 |
| tests-frontend | platform-shared | 77 |
| tests-frontend | profile-targets | 160 |
| tests-frontend | shell-pwa | 64 |

### Counts by callable kind

| Kind | Count |
|---|---:|
| FastAPI endpoint | 41 |
| React component | 94 |
| React hook | 6 |
| anonymous callback | 456 |
| database trigger/function | 5 |
| function | 452 |
| method | 45 |
| script callback | 15 |
| script function | 40 |
| test callback | 1009 |
| test function | 425 |
| test helper/function | 241 |

## Coverage and explicit exclusions

Included: project-owned Python/TypeScript/TSX/JavaScript functions and methods in the verified Git tree, including nested and anonymous callbacks; Backend and Frontend production code; tests; operational scripts; Alembic migrations; and PL/pgSQL functions embedded in migration SQL.

Excluded:

- Dependencies and package caches (`node_modules`, Python environments, lock-file package contents).
- Generated sources: `frontend/lib/generated/openapi.ts` and `frontend/next-env.d.ts`.
- Build/cache artifacts such as `.next`, coverage output, test output, and compiled bytecode.
- Non-code assets and declarative data without function definitions: CSS, JSON, SVG, PNG, YAML, TOML, lock files, Dockerfiles, and Markdown.
- Framework-generated constructors, ORM/Pydantic methods, dataclass methods, and functions created dynamically at runtime because they have no project-owned source definition.
- The dirty local working-tree files listed in the commit-basis section because the requested inventory is anchored to canonical `main`.

### Scanned code files with zero included definitions

- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/core/__init__.py`
- `backend/app/db/__init__.py`
- `backend/app/nutrition_rules/__init__.py`
- `backend/app/nutrition_rules/policies.py`
- `backend/app/ops/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/services/calc.py`
- `backend/scripts/__init__.py`
- `frontend/lib/labels.ts`
- `frontend/lib/types.ts`
- `frontend/postcss.config.mjs`
- `frontend/vitest.config.ts`

## Report index

- [Backend — Admin](backend/admin.md) — 9 definitions
- [Backend — Auth Account](backend/auth-account.md) — 22 definitions
- [Backend — Diary Analysis](backend/diary-analysis.md) — 62 definitions
- [Backend — Foods Nutrition](backend/foods-nutrition.md) — 86 definitions
- [Backend — Models Validation](backend/models-validation.md) — 4 definitions
- [Backend — Platform Shared](backend/platform-shared.md) — 10 definitions
- [Backend — Profile Targets](backend/profile-targets.md) — 62 definitions
- [Frontend — Admin](frontend/admin.md) — 36 definitions
- [Frontend — Auth Account](frontend/auth-account.md) — 53 definitions
- [Frontend — Diary Analysis](frontend/diary-analysis.md) — 205 definitions
- [Frontend — Foods Nutrition](frontend/foods-nutrition.md) — 239 definitions
- [Frontend — Platform Shared](frontend/platform-shared.md) — 81 definitions
- [Frontend — Profile Targets](frontend/profile-targets.md) — 127 definitions
- [Frontend — Shared Api Utilities](frontend/shared-api-utilities.md) — 14 definitions
- [Frontend — Shell Pwa](frontend/shell-pwa.md) — 20 definitions
- [Migrations and database functions — All](support/migrations.md) — 69 definitions
- [Scripts and operational entry points — All](support/scripts.md) — 55 definitions
- [Backend tests — Admin](tests/backend/admin.md) — 51 definitions
- [Backend tests — Auth Account](tests/backend/auth-account.md) — 152 definitions
- [Backend tests — Diary Analysis](tests/backend/diary-analysis.md) — 50 definitions
- [Backend tests — Foods Nutrition](tests/backend/foods-nutrition.md) — 95 definitions
- [Backend tests — Platform Shared](tests/backend/platform-shared.md) — 9 definitions
- [Backend tests — Profile Targets](tests/backend/profile-targets.md) — 88 definitions
- [Frontend tests — Admin](tests/frontend/admin.md) — 58 definitions
- [Frontend tests — Auth Account](tests/frontend/auth-account.md) — 306 definitions
- [Frontend tests — Diary Analysis](tests/frontend/diary-analysis.md) — 232 definitions
- [Frontend tests — Foods Nutrition](tests/frontend/foods-nutrition.md) — 333 definitions
- [Frontend tests — Platform Shared](tests/frontend/platform-shared.md) — 77 definitions
- [Frontend tests — Profile Targets](tests/frontend/profile-targets.md) — 160 definitions
- [Frontend tests — Shell Pwa](tests/frontend/shell-pwa.md) — 64 definitions
