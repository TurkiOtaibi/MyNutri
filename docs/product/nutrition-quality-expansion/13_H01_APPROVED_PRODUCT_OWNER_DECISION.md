# H01 Approved Product Owner Decision

## 1. Issue Identity

| Field | Value |
|---|---|
| Document ID | `DEC-H01-13` |
| Issue ID | `H01` |
| Severity | High |
| Title | Cut intensity, 750 kcal cap, and low-energy safety outcomes |
| Product Owner decision | Approved |
| Document lifecycle status | Draft - approved decision record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This document records the authoritative Product Owner decision for H01. It resolves the product/design decision blocker only. It does not authorize implementation and does not close H01.

## 2. Governing Decisions

This decision operationalizes the Wave 1 direction governed by `PD-005`, `PD-008`, `PD-022`, `PD-024`, `PD-025`, `PD-026`, and `PD-029`, while preserving the baseline and calculation boundaries in `PD-000`, `PD-004`, and `PD-007`.

## 3. Approved Persistence Direction

- Cut intensity is stored as a Profile preference.
- Supported values are `15%`, `20%`, and `25%`.
- The default and product-recommended option is `20%`.
- Existing Profiles are assigned the `20%` preference because it preserves the existing fixed `0.8` cut behavior.
- No historical Target Plans are invented.
- When a user changes to a non-cut goal, the last selected cut preference may remain stored but is not applied.
- Every newly activated immutable Target Plan stores the selected intensity and the resolved applied-deficit outcome.
- Profile update and Target Plan activation must not leave the saved preference and activated plan in an inconsistent state.

## 4. Approved Deficit Calculation

The Backend is the only calculation authority.

The calculation order is:

1. Calculate TDEE using the existing approved calculation engine.
2. Calculate `requested_deficit_kcal = TDEE x selected_intensity`.
3. Calculate `applied_deficit_kcal = min(requested_deficit_kcal, 750)`.
4. Calculate `raw_target_kcal = TDEE - applied_deficit_kcal`.
5. Apply the existing approved calorie-rounding behavior to produce the final persisted and displayed calorie target.
6. Determine the safety outcome using that final calorie target.

The automatic deficit may never exceed `750 kcal/day`. The selected intensity is not presented as a guaranteed rate of weight loss.

## 5. Approved Safety Behavior

Safety thresholds apply to every calculated target. Cut intensity and the `750 kcal/day` cap apply only to the cut goal.

| Final calorie target | Preview | Activation | Safety outcome | Override behavior |
|---|---|---|---|---|
| Greater than `1200 kcal` | Allowed | Allowed | `normal` | Not applicable |
| `800` through `1200 kcal`, inclusive | Allowed | Blocked | `specialist_review_required` | No acknowledgment may bypass the block |
| Below `800 kcal` | Allowed | Blocked | `very_low_energy_blocked` | No acknowledgment or user override may bypass the block |

For targets from `800` through `1200 kcal`, the UI must explain in neutral Arabic that the target is very low and requires a supervised specialist plan. For targets below `800 kcal`, the UI must use a stronger neutral Arabic safety explanation.

The acknowledgment-only option for the `800` through `1200 kcal` range is rejected. There is no Clinician Mode, specialist approval workflow, clinical override, or low-energy-plan activation in Wave 1.

## 6. Approved API Behavior

Preview must expose enough information to explain the result:

- `selected_cut_intensity`
- `requested_deficit_kcal`
- `applied_deficit_kcal`
- `deficit_cap_applied`
- `final_target_calories`
- `safety_outcome`
- `can_activate`

Approved safety outcomes are:

- `normal`
- `specialist_review_required`
- `very_low_energy_blocked`

Save or Target Plan activation must reject blocked outcomes using stable error codes. Recommended stable codes are:

- `SPECIALIST_REVIEW_REQUIRED`
- `VERY_LOW_ENERGY_TARGET_BLOCKED`

The frontend must not reproduce the deficit or safety calculation. Preview and save must use the same Backend policy and produce identical calculation results for identical inputs.

## 7. Historical And Migration Rules

- Existing cut Profiles preserve equivalent `20%` behavior.
- No historical Target Plan is fabricated.
- Existing Diary snapshots and nutritional history are unchanged.
- Unknown nutrient values remain unknown and are not converted to zero.
- Mifflin-St Jeor and the current approved activity factors remain unchanged.
- The exact schema, migration, rollback, compatibility, and transactional design remains subject to the required technical freeze artifacts and approvals.

## 8. Deferred Scope

This decision does not add:

- Progress UI.
- Four-week calorie review UI.
- Clinical nutrition mode.
- Specialist account or verification.
- Clinician override.
- Medication review.
- Nutritionally complete meal-replacement plans.
- Direct gram/ml Diary logging.
- Unrelated Profile redesign.

## 9. Approval And Work Boundaries

The Product Owner has approved the product behavior in this document. The following work remains open and requires the appropriate technical and delivery approvals:

- Architecture and security contracts.
- Physical schema and Target Plan design.
- API request, response, error, and compatibility contracts.
- Expand-Migrate-Contract and rollback design.
- Arabic UX states and acceptance criteria.
- Backend and frontend implementation.
- Golden calculations and automated verification.
- Traceability and final freeze evidence.

## 10. Recorded Status

```text
Product Owner decision: Approved
Persistence direction: Profile preference plus immutable Target Plan copy
800-1200 acknowledgment-only option: Rejected
800-1200 activation: Blocked
Below-800 activation: Blocked
Clinical override: Deferred
Product/design blocker: Resolved
Architecture, schema, API, migration, UX, implementation, and verification work: Still open
H01 overall status: Open
```

H01 must not be marked closed until the approved behavior is represented in the frozen technical contracts, implemented, migrated safely, verified, traced, and accepted in the final Wave 1 readiness recheck.
