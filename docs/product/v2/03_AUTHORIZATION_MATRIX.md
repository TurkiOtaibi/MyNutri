# V2 Authorization Matrix

The Admin-managed account lifecycle rows below are approved target authority
pending implementation; existing Profile, Diary, Target Plan, and Labs read-only
boundaries continue unchanged.

| Capability | User | Admin |
| --- | --- | --- |
| Read/update own Profile | Yes | Yes |
| Preview/write/read own dated Target Plans | Yes | Yes |
| Read own Diary and summaries | Yes | Yes |
| Read shared Foods | Yes | Yes |
| Add shared Food to own Diary | Yes | Yes |
| Create/update/permanently delete Food | No | Yes |
| List users | No | Yes |
| Read another user's monitored data | No | Yes, read-only |
| Mutate another user's Profile/Diary/Plans | No | No |
| Assign roles | No | No through product APIs |
| Self-register or auto-provision from an unknown Auth identity | No | No |
| Create a normal user with Admin-set initial password | No | Yes, through FastAPI |
| Edit another user's display name or reset password | No | Yes, normal users only; reset revokes existing Supabase sessions through FastAPI |
| Enable/disable or permanently delete another account | No | Yes, normal users only; deletion includes `provisioning` accounts via the same saga, with absent Auth identity counted as success |
| Change email or grant/change Admin role | No | No |
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
- Admin account management is distinct from selected-user monitoring. It never
  grants write access to another user's Profile, Diary, Target Plans, or Labs.
- Every writer of Principal-owned private data locks the Principal first and
  rechecks `active` before writing, including receipt replay paths. No write
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
