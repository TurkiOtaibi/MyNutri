import { expect, test } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";

async function token(email: string, password = "Acceptance-only-password-2026!") {
  const response = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  expect(response.status).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

function auth(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" };
}

const profile = (weight: number) => ({
  sex: "male",
  birth_date: "1990-01-01",
  height_cm: 175,
  weight_kg: weight,
  activity_level: "moderate",
  goal: "maintain",
  protein_per_kg: 1.2,
  fat_pct: 0.25,
  selected_cut_intensity: 0.2
});

test("User A, User B, and Admin remain isolated through API and UI", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `acceptance-a-${suffix}@example.test`;
  const emailB = `acceptance-b-${suffix}@example.test`;
  const tokenA = await token(emailA);
  const tokenB = await token(emailB);
  const adminToken = await token("admin.e2e@example.test", "E2e-only-password-2026!");

  const accountAResponse = await request.get(`${API_URL}/account/me`, { headers: auth(tokenA) });
  const accountBResponse = await request.get(`${API_URL}/account/me`, { headers: auth(tokenB) });
  expect(accountAResponse.status()).toBe(200);
  expect(accountBResponse.status()).toBe(200);
  const accountA = await accountAResponse.json() as { principal_id: string; role: string };
  const accountB = await accountBResponse.json() as { principal_id: string; role: string };
  expect(accountA.role).toBe("user");
  expect(accountB.role).toBe("user");
  expect(accountA.principal_id).not.toBe(accountB.principal_id);

  expect((await request.put(`${API_URL}/profile`, { headers: auth(tokenA), data: profile(71) })).status()).toBe(200);
  expect((await request.put(`${API_URL}/profile`, { headers: auth(tokenB), data: profile(89) })).status()).toBe(200);
  const ownA = await request.get(`${API_URL}/profile`, { headers: auth(tokenA) });
  const ownB = await request.get(`${API_URL}/profile`, { headers: auth(tokenB) });
  expect((await ownA.json()).weight_kg).toBe(71);
  expect((await ownB.json()).weight_kg).toBe(89);

  expect((await request.get(`${API_URL}/admin/users/${accountB.principal_id}`, { headers: auth(tokenA) })).status()).toBe(403);
  expect((await request.get(`${API_URL}/admin/users/${accountA.principal_id}/diary`, { headers: auth(tokenB) })).status()).toBe(403);
  expect((await request.post(`${API_URL}/foods`, {
    headers: auth(tokenA),
    data: {
      name: `Forbidden Food ${suffix}`,
      food_category_key: "other",
      food_kind: "simple",
      nutrition_basis: "per_100g",
      default_unit_type: "serving",
      unit_amount: 100,
      unit_basis: "g",
      calories: 100,
      protein_g: 1,
      carb_g: 20,
      fat_g: 1,
      nutrition_source: { type: "unknown" }
    }
  })).status()).toBe(403);

  const adminA = await request.get(`${API_URL}/admin/users/${accountA.principal_id}`, { headers: auth(adminToken) });
  const adminB = await request.get(`${API_URL}/admin/users/${accountB.principal_id}`, { headers: auth(adminToken) });
  expect(adminA.status()).toBe(200);
  expect(adminB.status()).toBe(200);
  expect((await adminA.json()).profile.weight_kg).toBe(71);
  expect((await adminB.json()).profile.weight_kg).toBe(89);
  expect((await request.put(`${API_URL}/admin/users/${accountA.principal_id}`, {
    headers: auth(adminToken), data: profile(55)
  })).status()).toBe(405);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill(emailA);
  await page.locator('input[type="password"]').fill("Acceptance-only-password-2026!");
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/diary$/);
  await page.goto("/foods");
  await expect(page.getByRole("heading", { name: "الأطعمة" })).toBeVisible();
  await expect(page.getByRole("link", { name: "الإدارة" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /إضافة طعام/ })).toHaveCount(0);
  await context.close();
});
