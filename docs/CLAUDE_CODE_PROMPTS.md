# Claude Code Phase Prompts

These prompts split the myNutri build into the seven dependency-ordered phases from the system plan.

## Phase 0 - Setup

Create a monorepo for a personal Arabic-first RTL nutrition PWA. Scaffold:

- `backend/`: FastAPI, SQLModel, Alembic, PostgreSQL configuration, pytest, ruff.
- `frontend/`: Next.js, TypeScript, Tailwind CSS variables, Base UI, RTL layout.
- Root files: README, `.env.example`, Docker Compose for PostgreSQL, CI workflow.

Keep auth single-user and minimal. Do not add roles, tenants, recipes, barcode scanning, public food APIs, micronutrients, historical targets, or meal types.

## Phase 1 - Profile And Calc

Implement the `profile` table as a single-row resource. Add a pure Python calc service using Mifflin-St Jeor:

- BMR by sex.
- TDEE by activity factor.
- Goal adjustment for cut, maintain, bulk.
- Macros from protein per kg and fat percentage.
- Clamp negative carb calories to zero and expose a flag.

Add pytest coverage for the documented example and edge cases. Add `/profile` GET/PUT and `/profile/preview`. Build `/profile` with Arabic RTL inputs and live targets.

## Phase 2 - Food Catalog

Implement `food` CRUD with required serving/core macro fields and optional detail fields. Compute `net_carbs_g` on read as `carb_g - fiber_g`; do not store it. Build `/foods` with list, search, add, edit, delete, and detail view. Use a collapsible details section for optional fields.

## Phase 3 - Diary Logging

Implement `diary_entry` with `entry_date`, `food_id`, decimal `quantity`, and `nutrition_snapshot`. On log creation, copy the food's current per-serving values into the snapshot. Entry totals must be `snapshot * quantity`. Deleting or editing a food must not corrupt historical diary totals.

Build day view in `/diary`: logged foods, totals, remaining calories, and progress bars against current targets.

## Phase 4 - Weekly View

Add an aggregation service for Sunday-to-Saturday weekly summaries. The week must be a query result, not a stored entity. Build the `/diary` home screen with week selector, per-day calorie totals vs target, and selectable day details.

## Phase 5 - PWA And Offline Reads

Add `manifest.json`, service worker shell caching, install-ready icons, offline screen, and Dexie stores for cached profile, foods, and diary entries. Cache server-computed targets locally. Mirror only simple daily/weekly summation on the client; do not duplicate the calc engine in TypeScript.

## Phase 6 - Offline Writes And Sync

Add a Dexie mutation queue and sync status UI. Client-generated UUIDs must make offline creates replayable. Implement `/sync/push` and `/sync/pull`; push queued mutations in creation order and then pull server state. Use last-write-wins semantics by applying queued operations in order, so later operations for the same resource overwrite earlier ones. Make replay idempotent so retrying the same batch does not duplicate foods or diary entries.
