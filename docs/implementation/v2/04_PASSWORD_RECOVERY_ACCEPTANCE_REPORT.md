# Password recovery provider acceptance

## Status

`PENDING — isolated local provider CI required`

This report is intentionally not a provider PASS record until the dedicated GitHub Actions gate succeeds on the reviewed head. The authorized functional provider gate uses Supabase CLI 2.111.0 to start disposable local Supabase Auth and Postgres services plus its bundled Mailpit mailbox. It exercises provider-generated recovery email and links without a hosted project, external SMTP, shared credential, or shared database.

Hosted SMTP deliverability, hosted-platform availability, email reputation, and production-provider latency are explicitly outside this functional gate and may be covered by a separate release smoke.

## Verified SDK contract

- Installed `@supabase/supabase-js`: `2.110.7`
- Installed `@supabase/auth-js`: `2.110.7`
- Installed `@supabase/ssr`: `0.12.3`
- Official password recovery guidance: <https://supabase.com/docs/guides/auth/passwords#resetting-a-password>
- Official auth event contract: <https://supabase.com/docs/reference/javascript/auth-onauthstatechange>
- Official client initialization contract: <https://supabase.com/docs/reference/javascript/auth-initialize>

The installed SDK and current official documentation agree that:

1. `resetPasswordForEmail` sends the recovery request and redirects through an allowed recovery URL.
2. A successful recovery redirect establishes a session and emits `PASSWORD_RECOVERY` instead of ordinary `SIGNED_IN`.
3. `updateUser` requires an authenticated session.

The frontend therefore treats only a `PASSWORD_RECOVERY` event carrying a session as recovery-ready. A merely existing signed-in session is insufficient.

## Deterministic state matrix

| Input/event | Resulting UI state | Permitted action |
|---|---|---|
| Recovery request not started | idle | submit one validated request |
| Recovery request in flight | requesting | duplicate submit blocked |
| Provider returns success for any address | neutral-sent | no account-existence signal |
| Provider returns an error, rejects, or aborts | retryable failure | one new retry after lock release |
| Reset page before auth initialization settles | checking-session | password update blocked |
| Missing/expired recovery context | invalid/expired | password update blocked |
| `PASSWORD_RECOVERY` with a session | ready | one password update allowed |
| Password update in flight | updating | duplicate update blocked |
| Provider update failure or rejection | retryable failure | input preserved; one retry allowed |
| Provider update success | success | redirect to Diary |
| Sign-out, subject replacement, or successful user update | invalid/expired | stale recovery action blocked |

All displayed failures use application-owned generic Arabic copy. Raw provider messages are not rendered.

## Local deterministic evidence

The loopback fixture covers neutral recovery requests, deterministic provider failure, expired and reused recovery codes, one-use recovery sessions, and successful password update. Fixture diagnostics retain only operation, HTTP method, pathname, and status; they do not retain email addresses, recovery codes, access tokens, or passwords.

The browser suite covers returned request failure, network abort, retry, duplicate-action locks, missing and expired recovery state, failed update with preserved input, successful update, refresh, sign-out invalidation, mobile layout, and accessibility.

## Required isolated local provider gate

The mandatory `Plan 020 provider acceptance` GitHub Actions job must establish all of the following against its loopback-only stack before the implementation can be reviewed for merge:

- equivalent public recovery-request behavior for known and unknown addresses;
- actual Auth recovery-email generation and Mailpit delivery;
- use of the exact provider-generated recovery link and allowlisted application redirect;
- `PASSWORD_RECOVERY` session establishment rather than URL-only readiness;
- missing-session, expired-link, reused-link, and replaced-subject rejection;
- exactly one authenticated password update and one final redirect;
- subsequent login with the new password and rejection of the previous password;
- Back, Forward, reload, duplicate-action, session-isolation, keyboard, mobile, and accessibility behavior;
- secret-safe failure diagnostics and unconditional disposable-resource cleanup.

The job obtains its local values from `supabase status` and masks key-like values immediately. The public key reaches only the loopback application and provider tests, the database URL reaches only the local migration process, and the administrative key reaches only provider-test discovery and execution. It must not call `supabase login`, `supabase link`, `supabase db push`, or any hosted API. The final provider run records the reviewed commit and sanitized scenario outcomes without recording an email address, recovery link, verifier, token, password, cookie, authorization header, mailbox body, or provider key.

The provider job deliberately does not start the application Backend: its browser scenarios exercise Auth, Mailpit, recovery lifecycle, and cross-context subject ownership only. Private draft/cache isolation remains certified by the normal database-backed Playwright regression gate, including Plan 016, in the same required CI pipeline. Neither gate alone is described as proving the other contract.

Synthetic passwords are generated at runtime and never retained in diagnostics. The provider flow checks coherent focus during duplicate locking and rejected login, plus the existing login password-visibility control. The recovery form currently has no visibility toggle, so the gate does not manufacture or claim one.
