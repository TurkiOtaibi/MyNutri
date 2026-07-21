import { expect, test, type Page } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";
const PASSWORD = "Session-isolation-password-2026!";
const ADMIN_EMAIL = "admin.e2e@example.test";
const ADMIN_PASSWORD = "E2e-only-password-2026!";

async function token(email: string, password = PASSWORD): Promise<string> {
  const response = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  expect(response.status).toBe(200);
  return ((await response.json()) as { access_token: string }).access_token;
}

function headers(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" };
}

function profile(weight: number) {
  return {
    sex: "male", birth_date: "1990-01-01", height_cm: 175, weight_kg: weight,
    activity_level: "moderate", goal: "maintain", protein_per_kg: 1.2,
    fat_pct: 0.25, selected_cut_intensity: 0.2
  };
}

async function signIn(page: Page, email: string, password: string, next: string) {
  await page.goto(`/auth/login?next=${encodeURIComponent(next)}`);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(new RegExp(`${next.replace("/", "\\/")}$`));
}

async function installLeakObserver(page: Page, markers: string[]) {
  await page.evaluate((observedMarkers) => {
    const records: string[] = [];
    const snapshot = () => {
      const inputs = Array.from(document.querySelectorAll("input")).map((input) => input.value).join(" ");
      const visible = `${document.body.innerText} ${inputs}`;
      if (observedMarkers.some((marker) => visible.includes(marker))) records.push(visible);
    };
    new MutationObserver(snapshot).observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true });
    snapshot();
    (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords = records;
  }, markers);
}

async function leakRecords(page: Page) {
  return page.evaluate(() => (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords ?? []);
}

test("same browser context isolates cached profile and diary data across A to B to A", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `session-a-${suffix}@example.test`;
  const emailB = `session-b-${suffix}@example.test`;
  const tokenA = await token(emailA);
  const tokenB = await token(emailB);
  const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenA), data: profile(71) })).status()).toBe(200);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenB), data: profile(89) })).status()).toBe(200);
  const diaryNameA = `A diary marker ${suffix}`;
  const foodResponse = await request.post(`${API_URL}/foods`, {
    headers: headers(adminToken),
    data: {
      name: diaryNameA, food_category_key: "other", food_kind: "simple", nutrition_basis: "per_100g",
      default_unit_type: "serving", unit_amount: 100, unit_basis: "g", calories: 200, protein_g: 10,
      carb_g: 25, fat_g: 7, nutrition_source: { type: "unknown", name: null, reference: null },
      ingredients: { text: null, source_type: null, source_name: null, source_reference: null },
      nova: null, group_contributions: [], analytical_traits: []
    }
  });
  expect(foodResponse.status()).toBe(201);
  const food = await foodResponse.json() as { id: string };
  const entry = await request.post(`${API_URL}/diary`, {
    headers: headers(tokenA),
    data: { entry_date: new Date().toISOString().slice(0, 10), food_id: food.id, quantity: 1, meal_type: "breakfast" }
  });
  expect(entry.status()).toBe(201);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await page.goto("/diary");
  await expect(page.getByText(diaryNameA, { exact: true })).toBeVisible();

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login$/);
  await installLeakObserver(page, ["71", diaryNameA]);
  let releaseProfileB!: () => void;
  let profileBWasBlocked = false;
  const profileBBlocked = new Promise<void>((resolve) => { releaseProfileB = resolve; });
  await page.route(`${API_URL}/profile`, async (route) => {
    profileBWasBlocked = true;
    await profileBBlocked;
    await route.continue();
  });
  await signIn(page, emailB, PASSWORD, "/profile");
  await expect.poll(() => profileBWasBlocked).toBe(true);
  await expect.poll(() => page.locator('input[aria-label="الوزن"]').count()).toBe(0);
  expect(await leakRecords(page)).toEqual([]);
  await expect(page.getByRole("link", { name: "الإدارة" })).toHaveCount(0);
  releaseProfileB();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("89");
  expect(await leakRecords(page)).toEqual([]);

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login$/);
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await context.close();
});

test("a delayed Admin account response cannot restore Admin identity after User B takes over", async ({ browser }) => {
  const suffix = Date.now();
  const emailB = `race-b-${suffix}@example.test`;
  await token(emailB);
  let releaseAdminAccount!: () => void;
  let adminAccountWasBlocked = false;
  let bAccountRequestedOnAdminPage = false;
  const adminAccountBlocked = new Promise<void>((resolve) => { releaseAdminAccount = resolve; });
  let releaseProfileB!: () => void;
  let profileBWasBlocked = false;
  const profileBBlocked = new Promise<void>((resolve) => { releaseProfileB = resolve; });
  const context = await browser.newContext({ storageState: undefined });
  const adminPage = await context.newPage();
  const userPage = await context.newPage();
  await adminPage.route(`${API_URL}/account/me`, async (route) => {
    if (!adminAccountWasBlocked) {
      adminAccountWasBlocked = true;
      await adminAccountBlocked;
    } else {
      bAccountRequestedOnAdminPage = true;
    }
    await route.continue();
  });
  await userPage.route(`${API_URL}/profile`, async (route) => {
    profileBWasBlocked = true;
    await profileBBlocked;
    await route.continue();
  });
  await signIn(adminPage, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile");
  await expect.poll(() => adminAccountWasBlocked).toBe(true);
  await installLeakObserver(adminPage, [ADMIN_EMAIL, "الإدارة"]);
  await signIn(userPage, emailB, PASSWORD, "/profile");
  await expect.poll(() => profileBWasBlocked).toBe(true);
  await expect.poll(() => bAccountRequestedOnAdminPage).toBe(true);
  await expect.poll(() => adminPage.getByRole("link", { name: "الإدارة" }).count()).toBe(0);
  await expect(userPage.getByRole("link", { name: "الإدارة" })).toHaveCount(0);
  releaseAdminAccount();
  releaseProfileB();
  await expect.poll(async () => (await leakRecords(adminPage)).length).toBe(0);
  await expect(adminPage.getByRole("link", { name: "الإدارة" })).toHaveCount(0);
  await context.close();
});
