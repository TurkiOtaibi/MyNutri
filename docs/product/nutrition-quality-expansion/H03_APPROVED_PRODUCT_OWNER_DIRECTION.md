# H03 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H03` |
| Issue ID | `H03` |
| Severity | High |
| Title | Zero or negative carbohydrate allocation is silently clamped |
| Product/contract direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This document records the authoritative Product Owner and contract direction for H03. It resolves the product/design blocker only. It does not authorize implementation and does not close H03.

## 2. Governing Decisions

This direction operationalizes `PD-007`, `PD-022`, `PD-025`, and `PD-029`, with dependencies on the approved H01 and H02 calculation directions and the Target Plan requirements in `PD-008`.

## 3. Approved Allocation Behavior

The Backend is the sole authority for carbohydrate allocation.

The authoritative carbohydrate calculation is based on the approved final calorie target after the H01 deficit and safety policy, minus the authoritative protein and fat calorie allocations. The frontend must not reproduce this formula.

No intermediate value is rounded merely to select a carbohydrate warning state. The final carbohydrate target is rounded using the existing approved one-decimal target-output policy. Warning classification shown to the user is based on the final rounded carbohydrate target so the visible value and visible warning cannot contradict each other.

Any raw carbohydrate calorie allocation that is zero or negative is invalid regardless of final display rounding. Any final rounded carbohydrate target that is zero or negative is also invalid.

## 4. Approved Valid States

| Final carbohydrate target | Result | Warning | Save and Target Plan activation |
|---|---|---|---|
| At least `130 g` | Valid | None | Allowed |
| At least `100 g` and below `130 g` | Valid | Calm general-reference warning | Allowed |
| Greater than zero and below `100 g` | Valid | Stronger warning | Allowed |

The `130 g` value is a general reference and must not be described as a mandatory medical minimum. A positive carbohydrate target below `100 g` is not automatically blocked or diagnosed as unsafe by this rule.

## 5. Approved Invalid State

When raw carbohydrate calories or the final carbohydrate target are zero or negative:

- Preview rejects the calculation through a structured Backend domain error.
- Save rejects the request.
- No Target Plan may be created or activated.
- The result is not returned as a successful zero-carbohydrate target.
- No client acknowledgment or override may bypass the rejection.

## 6. Approved Warning Contract

Use a shared additive Backend warning collection:

```text
calculation_warnings:
  - code
    severity
    dimension
    value
    reference_value
    message_ar
```

Approved warning codes:

- `CARBOHYDRATE_BELOW_GENERAL_REFERENCE`
- `CARBOHYDRATE_VERY_LOW`

Approved severity meanings:

- `info`
- `warning`

Approved dimension:

- `carbohydrate`

`CARBOHYDRATE_BELOW_GENERAL_REFERENCE` applies to final targets from `100 g` through less than `130 g`. `CARBOHYDRATE_VERY_LOW` applies to positive final targets below `100 g`.

Architecture and API owners may add technically necessary metadata if the stable codes, meanings, boundaries, and additive compatibility remain unchanged.

## 7. Approved Error Contract

Approved stable machine code:

```text
NON_POSITIVE_CARBOHYDRATE_ALLOCATION
```

The error applies to:

```text
macro_allocation
```

Do not assign the error exclusively to `fat_pct` or `protein_per_kg`, because the invalid remainder can result from multiple interacting inputs and the final calorie target.

Recommended HTTP status:

```text
422 Unprocessable Entity
```

The exact common error envelope and serialization are frozen later in the Wave 1 API Contracts artifact.

The Arabic message must explain that the selected calorie and macro settings leave no valid carbohydrate allocation, ask the user to revise calorie or macro settings, remain neutral and non-shaming, and avoid diagnosis or clinical claims.

## 8. Approved Compatibility Behavior

Retain the current successful-response field `carb_clamped` as a deprecated compatibility field during the current additive API cycle.

Rules:

- Successful responses always return `carb_clamped = false`.
- No successful response may return `carb_clamped = true`.
- Invalid allocations return the structured domain error instead.
- Mark the field deprecated in the API contract.
- Remove it only in a future major API version or separately approved breaking-change process.
- Retain the existing top-level `carb_g` field for valid successful responses.

## 9. Approved Legacy Data Behavior

Before migration or activation of the new contract, inventory every existing Profile against the complete approved H01, H02, fat, and carbohydrate calculation policy.

If no Profile produces a zero or negative allocation, record that result as migration evidence.

If any affected Profile exists:

- Do not rewrite its calorie, protein, fat, or goal inputs silently.
- Do not fabricate a Target Plan.
- Do not activate an invalid Target Plan.
- Stop the affected migration/readiness path.
- Require a separate explicitly approved recovery decision.

Historical Diary snapshots are not recalculated or rewritten.

## 10. Approved Target Plan Behavior

Every valid newly activated Target Plan preserves:

- Final carbohydrate target.
- Applicable carbohydrate warning code or explicit no-warning state.
- Calculation-engine version.
- Relevant nutrition-rule version.

No Target Plan may store or activate a non-positive carbohydrate allocation. Exact physical persistence remains subject to formal Physical Data Model approval.

## 11. Deferred Scope

This direction does not introduce:

- Ketogenic or low-carbohydrate diet mode.
- Clinical nutrition mode.
- Clinician override.
- Specialized diabetes treatment rules.
- Athlete-specific carbohydrate targets.
- Progress UI.
- Four-week review UI.
- Direct gram/ml Diary logging.
- Unrelated Profile redesign.

## 12. Approval And Work Boundaries

The Product Owner has approved the allocation states, warning meanings and codes, domain-error behavior, compatibility direction, legacy-data guard, and Target Plan requirements recorded here. The following remain open:

- Architecture and calculation-domain contract.
- Exact API error envelope and serialization.
- Physical Target Plan representation.
- Migration inventory and any conditional recovery decision.
- Arabic UX copy and acceptance criteria.
- Backend and frontend implementation.
- Golden, boundary, compatibility, and regression verification.
- Traceability and final freeze evidence.

## 13. Recorded Status

```text
Product/contract direction: Approved
Selected direction: Shared Backend warning collection plus typed domain
error
100-<130 g: Allowed with calm warning
0-<100 g: Allowed with stronger warning
Zero or negative allocation: Rejected
carb_clamped: Deprecated compatibility field
Client-side calculation: Prohibited
Product/design blocker: Resolved
Architecture, API, Data, UX, implementation, migration inventory, and
verification: Still open
H03 overall status: Open
```

H03 must not be marked closed until its approved behavior is represented in the frozen technical contracts, the legacy inventory is complete, implementation and verification pass, and the final Wave 1 readiness recheck accepts the closure evidence.
