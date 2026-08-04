# V2 Data Migration and Cutover

## Sequence

1. Back up and rehearse against a disposable clone.
2. Upgrade readers and schema with additive Principal/Auth and catalog fields.
3. Run identity and taxonomy preflight in dry-run mode.
4. Create or identify the Supabase Auth identity for the existing Principal.
5. Link the identity and bootstrap the existing Principal as admin.
6. Apply reviewed taxonomy mappings.
7. Verify ownership counts, Food IDs, Diary links, snapshots, and constraints.
8. Deploy Backend with Supabase JWT auth.
9. Deploy Frontend without `NEXT_PUBLIC_API_TOKEN`.
10. Run smoke and isolation checks before opening access.

## Safety

- No Principal ID, Food ID, Diary ID, Target Plan, or snapshot is rewritten.
- Auth linkage is explicit and idempotent.
- Ambiguous taxonomy rows remain review-required.
- Migration refuses duplicate global Food identities until reviewed.
- Downgrade is prohibited after V2-only identity/catalog data exists when it
  would lose role, linkage, archive, or taxonomy information.

## Environment Delta

Add Backend: `SUPABASE_URL`, `SUPABASE_JWT_AUDIENCE`, and optional explicit
`SUPABASE_JWKS_URL`. Bootstrap only: `SUPABASE_SERVICE_ROLE_KEY`.

Add Frontend: `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or compatible anon key).

Remove from final V2: `SINGLE_USER_TOKEN`, `PREVIOUS_SINGLE_USER_TOKENS`,
`DEPLOYMENT_PRINCIPAL_ID`, `PRINCIPAL_TOKEN_MAP`, and `NEXT_PUBLIC_API_TOKEN`.

## Preflight and Reviewed Taxonomy Commands

Run these commands only against the explicitly selected deployment database.
The first taxonomy command is read-only and writes a local review file.

```powershell
cd backend
alembic current
alembic upgrade head
python -m app.db.preflight
python -m app.ops.reclassify_food_taxonomy --output food-taxonomy-v2-review.json
python -m app.ops.reclassify_food_taxonomy --mapping reviewed-food-taxonomy-v2.json --apply
```

The `--output` command is read-only at the database level. It serializes the
complete JSON document before publishing it through a same-directory temporary
file and atomic no-clobber final-path creation. It never overwrites an existing
export: choose a new path, or deliberately archive or remove an obsolete export
before rerunning the command. An interrupted export cannot leave a valid-looking
partial final file, and temporary artifacts are removed on failure. The JSON
list's top-level category/detail fields are immutable review context, not an
approval or a fallback resolution. Copy the output file, review every row, and
replace each `null` `resolution` with one explicit object in this exact closed
shape:

The output parent directory must already exist. A regular file, directory, or
symbolic link already present at the destination is treated as an existing
export and is never replaced or followed.

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000022",
    "name": "Example reviewed food",
    "food_category_key": "grains_starches",
    "grain_type": "whole",
    "baked_good_type": null,
    "grain_starch_type": "other",
    "taxonomy_review_required": true,
    "legacy_category": "legacy",
    "legacy_primary_category_key": "whole_grains",
    "resolution": {
      "food_category_key": "fruits",
      "grain_type": null,
      "baked_good_type": null,
      "grain_starch_type": null
    },
    "reason": "ambiguous_requires_human_review"
  }
]
```

The file root must be a list. Food IDs must be valid and unique. Neither a row
nor its `resolution` may contain unknown keys. All four resolution fields are
required; `food_category_key` is a registered string and each detail field is
either a registered string or `null`. A missing, `null`, scalar, or partial
resolution is unresolved. The apply command never infers approval from the
Food name, free text, or generated top-level suggestion.

Every `id` must be a quoted JSON string containing a valid UUID. An unquoted
numeric ID is invalid even when its digits could be interpreted as a UUID, and
fails before database SQL or commit; the tool never converts numbers to
strings. Malformed UUID strings remain invalid. Operators must not remove the
quotation marks around IDs or rely on ID coercion or inference when editing the
reviewed artifact.

The reviewed mapping root must contain at least one row, and every row must
contain one complete explicit `resolution` object. An empty JSON list is
invalid: the apply command fails before database SQL or commit and never
reports the artifact as successfully applied. A zero-row apply is not a dry
run. The read-only export may legitimately contain rows whose `resolution` is
`null`; such an exported file is not directly applyable until an operator has
reviewed it and populated at least one complete resolution. If no Foods require
review and the export is empty, no apply operation is needed. Do not create an
empty reviewed artifact merely to produce a successful command result.

Before any write, the apply command validates the complete JSON schema,
registered vocabulary, and category/detail compatibility. It then locks every
requested Food in sorted UUID order and compares the current name, taxonomy,
review-required flag, and migration-audit context with the generated context.
A missing, duplicate, already-reviewed, or changed Food makes the whole file
stale. Only after every row passes does one transaction update values from the
explicit `resolution`, clear `taxonomy_review_required`, and commit once. Any
error rolls back the complete batch; per-row partial success is prohibited.
Two operators cannot avoid this freshness check by reversing Food order:
overlapping batches acquire Food locks in the same sorted UUID order. One
complete batch may commit while the other is rejected as stale; changes are
never merged across batches. A failed apply commits zero changes. After the
cause is corrected, a clean retry may commit once, but replaying the old review
context after a successful resolution is rejected as stale. Never edit the
expected context merely to bypass freshness protection; generate a new export
and review the current state instead. The command does not retry deadlocks,
invent taxonomy decisions, or permit partial success.

Retain the original output, reviewed input, sanitized applied Food IDs/count,
and rehearsal result as release evidence. Never retain credentials or private
database output in this evidence. Rehearse only on a disposable clone:

```powershell
cd backend
$env:DATABASE_URL = "<disposable-clone-url>"
python -m app.ops.reclassify_food_taxonomy --output food-taxonomy-v2-review.json
# Review every row and populate every resolution object before continuing.
python -m app.ops.reclassify_food_taxonomy --mapping reviewed-food-taxonomy-v2.json --apply
Remove-Item Env:DATABASE_URL
```

Do not run `--apply` against shared or production data until the reviewed file
and disposable rehearsal evidence have completed the release approval process.

## Existing Principal Admin Link

Validate first without changing Supabase Auth or PostgreSQL:

```powershell
cd backend
python -m app.ops.bootstrap_admin --principal-id <existing-principal-uuid> --email <admin-email> --display-name <display-name> --auth-user-id <supabase-auth-user-uuid> --dry-run
```

After the Auth user ID and dry-run output are reviewed, rerun without
`--dry-run`. Alternatively, `--create-auth-user` requires
`SUPABASE_SERVICE_ROLE_KEY` and `ADMIN_BOOTSTRAP_PASSWORD`; those values are
process-only secrets and must be removed from the shell immediately afterward.
The bootstrap operation validates `SUPABASE_URL` before constructing the
credential-bearing request and requires HTTPS by default.

For a local Supabase Auth emulator only, HTTP can be enabled explicitly:

```powershell
python -m app.ops.bootstrap_admin --principal-id <existing-principal-uuid> --email <admin-email> --display-name <display-name> --create-auth-user --allow-loopback-auth-emulator
```

The loopback exception accepts only literal `localhost`, `127.0.0.1`, or `::1`
hosts. It is prohibited in production and must never target shared or
production infrastructure. Service Role credentials and the bootstrap password
remain process-only secrets even when the local emulator exception is used.
