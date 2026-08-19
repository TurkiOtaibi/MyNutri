# PLAN 032 — Versioned Nutrition Pattern Analysis design 1.1 approval report

**Decision status: Design 1.1 refrozen for implementation remediation**

**Implementation authorized: NO**

**Design version:** `1.1`

**Analysis contract/interface version:** `1`

**WeeklyPriorityAnalysisInputV1 interface_version:** `1`

**First implementation-candidate rules version:** `w3-analysis-1.1.0`

**Withdrawn pre-release rules version:** `w3-analysis-1.0.0`

**Reopened implementation-review HEAD:** `e98ed022be045e649a58d0c9eb946f52f5a778af`

**Assessment date:** `2026-08-19`

## Artifact scope and authority

This decision modifies exactly:

1. `27_W3_VERSIONED_PATTERN_ANALYSIS_DESIGN.md`
2. `27A_W3_PATTERN_ANALYSIS_GOLDEN_VECTORS.json`
3. `tools/verify_w3_pattern_analysis_vectors.py`
4. `27B_W3_PATTERN_ANALYSIS_APPROVAL_REPORT.md`

No PLAN 033 artifact is modified. No application remediation, migration, generated contract, visual baseline, CI, publication, merge, deployment, or database action is authorized by this report.

## Why design 1.0 was reopened

Formal review of the pre-release implementation found two design omissions relevant to this amendment:

| Review finding | Severity | Design omission | 1.1 disposition |
| --- | --- | --- | --- |
| H2 — carb/fat target semantic incompatibility | High | Direction was range, but the authoritative scalar-to-range representation and cross-period compatibility rule were not exact | Target Plan carb/fat scalars now map only to degenerate ranges `[v,v]`; incompatible or missing target authority is closed and fail-safe |
| M1 — Admin monitoring projection incomplete | Medium | Cohort, counting unit, deduplication and exact coverage/stale/latency boundaries were not frozen | UTC ISO-week cohort and all closed monitoring maps/boundaries are now exact |

Because H2 can change analysis output, the rules version changes. `w3-analysis-1.0.0` is **WITHDRAWN PRE-RELEASE**: it was never merged to main as an accepted PLAN 032 implementation, deployed, or used for production/shared revisions. It is unavailable for dispatch and is never aliased or silently mapped to 1.1. `w3-analysis-1.1.0` is the first implementation candidate after refreeze.

## Amended decision matrix

| Decision | Refrozen result |
| --- | --- |
| Public contract | Analysis interface and `WeeklyPriorityAnalysisInputV1.interface_version` remain `1`; field names and enums unchanged |
| Rules | Exact dispatch only to `w3-analysis-1.1.0`; withdrawn 1.0 has no fallback |
| Unknown/zero | Wholly unknown stays null/unknown; observed zero stays explicit zero; mixed evidence aggregates known facts and reports reduced coverage |
| Carb/fat source | Exact effective `TargetResponse.carb_g`/`fat_g`; finite positive scalar `v` becomes range `[v,v]` with no tolerance |
| Compatibility | One non-null target only when one semantically identical target represents every target-bearing numeric day across both periods |
| Incompatible target | Null target; safe raw values retained; numeric periods are `target_incompatible`; comparison/persistence suppressed; `incompatible_target` flag |
| Missing target | Null target; known raw facts may be observed display-only; target-relative behavior suppressed; `missing_target` remains distinct |
| Schema | Direction and target type must agree; minimize/monitor-only forbid targets; contradictory projections fail validation |
| Monitoring cohort | Finalized revisions with `finalized_at` in requested UTC ISO week `[Monday,next Monday)` |
| Coverage bands | Current metric coverage, one count per revision/metric, exact null/50/75/100 boundaries and four closed keys |
| Stale reasons | Distinct revision per reason at query time; five closed reasons; duplicate events do not inflate counts |
| Latency | New-revision `finalized_at-generated_at`; exact five bands; replay/no-change creates no sample |
| Complete days | Existing `0-3`, `4-5`, `6-7` semantics unchanged |
| PLAN 033 | Not reopened; explicit source rules version remains fail-closed and carb/fat are not priority keys |

## Fresh discipline assessment matrix

Provenance: these are Codex discipline-specific assessments performed under explicit Project Owner authorization. They are **not** eight independently submitted named human reviews. No named-human signatures or independent submissions are asserted.

