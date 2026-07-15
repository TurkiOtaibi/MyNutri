# H11 Approved Product Owner Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `DEC-H11` |
| Issue ID | `H11` |
| Severity | High |
| Title | All-unknown nutrient data is displayed as numeric zero |
| Product/truthful-aggregation direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H11 product/contract blocker only. It does not authorize implementation and does not close H11.

## 2. Approved Authority Boundary

The Backend owns all Diary nutrient aggregation, coverage, target resolution, and evaluation semantics. The Frontend renders the authoritative response and must not maintain independently authoritative nutrient aggregation.

## 3. Approved Per-Nutrient Response Semantics

Return one aggregate for every applicable Nutrition Registry nutrient participating in Diary coverage. Each aggregate contains fields equivalent to:

- key;
- amount: number or null;
- `known_entry_count`;
- `total_entry_count`;
- `coverage_percent`: number or null;
- `coverage_state`;
- `amount_qualifier`;
- resolved target metadata or reference;
- evaluation/status metadata.

Exact names and serialization remain for the formal API Contracts.

Approved `coverage_state` meanings:

```text
no_entries
all_unknown
partial
complete
```

Approved `amount_qualifier` meanings:

```text
unavailable
at_least
exact
```

## 4. Counting Semantics

`total_entry_count` is the count of valid, owner-scoped Diary entries included in the day summary. `known_entry_count` counts those entries whose approved snapshot reader yields a numeric value for the nutrient.

- Explicit numeric zero is known.
- Null is unknown.
- A nutrient absent from valid legacy Snapshot v1 is unknown.
- Unsupported or malformed snapshots are not counted merely as unknown.
- Unsupported or malformed snapshots trigger H08 data-integrity behavior and prevent understated totals.

The Backend calculates:

```text
coverage_percent = known_entry_count / total_entry_count × 100
```

API precision may be technical, but counts are canonical evidence.

## 5. Empty-Day Behavior

When `total_entry_count = 0`:

```text
amount = null
known_entry_count = 0
coverage_percent = null
coverage_state = no_entries
amount_qualifier = unavailable
```

No nutrient progress, remaining/available value, adequacy, limit, or target status is returned. The UI shows an approved empty-day state instead of fabricated rows or zeros.

## 6. All-Unknown Behavior

When `total_entry_count > 0` and `known_entry_count = 0`:

```text
amount = null
coverage_percent = 0
coverage_state = all_unknown
amount_qualifier = unavailable
```

The user-facing amount means `غير متوفر`. Do not display numeric zero or `على الأقل`. Suppress percentage, target progress, remaining, available, adequacy, and limit status.

## 7. Partial-Coverage Behavior

When `known_entry_count > 0` and lower than `total_entry_count`:

- amount is the sum of known values after approved quantity scaling;
- `coverage_state = partial`;
- `amount_qualifier = at_least`;
- user-facing meaning is `على الأقل [القيمة]`;
- the amount is not presented as exact.

## 8. Complete-Coverage Behavior

For a non-empty day where known and total counts are equal:

```text
coverage_percent = 100
coverage_state = complete
amount_qualifier = exact
```

Amount is exact. Complete target evaluation and remaining/available semantics may be returned according to target type.

## 9. Target Evaluation With Partial Coverage

### 9.1 Minimum, recommended, and adequate

- If the confirmed known minimum reaches or exceeds target, evaluation meaning is `met_at_least`; achievement may be stated because actual intake cannot be below the confirmed amount.
- If confirmed amount is below target, evaluation meaning is `indeterminate_partial_coverage`; do not claim the target was missed or present definitive remaining amount.

### 9.2 Maximum

- If confirmed known amount exceeds maximum, evaluation meaning is `exceeded_at_least`; exceeding may be stated.
- Otherwise evaluation is `indeterminate_partial_coverage`; do not claim intake is within limit or return definitive available/remaining allowance.

### 9.3 Range

- If confirmed known amount exceeds upper bound, evaluation meaning is `above_range_at_least`.
- Other partial states use `indeterminate_partial_coverage`; do not claim below, within, or safely inside range.

### 9.4 Monitor only

Return amount and qualifier only. Do not return target progress, remaining, or adequacy status.

### 9.5 Minimize

Do not fabricate numeric target, percentage, or safe allowance when no approved numeric rule exists.

## 10. Progress And Remaining Semantics

- Complete coverage uses the approved target-type contract.
- Partial coverage may show confirmed progress amount with explicit `at_least` and visible coverage, but definitive remaining/available amounts are suppressed.
- Incomplete coverage must not imply confirmed shortfall or safe remaining allowance.
- All-unknown coverage displays no progress.
- Remaining or available values never display as negative numbers.

## 11. Historical Target Resolution

The Backend evaluates against the target source approved for the Diary date: versioned Target Plan, approved legacy target source, or no target source. Mutable current Profile must not reinterpret a historical day.

When `target_provenance = no_target_source`, return amount and coverage without fabricated target evaluation.

## 12. Overall Daily Nutrient Coverage

For a non-empty day, `overall_nutrient_coverage_percent` is the Backend-calculated arithmetic mean of per-nutrient percentages for Registry nutrients marked as participating in Diary coverage.

For an empty day:

```text
overall_nutrient_coverage_percent = null
```

Registry-excluded nutrients do not enter the average. Malformed or unsupported snapshots prevent misleading overall coverage and follow approved integrity-error behavior.

## 13. API And Frontend Boundary

The Backend returns authoritative nullable amounts, counts, coverage, target references, qualifiers, and evaluation meanings.

The Frontend does not authoritatively recalculate amounts, change null to zero, infer coverage, or independently decide target achievement. It maps approved semantics to Arabic UI.

Stable field names, errors, and localization ownership remain for formal API and UI artifacts.

## 14. Migration And Historical Compatibility

No H11-specific data backfill is required.

- Snapshot v1 remains unchanged.
- Snapshot v2 follows H08.
- Mixed v1/v2 aggregation uses approved version readers.
- Current Food does not enrich old snapshots.
- Unknown remains null and known zero remains zero.
- Malformed or unsupported snapshots are not silently omitted.

## 15. Deferred Scope

This direction does not introduce seven-day Nutrition Pattern Analysis, Progress UI, weekly recommendations, behavior goals, clinical interpretations, direct gram/ml Diary logging, offline aggregation authority, or unrelated Diary redesign.

## 16. Status

```text
Artifact ID: DEC-H11
Selected direction: Backend-authoritative nullable nutrient aggregation
Frontend authoritative aggregation: Prohibited
Known zero: Known value
Unknown: null
All-unknown amount: null
Partial amount: Confirmed minimum
Empty-day coverage: null
All-unknown coverage: 0
Partial remaining and available: Suppressed
Malformed Snapshot silent omission: Prohibited
Product/contract blocker: Resolved
Architecture, Security, API, UX, implementation, and verification: Still open
H11 overall status: Open
```

H11 remains open until exact contracts and UI states are approved and pinned, Backend and Frontend implementation completes, null/zero and mixed-history behavior is verified, and final traceability and readiness gates close.
