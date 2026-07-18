import { chromium, type FullConfig } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const EMAIL = "admin.e2e@example.test";
const PASSWORD = "E2e-only-password-2026!";
const AUTH_DIR = path.join(process.cwd(), "e2e", ".auth");
export const STORAGE_STATE = path.join(AUTH_DIR, "admin.json");
export const TOKEN_FILE = path.join(AUTH_DIR, "access-token.txt");

async function ensureSuccessful(response: Response, operation: string): Promise<void> {
  if (response.ok) return;
  throw new Error(`${operation} failed with ${response.status}: ${await response.text()}`);
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  for (const value of [API_URL, AUTH_URL]) {
    const hostname = new URL(value).hostname;
    if (hostname !== "127.0.0.1" && hostname !== "localhost") {
      throw new Error(`E2E setup refuses non-local target ${value}`);
    }
  }
  await mkdir(AUTH_DIR, { recursive: true });
  const tokenResponse = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD })
  });
  await ensureSuccessful(tokenResponse, "Local Auth sign-in");
  const auth = await tokenResponse.json() as { access_token: string };
  await writeFile(TOKEN_FILE, auth.access_token, { encoding: "utf8", mode: 0o600 });
  const headers = { Authorization: `Bearer ${auth.access_token}`, "Content-Type": "application/json" };

  const profile = await fetch(`${API_URL}/profile`, { headers });
  if (profile.status === 404) {
    await ensureSuccessful(await fetch(`${API_URL}/profile`, {
      method: "PUT", headers,
      body: JSON.stringify({
        sex: "male", birth_date: "1990-01-01", height_cm: 175, weight_kg: 80,
        activity_level: "moderate", goal: "maintain", protein_per_kg: 1.2,
        fat_pct: 0.25, selected_cut_intensity: 0.2
      })
    }), "Profile seed");
  } else {
    await ensureSuccessful(profile, "Profile read");
  }

  const foods = await fetch(`${API_URL}/foods`, { headers });
  await ensureSuccessful(foods, "Food seed read");
  const existing = await foods.json() as Array<{ name?: string }>;
  if (!existing.some((food) => food.name === "V2 E2E baseline")) {
    await ensureSuccessful(await fetch(`${API_URL}/foods`, {
      method: "POST", headers,
      body: JSON.stringify({
        name: "V2 E2E baseline", brand: null, food_category_key: "other", food_kind: "simple",
        nutrition_basis: "per_100g", default_unit_type: "serving", unit_amount: 100,
        unit_basis: "g", calories: 200, protein_g: 10, carb_g: 25, fat_g: 7,
        nutrition_source: { type: "unknown", name: null, reference: null },
        ingredients: { text: null, source_type: null, source_name: null, source_reference: null },
        nova: null, group_contributions: [], analytical_traits: []
      })
    }), "Food seed create");
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const baseURL = config.projects[0]?.use.baseURL as string;
  await page.goto(`${baseURL}/auth/login`);
  await page.locator('input[type="email"]').fill(EMAIL);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/(diary|profile)$/);
  await page.context().storageState({ path: STORAGE_STATE });
  await browser.close();
}
