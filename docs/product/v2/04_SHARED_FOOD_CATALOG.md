# V2 Shared Food Catalog

## Ownership Delta

Food visibility is no longer Principal-scoped. Existing `food.principal_id`
becomes `created_by_principal_id`; it is audit provenance, not an authorization
scope. `updated_by_principal_id`, lifecycle status, archive metadata, and a
global duplicate key are added.

Contribution and trait ownership columns become audit provenance. Their data is
loaded by Food ID. Diary keeps its private Principal ownership, while `food_id`
references the global Food ID without a composite owner relationship.

## Lifecycle

- Active Foods appear in normal catalog/search/filter results.
- Archived Foods remain resolvable for historical data and admin views.
- Admin may restore an archived Food.
- Unused Foods may be hard-deleted after confirmation.
- Foods referenced by Diary history are archived instead of deleted.
- Food edits and lifecycle changes never rewrite Diary snapshots.

## Duplicate Protection

Duplicate identity is global. A deterministic persisted duplicate key plus a
unique database constraint protects concurrent writes. Existing normalization
rules remain unless V2 explicitly removes the legacy category from duplicate
identity (it was already non-identifying).

