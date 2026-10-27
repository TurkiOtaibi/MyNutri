# Current user stories and acceptance criteria

## Approved stories and current delivery boundary

CURRENT in #111: the browser uses internal username/password login, opaque bearer sessions, forced initial-password change, and own-password change in Profile. Only the session token is persisted in localStorage; passwords stay in memory and no auth cookies are used. Reload during an initial-password change requires re-authentication. Forgotten/reset-password browser flows are absent; forgotten passwords go to the Admin. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; an internal password hash takes precedence and rejects JWT admission with `INTERNAL_LOGIN_REQUIRED`. Internal password changes/resets never update Supabase. Admin username-based creation and management UI is CURRENT in #112: new users have internal credentials only, with no email or provider call. Legacy backend email/provider lifecycle support and clearly marked email fallback for existing accounts remain until #113/#114; provider/email removal (#113) and destructive cutover (#114) remain APPROVED TARGET. No existing account migration or cutover is performed. This describes repository implementation, not deployment. (Product Owner decisions of 17 and 27 October 2026; issues #110/#111/#112; BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054; BR-AUT-001/003/004/005/007/008/010/011/012/017, BR-PRF-024–026, BR-USM-030/033.)

| Target story / acceptance | BRD authority, 17 October 2026 | Delivery |
|---|---|---|
| Sign in with «اسم المستخدم» and password inside the system; no Supabase Auth, email, MFA or self-service recovery; forgotten passwords go to the Admin. | AUT/USM decisions; BR-AUT-001/003/012 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112; provider removal pending #113 |
| Enforce minimum length 8 on the backend and require changing only the initial Admin-set password before using the system. | BR-AUT-004/007/008, BR-USM-023 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Lock after 5 consecutive failures; Admin reset alone unlocks a normal user without forced change; Admin auto-unlocks after 30 minutes; success resets the counter. No independent unlock action. | Final AUT/USM decisions; BR-AUT-011, BR-USM-030 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Change my own password in «بياناتي» using the current password; other devices sign out. Admin reset signs the user out everywhere. | BR-PRF-024–026, BR-USM-030/033 | Backend CURRENT #110; login/Profile UI CURRENT #111; Admin UI CURRENT #112 (27 October 2026) |
| Replace current test accounts/private data at cutover, preserve Foods and create the single Admin with a server-side command also able to reset its password. | AUT/USM/FOD cutover decisions; related BR-USM-027/043; issue #100 command requirement | #114 |

