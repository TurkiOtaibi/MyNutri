import { expect, test } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";

async function localToken(email: string): Promise<string> {
  const response = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: "E2e-user-password-2026!" })
  });
  expect(response.status).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

test("unauthenticated navigation redirects to Arabic login", async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await page.goto("/profile");
  await expect(page).toHaveURL(/\/auth\/login\?next=%2Fprofile/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
  await context.close();
});

test("new user receives user role and cannot mutate the shared Food catalog", async ({ request }) => {
  const token = await localToken(`user-${Date.now()}@example.test`);
  const headers = { Authorization: `Bearer ${token}` };
  const account = await request.get(`${API_URL}/account/me`, { headers });
  expect(account.status()).toBe(200);
  expect((await account.json()).role).toBe("user");
  const catalog = await request.get(`${API_URL}/foods`, { headers });
  expect(catalog.status()).toBe(200);
  const mutation = await request.post(`${API_URL}/foods`, {
    headers,
    data: {
      name: "Forbidden user Food", food_category_key: "other", food_kind: "simple",
      nutrition_basis: "per_100g", default_unit_type: "serving", unit_amount: 100,
      unit_basis: "g", calories: 100, protein_g: 1, carb_g: 20, fat_g: 1,
      nutrition_source: { type: "unknown" }
    }
  });
  expect(mutation.status()).toBe(403);
  expect(await mutation.text()).toContain("FORBIDDEN");
});

test("admin navigation and monitoring remain explicit and read-only", async ({ page }) => {
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "المستخدمون" })).toBeVisible();
  await expect(page.getByRole("link", { name: "الإدارة" })).toBeVisible();
  const firstUser = page.locator(".admin-user-row").first();
  await expect(firstUser).toBeVisible();
  await firstUser.click();
  await expect(page.getByText("وضع قراءة فقط")).toBeVisible();
  await expect(page.getByRole("button", { name: /حفظ|تعديل|حذف/ })).toHaveCount(0);
  await expect(page.locator("pre")).toHaveCount(0);
});

test("Food Taxonomy V2 and advanced analysis are mobile safe", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/foods/new");
  await expect(page.getByLabel(/فئة الطعام/)).toBeVisible();
  await expect(page.getByText("الفئة القديمة (للتوافق)")).toHaveCount(0);
  await page.getByLabel(/فئة الطعام/).selectOption("baked_goods");
  await expect(page.getByLabel(/نوع المخبوز/)).toBeVisible();
  await expect(page.getByLabel(/نوع الحبوب/)).toBeVisible();
  const advanced = page.locator("details", { hasText: "التحليل الغذائي المتقدم" });
  await expect(advanced).not.toHaveAttribute("open", "");
  await advanced.locator("summary").click();
  await expect(page.getByText("المجموعات الغذائية", { exact: true })).toBeVisible();
  await expect(page.getByText("السمات التحليلية", { exact: true })).toBeVisible();
  const layout = await page.evaluate(() => {
    const bar = document.querySelector(".form-actions-sticky")?.getBoundingClientRect();
    const root = document.documentElement;
    return { overflow: root.scrollWidth - root.clientWidth, barBottom: bar?.bottom ?? 0, viewport: innerHeight };
  });
  expect(layout.overflow).toBeLessThanOrEqual(1);
  expect(layout.barBottom).toBeLessThanOrEqual(layout.viewport + 1);
});

test("API base URL normalization never emits a double-slash route", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/foods");
  await expect(page.getByRole("heading", { name: "الأطعمة" })).toBeVisible();
  expect(requests.filter((url) => url.startsWith(API_URL))).not.toContainEqual(expect.stringMatching(`${API_URL}//`));
});
