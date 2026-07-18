# V2 Baseline Recertification

Date: 2026-07-18
Base: `6096fd2a1f372f8e08aa587274870e8f3929fe23`

| Gate | Result |
| --- | --- |
| Backend pytest without PostgreSQL marker environment | 118 passed; 8 migration tests skipped |
| Ruff | Passed |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| npm install audit | 0 vulnerabilities |
| Prior merged Wave 1 full E2E evidence | Passed; V2 will recertify after implementation |

The eight PostgreSQL migration tests are not accepted as final skips. They are
scheduled for disposable PostgreSQL rehearsal after V2 migrations exist.
