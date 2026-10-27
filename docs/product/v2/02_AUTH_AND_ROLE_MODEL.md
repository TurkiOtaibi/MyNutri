# V2 Authentication and Role Model

## CURRENT implementation versus APPROVED TARGET

CURRENT in #110: the backend supports internal username/password login alongside the existing Supabase/email browser flow. Internal credentials take precedence: any account with an internal password hash is rejected on the Supabase JWT path with `INTERNAL_LOGIN_REQUIRED`. Internal password changes and resets never update Supabase; accounts without internal credentials retain the existing JWT path. Frontend integration (#111), username-based Admin UI (#112), provider/email removal (#113), and destructive cutover (#114) remain APPROVED TARGET, not implemented or deployed by this change. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## APPROVED TARGET — backend delivered in #110; UI/removal/cutover pending

| Target rule | Decision / requirement (17 October 2026) |
|---|---|
| In-house login with «اسم المستخدم» and «كلمة المرور»; remove Supabase Auth and email everywhere in the system. Username is immutable after account creation; duplicate usernames are rejected. | AUT/USM final username/provider-removal decisions; BR-AUT-001, BR-AUT-012, BR-USM-022, BR-USM-023, BR-USM-025, BR-USM-036 |
| No MFA and no self-service password recovery. The Admin resets a forgotten password; display «ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف.». | AUT no-MFA decision; BR-AUT-003, BR-AUT-012, BR-USM-030 |
| After 5 consecutive failed login attempts, lock the account. A normal user unlocks only through an Admin password reset; the single Admin unlocks automatically after 30 minutes. A successful login resets the failure counter. | BR-AUT-011, BR-USM-030; final AUT/USM lock decisions |
| Force password change only for the initial password set by the Admin, before using the system. An Admin reset unlocks the user and permits direct login with the reset password, without another forced change. There is no independent unlock action. | BR-AUT-007, BR-AUT-008, BR-USM-030; final AUT/USM decisions superseding reset-time forced change and «فتح القفل» |
| In «بياناتي», self-service «تغيير كلمة المرور» requires the correct current password and signs out the owner's other devices. Admin reset signs the user out of all devices. | BR-PRF-024, BR-PRF-025, BR-PRF-026, BR-USM-030, BR-USM-033 |
| Minimum password length is 8, enforced by the backend, with «استخدم 8 أحرف على الأقل.» and «كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.». | AUT/USM password-length decision; BR-AUT-004, BR-AUT-007, BR-PRF-024, BR-PRF-025, BR-USM-023 |
| Admin-created normal accounts only; one Admin, no role assignment or self-registration through the product. The only Admin write to another user's Profile is correction of «الجنس»; all other Profile, Diary, plan and Labs access remains read-only. | BR-AUT-009, BR-USM-020, BR-USM-027, BR-USM-028, BR-PRF-006, BR-USM-032, BR-USM-061, BR-USM-067, BR-USM-074 |
| At cutover delete all current test accounts and their private data, keep the Food list, and create the single Admin through a server-side command that can also reset its password. | AUT/USM/FOD cutover decisions; related BR-USM-027, BR-USM-043; operational command required by issue #100 |

The final 17 October decisions supersede the earlier same-day email-as-login decision, forced change after every reset, separate «فتح القفل» / «تم فتح قفل الحساب.» action, and shorter contact-Admin sentence. Use the final requirements above, not those superseded entries.

Username identity is 3–32 ASCII English letters, digits, `.`, `_`, or `-`, with a unique lowercase normalized value. Passwords use standard-library scrypt with a random per-password salt; sessions use opaque random bearer tokens in the Authorization header, store only SHA-256 token hashes, and use no cookies. The implementation proposes a 30-day sliding inactivity expiry for Product Owner approval. Existing accounts retain null internal credentials. These details replace the former “to be decided in issue #110” placeholders. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## CURRENT implementation details


The Admin-managed lifecycle in this document is approved authority implemented
in the lifecycle revision; Production activation remains a separate release action.

## Authentication

The current browser still authenticates with Supabase Auth using email/password and sends `Authorization: Bearer <jwt>`. The backend also accepts internal opaque bearer sessions; JWT admission is refused once `principal.password_hash` is non-null. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

