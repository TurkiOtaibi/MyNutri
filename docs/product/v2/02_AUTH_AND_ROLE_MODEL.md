# V2 Authentication and Role Model

## CURRENT implementation versus APPROVED TARGET

The Supabase/email authentication, JWT admission, lifecycle saga and bootstrap sections below describe the CURRENT implemented repository state, not proof of production deployment. Email-based self-service recovery is currently implemented in `/auth/forgot-password` and `/auth/reset-password`. They remain current contracts until replacement is implemented and released; the target below is not live. Authority for the replacement: Product Owner decisions of **17 October 2026**, BRD AUT/PRF/USM decision tables and the cited requirements. Issues #110–#114 implement the login transition; issue #109 implements the separate sex-correction exception.

## APPROVED TARGET — not yet implemented

| Target rule | Decision / requirement (17 October 2026) |
|---|---|
| In-house login with «اسم المستخدم» and «كلمة المرور»; remove Supabase Auth and email everywhere in the system. Username is immutable after account creation. | AUT/USM final username/provider-removal decisions; BR-AUT-001, BR-AUT-012, BR-USM-022, BR-USM-023, BR-USM-036 |
| No MFA and no self-service password recovery. The Admin resets a forgotten password; display «ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف.». | AUT no-MFA decision; BR-AUT-003, BR-AUT-012, BR-USM-030 |
| After 5 consecutive failed login attempts, lock the account. A normal user unlocks only through an Admin password reset; the single Admin unlocks automatically after 30 minutes. A successful login resets the failure counter. | BR-AUT-011, BR-USM-030; final AUT/USM lock decisions |
| Force password change only for the initial password set by the Admin, before using the system. An Admin reset unlocks the user and permits direct login with the reset password, without another forced change. There is no independent unlock action. | BR-AUT-007, BR-AUT-008, BR-USM-030; final AUT/USM decisions superseding reset-time forced change and «فتح القفل» |
| In «بياناتي», self-service «تغيير كلمة المرور» requires the correct current password and signs out the owner's other devices. Admin reset signs the user out of all devices. | BR-PRF-024, BR-PRF-025, BR-PRF-026, BR-USM-030, BR-USM-033 |
| Minimum password length is 8, enforced by the backend, with «استخدم 8 أحرف على الأقل.» and «كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.». | AUT/USM password-length decision; BR-AUT-004, BR-AUT-007, BR-PRF-024, BR-PRF-025, BR-USM-023 |
| Admin-created normal accounts only; one Admin, no role assignment or self-registration through the product. The only Admin write to another user's Profile is correction of «الجنس»; all other Profile, Diary, plan and Labs access remains read-only. | BR-AUT-009, BR-USM-020, BR-USM-027, BR-USM-028, BR-PRF-006, BR-USM-032, BR-USM-061, BR-USM-067, BR-USM-074 |
| At cutover delete all current test accounts and their private data, keep the Food list, and create the single Admin through a server-side command that can also reset its password. | AUT/USM/FOD cutover decisions; related BR-USM-027, BR-USM-043; operational command required by issue #100 |

The final 17 October decisions supersede the earlier same-day email-as-login decision, forced change after every reset, separate «فتح القفل» / «تم فتح قفل الحساب.» action, and shorter contact-Admin sentence. Use the final requirements above, not those superseded entries.

Username format, length, allowed characters, normalization/uniqueness rules, credential representation, session transport/storage/lifetime and command interface are **to be decided in issue #110**; the BRD does not define those implementation details. Case-insensitive partial Admin search is already specified by BR-USM-005 and must not be mistaken for an approved username identity-normalization rule. No schema or API for this target is approved by this documentation change. (17 October 2026, BR-AUT-001/011/017, BR-USM-005/022/025/036; issue #100.)

## CURRENT implementation details


The Admin-managed lifecycle in this document is approved authority implemented
in the lifecycle revision; Production activation remains a separate release action.

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
the user's existing Supabase sessions through FastAPI), enable/disable, and
request permanent deletion. Email changes are not supported. Passwords are never
persisted, logged, or returned by myNutri. Password reset and status changes
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

`PrincipalContext` contains `principal_id`, `auth_user_id`, and `role`.

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
