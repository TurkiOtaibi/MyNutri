# Wave 1 Data, API, And Migration Delta

Audit date: 2026-07-14

## 1. Executive Result

The current database can support the approved Nutrition Quality Wave 1 without a new database migration.

The required work is:

- stabilize/version the already-applied `0002` and `0003` migrations,
- centralize nutrient definition metadata,
- correct frontend unknown-value aggregation,
- preserve the additive Profile target contract,
- add missing verification.

No nutrient target values should be persisted, and no unknown nutrient should be backfilled to zero.

## 2. Current Data Model

### 2.1 Profile

Current persisted fields already support:

- sex-aware defaults at validation/UI level,
- custom `protein_per_kg`,
- custom `fat_pct`,
- server-derived calorie and macro targets.

No target columns exist or are needed. Existing profiles retain saved values.

### 2.2 Food

The current Food table has all six Wave 1 nutrient fields as nullable numeric columns:

| Wave 1 nutrient | Existing field | Null semantics |
|---|---|---|
| Fiber | `fiber_g` | unknown when null |
| Sodium | `sodium_mg` | unknown when null |
| Saturated fat | `saturated_fat_g` | unknown when null |
| Added sugar | `added_sugar_g` | unknown when null |
| Potassium | `potassium_mg` | unknown when null |
| Cholesterol | `cholesterol_mg` | unknown when null |

The Food model also contains other optional nutrients. Wave 1 tracking is limited to the approved six-item registry; those additional stored fields do not automatically acquire targets.

### 2.3 Diary

`nutrition_snapshot` is JSONB and already stores all optional Food nutrient values. The response schema defaults absent legacy keys to `null`.

Required semantics already supported:

- numeric zero is known,
- `null`/missing is unknown,
- known values scale with quantity,
- unknown values remain unknown,
- meal moves do not recreate the snapshot,
- Food edit/delete does not mutate history.

## 3. Current Versus Committed Schema Delta

The current local PostgreSQL schema is ahead of `HEAD`.

| Area | `HEAD` | Current worktree/database |
|---|---|---|
| Food source | Per serving | Per 100g/per 100ml plus default unit |
| Optional nutrients | Initial subset | Full D-026 field set |
| Food identity metadata | Limited | Brand/category/notes/data source |
| Diary meal grouping | None | `meal_type` enum and column |
| Snapshot | Serving-era shape | Backward-compatible per-basis/default-unit shape with nullable nutrients |
| Profile defaults | Protein 1.8, fat 0.25 | Protein 1.2; sex-aware fat default in schema/UI |

This is baseline debt, not a reason to add another Wave 1 migration.

## 4. Existing Migration Delta

### 4.1 `0002_foods_v1_per_basis`

Current status: staged, uncommitted, applied locally.

It:

- adds per-basis/default-unit enums and fields,
- adds optional nutrient and metadata columns,
- converts legacy per-serving values to per-100 values when `serving_grams` is valid,
- maps `total_sugars_g` to `sugar_g`,
- removes legacy Food source columns.

### 4.2 `0003_diary_meal_type`

Current status: untracked, applied locally.

It:

- creates `meal_type_enum`,
- adds non-null `meal_type`,
- safely defaults existing entries to `unspecified`,
- removes the default after backfill.

### 4.3 Wave 1 migration decision

**Exact migration delta: none.**

Do not create `0004` for:

- nutrient targets,
- completeness,
- coverage,
- Profile default changes,
- additional snapshot nutrient keys.

Those are derived metadata/UI behaviors or are already supported by nullable columns/JSONB.

### 4.4 Required migration verification

Before sign-off, run on a disposable local PostgreSQL database:

1. Upgrade from `0001` to `head`.
2. Verify old Food conversion and nullable unknown preservation.
3. Verify old Diary entries become `unspecified` without snapshot mutation.
4. Downgrade `0003` to `0002`.
5. Upgrade again to `0003`.
6. Run backend Foods/Diary/snapshot tests against the migrated schema where supported.

Do not reset the existing `mynutri_dev` database merely for this rehearsal; it contains local development data.

## 5. Current API Delta Already Implemented

### 5.1 Profile preview

`POST /profile/preview` is an additive, non-persisting endpoint. It validates through `ProfileUpsert` and calls the same server target service used by saved Profile responses.

Status: implemented but uncommitted.

### 5.2 Additional targets

