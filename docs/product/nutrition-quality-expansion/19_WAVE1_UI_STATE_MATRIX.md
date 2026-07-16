# Wave 1 UI State Matrix

## Metadata

| Field | Value |
|---|---|
| Artifact ID | `W1-UI-19` |
| Version | `1.0` |
| Status | `Approved — BA, UX, and Accessibility` |
| Owner | BA / UX / Accessibility |
| Approver | BA / UX / Accessibility |
| Approval date | `2026-07-16` |
| Review | `19A_WAVE1_UI_STATE_MATRIX_REVIEW.md` |
| Critical / High / Product decisions | `0 / 0 / 0` |
| Pinned revision | Pending |
| Implementation authorization | `No` |

## 1. Global UI Contract

Arabic-first RTL, Western numerals, bidi-isolated value/unit pairs, visible focus, 44×44px controls, semantic headings, named dialogs, focus trap/restore, Escape where applicable, reduced motion, and no color-only meaning apply throughout. Verify 320/360/390/430px, no horizontal scroll, no overlap, and safe-area padding. Existing Profile, Foods, Add Food, Diary, and navigation visual direction is preserved; only Wave 1 controls/states are added.

## 2. State Matrix

| ID | Surface / trigger | Visible content and actions | Blocked actions / Arabic intent | A11y / responsive | API / story / test |
|---|---|---|---|---|---|
| `W1-UI-001` | Global auth loading | stable shell/loading; no user data | mutations unavailable | no blank alert; focus unchanged | auth / US-001 / `UI-T001` |
| `W1-UI-002` | `401` | neutral auth failure, retry/reload | no data retained from another Principal | `role=alert` only with text | common errors / US-001 |
| `W1-UI-003` | owner ID absent/cross-owner | same generic not-found and back action | no existence hint | focus on heading/back; identical DOM intent | `RESOURCE_NOT_FOUND` / US-001 |
| `W1-UI-004` | Profile current targets | current plan/source, targets, effective date | draft is not current | heading hierarchy; values isolated | GET Profile / US-002/006 |
| `W1-UI-005` | Profile draft dirty | draft inputs and preview CTA | activation until preview/confirm | errors linked; 320px fields stack | preview / US-002 |
| `W1-UI-006` | Cut selector | segmented 15/20/25, 20 recommended | no guaranteed-loss wording | radiogroup/selected state | preview / US-002 |
| `W1-UI-007` | Preview loading/failure | stable result area; retry on error | confirm blocked | busy semantics; no flash | preview / US-006 |
| `W1-UI-008` | Normal preview | proposed calories/macros/nutrients, basis, start date | none after confirmation | summary announced, not auto-focused | preview / US-003-006 |
| `W1-UI-009` | 800-1200 | specialist-review-required Arabic explanation | activation; no bypass | textual block + focus to explanation | safety / US-003 |
| `W1-UI-010` | below 800 | stronger neutral safety block | activation/override | alert only on attempted activation | safety / US-003 |
| `W1-UI-011` | carb 100-<130 | calm reference info | not blocked | icon+text, not color-only | warning / US-005 |
| `W1-UI-012` | carb >0-<100 | stronger warning | not blocked | warning text includes visible grams | warning / US-005 |
| `W1-UI-013` | non-positive carb | settings revision prompt | save/activation | field group summary `macro_allocation` | 422 / US-005 |
| `W1-UI-014` | Protein basis | approved actual/adjusted Arabic explanation and Backend values | no client formula/control | definition list; long values wrap | protein object / US-004 |
| `W1-UI-015` | Pending plan | current plus scheduled start | scheduled not used early | labels distinguish current/scheduled | pending API / US-006 |
| `W1-UI-016` | Replace pending confirmation | old/new summary, replacement disclosure | submit until explicit confirm | modal named; trap/restore/Escape | replace API / US-007 |
| `W1-UI-017` | Replay success | original result, quiet completed state | duplicate effect absent | status message not repeated excessively | idempotency / US-017 |
| `W1-UI-018` | Key conflict/stale preview | re-preview action | activation | clear nontechnical Arabic intent | 409 / US-017 |
| `W1-UI-019` | Registry loading | compact skeleton where metadata needed | Registry-dependent create/activate | stable dimensions | Registry / US-008 |
| `W1-UI-020` | Registry unavailable | `تعذر تحميل البيانات الغذائية` + retry | no fabricated metadata | named error; retry 44px | Registry / US-008 |
| `W1-UI-021` | Registry incompatible | version incompatibility/support message | dependent mutations | status text and focus | Registry 409 / US-008 |
| `W1-UI-022` | Food exact nutrient | amount or `غير متوفر`; zero as `0` | no target % without target | dl/table semantics; units attached | Food / US-009 |
| `W1-UI-023` | Legacy DFE/RAE | `قيمة قديمة غير محددة المعيار` | no conversion/completeness credit | disclosure not color-only | Food / US-009 |
| `W1-UI-024` | Food classification edit | category, kind, status/completeness, contribution rows, traits | invalid total/duplicates | grouped controls; numeric errors | Food / US-010 |
| `W1-UI-025` | Legacy Food classification | unknown/unreviewed; explicit review CTA | no inferred selections | controlled fields start unselected/unknown | Food / US-010-012 |
| `W1-UI-026` | Source reliability | selected source + Backend Arabic reliability | reliability not editable | readonly description | Food / US-011 |
| `W1-UI-027` | Ingredients/NOVA | optional ingredients/source; NOVA 1-4/unknown + review status | no AI/hazard claim | radio/select labels; wraps at 320 | Food / US-012 |
| `W1-UI-028` | Diary entry logged | meal rows/totals update from response without full reload | no client snapshot fields | subtle reduced-motion-safe update | Diary / US-013 |
| `W1-UI-029` | Quantity/meal edit | updated aggregate; snapshot provenance unchanged | Food/date editing | touch targets and focus preserved | Diary PATCH / US-013 |
| `W1-UI-030` | Food deleted history | captured Food name/nutrition retained; source unavailable marker | editing source Food | no broken link semantics | Diary / US-016 |
| `W1-UI-031` | Versioned/legacy/no target | compact provenance label and appropriate target state | no target evaluation for no source | accessible description | summaries / US-014 |
| `W1-UI-032` | Empty day | `لا توجد أطعمة مسجلة لهذا اليوم` | no fake nutrient rows/progress | calm empty heading | summary / US-015 |
| `W1-UI-033` | All unknown nutrient | `غير متوفر`, coverage 0 | no zero/progress/remaining | full accessible sentence | aggregate / US-015 |
| `W1-UI-034` | Partial nutrient | `على الأقل [value]`, visible coverage | definitive remaining/available suppressed | qualifier in accessible name | aggregate / US-015 |
| `W1-UI-035` | Complete nutrient | exact amount, truthful target evaluation/progress | visual progress clamped only | progressbar real percentage | aggregate / US-015 |
| `W1-UI-036` | Integrity error | totals unavailable, retry/support action | numeric summary | alert with no cross-owner leak | 409 / US-013/015 |
| `W1-UI-037` | Hard delete confirmation | effect on Food vs retained Diary history | delete until confirmation | named modal/focus restore | delete / US-016 |
| `W1-UI-038` | Offline/network loss | online-only unavailable/retry | offline mutation/queue | no false saved state | network / all |

