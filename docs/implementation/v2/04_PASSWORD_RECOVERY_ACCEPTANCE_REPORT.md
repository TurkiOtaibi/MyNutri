# Password recovery provider acceptance

## Status

`PENDING — isolated non-production provider authorization required`

This report is intentionally not a provider PASS record. The implementation and loopback fixture may be verified locally and in CI, but they do not prove hosted email delivery, redirect allowlisting, expiry, or one-time-link behavior. No shared or production Supabase project, mailbox, credential, or environment was used.

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

## Required isolated non-production gate

An explicitly authorized isolated non-production Supabase project and test mailbox must establish all of the following before Plan 020 can be marked DONE:

- recovery email delivery
- configured recovery redirect
- `PASSWORD_RECOVERY` session establishment
- expired-link rejection
- reused-link rejection
- password update
- subsequent login with the new password

The final provider run must record the environment class, reviewed frontend commit, date, and reviewer without recording a project identifier, email address, token, password, authorization header, or provider secret.
