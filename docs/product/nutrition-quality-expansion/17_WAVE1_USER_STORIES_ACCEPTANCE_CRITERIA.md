# Wave 1 User Stories and Acceptance Criteria

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-BAQA-17` |
| Version | `1.0` |
| Status | `Approved — Product, BA, and UX` |
| Owner | Product / BA / UX |
| Approver | Product / BA / UX |
| Approval date | `2026-07-16` |
| Review | `17A_WAVE1_USER_STORIES_ACCEPTANCE_REVIEW.md` |
| Critical / High / Product decisions | `0 / 0 / 0` |
| Pinned revision | Pending |
| Implementation authorization | `No` |

## Common Acceptance Contract

All stories are Arabic-first RTL, use Western numerals, preserve at least 44px targets, visible focus, semantic headings, keyboard access, no blank alerts, and responsive layouts at 320/360/390/430px without horizontal overflow. Authentication and data are Principal-scoped. Cross-owner and nonexistent IDs are indistinguishable. Legacy data is never inferred or rewritten. Dependencies are Artifacts 13-16 unless narrowed. Progress, seven-day Analysis, clinical modes, offline sync, and unrelated redesign are out of scope for every story.

## Stories

### `W1-US-001` — Principal-isolated baseline data

- **Feature/story:** As the authenticated personal user, I access only my Profile, Foods, Diary, summaries, plans, and duplicates so credentials cannot expose another Principal.
- **Rationale/preconditions:** Durable Principal provisioned; valid credential.
- **Acceptance:** Given two Principals, when either lists/reads/updates/deletes/aggregates, then only owner rows participate. Given another owner's ID or a random ID, then both return the same `404`. Missing/invalid auth returns `401`. Token rotation preserves access to the same rows.
- **Negative/legacy:** Client owner fields are rejected; no global fallback. Migrated rows belong only to the confirmed deployment Principal.
- **Accessibility/RTL:** Auth errors use a named alert only when present; focus moves to actionable recovery.
- **Traceability:** C01; PD-023/025; ADR-001/002; API sections 1-2.

### `W1-US-002` — Profile cut preference and defaults

- **Story:** As a user editing Profile, I select 15%, 20%, or 25% cut intensity and understand 20% is recommended.
- **Acceptance:** Given cut goal, selection persists only on successful activation. Existing Profile starts at 20%. Non-cut goal retains but does not apply preference. Restore Defaults changes draft only. Sex-aware fat defaults and custom protein/fat remain preserved.
- **Negative/legacy:** Preview does not save; failed activation does not update Profile. No guaranteed weight-loss claim.
- **Traceability:** H01; PD-005; API Profile/activation.

### `W1-US-003` — Calorie safety outcome

- **Story:** As a user, I can preview any calculated target but cannot activate a blocked low-energy result.
- **Acceptance:** Final >1200 allows activation; 800-1200 inclusive shows neutral specialist-review text and blocks; below 800 shows stronger neutral block. No acknowledgment bypass. Deficit cap disclosure is shown when applied.
- **Negative:** Stable errors remain announced; no clinical override or diagnosis.
- **Traceability:** H01; API safety outcomes; Golden `W1-GC-02`.

### `W1-US-004` — Protein basis disclosure

- **Story:** As a user, I see whether current or adjusted calculation weight produced protein without client-side formulas.
- **Acceptance:** BMI <30 uses actual; BMI >=30 uses adjusted. UI displays Backend values and approved Arabic meaning; reference weight is called `وزن مرجعي للحساب`, never ideal/goal weight. Top-level protein equals nested target.
- **Negative:** Client basis is not accepted; custom protein factor remains.
- **Traceability:** H02; PD-006; API protein object.

### `W1-US-005` — Carbohydrate warning or rejection

- **Story:** As a user, I receive truthful warnings for positive low carbohydrates and a block when allocation is non-positive.
- **Acceptance:** >=130 no warning; 100-<130 calm info; >0-<100 stronger warning; raw or rounded <=0 returns domain error and no activation. `carb_clamped` is never true on success.
- **Negative:** No diagnosis/override; warnings are not blocks.
- **Traceability:** H03; PD-007; API warnings/errors.

### `W1-US-006` — Preview and activate Target Plan

- **Story:** As a user, I preview, explicitly confirm, and activate an immutable plan with a clear start date.
- **Acceptance:** Preview persists nothing. New Profile without target source may start today; legacy/existing starts next Riyadh date. Activation is atomic/idempotent. Current/proposed/scheduled targets are distinct.
- **Negative:** Backdating/arbitrary scheduling/client effective date are rejected. Blocked H01/H03 result creates no plan or Profile update.
- **Traceability:** H04; ADR-005/009/010; API lifecycle.

### `W1-US-007` — Replace pending plan

- **Story:** As a user with a next-date plan, I can confirm replacement while preserving audit history.
- **Acceptance:** UI discloses replacement; old pending becomes superseded-before-effective; one pending remains; retry returns same result.
- **Negative:** Missing confirmation, payload-mismatched key, overlap, or already-effective plan fails without partial state.
- **Traceability:** H04; API pending replace.

### `W1-US-008` — Registry loading and compatibility

- **Story:** As a user, I receive authoritative labels/rules or an honest loading/error/incompatible state.
- **Acceptance:** Registry-dependent UI waits for Backend metadata; retry works; incompatible schema blocks Food controlled writes and plan activation while unrelated truthful baseline views continue.
- **Negative:** No fabricated fallback labels/targets/rules and no offline rule authority.
- **Traceability:** H05/H10; ADR-004/007; Registry API.

### `W1-US-009` — Complete 16-nutrient Food data

- **Story:** As a user, I enter/view all approved exact nullable nutrients per 100 basis.
- **Acceptance:** Explicit zero displays `0`; null displays `غير متوفر`; DFE/RAE exact fields are separate; serving display scales Backend source values without changing source basis.
- **Negative/legacy:** Generic folate/vitamin A remain labeled legacy and never auto-convert or satisfy exact completeness.
- **Traceability:** H05; PD-009; Data Food.

### `W1-US-010` — Food groups, contributions, and traits

- **Story:** As a user, I classify a simple/composite Food with reviewed quantitative contributions and independent traits.
- **Acceptance:** Controlled primary category is organizational only. Contributions >0 and <=100, unique group, total <=100, partial total allowed. Traits do not add servings. Status/completeness shown separately.
- **Negative/legacy:** No inference from name/category/macros; remainder not assigned; legacy begins unknown. Invalid subtype/overlap returns field error.
- **Traceability:** H06; PD-010/011.

### `W1-US-011` — Source and reliability

- **Story:** As a user, I select source type and see Backend-derived Arabic reliability without choosing it.
- **Acceptance:** Known source requires name; optional reference; exact mapping is returned with version. `multiple_sources` displays mixed.
- **Negative/legacy:** Reliability input rejected; legacy source preserved but not inferred; reliability is not health/quality score.
- **Traceability:** H07; PD-012/013.

### `W1-US-012` — Ingredients and NOVA

- **Story:** As a user, I optionally record ingredients/source and manually review NOVA 1-4 or unknown.
- **Acceptance:** ingredient text requires source type; known type requires source name. Saving NOVA marks reviewed; unknown+reviewed is valid.
- **Negative/legacy:** No automated suggestion, hazard claim, allergen workflow, or general review workflow. Legacy is unknown/unreviewed.
- **Traceability:** H07; PD-012.

### `W1-US-013` — Snapshot v2 logging

- **Story:** As a user logging Food, I preserve nutrition/classification/source history as captured even after Food changes.
- **Acceptance:** Backend creates v2 from owner Food and date-effective plan. Quantity scales known values; null stays null. Meal/quantity edits do not mutate snapshot. Food deletion retains captured identity.
- **Negative/legacy:** Client snapshot/plan/version rejected; Food/date change requires delete/create. V1 remains readable and unenriched.
- **Traceability:** H08; ADR-006; Diary API.

### `W1-US-014` — Diary target provenance

- **Story:** As a user, I understand whether a day uses versioned, legacy, or no target source.
- **Acceptance:** Backend resolves by Principal+date. New-user same-date eligible entries bind atomically without snapshot change; legacy current-day entries remain unversioned. Current Profile never changes historical day meaning.
- **Negative:** Scheduled plan not used early; ended plan not used after exclusive end.
- **Traceability:** H04/H08/H11.

### `W1-US-015` — Truthful nutrient coverage

- **Story:** As a user, I see exact, at-least, unavailable, or empty amounts based on snapshot coverage.
- **Acceptance:** Empty coverage null; all-unknown amount null/coverage 0; partial known sum `على الأقل`; complete exact. Known zero counts known. Partial min/max/range evaluation follows H11 asymmetric rules and suppresses definitive remaining/available.
- **Negative:** Null never becomes zero; malformed/unsupported snapshot blocks understated summary and offers retry/support state, not fake totals.
- **Traceability:** H11; ADR-008; API aggregation.

### `W1-US-016` — Hard delete and historical safety

- **Story:** As a user deleting my Food, historical Diary remains readable from immutable snapshots.
- **Acceptance:** Owner confirmation deletes Food/group/traits, clears live Diary Food link, retains snapshot values/name and target binding.
- **Negative:** Cross-owner ID is non-enumerating; no snapshot recalculation or deletion cascade to Diary.
- **Traceability:** H08; Data deletion matrix.

### `W1-US-017` — Idempotency and concurrent actions

- **Story:** As a user retrying activation/replacement, I receive one durable result without duplicate plans.
- **Acceptance:** Same key/payload replays; same key/different payload conflicts; concurrent requests yield one valid plan/pending state; failure rolls back all.
- **Negative:** Cross-Principal key reuse leaks nothing; stale preview requires re-preview.
- **Traceability:** ADR-009; API idempotency.

### `W1-US-018` — Responsive accessible Wave 1 controls

- **Story:** As a keyboard, screen-reader, and mobile user, I can complete every Wave 1 flow.
- **Acceptance:** Dialog/sheet naming, focus trap/restore, Escape, reduced motion, semantic progress, textual status, bidi-isolated values, safe-area padding, readable wraps, and 44px targets pass at required widths.
- **Negative:** No color-only status, overlap, horizontal scroll, hidden home-indicator content, or blank alert.
- **Traceability:** PD-022; UI Matrix; Verification Plan.

## Error, Loading, and Retry Matrix

| State | Required behavior |
|---|---|
| Initial loading | Stable compact skeleton only when perceptible; no content shift |
| Network failure | Named Arabic error and explicit retry; draft input retained in memory |
| Registry incompatible | Explain incompatibility; block dependent mutation; no fallback |
| Validation | Field or domain summary linked to controls; focus first invalid field |
| Authorization | `401` recovery; owner-missing `404` non-enumerating |
| Integrity failure | No totals; explicit data-integrity state; owner-safe reference |
| Empty | Purpose-specific calm empty state; no fake zeros |
| Legacy | Preserve and label ambiguity; do not demand fabricated values |

## Story Coverage Gate

Each story requires positive, negative, authorization, legacy, accessibility, RTL/responsive, API, Backend, and regression tests where applicable. Physical-device evidence may remain pending during implementation but is mandatory before release sign-off.
