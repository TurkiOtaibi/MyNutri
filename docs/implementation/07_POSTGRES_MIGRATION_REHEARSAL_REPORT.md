# PostgreSQL Migration Rehearsal Report

Status: Completed
Date: 2026-07-10
Scope: Foods v1 PostgreSQL migration rehearsal and smoke checks against local/dev PostgreSQL.
Application code changed: No.
BA files changed: No.
QA files changed: No.
Committed: No.

## 1. PostgreSQL Installation Result

PostgreSQL is installed locally and the service is running.

Environment verification:

- Operating system: Windows 10 (`Microsoft Windows NT 10.0.19045.0`).
- PostgreSQL service: `postgresql-x64-16`, status `Running`.
- `psql` found at: `C:\Program Files\PostgreSQL\16\bin\psql.exe`.
- PostgreSQL version verified:

```text
PostgreSQL 16.14, compiled by Visual C++ build 1944, 64-bit
```

Docker was not used.

## 2. PostgreSQL Connection Result

Connection result: Passed.

Connection verified with `psql`:

```powershell
$env:PGPASSWORD='<local-dev-password>'
psql -h localhost -U postgres -d postgres -c "SELECT version();"
```

Database verified:

```text
current_database: mynutri_dev
current_user: postgres
```

The database exists and is local/dev only.

## 3. Database Used

Database used: `mynutri_dev`

Connection used for backend/Alembic commands:

```text
postgresql+psycopg://postgres:<local-dev-password>@localhost:5432/mynutri_dev
```

Notes:

- The user-provided local development database was used.
- The password was used only through the current shell environment and is intentionally masked in this report.
- No production database was used.
- No database credentials were written to committed configuration files.

Initial state:

- `mynutri_dev` existed.
- The database had no public tables before the first Alembic upgrade.
- No `alembic_version` table existed before migration.

## 4. Migration Command Run

Initial upgrade command:

```powershell
$env:DATABASE_URL='postgresql+psycopg://postgres:<local-dev-password>@localhost:5432/mynutri_dev'
cd backend
python -m alembic upgrade head
```

Result:

```text
Running upgrade  -> 0001_initial, initial schema
Running upgrade 0001_initial -> 0002_foods_v1_per_basis, foods v1 per-basis schema
```

Result status: Passed.

Legacy-row conversion rehearsal:

1. Downgraded the empty migrated DB to `0001_initial`.
2. Inserted representative legacy Food rows:
   - One old row with `serving_grams = 50`.
   - One old row with `serving_grams = NULL`.
3. Upgraded back to head.

Commands:

```powershell
python -m alembic downgrade 0001
python -m alembic upgrade head
```

Result status: Passed.

Final Alembic version:

```text
0002_foods_v1_per_basis
```

## 5. Migration Result

Live PostgreSQL migration result: Passed.

The Foods v1 migration applied successfully on PostgreSQL 16.

Verified:

- `0001_initial` applied successfully.
- `0002_foods_v1_per_basis` applied successfully.
- PostgreSQL enum types were created successfully.
- Food table migration completed successfully.
- Legacy columns were dropped from the Food catalog table.
- Alembic version is now `0002_foods_v1_per_basis`.

## 6. Schema Verification Result

Schema verification result: Passed.

Verified Food columns after migration:

```text
id
name
calories
protein_g
carb_g
fat_g
saturated_fat_g
trans_fat_g
cholesterol_mg
sodium_mg
fiber_g
added_sugar_g
created_at
updated_at
brand
category
nutrition_basis
default_unit_type
unit_amount
unit_basis
sugar_g
potassium_mg
calcium_mg
iron_mg
magnesium_mg
zinc_mg
vitamin_d_mcg
vitamin_b12_mcg
vitamin_c_mg
vitamin_a_mcg
folate_mcg
vitamin_k_mcg
notes
data_source
```

Verified absent Food columns:

- `is_active`
- `archived_at`
- `serving_label`
- `serving_grams`
- `total_sugars_g`

Result:

- No Food archive/inactive schema was introduced.
- No Active/Archived schema support exists.
- Removed legacy Food catalog columns are not required by current Food code.
- Legacy snapshot fields remain only in Diary snapshot compatibility code, not in the Food catalog schema.

## 7. Old-Row / Default Migration Behavior

Old-row migration behavior: Passed.

Representative migrated row with `serving_grams = 50`:

