# V2 Authentication and Role Model

## CURRENT implementation versus APPROVED TARGET

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility until #114, not an authentication path. New users are created atomically by immutable username. No account conversion, destructive cutover, deployment or production configuration change is performed. Cutover #114 remains APPROVED TARGET. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043).

## Approved rules — backend #110, browser #111 and Admin UI #112; provider removal CURRENT #113; cutover pending #114

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

## Authentication and Principal

The browser calls `POST /auth/login` with username/password and sends the opaque
session token as `Authorization: Bearer <token>`. FastAPI admits only internal
sessions, rechecking active Principal status, expiry and revocation on every request.
JWT credentials and legacy-only accounts cannot authenticate. Supabase Auth and
its configuration, JWKS/AMR verification and privileged operations are removed (#113).
Supabase PostgreSQL hosting remains available through `DATABASE_URL`.

`Principal.id` remains the durable ownership key. Existing nullable identity/email
columns are retained as historical data until #114, with no admission authority.
Exactly one Admin is allowed: the partial unique role index prevents a second and
the internal Admin command enforces the same rule. No product API assigns roles,
self-registers users, or disables/deletes the Admin's own account.

Admin creation is atomic and username-only. Reset revokes every internal session;
legacy-only reset is refused because no internal credential exists. Local deletion
locks out the account, purges private dependents/sessions and scrubs the durable
Principal tombstone while preserving all Food attribution IDs. Local failure stays
retryable and cannot revive private data. External creation/deletion sagas and
reconciliation are removed; historical provisioning status grants no admission.
`PrincipalContext` carries Principal, role, username, forced-change and session state;
retained optional legacy identity fields are inert compatibility data.

## Errors

- Missing credentials: `401 AUTHENTICATION_REQUIRED`.
- Invalid or expired credentials: `401 INVALID_CREDENTIAL`.
- Authenticated but unauthorized: `403 FORBIDDEN`.
- Owner-scoped object lookup remains non-enumerating `404`.
- Internal login/session status and forced-change errors retain the approved Arabic copy.

## CURRENT internal authentication backend (#110)

Internal credentials and sessions are the only authentication authority in #113. Existing accounts are not migrated.

| Endpoint | Contract |
|---|---|
| `POST /auth/login` | Username/password to a bearer token returned once, expiry, and account/role/forced-change flag. Unknown usernames perform one dummy scrypt verification and return the same generic failure as a wrong password. Inactive accounts cannot log in; a correct password on a disabled account returns `ACCOUNT_DISABLED`. |
| `POST /auth/logout` | Internal session only; revoke the caller's current session. The current browser uses this endpoint and clears its local token on logout even if remote revocation fails; the failure is shown explicitly (BR-NAV-008/009). |
| `POST /auth/change-password` | Internal session and correct current password required; minimum 8, maximum 256 characters; clear initial-change flag and revoke only other internal sessions. No external credential is read or updated. |
| `GET /account/me` | Account, role, username and forced-change flag, with nullable legacy Auth ID; no secrets. |
| `PUT /admin/accounts/{principal_id}/password` | Existing Admin-only reset, never self-targeting: internal target resets hash, clears counter/lock, does not force another change, revokes all sessions; legacy-only target is refused; no implicit conversion. |

These endpoints implement BR-AUT-001/004/005/007/008/010/011/015/017, BR-PRF-024–026 and BR-USM-030/033 (17/27 October 2026). Login returns enough account state to route an initial password change; until that change, all authenticated product endpoints, including `/account/me`, are refused with `PASSWORD_CHANGE_REQUIRED`, except POST change-password and logout. Public health/login remain available. Five consecutive failures lock a normal user until Admin reset; Admin unlocks at 30 minutes, and successful login clears the counter. Every internal admission rechecks active status, revocation and expiry. Disable/delete revoke sessions under the Principal lock; deletion purges sessions and scrubs credentials while preserving the Principal tombstone and Food attribution.

Implementation choices proposed for approval: scrypt `n=32768, r=8, p=1`, 16 random salt bytes, 64-byte derived key, explicit 64 MiB maxmem; at most two concurrent hashes per worker limits hashing memory to roughly 64 MiB. The versioned stored encoding carries parameters/salt/hash and accepts only reviewed parameter sets. Tokens contain 32 random bytes and are never stored raw on the backend. The approved inactivity expiry remains 30 days. Admission reads the current Principal status and session revocation/expiry without row locks; it refreshes last-used time and expiry only when the last refresh is older than five minutes, through one conditional update that excludes revoked or expired sessions. Normal admissions within that interval do not write. Existing revocation writers keep Principal-first locking, and committed revocation or non-active status is rejected on the next admission (issue #128; BR-AUT-017; approved 30-day lifetime, 27 October 2026). In #111 the browser stores only the raw session token in localStorage; passwords and pending initial-password state remain in memory. No auth cookies, offline queue or new dependency is introduced.

The server-side command is `python -m app.ops.internal_admin create --username <username>` or `reset --username <username>`. It prompts without echo or accepts one line via `--password-stdin`; passwords are never command arguments or logs. Create refuses any existing Admin (including a legacy Admin), and sets the initial-change flag. Reset addresses the existing internal Admin, clears lock/counter/initial-change flag and revokes all sessions without external calls. The database also enforces the single Admin. Running either command against production requires separate release authorization. (17/27 October 2026 AUT/USM decisions; BR-AUT-007/008/011, BR-USM-027/030; issue #110.)

Issue #111 adds `python -m app.ops.internal_admin attach --username <username>` for the existing active legacy Admin only. It refuses any existing internal username/normalized username/hash, attaches internal credentials to the same Principal with `must_change_password=false`, and preserves legacy identity/email, role/status, private data and Food attribution. It makes no external call or session revocation; all legacy JWT admission is removed in #113. Password input is hidden or supplied through `--password-stdin`, never an argument or log. This is a user-run release step requiring authorization for the exact production action and revision; it has not been executed by this change. Admin creation/reset and destructive cutover retain their separate authorization boundaries. (Product Owner #111 authorization, 27 October 2026; BR-AUT-017, BR-USM-027.)

## CURRENT username account management — issue #112

The Admin UI uses username, display name and initial password. Internal creation is one database transaction: an active normal-user Principal, unique normalized username, scrypt password hash, initial-change flag and idempotency key commit together or roll back together. It stores no email/Auth UUID and makes no provider call. A matching idempotency replay returns the same account; a conflicting request is rejected. Username is immutable, including retries; the legacy creation saga is removed in #113. (BR-USM-022/023/025/027/028/036/049; final USM decisions, 17 October 2026; [issue #112](https://github.com/TurkiOtaibi/MyNutri/issues/112).)

Admin list and selected-user summary expose username, nullable `last_login_at` and `is_locked`. Search matches literal partial username/display name case-insensitively, with email fallback only for legacy accounts lacking username. «مقفل» is a filter and badge, not a lifecycle status; it reflects a normal internal user's lock, never the Admin's transient lock. Each row displays «آخر دخول» and Gregorian registration dates. Existing accounts without username remain clearly marked as legacy; no username or login date is inferred. Reset shows «سيخرج المستخدم من كل أجهزته.», clears an internal user's lock and sessions, and does not force another password change. Self rows have no account actions. (BR-USM-005/006/013/014/017/020/030/033/054; final USM decisions, 17 October 2026.)

Deletion selects confirmation from the stored target identity: username for internal accounts, retained email fallback for legacy accounts without username. The approved instruction is «اكتب اسم المستخدم لتأكيد الحذف النهائي.» and mismatch is «اسم المستخدم المدخل لا يطابق هذا الحساب.». Internal-only deletion performs no provider call or provider reconciliation; it locks out the account, purges private data/sessions and scrubs username, normalized username, password/lock/login fields, email and display name on the durable tombstone. The cleared username can be reused by a new Principal without restoring deleted data. Food attribution keeps the original tombstone ID. Legacy-linked accounts use the same local purge and tombstone operation; no external deletion/reconciliation executes. (BR-USM-012/038/042/043/044; [Product Owner decision, 27 October 2026](https://github.com/TurkiOtaibi/MyNutri/issues/112#issuecomment-6437936388).)

Issue #113 removes provider authentication and lifecycle operations without a migration, existing-account conversion, production action or cutover. Existing legacy display/deletion confirmation remains until #114; historical columns do not enable login.
