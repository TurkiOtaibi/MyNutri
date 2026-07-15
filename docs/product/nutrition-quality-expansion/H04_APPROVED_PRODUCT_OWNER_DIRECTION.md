# H04 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H04` |
| Issue ID | `H04` |
| Severity | High |
| Title | Immutable Target Plan model and lifecycle are not frozen |
| Product/lifecycle direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This document records the authoritative Product Owner lifecycle direction for H04. It resolves the product/lifecycle blocker only. It does not authorize implementation and does not close H04.

## 2. Governing Decisions

This direction operationalizes `PD-008`, `PD-023`, `PD-024`, `PD-025`, `PD-026`, and `PD-029`. Its technical contracts depend on C01 and the approved H01 through H03 calculation directions.

## 3. Approved Architecture Direction

Wave 1 uses a hybrid immutable Target Plan.

Relational fields govern:

- Plan identity.
- Principal and Profile ownership.
- Lifecycle state.
- Effective period.
- Activation metadata.
- Idempotency.
- Relationship to preceding or superseding plans.
- Calculation and registry versions.

A versioned and Backend-validated calculation document preserves the authoritative inputs and resolved outputs that produced the plan. It includes, where applicable:

- Profile calculation inputs.
- Goal and activity.
- Selected cut intensity.
- Requested and applied deficit.
- Deficit-cap and calorie-safety outcomes.
- Protein-calculation provenance.
- Calorie and macro targets.
- Carbohydrate warning state.
- Additional nutrient targets.
- Custom target settings.
- Calculation-engine, nutrition-registry, related rule, and document-schema versions.

Exact physical columns and the JSON/document schema remain subject to Architecture, Data, API, and QA approval in the formal freeze artifacts.

## 4. Approved Immutability Rules

Preview does not persist a Target Plan.

After activation, a plan's calculation inputs, calculated outputs, rule versions, and effective start date cannot be edited or moved backward. A plan is never rewritten when Profile data or rules later change.

Lifecycle metadata may change only through an approved Backend lifecycle operation, including:

- Closing an active period when a later plan becomes effective.
- Marking an unstarted scheduled plan as superseded before effective.
- Linking the superseding plan.
- Recording activation or supersession audit metadata.

A plan row must never be edited to represent a different calculation.

## 5. Approved Effective-Date Semantics

Target Plan effectiveness uses a Diary calendar date, not a timestamp.

```text
effective_from: inclusive
effective_to: exclusive
```

Targets apply to a complete Diary calendar date. A plan change must not cause one Diary day to use different daily targets before and after a time-of-day boundary.

The Architecture and API artifacts must define the exact timezone and calendar-source contract. The frontend may not choose an authoritative ownership or effective date outside the approved Backend contract.

## 6. Approved First Activation

### Brand-new Profile without a prior target source

When a newly created Profile has no previous active, legacy, or versioned target:

- Explicit activation may create the first plan effective on the current Diary calendar date.
- The user must preview and confirm targets before activation.

### Existing Profile with legacy calculated targets

When an existing Profile has legacy target behavior but no Target Plan:

- Do not fabricate a historical plan.
- The legacy target remains the source for the current Diary date.
- The first explicitly confirmed Target Plan becomes effective on the next Diary calendar date.
- Earlier days remain legacy and unversioned.

## 7. Approved Subsequent Activation And Scheduling

When a current Target Plan or legacy target source exists, a newly confirmed plan becomes effective on the next Diary calendar date and must not replace the current day's target. The UI distinguishes current and scheduled targets.

Backdating is prohibited. Arbitrary future scheduling and a scheduling date picker are deferred.

Wave 1 supports only:

- Current-date first activation for a genuinely new Profile without an existing target source.
- Next-date activation for an existing or previously activated Profile.

## 8. Approved Same-Date Replacement

At most one future scheduled plan may be pending for one Principal.

If a plan is already scheduled for the next effective date and the user explicitly confirms a different proposal before that date:

- The new plan may replace the pending plan.
- The previous pending plan is retained for audit and not deleted.
- Its lifecycle meaning is equivalent to `superseded_before_effective`.
- It never becomes effective.
- Replacement requires explicit confirmation.
- The UI discloses that a scheduled plan is being replaced.

Architecture and Data may select the exact lifecycle enum name if this meaning and audit behavior are preserved.

## 9. Approved Idempotency And Concurrency

