# Plan 005 — Preserve cut intensity and expose Profile safety decisions

> **Executor instructions:** Follow this plan in order, run every verification command, and confirm its expected result before continuing. The backend remains the sole calculation and activation authority. If a STOP condition occurs or drift invalidates an excerpt, stop and report rather than improvising. When complete, update this plan's row in `plans/README.md` unless a reviewer owns the index.

## Plan status

- Priority: P1
- Effort: M
- Risk: MED
- Depends on: none; execute after Plan 001 when practical for a clean session-isolation baseline
- Category: bug / direction
- Planned at: commit `a91ba09`, 2026-07-21
- Status: TODO — exact Arabic safety strings are approved and frozen in `docs/product/nutrition-quality-expansion/20_H03_APPROVED_ARABIC_SAFETY_MESSAGES.md`

## Why this matters

The Profile API supports and stores a 15%, 20%, or 25% cut preference. The frontend draft omits that field, so an unrelated edit sends no value and silently triggers the backend compatibility default of 20%. The preview response already contains activation safety, deficit-cap, warning, and protein-basis information, but the UI renders only calories/macros and lets any preview hash enter confirmation. Users therefore lose their selected preference and see a generic backend rejection instead of the approved safety explanation.

Required invariant: the frontend always preserves and submits the explicit preference, retains it while a non-cut goal hides the selector, renders authoritative backend preview fields without duplicating formulas, and never opens confirmation or sends activation when `can_activate` is false.

## Drift check

From the repository root:

```powershell
git diff --stat a91ba09..HEAD -- frontend/lib/types.ts frontend/components/ProfilePage.tsx frontend/app/globals.css frontend/e2e/profile/profile.spec.ts
git diff --stat a91ba09..HEAD -- backend/app/schemas.py backend/app/nutrition_rules/calculation.py backend/app/services/target_plans.py docs/product/nutrition-quality-expansion
git status --short
```

Expected: the first diff covers every modifiable file in Scope; the second checks read-only contracts. Re-read changed response fields, stable error codes, and Profile interaction state. Backend/docs are reference-only and must not be edited by this plan.

## Current state and evidence

`frontend/lib/types.ts:19-51` already models authoritative target output including selected cut intensity, requested/applied deficit, cap state, final calories, safety outcome, `can_activate`, protein calculation, and calculation warnings.

`frontend/lib/types.ts:77-87` makes the request field optional:

```ts
selected_cut_intensity?: 0.15 | 0.2 | 0.25;
```

`frontend/components/ProfilePage.tsx:77-115` defines `DraftProfile`, `toDraft`, and `blankDraft` without cut intensity. `frontend/components/ProfilePage.tsx:140-174` validates/builds the request without it.

The backend therefore applies its documented compatibility default in `backend/app/schemas.py:104-115`:

```python
selected_cut_intensity: Literal[0.15, 0.2, 0.25] = 0.2
```

`frontend/components/ProfilePage.tsx:516-528` treats any current preview hash as reviewable without checking `preview.can_activate`. `frontend/components/ProfilePage.tsx:735-742` renders only calories/macros. `frontend/components/ProfilePage.tsx:313-324` maps activation safety failures to a generic save error.

Governing requirements:

