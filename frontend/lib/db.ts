import Dexie, { type Table } from "dexie";

import { apiFetch } from "./api";
import { addDays } from "./dates";
import type {
  DiaryEntryInput,
  DiaryEntryResponse,
  FoodInput,
  FoodResponse,
  NutritionSnapshot,
  NutritionTotals,
  ProfileResponse,
  QueuedMutation,
  SyncOperation,
  SyncPullResponse,
  SyncPushResponse,
  TargetResponse,
  WeekSummary
} from "./types";

class MyNutriDb extends Dexie {
  foods!: Table<FoodResponse, string>;
  diaryEntries!: Table<DiaryEntryResponse, string>;
  profile!: Table<ProfileResponse, string>;
  mutations!: Table<QueuedMutation, number>;

  constructor() {
    super("mynutri");
    this.version(1).stores({
      foods: "id,name,updated_at",
      diaryEntries: "id,entry_date,food_id,created_at",
      profile: "id,updated_at",
      mutations: "++id,created_at,status"
    });
  }
}

let database: MyNutriDb | null = null;

export function getDb(): MyNutriDb {
  if (typeof window === "undefined") {
    throw new Error("IndexedDB is only available in the browser.");
  }
  database ??= new MyNutriDb();
  return database;
}

export async function cacheProfile(profile: ProfileResponse | null): Promise<void> {
  if (!profile) return;
  await getDb().profile.put(profile);
}

export async function getCachedProfile(): Promise<ProfileResponse | null> {
  return (await getDb().profile.orderBy("updated_at").last()) ?? null;
}

export async function cacheFoods(foods: FoodResponse[]): Promise<void> {
  await getDb().foods.bulkPut(foods);
}

export async function getCachedFoods(): Promise<FoodResponse[]> {
  return getDb().foods.orderBy("name").toArray();
}

export async function cacheDiaryEntries(entries: DiaryEntryResponse[]): Promise<void> {
  await getDb().diaryEntries.bulkPut(entries);
}

export async function getCachedEntriesByDate(entryDate: string): Promise<DiaryEntryResponse[]> {
  return getDb().diaryEntries.where("entry_date").equals(entryDate).reverse().sortBy("created_at");
}

export async function queueMutation(mutation: Omit<QueuedMutation, "created_at" | "status">) {
  await getDb().mutations.add({
    ...mutation,
    created_at: new Date().toISOString(),
    status: "pending"
  });
}

export async function getPendingMutationCount(): Promise<number> {
  return getDb()
    .mutations.filter((mutation) => mutation.status === "pending" || mutation.status === "syncing")
    .count();
}

export async function flushQueuedMutations(): Promise<number> {
  const db = getDb();
  const stuckSyncing = await db.mutations.where("status").equals("syncing").toArray();
  for (const item of stuckSyncing) {
    if (item.id != null) {
      await db.mutations.update(item.id, { status: "pending" });
    }
  }

  const pending = await db.mutations.where("status").equals("pending").sortBy("created_at");

  if (pending.length === 0) {
    await pullServerState();
    return 0;
  }

  const pendingIds = pending.flatMap((item) => (item.id == null ? [] : [item.id]));
  for (const id of pendingIds) {
    await db.mutations.update(id, { status: "syncing" });
  }

  const operations: SyncOperation[] = pending.map((item) => ({
    method: item.method,
    path: item.path,
    body: item.body,
    client_id: item.id == null ? undefined : String(item.id),
    created_at: item.created_at
  }));

  try {
    const result = await apiFetch<SyncPushResponse>("/sync/push", {
      method: "POST",
      body: JSON.stringify({ operations })
    });

    const acceptedIds = new Set(result.accepted_client_ids.map((id) => Number(id)));
    if (acceptedIds.size === 0 && result.rejected.length === 0 && result.accepted === pending.length) {
      pendingIds.forEach((id) => acceptedIds.add(id));
    }

    await db.mutations.bulkDelete([...acceptedIds]);

    const rejectedIds = new Set(
      result.rejected
        .map((item) => (item.client_id == null ? Number.NaN : Number(item.client_id)))
        .filter((id) => Number.isFinite(id))
    );
    const stillPending = pendingIds.filter((id) => !acceptedIds.has(id) || rejectedIds.has(id));
    for (const id of stillPending) {
      await db.mutations.update(id, { status: "pending" });
    }

    if (result.rejected.length > 0) {
      throw new Error(result.rejected[0]?.error ?? "Sync push rejected one or more operations.");
    }

    await pullServerState();
    return acceptedIds.size;
  } catch (error) {
    for (const id of pendingIds) {
      const existing = await db.mutations.get(id);
      if (existing?.status === "syncing") {
        await db.mutations.update(id, { status: "pending" });
      }
    }
    throw error;
  }
}

export async function pullServerState(): Promise<void> {
  const pulled = await apiFetch<SyncPullResponse>("/sync/pull");
  const db = getDb();
  await db.transaction("rw", db.profile, db.foods, db.diaryEntries, async () => {
    await db.profile.clear();
    if (pulled.profile) {
      await db.profile.put(pulled.profile);
    }
    await db.foods.clear();
    await db.foods.bulkPut(pulled.foods);
    await db.diaryEntries.clear();
    await db.diaryEntries.bulkPut(pulled.diary_entries);
  });
}

