# UX, Mobile, RTL, and Accessibility Audit

Sources:
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `frontend/app/globals.css`
- `frontend/components/*.tsx`
- `frontend/public/manifest.json`
- `frontend/public/service-worker.js`

## BA Coverage Verdict

UX/mobile/RTL/a11y coverage is Partially Ready.

The BA package covers the major quality expectations:
- Arabic RTL shell.
- Required browser/device matrix.
- 360, 390, 430, 768, and desktop viewports.
- No horizontal scrolling for standard use.
- Usable touch targets.
- Keyboard not hiding critical actions.
- Mixed Arabic/English readability.
- Long food-name behavior.
- Accessible names for icon buttons.
- Field error associations.
- Confirmation dialog focus management.
- Status announcements.

## UX Gaps

| Gap ID | Area | Severity | Evidence | Issue | Recommended BA fix |
|---|---|---|---|---|---|
| UX-001 | Focus/error behavior | Medium | `US-A11Y-001`, `09_ACCEPTANCE_CRITERIA.md` | Uses "where practical" without minimum exception rules. | Define minimum focus behavior and allowed exceptions. |
| UX-002 | Fixed overlays | Medium | `globals.css`, `InstallPrompt`, `SyncStatus` | Current UI has fixed install/sync widgets; BA does not explicitly cover overlap/safe-area behavior. | Add safe-area and fixed-widget overlap criteria or remove sync widget from v1 scope. |
| UX-003 | Week grid horizontal scroll | Medium | `globals.css` uses `overflow-x: auto`; BA says no horizontal scrolling for standard use. | Clarify whether week grid horizontal scroll is acceptable or must adapt without scroll. |
| UX-004 | Dialog accessibility details | Low | BA requires keyboard accessible/focus return | Criteria do not specify focus trap, initial focus, Escape, or aria modal naming. | Add minimum dialog a11y criteria. |
| UX-005 | Reduced motion | Low | No motion requirements visible | No major animation exists, but requirement absent. | Add "no essential motion" or reduced-motion criterion if needed. |

## RTL and Arabic Text

BA coverage:
- HTML `lang=ar`, `dir=rtl`.
- Base UI DirectionProvider uses RTL.
- Mixed Arabic/English names must be readable.
- Long names truncate in list/card and show full in details/edit.

Current code alignment notes:
- `frontend/app/layout.tsx` sets `lang="ar"` and `dir="rtl"`.
- `frontend/components/Providers.tsx` uses `DirectionProvider direction="rtl"`.
- `.row-title` uses `overflow-wrap:anywhere`, but BA's two-line ellipsis rule is not implemented yet.

## Mobile Viewports

BA required viewports:
- 360px
- 390px
- 430px
- 768px
- Desktop

Current code evidence:
- Responsive grid collapses at 920px and 640px.
- Buttons have `min-height: 40px`.
- Main surface has mobile padding.

Implementation alignment risks:
- Week grid uses horizontal overflow.
- Fixed sync/install widgets can overlap content or each other.
- Keyboard-safe form actions are not verified.

## Accessibility

BA covered:
- Icon-only button accessible names.
- Field-level errors with `aria-invalid` and `aria-describedby`.
- Focus first invalid field where practical.
- Dialog keyboard access and focus return.
- Status regions.

Current code alignment risks:
- Icon buttons rely mostly on `title`, not explicit accessible labels.
- Field validation currently uses browser defaults and no custom error regions.
- Food archive and Diary delete dialogs do not exist yet.
- Sync status is visible but is future-scope for v1.
