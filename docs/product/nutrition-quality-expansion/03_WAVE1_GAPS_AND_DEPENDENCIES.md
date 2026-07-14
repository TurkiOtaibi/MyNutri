# Wave 1 Gaps And Dependencies

Audit date: 2026-07-14

## 1. Scope Boundary

Wave 1 is the approved Nutrition Quality & Progress expansion layered on the current Foods, Diary, Profile, and Add Food implementation.

Wave 1 does not include:

- Gram/ml Diary logging.
- Numeric limits for sodium, saturated fat, added sugar, or potassium without product approval.
- Health/Food-quality scores.
- Field-level nutrient provenance migration.
- Offline storage, sync, queues, or stale personal-data cache.
- Multiple profiles.
- Food photos.
- A redesign of unrelated routes.

## 2. Critical Gaps

### W1-C01 - Current baseline is not reproducible from Git

**Evidence**

- `HEAD` is the initial offline-first implementation.
- Current source spans staged, unstaged, and 107 untracked paths.
- Local PostgreSQL reports `0003_diary_meal_type`.
- `0003_diary_meal_type.py` is untracked.
- Nutrition registry, expansion tests, and implementation report are untracked.

**Impact**

Another developer or CI checkout cannot recreate the current app or safely advance its database. Wave 1 cannot be signed off against a stable revision.

**Required dependency**

Create a verified baseline checkpoint before implementing additional Wave 1 deltas. Include migrations, source, tests, and intentional reports; exclude secrets, local databases, logs, caches, runtime traces, and debug images.

### W1-C02 - Governing v1.1 decision register is unavailable

**Evidence**

The named file was not found in the repository or local attachments. Existing BA decisions conflict with later approved implementation direction on gram mode, Diary edit scope, read copy, and list presentation.

**Impact**

The audit cannot truthfully certify that every approved v1.1 decision was classified. Implementers could reintroduce superseded requirements or omit an approved delta.

**Required dependency**

Supply/version the register, assign stable decision IDs, and reconcile this audit matrix before Wave 1 final sign-off.

## 3. High Gaps

### W1-H01 - The “central” nutrient registry is duplicated

**Evidence**

- Backend definitions: `backend/app/services/nutrients.py`.
- Frontend definitions: `frontend/lib/nutrients.ts`.
- Both independently contain keys, Arabic labels, units, precision, order, target types, target values, and participation flags.
- Food Details uses frontend constants directly; Profile/Diary overlay API target metadata.

**Impact**

A future target/label/order change can produce contradictory Profile, Diary, and Food Details behavior.

**Required Wave 1 delta**

Use one repository-owned definition contract consumed by both runtimes. Keep server-calculated target responses authoritative; do not add client formulas.

### W1-H02 - All-unknown Diary nutrient data is presented as numeric zero

**Evidence**

`aggregateDailyNutrients()` initializes `amount=0`. When `known=0`, `DailyNutrientRow` still displays `0 [unit] على الأقل` and may compute target progress/status.

**Impact**

This violates the core approved rule that missing is not known zero. It can falsely imply confirmed zero sodium, saturated fat, sugar, potassium, cholesterol, or fiber.

**Required Wave 1 delta**

Represent aggregate amount as `null` when `known===0`; show `غير متوفر`; suppress amount-based progress/remaining status; retain coverage 0%. Known explicit zero must continue to display `0`.

### W1-H03 - Negative-carbohydrate configuration is still silent in the UI

**Evidence**

The backend clamps negative carbohydrate calories to zero and returns `carb_clamped=true`. The Profile UI displays returned targets without surfacing that flag.

**Impact**

An invalid macro configuration appears as an ordinary valid zero-carb target, contrary to the approved “must not silently produce negative carbs” rule.

**Required decision/delta**

Choose and test one server-authoritative behavior:

1. Reject preview/save with a structured field/form error, or
2. Preserve clamp behavior but render an explicit warning that blocks silent acceptance.

Do not reproduce the calculation in TypeScript.

### W1-H04 - Expansion-specific tests are materially incomplete

**Evidence**

The dedicated backend nutrition file has five tests. The dedicated frontend nutrition file has three broad scenarios. They do not cover many approved requirements independently.

**Missing high-risk examples**

- Preview and save equivalence using actual PUT response.
- Default-switch versus custom-value preservation.
- All-unknown versus known-zero Diary rendering.
- Add/edit/move/delete meal macro recalculation.
- Snapshot nutrients after Food edit/delete.
- Completeness thresholds and denominator.
- Focus trap/restoration and no-overflow across all target widths.

**Required dependency**

Add focused backend and frontend characterization before changing registry/aggregation behavior.

### W1-H05 - Existing migration dependency is applied but not versioned

**Evidence**

Migration `0003` is active in PostgreSQL but untracked. Migration `0002` is staged but uncommitted.

