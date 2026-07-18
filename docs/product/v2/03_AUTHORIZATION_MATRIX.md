# V2 Authorization Matrix

| Capability | User | Admin |
| --- | --- | --- |
| Read/update own Profile | Yes | Yes |
| Preview/activate own Target Plans | Yes | Yes |
| Read own Diary and summaries | Yes | Yes |
| Read active shared Foods | Yes | Yes |
| Add shared Food to own Diary | Yes | Yes |
| Create/update/archive/restore/delete Food | No | Yes |
| List users | No | Yes |
| Read another user's monitored data | No | Yes, read-only |
| Mutate another user's Profile/Diary/Plans | No | No |
| Assign roles | No | No through product APIs |

## Enforcement

- Normal services infer ownership from `PrincipalContext`; they accept no user ID.
- Admin monitoring has dedicated `/admin/users/...` read routes.
- Admin-selected IDs never replace the caller's `PrincipalContext`.
- Shared Food reads are global and active-only by default.
- Food writes require an explicit admin dependency in FastAPI.
- Cross-owner private lookups are non-enumerating.
- Authorization is tested with User A, User B, and Admin fixtures.