| Authority | Decision | Blocking findings | Non-blocking notes | Evidence |
| --- | --- | --- | --- | --- |
| Product Owner | APPROVED | None | Implementation remediation still requires separate authority | Exact source target, no invented tolerance, closed incompatible/missing states, and useful monitoring semantics resolve the reviewed product ambiguity |
| Nutrition / Safety | APPROVED | None | Degenerate range is allocation representation, not a clinical safe range | Non-finite/non-positive sources fail closed; unknown is not zero; incompatible/missing targets cannot drive downstream selection; no clinical claim added |
| Data / Analysis | APPROVED | None | Monitoring latency is diagnostic, not an SLA | Exact range distance, cross-period semantic equality, UTC cohort, deduplicated stale counts, and 49.999/50/74.999/75/100 plus latency boundaries are executable |
| Architecture / API | APPROVED | None | Application paths must be re-derived before remediation | Interface v1 and enums remain stable; projection contradictions fail validation; rules 1.0 is not aliased; monitoring is defined from authoritative revision/events |
| Security / Privacy | APPROVED | None | Existing access control remains implementation evidence | Monitoring exposes aggregate bands only, with no Principal/raw evidence; raw safe metric values remain owner-bound; error/fail-closed behavior is unchanged |
| UX / Arabic / Accessibility | APPROVED | None | No copy or shape change is needed | Existing unavailable/observed/incompatible vocabulary remains; null target is truthful; no new UI field, enum, focus, RTL, or accessibility contract is introduced |
| Notifications / Operations | APPROVED | None | PLAN 033 launch/reminder ownership remains separate | UTC operational cohort is distinct from Diary time; complete keys include zero; latency bands are diagnostics only; no reminder or rollout threshold changes |
| QA | APPROVED | None | Production remediation must exercise orchestration and monitoring queries | 77 deterministic vectors and 17 independent mutations cover unknown/zero, exact ranges, incompatibility, schema contradictions, monitoring boundaries and replay exclusion |

## Findings and disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | H2 scalar/range and incompatible-target semantics were incomplete | Resolved in design, corpus and independent mutations |
| Medium | M1 monitoring cohort and map semantics were incomplete | Resolved in design, corpus and independent mutations |
| Note | Rules version must reflect output-semantic change | Resolved: 1.0 withdrawn pre-release; 1.1 first implementation candidate |
| Note | Downstream PLAN 033 is frozen | Verified read-only compatible; no PLAN 033 artifact or contract change |

Unresolved Blocker/Critical/High/Medium findings: **none**.

## Cross-plan compatibility

- **PLAN 031 → PLAN 032: PASS.** This amendment does not alter the captured Riyadh date, Diary status, completion, eligibility, or evidence-version contracts.
- **PLAN 032 → PLAN 033: PASS.** `WeeklyPriorityAnalysisInputV1.interface_version` stays `1`; no field or enum changes. Its target was already nullable and its closed vocabulary already contains `target_incompatible`, `incompatible_target`, `missing_target`, and `target_changed`. PLAN 033 consumes an explicit `analysis_rules_version`, fails closed on unsupported `w3-analysis-1.1.0`, does not select carb/fat priority keys, and does not reconstruct range bounds.

## Validation evidence

| Gate | Result |
| --- | --- |
| Golden vectors | 77 passed, 0 failed |
| Independent negative mutations | 17/17 correctly rejected |
| JSON syntax | PASS |
| Verifier independence | PASS — expected JSON is compared against standard-library calculations and seven new semantic mutations alter evaluator behavior independently |
| Decision completeness | PASS |
| Cross-artifact consistency | PASS |
| PLAN 032 → PLAN 033 read-only compatibility | PASS |
| `git diff --check` | PASS |
| Changed scope | Exactly four authorized PLAN 032 design artifacts |

New evidence proves wholly unknown/observed-zero/mixed aggregation, carb/fat scalar-to-degenerate-range projection, below/exact/above range distance, incompatible versus missing targets, schema contradictions, exact coverage and latency boundaries, distinct stale-reason counting, no replay latency, and unchanged V1 downstream structure. Independent mutations reject scalar-minimum substitution, invented tolerance, target selection from incompatible evidence, false non-null incompatible targets, duplicate stale counting, and shifted coverage/latency boundaries in addition to the original ten mutations.

## Gate result

All eight fresh discipline assessments approve design 1.1. The amended decisions are deterministic, executable, internally consistent, privacy/safety bounded, and compatible with frozen PLAN 031 and PLAN 033. No unresolved Medium-or-higher finding remains.

**PLAN 032 DESIGN 1.1 — REFROZEN FOR IMPLEMENTATION REMEDIATION**

Implementation remediation remains unauthorized. Its exact path scope may now be re-derived in a separate read-only gate.
