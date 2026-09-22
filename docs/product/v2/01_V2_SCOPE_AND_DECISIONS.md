# myNutri V2 Scope and Decisions

Status: Implementation authority
Release: V2 multi-user, shared Food catalog, simplified Food model, standalone Labs

## Objective

V2 uses Supabase email/password accounts, durable Principal ownership, `user`
and `admin` roles, read-only admin monitoring, and a global admin-managed Food
catalog. Food taxonomy and provenance are intentionally small and stable.
Standalone Labs lets adults record private numeric laboratory facts and follow
their history using current system reference rules. Labs has no effect on Food,
Diary, Target Plans, nutrition calculations, recommendations or Progress.

## Authoritative decisions

- `Principal.id` is the durable private-resource ownership key.
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
  on a day state machine, and permit past, current, and future Diary dates.
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
- Sex is immutable after the first successful Profile save. A DOB change cannot
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
