# C02 Approved Product Owner Decision

## 1. Issue Identity

| Item | Value |
|---|---|
| Artifact ID | `DEC-C02-11` |
| Issue ID | `C02` |
| Severity | Critical |
| Title | The formal Wave 1 freeze package does not exist |
| Product Owner decision | Approved |
| Selected direction | Linked modular freeze package |
| Authoritative manifest | One Wave 1 Freeze Index |
| Decision-record lifecycle | Draft - unpinned local record |
| Version | Pending |
| Pinned commit/revision | Pending |
| Product Owner name | Pending |
| Approval date | Pending |

The Product Owner decision is approved. This uncommitted local record is not approved freeze evidence until it is reviewed, versioned, and pinned to an exact repository revision.

## 2. Governing Decisions

- `PD-001` - Document authority and change control.
- `PD-004` - Expansion waves and scope sequencing.
- `PD-029` - Readiness gate and formal scope freeze.

The complete v1.1 register remains authoritative for product intent. This record defines the approved package structure used to satisfy its readiness gate; it does not replace the register.

## 3. Approved Option

Wave 1 uses linked modular freeze artifacts governed by one authoritative Freeze Index.

The Freeze Index is a manifest and authority map. It must not duplicate the complete content of the linked contracts.

The Freeze Index distinguishes:

1. **Implemented Baseline Code Commit** - the stable operational application baseline that the expansion must preserve.
2. **Governing Register Commit** - the exact approved Product Decision Register revision.
3. **Final Freeze Package Commit** - the exact revision containing all completed, approved, and pinned Wave 1 freeze artifacts.

Uncommitted local drafts are not approved freeze evidence. A Final Freeze Package Commit must not be invented or inferred from a working tree.

## 4. Non-Selected Alternative

### One monolithic Wave 1 specification

This alternative was not selected.

Reasons:

- It creates one oversized approval surface.
- It makes architecture, schema, API, BA/UX, and QA ownership unclear.
- It increases the likelihood of internal contradictions.
- It encourages broad implementation changes rather than independently reviewable stages.
- It makes versioning and supersession harder to audit.

The modular package is selected because each contract can be independently reviewed while one Freeze Index preserves cross-artifact authority and traceability.

## 5. Rationale

The selected structure:

- separates Product Owner decisions from technical design;
- prevents implementation from resolving unapproved assumptions;
- allows independent specialist approvals;
- exposes unresolved dependencies rather than hiding them;
- preserves one authoritative package view;
- supports small implementation stages after freeze;
- protects the implemented brownfield baseline;
- prevents later-wave and deferred scope from entering Wave 1;
- preserves existing regression coverage as a mandatory baseline asset.

The modular artifacts must not become isolated or contradictory sources of truth. Any contradiction blocks freeze until the authoritative decision and dependent artifacts are reconciled.

## 6. Authority And Approval Ownership

| Authority | Approval responsibility |
|---|---|
| Product Owner | Wave 1 product scope, exclusions, user-visible behavior, Product Decisions, and final product scope-freeze status |
| Architecture | Architecture ADRs and system-boundary decisions |
| Security | Authentication, ownership, authorization, privacy, and security ADRs |
| Engineering/Data | Physical schema, migration, rollback, compatibility, and data-integrity design |
| API owners | Requests, responses, errors, null semantics, idempotency, and backward compatibility |
| BA/UX | User stories, acceptance criteria, Arabic behavior, and user-facing states |
| QA | Verification coverage, regression scope, traceability, and release evidence |

Unknown individual owners, approvers, dates, versions, and commits remain `Pending`. No person or approval date is inferred by this decision record.

## 7. Required Artifact Structure

The approved modular freeze package consists of:

