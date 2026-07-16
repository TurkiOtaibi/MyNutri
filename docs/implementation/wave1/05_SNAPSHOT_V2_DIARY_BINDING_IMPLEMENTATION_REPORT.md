# Wave 1 Stage 05 - Snapshot v2 and Diary Target Binding

## 1. Stage identity

| Field | Value |
|---|---|
| Stage | 05 - Snapshot v2 and historical Diary target binding |
| Branch | `impl/wave1-05-snapshot-v2-diary-binding` |
| Worktree | `C:\Users\DELTA\Desktop\MyNutri-wave1-05` |
| Base SHA | `97cb77894187d90cb8340f2fd1b907b658d7dba6` |
| Implementation commit | Pending |
| Pull request | Pending |

## 2. Frozen authority

- H04 through H10 and W1-CD-01.
- ADR-003, ADR-005, ADR-006, ADR-009, and ADR-010.
- Artifacts 14 v1.1, 15 v1.1, 16 v1.1, 17 v1.1, 18 v1.1, 20 v1.1, and 21 v1.1.
- Golden requirements W1-GC-029 and the Snapshot scaling/null scenarios.

## 3. Implementation

- Added Alembic revision `0011_diary_snapshot_v2_expand` after immutable revision 0010.
- Added owner-consistent nullable Target Plan linkage, target provenance, and snapshot schema version to Diary Entry.
- Backfilled existing Diary rows only to `legacy_unversioned`; Snapshot v1 JSON remains byte-for-byte unchanged and unversioned.
- Added database checks, owner FK, access indexes, and immutable snapshot/binding trigger.
- Added the closed Backend-validated Snapshot v2 envelope with captured Food/unit identity, core macros, all 16 Wave 1 nutrients, completeness, groups, traits, source reliability, NOVA, and independent versions.
- Added dedicated v1 and v2 readers. Unknown versions and malformed data fail explicitly and never fall back, become zero, or read current Food.
- New v2 values represent one captured logging unit. Diary quantity remains relational and scales known values while preserving null and explicit zero.
- Quantity and meal updates no longer rewrite either v1 or v2 snapshot JSON.
- Diary creation resolves target binding by authenticated Principal and Diary date. Client-supplied snapshot, owner, plan, provenance, totals, and versions remain non-authoritative.
- Added additive `/diary/entries` create/list/read/PATCH/delete routes while retaining baseline `/diary` compatibility routes.
- Added same-date binding of eligible new-Profile `no_target_source` rows during first activation without mutating their nutrition snapshots.
- Added an explicit, disabled-by-default `SNAPSHOT_V2_WRITER_ENABLED` rollout gate so reader-aware releases can deploy before the first v2 write.
- Food hard deletion clears only the live relationship; PostgreSQL evidence proves captured Snapshot v2 remains unchanged.

## 4. API and Frontend compatibility

- Diary responses add nullable `target_plan_id`, `target_provenance`, and `snapshot_schema_version`.
- Raw v2 JSON remains internal; existing normalized `nutrition_snapshot` and totals responses continue to serve the Frontend.
- TypeScript contracts include the four exact new nutrient totals and nullable deleted-Food relationship.
- Existing Diary UI requires no unrelated redesign and passed the complete nonvisual regression suite.

## 5. Migration and rollback

- Fresh and populated upgrades to one Alembic head passed on disposable PostgreSQL.
- Existing v1 snapshot bytes, nulls, zeros, and ownership survive migration.
- Database evidence covers immutable content, quantity/meal-only updates, Food hard delete, target linkage shape, and owner isolation.
- Downgrade to 0010 is permitted only before v2 or plan-linked Diary data exists; a lossy downgrade fails closed.
- After v2 writes, application rollback requires a v2-capable reader and the expanded schema remains in place.

## 6. Validation evidence

| Gate | Result |
|---|---|
| Backend full suite with PostgreSQL | `115 passed`, `1` expected Future Scope skip |
| Focused Snapshot/Target/security tests | `28 passed` |
| PostgreSQL migration rehearsals | `8 passed` |
| Ruff | Passed |
| Alembic heads | One head: `0011_diary_snapshot_v2_expand` |
| Model/migration drift | No new upgrade operations detected |
| Frontend typecheck | Passed |
| Frontend production build | Passed |
| Full nonvisual Playwright | `243/243 passed` in 11.9 minutes |
| `git diff --check` | Passed |

The first E2E attempt used an incorrect local CORS origin and omitted the required baseline Profile fixture. It was not reported as a pass. After correcting only the isolated test environment, the seven affected cases passed 7/7 and the complete 243-test suite passed from a clean migrated database with the v2 writer enabled.

## 7. Security and data review

- Every create/read/update/delete and target resolution remains Principal-scoped.
- Cross-owner Food and Diary behavior remains non-enumerating.
- Target Plan identity and provenance are Backend-derived; owner IDs and raw snapshots are rejected from client input.
- The owner-consistent Target Plan FK prevents cross-Principal binding.
- Snapshot v2 excludes ingredients text and bearer credentials.
- Malformed snapshot errors expose no cross-owner identifiers through ordinary entry reads.

## 8. Legacy compatibility

- Snapshot v1 reader remains active and receives no enrichment.
- Existing Diary entries are not rewritten or rebound by migration.
- Legacy current-day transition entries remain `legacy_unversioned` with null plan linkage.
- New-user same-date binding changes only relational provenance/linkage.
- Current Food edits and deletions never reinterpret captured values.

## 9. Findings and fixes

- Critical findings: 0.
- High findings: 0.
- Corrected during review: immutable quantity updates, exact cursor-independent binding resolution, explicit client-authority errors, hard-delete trigger allowance, reader-before-writer gate, and Riyadh future-date validation.
- Frozen-contract deviations: 0.

## 10. Residual risks

- Writer enablement requires operational evidence that every active Backend is v2-reader capable; the default remains disabled.
- Advanced H11 nullable nutrient aggregation is intentionally Stage 06.
- Physical-device and deployment evidence remains a Stage 08 release gate.

## 11. Traceability

Implemented H08, the Snapshot portions of H04-H07/H09/H10, ADR-006, W1-GC-029, Artifact 14 Diary/Snapshot structures, Artifact 15 Diary contracts, Artifact 16 revision 0011 and rollback floor, and the corresponding Artifact 20 tests.

## 12. Stage verdict

```text
Critical findings: 0
High findings: 0
Snapshot v1/v2 compatibility: Passed
Target binding: Passed
Migration rehearsals: Passed
Rollback compatibility checks: Passed
Full nonvisual regression: Passed
Frozen-contract deviations: 0
Stage verdict: Ready to Merge
```
