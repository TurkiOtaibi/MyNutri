import { expect, test, type Page, type Request } from "@playwright/test";

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
    sex: "male",
    birth_date: "1990-01-01",
    height_cm: 175,
    weight_kg: weight,
    activity_level: "moderate",
    goal: "maintain",
    protein_per_kg: 1.2,
    fat_pct: 0.25,
    selected_cut_intensity: 0.2
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
      if (observedMarkers.some((marker) => visible.includes(marker))) records.push(document.body.innerText);
    };
    new MutationObserver(snapshot).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true
    });
    snapshot();
    (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords = records;
  }, markers);
}

async function leakRecords(page: Page) {
  return page.evaluate(() => (window as Window & { __sessionLeakRecords?: string[] }).__sessionLeakRecords ?? []);
}

async function e2eAuthAction(page: Page, action: "refresh" | "signOut" | "signIn", credentials?: { email: string; password: string }) {
  const result = await page.evaluate(async ({ operation, login }) => {
    const testWindow = window as Window & {
      __mynutriE2ERefreshSession?: () => Promise<{ error: { message: string } | null }>;
      __mynutriE2ESignOut?: () => Promise<{ error: { message: string } | null }>;
      __mynutriE2ESignInWithPassword?: (email: string, password: string) => Promise<{ error: { message: string } | null }>;
    };
    const call = operation === "refresh" ? testWindow.__mynutriE2ERefreshSession : testWindow.__mynutriE2ESignOut;
    if (operation === "signIn") {
      if (!testWindow.__mynutriE2ESignInWithPassword || !login) throw new Error("Local E2E auth control is unavailable.");
      return testWindow.__mynutriE2ESignInWithPassword(login.email, login.password);
    }
    if (!call) throw new Error("Local E2E auth control is unavailable.");
    return call();
  }, { operation: action, login: credentials });
  expect(result.error).toBeNull();
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
      name: diaryNameA,
      food_category_key: "other",
      food_kind: "simple",
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
    }
  });
  expect(foodResponse.status()).toBe(201);
  const food = await foodResponse.json() as { id: string };
  const diaryResponse = await request.post(`${API_URL}/diary`, {
    headers: headers(tokenA),
    data: {
      entry_date: new Date().toISOString().slice(0, 10),
      food_id: food.id,
      quantity: 1,
      meal_type: "breakfast"
    }
  });
  expect(diaryResponse.status()).toBe(201);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  const historyMarkerA = `A target history marker ${suffix}`;
  let blockHistoryB = false;
  let historyBWasBlocked = false;
  let releaseHistoryB!: () => void;
  const historyBBlocked = new Promise<void>((resolve) => { releaseHistoryB = resolve; });
  await page.route(`${API_URL}/target-plans*`, async (route) => {
    if (blockHistoryB) {
      historyBWasBlocked = true;
      await historyBBlocked;
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [], next_cursor: null }) });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [{ id: `plan-${suffix}`, status: "active", effective_from: historyMarkerA, effective_to: null, targets: { target_calories: 2100 } }],
        next_cursor: null
      })
    });
  });
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await expect(page.getByText(historyMarkerA, { exact: true })).toBeVisible();
  await page.goto("/diary");
  await expect(page.getByText(diaryNameA, { exact: true })).toBeVisible();

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  blockHistoryB = true;
  await installLeakObserver(page, [emailA, "71", diaryNameA, historyMarkerA]);
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
  await expect.poll(() => historyBWasBlocked).toBe(true);
  await expect.poll(() => page.locator('input[aria-label="الوزن"]').count()).toBe(0);
  expect(await leakRecords(page)).toEqual([]);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  releaseHistoryB();
  releaseProfileB();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("89");
  expect(await leakRecords(page)).toEqual([]);

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("71");
  await context.close();
});

