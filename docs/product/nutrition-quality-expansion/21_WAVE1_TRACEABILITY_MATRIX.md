# Wave 1 Traceability Matrix

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-TRACE-21` |
| Version | `1.0` |
| Status | `Approved — BA, QA, and Governance` |
| Owner | BA / QA / Governance |
| Approver | BA / QA / Governance |
| Approval date | `2026-07-16` |
| Review | `21A_WAVE1_TRACEABILITY_REVIEW.md` |
| Critical / High / Product decisions / gaps | `0 / 0 / 0 / 0` |
| Pinned revision | `da507c16e1d233238885e631d4daeed5d635aca5` |
| Implementation authorization | `No` |

## 1. Artifact Version and Pin Register

| Artifact | Version | Approval | Pinned revision |
|---|---:|---|---|
| `W1-ADR-13` | 1.0 | Architecture and Security | `c7c48746715d24238acd70cd4eea137bf0f87cfd` |
| `W1-DATA-14` | 1.0 | Engineering and Data | `afa3a9bb220a7798920d7edc1b0949da15f2d7fe` |
| `W1-API-15` | 1.0 | API and Architecture | `400366b39abb73bb2e2d2ba82c79c1cd524d6e67` |
| `W1-MIG-16` | 1.0 | Engineering, Data, Operations | `ead5de21fe1153126f6c19c9f7aeba6a732ace89` |
| `W1-BAQA-17` | 1.0 | Product, BA, UX | `ffde6f597750b18e85d861c36d3dfad105d36f0e` |
| `W1-GOLDEN-18` | 1.0 | Engineering and QA | `e714b4c374166a27a8aa1b40ab4b851ce0b92a9d` |
| `W1-UI-19` | 1.0 | BA, UX, Accessibility | `6a392d11c747c784e37f42c9fd6bfb15cc010d5a` |
| `W1-VERIFY-20` | 1.0 | QA, Security, Engineering | `02d1abed01aeb5681b3f84245b692516235da60b` |
| `W1-TRACE-21` | 1.0 | BA, QA, Governance | `da507c16e1d233238885e631d4daeed5d635aca5` |

Pinned revision identifies the approval content commit; subsequent pin metadata commits do not change the approved substantive contract.

## 2. Product Decision Traceability

| Decision | Wave 1 disposition | Direction/ADR | Data/API/Migration | Story/Golden/UI | Verification |
|---|---|---|---|---|---|
| `PD-000` baseline | Preserve/additive | ADR all | 14 delta; 15 compatibility; 16 baseline | common contract | regression inventory |
| `PD-001` authority | Active governance | C02/Freeze Index | all artifacts | IDs/versioning | approval/pin gates |
| `PD-002` product boundary | Active | ADR-001/004/008 | 14-16 | US-001/008/015 | ownership/authority |
| `PD-003` navigation | Preserve, no redesign | ADR-010 | API dates | UI global | responsive regressions |
| `PD-004` waves | Wave 1 only | C02 | deferred excluded | common out-of-scope | scope gate |
| `PD-005` deficit | Active | H01/ADR-005 | plan/profile/preview | US-002/003; GC-002/003 | golden/API |
| `PD-006` protein | Active | H02/ADR-004/005 | plan provenance/API object | US-004; GC-004/005 | boundary golden |
| `PD-007` fat/carbs | Active | H03 | warning/error contract | US-005; GC-006/007 | preview/activation |
| `PD-008` Target Plans | Wave 1 foundation; Progress review UI deferred | H04/ADR-005/009/010 | plan model/API/migration | US-006/007/014; GC-029-035 | atomic/concurrency |
| `PD-009` nutrients | Active 16 | H05/ADR-004/007 | Food/Registry/plan/snapshot | US-008/009/015; GC-008-015 | Registry/golden |
| `PD-010` groups/servings | Active foundation | H06/ADR-004/007 | group model/API | US-010; GC-016-024 | rule/constraint |
| `PD-011` contributions | Active | H06 | normalized tables/API | US-010 | concurrent totals |
| `PD-012` NOVA/ingredients | Active foundation | H07 | Food/API/snapshot | US-011/012 | transitions/history |
| `PD-013` completeness/source/coverage | Active | H07/H11/ADR-008 | Food/snapshot/summary | US-009/011/015; UI-033-035 | null/coverage |
| `PD-014` Snapshot v2 | Active | H08/ADR-006 | Diary model/API/migration | US-013/014/016; GC-025-028 | v1/v2/integrity |
| `PD-015` day status | Deferred later analysis foundation | scope exclusion | no Wave 1 field/route | no story/UI | scope test |
| `PD-016` Pattern Analysis | Deferred Wave 3 | H10 reserved analysis | no schema/API | none | no implementation |
| `PD-017` priority engine | Deferred Wave 3 | H10 | none | none | no implementation |
| `PD-018` behavior goals | Deferred | scope | none | none | no implementation |
| `PD-019` analysis snapshots | Deferred Wave 3 | H10 analysis null | no table | none | no implementation |
| `PD-020` Progress/measurements | Deferred | H01/H04 exclusions | no fields/routes | none | no implementation |
| `PD-021` milestones | Deferred | scope | none | none | no implementation |
| `PD-022` safety/language | Active | H01/H03/ADR-008 | stable errors | US-003/005/015/018; UI | a11y/language |
| `PD-023` ownership/security | Active | C01/ADR-001/002/009 | owner model/API/migration | US-001/017 | two-Principal/IDOR |
| `PD-024` migration | Active | H09/ADR-003 | Artifact16 | legacy criteria | PostgreSQL gates |
| `PD-025` Backend authority | Active | ADR-002/004/006-008 | all API/writers | common | no client authority |
| `PD-026` versions | Active | H10/ADR-004/007 | version matrices/Registry | GC versions | manifest/history |
| `PD-027` recommendation validation | Deferred with recommendation engine | scope | none | none | no implementation |
| `PD-028` success metrics | Deferred measurement | scope | none | none | no implementation |
| `PD-029` readiness/freeze | Active | C02 | all approvals/pins | coverage gates | final recheck |

## 3. Critical/High Issue Traceability

| Issue | Approved direction | ADR | Contracts | Story/UI | Verification/closure |
|---|---|---|---|---|---|
| C01 | `DEC-C01-10` | 001/002 | 14 Principal; 15 auth; 16 backfill | US-001 | two-Principal + migration |
| C02 | `DEC-C02-11` | artifact governance | 13-21 | all IDs | final recheck/freeze |
| H01 | `DEC-H01` | 005 | plan/API | US-002/003; GC-002/003 | golden/atomic |
| H02 | `DEC-H02` | 004/005 | plan/API protein | US-004; GC-004/005 | BMI boundaries |
| H03 | `DEC-H03` | 005 | API warning/error | US-005; GC-007 | no clamp |
| H04 | `DEC-H04` | 005/009/010 | plan lifecycle | US-006/007/014 | concurrency/date |
| H05 | `DEC-H05` | 004/007 | Registry/Food | US-008/009 | manifest/16 fields |
| H06 | `DEC-H06` | 004/007 | groups/traits | US-010; GC-016-024 | constraints/rules |
| H07 | `DEC-H07` | 004/007 | source/NOVA | US-011/012 | mapping/history |
| H08 | `DEC-H08` | 006 | snapshot/Diary | US-013/014/016 | v1/v2/integrity |
| H09 | `ADR-DIR-H09` | 003 | migration plan | legacy criteria | disposable PG |
| H10 | `ADR-DIR-H10` | 004/007 | versions/Registry | US-008; GC versions | manifest bump |
| H11 | `DEC-H11` | 008 | aggregation API | US-015; UI-032-036 | null/coverage |

## 4. Bidirectional Contract Map

- Every Artifact 14 table/constraint maps to ADR-001/003/005/006/009/010 and API/migration/security tests.
- Every Artifact 15 capability maps to at least one story and verification section; no orphan endpoint exists.
- Every Artifact 16 step maps to Artifact 14 delta and Artifact 20 migration evidence.
- Every `W1-US-001..018` maps backward to approved decisions and forward to API/UI/tests.
- Every `W1-GC-001..035` maps to calculation/group/snapshot/plan rules and future automated tests.
- Every `W1-UI-001..038` maps to API/story and test placeholder.
- Artifact 20 covers all active decisions and explicitly checks deferred non-implementation.

## 5. Uncovered and Orphan Audit

| Check | Result |
|---|---|
| Active Wave 1 PD without contract | 0 |
| C01/C02/H01-H11 without direction/ADR/contract/test | 0 |
| ADR-001-010 without downstream artifact | 0 |
| Data table without API/migration/test rationale | 0 |
| API capability without story/test | 0 |
| Story without governing decision | 0 |
| Golden scenario without rule | 0 |
| UI state without API/story/test | 0 |
| Deferred decision accidentally implemented in contract | 0 |
| Superseded source used as authority | 0 |

Traceability gaps: `0`.

## 6. Superseded and Deferred Integrity

The complete v1.1 Register, approved direction records, and Artifact 13 supersede provisional NQ IDs, old offline-first/multi-profile assumptions, actual-weight-only protein, silent carb clamp, duplicated Registry authority, and mutable historical target assumptions. PD-015-021 and PD-027-028 remain approved future decisions but are outside Wave 1 implementation. PD-008's four-week Progress experience remains deferred while immutable Target Plan foundation is Wave 1.

## 7. Implementation Stage Sequence

1. Architecture-preserving package/rules/auth calendar foundations.
2. Artifact 16 nullable Principal expansion/provision/backfill/contract.
3. Food exact fields and controlled source/NOVA.
4. Group/trait structures and Registry read capability.
5. Target Plan/idempotency structures and dual-compatible APIs.
6. Diary owner/link/version and v1/v2 readers.
7. Controlled Target Plan then Snapshot v2 writers.
8. Frontend Profile/Food/Diary states without unrelated redesign.
9. Full Artifact 20 gates, physical QA, release evidence.

Each stage is independently reviewable; no broad rewrite or later-wave mixing.

## 8. Readiness Checklist

- Artifacts 13-20 approved and pinned: Yes.
- Artifact 21 review pending at draft stage.
- Critical/High findings in approved artifacts: 0.
- Product decisions remaining: 0.
- Traceability gaps: 0.
- Deferred scope preserved: Yes.
- Product code changed by freeze authoring: No.

Artifact 21 approval and pinning are required before final readiness recheck.
