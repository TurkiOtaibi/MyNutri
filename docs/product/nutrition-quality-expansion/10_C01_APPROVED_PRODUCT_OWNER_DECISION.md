# C01 Approved Product Owner Decision

## 1. Decision Record

| Item | Value |
|---|---|
| Artifact ID | `DEC-C01-10` |
| Issue | `C01 - Authenticated ownership cannot be safely migrated` |
| Decision status | Approved by Product Owner |
| Selected option | Deployment-Provisioned Durable Principal |
| Audited implementation HEAD | `255b8339e66e7dd6da0cb48ad7d93c2f0243e66f` |
| Governing decisions | `PD-023`, `PD-024`, `PD-025`, `PD-029` |
| Product model | Personal single-principal |
| Profile rule | One Profile per Principal |
| Decision date | 2026-07-15 |

This record is an approved product decision for C01. It does not modify the frozen v1.1 register and does not constitute approval of the physical schema, API contract, migration, implementation, or verification evidence.

## 2. Approved Direction

### Principal and product model

- myNutri v1 remains a personal single-principal product.
- The Backend uses a durable local Principal with a stable internal identifier.
- One Profile is allowed per Principal.
- The current deployment explicitly provisions one durable Principal.

### Credential separation and authentication

- The Principal identifier is independent from bearer tokens and other credentials.
- Token rotation must not change or transfer ownership.
- The Backend derives the Principal from the authenticated request.
- Missing or invalid production authentication configuration must fail closed.
- Future identity providers may map to the existing stable local Principal without changing record ownership.

### Frontend and ownership authority

- The frontend never sends an authoritative `principal_id`, `owner_id`, or `user_id`.
- All current and future user-created records are Principal-bound.
- All list, read, update, delete, aggregation, uniqueness, and duplicate behavior is Principal-scoped.
- Unauthorized and nonexistent identifiers use the same non-enumerating outward response.
- Normal product operations do not use Service Role.

### Legacy-data migration

Existing Profile, Food, and Diary Entry records are assigned to one explicitly confirmed deployment Principal using:

```text
Expand -> Migrate -> Contract
```

The migration must stop if the deployment Principal cannot be established explicitly.

The migration must not:

- infer ownership from record content;
- rewrite historical nutrition snapshots;
- invent historical Target Plans;
- change nutrient values;
- convert unknown nutrition values to zero.

### Required security verification

- Tests use at least two Principals to prove isolation, even though the released product remains single-principal.
- Token rotation preserves the same Principal and ownership.
- Cross-Principal list/read/update/delete/aggregation/uniqueness behavior is denied and does not leak record existence.
- Missing or invalid production authentication configuration fails closed.

## 3. Explicitly Deferred Scope

This decision does not introduce:

- public registration;
- account-management UI;
- profile switching;
- multiple Profiles per Principal;
- public or shared Foods;
- multi-user product UX;
- external identity-provider integration.

The internal ability to test more than one Principal is a security-verification requirement, not a released multi-user feature.

## 4. Decision Effect On C01

| C01 resolution component | State after this decision |
|---|---|
| Product Decision Required | Resolved |
| Architecture Decision Required | Open |
| Data Contract Required | Open |
| API Contract Required | Open |
| Migration Design Required | Open |
| User Stories / Acceptance Criteria Required | Open |
| Implementation Required | Open |
| Test / Verification Required | Open |
| Documentation Reconciliation Required | Open |

**C01 remains Critical and open.** Only its Product Owner decision is closed. Wave 1 implementation must not begin until the remaining pre-implementation C01 contracts and designs are approved and the formal readiness gate is rerun.

## 5. Required Next Artifacts

1. Architecture/Security ADR for the durable Principal, provisioning, request context, credential rotation, and fail-closed behavior.
2. Exact owner-scoped physical schema and constraints.
3. Additive API/authentication contract with non-enumerating errors.
4. Expand-Migrate-Contract and rollback design for existing records.
5. User stories and acceptance criteria for ownership and authorization behavior.
6. Two-Principal security, migration, compatibility, and regression verification plan.

No product implementation is authorized by this decision record alone.
