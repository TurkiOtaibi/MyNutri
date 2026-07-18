# myNutri V2 Implementation Plan

Base: `6096fd2a1f372f8e08aa587274870e8f3929fe23`
Branch: `feat/v2-multi-user-admin-food-catalog`

| Phase | Scope | Primary evidence |
| --- | --- | --- |
| 0 | Audit, decisions, baseline | V2 docs; baseline report |
| 1 | Principal/Auth/roles/bootstrap | migration; auth services/tests |
| 2 | isolation/admin read APIs | User A/B/Admin tests |
| 3 | shared Food catalog/lifecycle | migration; global catalog tests |
| 4 | taxonomy/Registry/tooling | Registry lock; migration tests |
| 5 | Supabase frontend auth/guards | auth E2E; bundle secret scan |
| 6 | admin users/Foods UI | admin E2E; read-only checks |
| 7 | Food form advanced UX | RTL/a11y/responsive E2E |
| 8 | certification/runbooks | full regression and rehearsal |
| 9 | atomic commits, push, PR | commit/PR evidence |

## Invariants

Existing IDs and snapshots remain stable; private queries remain owner-scoped;
Food reads become global; writes are admin-only; no role comes from client
metadata; no shared token enters browser output; no production operation runs.
