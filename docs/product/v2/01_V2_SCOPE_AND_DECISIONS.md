# myNutri V2 Scope and Decisions

Status: Implementation authority
Release: V2 multi-user, shared Food catalog, simplified Food model

## Objective

V2 uses Supabase email/password accounts, durable Principal ownership, `user`
and `admin` roles, read-only admin monitoring, and a global admin-managed Food
catalog. Food taxonomy and provenance are intentionally small and stable.

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
- Food nutrition is current authoritative truth. Every Diary calculation joins
  through `food_id` to the current Food nutrition.
- A Diary entry stores the historical consumed quantity and captured measurement
  basis. Later Food serving-default edits cannot change what was consumed.
- Food snapshots and snapshot version machinery are absent.
- Archived Foods remain resolvable by Diary history. Referenced Foods cannot be
  hard-deleted; the foreign key uses `RESTRICT`.
- Target Plans remain immutable, effective-dated historical truth. A later plan
  does not rewrite the target bound to an earlier Diary date.
- Required core nutrients remain calories, protein, carbohydrates, and fat.
  Optional nutrients remain nullable; unknown never means zero.
- `normalized_name` remains system-generated and is not user-editable.

## Preserved behavior

Authentication, authorization, private Principal isolation, Target Plan
versioning, Arabic-first RTL behavior, responsive behavior, accessibility, PWA
isolation, audit principals, archival timestamps, measurement/serving fields,
notes, and nutrient representation fields remain active unless another approved
decision says otherwise.

## Retired concepts

NOVA, Pattern Analysis, Weekly Priority, Food Group Contributions, Food
Analytical Traits, and Food nutrition snapshots are retired product history.
Historical Alembic revisions that introduced them remain immutable technical
history so clean and supported databases can reproduce the migration chain.

## Deferred

Organizations, extra roles, private user Foods, social features, payments,
clinical modes, AI/OCR/barcodes, and production cleanup are outside this change.
