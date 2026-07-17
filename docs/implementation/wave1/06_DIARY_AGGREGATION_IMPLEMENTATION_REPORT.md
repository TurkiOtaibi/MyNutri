# Wave 1 Stage 06 - Backend-Authoritative Diary Aggregation

## 1. Stage identity

| Field | Value |
|---|---|
| Stage | 06 - Backend-authoritative Diary nutrient aggregation |
| Branch | `impl/wave1-06-diary-aggregation` |
| Worktree | `C:\Users\DELTA\Desktop\MyNutri-wave1-06` |
| Base SHA | `e7b71d191a0ea671c0fc41594911fa3a36a050f3` |
| Implementation commit | Pending |
| Pull request | Pending |

## 2. Frozen authority

- H11 and ADR-008.
- Artifacts 15 v1.1, 17 v1.1, 18 v1.1, 19 v1.0, 20 v1.1, and 21 v1.1.
- Golden scenarios `W1-GC-025` through `W1-GC-028`.
- W1-CD-01 historical target-source precedence.

## 3. Implementation

- Added one Backend aggregate for every Registry nutrient participating in Diary coverage.
- Preserved explicit zero as known and null as unknown through quantity-scaled v1/v2 readers.
- Added exact `no_entries`, `all_unknown`, `partial`, and `complete` states and `unavailable`, `at_least`, and `exact` qualifiers.
- Added canonical known/total counts and Backend-calculated per-nutrient and overall coverage percentages.
- Added resolved historical target metadata and asymmetric partial evaluation for minimum/recommended/adequate, maximum, and range targets.
- Suppressed partial remaining, available, and progress values; complete remaining/available values are clamped at zero.
- Kept monitor-only and minimize semantics free from fabricated numeric allowances.
- Day summaries resolve Target Plan, legacy transition, or no preserved source by authenticated Principal and Diary date.
- Malformed or unsupported snapshots fail the entire summary with `DIARY_SUMMARY_DATA_INTEGRITY_ERROR`; no entry is omitted or converted to zero.
- Existing weekly macro totals and compatibility fields remain additive while every day now carries its own authoritative targets and aggregates.

## 4. Frontend boundary

- Diary no longer calculates nutrient amounts, coverage, qualifiers, target evaluation, or daily totals authoritatively.
- The selected historical day uses only the Backend day target; mutable current Profile targets are not a fallback.
- Registry metadata supplies labels, order, precision, and localized units; a failed Registry load produces an explicit retry state without fabricated metadata.
- Empty, all-unknown, partial, complete, no-target-source, and integrity-failure paths remain distinguishable.
- Partial amounts display `على الأقل`; all-unknown amounts display `غير متوفر`; definitive partial remaining/available values are absent.

## 5. API compatibility

- `GET /diary/week` remains additive and owner-scoped.
- Each day adds target provenance, 16 nutrient aggregates, and nullable overall coverage.
- Existing day totals, week totals, dates, and top-level compatibility targets remain available.
- Integrity errors return only authenticated owner entry references and stable nested cause codes.

## 6. Security and data integrity review

- Summary entry selection remains Principal-scoped before any identifier can be returned.
- Cross-Principal aggregate tests prove zero entries and `no_entries` states for the other Principal.
- Snapshot readers remain the sole historical value source; current Food is never consulted.
- Historical target evaluation uses date-effective immutable sources and never the current Profile after transition.
- No schema or migration change is required for H11.

## 7. Tests and validation

| Gate | Result |
|---|---|
| H11 golden unit matrix | Passed |
| Snapshot integrity failure | Passed |
| Two-Principal aggregate isolation | Passed |
| Backend full suite | `119 passed, 1 expected Future Scope skip` |
| PostgreSQL migration rehearsals | `8/8 passed` |
| Ruff | Passed |
| Alembic head / model drift | One head at `0011`; no drift |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| Targeted Diary Playwright | Passed: all-unknown, partial, historical target, and RTL summary cases |
| Food socket-failure stability check | `10/10 passed` without retry after one environmental socket reset |
| Full nonvisual Playwright | `244/244 passed`; no skip or retry |
| `git diff --check` | Passed |

## 8. Findings and corrections

- Critical findings: 0.
- High findings: 0.
- Removed the previous Frontend nutrient aggregation and target-evaluation implementation.
- Removed the mutable current-Profile fallback from historical Diary rendering.
- Added a truthful no-target-source path that still permits viewing amounts and coverage.
- Corrected the existing all-unknown E2E expectation from `على الأقل` to `غير متوفر`.
- Corrected legacy E2E assumptions that compared historical Diary days with mutable current Profile targets; tests now use the date-authoritative Target Plan endpoint or a date with an approved target source.
- One full Playwright run encountered a transient socket reset after the Food detail page had loaded correctly. The unchanged Food scenario then passed 10/10 and the final complete suite passed 244/244.
- Frozen-contract deviations: 0.

## 9. Legacy compatibility and rollback

- Snapshot v1 remains read-only, unversioned, and unenriched.
- Mixed v1/v2 aggregation treats an absent v1 nutrient as unknown and a v2 numeric zero as known.
- No migration, backfill, or persisted-data rewrite is introduced.
- Rollback is an application rollback to the Stage 5 reader; no Stage 6 data format is written.

## 10. Traceability

Implemented H11, ADR-008, W1-US-014/015, W1-UI-031 through W1-UI-036, W1-GC-025 through W1-GC-028, and the nullable aggregation/security/integrity gates in Artifact 20.

## 11. Residual risks

- Physical-device and deployment evidence remains a Stage 08 release gate.
- Complete Wave 1 frontend state conformance remains Stage 07.

## 12. Stage verdict

```text
Critical findings: 0
High findings: 0
Nullable aggregation golden scenarios: Passed
Owner isolation: Passed
Frozen-contract deviations: 0
Stage verdict: Ready to Merge
```