| Artifact | Purpose |
|---|---|
| `12_WAVE1_FREEZE_INDEX.md` | Authoritative manifest, dependency map, approval map, and readiness status |
| `13_WAVE1_ARCHITECTURE_SECURITY_ADRS.md` | Approved architecture, security, ownership, and rule-authority decisions |
| `14_WAVE1_PHYSICAL_DATA_MODEL.md` | Exact physical schema, constraints, ownership, compatibility, and data semantics |
| `15_WAVE1_API_CONTRACTS.md` | Exact additive APIs, errors, nulls, idempotency, and compatibility examples |
| `16_WAVE1_MIGRATION_ROLLBACK_PLAN.md` | Expand-Migrate-Contract, rollback, rehearsal, and legacy-data protection |
| `17_WAVE1_USER_STORIES_ACCEPTANCE_CRITERIA.md` | Approved stories and testable acceptance criteria |
| `18_WAVE1_GOLDEN_CALCULATIONS.md` | Fixed calculation, target, boundary, warning, and rejection scenarios |
| `19_WAVE1_UI_STATE_MATRIX.md` | Loading, empty, partial, unknown, legacy, error, keyboard, RTL, responsive, and accessibility states |
| `20_WAVE1_VERIFICATION_REGRESSION_PLAN.md` | Focused verification, full baseline regression, migration, security, and release evidence |
| `21_WAVE1_TRACEABILITY_MATRIX.md` | Decision-to-contract-to-story-to-test-to-closure traceability |

Artifacts 13-21 must remain independently reviewable and linked through artifact IDs and exact dependencies.

## 8. Freeze Index Requirements

Every referenced artifact records:

- stable Artifact ID;
- exact repository path;
- purpose;
- version;
- lifecycle status;
- owner;
- approver;
- approval date;
- exact pinned commit or revision;
- dependencies;
- superseded artifact or version, when applicable;
- blocking issues;
- closure evidence.

The Freeze Index must:

- expose unresolved dependencies;
- distinguish product approval from technical approval;
- distinguish approved decisions from unpinned records;
- never mark a blocked artifact `Approved` or `Frozen`;
- pin the baseline, register, and final package separately;
- preserve the current implemented baseline;
- state the current Critical and High unresolved counts;
- state whether implementation is authorized;
- require a final readiness recheck against the exact Final Freeze Package Commit.

## 9. Compatibility And Baseline-Preservation Rules

The freeze package must preserve:

- the current implemented Foods, Diary, Add Food, and Profile behavior unless an approved Wave 1 delta explicitly changes a contract;
- current route compatibility through additive contracts where practical;
- existing per-100 Food source-of-truth behavior;
- immutable Diary nutrition history;
- online-only operation;
- the personal single-principal product decision;
- existing regression suites and meaningful coverage.

The package must prevent:

- broad or greenfield rewrites;
- unrelated UI redesigns;
- reintroduction of offline personal-data storage or synchronization;
- reintroduction of multiple Profiles or profile switching;
- accidental implementation of later waves;
- accidental implementation of deferred scope;
- weakening existing regression coverage;
- silent reinterpretation of historical data.

## 10. C02 Status

```text
Product Owner decision: Approved
Selected direction: Linked modular freeze package
Authoritative manifest: One Wave 1 Freeze Index
Product/design decision blocker: Resolved
Freeze package completion blocker: Still open
C02 overall status: Open until all required artifacts are completed,
approved, pinned, and the final readiness recheck passes
```

Status interpretation:

- **Product decision resolved.**
- **Technical and documentation work still open.**
- **Overall Critical issue still open.**

This decision does not authorize implementation and does not mark Wave 1 `Ready to Build`.

## 11. Complete-Closure Conditions

C02 closes only when:

1. The Freeze Index and every required artifact exist.
2. Every required artifact has an approved lifecycle status.
3. Artifact ownership and approval responsibility are complete.
4. Every approved artifact records its approver and approval date.
5. Every artifact is pinned to an exact commit or revision.
6. The Implemented Baseline Code Commit is recorded.
7. The Governing Register Commit is recorded.
8. The Final Freeze Package Commit is recorded and contains the complete package.
9. Every active Wave 1 decision is traceable to approved contracts and verification.
10. Exact physical schema and ownership constraints are approved.
11. Migration, rollback, compatibility, and rehearsal design are approved.
12. API requests, responses, errors, null semantics, idempotency, and backward compatibility are approved.
13. User stories and acceptance criteria are approved.
14. Golden calculations and boundaries are approved.
15. UI states and accessibility/responsive behavior are approved.
16. Verification and regression coverage are approved.
17. Critical issues equal zero.
18. High unresolved issues equal zero.
19. Deferred and later-wave scope remains excluded.
20. A readiness recheck against the exact Final Freeze Package Commit reports `Ready to Build`.

Until every condition is met, C02 remains open and implementation authorization remains `No`.