```text
name: Legacy 50g Food
nutrition_basis: per_100g
default_unit_type: serving
unit_amount: 50.00
unit_basis: g
calories: 200.00
protein_g: 20.00
carb_g: 40.00
fat_g: 10.00
sugar_g: 12.00
fiber_g: 6.00
added_sugar_g: 2.00
```

Expected behavior:

- Original per-serving values were multiplied by `100 / serving_grams`.
- `total_sugars_g` was copied and converted into `sugar_g`.
- `unit_amount` preserved the old `serving_grams` value for default-unit convenience.

Representative migrated row with `serving_grams = NULL`:

```text
name: Legacy Unknown Serving
nutrition_basis: per_100g
default_unit_type: serving
unit_amount: 100.00
unit_basis: g
calories: 80.00
protein_g: 2.00
carb_g: 15.00
fat_g: 1.00
sugar_g: 4.00
```

Expected behavior:

- Row defaulted to `per_100g`.
- `unit_amount` defaulted to `100`.
- Nutrition values remained best-effort as already stored.

Remaining note:

- Existing real Food rows without reliable `serving_grams` still need manual data review after migration because the fallback cannot infer the true historical serving weight.
- The representative legacy rehearsal rows were removed after verification so the local dev database is clean for Manual QA.

## 8. Food API Smoke-Check Results

Food API smoke checks against migrated PostgreSQL: Passed.

Smoke checks run through FastAPI `TestClient` using the PostgreSQL-backed app configuration.

Passed checks:

- Create valid Food.
- Reject duplicate Food using normalized duplicate key.
- Reject invalid optional nutrient value (`vitamin_d_mcg > 250`).
- Get Food details.
- Update Food.
- Search Food by name.
- Delete Food permanently.
- Confirm deleted Food is no longer listed.

Smoke artifacts:

- Smoke Food rows were cleaned up after the run.
- Final check: `Smoke PG%` Food rows = `0`.
- Final check after all rehearsal cleanup: total `food` rows = `0`.

## 9. Diary Snapshot Safety Result

Diary snapshot PostgreSQL smoke check: Passed.

Smoke flow:

1. Created a Food in PostgreSQL.
2. Created a Diary entry from that Food.
3. Permanently deleted the Food.
4. Read the historical Diary entry.
5. Verified historical display and totals still came from `nutrition_snapshot`.
6. Cleaned up the smoke Diary entry.

Verified result:

- Historical Diary entry remained readable after Food hard delete.
- Snapshot retained the Food name.
- Snapshot totals remained accurate.
- Final check: smoke Diary entries = `0`.
- Final check after all rehearsal cleanup: total `diary_entry` rows = `0`.

## 10. Test Results

Backend tests run with the local PostgreSQL `DATABASE_URL` set:

```powershell
python -m pytest
```

Result:

```text
18 passed, 1 skipped, 1 warning
```

Skipped test:

- `backend/tests/test_sync.py` is skipped as Future Scope.

Warning:

- Upstream `StarletteDeprecationWarning` from `fastapi.testclient` / `httpx`; not related to Foods migration behavior.

Ruff run:

```powershell
python -m ruff check
```

Result:

```text
All checks passed.
```

Frontend checks were not rerun because this task changed no application code and focused on PostgreSQL migration/API rehearsal.

## 11. Remaining Risks

| Risk | Severity | Impact | Recommendation |
|---|---:|---|---|
| Real existing Food rows without reliable `serving_grams` may need review. | Medium | Their migrated nutrition values may be best-effort rather than semantically correct. | Spot-check real migrated Food rows before release. |
| Duplicate blocking remains service-level only. | Low to Medium | Concurrent duplicate creates could theoretically race. | Accept for personal-use v1 or add a database-level normalized key later. |
| Manual browser QA is still required. | Medium | Backend/API rehearsal does not prove mobile RTL rendering, dialogs, and accessibility behavior. | Run Foods manual QA using the regenerated test cases. |

## 12. Manual QA Start Recommendation

Manual QA status: Ready to start.

Rationale:

- PostgreSQL migration applied successfully.
- Foods v1 schema verified.
- Legacy-row migration behavior verified.
- Food API smoke checks passed against PostgreSQL.
- Diary snapshot safety passed against PostgreSQL.
- Backend tests passed.
- No archive/inactive fields exist.
- No offline/sync behavior was reintroduced by this task.

## 13. Commit Recommendation

Commit recommendation: A checkpoint commit can be made after reviewing the working tree.

Do not label the project release-ready until:

1. Foods manual QA is completed.
2. Mobile RTL and accessibility behavior are manually verified.
3. Any manual QA findings are resolved or accepted.

This rehearsal itself made no application-code changes.
