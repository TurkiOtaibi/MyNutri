# System Architecture — Services Breakdown

> Companion to SYSTEM_PLAN.md. Splits the system into **4 layers** based on the final approved stack. The data model and calc formulas live in SYSTEM_PLAN.md (unchanged).

---

## Final Stack (approved)

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLModel (SQLAlchemy) |
| Database | PostgreSQL |
| Frontend | Next.js + TypeScript + Base UI + Tailwind / CSS variables |
| PWA | Service Worker + IndexedDB (Dexie) + sync status + offline screens |
| Calc Engine | Python (pure functions, pytest) |
| Auth | single-user, minimal |

**Layer definitions (in brief):**
- **Infra** — where and how the system runs (hosting, DB, deployment, environments, CI/CD).
- **Backend** — the FastAPI app: API, ORM, auth (the shell that receives requests and returns data).
- **Frontend** — the Next.js PWA: UI, local storage, offline, sync.
- **Services** — the domain-service units that actually implement functionality. They live inside the backend codebase as a separate `services/` layer (the modular-monolith pattern from NutriPlan), and the backend calls them.

---

## Flow Overview

```
┌──────────────────────────────────────────────┐
│  Frontend  (Next.js PWA)                       │
│  UI · Dexie (offline cache) · Sync UI          │
└───────────────┬────────────────────────────────┘
                │  HTTPS / REST (JSON)
┌───────────────▼────────────────────────────────┐
│  Backend  (FastAPI)                             │
│  Routers · Pydantic Schemas · Auth · ORM        │
│         ── calls ──                             │
│  Services:  Calc · Food · Diary · Aggregation   │
└───────────────┬────────────────────────────────┘
                │  SQLAlchemy
┌───────────────▼────────────────────────────────┐
│  Infra:  PostgreSQL · Hosting · CI/CD           │
└──────────────────────────────────────────────┘

  Sync Service bridges both sides:  Dexie (front) ⇄ API (back)
```

---

## 1. Infra

Responsibility: running, deploying, and keeping the system alive.

- **Backend hosting** — run FastAPI via uvicorn inside a container (Render / Railway / Fly.io).
- **Managed PostgreSQL** — Supabase Postgres / Neon / Render Postgres. With connection pooling.
- **Frontend hosting** — Next.js on Vercel (best fit) or the same platform as the backend.
- **Migrations** — **Alembic** for schema changes (definitions live with the backend, run from CI/CD).
- **Environments** — dev / prod, secrets management (`DATABASE_URL`, secret keys) via env vars.
- **CI/CD** — GitHub → pipeline: lint + pytest + build + deploy.
- **Static assets** — PWA icons, the manifest, Arabic fonts.
- **Basic monitoring** — logging + error tracking (optional for a personal system, but useful).

---

## 2. Backend (FastAPI app)

Responsibility: the API shell — receives requests, validates, calls Services, returns JSON.

- **Routers / Endpoints** — REST, split by resource:
  - `/profile` — GET/PUT (read and update your stats + return computed targets).
  - `/foods` — GET/POST/PUT/DELETE (food catalog).
  - `/diary` — GET/POST/PUT/DELETE (records) + `/diary/week?start=` for the weekly table.
  - `/sync` — sync endpoints (push/pull).
- **ORM Models (SQLModel)** — `Profile`, `Food`, `DiaryEntry` (fields per SYSTEM_PLAN.md). `nutrition_snapshot` as JSONB.
- **Schemas (Pydantic)** — request/response DTOs + validation (e.g. core macros required, quantity > 0).
- **Persistence** — SQLAlchemy session management + a data-access layer (repositories).
- **Auth** — single-user, minimal: one account + token/session. Not a full auth service.
- **Alembic** — migration definitions live here.

> The Backend is deliberately **thin**: no business logic, just routing + validation + calling Services.

---

## 3. Frontend (Next.js PWA)

Responsibility: the Arabic RTL UI, working offline, and sync state.

- **UI Layer** — Next.js pages/components, Base UI + Tailwind, design tokens via CSS variables, native RTL.
- **Routing** — `/profile` · `/foods` · `/diary` (the weekly table is the home screen).
- **State / Data Fetching** — React Query (or SWR): caching, mutations, retries.
- **PWA Shell** — `manifest.json` + Service Worker (caches shell and assets) + install prompt + **offline screens**.
- **Local Store (Dexie)** — a local copy in IndexedDB of foods and records, for reading and logging offline.
- **Sync Status UI** — an indicator showing: synced / pending upload / offline.
- **Display logic** — progress bars for targets, remaining calculation, input forms + parallel validation.

---

## 4. Services (business logic)

The units that actually implement functionality. They live in `backend/services/`, and the routers call them.

**a) Calc Service (compute engine)** — *server (Python)*
- Input: profile stats. Output: targets (calories + macros).
- Logic: Mifflin-St Jeor → TDEE → goal adjustment → macro distribution (formulas in SYSTEM_PLAN.md).
- Pure functions, covered by pytest.

**b) Food Service** — *server*
- CRUD for foods + validation (core macros required, detail optional).
- Computes `net_carbs` on read.

**c) Diary Service** — *server*
- CRUD for records.
- **Snapshot logic**: on logging, copies the food's current per-serving values into `nutrition_snapshot`.
- Entry totals = snapshot × quantity.

**d) Aggregation Service (weekly rollup)** — *server + client mirror*
- Input: date range (Sun→Sat). Output: per-day totals + weekly total vs. targets.
- Simple (summation), so it is mirrored client-side over the Dexie cache to work offline.

**e) Sync Service** — *client + server*
- Bridges Dexie ⇄ API. Pushes mutations saved offline, pulls server updates when back online.
- Conflict resolution: last-write-wins (per the plan).

---

## Architectural Note — Offline Without Duplicating the Engine

In offline-first systems there's a temptation to duplicate the compute logic in TypeScript so it works without a network. **Avoid it** with this design:

- **Targets** are computed server-side (Python) and cached locally. They change rarely (only when you edit your stats), so the comparison works offline from the cache without duplicating the engine.
- **Daily aggregation** is just summation over Dexie records — trivial to mirror client-side safely.
- **The snapshot** makes each record carry its own nutritional values, so computing daily totals offline doesn't need the backend at all.

Result: the engine (the complex logic) stays in one place in Python, and only trivial summation is mirrored on the client. DRY + offline at the same time.

---

## Next Step

All layers and decisions are settled. Next deliverable: a **prompts file split across the seven phases** for Claude Code, each phase as an independent prompt that implements part of these layers in dependency order — see **CLAUDE_CODE_PROMPTS.md**.
