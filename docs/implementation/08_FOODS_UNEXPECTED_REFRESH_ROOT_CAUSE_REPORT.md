# Foods Unexpected Refresh Root Cause Report

Date: 2026-07-10
Scope: Add Food route `/foods/new`
Environment: Next.js development server accessed through LAN address `192.168.100.9`

## 1. Exact Root Cause

The reset was caused by the Next.js development server rejecting its HMR WebSocket when the frontend was opened through the computer's LAN IP.

The server was bound to `0.0.0.0`, but `next.config.mjs` did not define `allowedDevOrigins`. Next.js therefore blocked `192.168.100.9` from the development resource `/_next/webpack-hmr`. The browser repeatedly retried the failed HMR connection. After approximately 44 seconds, the Next development client performed a full document reload of `/foods/new`. The URL remained visually unchanged, but the browser document and React component were recreated, so all in-memory form state returned to `emptyFoodForm`.

This was a development-origin configuration failure, not a Food form reset, API response, service worker, validation, or draft-storage defect.

## 2. How It Was Reproduced

### Before the fix

Playwright opened `http://192.168.100.9:3000/foods/new`, filled multiple basic and nutrition fields, marked the current document and form node, and waited 65 seconds.

Observed evidence:

- Repeated console errors for `ws://192.168.100.9:3000/_next/webpack-hmr` with `ERR_INVALID_HTTP_RESPONSE`.
- Next server warning: cross-origin access to the HMR resource was blocked and `192.168.100.9` needed to be added to `allowedDevOrigins`.
- At about 44 seconds, `beforeunload` fired.
- A second document GET requested `/foods/new`.
- The document ID changed.
- The marked form node disappeared.
- All entered values became empty.

### After the fix, backend running

The same LAN browser scenario ran for 65 seconds with multiple fields populated and Optional nutrients open.

Result:

- URL unchanged.
- No additional document request after setup.
- No unexpected navigation after setup.
- Same document ID.
- Same form node.
- All values retained.
- Optional nutrients remained open.
- Editing continued successfully after the wait.
- No HMR WebSocket error.

### After the fix, backend stopped

The backend process was stopped, the LAN Add Food form was populated, and the browser remained idle for 65 seconds.

Result:

- Same document ID and form node.
- URL unchanged.
- No reload or additional document request.
- Existing values remained and another field could be edited after the wait.

### Failure and interaction scenarios

Automated tests also verified aborted create requests, validation errors, Optional nutrient toggling, form button types, and successful-save navigation.

## 3. Investigation Findings

| Investigated path | Finding |
|---|---|
| `router.refresh()` | Not present in the Add Food flow. |
| Unexpected `router.push()` / `replace()` | Create mode calls `router.push` only in the successful create mutation callback. |
| `window.location.reload()` | Not present. |
| Form submit | `preventDefault()` is called before validation or mutation. |
| Button types | Save is the only submit button. Edit-only Delete explicitly uses `type="button"`; Cancel and Back are links. |
| React keys | No changing page/form key causes remount. |
| Form-reset effects | The only `setForm` effect consumes Food detail data in edit mode. Its query is disabled for create mode. |
| Unstable effects | No create-mode effect resets state. |
| API error handling | Errors update messages only and preserve form state. |
| Service worker | It does not cache or intercept `/foods/new`, and no `controllerchange` handler reloads the page. Not causal. |
| Next Fast Refresh | HMR was blocked for the LAN origin; the reconnect fallback caused the full reload. |
| Duplicate dev servers | One frontend listener was present on port 3000 during reproduction. |
| Parent providers/layout | Provider identity is stable and no changing key remounts the page. |
| Initial values | `emptyFoodForm` is used only for initial component state, not reapplied during create mode. |
| Loading/error boundaries | No route-level boundary replaced `/foods/new`. |
| Hydration/runtime errors | No application runtime error caused the reproduced reload. |

## 4. Files Changed

- `frontend/next.config.mjs`
- `frontend/playwright.config.ts`
- `frontend/e2e/foods/stability.spec.ts`
- `docs/implementation/08_FOODS_UNEXPECTED_REFRESH_ROOT_CAUSE_REPORT.md`

No BA files, QA test-case definitions, backend business logic, database schema, migrations, or Food product decisions were changed.

## 5. Fix Implemented

`next.config.mjs` now discovers the computer's active non-loopback IPv4 interface addresses and supplies them to Next.js as `allowedDevOrigins`. Additional development origins can be supplied through the comma-separated `NEXT_ALLOWED_DEV_ORIGINS` environment variable.

This keeps the HMR WebSocket valid when the development app is opened from another device on the same network. It removes the failed reconnect cycle that triggered the full document reload.

The Playwright local-target guard was updated to permit only addresses currently assigned to this computer, allowing the regression test to execute against the LAN origin without permitting production targets.

No form draft persistence was used to mask the issue.

## 6. Tests Added

`frontend/e2e/foods/stability.spec.ts` adds six automated scenarios:

1. Populated form remains on the same document and form node for at least 60 seconds, with no new navigation/reload.
2. Failed create request preserves all entered fields.
3. Opening and closing Optional nutrients preserves the form.
4. Save is the only submit control; Back and Cancel are explicit links.
5. Validation errors preserve entered values.
6. Successful Save is the only tested path that leaves and clears the form.

The backend-stopped 65-second scenario was executed separately with lifecycle instrumentation because stopping the shared backend inside the permanent parallelizable test suite would make unrelated tests unsafe.

## 7. Test Results

| Check | Result |
|---|---|
| Pre-fix LAN reproduction | Reproduced full reload and reset at about 44 seconds |
| Post-fix LAN idle/Optional nutrients, 65 seconds | Passed |
| Post-fix backend stopped, 65 seconds | Passed |
| Targeted stability Playwright tests | 6 passed |
| Full Foods Playwright suite over LAN dev origin | 157 passed |
| Frontend typecheck | Passed |
| Frontend production build | Passed |

## 8. Draft Persistence

Draft persistence was **not added**. It is not necessary for the confirmed defect. The form remains stable after correcting the development-origin/HMR configuration.

## 9. Remaining Risks

- If the computer changes networks and receives a new LAN address while the Next dev server is already running, restart the dev server so `allowedDevOrigins` is recalculated.
- Intentional source-code edits during development can still invoke normal Fast Refresh behavior. This is distinct from the periodic failed-HMR reload fixed here and does not occur in the production build.
- The service worker remains shell-only. It was not causal and does not intercept `/foods/new`.
