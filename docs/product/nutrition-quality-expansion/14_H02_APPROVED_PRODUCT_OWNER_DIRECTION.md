# H02 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Document ID | `DEC-H02-14` |
| Issue ID | `H02` |
| Severity | High |
| Title | BMI-aware adjusted protein calculation and basis disclosure are absent |
| Product direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This document records the authoritative Product Owner and contract direction for H02. It resolves the product/design blocker only. It does not authorize implementation and does not close H02.

## 2. Governing Decisions

This direction operationalizes `PD-006`, `PD-008`, `PD-025`, and `PD-026`, while preserving the brownfield, historical-data, migration, and readiness boundaries in `PD-000`, `PD-024`, and `PD-029`.

## 3. Approved Calculation Behavior

The Backend remains the sole authority for protein calculation.

For BMI below `30`:

```text
protein_weight_basis = actual_weight
protein_calculation_weight_kg = actual_weight_kg
reference_weight_kg = null
```

For BMI equal to or above `30`:

```text
height_m = height_cm / 100

reference_weight_kg =
25 x height_m^2

protein_calculation_weight_kg =
reference_weight_kg
+ 0.33 x (actual_weight_kg - reference_weight_kg)

protein_weight_basis = adjusted_weight
```

The protein target is:

```text
protein_target_g =
protein_calculation_weight_kg x protein_per_kg
```

The BMI comparison with `30` uses the Backend's unrounded calculated BMI. A displayed rounded BMI must not determine the branch. BMI exactly equal to `30` uses adjusted weight.

No intermediate calculation value may be rounded before the final protein target is determined. The final protein target follows the existing approved output rounding policy of one decimal place. The server calculation must be decimal-safe rather than rely on binary floating-point behavior that could alter the BMI boundary or target result.

## 4. Approved API Direction

Use an additive nested object:

```text
protein_calculation:
  basis
  bmi_used
  actual_weight_kg
  reference_weight_kg
  calculation_weight_kg
  protein_per_kg
  target_g
  calculation_engine_version
```

Approved basis values are:

```text
actual_weight
adjusted_weight
```

Rules:

- Retain the existing top-level `protein_g` field for backward compatibility.
- `protein_calculation.target_g` equals the authoritative top-level `protein_g`.
- `reference_weight_kg` is `null` when the basis is `actual_weight`.
- The API returns the calculation result; the frontend does not reproduce it.
- Preview and save return identical protein results and provenance for identical inputs.
- No client-supplied calculation basis is authoritative.
- Architecture and API owners may define exact serialization precision and schema types only if persisted and returned values preserve the approved result and boundary behavior.

## 5. Approved Target Plan Persistence

Every newly activated immutable Target Plan stores enough information to reproduce and explain the original protein target:

- `protein_weight_basis`.
- BMI used for the calculation.
- Actual weight used.
- Reference weight where applicable.
- Protein calculation weight.
- Protein-per-kilogram factor.
- Final protein target.
- Calculation-engine version.

The Target Plan also preserves the approved inputs required by the broader Target Plan contract.

Do not add derived calculation fields to Profile merely to cache the result. Profile stores user inputs and preferences. Target Plan stores the immutable resolved calculation outcome.

No historical Target Plans or derived historical protein bases are invented during migration. Existing custom `protein_per_kg` values remain unchanged and apply to the approved calculation weight.

## 6. Approved User-Facing Explanation

When the basis is `actual_weight`, the approved meaning is:

```text
تم حساب البروتين باستخدام وزنك الحالي لأن مؤشر كتلة الجسم أقل من 30.
```

When the basis is `adjusted_weight`, the approved meaning is:

```text
تم حساب البروتين باستخدام وزن حسابي معدل لأن مؤشر كتلة الجسم يساوي
30 أو أكثر.
```

Do not describe `reference_weight_kg` as ideal weight, goal weight, or recommended body weight. Use wording equivalent to:

```text
وزن مرجعي للحساب
```

The frontend displays Backend-provided values and explanations and does not implement the formula in TypeScript.

## 7. Compatibility Rules

Preserve:

- Existing Profile routes.
- Server preview/save flow.
- Existing custom protein factor.
- Current Mifflin-St Jeor behavior.
- Current activity factors.
- Existing Diary snapshots.
- Current top-level target fields.

Exact physical schema types, serialization precision, migration ordering, compatibility mechanics, and technical approvals remain pending in the modular freeze artifacts.

## 8. Deferred And Excluded Scope

This direction does not add:

- Clinical protein exceptions.
- Kidney-disease rules.
- Pregnancy rules.
- Athlete-specific formulas.
- Target-weight protein calculation.
- Ideal-body-weight selection.
- User-selectable weight basis.
- Progress UI.
- Historical Target Plan fabrication.
- Direct gram/ml Diary logging.

## 9. Approval And Work Boundaries

The Product Owner has approved the calculation, API shape direction, persistence boundary, compatibility behavior, and user-facing meaning recorded here. The following work remains open:

- Architecture and calculation-domain contract.
- Decimal precision and exact physical schema types.
- Additive API schema and compatibility approval.
- Target Plan physical data model and migration design.
- Arabic UX states and acceptance criteria.
- Backend and frontend implementation.
- Boundary, golden, migration, and regression verification.
- Traceability and final freeze evidence.

## 10. Recorded Status

```text
Product direction: Approved
Selected API direction: Nested protein_calculation object
Existing top-level protein_g: Preserved
BMI boundary rule: Unrounded Backend BMI
BMI exactly 30: Adjusted weight
Frontend formula: Prohibited
Clinical exceptions: Deferred
Product/design blocker: Resolved
Architecture, Data, API, UX, implementation, and verification:
Still open
H02 overall status: Open
```

H02 must not be marked closed until its approved behavior is represented in the frozen technical contracts, implemented, migrated safely, verified, traced, and accepted in the final Wave 1 readiness recheck.
