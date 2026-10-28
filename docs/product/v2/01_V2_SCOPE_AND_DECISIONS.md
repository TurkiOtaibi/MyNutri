# myNutri V2 Scope and Decisions

## State boundary for authentication

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility, not an authentication path; #114 clears them only on selected legacy-user tombstones. New users are created atomically by immutable username. The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043).

The CURRENT implementation allows only Admin correction of another user's «الجنس» in issue #109; all other private-data monitoring remains read-only. The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. (17 October 2026 PRF/USM/AUT/FOD decisions; BR-PRF-006, BR-USM-027/032/043/061/067/074; issue #100; [V2 06](06_DATA_MIGRATION_AND_CUTOVER.md).)


Status: Implementation authority
Release: V2 multi-user, shared Food catalog, simplified Food model, standalone Labs

The Admin-managed account lifecycle below is approved Product authority implemented
in the lifecycle revision; Production activation remains a separate release action.

## Objective

V2 supports internal username/password authentication and opaque bearer sessions (#113; BR-AUT-001/017), durable Principal ownership, `user`
and `admin` roles, read-only admin monitoring, and a global admin-managed Food
catalog. Food taxonomy and provenance are intentionally small and stable.
Standalone Labs lets adults record private numeric laboratory facts and follow
their history using current system reference rules. Labs has no effect on Food,
Diary, Target Plans, nutrition calculations, recommendations or Progress.

## Authoritative decisions

- `Principal.id` is the durable private-resource ownership key.
- Exactly one Admin is permitted. Only the bootstrap tool establishes that Admin;
  a database partial unique index on `role='admin'` prevents a second one, and
  bootstrap refuses when an Admin already exists. No product API grants or
  changes the Admin role. The Admin cannot change their own role, disable
  themselves, or delete themselves.
- Accounts are Admin-created only. Self-registration and automatic Principal
  provisioning for unknown identities are retired. Unknown and
  non-active identities receive `401 INVALID_CREDENTIAL`; existing Principals
  are preserved. Admin account management is separate from read-only monitoring
  of another user's Profile, Diary, Target Plans, and Labs.
- An Admin creates a normal user with immutable username, display name, and an initial
  Admin-set password (#112; BR-USM-022/023/025/036). They may edit display name, reset password (revoking the
  user's internal sessions; legacy-only targets cannot reset without internal credentials), enable or disable the
  user, and request permanent deletion. Email changes are out of scope.
  Raw passwords are never stored, logged, or returned; internal accounts store only a scrypt hash (#110; 27 October 2026; BR-AUT-001/017, BR-USM-030/033).
- Creation commits an active Principal, immutable normalized username, password hash,
  initial-change flag and idempotency key atomically. No external identity is created.
- Deletion commits `deleting` under the Principal lock, then purges private data and
  sessions and scrubs the durable tombstone locally. Failed local deletion remains
  locked out and retryable. Historical `provisioning` accounts may be deleted without
  an external lease or absence check. No reconciliation or external lifecycle remains.
- Global Foods survive deletion. Their creator/updater attribution retains the
  scrubbed Principal tombstone. The UI does not display Food creator or updater
  attribution (including any deleted-user label) to any role, per BR-FOD-021
  and the Product Owner decision of 17 October 2026, reconfirmed on 25 October 2026.
  No Food history is rewritten. Every Principal-owned-data writer rechecks
  `active` under the Principal lock so nothing private can be written after purge;
  the sex-only Admin correction permits active/disabled targets only (BR-USM-032; #109).
- Foods form a global catalog; Food mutation requires `admin`.
- Food taxonomy has exactly `primary_category` and `subcategory`.
- Food nutrition provenance is only `nutrition_data_source`, with `official`
  and `estimated` as its allowed values.
- Ingredient text is stored in `ingredients`; ingredient provenance is absent.
- Food status, Food kind, group completeness, NOVA, Food Groups, and Food
  Analytical Traits are absent.
- Pattern Analysis and Weekly Priority are absent and have no replacement.
- Day Logging Status is absent. Diary days have no complete/reopen commands,
  persisted completion state, day version, status history, or status-command
  idempotency.
- Diary entry create, update, and delete do not require `If-Match`, do not depend
  on a day state machine. New Diary entries allow past dates without limit and
  future dates through Asia/Riyadh today + 7 days, per BR-DRY-028 and the Product
  Owner decision of 17 October 2026, reconfirmed on 25 October 2026. Existing
  entries retain their update, delete, and replay rules.
- Diary day and week views derive from Diary entries and target/nutrition data;
  they expose no day-status or entry-presence badge contract.
- Food nutrition is current authoritative truth. Every Diary calculation joins
  through `food_id` to the current Food nutrition.
- A Diary entry stores the historical consumed quantity and captured measurement
  basis. Later Food serving-default edits cannot change what was consumed.
- Food snapshots and snapshot version machinery are absent.
- Food Archive is retired. Admin deletion permanently removes the Food and all
  referencing Diary entries across all Principals through the database cascade.
  Target Plans remain unchanged.
- Target Plans have no lifecycle status or semantic Nutrition version columns.
  They are immutable revisions selected by date: the canonical revision at the
  greatest `effective_from` not later than the requested date. Writes are
  limited to Riyadh today or the future.
- Past Diary Target Plan bindings remain immutable. Today/future bindings are
  recomputed when a new canonical plan changes their effective interval. A
  nullable `target_plan_id` is the complete binding state; Diary target
  provenance is not persisted or exposed.
- Target resolution returns the canonical dated Target Plan or null. Profile
  inputs and retired transition snapshots never substitute for a Target Plan.
- The Nutrition Registry and direct manifest/preview integrity hashes remain;
  semantic engine, Registry, and calculation-document version numbers are absent.
- Required core nutrients remain calories, protein, carbohydrates, and fat.
  Optional nutrients remain nullable; unknown never means zero.
- `normalized_name` remains system-generated and is not user-editable.

## Preserved behavior

Labs uses the existing top navigation without removing a destination. Its six
views are owner overview, batch add, detail/history, edit, admin-selected overview,
and admin-selected detail. Arabic/RTL, keyboard/focus, responsive layouts and
session isolation are acceptance requirements; runtime evidence lives in tests
and CI, not in this authority document.

## Labs decisions

- The immutable packaged catalog has exactly 51 tests, 15 categories and 7 panels.
  Panels select tests only; they are not stored entities. Numeric rules and exact
  membership belong to `backend/app/labs/catalog.v1.json`.
- `LabResult` entered value/unit/test/date are authoritative. Status, reference
  zones and canonical values are derived from the current catalog on every fresh
  read; rule changes reinterpret history without rewriting entered facts.
- Complete Profile supplies sex and DOB. Labs requires complete Gregorian age
  at least 18 on each test date, with the existing leap-day behavior. Profile's
  nutrition age 10–100 rule remains separate. There is no pregnancy input.
- Owners cannot change sex after the first successful Profile save; Admin correction
  is the sole exception (17 October 2026; BR-PRF-006, BR-USM-032/061; #109). A DOB change cannot
  make any stored result pre-adult. An accepted DOB change reinterprets history.
- Users own CRUD; admins read own/selected-user Labs and cannot mutate Labs,
  including their own. Owner/test/date is unique. Batch create and its durable
  idempotency receipt commit atomically under the shared Principal lock.
- Input is explicit finite nonnegative decimal text and an approved unit. Exact
  rational conversion/classification precedes display rounding. The 128-character
  normalized storage limit is technical, not a medical maximum.
- Labs is online-only and volatile in the browser: no polling, personal persistence,
  service-worker API cache, offline queue, sharing/export, editable catalog, custom
  tests/units/ranges/panels, automatic biomarkers, diagnosis, treatment targets or
  emergency workflow. Lipids and Iron Studies assume fasting without collecting
  a fasting field. The UI calls references `القيم المرجعية للنظام`.

## Preserved nutrition and application behavior

Authentication, authorization, private Principal isolation, Target Plan
revision history, legacy Target Plan API idempotency replay, Arabic-first RTL behavior,
responsive behavior, accessibility, static-shell PWA isolation, Principal/Food
creation and update attribution, measurement/serving fields, notes, and nutrient
representation fields remain active unless another approved decision says otherwise.

## Retired concepts

NOVA, Day Logging Status, the Target Plan lifecycle state machine, semantic
Nutrition versioning, legacy Target data compatibility, Pattern Analysis,
Weekly Priority, Food Group Contributions, Food Analytical Traits, and Food
nutrition snapshots are retired product history.
Historical Alembic revisions that introduced them remain immutable technical
history so clean and supported databases can reproduce the migration chain.

## Deferred

Organizations, extra roles, private user Foods, social features, payments,
clinical modes, AI/OCR/barcodes, and production cleanup are outside this change.