- `docs/product/nutrition-quality-expansion/13_H01_APPROVED_PRODUCT_OWNER_DECISION.md:27-34`: the 15/20/25 preference persists; non-cut retains but does not apply it.
- The same decision at lines 51-63: 800–1200 and below-800 previews may be shown but never activated or bypassed.
- The same decision at lines 67-88: frontend consumes backend calculations and must not recreate thresholds/formulas.
- `docs/product/nutrition-quality-expansion/17_WAVE1_USER_STORIES_ACCEPTANCE_CRITERIA.md:34-53`: 20% recommended, cap disclosure, blocked states, and backend-owned protein-basis wording.
- `docs/product/nutrition-quality-expansion/14_H02_APPROVED_PRODUCT_OWNER_DIRECTION.md:63-93,130-133`: nested protein fields, authoritative top-level agreement, and the approved `وزن مرجعي للحساب` label.
- `docs/product/nutrition-quality-expansion/19_WAVE1_UI_STATE_MATRIX.md:30-39`: segmented accessible selector, safety blocks, warnings, and protein basis.
- `docs/product/nutrition-quality-expansion/PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md:235-250`: frozen Arabic option labels `خفيف 15%`, `عادي 20%`, `قوي 25%`.
- `docs/product/nutrition-quality-expansion/18_WAVE1_GOLDEN_CALCULATIONS.md:30-36,56-69`: regression boundaries for 15/20/25, 799/800/1200/1201, carbohydrate warnings, and cap behavior. These are backend fixtures, not client formulas.

Backend authority is already present in `backend/app/nutrition_rules/calculation.py:273-297` and `backend/app/services/target_plans.py:229-238`. Existing backend tests cover calculation boundaries. Existing frontend route-interception and restoration helpers are in `frontend/e2e/profile/profile.spec.ts:8-33,150-190`; responsive checks are at lines 319-334.

## Pre-implementation approval gate

The Product Owner and Arabic content review gate is complete. The authoritative decision artifact is:

`docs/product/nutrition-quality-expansion/20_H03_APPROVED_ARABIC_SAFETY_MESSAGES.md`

It records the exact Arabic strings, their outcome-code mapping, approval roles, approval date, presentation locations, blocking behavior, Backend authority, and frozen status for implementation and testing. The exact strings are inlined in Step 4 and repeated as the test oracle in Step 7.

Before changing frontend source, the executor must confirm that the artifact remains present and that both inlined strings are byte-for-byte identical across the artifact, Step 4, and Step 7. If the artifact or mapping drifts, STOP and request Product clarification; do not draft substitute copy in application code or tests.

## Commands you will need

Command-location rule: treat every fenced PowerShell block in this plan as a fresh shell. Start it at the repository root unless the immediately preceding text says `frontend` or `backend`; a `Set-Location` in one block never carries into another.

| Purpose | Command | Expected |
|---|---|---|
| Install (from `frontend`) | `npm ci` | Exit 0; lockfile honored |
| Typecheck (from `frontend`) | `npm run typecheck` | Exit 0; no TypeScript errors |
| Profile E2E (from `frontend`) | `npx playwright test e2e/profile/profile.spec.ts --project=foods-chromium` | Existing and new Profile cases pass |
| Build (from `frontend`) | `npm run build` | Exit 0 |
| Full frontend E2E | `npm run test:e2e` | Zero failures |
| Backend contract guard (from `backend`) | `python -m pytest -q tests/test_calc.py tests/test_rules_registry_api.py tests/test_target_plans.py` | All pass without backend edits |

### Mandatory Playwright service prerequisite

`frontend/playwright.config.ts` has no `webServer`; Playwright does not start the application. Before any focused or full E2E command, either run it in the repository's `e2e` GitHub Actions job (`.github/workflows/ci.yml:90-163`) or reproduce that job locally. Completion requires a passing E2E job/harness; a connection-refused local run is not evidence.

The canonical harness is:

1. Python 3.12, Node 24, Chromium, and an approved disposable PostgreSQL 16 database.
2. Set the same local-only environment contract before migration/build/start:

   ```powershell
   $env:DATABASE_URL='<approved disposable PostgreSQL SQLAlchemy URL>'
   $env:SUPABASE_URL='http://127.0.0.1:8765'
   $env:SUPABASE_JWT_AUDIENCE='authenticated'
   $env:CALENDAR_TIMEZONE='Asia/Riyadh'
   $env:SNAPSHOT_V3_WRITER_ENABLED='true'
   $env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8000'
   $env:NEXT_PUBLIC_SUPABASE_URL='http://127.0.0.1:8765'
   $env:NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY='e2e-public-key'
   $env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3000'
   $env:PLAYWRIGHT_API_URL='http://127.0.0.1:8000'
   $env:PLAYWRIGHT_SUPABASE_URL='http://127.0.0.1:8765'
   ```