test("a delivered delayed Admin account response cannot restore Admin identity after User B takes over", async ({ browser }) => {
  const emailB = `race-b-${Date.now()}@example.test`;
  await token(emailB);
  let releaseAdminAccount!: () => void;
  let adminAccountWasBlocked = false;
  let bAccountRequestedOnAdminPage = false;
  let delayedAdminRequest: Request | null = null;
  const adminAccountBlocked = new Promise<void>((resolve) => { releaseAdminAccount = resolve; });
  const context = await browser.newContext({ storageState: undefined });
  const adminPage = await context.newPage();

  await adminPage.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
      if (new URL(url, window.location.href).pathname === "/account/me" && init?.signal) {
        const { signal: _signal, ...withoutSignal } = init;
        return originalFetch(input, withoutSignal);
      }
      return originalFetch(input, init);
    };
  });
  await adminPage.route(`${API_URL}/account/me`, async (route) => {
    if (!adminAccountWasBlocked) {
      adminAccountWasBlocked = true;
      delayedAdminRequest = route.request();
      await adminAccountBlocked;
    } else {
      bAccountRequestedOnAdminPage = true;
    }
    await route.continue();
  });
  await signIn(adminPage, ADMIN_EMAIL, ADMIN_PASSWORD, "/profile");
  await expect.poll(() => adminAccountWasBlocked).toBe(true);
  const delayedAdminResponse = adminPage.waitForResponse((response) => response.request() === delayedAdminRequest);
  await installLeakObserver(adminPage, [ADMIN_EMAIL, "الإدارة"]);
  await e2eAuthAction(adminPage, "signOut");
  await e2eAuthAction(adminPage, "signIn", { email: emailB, password: PASSWORD });
  await expect.poll(() => bAccountRequestedOnAdminPage).toBe(true);
  await expect(adminPage.locator(".nav-signout")).toBeVisible();
  await expect(adminPage.locator('a[href="/admin"]')).toHaveCount(0);

  releaseAdminAccount();
  const response = await delayedAdminResponse;
  expect(await response.finished()).toBeNull();
  await adminPage.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  expect(await leakRecords(adminPage)).toEqual([]);
  await expect(adminPage.locator('a[href="/admin"]')).toHaveCount(0);
  await context.close();
});

test("Admin private list and detail caches disappear when the same browser context becomes User B", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailB = `admin-cache-b-${suffix}@example.test`;
  const emailMonitored = `admin-cache-monitored-${suffix}@example.test`;
  const tokenB = await token(emailB);
  const tokenMonitored = await token(emailMonitored);
  const adminToken = await token(ADMIN_EMAIL, ADMIN_PASSWORD);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenB), data: profile(83) })).status()).toBe(200);
  const monitoredAccount = await request.get(`${API_URL}/account/me`, { headers: headers(tokenMonitored) });
  expect(monitoredAccount.status()).toBe(200);
  const monitoredPrincipalId = (await monitoredAccount.json() as { principal_id: string }).principal_id;
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(adminToken) })).status()).toBe(200);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, ADMIN_EMAIL, ADMIN_PASSWORD, "/admin/users");
  await expect(page.getByText(emailMonitored, { exact: true })).toBeVisible();
  await page.goto(`/admin/users/${monitoredPrincipalId}`);
  await expect(page.getByText(emailMonitored, { exact: true })).toBeVisible();

  await page.locator(".nav-signout").click();
  await page.waitForURL(/\/auth\/login(?:\?.*)?$/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await installLeakObserver(page, [emailMonitored, ADMIN_EMAIL]);
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
  await expect(page.locator(".selected-user-banner")).toHaveCount(0);
  await expect(page.locator(".admin-user-row")).toHaveCount(0);
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  expect(await leakRecords(page)).toEqual([]);
  releaseProfileB();
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("83");
  expect(await leakRecords(page)).toEqual([]);
  await context.close();
});

test("a refresh-token session update keeps User A's query client and does not request another subject's profile", async ({ browser, request }) => {
  const suffix = Date.now();
  const emailA = `refresh-a-${suffix}@example.test`;
  const tokenA = await token(emailA);
  expect((await request.put(`${API_URL}/profile`, { headers: headers(tokenA), data: profile(74) })).status()).toBe(200);

  const context = await browser.newContext({ storageState: undefined });
  const page = await context.newPage();
  await signIn(page, emailA, PASSWORD, "/profile");
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("74");
  let accountRequestsAfterRefresh = 0;
  let profileRequestsAfterRefresh = 0;
  page.on("request", (requestEvent) => {
    if (requestEvent.url() === `${API_URL}/account/me`) accountRequestsAfterRefresh += 1;
    if (requestEvent.url() === `${API_URL}/profile`) profileRequestsAfterRefresh += 1;
  });

  await e2eAuthAction(page, "refresh");
  await expect.poll(() => accountRequestsAfterRefresh).toBeGreaterThanOrEqual(1);
  await expect(page.locator('input[aria-label="الوزن"]')).toHaveValue("74");
  expect(profileRequestsAfterRefresh).toBe(0);
  await context.close();
});
