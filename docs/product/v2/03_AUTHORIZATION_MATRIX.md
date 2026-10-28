# V2 Authorization Matrix

## Approved permissions — implemented through #113; deployment separate

| Capability | User | Admin | Decision / requirement (17 October 2026) |
|---|---|---|---|
| Write any other field in another user's Profile, or another user's Diary/plans/Labs | No | No; selected-user access otherwise stays read-only | BR-USM-061, BR-USM-067, BR-USM-074 |
| Integrate internal reset/lock state into the Admin UI | No | Yes | Backend CURRENT in #110; UI CURRENT #112; BR-AUT-011, BR-USM-030/033 |
| Manage accounts by username, change username, or self-register | No account management or self-registration | Create normal users by username; cannot change username or assign roles | BR-AUT-009, BR-USM-022/027/028/036; issues #110–#112 |

No independent unlock permission is added: the final USM decision cancels that action. The final FOD decision also cancels «إيقاف الطعام»; the existing no-status/permanent-delete Food rules remain unchanged. (17 October 2026 USM/FOD decisions; BR-USM-030, BR-FOD-035.)


## CURRENT implemented authorization

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility, not an authentication path; #114 clears them only on selected legacy-user tombstones. New users are created atomically by immutable username. The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043).

| Capability | User | Admin |
| --- | --- | --- |
| Read/update own Profile | Yes | Yes |
| Preview/write/read own dated Target Plans | Yes | Yes |
| Read own Diary and summaries | Yes | Yes |
| Read shared Foods | Yes | Yes |
| Add shared Food to own Diary | Yes | Yes |
| Create/update/permanently delete Food | No | Yes |
| Read aggregate Food usage counts (Diary entries and distinct users only) | No | Yes |
| List users | No | Yes |
| Read another user's monitored data | No | Yes, read-only, only while the selected account is active or disabled (BR-USM-021; issue #137) |
| Correct another user's «الجنس» | No | Yes, only a saved Profile of another active/disabled user, with «تصحيح الجنس يغيّر حساب الأهداف وتقييم نتائج التحاليل.» (17 October 2026; BR-PRF-006, BR-USM-032/061; #109) |
| Mutate any other field in another user's Profile, or their Diary/Plans | No | No |
| Assign roles | No | No through product APIs |
| Self-register or auto-provision from an unknown Auth identity | No | No |
| Create a normal user with Admin-set initial password | No | Yes, by immutable username through FastAPI; atomic internal-only creation, no email/provider call (#112; BR-USM-022/023/025/027/036) |
| Edit another user's display name or reset password | No | Yes, normal users only; internal reset unlocks without forced change and revokes all internal sessions, no external call; legacy-only reset is refused (17/27 October 2026; BR-USM-030/033; #110) |
| Change own internal password with correct current password | Yes | Yes; current session survives, other sessions revoked; no external update; Profile UI CURRENT #111 (17/27 October 2026; BR-PRF-024–026; #110/#111) |
| Enable/disable or permanently delete another account | No | Yes, normal users only; internal-only deletion uses username confirmation and no provider calls; legacy `provisioning` accounts use the local locked purge and scrubbed tombstone (#112; BR-USM-038/042/043) |
| Change username, legacy email or grant/change Admin role | No | No |
| Disable/delete own Admin account | No | No |
| Read authenticated Labs catalog | Yes | Yes |
| Read own Labs overview/detail/history | Yes | Yes, read-only |
| Create/edit/delete own LabResult | Yes | No, including admin's own results |
| Read another user's Labs overview/detail/history | No | Yes, selected-user read-only, only while the selected account is active or disabled (BR-USM-021; issue #137) |
| Mutate another user's Labs | No | No |

## Enforcement

- Normal services infer ownership from `PrincipalContext`; they accept no user ID.
- Exactly one Admin is enforced by a partial unique database index and guarded
  bootstrap; account-management APIs never accept a role change. Admin account
  mutations cannot target the Admin's own account.
- Unknown, `provisioning`, `disabled`, `deleting`, and `deleted` identities fail
  authentication with `401 INVALID_CREDENTIAL`. Even a previously issued token
  fails after `deleting` is committed because Principal status is checked per request.
- Admin account management is distinct from selected-user monitoring. Its sole
  private-data write is `PUT /admin/accounts/{principal_id}/profile/sex`, restricted
  to another active/disabled user's saved Profile. It changes only sex under
  Principal then Profile locks; other fields, timestamps, plans, Diary and Labs
  rows remain unchanged. The owner's sex lock remains. New target saves use the
  corrected sex; Labs evaluations use it on fresh reads. (17 October 2026 decision; BR-PRF-006, BR-USM-032/061; issue #109.)
- Every writer of Principal-owned private data locks the Principal first and
  rechecks `active` before writing, including receipt replay paths. The sex-only
  Admin correction also permits a `disabled` target (BR-USM-032; issue #109). No write
  can follow the locked purge of a `deleting` Principal.
Session-admission metadata is the narrow exception: #128 permits a conditional refresh of an existing unrevoked, unexpired session after five minutes without a Principal lock; it cannot insert or revive sessions. Revocation writers retain their existing lock order and every admission rechecks status (BR-AUT-017; approved 30-day sliding lifetime, 27 October 2026).
- Admin monitoring has dedicated `/admin/users/...` read routes.
- Admin-selected IDs never replace the caller's `PrincipalContext`.
- Shared Food reads are global; no archive state exists.
- Food writes require an explicit admin dependency in FastAPI.
- Permanent Food deletion cascades to every referencing Diary entry across all Principals.
- Cross-owner private lookups are non-enumerating.
- Target Plan writes are Principal-scoped, require idempotency, and accept only
  effective dates on or after the database-derived Riyadh Diary date. Target
  Plan history and date resolution never expose another Principal's plans.
- Authorization is tested with User A, User B, and Admin fixtures.
- Labs owner routes derive Principal from `PrincipalContext`; no write payload
  accepts an owner ID. Selected-user IDs occur only on the two admin read routes
  listed in V2 11. Cross-owner result IDs return the existing non-enumerating 404.
- Labs writes recheck current actor status/role under the Principal lock, before
  receipt replay. All admin writes return 403. Direct `lab_result` privileges are
  revoked from `PUBLIC`, `anon`, and `authenticated`; no admin mutation route exists.