3. Install and migrate from the repository root:

   ```powershell
   python -m pip install -e ".\backend[dev]"
   Set-Location frontend
   npm ci
   npx playwright install chromium
   Set-Location ..\backend
   alembic upgrade head
   Set-Location ..
   ```

4. Provision the fixed local Admin Principal (`auth_user_id=10000000-0000-0000-0000-000000000001`, `admin.e2e@example.test`) using the exact SQL in `.github/workflows/ci.yml:135-144`. Do this only in the disposable database; the auth emulator and global setup depend on that identity.
5. In separate local terminals—or through the CI job—run these long-lived processes with the environment above:

   ```powershell
   # Repository root
   python backend/scripts/e2e_supabase_auth.py

   # backend/
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

   # frontend/ (build once before start)
   npm run build
   npm run start -- --hostname 127.0.0.1 --port 3000
   ```

6. Require HTTP success from `http://127.0.0.1:8765/health`, `http://127.0.0.1:8000/health`, and `http://127.0.0.1:3000/profile` before Playwright. If local provisioning is unavailable, stop local E2E work and require the canonical CI `e2e` job instead; never target a shared or real Supabase project.

## Scope

In scope:

- `frontend/lib/types.ts`
- `frontend/components/ProfilePage.tsx`
- `frontend/app/globals.css` only for new Profile-specific selectors
- `frontend/e2e/profile/profile.spec.ts`

Out of scope:

- Backend schemas, calculations, thresholds, routes, or migrations
- Client-side copies of the 750/800/1200 rules or calorie/macro formulas
- Clinical override, acknowledgment bypass, or specialist workflow
- Custom cut percentages outside 15/20/25
- Effective-date/timezone redesign
- Diary/TargetPlan presentation elsewhere
- Global stylesheet cleanup
- Unrelated Profile redesign, field ranges, or dirty-form architecture
- Adding a new frontend unit-test framework

## Git workflow

```powershell
git switch -c fix/profile-cut-safety-preview
git status --short
```

Suggested commits:

```text
fix(profile): preserve cut intensity in drafts
feat(profile): present authoritative safety previews
test(profile): cover blocked and warning outcomes
```

Run `git diff --check`; stage only the four frontend files. Do not commit generated screenshots unless the repository's established visual workflow explicitly requires updating a tracked baseline. Do not push or open a pull request unless the operator explicitly asks.

## Implementation steps

### 1. Make cut-intensity omission impossible in frontend types

In `frontend/lib/types.ts`:

- export `type CutIntensity = 0.15 | 0.2 | 0.25`;
- use it in `TargetResponse` and related profile response shapes;
- make `ProfileInput.selected_cut_intensity` required.

Do not broaden to arbitrary numbers or strings. Resolve every TypeScript error by carrying the actual field, not by adding assertions/defaults at call sites.

Verification:

```powershell
rg -n "selected_cut_intensity|CutIntensity" frontend --glob '*.{ts,tsx}'
```

Expected: every Profile request has an explicit typed value; no `as CutIntensity` hides unvalidated input.

### 2. Preserve the preference through all draft transitions

In `frontend/components/ProfilePage.tsx`:

- add `selected_cut_intensity` to `DraftProfile`;
- copy the saved backend value in `toDraft`;
- initialize a new/blank draft to `0.2`;
- normalize/validate the value against exactly `0.15`, `0.2`, or `0.25`;
- include it in preview and activation payloads and dirty-state/hash comparisons;
- after successful activation/refetch, adopt the returned persisted value.

Changing weight, height, goal, macros, or another unrelated field must not alter the selected intensity. A failed preview/activation must not mutate the saved Profile.