Activation requires an `Idempotency-Key`.

For the same Principal:

- Repeating the same request with the same key returns the original activation result.
- Reusing the same key with different content is rejected.
- Concurrent requests cannot create duplicate or overlapping active or scheduled plans.
- The database and Backend transaction enforce at most one active plan and one pending next-date plan.

## 10. Approved Profile Transaction Behavior

Profile editing and Target Plan activation are separate concepts.

Preview:

- Does not persist Profile changes as an active target.
- Does not create a Target Plan.
- Returns authoritative proposed results.

Activation:

- Requires explicit confirmation.
- Updates approved Profile inputs and preferences.
- Creates the immutable Target Plan.
- Closes or supersedes applicable lifecycle records.
- Completes in one Backend transaction.

If activation fails, the Profile preference update must not commit independently, no partial plan may remain, and no invalid H01 or H03 outcome may activate. Changing Profile draft values alone must not silently change the active Target Plan.

## 11. Approved Plan Cardinality

For each Principal:

- At most one plan may be active for a Diary date.
- At most one unstarted next-date plan may be scheduled.
- Effective periods may not overlap.
- Activated plan content is immutable.
- Current and historical resolution is Backend-authoritative.

One Profile remains allowed per Principal under C01.

## 12. Approved Legacy And Historical Behavior

Migration must not create Target Plans for historical dates. Existing Profile rows remain valid inputs. Existing Diary entries and nutrition snapshots are not rewritten.

Diary dates before the first effective Target Plan remain:

```text
target_plan_id = null
target_provenance = legacy_unversioned
```

The physical representation of `legacy_unversioned` remains subject to formal Data and API contracts.

Snapshot v2 entries created after activation bind to the Target Plan effective for their Diary date. A scheduled plan is not used before its effective date. Historical resolution must not query mutable current Profile data to reinterpret a previously logged versioned day.

## 13. Approved API Capabilities

The lifecycle requires additive Backend capabilities for:

- Non-persisting preview.
- Explicit activation.
- Current effective plan.
- Next scheduled plan where present.
- Plan history.
- Replacement of an unstarted scheduled plan.
- Lifecycle and idempotency errors.

Exact endpoints, shapes, statuses, stable error codes, and pagination remain subject to formal API Contracts approval. Existing Profile routes remain baseline assets and are not removed without an approved compatibility plan.

## 14. Approved User-Facing Lifecycle

The user must understand current targets, proposed targets, when proposed targets begin, whether a plan is scheduled, whether confirmation replaces a scheduled plan, and that Preview alone does not save or activate.

The minimal Profile confirmation states needed to activate a versioned plan are in Wave 1. The full four-week Progress review UI is not.

## 15. Deferred Scope

This direction does not introduce:

- Backdated Target Plans.
- Arbitrary future plan scheduling or a scheduling date picker.
- Clinician-created or specialist-approved plans.
- Multiple Profiles per Principal or Profile switching.
- Four-week calorie-review UI or Progress UI.
- Analysis Snapshots.
- Public/shared plans.
- Historical-plan fabrication.
- Direct gram/ml Diary logging.
- Unrelated UI redesign.

## 16. Approval And Work Boundaries

The Product Owner has approved the lifecycle behavior in this record. Exact physical schema, timezone/date contract, API representation, migration sequence, transaction mechanics, Arabic UX states, implementation, verification, and traceability remain open for their designated approvers.

## 17. Recorded Status

```text
Artifact ID: DEC-H04
Selected architecture direction: Hybrid immutable Target Plan
Effective granularity: Diary calendar date
Effective interval: effective_from inclusive, effective_to exclusive
Backdating: Prohibited
Arbitrary future scheduling: Deferred
First plan for new Profile without prior targets: Current date
First versioned plan for existing legacy Profile: Next date
Subsequent plan changes: Next date
Pending plan replacement: Allowed with audit preservation
Preview persistence: None
Explicit activation confirmation: Required
Activation idempotency: Required
Profile preference and plan activation transaction: Atomic
Historical plan fabrication: Prohibited
Product/lifecycle blocker: Resolved
Architecture, Security, Data, API, Migration, UX, implementation, and
verification: Still open
H04 overall status: Open
```

H04 must not be marked closed until its approved behavior is frozen in the formal contracts, implemented, migrated safely, verified, traced, and accepted by the final Wave 1 readiness recheck.
