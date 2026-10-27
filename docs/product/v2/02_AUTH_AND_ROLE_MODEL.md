# V2 Authentication and Role Model

## CURRENT implementation versus APPROVED TARGET

CURRENT in #111: the browser uses internal username/password login, opaque bearer sessions, forced initial-password change, and own-password change in Profile. Only the session token is persisted in localStorage; passwords stay in memory and no auth cookies are used. Reload during an initial-password change requires re-authentication. Forgotten/reset-password browser flows are absent; forgotten passwords go to the Admin. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; an internal password hash takes precedence and rejects JWT admission with `INTERNAL_LOGIN_REQUIRED`. Internal password changes/resets never update Supabase. Admin username-based creation and management UI is CURRENT in #112: new users have internal credentials only, with no email or provider call. Legacy backend email/provider lifecycle support and clearly marked email fallback for existing accounts remain until #113/#114; provider/email removal (#113) and destructive cutover (#114) remain APPROVED TARGET. No existing account migration or cutover is performed. This describes repository implementation, not deployment. (Product Owner decisions of 17 and 27 October 2026; issues #110/#111/#112; BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054; BR-AUT-001/003/004/005/007/008/010/011/012/017, BR-PRF-024–026, BR-USM-030/033.)

## Approved rules — backend #110, browser #111 and Admin UI #112; removal/cutover pending

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