Expected: a seeded 15% or 25% Profile sends that same value in both requests after an unrelated edit.

Verification:

```powershell
Set-Location frontend
npm run typecheck
```

Expected: exit 0; draft hydration, defaults, comparison, preview, and activation paths all satisfy the required field.

### 3. Add the approved accessible selector

When `draft.goal === 'cut'`, render a segmented radiogroup with three at-least-44px choices:

- `خفيف` / `15%`
- `عادي` / `20%` / visible `موصى به`
- `قوي` / `25%`

Use native radios or the established `OptionList` radiogroup semantics around `frontend/components/ProfilePage.tsx:746-747`. Ensure keyboard arrow/tab behavior, checked state, focus visibility, and accessible group label. Use Western numerals with bidi isolation where needed.

Do not describe percentages as guaranteed loss rates. Switching to maintain/bulk hides the selector but retains and still submits the preference; the backend decides that it is not applied. Switching back to cut restores the prior choice.

Verification:

```powershell
Set-Location frontend
npm run typecheck
```

Expected: exit 0. Keyboard, retention, and axe behavior are proven by the Step 7 Playwright cases.

### 4. Render the authoritative preview decision

Expand `ExpectedTargetsCard` using response values only. Present:

- `final_target_calories` and existing macros;
- selected intensity for a cut preview;
- returned requested and applied deficit values;
- a textual disclosure when `deficit_cap_applied` is true, using the returned applied value rather than calculating 750 locally;
- `safety_outcome` and `can_activate` as a calm but unmistakable status;
- every `calculation_warnings` entry using backend `message_ar` and, when numeric context is shown, the returned `value` and `reference_value`; the current warning object has no `unit` field, so use the typed carbohydrate dimension's existing gram presentation rather than inventing a response field;
- protein-calculation disclosure as a definition list: render backend `explanation_ar`, `basis`, `bmi_used`, `actual_weight_kg`, nullable `reference_weight_kg`, `reference_weight_label_ar`, `calculation_weight_kg`, `protein_per_kg`, and `target_g`; use the returned reference label (whose approved value is `وزن مرجعي للحساب`), never ideal/goal weight. Do not recompute BMI, adjusted weight, or protein in the client.

Map enum/code to presentation only. Use the two exact Arabic strings frozen in `docs/product/nutrition-quality-expansion/20_H03_APPROVED_ARABIC_SAFETY_MESSAGES.md`:

- `specialist_review_required`: **لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.**
- `very_low_energy_blocked`: **لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.**

The approved messages must remain verbatim and retain the frozen constraints: no diagnosis or treatment promise, no implication of an in-product specialist workflow, and no acknowledgment/override path. Tests must assert the exact inlined strings as well as the stable outcome container, focus/alert semantics, and activation block.

Do not infer an outcome from calorie/carbohydrate numbers. Do not turn an informational/warning entry into a block when `can_activate` is true. Unknown future outcome codes must fail visibly/conservatively rather than display an activatable normal state.

Verification:

```powershell
Set-Location frontend
npm run typecheck
```

Expected: exit 0; all fields are read from the typed `TargetResponse`, with no locally introduced calorie/carb threshold constant.

### 5. Enforce `can_activate` across every submit path

Before opening the confirmation UI, require a current preview hash and `preview.can_activate === true`.

For a blocked submit attempt:

- send no activation request;
- do not open the confirmation dialog;
- retain the draft and preview;
- focus a named safety explanation element;
- announce meaningful text without inserting an empty alert;
- reset attempted/focus state when the draft or preview changes.

Require `can_activate` again in the confirmation render and mutation guards as defense in depth, including keyboard/programmatic submission and double-click paths.

When the backend rejects activation with stable `SPECIALIST_REVIEW_REQUIRED` or `VERY_LOW_ENERGY_TARGET_BLOCKED` (use the exact existing response codes after re-reading the contract), map it into the same safety recovery UI, preserve the draft, close/prevent confirmation, and require a fresh preview. Do not label it a network/save failure.

