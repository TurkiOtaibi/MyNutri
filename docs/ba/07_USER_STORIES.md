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

## Experience

The application remains Arabic-first and RTL, keyboard/focus accessible, responsive at supported mobile and desktop sizes, online-only for personal data, and a static-shell PWA without API caching or mutation queues.
