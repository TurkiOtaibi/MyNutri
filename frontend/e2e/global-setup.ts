import type { FullConfig } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const API_TOKEN = process.env.PLAYWRIGHT_API_TOKEN ?? "dev-token";
const headers = { Authorization: `Bearer ${API_TOKEN}`, "Content-Type": "application/json" };

async function ensureSuccessful(response: Response, operation: string): Promise<void> {
  if (response.ok) return;
  throw new Error(`${operation} failed with ${response.status}: ${await response.text()}`);
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const hostname = new URL(API_URL).hostname;
  if (hostname !== "127.0.0.1" && hostname !== "localhost") {
    throw new Error(`E2E seed refuses non-local API target ${API_URL}`);
  }

  const profile = await fetch(`${API_URL}/profile`, { headers });
  if (profile.status === 404) {
    const created = await fetch(`${API_URL}/profile`, {
      method: "PUT",
      headers,
      body: JSON.stringify({
        sex: "male",
        birth_date: "1990-01-01",
        height_cm: 175,
        weight_kg: 80,
        activity_level: "moderate",
        goal: "maintain",
        protein_per_kg: 1.2,
        fat_pct: 0.25,
        selected_cut_intensity: 0.2
      })
    });
    await ensureSuccessful(created, "Profile seed");
  } else {
    await ensureSuccessful(profile, "Profile read");
  }

  const foods = await fetch(`${API_URL}/foods`, { headers });
  await ensureSuccessful(foods, "Food seed read");
  const existing = await foods.json() as Array<{ name?: string }>;
  if (existing.some((food) => food.name === "Wave 1 E2E baseline")) return;

  const createdFood = await fetch(`${API_URL}/foods`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      name: "Wave 1 E2E baseline",
      brand: null,
      category: "Baseline",
      primary_category_key: "other",
      food_kind: "simple",
      group_data_status: "unknown",
      group_data_completeness: "unknown",
      nutrition_basis: "per_100g",
      default_unit_type: "serving",
      unit_amount: 100,
      unit_basis: "g",
      calories: 200,
      protein_g: 10,
      carb_g: 25,
      fat_g: 7,
      nutrition_source: { type: "unknown", name: null, reference: null },
      ingredients: { text: null, source_type: null, source_name: null, source_reference: null },
      nova: null,
      group_contributions: [],
      analytical_traits: []
    })
  });
  await ensureSuccessful(createdFood, "Food seed create");
}