export function emptyTotals(): NutritionTotals {
  return {
    calories: 0,
    protein_g: 0,
    carb_g: 0,
    fat_g: 0,
    saturated_fat_g: null,
    trans_fat_g: null,
    cholesterol_mg: null,
    sodium_mg: null,
    fiber_g: null,
    total_sugars_g: null,
    added_sugar_g: null,
    net_carbs_g: 0
  };
}

function sumOptional(left: number | null, right: number | null): number | null {
  if (left == null && right == null) return null;
  return Number(((left ?? 0) + (right ?? 0)).toFixed(2));
}

export function addTotals(left: NutritionTotals, right: NutritionTotals): NutritionTotals {
  return {
    calories: Number((left.calories + right.calories).toFixed(2)),
    protein_g: Number((left.protein_g + right.protein_g).toFixed(2)),
    carb_g: Number((left.carb_g + right.carb_g).toFixed(2)),
    fat_g: Number((left.fat_g + right.fat_g).toFixed(2)),
    saturated_fat_g: sumOptional(left.saturated_fat_g, right.saturated_fat_g),
    trans_fat_g: sumOptional(left.trans_fat_g, right.trans_fat_g),
    cholesterol_mg: sumOptional(left.cholesterol_mg, right.cholesterol_mg),
    sodium_mg: sumOptional(left.sodium_mg, right.sodium_mg),
    fiber_g: sumOptional(left.fiber_g, right.fiber_g),
    total_sugars_g: sumOptional(left.total_sugars_g, right.total_sugars_g),
    added_sugar_g: sumOptional(left.added_sugar_g, right.added_sugar_g),
    net_carbs_g: Number((left.net_carbs_g + right.net_carbs_g).toFixed(2))
  };
}

export function totalsFromSnapshot(snapshot: NutritionSnapshot, quantity: number): NutritionTotals {
  const fiber = snapshot.fiber_g ?? 0;
  return {
    calories: Number((snapshot.calories * quantity).toFixed(2)),
    protein_g: Number((snapshot.protein_g * quantity).toFixed(2)),
    carb_g: Number((snapshot.carb_g * quantity).toFixed(2)),
    fat_g: Number((snapshot.fat_g * quantity).toFixed(2)),
    saturated_fat_g:
      snapshot.saturated_fat_g == null ? null : Number((snapshot.saturated_fat_g * quantity).toFixed(2)),
    trans_fat_g: snapshot.trans_fat_g == null ? null : Number((snapshot.trans_fat_g * quantity).toFixed(2)),
    cholesterol_mg:
      snapshot.cholesterol_mg == null ? null : Number((snapshot.cholesterol_mg * quantity).toFixed(2)),
    sodium_mg: snapshot.sodium_mg == null ? null : Number((snapshot.sodium_mg * quantity).toFixed(2)),
    fiber_g: snapshot.fiber_g == null ? null : Number((snapshot.fiber_g * quantity).toFixed(2)),
    total_sugars_g:
      snapshot.total_sugars_g == null ? null : Number((snapshot.total_sugars_g * quantity).toFixed(2)),
    added_sugar_g:
      snapshot.added_sugar_g == null ? null : Number((snapshot.added_sugar_g * quantity).toFixed(2)),
    net_carbs_g: Number(((snapshot.carb_g - fiber) * quantity).toFixed(2))
  };
}

export function snapshotFromFood(food: FoodResponse): NutritionSnapshot {
  const input: FoodInput = {
    name: food.name,
    serving_label: food.serving_label,
    serving_grams: food.serving_grams,
    calories: food.calories,
    protein_g: food.protein_g,
    carb_g: food.carb_g,
    fat_g: food.fat_g,
    saturated_fat_g: food.saturated_fat_g,
    trans_fat_g: food.trans_fat_g,
    cholesterol_mg: food.cholesterol_mg,
    sodium_mg: food.sodium_mg,
    fiber_g: food.fiber_g,
    total_sugars_g: food.total_sugars_g,
    added_sugar_g: food.added_sugar_g
  };
  return { ...input, food_id: food.id };
}

export async function addLocalDiaryEntry(input: DiaryEntryInput, food: FoodResponse): Promise<DiaryEntryResponse> {
  const entryId = crypto.randomUUID();
  const snapshot = snapshotFromFood(food);
  const entry: DiaryEntryResponse = {
    id: entryId,
    entry_date: input.entry_date,
    food_id: input.food_id,
    quantity: input.quantity,
    nutrition_snapshot: snapshot,
    totals: totalsFromSnapshot(snapshot, input.quantity),
    created_at: new Date().toISOString()
  };
  await getDb().diaryEntries.put(entry);
  await queueMutation({ method: "POST", path: "/diary", body: { ...input, id: entryId } });
  return entry;
}

export async function buildOfflineWeek(start: string, targets: TargetResponse | null): Promise<WeekSummary> {
  let weeklyTotals = emptyTotals();
  const days = [];

  for (let index = 0; index < 7; index += 1) {
    const date = addDays(start, index);
    const entries = await getCachedEntriesByDate(date);
    const totals = entries.reduce(
      (current, entry) => addTotals(current, totalsFromSnapshot(entry.nutrition_snapshot, entry.quantity)),
      emptyTotals()
    );
    weeklyTotals = addTotals(weeklyTotals, totals);
    days.push({ date, totals, targets });
  }

  return {
    start,
    end: addDays(start, 6),
    days,
    weekly_totals: weeklyTotals,
    targets
  };
}