## 3. Nutrient Target-Type Presentation

- Minimum/recommended/adequate: complete coverage shows progress and remaining/met; partial only `met_at_least` when confirmed amount reaches target, otherwise indeterminate.
- Maximum: complete shows available/at/exceeded; partial only `exceeded_at_least` when confirmed amount exceeds limit.
- Range: complete below/within/above; partial only above-at-least when confirmed amount exceeds upper.
- Monitor-only: amount/qualifier, no progress.
- Minimize without number: amount/qualifier and minimize meaning, no fabricated allowance.
- Remaining/available never negative. Over-limit visual uses calm amber plus text.

## 4. Layout and Interaction Gates

At 320px, metadata and nutrient rows stack cleanly; no font below readable baseline. At 360-430px, compact wrapping preserves chevrons/actions. Sheets use max 92-96dvh, fixed header, internal scrolling, 22-24px top corners, drag handle, safe-area bottom, focus trap/restore, Escape, and reduced motion. These patterns apply only where existing app already uses sheets or the story requires a confirmation/detail overlay.

## 5. Physical Device Status

Real iPhone Safari, Android Chrome, dynamic browser bars, software keyboard, safe areas, touch scrolling, and sheet gestures are required release evidence but are `Pending` until implementation exists. This document does not claim they passed.

## 6. Deferred Scope

No Progress tab/UI, seven-day Analysis, recommendations, health score, clinical workflow, offline behavior, account/profile switching, direct gram/ml logging, or unrelated redesign.
