# H09 Approved Architecture And Migration Direction

## 1. Issue Identity

| Field | Value |
|---|---|
| Artifact ID | `ADR-DIR-H09` |
| Issue ID | `H09` |
| Severity | High |
| Title | Wave 1 migration and rollback are unfrozen; schema authority is ambiguous |
| Architecture/migration direction | Approved |
| Document lifecycle status | Draft - approved direction record, not pinned freeze evidence |
| Version | Pending |
| Owner | Pending |
| Approver | Pending |
| Approval date | Pending |
| Pinned commit/revision | Pending |

This record resolves the H09 architecture/migration direction blocker only. It does not authorize implementation and does not close H09.

## 2. Approved Schema-Authority Direction

Alembic is the sole schema authority for:

- application runtime;
- local application development;
- deployed environments;
- integration environments;
- migration verification;
- release evidence.

Application startup must not call `SQLModel.metadata.create_all` or an equivalent automatic schema-creation operation. It must not silently apply migrations.

Application startup may perform a read-only compatibility or preflight check and fail clearly when the database revision is missing, behind, divergent, or unsupported.

Local development and deployment explicitly run an approved command equivalent to `alembic upgrade head` before starting the application.

## 3. Test-Only `create_all` Boundary

`SQLModel.metadata.create_all` may be used only inside explicitly isolated and disposable unit-test fixtures.

- Such a fixture must not be imported or invoked by application runtime.
- It must not be used by integration, migration, compatibility, or release tests.
- It is not accepted as migration evidence.
- It must be unmistakably test-only.
- CI must prove runtime startup does not invoke `create_all`.

Integration and migration tests use disposable PostgreSQL databases constructed through Alembic.

## 4. Existing Migration Baseline

The immutable Wave 1 migration baseline is:

```text
0001_initial
→ 0002_foods_v1_per_basis
→ 0003_diary_meal_type
```

Do not edit, reorder, squash, or change the revision/down-revision identities of these revisions. Later corrections use new revisions.

## 5. Approved Logical Wave 1 Ordering

Exact revision numbers, filenames, and physical split remain subject to the formal Physical Data Model and Migration Plan approvals. The sequence must respect this dependency order:

1. Add durable Principal structure and nullable ownership relationships.
2. Explicitly provision the approved deployment Principal.
3. Backfill existing ownership and verify row counts.
4. Enforce ownership, uniqueness, and owner-aware indexes.
5. Add approved exact nutrient, source, ingredients, and NOVA fields.
6. Add normalized Food-group contribution and analytical-trait structures.
7. Add hybrid immutable Target Plan and rule-version structures.
8. Add Diary ownership, Target Plan linkage, target provenance, and Snapshot v2 version/linkage support.
9. Deploy compatible readers for old and new data.
10. Enable new writers only after compatibility and migration evidence passes.
11. Retain legacy compatibility fields and readers throughout Wave 1.

One logical stage may use multiple independently reviewable Alembic revisions for safe `Expand → Migrate → Contract` behavior. Unrelated schema changes must not be combined merely to reduce revision count.

## 6. Principal Provisioning And Ownership Backfill

No migration embeds an arbitrary environment-specific owner identity.

Use an explicit staged process equivalent to:

1. expand with Principal and nullable owner relationships;
2. explicitly provision and confirm the deployment Principal;
3. verify exactly one authoritative deployment Principal for the existing single-principal dataset;
4. backfill Profile, Food, and Diary ownership;
5. reconcile expected and migrated row counts;
6. verify no orphan or ambiguous row remains;
7. enforce non-null and owner-aware constraints.

If the deployment Principal cannot be established explicitly, stop. Do not use an unknown or anonymous owner, infer identity from record content, or proceed to non-null enforcement.

Exact provisioning command, transaction boundaries, and revision split require Architecture, Security, Engineering/Data, and QA approval.

## 7. Additive And No-Inference Rules

Wave 1 migrations must not infer or fabricate:

- record ownership;
- nutrient values;
- exact Folate DFE or Vitamin A RAE values;
- primary categories or Food kind;
- Food-group contributions or analytical traits;
- controlled source types or source reliability;
- ingredients or NOVA;
- Snapshot v2 content;
- historical Target Plans;
- historical rule versions.

Unknown remains null or the approved explicit unknown state. Known numeric zero remains zero. Historical Snapshot v1 content is not enriched or rewritten. Legacy fields remain readable.

No legacy field, table, or reader is removed during Wave 1 without a separate formal Change Decision.

## 8. Reader-Before-Writer Rollout

Compatible readers must be deployed and verified before enabling any writer that produces Target Plans, Snapshot v2, Registry-version-bound documents, or lifecycle states not understood by the baseline reader.

The rollout provides a controlled writer-enable boundary. Mixed-version compatibility must be tested. Frontend and Backend must not assume historical rows have new fields populated.

## 9. Rollback Policy

### 9.1 Before new-format data is written

Additive revisions should support tested downgrade and re-upgrade where this is lossless.

### 9.2 After new-format data is written

Production rollback may target only an application release capable of reading every written format. Do not roll back to a release that cannot read new data, and do not drop data-bearing Wave 1 objects as an emergency rollback.

Keep expanded schema while rolling the application back to a compatible reader. Schema downgrade is allowed only when proven lossless for actual data. A potentially lossy or reinterpretive downgrade must fail clearly or be documented as unsupported.

The Contract/removal phase is outside Wave 1.

## 10. CI And Verification Gates

Formal Migration and Verification artifacts require executable PostgreSQL evidence for:

- exactly one Alembic head;
- fresh upgrade to head;
- upgrade from verified `0003` baseline;
- realistically populated baseline upgrade;
- deployment Principal provisioning;
- ownership backfill and row-count reconciliation;
- fail-closed absent or ambiguous Principal behavior;
- owner constraints and orphan checks;
- reader-before-writer rollout and mixed formats;
- permitted downgrade and re-upgrade;
- compatible application rollback after new writes;
- null and known-zero preservation;
- Snapshot v1 preservation;
- no historical Target Plan fabrication;
- Alembic ledger consistency;
- model-versus-migration drift detection;
- proof runtime startup does not invoke `create_all`;
- full Backend and Frontend regression gates.

Exact CI implementation and commands require Engineering/Data and QA approval.

## 11. Deferred And Prohibited Scope

This direction does not create migration revisions, approve final physical schema, remove legacy fields or the Snapshot v1 reader, enable new-format writers, introduce automatic runtime migrations or a second schema authority, add deferred product features, or authorize product implementation.

## 12. Status

```text
Artifact ID: ADR-DIR-H09
Selected direction: Alembic runtime authority with isolated unit-test create_all
Runtime create_all: Prohibited
Automatic runtime migration: Prohibited
Integration database setup: Alembic on disposable PostgreSQL
Existing revisions 0001 through 0003: Immutable
Principal provisioning: Explicit and fail-closed
Ownership backfill: Verified before constraint enforcement
Reader-before-writer rollout: Required
Production rollback after new-format writes: Compatible application rollback
Lossy schema downgrade: Prohibited
Legacy removal during Wave 1: Prohibited
Architecture/migration blocker: Resolved
Physical schema, revision design, implementation, and verification: Still open
H09 overall status: Open
```

H09 remains open until the physical schema and revision design are approved and pinned, implementation completes, all migration and rollback evidence passes on disposable PostgreSQL, and final traceability and readiness gates close.
