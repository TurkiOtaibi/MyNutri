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

The reviewed mapping file must be retained as release evidence. Do not apply a
mapping while any row has an unresolved `resolution`.

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
