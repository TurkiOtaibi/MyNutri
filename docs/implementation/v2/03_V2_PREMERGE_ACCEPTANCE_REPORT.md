# myNutri V2 Pre-Merge Acceptance Report

## Metadata

- Branch: `feat/v2-multi-user-admin-food-catalog`
- Pull request: [#19](https://github.com/TurkiOtaibi/MyNutri/pull/19)
- PR lifecycle: Draft
- Starting audited head: `0d912d4ed984be6b91873aa9d8c0d242ecc3c7ac`
- Production access or mutation: None
- Verdict: **NO-GO - external acceptance evidence remains required**

This report does not invalidate the repository implementation or its green CI.
It records the stricter pre-merge acceptance gate requested after PR creation.

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Migrations `0012`-`0014` on a disposable populated clone | Partial / blocked | Representative populated `0011` clone passed. Credentials for the current populated local database were unavailable, so the exact requested source clone was not accessed. |
| Real non-production Supabase Auth | Blocked | No `SUPABASE_URL`, public key, or service-role credential was available in the execution environment. Local fixture evidence is not substituted for this gate. |
| Visual QA at 320/390/430 | Passed after correction | 33 Chromium screenshots under [`evidence/premerge`](evidence/premerge/) and layout assertions. |
| User A/User B/Admin isolation via API and UI | Passed locally | `v2-premerge-acceptance.spec.ts`; direct API owner/admin checks plus normal-user UI checks. |
| Expected Backend skip identified | Passed | `backend/tests/test_sync.py` intentionally skips one future-scope sync test because offline push/pull authority is not part of V2. |
| Database URL runbook wording | Passed | Runbook now specifies the project's Supabase PostgreSQL pooler connection URL. |
| Complete local regression | Passed | Backend 129 passed/1 expected skip; migrations 8/8; Playwright 266/266; Ruff, drift, typecheck, audit, build, and diff checks passed. |
| GitHub CI on final exact head | Pending | A new head is required for this report, visual correction, and acceptance test. PR must remain Draft until that CI run passes and the two blocked external gates are completed. |

## Populated Migration Rehearsal

A local PostgreSQL 16 database was populated at revision
`0011_diary_snapshot_v2_expand` with one Principal, Profile, Food, Diary Entry,
and legacy Diary snapshot. It was copied using `pg_dump`/`pg_restore` into a
separate disposable database before applying `0012`, `0013`, and `0014`.

| Measure | Before | After |
| --- | --- | --- |
| Revision | `0011_diary_snapshot_v2_expand` | `0014_v2_food_taxonomy` |
| Principals | 1 | 1 |
| Profiles | 1 | 1 |
| Foods | 1 | 1 |
| Diary Entries | 1 | 1 |
| Diary snapshot MD5 | `0a1f2beb188918c2980eff8a2e49e9de` | `0a1f2beb188918c2980eff8a2e49e9de` |
| Taxonomy audit rows | Not applicable | 1 |
| Alembic model drift | Not applicable | None |

Temporary dump SHA-256:
`C4146EEB4D7D99DC3969CF15C5F657F7C796B7759D30AA425F32B52DA2C8D1D6`.
The dump lives outside the repository and is not release evidence for the
current populated project database. The exact-source rehearsal remains blocked
until an authorized, non-production clone or read-only dump is supplied.

## Real Supabase Acceptance

The following mandatory behavior still requires execution against a real,
non-production Supabase project:

- signup with immediate-session and confirmation-required configurations;
- email confirmation redirect;
- login and logout;
- password recovery email and reset redirect;
- session restoration and expiry handling;
- refresh-token rotation;
- asymmetric JWKS retrieval, caching, key selection, issuer, audience, expiry,
  and subject validation.

The loopback fixture passed signup, login, logout, recovery/reset request shape,
session restoration, refresh handling, and JWKS-backed JWT validation, but it
does not prove Supabase-hosted email delivery, project redirect configuration,
or provider behavior. Therefore this gate is Blocked rather than Passed.

## Isolation Acceptance

The acceptance scenario provisioned distinct User A and User B identities and
the preserved Admin identity. It proved:

- A and B receive different Principal IDs and role `user`;
- A and B read their own distinct Profile values;
- A cannot read B through admin detail routes;
- B cannot read A's Diary through admin routes;
- a normal user receives `403` for Food creation;
- Admin reads A and B details without replacing Admin's Principal context;
- Admin monitoring endpoints expose no update operation (`405`);
- the normal-user UI exposes neither the Admin navigation item nor Food create
  controls.

## Visual QA

Evidence covers 320, 390, and 430 pixel widths for:

- login, signup, forgot-password, and reset-password pages;
- normal-user Food catalog;
- Admin users list and read-only user details;
- Admin Food management;
- baked-goods category fields;
- expanded advanced nutrition analysis;
- sticky save bar and bottom safe-area behavior.

The first 320px inspection found clipped sticky-bar button content. The CSS was
corrected without changing Product behavior. Re-capture then proved:

- no horizontal document overflow;
- no clipped sticky-bar controls;
- the final form content remains above the sticky bar at the bottom boundary;
- the bar remains within the viewport at all three widths.

Admin detail status, role, goal, activity, and date values were also localized
for the Arabic read-only view after visual inspection found raw enum/ISO values.

## Expected Skip

The single Backend skip is `test_sync_api_is_future_scope` in
`backend/tests/test_sync.py`. It is intentionally skipped because sync push/pull
and offline personal-data authority remain future scope. V2 remains online-only
for authoritative personal data. This is not a skipped authentication,
authorization, isolation, migration, catalog, or taxonomy test.

## Local Regression

| Command/gate | Result |
| --- | --- |
| Backend full suite with PostgreSQL | 129 passed, 1 expected skip |
| PostgreSQL migration rehearsal suite | 8/8 passed within the full Backend run |
| Ruff | Passed |
| Alembic heads | One: `0014_v2_food_taxonomy` |
| Alembic model drift | None |
| Frontend typecheck | Passed |
| Production dependency audit | 0 vulnerabilities |
| Next.js production build | Passed; 15 application routes |
| Full Playwright | 266/266 passed; no retries or skips |
| Acceptance screenshots | 33 captured |

## Required Actions Before GO

1. Supply an authorized disposable clone or sanitized read-only dump of the
   current populated non-production database and rerun the exact clone rehearsal.
2. Supply a dedicated non-production Supabase project configured with email
   authentication and approved test inboxes; execute the hosted Auth matrix.
3. Push the acceptance commit and require Backend, Frontend, and E2E GitHub jobs
   to pass on the new exact PR head.
4. Review the resulting evidence and update this verdict to GO in a follow-up
   commit. Do not mark PR #19 Ready before all three actions pass.

## Verdict

```text
Migration rehearsal on representative populated clone: Passed
Migration rehearsal on exact current populated clone: Blocked
Real non-production Supabase acceptance: Blocked
Visual QA: Passed
User isolation and Admin read-only monitoring: Passed locally
Complete local regression: Passed
GitHub CI on final head: Pending
Pre-merge verdict: NO-GO
PR lifecycle: Draft
Production deployment authorized: No
```