The backend remains the final authority; client guarding improves explanation but does not replace server rejection.

Verification:

```powershell
Set-Location frontend
rg -n "can_activate|SPECIALIST_REVIEW_REQUIRED|VERY_LOW_ENERGY_TARGET_BLOCKED" components/ProfilePage.tsx
npm run typecheck
```

Expected: every confirmation/mutation entry is guarded, both stable backend codes have explicit recovery, and typecheck exits 0.

### 6. Add narrowly scoped responsive styling

In `globals.css`, add Profile-specific selectors near the current Profile styles:

- three equal segmented columns with wrapping when necessary;
- minimum 44px interactive size;
- focus-visible treatment matching existing tokens;
- safety/warning panels with icon/text semantics in addition to color;
- wrapping at 320px without horizontal overflow;
- existing `--warning`, `--danger`, `--danger-soft`, card, RTL, and reduced-motion conventions.

Do not refactor or remove the large global stylesheet in this plan. Confirm sticky actions and current Profile layout remain intact at 320, 360, 390, and 430px.

Verification:

```powershell
Set-Location frontend
npm run build
```

Expected: exit 0; CSS parses in the production build and no unrelated global selector is removed.

### 7. Add focused Playwright regressions

Extend `frontend/e2e/profile/profile.spec.ts`, reusing the helper that restores all Profile fields after tests. Add clearly named cases:

Use these exact approved Arabic strings as the explicit test oracle in every corresponding preview-block and activation-recovery assertion:

- `SPECIALIST_REVIEW_REQUIRED`: **لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.**
- `VERY_LOW_ENERGY_TARGET_BLOCKED`: **لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.**

1. `@p0 cut intensity survives edits and activation payloads`
   - seed 15%, change unrelated input, preview/activate, assert both request bodies contain 0.15 and returned Profile remains 0.15;
   - repeat or parameterize for 25%.
2. `@p0 cut preference defaults and survives non-cut goals`
   - create a unique normal user through the local auth emulator using the same local-only signup/provisioning pattern as `frontend/e2e/v2-premerge-acceptance.spec.ts:32-98`, open its initially missing Profile in a fresh context, and assert the blank draft uses 20%; select 15%, switch away from cut and back, retain 15%; submitted non-cut payload still carries 15%. Do not point signup at a real Supabase project.
3. `@p0 specialist review preview blocks activation`
   - route-modify preview to the real 800–1200 boundary outcome; assert the exact approved Arabic string in the updated Step 4, focus, no dialog, and zero activation POSTs.
4. `@p0 very low energy preview blocks activation`
   - cover the below-800 outcome; assert the corresponding exact approved Arabic string in the updated Step 4 and the same focus/no-dialog/no-POST invariant.
5. `@p0 preview discloses cap and server calculation warnings`
   - preserve a complete real response but set returned cap/warning fields and an adjusted-weight `protein_calculation`; assert Arabic server message plus returned `value`/`reference_value` (the warning schema has no unit field), assert the protein explanation/definition-list values and `وزن مرجعي للحساب` label, and prove a `can_activate=true` warning remains activatable. Add a normal actual-weight assertion as the paired basis case; never assert a locally recomputed value.
6. `@p0 activation safety errors preserve the draft`
   - allow confirmation from a normal preview, return each stable safety error from activation, assert the corresponding exact approved recovery string, retained inputs, closed confirmation, and required re-preview.

Also cover exact backend regression fixtures 799/800/1200/1201 through stubbed response semantics, not local computations. Assert normal preview still activates. Extend responsive/axe coverage for the selector and safety panels at 320/360/390/430 widths, no overflow, 44px controls, meaningful alert text, and focus after a blocked attempt.

When intercepting preview responses, begin with a valid real/fixture response and change only scenario fields. Do not omit fields and accidentally test an impossible payload.