Username identity is 3–32 ASCII English letters, digits, `.`, `_`, or `-`, with a unique lowercase normalized value. Passwords use standard-library scrypt with a random per-password salt; sessions use opaque random bearer tokens in the Authorization header, store only SHA-256 token hashes on the backend, and use no cookies; the browser persists only the raw session token in localStorage (#111). The Product Owner approved the 30-day sliding inactivity expiry for #111 on 27 October 2026. Existing accounts retain null internal credentials unless the explicitly authorized existing-Admin attach command is run. These details replace the former “to be decided in issue #110” placeholders. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## CURRENT implementation details


The Admin-managed lifecycle in this document is approved authority implemented
in the lifecycle revision; Production activation remains a separate release action.

## Authentication

The browser authenticates with internal username/password through `POST /auth/login` and sends the opaque token as `Authorization: Bearer <token>`. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; JWT admission is refused once `principal.password_hash` is non-null. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

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

An Admin creates normal users with immutable username, display name, and an initial password (#112; BR-USM-022/023/025/036)
they set; they may edit display name, reset password (including revocation of
the user's internal sessions when an internal hash exists, otherwise existing Supabase sessions through FastAPI), enable/disable, and
request permanent deletion. Email changes are not supported. Raw passwords are never persisted, logged, or returned by myNutri; internal accounts store only the versioned scrypt hash. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.) Legacy password reset and status changes
set `sessions_valid_after` to the next whole second. FastAPI compares that
cutoff to the latest valid Supabase
`amr[].timestamp` authentication time, not access-token `iat`; missing or
malformed AMR always fails closed, so refreshing an older
session cannot restore admission. The supported Admin password-update call
also revokes Supabase refresh sessions. Legacy email/provider creation commits a `provisioning`
Principal and idempotency key before calling Supabase Auth; the same-key retry
resumes creation and activation. Before the create call, the Principal also
stores a backend-generated Supabase Auth UUID; the call uses that pre-assigned
ID and records `identity_requested_at` for every attempt. The explicit bounded
Admin HTTP timeout determines the creation lease:
`max(5 minutes, 10 x timeout)`. Deleting `provisioning` within the lease is
refused with 409 and the approved creation-incomplete copy. `provisioning`
never authenticates.

Legacy provider-linked deletion of a `provisioning` account is allowed and follows the same saga as
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
| `POST /auth/logout` | Internal session only; revoke the caller's current session. The current browser uses this endpoint and clears its local token on logout even if remote revocation fails; the failure is shown explicitly (BR-NAV-008/009). |
| `POST /auth/change-password` | Internal session and correct current password required; minimum 8, maximum 256 characters; clear initial-change flag and revoke only other internal sessions. Supabase credentials are untouched and cannot admit this account. |
| `GET /account/me` | Account, role, username and forced-change flag, with nullable legacy Auth ID; no secrets. |
| `PUT /admin/accounts/{principal_id}/password` | Existing Admin-only reset, never self-targeting: internal target resets hash, clears counter/lock, does not force another change, revokes all sessions; legacy-only target uses the existing Supabase reset. |

These endpoints implement BR-AUT-001/004/005/007/008/010/011/015/017, BR-PRF-024–026 and BR-USM-030/033 (17/27 October 2026). Login returns enough account state to route an initial password change; until that change, all authenticated product endpoints, including `/account/me`, are refused with `PASSWORD_CHANGE_REQUIRED`, except POST change-password and logout. Public health/login remain available. Five consecutive failures lock a normal user until Admin reset; Admin unlocks at 30 minutes, and successful login clears the counter. Every internal admission rechecks active status, revocation and expiry. Disable/delete revoke sessions under the Principal lock; deletion purges sessions and scrubs credentials while preserving the Principal tombstone and Food attribution.

Implementation choices proposed for approval: scrypt `n=32768, r=8, p=1`, 16 random salt bytes, 64-byte derived key, explicit 64 MiB maxmem; at most two concurrent hashes per worker limits hashing memory to roughly 64 MiB. The versioned stored encoding carries parameters/salt/hash and accepts only reviewed parameter sets. Tokens contain 32 random bytes and are never stored raw on the backend. The approved inactivity expiry is 30 days, renewed on admission. In #111 the browser stores only the raw session token in localStorage; passwords and pending initial-password state remain in memory. No auth cookies, offline queue or new dependency is introduced.

The server-side command is `python -m app.ops.internal_admin create --username <username>` or `reset --username <username>`. It prompts without echo or accepts one line via `--password-stdin`; passwords are never command arguments or logs. Create refuses any existing Admin (including a legacy Admin), and sets the initial-change flag. Reset addresses the existing internal Admin, clears lock/counter/initial-change flag and revokes all sessions without touching Supabase. The database also enforces the single Admin. Running either command against production requires separate release authorization. (17/27 October 2026 AUT/USM decisions; BR-AUT-007/008/011, BR-USM-027/030; issue #110.)

Issue #111 adds `python -m app.ops.internal_admin attach --username <username>` for the existing active legacy Admin only. It refuses any existing internal username/normalized username/hash, attaches internal credentials to the same Principal with `must_change_password=false`, and preserves legacy identity/email, role/status, private data and Food attribution. It does not call Supabase or revoke sessions; internal credential precedence rejects subsequent legacy JWT admission. Password input is hidden or supplied through `--password-stdin`, never an argument or log. This is a user-run release step requiring authorization for the exact production action and revision; it has not been executed by this change. Admin creation/reset, provider removal and destructive cutover retain their separate boundaries. (Product Owner #111 authorization, 27 October 2026; BR-AUT-017, BR-USM-027.)

## CURRENT username account management — issue #112

The Admin UI uses username, display name and initial password. Internal creation is one database transaction: an active normal-user Principal, unique normalized username, scrypt password hash, initial-change flag and idempotency key commit together or roll back together. It stores no email/Auth UUID and makes no provider call. A matching idempotency replay returns the same account; a conflicting request is rejected. Username is immutable, including retries; only legacy provider provisioning retains its resumable creation saga. (BR-USM-022/023/025/027/028/036/049; final USM decisions, 17 October 2026; [issue #112](https://github.com/TurkiOtaibi/MyNutri/issues/112).)

Admin list and selected-user summary expose username, nullable `last_login_at` and `is_locked`. Search matches literal partial username/display name case-insensitively, with email fallback only for legacy accounts lacking username. «مقفل» is a filter and badge, not a lifecycle status; it reflects a normal internal user's lock, never the Admin's transient lock. Each row displays «آخر دخول» and Gregorian registration dates. Existing accounts without username remain clearly marked as legacy; no username or login date is inferred. Reset shows «سيخرج المستخدم من كل أجهزته.», clears an internal user's lock and sessions, and does not force another password change. Self rows have no account actions. (BR-USM-005/006/013/014/017/020/030/033/054; final USM decisions, 17 October 2026.)

Deletion selects confirmation from the stored target identity: username for internal accounts, retained email fallback for legacy accounts without username. The approved instruction is «اكتب اسم المستخدم لتأكيد الحذف النهائي.» and mismatch is «اسم المستخدم المدخل لا يطابق هذا الحساب.». Internal-only deletion performs no provider call or provider reconciliation; it locks out the account, purges private data/sessions and scrubs username, normalized username, password/lock/login fields, email and display name on the durable tombstone. The cleared username can be reused by a new Principal without restoring deleted data. Food attribution keeps the original tombstone ID. Provider-linked accounts retain their legacy deletion/reconciliation safeguards. (BR-USM-012/038/042/043/044; [Product Owner decision, 27 October 2026](https://github.com/TurkiOtaibi/MyNutri/issues/112#issuecomment-6437936388).)

This repository change adds no migration and performs no existing-account conversion, provider removal, production action or cutover. Legacy backend flows remain until #113/#114; the system-wide no-email/no-provider target is not yet current.