Username identity is 3–32 ASCII English letters, digits, `.`, `_`, or `-`, with a unique lowercase normalized value. Passwords use standard-library scrypt with a random per-password salt; sessions use opaque random bearer tokens in the Authorization header, store only SHA-256 token hashes on the backend, and use no cookies; the browser persists only the raw session token in localStorage (#111). The Product Owner approved the 30-day sliding inactivity expiry for #111 on 27 October 2026. Existing accounts retain null internal credentials unless the explicitly authorized existing-Admin attach command is run. These details replace the former “to be decided in issue #110” placeholders. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

## CURRENT implementation stories


Status: supporting requirements. V2 authority and executable tests control conflicts.

## Authentication and isolation

- As a user, I can authenticate with my internal username/password and access only my private resources.
- As an Admin, I can monitor users read-only and correct only «الجنس» on another
  active/disabled user with a saved Profile, with the approved warning. Owner sex
  locking and stored plans/Diary/Labs remain unchanged; new plan saves and fresh
  Labs evaluations use the correction. (17 October 2026 decision; BR-PRF-006, BR-USM-032/061; issue #109.)
- Missing/invalid credentials return 401; authenticated unauthorized mutations return 403; cross-owner private-resource lookup remains non-enumerating.

Acceptance: direct API calls enforce the same authorization as the UI; frontend hiding is not an authorization boundary.

## Profile and targets

- As a user, I can edit confirmed inputs, preview calculated targets, and save a plan effective today or later.
- As a user, I can retain multiple future effective points and revise a same-date point without destroying history.
- As a user, I see null targets when no plan applies; Profile does not silently substitute.
- Blocked safety outcomes remain visible but cannot open confirmation, submit, acknowledge, or override.

Acceptance: reads cause no lifecycle writes; revisions are immutable; stale preview/manifest hashes fail; idempotent replay cannot create duplicates; past effective dates are rejected.

## Foods

- As any authenticated user, I can browse, search, filter, sort, paginate, inspect, and select Foods from `/foods`.
- As an Admin, I additionally see Add, Edit, and Delete in that same experience.
- As a normal user, I cannot see mutation controls and direct mutation calls return 403.
- As an Admin deleting a Food, I receive the exact governed irreversible/cross-user warning.

Acceptance: `GET /foods` is always paginated; there is no `/admin/foods`, archive state, restore action, V3 schema alias, bare-array response, or uncategorized sentinel. Successful delete returns 204 and atomically cascades all referencing Diary rows across Principals while preserving unrelated Diary rows and Target Plans.

## Diary

- As a user, I can create Diary entries for past dates without limit and through Asia/Riyadh today + 7 days (BR-DRY-028). Reading, updating, and deleting existing entries keep their current rules.
- As a user, I see recorded measurement context even after serving-default edits.
- As a user, I see day/week totals calculated from current Food nutrition and consumed measurement.
- As a user, I see date-specific targets where a canonical TargetPlan exists and an explicit no-target state otherwise.

Acceptance: ownership is Principal-scoped; Food/TargetPlan references are valid; past TargetPlan bindings are immutable; today/future eligible bindings can be canonically rebound; client UUID replay is safe; Food deletion removes affected entries from totals, recency, and Admin monitoring without persisted aggregate repair.

## Registry and nutrition

- As a user, I receive Registry-defined Arabic labels, units, ordering, taxonomy, target types, and nullable nutrient semantics.
- As a user, I can distinguish unknown from known zero and incomplete coverage from complete evaluation.

Acceptance: malformed or duplicate Registry definitions fail closed; the manifest hash/lock detect content drift; semantic version fields are absent.

## Labs ownership and catalog

- As an authenticated actor, I can browse exactly 51 approved tests, 15 categories
  and 7 selection panels without editing the medical catalog.
- As an owner, I can see my overview and full detail/history, create an atomic
  batch, edit date/value/unit only, and physically delete a result.
- As an owner, I retain original entered facts for editing while list/chart/history
  show canonical values, current Status and age-aware system reference zones.
- As an owner, I receive fresh current-rule interpretation after a rule or accepted
  DOB change without a write to my recorded facts.

Acceptance: exact decimal conversion/comparison precedes display rounding; each
response uses one current catalog version. Owner/test/date is unique. No partial
batch or failed receipt persists. Same key/body returns the ID-only success receipt
after edit/delete/rule changes without recreating rows; changed scale/unit/body is
409. Latest `test_date` and latest remaining update activity are separate, all five
sorts preserve that distinction, and final deletion removes the owned row while
the test remains in the catalog. Full history supplies every chart point.

## Labs demographics, authorization and privacy

- As an owner, I use Profile sex/DOB without entering them again in Labs; each
  result must be at least age 18 on its test date.
- As a Profile owner, I cannot change sex after first successful save or change
  DOB so existing Labs history becomes pre-adult. Rejection changes neither
  Profile, Target Plan nor Labs; accepted DOB changes reinterpret unchanged facts.
- As an admin, I read own and selected-user Labs but cannot create/edit/delete,
  including my own results. Another user's result ID remains non-enumerating.

Acceptance: the backend derives ownership, rejects owner/test identity changes,
returns 403 for every admin write and 404 for cross-owner IDs, and rechecks active
actor/role under the Principal lock before replay. No medical values appear in
URLs/logs/browser storage. Labs CRUD leaves Profile/TargetPlan/Diary/Food facts
and nutrition calculations unchanged. Existing Profile nutrition age rules remain.

## Labs experience acceptance

The existing top navigation adds `التحاليل` and retains every destination. Owner
overview/add/detail/edit and admin overview/detail provide six views. Panel and
individual selection deduplicates, blank rows are omitted, explicit zero remains,
and at least one populated row is required. A fresh session resets defaults;
the announced save count matches submitted rows. No Status appears before save.
Errors preserve draft/date/unit and focus the relevant field; ambiguous POST
retains the same actor-scoped payload/key and permits only same-command retry.
Confirmed success/replay refreshes current data by GET without resending a write.

Arabic/RTL, 320/390/430 layouts, keyboard chart navigation, accessible text plus
color, modal focus containment/restoration, reduced motion and full readable
history are required. Account/selected-subject changes discard stale responses
and volatile state; same-subject navigation preserves active current queries.
There is no polling, personal browser persistence, service-worker API cache or
offline mutation queue. The offline destination is only the generic static shell.

## Shared experience

The application remains Arabic-first and RTL, keyboard/focus accessible, responsive at supported mobile and desktop sizes, online-only for personal data, and a static-shell PWA without API caching or mutation queues.


CURRENT backend proof for #110: `test_internal_credentials.py` covers format/hash validation; `test_internal_auth.py` covers login/locks, forced change, session revocation/expiry, internal-over-JWT precedence, separate credentials, Admin command and migration round-trip. Browser login, forced initial change and own-password change are implemented in #111; Admin username-management UI is CURRENT in #112; provider removal/cutover remains pending #113/#114 (BR-USM-005/006/013/014/022/023/025/036/038/042/054). Browser coverage is in internal-session unit tests and authentication/Profile Playwright tests. Tests prove repository behavior, not deployment. (17/27 October 2026; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

CURRENT #112 acceptance: username creation is atomic and provider-free; duplicate normalized usernames and conflicting idempotency replays are rejected. Username is immutable, search is literal/case-insensitive, lock filter/badge and last-login dates are exposed, reset signs out all sessions and unlocks, and username-confirmed deletion scrubs the tombstone while preserving Food attribution and permitting username reuse. Legacy account email fallback and provider sagas remain pending #113/#114; no migration/cutover is performed. Authority: BR-USM-005/006/012/013/014/022/023/025/030/036/038/042/043/049/054, final USM decision table (17 October 2026), and [PO decision (27 October 2026)](https://github.com/TurkiOtaibi/MyNutri/issues/112#issuecomment-6437936388).
