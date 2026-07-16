# Wave 1 Migration and Rollback Plan

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-MIG-16` |
| Version | `1.1` |
| Status | `Approved — Engineering, Data, and Operations` |
| Owner | Engineering / Data / Operations |
| Approver | Engineering / Data / Operations |
| Approval date | `2026-07-16` |
| Review evidence | `16A_WAVE1_MIGRATION_ROLLBACK_REVIEW.md` |
| Change review evidence | `W1-CD-01A_LEGACY_TARGET_TRANSITION_IMPACT_REVIEW.md` |
| Critical / High / Product decisions | `0 / 0 / 0` |
| Pinned revision | Pending |
| Implementation authorization | `No` |

## 1. Baseline and Authority

Alembic is the sole schema authority. `0001_initial → 0002_foods_v1_per_basis → 0003_diary_meal_type` is immutable. Runtime `create_all`, startup migration, manual ledger repair, and migration-file loops are prohibited. Every environment explicitly runs `alembic upgrade head` before application startup; runtime may perform read-only revision compatibility checks.

## 2. Proposed Revision Boundaries

Names are contract labels; implementation uses new immutable Alembic revisions with these dependency boundaries:

1. `0004_principal_expand`: Principal table; nullable owner columns; composite alternate keys.
2. `0005_principal_backfill`: data migration gated by explicitly provisioned deployment Principal; no hard-coded owner.
3. `0006_principal_contract`: owner non-null, one-Profile, owner indexes/FKs after reconciliation.
4. `0007_food_quality_expand`: four nullable exact nutrients and controlled source/ingredients/NOVA/category/status fields.
5. `0008_food_groups_expand`: contribution/trait tables, constraints, indexes, deferred total trigger.
6. `0009_legacy_target_transition_expand`: immutable transition table, owner/date uniqueness, indexes, and update/delete rejection trigger.
7. `0010_target_plan_expand`: Target Plan, immutable document/version/lifecycle, idempotency records, range/partial indexes.
8. `0011_diary_snapshot_v2_expand`: Diary owner-consistent plan link, provenance, nullable schema version, indexes.
9. `0012_wave1_constraint_contract`: constraints that require compatible readers and verified data; writer remains feature-gated.

Each revision is independently reviewable. Physical implementation may split a boundary for transactional PostgreSQL requirements but may not reorder dependencies or combine unrelated changes.

Version 1.1 requires the snapshot-aware reader to deploy with the writer disabled after `0009`. No migration creates snapshot rows or backfills historical targets. The first eligible activation creates its row at runtime in the same transaction as Profile and Target Plan changes.

Required W1-CD-01 rehearsal adds: fresh and populated upgrade; zero rows after migration; exact first-runtime insert; one row under concurrent activation; owner/profile FK and immutable trigger failures; transaction rollback leaving zero rows; safe rerun after failed deployment; downgrade/re-upgrade before writes; and explicit refusal to downgrade after snapshot or Target Plan writes.

The compatibility floor after first snapshot/plan write is the first release that understands `legacy_target_transition_snapshots` and the W1-CD-01 precedence. Application rollback keeps the expanded schema and may target only a verified snapshot-aware reader. Rollback to a reader that calculates historical targets from mutable Profile is prohibited. Schema downgrade is lossless only while both transition and Target Plan tables contain no data; otherwise it fails without deleting data.

## 3. Expand → Migrate → Contract

### Expand

- Add nullable owner/link/version fields and new tables.
- Preserve every legacy field and Snapshot v1 reader.
- Deploy application readers that understand old/new rows before any new writer.
- Do not assign current versions to legacy records.

### Migrate ownership

Provisioning is an explicit deployment command executed before `0005` completion. It accepts one confirmed stable Principal UUID through a protected operational input, creates/verifies that Principal, and records non-secret evidence. Migration SQL never embeds an environment owner.

Preconditions:

1. Database is at expected single Alembic head.
2. Exactly one explicitly confirmed deployment Principal exists.
3. Existing Profile cardinality is compatible with one Profile for that Principal.
4. Baseline counts for Profile, Food, Diary and null ownership are captured.

Within transaction(s), update only null owner columns to the confirmed Principal. Then compare pre/post counts, require zero null/orphan owners, and verify all existing IDs unchanged. If Principal is absent, multiple candidates exist, a row is already assigned elsewhere, or counts differ, abort and roll back. Never infer ownership from content.

### Contract

Only after reconciliation evidence: add non-null constraints, owner-consistent FKs, one-Profile uniqueness, owner indexes, and application preflight. Contract here means enforcing additive Wave 1 invariants, not removing legacy columns/readers. Removal is outside Wave 1.

## 4. No-Inference Rules

Migration never fabricates nutrients, DFE/RAE conversions, category, kind, contributions, traits, source type/reliability, ingredients, NOVA, Snapshot v2, Target Plans, historical versions, or target bindings. Known zero remains zero; unknown remains null/approved unknown. Existing cut Profiles receive only `cut_intensity=0.200`. Existing controlled fields receive approved explicit legacy states. Snapshot v1 JSON and Diary nutritional history are byte-for-byte unchanged.

## 5. Reader-Before-Writer Rollout

1. Upgrade schema through nullable expansion.
2. Deploy dual readers with v2 writer disabled.
3. Validate every v1 snapshot against the approved v1 discriminator; quarantine failures as release blockers, not repairs.
4. Rehearse mixed legacy/new relational rows.
5. Enable Target Plan writer only after Principal, rules, API, and calendar contracts are live.
6. Enable Snapshot v2 writer only after all active Backend versions can read v2.
7. Keep v1 reader and legacy response compatibility through Wave 1.

Writer gates are deployment configuration, default false until verified, and never controlled by clients.

## 6. Populated Migration Rehearsal

Use disposable PostgreSQL with anonymized/seeded realistic cardinalities and cases: one Profile, many Foods, deleted Food links, each nullable nutrient including zero/null, ambiguous legacy vitamins, Diary v1 snapshots, all meal types, and no Target Plans.

Required executable rehearsals:

- fresh database `upgrade head`;
- `0003` to head;
- populated `0003` to head;
- missing/ambiguous Principal failure;
- successful owner backfill/count reconciliation;
- interrupted boundary and safe rerun;
- mixed readers before writer;
- first Target Plan and Snapshot v2 writes;
- compatible application rollback after new writes;
- supported downgrade/re-upgrade before writes;
- schema/model drift and one-head checks.

## 7. Transaction, Failure, and Resume

Schema/data steps use Alembic/PostgreSQL transactions where supported. Indexes requiring `CONCURRENTLY` use isolated revisions with explicit failure/resume runbook. Every data migration is idempotent for already-correct rows but rejects conflicting state. A failed revision leaves the Alembic ledger unapplied. No `alembic stamp`, repair, or manual ledger mutation is allowed as automatic recovery.

Resume procedure: stop writers; capture revision and invariant queries; restore/roll back failed transaction as designed; correct only the external prerequisite; rerun the same revision; compare counts and ledger. Any manual data correction requires incident evidence and approval, never hidden SQL.

## 8. Rollback Matrix

| State | Application rollback | Schema downgrade |
|---|---|---|
| Expanded, no new-format writes | Prior reader if it tolerates additive schema | Allowed only when tested lossless |
| Ownership backfilled, before non-null | Compatible reader | May clear only migration-owned owner values if explicitly proven/rehearsed; never delete Principal silently |
| Owner constraints active | Compatible owner-aware reader | Unsupported if it would remove ownership/isolation |
| Target Plan written | Target-Plan-capable reader only | No dropping plan/version/idempotency data |
| Snapshot v2 written | v2-capable reader only | No rollback to pre-v2 reader; no dropping v2 linkage/schema |
| New Food controlled data written | compatible reader preserving fields | no lossy column/table drop |

Emergency rollback keeps expanded schema and deploys the latest previously verified compatible reader. A downgrade that would lose or reinterpret data fails explicitly as unsupported. Database restore is disaster recovery, not routine deployment rollback.

## 9. Preflight and Postflight

Preflight: expected repository revisions unique/ordered; one Alembic head; database revision known and non-divergent; explicit Principal prerequisite; valid `Asia/Riyadh`; required extensions/privileges (`btree_gist` where approved); writer gates off; backup/recovery point confirmed.

Postflight: exact ledger equality; table/column/constraint/index signatures; owner counts/orphans; one Profile/Principal; no changed snapshot hashes; no created plans; null/zero samples; legacy fields present; reader health; writer gates expected.

## 10. CI Evidence and Commands

On disposable PostgreSQL:

```text
alembic heads
alembic upgrade 0003_diary_meal_type
alembic upgrade head
alembic current
alembic downgrade <tested_lossless_boundary>
alembic upgrade head
pytest -m migration
```

CI must compare repository and database ledger exactly, run migrations with fail-closed shell behavior, detect model/migration drift, prove runtime startup never calls `create_all`, and retain logs as build artifacts without secrets. No remote/shared database is used for PR validation.

## 11. Operational Runbook

1. Announce maintenance/write gate and identify release/rollback readers.
2. Verify backup, revision, capacity, locks, and timezone/auth settings.
3. Provision/confirm Principal through approved command.
4. Run dry-run/preflight and archive outputs.
5. Apply one approved boundary at a time.
6. Run invariant/postflight queries after each boundary.
7. Deploy readers; verify mixed compatibility.
8. Enable Target Plan then Snapshot writers through separate controlled gates.
9. Monitor errors, locks, latency, integrity failures, and owner denials.
10. Close only with ledger, count, compatibility, and rollback evidence.

## 12. Security and Privileges

Migration identity has DDL rights only during approved operation. Runtime identity has no schema-owner or Service Role privilege. Provisioning inputs are not logged as credentials. All evidence redacts secrets. Advisory locks/concurrency prevent two migrations against the same target.

## 13. Deferred Scope

No legacy removal, v1 reader removal, historical fabrication, schema squash, online multi-tenant onboarding, registration, offline sync, later-wave tables, or production migration execution is authorized by this document.
