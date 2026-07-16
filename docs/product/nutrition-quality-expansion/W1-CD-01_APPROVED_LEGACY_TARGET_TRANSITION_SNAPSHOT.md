# W1-CD-01 Approved Legacy Target Transition Snapshot

## Metadata

| Field | Value |
|---|---|
| Change ID | `W1-CD-01` |
| Title | Legacy Target Transition Snapshot |
| Status | Approved |
| Decision type | Wave 1 frozen-package clarification |
| Product Owner approval | Approved |
| Architecture approval | Approved |
| Engineering/Data approval | Approved |
| API approval | Approved |
| Approval date | `2026-07-16` |
| Pinned revision | Pending |
| Implementation authorization | Paused pending re-freeze |

## Problem

An existing legacy Profile has no immutable historical target source. H04 requires its first Target Plan to begin on the next `Asia/Riyadh` Diary date while activation atomically updates Profile preferences immediately. The baseline calculates the legacy target from mutable Profile values, so updating Profile without preserving the pre-update result would silently change today's target and reinterpret legacy history.

## Approved Behavior

1. Before the first legacy-to-versioned activation changes Profile preferences, the Backend creates one immutable Legacy Target Transition Snapshot containing today's exact pre-update legacy target.
2. Snapshot creation, Profile preference update, Target Plan creation or pending replacement, lifecycle changes, and idempotency completion are one transaction under Principal/Profile locking.
3. The snapshot is authoritative only for its `transition_date` in the deployment-configured `Asia/Riyadh` timezone.
4. Profile preferences update immediately. The existing legacy Profile's first Target Plan remains effective on the next Diary date.
5. The transition date continues to display and evaluate the exact captured legacy target. Tomorrow and later resolve to an effective Target Plan.
6. Earlier dates have no preserved target source and return target unavailable. Mutable current Profile data is never a historical fallback after transition.
7. Resolution precedence is: effective Target Plan; transition snapshot when the requested date equals `transition_date`; otherwise no preserved target source.
8. The transition snapshot is neither a Target Plan nor a Diary nutrition snapshot. It does not fabricate history and does not rewrite Diary Entries.
9. Transition-date Diary Entries remain `target_provenance=legacy_unversioned` and `target_plan_id=null`; day-level target resolution may identify the transition snapshot as the legacy target detail without changing that provenance.
10. A genuinely new Profile whose first plan is effective today creates no transition snapshot.
11. Only the first legacy-to-versioned transition may create a snapshot. Same-date pending replacement reuses it and cannot overwrite or recalculate it.
12. Failed activation rolls back snapshot, Profile, plan/lifecycle, and idempotency changes.
13. Unknown remains unknown, known zero remains zero, and bearer credentials are never persisted.
14. This decision introduces no user-visible feature and authorizes no later-wave scope.

## Approved Physical Direction

The exact table name is `legacy_target_transition_snapshots`. It stores `id`, `principal_id`, `profile_id`, `transition_date`, `calendar_timezone`, `target_document_schema_version`, `legacy_target_document`, and `created_at`. Artifact 14 v1.1 freezes exact types, JSON schema, owner consistency, uniqueness, immutability, indexes, concurrency, and delete restrictions.

## API Consequences

Existing target provenance values remain unchanged. Target-source responses add only a stable detail identifying `legacy_transition_snapshot` as the resolved legacy source for the transition date. Raw internal JSON is not public. Historical no-source responses are explicit and never calculate from current Profile.

## Migration And Rollback Consequences

The table is additive and receives no historical backfill. A snapshot-aware reader deploys before the first writer. After any transition snapshot or Target Plan write, rollback below the snapshot-aware reader floor is prohibited. Lossy downgrade is prohibited.

## Testing Consequences

Mandatory coverage includes exact before/after target equality, immediate preference persistence, tomorrow's plan, prior-date no-source behavior, new-Profile no-snapshot behavior, one-snapshot concurrency, idempotent replay/conflict, atomic rollback, owner isolation, immutability, and Riyadh midnight boundaries.

## Legacy Compatibility

No historical Target Plan, version, Diary binding, or Snapshot v2 data is fabricated. Existing Diary rows and nutrition snapshots are unchanged. Transition-date Diary provenance remains `legacy_unversioned`.

## Rejected Alternatives

- Delaying Profile preference update violates the approved atomic activation contract.
- Reading mutable Profile values for today's target allows silent reinterpretation.
- Treating tomorrow's pending Target Plan as today's source violates effective-date semantics.
- Fabricating a historical Target Plan violates H04.
- Rewriting existing Diary Entries violates H08 and historical immutability.
- Overloading Diary Snapshot v2 confuses consumed-food facts with day-level targets.
- Leaving historical behavior ambiguous would force implementation invention.

## Affected Artifacts

- Artifact 14 Physical Data Model.
- Artifact 15 API Contracts.
- Artifact 16 Migration and Rollback Plan.
- Artifact 17 User Stories and Acceptance Criteria.
- Artifact 18 Golden Calculations.
- Artifact 20 Verification and Regression Plan.
- Artifact 21 Traceability Matrix.

## Unaffected Artifacts

- Artifact 13 remains version 1.0; W1-CD-01 supplements ADR-005 without changing other ADRs.
- Artifact 19 remains version 1.0 because existing current/scheduled/legacy UI states already express the approved behavior and no new user-visible state is introduced.
- C01-C02, H01-H03, H05-H11, Registry, Food, Snapshot value content, aggregation semantics, and later-wave exclusions are unchanged.

## Approval And Pause Status

```text
Product Owner approval: Approved
Architecture approval: Approved
Engineering/Data approval: Approved
API approval: Approved
Wave 1 implementation authorization: Paused pending W1-CD-01 re-freeze
Later-wave implementation authorization: No
```