Verification:

```powershell
Set-Location frontend
npx playwright test e2e/profile/profile.spec.ts --project=foods-chromium
```

Expected: existing tests plus all six named cases pass without retry dependence; blocked cases make zero activation POSTs and small-width/axe assertions pass.

## Test plan

First, from `frontend`, run static gates before starting the built Next server:

```powershell
npm ci
npm run typecheck
npm run build
```

Then start and health-check the Mandatory Playwright service prerequisite above. While all three local services are running (or inside the canonical CI E2E job), run:

```powershell
npx playwright test e2e/profile/profile.spec.ts --project=foods-chromium
npm run test:e2e
```

Expected: install/typecheck/build exit 0; all existing and six new Profile cases pass; blocked cases send zero activation POSTs; axe/responsive assertions have no regression.

From the repository root, run the backend compatibility guard without backend edits:

```powershell
Set-Location backend
python -m pytest -q tests/test_calc.py tests/test_rules_registry_api.py tests/test_target_plans.py
```

Expected: authoritative formulas, boundaries, preview response, and activation enforcement tests pass unchanged.

Finish with:

```powershell
git diff --check
git diff --name-only
```

Expected: only `frontend/lib/types.ts`, `frontend/components/ProfilePage.tsx`, `frontend/app/globals.css`, and `frontend/e2e/profile/profile.spec.ts` are changed, plus plan-status metadata only if the workflow tracks it.

## Done criteria

- [ ] `selected_cut_intensity` is a required 15/20/25 frontend input and exists in every draft/payload path.
- [ ] Stored 15% and 25% survive unrelated edits, preview, and activation; new drafts default to 20%.
- [ ] Non-cut goals hide but retain the preference and restore it on return to cut.
- [ ] The approved accessible selector works by keyboard and at small widths.
- [ ] Preview displays returned safety outcome, activation eligibility, cap disclosure, calculation warnings, and protein basis without client formulas.
- [ ] The prerequisite artifact path and both exact approved Arabic safety strings are inlined in Step 4 and asserted verbatim in focused E2E tests.
- [ ] Every blocked preview path prevents confirmation and activation POST, focuses the exact approved safety copy, and retains the draft.
- [ ] Stable backend safety rejections recover into the same state rather than a generic error.
- [ ] Normal and warning-only previews remain activatable when `can_activate` is true.
- [ ] Focused/full frontend gates and unchanged backend compatibility tests pass.
- [ ] `git status --short` shows no modified file outside this plan and the intentional index status update.

## STOP conditions

- The approval gate is complete in `docs/product/nutrition-quality-expansion/20_H03_APPROVED_ARABIC_SAFETY_MESSAGES.md`. Stop if that artifact becomes missing or loses Approved/Frozen status, either required approval role or approval date is removed, or either Arabic string differs between the artifact, Step 4, and Step 7.
- Stop if Profile GET no longer returns a valid `selected_cut_intensity`; establish the current API contract first.
- Stop if response fields or stable safety error codes differ from the cited contract; update the presentation map from authoritative docs/backend before coding.
- Stop if implementation requires local copies of the 750/800/1200 or carbohydrate/calorie formulas.
- Stop if a warning must block despite `can_activate=true`; that is a backend/product policy change.
- Stop if work expands into clinical override, backend policy, custom intensities, or unrelated Profile redesign.
- Stop if Plan 001/provider drift changes Profile mount/cache behavior in a way that invalidates test setup; rebase and re-run the drift review.

## Maintenance notes

- Future safety outcomes must extend the typed presentation map and E2E cases; never infer them from numeric thresholds in the client.
- Treat `can_activate` as the only client presentation gate and backend activation as the final enforcement gate.
- Keep request-field requiredness so compatibility defaults do not silently mask future frontend omissions.
- Preserve server-provided Arabic warning text and returned values/reference values; presentation may style them but must not recalculate them or invent response fields.
