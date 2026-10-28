# myNutri current product requirements

## CURRENT versus APPROVED TARGET

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility until #114, not an authentication path. New users are created atomically by immutable username. No account conversion, destructive cutover, deployment or production configuration change is performed. Cutover #114 remains APPROVED TARGET. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043).

Admin correction of another user's «الجنس» is the sole CURRENT Profile-write exception, implemented in #109; other Profile fields, Diary, plans and Labs stay read-only. At the target cutover, delete all current test accounts/private data, keep Foods and recreate the single Admin through a server-side create/reset command. Username and credential/session details are CURRENT backend contracts in V2 02/11 (#110; 27 October 2026; BR-AUT-001/011/017). (17 October 2026 PRF/USM/AUT/FOD decisions; BR-PRF-006, BR-USM-027/032/043/061/067/074; issue #100; V2 03/06.)


Status: supporting requirements. V2 Product and architecture documents remain authoritative.

## Product

myNutri is an Arabic-first, responsive, online-only nutrition application. Internal
username/password browser authentication identifies a durable Backend Principal. Each Principal
owns private Profile, Target Plan, Diary, and idempotency data. Foods are a shared
global catalog.
Private LabResult facts form a standalone adult Labs domain interpreted using
the current immutable system catalog, independently of nutrition.

## User capabilities

- Sign in, change the initial password when required, change their own password
  from Profile using the current password, and sign out. Forgotten passwords go
  to the Admin; self-service recovery and self-registration are absent.
- Maintain the latest confirmed Profile inputs and preview calculated targets.
- Create immutable Target Plan revisions effective on Riyadh today or a future date.
- Read current, historical, and future-effective Target Plans by date.
- Browse, search, filter, sort, and inspect the Food catalog.
- Create, update, delete, and read Diary entries for past, current, or future dates.
- Read day/week nutrition totals, targets, and nutrient coverage.
- Browse the authenticated Labs catalog; read own overview, canonical detail/chart
  and complete history; create an atomic batch, edit date/value/unit and delete.
  Complete Profile and age >=18 on each result date are prerequisites.

## Admin capabilities

- The existing account/nutrition capabilities above; Labs is read-only even for
  the admin's own results, with additional selected-user overview/detail access.
- Add, edit, and permanently delete global Foods from the same `/foods` experience.
- Read user-monitoring pages without mutating another Principal's private data.
- Create normal-user accounts with Admin-set initial passwords; edit display
  names, reset passwords, enable/disable, and permanently delete those accounts
  through the separate account-management surface. Exactly one Admin exists;
  the Admin cannot disable/delete self or change roles. Interrupted creation or
  deletion remains locked out and resumable. Global Foods survive user deletion.

The Admin UI creates internal users by immutable username in #112; internal login/Profile UI is CURRENT in #111. Provider authentication/lifecycle removal is CURRENT #113. Historical existing-account display/deletion fallback remains until the APPROVED TARGET cutover #114. Current copy and scope are recorded in the field dictionary (27 October 2026; BR-USM-022/023/025/036/038/042). (17 October 2026 AUT/USM decisions; BR-AUT-001, BR-USM-022/030/036; issue #100.)

Deleting a Food permanently deletes every referencing Diary entry across all
Principals. This is intentional and has no archive, restore, tombstone, or audit event.

## Current boundaries

- Profile is latest confirmed input/preferences; it is not historical target truth.
- TargetPlan is immutable dated calculated output.
- DiaryEntry retains consumed measurement facts and an optional historical TargetPlan binding.
- Food nutrition is current catalog truth; Diary totals join the current Food row.
- Optional nutrient unknown is null, never zero.
- The Nutrition Registry and integrity hashes remain; semantic Nutrition versions do not.
- The PWA is a static shell. Personal API data is not cached for offline authority and mutations are not queued.
- Labs stores entered facts, not Status/reference/canonical interpretation. Fresh
  reads apply current rules and accepted DOB. Sex is locked to its owner after first Profile
  save, with the sole Admin correction exception (17 October 2026; BR-PRF-006, BR-USM-032/061; #109); DOB cannot invalidate stored adult history. There is no nutrition effect,
  browser personal-data persistence, polling, API caching or offline mutation queue.

## Explicitly absent

Day completion/reopen status, Target Plan lifecycle labels, pending plans, legacy
Target fallback, Food Archive/Restore, a second Admin Food UI, Sync APIs/queues,
Food V3 schema aliases, uncategorized sentinels, and `/admin/foods` do not exist.
Labs excludes custom tests/units/ranges/panels, editable medical catalogs, admin
medical editing, diagnosis/treatment/emergency claims, export/sharing, pregnancy
interpretation, automatic biomarkers and nutrition integration.
