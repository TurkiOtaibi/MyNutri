# Current user stories and acceptance criteria

Status: supporting requirements. V2 authority and executable tests control conflicts.

## Authentication and isolation

- As a user, I can authenticate through Supabase and access only my private resources.
- As an Admin, I can monitor users read-only without gaining a cross-owner mutation path.
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

- As a user, I can create, update, delete, and read my Diary entries for past, current, or future dates.
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
