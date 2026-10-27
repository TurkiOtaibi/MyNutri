# myNutri current product requirements

## CURRENT versus APPROVED TARGET

CURRENT in #111: the browser uses internal username/password login, opaque bearer sessions, forced initial-password change, and own-password change in Profile. Only the session token is persisted in localStorage; passwords stay in memory and no auth cookies are used. Reload during an initial-password change requires re-authentication. Forgotten/reset-password browser flows are absent; forgotten passwords go to the Admin. The backend retains legacy Supabase JWT admission for accounts without internal credentials until #113; an internal password hash takes precedence and rejects JWT admission with `INTERNAL_LOGIN_REQUIRED`. Internal password changes/resets never update Supabase. Admin email-based creation UI/API remains CURRENT until #112; provider/email removal (#113) and destructive cutover (#114) remain APPROVED TARGET. This describes repository implementation, not deployment. (Product Owner decisions of 17 and 27 October 2026; issues #110/#111; BR-AUT-001/003/004/005/007/008/010/011/012/017, BR-PRF-024–026, BR-USM-030/033.)

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

The Admin-managed Supabase/email creation UI/API remains CURRENT until #112; internal login/Profile UI is CURRENT in #111, while username-based Admin UI/provider removal/cutover remains APPROVED TARGET (27 October 2026; BR-AUT-001/017). Its target copy and scope are separated in the field dictionary. (17 October 2026 AUT/USM decisions; BR-AUT-001, BR-USM-022/030/036; issue #100.)

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
