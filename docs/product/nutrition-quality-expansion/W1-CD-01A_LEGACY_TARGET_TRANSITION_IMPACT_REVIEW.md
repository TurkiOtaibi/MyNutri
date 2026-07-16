# W1-CD-01 Legacy Target Transition Impact Review

## Review Metadata

| Field | Value |
|---|---|
| Review ID | `W1-CD-01A` |
| Change | `W1-CD-01` |
| Audited branch | `docs/wave1-change-legacy-target-transition` |
| Audited base | `9121b893bbe582d851c7570cdb899a8564a896ae` |
| Review date | `2026-07-16` |
| Reviewer roles | Architecture / Security / Engineering-Data / API / QA / Governance |
| Verdict | Ready for Change Approval |

## Sources Reviewed

- W1-CD-01 approved Product Owner decision.
- Freeze Index and governing v1.1 Product Decision Register.
- H04, H08, ADR-005, ADR-006, ADR-009, and ADR-010.
- Artifacts 14, 15, 16, 17, 18, 19, 20, and 21.
- Current merged Profile calculation, ownership, authentication, Alembic, and Diary behavior as brownfield evidence.

## Product Consistency

The change closes the exact conflict between immediate Profile preference persistence and next-date first-plan effectiveness. It preserves H04's current/next-date behavior, H08 provenance and no-rewrite rules, null/zero semantics, and all deferred scope. It introduces no new user workflow. Product Owner decisions required: 0.

## Architecture And Security

The dedicated aggregate is intentionally separate from Target Plan and Diary Snapshot. Principal/Profile composite ownership, one-row/Profile uniqueness, Principal/Profile row locks, database immutable trigger, no mutation API, and non-enumerating owner boundaries prevent anonymous ownership, IDOR, duplicate transition sources, and silent rewrite. Credentials and client owner IDs are prohibited. Architecture direction is complete for Data/API implementation.

## Engineering And Data

Artifact 14 v1.1 defines exact table name, columns, PostgreSQL types, nullability, checks, FKs, uniqueness, indexes, closed JSON schema, precision rules, immutability layers, and resolution role. The closed document now includes every target response value needed to preserve current legacy behavior. It does not impersonate a plan or historical Diary snapshot.

## API Compatibility

The additive `target_source_detail` distinguishes the resolved source without changing `target_provenance`. Existing Diary rows retain `legacy_unversioned`/null plan linkage. Raw JSON and owner/snapshot IDs remain private. Existing target consumers receive normalized target fields. Earlier-date no-source behavior is explicit.

## Migration And Rollback

`0009_legacy_target_transition_expand` establishes the reader boundary before `0010_target_plan_expand`; later boundaries shift without changing dependency order. Migration creates no rows. Runtime first activation is the only writer. No-write downgrade is rehearsed; post-write rollback requires a snapshot-aware reader and schema retention. Lossy downgrade and historical backfill are prohibited.

## Idempotency And Concurrency

One transaction and Principal/Profile locks cover snapshot creation, Profile update, plan/lifecycle mutation, and idempotency completion. Database uniqueness remains the final race guard. Replay reuses the original result; payload conflict mutates nothing. Pending replacement reuses the immutable snapshot.

## Traceability

W1-CD-01 is mapped bidirectionally to H04/ADR-005, Artifact 14 data, Artifact 15 API, Artifact 16 migration, W1-US-006, `W1-GC-036..046`, Artifact 20 gates, and Stage 4 implementation responsibilities. Unexplained traceability gaps: 0.

## Unaffected Artifact Review

- Artifact 13 remains version 1.0 because W1-CD-01 supplies the missing approved transition direction without changing ADR-005's other architecture or any other ADR.
- Artifact 19 remains version 1.0 because no state, action, copy, navigation, accessibility, or responsive behavior changes; existing current/scheduled/legacy/unavailable states render the normalized Backend result.
- Artifacts 14, 15, 16, 17, 18, 20, and 21 are the complete affected set.

## Findings

| Severity | Finding | Disposition |
|---|---|---|
| Critical | None | N/A |
| High | None | N/A |
| Medium | Initial Artifact 14 draft did not enumerate every target-response field needed for exact replay | Corrected with a closed full resolved-target schema before approval |
| Low | Existing documents use some historical lifecycle prose outside the revised sections | Freeze Index explicitly identifies active v1.1 change state; no contract ambiguity remains |

## Required Corrections

No unresolved correction remains. Approval metadata and exact pinned revisions must be completed through the two-commit change lifecycle and merge/re-pin workflow.

## Review Counts

```text
Critical: 0
High: 0
Medium: 1 (resolved before approval)
Low: 1 (non-substantive)
Substantive contradictions: 0
Product Owner decisions required: 0
Traceability gaps: 0
Verdict: Ready for Change Approval
```