FastAPI verifies asymmetric Supabase JWTs against the project JWKS endpoint and
validates signature algorithm, issuer, audience, expiry, and UUID subject. JWKS
cache behavior must permit key rotation and fail closed. Production requires
Supabase configuration at startup.

The implementation follows the current official guidance:

- https://supabase.com/docs/guides/auth/jwts
- https://supabase.com/docs/guides/auth/server-side/creating-a-client?framework=nextjs
- https://supabase.com/docs/guides/auth/jwt-fields

## Principal

The current `principal` model has:

- `auth_user_id UUID UNIQUE NULL` for safe brownfield expansion;
- `email VARCHAR(320) NULL`;
- `display_name VARCHAR(120) NULL`;
- `role TEXT NOT NULL CHECK (role IN ('user','admin'))`;
- existing `status`, `created_at`, and `updated_at` remain authoritative.

Automatic Principal provisioning for unknown Supabase identities is retired.
Principals are created only by Admin account management or the bootstrap tool
for the single Admin. Unknown or non-active (`provisioning`, `disabled`,
`deleting`, or `deleted`) identities receive `401 INVALID_CREDENTIAL`; existing
Principals remain intact. User metadata never grants role or status. Public
self-registration is removed from the product and must be disabled at the
Supabase Auth configuration boundary, not merely hidden in the frontend.

Exactly one Admin is allowed. A partial unique index on `role='admin'` enforces
at most one; bootstrap refuses if an Admin already exists, and release preflight
must establish that one Admin exists. No product API creates or changes an Admin
role. The Admin cannot change their own role, disable, or delete themselves.

An Admin creates normal users with email, display name, and an initial password
they set; they may edit display name, reset password (including revocation of
the user's internal sessions when an internal hash exists, otherwise existing Supabase sessions through FastAPI), enable/disable, and
request permanent deletion. Email changes are not supported. Raw passwords are never persisted, logged, or returned by myNutri; internal accounts store only the versioned scrypt hash. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.) Legacy password reset and status changes
set `sessions_valid_after` to the next whole second. FastAPI compares that
cutoff to the latest valid Supabase
`amr[].timestamp` authentication time, not access-token `iat`; missing or
malformed AMR always fails closed, so refreshing an older
session cannot restore admission. The supported Admin password-update call
also revokes Supabase refresh sessions. Creation commits a `provisioning`
Principal and idempotency key before calling Supabase Auth; the same-key retry
resumes creation and activation. Before the create call, the Principal also
stores a backend-generated Supabase Auth UUID; the call uses that pre-assigned
ID and records `identity_requested_at` for every attempt. The explicit bounded
Admin HTTP timeout determines the creation lease:
`max(5 minutes, 10 x timeout)`. Deleting `provisioning` within the lease is
refused with 409 and the approved creation-incomplete copy. `provisioning`
never authenticates.

Deletion of a `provisioning` account is allowed and follows the same saga as
deletion of another normal-user account: commit `deleting` under the Principal
lock, purge private dependent data in one locked transaction, delete the stored
Supabase Auth UUID and verify absence through the supported Admin API (absence
is success), then mark a scrubbed, unlinked `deleted` tombstone. Its email and
display name are erased; its pre-assigned UUID moves to a unique, permanent
`retired_auth_user_id` that is never eligible for admission. Failure leaves a
locked-out `deleting` account for Admin-visible retry. Supabase JWTs issued
before deletion are denied by the existing per-request Principal status check.
Create retry is refused after `deleting` is committed. Unknown and retired
Auth UUIDs also receive 401 `INVALID_CREDENTIAL`.

The completed-deletion guarantee is permanent denial of myNutri admission,
including if an in-flight provider create finishes late. Such a late identity
is removed by idempotent reconciliation using its retired UUID, followed by an
absence check. Reconciliation runs after completed/retried deletion, in a
bounded non-blocking batch for tombstones deleted within the last 30 days when
the Admin list loads, through a full-sweep ops command, and before a new
account create if Supabase reports an email taken by a retired UUID. A
non-retired duplicate keeps the approved duplicate-email error. Failures are
sanitized, logged by count/type only, and retried at the next trigger; they
never recreate private data or reactivate a tombstone.

`PrincipalContext` contains `principal_id`, optional `auth_user_id`, `role`, `username`, `must_change_password`, and the internal `session_id` when applicable. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## Errors

