# Wave 1 Stage 08 - Residual Risk Register

## Status

| Field | Value |
|---|---|
| Stage | 08 verification certification |
| Base SHA | `97d9864ab4eac3c9b3278414c2db0a07f2725016` |
| Critical implementation risks | 0 |
| High implementation risks | 0 |
| Frozen-contract deviations | 0 |
| Production release | Not authorized by this workflow |

## Open release evidence

| ID | Evidence still required | Severity | Blocks implementation completion | Blocks production release | Owner |
|---|---|---|---:|---:|---|
| W1-RR-001 | Real iPhone Safari: dynamic bars, home indicator, keyboard, touch, sheet scroll | Release gate | No | Yes | Physical-device QA / UX |
| W1-RR-002 | Real Android Chrome: keyboard, Back behavior, touch and sheet scroll | Release gate | No | Yes | Physical-device QA / UX |
| W1-RR-003 | Installed PWA physical-device shell/navigation and online-only failure behavior | Release gate | No | Yes | Physical-device QA / Operations |
| W1-RR-004 | Manual screen-reader names, live status, focus order, trap, and restoration review | Release gate | No | Yes | Accessibility / QA |
| W1-RR-005 | Production deployment rehearsal, secrets, monitoring, and rollback execution | Release gate | No | Yes | Operations / Security |

Artifact 20 explicitly states that pending physical evidence does not block implementation start or documentation freeze, but blocks Wave 1 release sign-off. Automated Chromium coverage is evidence, not a substitute for these physical checks.

## Closed during Stage 08

| ID | Finding | Disposition |
|---|---|---|
| W1-RR-C01 | Additional-target type text contrast 4.39:1 | Corrected to existing dark brand color; axe passed |
| W1-RR-C02 | Target-provenance text contrast 3.93:1 | Corrected to existing dark brand color; axe passed |
| W1-RR-C03 | Historical-date visual fixture assumed mutable legacy target fallback | Uses current authoritative Diary date and explicit refresh |
| W1-RR-C04 | Profile visual API interception depended on `127.0.0.1` spelling | Host-agnostic API route interception; document navigation excluded |

## Residual-risk verdict

```text
Critical implementation defects: 0
High implementation defects: 0
Implementation completion blockers: 0
Production release blockers: 5 evidence items
Production release status: Not Ready - physical/manual/deployment evidence pending
```
