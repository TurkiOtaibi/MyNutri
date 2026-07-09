# System Build Plan — Personal Nutrition Tracker

> Planning document, ready to hand to Claude Code. Goal: a personal single-user PWA that computes daily targets and tracks food intake against them.

---

## 1. Overview & Scope

A single-user web/PWA app (for you only), Arabic-first RTL. Three modules:

1. **Profile & Targets** — you enter your stats; the system computes your calorie + macro needs.
2. **Food Catalog** — a food catalog you populate manually (CRUD).
3. **Diary / Log** — you log what you ate each day and see a weekly table (Sun → Sat) comparing consumed vs. target.

**Key upfront point:** since the system is for you alone, auth is minimal — no multi-tenancy, no roles, no sharing. This removes significant complexity from the start; we don't build what we don't need.

---

## 2. Architecture & Tech Stack (approved)

Final decision — offline-first PWA:

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + SQLModel (SQLAlchemy) |
| Database | PostgreSQL |
| Frontend | Next.js + TypeScript + Base UI + Tailwind / CSS variables |
| PWA | Service Worker + IndexedDB (Dexie) + sync status + offline screens |
| Calc Engine | Python (pure functions, pytest) |
| Auth | single-user, minimal |

The detailed layer breakdown (Infra / Backend / Frontend / Services) is in **ARCHITECTURE_SERVICES.md**.

---

## 3. The Three Modules

**Module A — Profile & Targets**
- Stores a single row with your stats.
- Owns the **Calc Engine**: converts stats → needs (calories + macros).
- Targets are derived from current stats (computed on demand), not a stored table.

**Module B — Food Catalog**
- The single source of truth for food values.
- Each food defines its own serving + nutritional values per serving.
- Full CRUD: add / edit / delete / detail.

**Module C — Diary / Log**
- Each record = date + food + quantity (in servings).
- **The weekly table is not a stored entity** — it's a query/aggregation over records by date. Do not build a "week" entity.

---

## 4. Data Model

Three tables only.

### `profile` (single row)
```
id                uuid (pk)
sex               enum('male','female')      -- affects BMR
birth_date        date                        -- age derived automatically
height_cm         numeric
weight_kg         numeric
activity_level    enum(...)                   -- see activity factors below
goal              enum('cut','maintain','bulk')
protein_per_kg    numeric  default 1.8        -- adjustable 1.6–2.2
fat_pct           numeric  default 0.25       -- fat share of calories 0.20–0.30
updated_at        timestamptz
```
> Targets (target_calories/protein/carb/fat) are **not stored** — computed from this row on demand, so they always match your current stats.

### `food` (the catalog)
```
id                uuid (pk)
name              text
serving_label     text        -- serving description: "15 g" / "piece" / "loaf" / "plate"
serving_grams     numeric?    -- optional: grams per serving (if you want weight tracking)

-- Core (required; have targets + feed the weekly comparison):
calories          numeric
protein_g         numeric
carb_g            numeric
fat_g             numeric

-- Detail (optional; displayed as totals, no targets):
saturated_fat_g   numeric?
trans_fat_g       numeric?
cholesterol_mg    numeric?
sodium_mg         numeric?
fiber_g           numeric?
total_sugars_g    numeric?
added_sugar_g     numeric?

created_at        timestamptz
updated_at        timestamptz
```
> **net_carbs** = `carb_g − fiber_g` — a **computed** field (not stored). Useful for keto tracking.
> All values are **per single serving**, matching the label directly.

### `diary_entry` (the log)
```
id                 uuid (pk)
entry_date         date
food_id            uuid (fk → food)   -- for display and linking
quantity           numeric             -- number of servings, allows decimals (0.5, 1.5, 2)
meal_type          enum? (deferred)    -- breakfast/lunch/dinner/snack — deferred to v2
nutrition_snapshot jsonb               -- copy of per-serving values at log time
created_at         timestamptz
```

**Key design decision — Snapshot vs. Reference:**
When logging a meal, we store a **snapshot** of the food's nutritional values in `nutrition_snapshot`, not just a reference to the food. Rationale (root-cause):
- **Historical accuracy:** if you edit a food (e.g. "Galaxy") next month, your old records stay correct for what you actually ate then.
- **Solves deletion automatically:** deleting a food from the catalog does not break old entries, because each entry owns its own copy.

