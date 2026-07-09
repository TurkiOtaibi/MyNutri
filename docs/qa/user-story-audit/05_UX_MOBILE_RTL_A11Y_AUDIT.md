# UX, Mobile, RTL, and Accessibility Audit

Source files:
- `docs/ba/07_USER_STORIES.md`
- `docs/ba/08_NEGATIVE_SCENARIOS.md`
- `docs/ba/09_ACCEPTANCE_CRITERIA.md`
- `frontend/app/layout.tsx`
- `frontend/components/*.tsx`
- `frontend/app/globals.css`

Overall verdict: Partially Ready.

The app has meaningful Arabic RTL and responsive foundations, but the BA stories are not yet precise enough for full UI, mobile, and accessibility test generation.

## Confirmed UX/RTL Evidence

| Area | Evidence | Confidence |
|---|---|---|
| Arabic document language and RTL | `frontend/app/layout.tsx` uses `lang="ar"` and `dir="rtl"` | High |
| RTL provider | `frontend/components/Providers.tsx` uses `DirectionProvider direction="rtl"` | High |
| Arabic navigation labels | `frontend/components/AppNav.tsx` | High |
| Responsive CSS | `frontend/app/globals.css` includes responsive layout rules | High |
| Icon buttons have some accessible naming | Icon buttons use `title` values in several components | Medium |
| Progress bar exposes percent text through `aria-label` | `frontend/components/ProgressBar.tsx` | Medium |

## UX and State Gaps

| ID | Area | Severity | Gap | Evidence | Recommended update |
|---|---|---|---|---|---|
| UX-001 | Loading states | High | Loading states are inconsistent and not defined per page/operation. | `DiaryPage` has "loading week"; Food/Profile states are weak | Add page-specific loading criteria. |
| UX-002 | Empty states | Medium | Empty food catalog exists but add-food action and wording are not fully specified. | `FoodsPage` empty state | Define empty catalog UI and primary action. |
| UX-003 | No-results state | Medium | Search no-results must be distinct from empty catalog, but current UI uses the same empty message. | `US-FOOD-HAPPY-002`, `FoodsPage` | Add no-results story/copy. |
| UX-004 | Error states | High | API/network/server validation error states are broad and not mapped to UI placement. | `US-NETWORK-ERROR-001` | Split into page/form-level error stories. |
| UX-005 | Success feedback | Medium | Notes exist, but offline-sync success messages contradict v1. | `ProfilePage`, `FoodsPage`, `DiaryPage` | Replace local-sync messages with online-only save/failure copy. |
| UX-006 | Delete confirmation | Critical | Food delete has no confirmation; diary delete also lacks a decision. | Delete buttons in `FoodsPage`, `DiaryPage` | Add confirmation or undo requirements. |
| UX-007 | Required fields | Medium | Required fields are not consistently obvious beyond HTML required. | Form components | Define required indicators and validation timing. |
| UX-008 | Form density | Medium | Food form has many fields visible at once; collapsible detail section is planned but not strongly specified. | `FoodsPage` optional detail section currently always visible | Decide collapsible optional nutrients behavior. |

## Mobile-First Gaps

| ID | Area | Severity | Gap | Recommended update |
|---|---|---|---|---|
| MOB-001 | Safe area | High | Safe-area behavior for install prompt, sync/status widgets, and bottom spacing is not specified. | Add iPhone Safari/PWA safe-area acceptance criteria. |
| MOB-002 | Keyboard behavior | Medium | Number/date/select keyboard behavior is not covered by stories. | Add mobile keyboard and focus criteria for forms. |
| MOB-003 | Touch targets | Medium | Minimum touch target size is not specified. | Define minimum target size for icon and submit buttons. |
| MOB-004 | Fixed widgets | High | `SyncStatus` fixed widget is future-scope and can overlap content. | Remove/hide for v1 or define replacement connection banner. |
| MOB-005 | Long text | Medium | Long mixed Arabic/English food names are mentioned but not testable enough. | Define wrap/truncate behavior and visual regression case. |
| MOB-006 | Horizontal scrolling | Medium | Acceptance says no horizontal scrolling, but not per page/card/form. | Add per-page responsive examples. |

## RTL and Localization Gaps

| ID | Area | Severity | Gap | Recommended update |
|---|---|---|---|---|
| RTL-001 | Arabic error copy | High | Field-level Arabic errors are missing. | Create exact Arabic message matrix. |
| RTL-002 | Mixed text | Medium | Mixed Arabic/English/numbers in food names and units is not fully specified. | Add wrapping/direction criteria. |
| RTL-003 | Icon direction | Low | Direction-sensitive icons are not explicitly reviewed. | Add visual check for previous/next/week controls. |
| RTL-004 | Placeholder direction | Low | Placeholder localization is partial. | Confirm Arabic-first placeholders for all text fields. |

## Accessibility Gaps

| ID | Area | Severity | Gap | Evidence | Recommended update |
|---|---|---|---|---|---|
| A11Y-001 | Icon-only buttons | High | `title` is used, but explicit `aria-label` is not consistently required. | Icon buttons in `FoodsPage`, `DiaryPage`, `SyncStatus` | Require accessible names for icon-only controls. |
| A11Y-002 | Field errors | High | `aria-invalid`, `aria-describedby`, and field-level error association are not specified. | Forms lack custom error components | Add field error a11y acceptance criteria. |
| A11Y-003 | Focus management | High | Focus-first-invalid and focus after dialog/error are undefined. | `US-A11Y-001` broad | Add focus criteria. |
| A11Y-004 | Live status | High | Connection/loading/error status is not specified with `aria-live`. | Network error requirements | Add live region behavior. |
| A11Y-005 | Keyboard-only flows | Medium | Keyboard operation for detail toggles, confirmation, and navigation is not explicitly tested. | Component buttons/selects | Add keyboard QA scenarios. |
| A11Y-006 | Dialog accessibility | High | Delete confirmation is required but no dialog a11y behavior exists. | Food delete/archive story | Define focus trap, labels, escape/cancel behavior. |

## Recommendation

Do not generate final mobile/a11y QA test cases until:
1. Online-only connection error UI is designed.
2. Delete confirmation UI pattern is selected.
3. Field-level Arabic validation messages and a11y semantics are defined.
4. Fixed sync/offline status UI is removed or future-scoped from v1.

