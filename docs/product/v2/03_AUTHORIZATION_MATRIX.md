# V2 Authorization Matrix

## Approved permissions — implemented through #112; deployment separate

| Capability | User | Admin | Decision / requirement (17 October 2026) |
|---|---|---|---|
| Write any other field in another user's Profile, or another user's Diary/plans/Labs | No | No; selected-user access otherwise stays read-only | BR-USM-061, BR-USM-067, BR-USM-074 |
| Integrate internal reset/lock state into the Admin UI | No | Yes | Backend CURRENT in #110; UI CURRENT #112; BR-AUT-011, BR-USM-030/033 |
| Manage accounts by username, change username, or self-register | No account management or self-registration | Create normal users by username; cannot change username or assign roles | BR-AUT-009, BR-USM-022/027/028/036; issues #110–#112 |

No independent unlock permission is added: the final USM decision cancels that action. The final FOD decision also cancels «إيقاف الطعام»; the existing no-status/permanent-delete Food rules remain unchanged. (17 October 2026 USM/FOD decisions; BR-USM-030, BR-FOD-035.)


## CURRENT implemented authorization

CURRENT in #111: the browser uses internal username/password login, opaque bearer sessions, forced initial-password change, and own-password change in Profile. Only the session token is persisted in localStorage; passwords stay in memory and no auth cookies are used. Reload during an initial-password change requires re-authentication. Forgotten/reset-password browser flows are absent; forgotten passwords go to the Admin. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; an internal password hash takes precedence and rejects JWT admission with `INTERNAL_LOGIN_REQUIRED`. Internal password changes/resets never update Supabase. Admin username-based creation and management UI is CURRENT in #112: new users have internal credentials only, with no email or provider call. Legacy backend email/provider lifecycle support and clearly marked email fallback for existing accounts remain until #113/#114; provider/email removal (#113) and destructive cutover (#114) remain APPROVED TARGET. No existing account migration or cutover is performed. This describes repository implementation, not deployment. (Product Owner decisions of 17 and 27 October 2026; issues #110/#111/#112; BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054; BR-AUT-001/003/004/005/007/008/010/011/012/017, BR-PRF-024–026, BR-USM-030/033.)

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
| Read another user's monitored data | No | Yes, read-only |
| Correct another user's «الجنس» | No | Yes, only a saved Profile of another active/disabled user, with «تصحيح الجنس يغيّر حساب الأهداف وتقييم نتائج التحاليل.» (17 October 2026; BR-PRF-006, BR-USM-032/061; #109) |
| Mutate any other field in another user's Profile, or their Diary/Plans | No | No |
| Assign roles | No | No through product APIs |
| Self-register or auto-provision from an unknown Auth identity | No | No |
| Create a normal user with Admin-set initial password | No | Yes, by immutable username through FastAPI; atomic internal-only creation, no email/provider call (#112; BR-USM-022/023/025/027/036) |
| Edit another user's display name or reset password | No | Yes, normal users only; internal reset unlocks without forced change and revokes all internal sessions, never calls Supabase; legacy-only reset retains Supabase behavior (17/27 October 2026; BR-USM-030/033; #110) |
| Change own internal password with correct current password | Yes | Yes; current session survives, other sessions revoked; no Supabase update; Profile UI CURRENT #111 (17/27 October 2026; BR-PRF-024–026; #110/#111) |
| Enable/disable or permanently delete another account | No | Yes, normal users only; internal-only deletion uses username confirmation and no provider calls; legacy `provisioning` accounts retain the provider saga, with absent Auth identity counted as success (#112; BR-USM-038/042/043) |
| Change username, legacy email or grant/change Admin role | No | No |
| Disable/delete own Admin account | No | No |
| Read authenticated Labs catalog | Yes | Yes |
| Read own Labs overview/detail/history | Yes | Yes, read-only |
| Create/edit/delete own LabResult | Yes | No, including admin's own results |
| Read another user's Labs overview/detail/history | No | Yes, selected-user read-only |
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
