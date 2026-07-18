# V2 Authentication and Role Model

## Authentication

The browser authenticates with Supabase Auth using email/password and sends the
current Supabase access token to FastAPI as `Authorization: Bearer <jwt>`.

FastAPI verifies asymmetric Supabase JWTs against the project JWKS endpoint and
validates signature algorithm, issuer, audience, expiry, and UUID subject. JWKS
cache behavior must permit key rotation and fail closed. Production requires
Supabase configuration at startup.

The implementation follows the current official guidance:

- https://supabase.com/docs/guides/auth/jwts
- https://supabase.com/docs/guides/auth/server-side/creating-a-client?framework=nextjs
- https://supabase.com/docs/guides/auth/jwt-fields

## Principal

`principal` gains:

- `auth_user_id UUID UNIQUE NULL` for safe brownfield expansion;
- `email VARCHAR(320) NULL`;
- `display_name VARCHAR(120) NULL`;
- `role TEXT NOT NULL CHECK (role IN ('user','admin'))`;
- existing `status`, `created_at`, and `updated_at` remain authoritative.

The existing production Principal remains unchanged until the bootstrap command
links it. Unknown valid Supabase users are provisioned transactionally and
idempotently as active `user` Principals. User metadata may supply a display name
but never role or status.

`PrincipalContext` contains `principal_id`, `auth_user_id`, and `role`.

## Errors

- Missing credentials: `401 AUTHENTICATION_REQUIRED`.
- Invalid/expired/wrong-project credentials: `401 INVALID_CREDENTIAL`.
- Disabled or missing linked Principal: `401 INVALID_CREDENTIAL`.
- Authenticated but unauthorized: `403 FORBIDDEN`.
- Owner-scoped object lookup remains non-enumerating `404`.

## Bootstrap

The admin bootstrap is a dry-run-first command. It links an explicitly selected
Supabase Auth UUID to the existing Principal or creates/invites an identity via
the Supabase Admin API when explicitly requested. It preserves `Principal.id`,
sets role `admin`, refuses ambiguity, and never prints credentials or links.

The Supabase service-role/secret key is server-side bootstrap input only and is
never an application runtime or browser variable.

