# myNutri V2 Scope and Decisions

Status: Implementation authority
Release: V2 multi-user and shared catalog
Supersedes: V1 single-user/shared-token assumptions for V2 runtime only

## Objective

V2 introduces Supabase email/password accounts, `user` and `admin` roles, strict
Principal isolation, read-only admin monitoring, a global admin-managed Food
catalog, Food Taxonomy V2, and a simplified advanced-analysis experience.

The frozen Wave 1 documents remain historical evidence. V2 does not rewrite
Target Plans, Diary Snapshot v1/v2, nutrition calculations, or historical data.

## Decisions

- `Principal.id` remains the durable ownership key.
- Supabase `auth.users.id` maps one-to-one to `Principal.auth_user_id`.
- New accounts are provisioned as `user`; clients cannot assign roles.
- Only a trusted bootstrap operation may assign `admin`.
- Private resources remain Principal-scoped.
- Admin monitoring uses dedicated read-only services and routes.
- Foods become a global catalog; mutations require `admin`.
- Existing Food IDs and historical Diary snapshots remain unchanged.
- Food category metadata moves to Taxonomy V2 and Registry schema 2.
- V1 category values embedded in historical snapshots remain readable.
- Production uses Supabase JWT verification and has no browser shared token.

## Preserved Behavior

Profile calculations, immutable Target Plans, transition snapshots, Diary
entries, Snapshot readers, nullable nutrition semantics, Registry nutrient
targets, Arabic RTL, responsive behavior, accessibility, and PWA behavior are
preserved unless explicitly changed by the V2 scope.

## Deferred

Organizations, extra roles, account management beyond the required auth flows,
admin mutation of another user's private data, private user Foods, social
features, payments, clinical modes, AI/OCR/barcodes, and later-wave analysis are
out of scope.
