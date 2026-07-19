# myNutri V2 Implementation Report

Base SHA: `6096fd2a1f372f8e08aa587274870e8f3929fe23`

Branch: `feat/v2-multi-user-admin-food-catalog`

## Delivered Scope

- Supabase email/password authentication with SSR session handling and Arabic routes.
- Backend JWT/JWKS validation, transactional Principal provisioning, roles, and admin bootstrap.
- Principal-scoped private resources and explicit read-only admin monitoring services.
- Global active Food catalog with admin-only mutation, archive, restore, and safe delete.
- Food Taxonomy V2, structured grain/baked/starch detail, reviewed reclassification tooling.
- Registry schema/version 2 and Snapshot v3 writer while retaining v1/v2 readers.
- Admin users and Food management UI, role-gated navigation, and read-only user context.
- Redesigned advanced Food analysis, confirmed suggestions, and mobile-safe save actions.

## Schema Delta

| Revision | Purpose | Rollback boundary |
| --- | --- | --- |
| `0012_v2_principal_auth_expand` | Auth identity, role, account metadata | Refuses after identity links exist |
| `0013_v2_shared_food_catalog` | Global catalog and lifecycle/audit fields | Refuses after shared or archived use |
| `0014_v2_food_taxonomy` | Taxonomy V2, migration audit, Snapshot v3 | Refuses after v3/new unmapped data |

Existing Principal, Food, Diary, Target Plan, and Snapshot identifiers are preserved.
Historical Snapshot v1/v2 data is not rewritten.

## Security Review

- Browser shared token removed; only the Supabase public publishable key is public.
- JWT issuer, audience, expiry, subject, and asymmetric signature are validated.
- Client metadata cannot assign role; unknown identities provision as `user` only.
- Normal private routes infer the authenticated Principal and remain owner-scoped.
- Admin monitoring uses dedicated read-only routes and never substitutes admin ownership.
- Normal users receive `403` for catalog mutations; archived records are hidden from normal reads.
- Production Auth and CORS configuration fails closed; wildcard credentialed CORS is rejected.

## Compatibility and Deferred Scope

Wave 1 calculations, Target Plans, Diary aggregation, Arabic RTL, responsive behavior,
and PWA assets remain in place. Historical taxonomy keys are accepted only by historical
snapshot readers. No organization, coach, private Food, payment, messaging, or later-wave
feature was introduced.

## Verification Status

Local Backend, Ruff, OpenAPI, TypeScript, production build, dependency audit, UTF-8,
and diff checks passed. Disposable PostgreSQL migration rehearsals and full Playwright
remain assigned to GitHub CI because the workstation has no approved disposable
PostgreSQL credentials. No production database or deployment was touched.