**Impact**

Migration upgrade/downgrade and deployment rehearsal are not reproducible. This is not a request for a new nutrition migration; it is a baseline integrity problem.

**Required dependency**

Version both existing migration files and rerun upgrade/downgrade/upgrade rehearsal on a disposable local PostgreSQL database before Wave 1 sign-off.

## 4. Medium Gaps

### W1-M01 - Profile explanation is incomplete

The calculation sheet mentions settings generally but does not explicitly state:

- protein uses configured grams per kilogram,
- fat uses configured percentage of calories,
- carbohydrates receive remaining calories.

This is a copy-only Wave 1 delta.

### W1-M02 - Profile validation decisions remain contradictory

Current schema accepts any positive height/weight, no age limits, protein 1.0-3.0, and fat 20-30%. D-009/D-012 specify age 10-100, height 100-250, weight 20-300, and a different fat range. The implementation must not guess which source v1.1 supersedes.

### W1-M03 - API/read-error copy differs from D-022

Foods uses the older exact copy; current Profile and Diary use newer shorter copy. This is not necessarily a product bug, but the governing copy must be reconciled.

### W1-M04 - Nutrition Quality report overstates two facts

`docs/implementation/10_NUTRITION_QUALITY_ENHANCEMENT_REPORT.md` calls the registry centralized despite two sources, and states legacy missing nutrients never become zero despite the all-unknown UI behavior. The report should be corrected after implementation, not used as proof now.

### W1-M05 - Physical-device QA remains pending

Responsive emulation exists, but real iPhone Safari and Android Chrome behavior is unverified, including safe areas, dynamic bars, touch scrolling, bottom-sheet drag, and keyboard interactions.

### W1-M06 - LAN runtime configuration is session-dependent

The default backend CORS origins and frontend API URL cover localhost only. Local logs contain failed LAN preflights. This is an environment/configuration issue, not a Nutrition Quality product change, but it blocks reliable physical-device QA until the approved dev origin/API URL is supplied per session.

## 5. Low Gaps

### W1-L01 - Untracked debug artifact

`frontend/debug-diary.png` is untracked and should not be included in a product checkpoint unless intentionally retained as documentation.

### W1-L02 - No dedicated frontend lint script

The package provides build, typecheck, and Playwright scripts, but no explicit frontend lint command. Build/typecheck provide useful gates; a lint gate is a later tooling improvement, not a Wave 1 blocker.

## 6. Dependencies

| Dependency | Required before | Reason |
|---|---|---|
| Versioned v1.1 decision register | Final decision matrix/sign-off | Resolves governing contradictions |
| Verified checkpoint of current worktree | Any new Wave 1 edit | Prevents mixing baseline stabilization with feature delta |
| `0002` and `0003` committed/rehearsed | Wave 1 DB sign-off | Current DB already depends on them |
| Characterization tests for unknown/zero and registry | Registry/Diary fixes | Protects snapshot semantics |
| Product choice for `carb_clamped` | Profile completion | Prevents silently invalid macro output |
| Product confirmation of Profile ranges | Profile validation alignment | Avoids inventing validation rules |
| LAN dev configuration | Physical-device QA | Allows phone browser to reach API |

## 7. Recommended Execution Order

1. **Governance freeze**: provide the v1.1 register and resolve gram mode, Profile ranges, copy, and `carb_clamped` behavior.
2. **Baseline checkpoint**: verify and commit current implementation/migrations without Wave 1 behavior changes.
3. **Characterization tests**: add missing tests for registry identity, null/zero aggregation, snapshots, and defaults.
4. **Centralize registry**: move definitions to one shared contract; retain API compatibility.
5. **Fix unknown-only Diary rendering**: use nullable aggregate semantics.
6. **Complete Profile explanation and negative-carb behavior**.
7. **Run migration rehearsal and all regression gates**.
8. **Run physical-device QA** after LAN configuration is confirmed.
9. **Correct implementation reports and architecture/system documentation** in a separate documentation reconciliation.

## 8. Wave 1 Entry Criteria

Wave 1 implementation can begin when:

- The v1.1 decision source is available or the unresolved decisions are explicitly approved.
- Current baseline and migrations are versioned.
- No secret/local runtime artifacts are in the checkpoint.
- Existing 245 Playwright and backend baselines can be reproduced from that checkpoint.

## 9. Wave 1 Exit Criteria

Wave 1 is complete only when:

- One nutrient registry source drives backend and frontend.
- Unknown-only data is never displayed as known zero.
- `carb_clamped` has explicit approved behavior.
- Snapshot and coverage tests pass for null and explicit zero.
- All existing Foods/Diary/Profile/Add Food regressions pass.
- PostgreSQL migration rehearsal passes from a clean baseline.
- Documentation reflects actual architecture and decisions.
- Physical-device status is reported honestly, even if pending.
