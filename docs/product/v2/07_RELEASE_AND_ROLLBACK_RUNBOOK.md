# V2 Release and Rollback Runbook

## Pre-release Gates

- One Alembic head and zero model drift.
- Fresh and populated PostgreSQL rehearsals pass.
- Admin bootstrap and taxonomy tools pass dry-run.
- User A/User B/Admin isolation suite passes.
- Backend, Frontend, Playwright, accessibility, audit, and build gates pass.
- Built browser assets contain no shared token or service-role secret.

## Deployment Order

1. Configure Supabase email/password, redirect URLs, and asymmetric signing key.
2. Configure Backend Supabase URL/issuer/audience and trusted CORS origins.
3. Apply migrations and run preflight.
4. Link/bootstrap the preserved production Principal as admin.
5. Deploy Backend and verify health/auth/isolation.
6. Configure and deploy Frontend Supabase public values.
7. Verify signup, login, logout, reset, shared catalog, and admin read views.

No production command is executed as part of repository implementation.

## Render and Supabase Configuration

Backend values:

```text
DATABASE_URL=<Supabase PostgreSQL pooler connection URL used by this project>
ENVIRONMENT=production
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWKS_TIMEOUT_SECONDS=5
SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS=600
SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS=30
SUPABASE_JWKS_MAX_KEYS=32
SUPABASE_JWT_KID_MAX_LENGTH=256
ALLOWED_ORIGINS=["https://<frontend-host>"]
CALENDAR_TIMEZONE=Asia/Riyadh
SNAPSHOT_V3_WRITER_ENABLED=true
```

Frontend values:

```text
NEXT_PUBLIC_API_URL=https://<backend-host>
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<public-publishable-key>
```

Do not configure `NEXT_PUBLIC_API_TOKEN` or expose
`SUPABASE_SERVICE_ROLE_KEY` to the Frontend. In Supabase Auth, configure the
production Site URL and the exact login/reset redirect URLs before deploying.

The JWKS limits above bound refresh work per Backend process, not across the
whole cluster. `SUPABASE_JWKS_TIMEOUT_SECONDS` bounds both provider calls and
singleflight waits. `SUPABASE_JWKS_CACHE_LIFESPAN_SECONDS` controls the
successful snapshot lifetime, while
`SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS` limits refresh attempts after misses
and failures. `SUPABASE_JWKS_MAX_KEYS` and `SUPABASE_JWT_KID_MAX_LENGTH` bound
provider documents and token key IDs. The defaults are 5, 600, 30, 32, and 256
respectively. A newly published provider key can be rejected until the next
cooldown eligibility, at most 30 seconds with the default policy.

Before rollout, inspect the real non-production provider JWKS and confirm its
key count and key-ID lengths fit these bounds. Do not record private tokens or
authorization headers while performing that check.

## Smoke Test Order

1. Confirm Backend health and schema preflight.
2. Sign in as the linked admin and verify `/account/me` returns `admin`.
3. Register two ordinary accounts and verify each returns role `user`.
4. Verify ordinary users share the active catalog but receive `403` on Food mutation.
5. Verify cross-user Profile, Diary, and Target Plan identifiers do not disclose data.
6. Verify admin users/details are read-only and Food archive/restore works.
7. Log a Food and confirm the historical Snapshot remains stable after catalog edit.

## Rollback

Roll the application back only to a release that understands V2 schema and
shared Foods after V2 writes begin. Do not restore owner-scoped Food visibility,
re-enable a browser shared token, or downgrade schema if doing so loses V2 data.
For a frontend-only fault, keep Backend/schema and roll back to a V2-compatible
frontend. For auth-provider outage, fail closed and restore service rather than
bypass authentication.

Rolling back the JWKS policy removes the application-owned snapshot,
singleflight, cooldown, and input limits and restores the prior PyJWT client
behavior. Retain fail-closed authentication during rollback; do not accept
expired cached keys.