`TargetResponse.additional_targets` is additive and backward compatible. It currently returns six definitions with nullable target values.

Status: implemented but uncommitted.

### 5.3 Diary response

Diary entry totals already include nullable optional nutrient totals. No new daily nutrient endpoint is required because the current Diary screen receives snapshot totals for the selected day.

Status: implemented but uncommitted.

## 6. Exact Wave 1 API Delta

### 6.1 Required route changes

**No new runtime route is required.**

Reasons:

- Profile and week responses already carry authoritative target metadata.
- Food Details completeness must calculate from the loaded Food without a separate blocking request.
- Diary details can aggregate the already-loaded snapshot totals.
- A new endpoint would add latency and another failure mode without adding data.

### 6.2 Required contract stabilization

Preserve and formally test:

- `TargetResponse.additional_targets` is optional/additive for old clients.
- Unknown target values serialize as `null`.
- Only fiber has numeric `target_value=30`.
- Cholesterol is `monitor_only` with null target.
- The four unconfigured nutrients retain null target values.
- Preview and save use the same target response shape.
- `carb_clamped` has an explicitly approved UI/API outcome.

### 6.3 Central registry contract

Preferred exact delta:

1. Add one repository-owned data contract, for example `shared/nutrition/additional_nutrients.json`.
2. Store stable key, Arabic label, unit, precision, order, target type/source/value, and participation flags in that file.
3. Validate/load it in Python for `TargetResponse.additional_targets`.
4. Import/generate TypeScript definitions from the same file for Food Details, Profile, and Diary.
5. Keep numeric target calculation and response generation on the server.

This removes duplicated definitions without requiring a new endpoint or client-side target formula.

If the build toolchain cannot consume one shared contract, stop and document the constraint before selecting an additive registry endpoint. Do not silently retain two editable sources.

## 7. Exact Service/Frontend Delta

### 7.1 Backend

- Keep `calculate_targets()` unchanged except for the approved explicit negative-carb outcome.
- Load the shared nutrient definition contract.
- Continue returning target metadata through Profile/Week target responses.
- Preserve snapshot number/null semantics.
- Add pure tests for registry validity and target payload identity.

### 7.2 Frontend

- Remove independently authored nutrient values from `frontend/lib/nutrients.ts`; consume generated/shared definitions.
- Change daily nutrient aggregate `amount` to `number | null`.
- When `known===0`, render `غير متوفر`, coverage 0%, and no target progress/status.
- When `known>0` and coverage is incomplete, render the known sum as `على الأقل`.
- When known values include explicit zero, display zero and count it in coverage.
- Expand Profile explanation copy without adding formulas.
- Surface approved `carb_clamped` behavior.

### 7.3 No-change areas

- Food per-100 storage.
- Serving calculation utility.
- Foods list/search/pagination.
- Add Food sheet internals.
- Diary meal type schema.
- Hard-delete behavior.
- Global navigation.

## 8. Backward Compatibility

### 8.1 Existing profiles

- Do not rewrite saved protein/fat settings.
- A legacy `1.8` protein value remains valid and visible.
- A saved `0.25` female fat ratio remains custom/saved until explicit user action.

### 8.2 Existing Foods

- Nullable nutrient columns remain nullable.
- Explicit zeros remain zeros.
- No completeness backfill occurs.

### 8.3 Existing Diary entries

- Missing snapshot keys validate as null.
- No backfill to zero.
- Historical totals continue using saved snapshots.
- Legacy `unspecified` meal entries remain readable.

### 8.4 Existing clients

- Existing Profile clients can ignore `additional_targets`.
- Food/Diary routes retain their current shape.
- No enum values are renamed.

## 9. Security And Environment Constraints

- Use local/dev PostgreSQL only for rehearsal.
- Do not place connection strings or passwords in reports/config commits.
- Keep `.env*`, local databases, logs, `.next`, `node_modules`, Playwright runtime artifacts, and debug fixtures excluded.
- Keep single-user bearer auth on any additive endpoint if the fallback endpoint option is ever approved.

## 10. Data/API/Migration Verdict

| Area | Verdict |
|---|---|
| New database columns | Not required |
| New migration | Not required |
| Existing migrations | Must be versioned and rehearsed |
| New API route | Not required |
| Existing additive API field | Keep and contract-test |
| Shared registry | Required Wave 1 delta |
| Snapshot data rewrite | Prohibited |
| Unknown-to-zero backfill | Prohibited |
