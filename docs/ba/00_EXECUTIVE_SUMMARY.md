# myNutri current product requirements

## CURRENT versus APPROVED TARGET

The capabilities below describe the CURRENT repository implementation: Supabase email/password login and self-service email recovery, with read-only other-user nutrition monitoring. This is not proof of production deployment. The APPROVED TARGET, pending issues #110–#114, is internal username/password login with no Supabase Auth, no email anywhere, no MFA and no self-service recovery. Passwords have a backend-enforced minimum of 8. Five consecutive failures lock an account; an Admin reset unlocks a user and signs out all devices without forcing a new change, while the single Admin unlocks after 30 minutes. Successful login resets the counter. Force change only for the initial password. Own-password change in «بياناتي» requires the current password and signs out other devices. (Product Owner, 17 October 2026 AUT/PRF/USM decisions; BR-AUT-001/003/004/007–012, BR-PRF-024–026, BR-USM-023/030/033; V2 02.)

Admin correction of another user's «الجنس» is the sole CURRENT Profile-write exception, implemented in #109; other Profile fields, Diary, plans and Labs stay read-only. At the target cutover, delete all current test accounts/private data, keep Foods and recreate the single Admin through a server-side create/reset command. Username format and unspecified implementation details are **to be decided in issue #110**. (17 October 2026 PRF/USM/AUT/FOD decisions; BR-PRF-006, BR-USM-027/032/043/061/067/074; issue #100; V2 03/06.)


Status: supporting requirements. V2 Product and architecture documents remain authoritative.

## Product

myNutri is an Arabic-first, responsive, online-only nutrition application. Supabase
email/password authentication identifies a durable Backend Principal. Each Principal
owns private Profile, Target Plan, Diary, and idempotency data. Foods are a shared
global catalog.
Private LabResult facts form a standalone adult Labs domain interpreted using
the current immutable system catalog, independently of nutrition.

## User capabilities

- Sign in, recover/reset their own password, and sign out. Self-registration is
  retired; accounts are created only through Admin management.
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

The Admin-managed Supabase/email lifecycle above is CURRENT implemented behavior; the username-based replacement remains APPROVED TARGET. Its target copy and scope are separated in the field dictionary. (17 October 2026 AUT/USM decisions; BR-AUT-001, BR-USM-022/030/036; issue #100.)

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