- Missing credentials: `401 AUTHENTICATION_REQUIRED`.
- Invalid/expired/wrong-project credentials: `401 INVALID_CREDENTIAL`.
- Non-active or missing linked Principal: `401 INVALID_CREDENTIAL`.
- Authenticated but unauthorized: `403 FORBIDDEN`.
- Owner-scoped object lookup remains non-enumerating `404`.

## Bootstrap

The admin bootstrap is a dry-run-first command. It links an explicitly selected
Supabase Auth UUID to the existing Principal or creates/invites an identity via
the Supabase Admin API when explicitly requested. It preserves `Principal.id`,
sets role `admin`, refuses ambiguity, and never prints credentials or links.

The Supabase service-role/secret key may be used by the bootstrap tool and at
FastAPI runtime only for Admin account-management creation, password reset,
and Auth identity deletion. No other runtime path may use it. It is backend-only,
never `NEXT_PUBLIC_`, logged, or returned. The frontend never calls privileged
Supabase Auth operations directly.


## CURRENT internal authentication backend (#110)

The 27 October 2026 Product Owner decision keeps credentials separate and does not extend the privileged Supabase boundary above. Internal Admin reset dispatches by the target's stored credential, not a client-selected mode; it never calls Supabase when an internal hash exists. Legacy-only reset retains the provider operation and JWT cutoff. No existing email or username is migrated. (BR-AUT-017, BR-PRF-024–026, BR-USM-030/033.)

| Endpoint | Contract |
|---|---|
| `POST /auth/login` | Username/password to a bearer token returned once, expiry, and account/role/forced-change flag. Unknown usernames perform one dummy scrypt verification and return the same generic failure as a wrong password. Inactive accounts cannot log in; a correct password on a disabled account returns `ACCOUNT_DISABLED`. |
| `POST /auth/logout` | Internal session only; revoke the caller's current session. Legacy browser logout remains with Supabase until #113. |
| `POST /auth/change-password` | Internal session and correct current password required; minimum 8, maximum 256 characters; clear initial-change flag and revoke only other internal sessions. Supabase credentials are untouched and cannot admit this account. |
| `GET /account/me` | Account, role, username and forced-change flag, with nullable legacy Auth ID; no secrets. |
| `PUT /admin/accounts/{principal_id}/password` | Existing Admin-only reset, never self-targeting: internal target resets hash, clears counter/lock, does not force another change, revokes all sessions; legacy-only target uses the existing Supabase reset. |

These endpoints implement BR-AUT-001/004/005/007/008/010/011/015/017, BR-PRF-024–026 and BR-USM-030/033 (17/27 October 2026). Login returns enough account state to route an initial password change; until that change, all authenticated product endpoints, including `/account/me`, are refused with `PASSWORD_CHANGE_REQUIRED`, except POST change-password and logout. Public health/login remain available. Five consecutive failures lock a normal user until Admin reset; Admin unlocks at 30 minutes, and successful login clears the counter. Every internal admission rechecks active status, revocation and expiry. Disable/delete revoke sessions under the Principal lock; deletion purges sessions and scrubs credentials while preserving the Principal tombstone and Food attribution.

Implementation choices proposed for approval: scrypt `n=32768, r=8, p=1`, 16 random salt bytes, 64-byte derived key, explicit 64 MiB maxmem; at most two concurrent hashes per worker limits hashing memory to roughly 64 MiB. The versioned stored encoding carries parameters/salt/hash and accepts only reviewed parameter sets. Tokens contain 32 random bytes, are never stored raw, and expire after 30 days without use; admission renews the inactivity deadline. No cookies, browser storage, offline queue or new dependency is introduced.

The server-side command is `python -m app.ops.internal_admin create --username <username>` or `reset --username <username>`. It prompts without echo or accepts one line via `--password-stdin`; passwords are never command arguments or logs. Create refuses any existing Admin (including a legacy Admin), and sets the initial-change flag. Reset addresses the existing internal Admin, clears lock/counter/initial-change flag and revokes all sessions without touching Supabase. The database also enforces the single Admin. Running either command against production requires separate release authorization. (17/27 October 2026 AUT/USM decisions; BR-AUT-007/008/011, BR-USM-027/030; issue #110.)
