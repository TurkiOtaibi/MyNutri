# myNutri current product requirements

Status: supporting requirements. V2 Product and architecture documents remain authoritative.

## Product

myNutri is an Arabic-first, responsive, online-only nutrition application. Supabase
email/password authentication identifies a durable Backend Principal. Each Principal
owns private Profile, Target Plan, Diary, and idempotency data. Foods are a shared
global catalog.

## User capabilities

- Sign up, sign in, recover/reset a password, and sign out.
- Maintain the latest confirmed Profile inputs and preview calculated targets.
- Create immutable Target Plan revisions effective on Riyadh today or a future date.
- Read current, historical, and future-effective Target Plans by date.
- Browse, search, filter, sort, and inspect the Food catalog.
- Create, update, delete, and read Diary entries for past, current, or future dates.
- Read day/week nutrition totals, targets, and nutrient coverage.

## Admin capabilities

- Everything available to a normal user.
- Add, edit, and permanently delete global Foods from the same `/foods` experience.
- Read user-monitoring pages without mutating another Principal's private data.

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

## Explicitly absent

Day completion/reopen status, Target Plan lifecycle labels, pending plans, legacy
Target fallback, Food Archive/Restore, a second Admin Food UI, Sync APIs/queues,
Food V3 schema aliases, uncategorized sentinels, and `/admin/foods` do not exist.