This is a standard pattern for transactional records (like freezing a product's price on an invoice), and it is **not over-engineering** — it prevents an entire class of data-corruption bugs.
The simpler alternative (reference-only, always aggregate via join) exists, but it creates the edit and delete problems above. **Recommendation: snapshot.**

Totals for any entry = `nutrition_snapshot × quantity`.

---

## 5. Calc Engine

Pure functions in a clear order. Formula: **Mifflin-St Jeor** (most accurate documented BMR).

**1) BMR:**
```
male:    BMR = 10·weight_kg + 6.25·height_cm − 5·age + 5
female:  BMR = 10·weight_kg + 6.25·height_cm − 5·age − 161
```

**2) TDEE = BMR × activity factor:**
```
sedentary    (little/no exercise)        1.2
light        (1–3 days/week)             1.375
moderate     (3–5 days/week)             1.55
active       (6–7 days/week)             1.725
very_active  (physical job + training)   1.9
```

**3) Goal adjustment:**
```
cut       TDEE × 0.80    (~20% deficit)
maintain  TDEE × 1.00
bulk      TDEE × 1.10    (~10% surplus)
```

**4) Macros:**
```
protein_g = protein_per_kg × weight_kg               → protein_cal = protein_g × 4
fat_cal   = target_calories × fat_pct                → fat_g       = fat_cal / 9
carb_cal  = target_calories − protein_cal − fat_cal  → carb_g      = carb_cal / 4
```
> **Edge case:** if `carb_cal` is negative (very low calories + high protein), clamp to 0 and show a flag.

**Verification example** — male, 30y, 175 cm, 80 kg, moderate activity, cut goal:
```
BMR  = 800 + 1093.75 − 150 + 5           = 1748.75
TDEE = 1748.75 × 1.55                     = 2710.6
Cut  = 2710.6 × 0.80                       ≈ 2169 kcal
protein = 1.8 × 80 = 144 g  (576 kcal)
fat     = 2169 × 0.25 = 542 kcal → 60 g
carb    = 2169 − 576 − 542 = 1051 kcal → 263 g
```

---

## 6. Screens (RTL, Arabic-first)

**1) Profile (`/profile`)**
- Inputs: sex, birth date, height, weight, activity level, goal. (Advanced, optional: protein/kg, fat %.)
- Live display of computed targets: calories + macros.
- Save.

**2) Foods (`/foods`)**
- Food list + search.
- Add button → form with core fields + a collapsible section for detail fields.
- Edit / delete / detail view.

**3) Diary (`/diary`) — the home screen**
- Week selector (Sun → Sat), default current week.
- Weekly overview: each day shows its calorie total vs. target.
- Open a day: list of logged foods + totals vs. targets (progress bars) + remaining.
- Add entry: pick a food + quantity (servings).

---

## 7. Build Order (sequential — each phase independent and testable)

| Phase | Content | Depends on |
|-------|---------|------------|
| **0 — Setup** | monorepo scaffold, FastAPI + PostgreSQL + SQLModel + Alembic, Next.js + RTL + base design tokens | — |
| **1 — Profile & Calc** | Profile model + Calc Engine (pytest) + `/profile`; profile page with live targets | independent, testable immediately |
| **2 — Food Catalog** | full food CRUD (incl. net carbs + detail fields) | logging foundation |
| **3 — Diary Logging** | DiaryEntry + snapshot logic + day view with totals vs. targets | 1, 2 |
| **4 — Weekly View** | Aggregation service (Sun→Sat) + weekly visualization | 3 |
| **5 — PWA & Offline Reads** | manifest, service worker, Dexie cache, offline screens, cached targets | 1–4 |
| **6 — Offline Writes & Sync** | mutation queue, Sync service (push/pull, last-write-wins), sync status | 5 |

Dependency-correct ordering: engine first (produces targets), then foods (needed to log), then diary (needs foods), then weekly (aggregates diary), then the offline layer last.

---

## 8. Out of Scope (v1) — deliberately, to avoid over-engineering

- **Recipes** (a food composed of foods) → v2.
- **Barcode scanning** → later.
- **Public food database / API import** → not needed; manual entry by design.
- **Vitamins & minerals (micros)** → excluded; unreliable when entered manually.
- **Historical target snapshots** (targets over time) → v2.
- **Weight tracking (weight trend)** → optional, v1.5 if desired.

---

## 9. Decisions (resolved)

1. **Record storage:** Snapshot.
2. **UI layer:** Next.js + FastAPI (offline-first).
3. **Database:** PostgreSQL.
4. **Meal type:** Deferred to v2.

Next step: a prompts file split across the seven phases for Claude Code, each phase as an independent prompt — see **CLAUDE_CODE_PROMPTS.md**.
