import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { ADMIN_EMAIL, ADMIN_PASSWORD, fixtureUsername, internalLogin, seedInternalUser, SESSION_TOKEN_KEY } from "./internal-auth";
import { applyProfileThroughTargetPlan } from "./profile-api";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const PASSWORD = "Internal-initial-password-2026!";
const NEW_PASSWORD = "Internal-updated-password-2026!";
const GENERIC = "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى.";
const SHORT = "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.";

test.use({ storageState: { cookies: [], origins: [] }, trace: "off", screenshot: "off", video: "off" });

function actor(forced = false) {
  const email = `internal-${randomUUID()}@example.test`;
  seedInternalUser(email, PASSWORD, forced);
  return email;
}

async function signIn(page: Page, email: string, password = PASSWORD, next = "/diary") {
  await page.goto(`/auth/login?next=${encodeURIComponent(next)}`);
  await page.getByLabel("اسم المستخدم", { exact: true }).fill(fixtureUsername(email));
  await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
  await page.getByRole("button", { name: "دخول", exact: true }).click();
}

async function storedToken(page: Page) {
  const token = await page.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY);
  if (!token) throw new Error("Expected an internal session.");
  return token;
}

function headers(token: string) { return { Authorization: `Bearer ${token}` }; }

for (const [code, message] of [
  ["ACCOUNT_DISABLED", "حسابك موقوف. تواصل مع المشرف."],
  ["ADMIN_LOCKED", "تم قفل الحساب بعد 5 محاولات دخول فاشلة. حاول مرة أخرى بعد 30 دقيقة."],
] as const) {
  test(`@issue111 login maps ${code} to its governed message`, async ({ page }) => {
    await page.route(`${API_URL}/auth/login`, route => route.fulfill({ status: 401, json: { detail: { code } } }));
    await signIn(page, "message@example.test");
    await expect(page.getByRole("status")).toHaveText(message);
    expect(await page.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY)).toBeNull();
  });
}

test("@issue111 login network failure has the governed connection message", async ({ page }) => {
  await page.route(`${API_URL}/auth/login`, route => route.abort("failed"));
  await signIn(page, "network@example.test");
  await expect(page.getByRole("status")).toHaveText("تعذر الاتصال بالخادم. حاول مرة أخرى.");
});

for (const [code, message] of [
  ["INVALID_CREDENTIAL", "انتهت جلستك. سجّل الدخول مرة أخرى."],
  ["ACCOUNT_DISABLED", "حسابك موقوف. تواصل مع المشرف."],
] as const) {
  test(`@issue111 ${code} clears a restored session and preserves the requested page`, async ({ page }) => {
    await signIn(page, actor());
    await expect(page).toHaveURL(/\/diary$/);
    await page.route(`${API_URL}/account/me`, route => route.fulfill({ status: 401, json: { detail: { code } } }));
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/auth\/login\?/);
    await expect(page.getByRole("status")).toHaveText(message);
    expect(new URL(page.url()).searchParams.get("next")).toBe("/profile");
    expect(await page.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY)).toBeNull();
  });
}

test("@issue111 an already signed-in login visit goes to Diary after consuming return-to", async ({ page }) => {
  const email = actor();
  await signIn(page, email, PASSWORD, "/profile");
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("heading", { name: "بياناتك وأهدافك", exact: true })).toBeVisible();
  await page.evaluate(() => history.pushState(null, "", "/auth/login"));
  await expect(page).toHaveURL(/\/diary$/);
});

test("@issue111 login offers Admin help without recovery and is mobile accessible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/auth/login");
  await expect(page.getByText("ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف.")).toBeVisible();
  await expect(page.locator('input[type="email"]')).toHaveCount(0);
  await expect(page.locator('a[href*="forgot-password"], a[href*="reset-password"]')).toHaveCount(0);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
});

test("@issue111 missing username sends no login request", async ({ page }) => {
  let calls = 0;
  page.on("request", request => { if (new URL(request.url()).pathname === "/auth/login" && request.method() === "POST") calls++; });
  await page.goto("/auth/login");
  await page.getByLabel("كلمة المرور", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "دخول", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("أدخل اسم المستخدم.");
  expect(calls).toBe(0);
});

test("@issue111 short login password sends no login request", async ({ page }) => {
  let calls = 0;
  page.on("request", request => { if (new URL(request.url()).pathname === "/auth/login" && request.method() === "POST") calls++; });
  await page.goto("/auth/login");
  await page.getByLabel("اسم المستخدم", { exact: true }).fill("synthetic_user");
  await page.getByLabel("كلمة المرور", { exact: true }).fill("short");
  await page.getByRole("button", { name: "دخول", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(SHORT);
  expect(calls).toBe(0);
});

test("@issue111 unknown username and wrong password use the same generic response", async ({ page }) => {
  const email = actor();
  for (const identity of [email, `unknown-${randomUUID()}@example.test`]) {
    await signIn(page, identity, "Wrong-password-2026!");
    await expect(page.getByRole("status")).toHaveText(GENERIC);
    await expect(page.getByLabel("كلمة المرور", { exact: true })).toBeFocused();
    expect(await page.evaluate(key => localStorage.getItem(key) === null, SESSION_TOKEN_KEY)).toBe(true);
  }
});

test("@issue111 five failures lock a user until Admin reset permits direct login", async ({ page, request }) => {
  const email = actor();
  const prior = await internalLogin(email, PASSWORD);
  for (let attempt = 1; attempt <= 5; attempt++) {
    await signIn(page, email, "Wrong-password-2026!");
    await expect(page.getByRole("status")).toHaveText(attempt === 5
      ? "تم قفل الحساب بعد 5 محاولات دخول فاشلة. تواصل مع المشرف لفتحه." : GENERIC);
  }
  const admin = await internalLogin(ADMIN_EMAIL, ADMIN_PASSWORD);
  const reset = await request.put(`${API_URL}/admin/accounts/${prior.account.principal_id}/password`, {
    headers: headers(admin.access_token), data: { new_password: NEW_PASSWORD },
  });
  expect(reset.status()).toBe(204);
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(prior.access_token) })).status()).toBe(401);
  await signIn(page, email, NEW_PASSWORD);
  await expect(page).toHaveURL(/\/diary$/);
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toHaveCount(0);
});

test("@issue111 initial password gates product endpoints and rejects a short replacement", async ({ page, request }) => {
  await signIn(page, actor(true));
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toBeVisible();
  const token = await storedToken(page);
  for (const endpoint of ["/account/me", "/profile", "/foods"]) {
    const response = await request.get(`${API_URL}${endpoint}`, { headers: headers(token) });
    expect(response.status()).toBe(403);
    expect((await response.json()).detail.code).toBe("PASSWORD_CHANGE_REQUIRED");
  }
  let updates = 0;
  page.on("request", request => { if (new URL(request.url()).pathname === "/auth/change-password") updates++; });
  await expect(page.getByText("استخدم 8 أحرف على الأقل.")).toBeVisible();
  await page.getByLabel("كلمة المرور الجديدة", { exact: true }).fill("short");
  await page.getByRole("button", { name: "حفظ كلمة المرور" }).click();
  await expect(page.getByRole("alert").filter({ hasText: SHORT })).toHaveText(SHORT);
  expect(updates).toBe(0);
});

test("@issue111 initial password change admits the user and rejects the old password", async ({ page, request }) => {
  const email = actor(true);
  await signIn(page, email);
  await page.getByLabel("كلمة المرور الجديدة", { exact: true }).fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "حفظ كلمة المرور" }).click();
  await expect(page).toHaveURL(/\/diary$/);
  const account = await request.get(`${API_URL}/account/me`, { headers: headers(await storedToken(page)) });
  expect(account.status()).toBe(200);
  expect((await account.json()).must_change_password).toBe(false);
  const old = await request.post(`${API_URL}/auth/login`, { data: { username: fixtureUsername(email), password: PASSWORD } });
  expect(old.status()).toBe(401);
  await page.reload();
  await expect(page).toHaveURL(/\/diary$/);
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toHaveCount(0);
});

test("@issue111 reloading initial change requires login without persisting the initial password", async ({ page }) => {
  const email = actor(true);
  await signIn(page, email);
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toBeVisible();
  expect(await page.evaluate(secret => [...Object.values(localStorage), ...Object.values(sessionStorage)].some(value => value.includes(secret)), PASSWORD)).toBe(false);
  await page.reload();
  await expect(page.getByRole("heading", { name: "تسجيل الدخول", exact: true })).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key) === null, SESSION_TOKEN_KEY)).toBe(true);
  await signIn(page, email);
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toBeVisible();
});

test("@issue111 initial-change logout revokes its bearer session", async ({ page, request }) => {
  await signIn(page, actor(true));
  await expect(page.getByRole("heading", { name: "تغيير كلمة المرور", exact: true })).toBeVisible();
  const token = await storedToken(page);
  await page.getByRole("button", { name: "تسجيل الخروج", exact: true }).click();
  await expect(page.getByRole("heading", { name: "تسجيل الدخول", exact: true })).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key) === null, SESSION_TOKEN_KEY)).toBe(true);
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(token) })).status()).toBe(401);
});

test("@issue111 Profile change requires current password and revokes only other sessions", async ({ page, request }) => {
  const email = actor();
  const other = await internalLogin(email, PASSWORD);
  await applyProfileThroughTargetPlan(request, other.access_token, {
    sex: "male", birth_date: "1990-01-01", height_cm: 175, weight_kg: 80,
    activity_level: "moderate", goal: "maintain", protein_per_kg: 1.2, fat_pct: 0.25, selected_cut_intensity: 0.2,
  });
  await signIn(page, email, PASSWORD, "/profile");
  await expect(page).toHaveURL(/\/profile$/);
  const current = await storedToken(page);
  await page.getByLabel("كلمة المرور الحالية", { exact: true }).fill("Wrong-password-2026!");
  await page.getByLabel("كلمة المرور الجديدة", { exact: true }).fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "تغيير كلمة المرور", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "كلمة المرور الحالية غير صحيحة." })).toBeVisible();
  await expect(page.getByLabel("كلمة المرور الحالية", { exact: true })).toBeFocused();
  await page.getByLabel("كلمة المرور الحالية", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "تغيير كلمة المرور", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "تم تغيير كلمة المرور." })).toBeVisible();
  await expect(page.getByLabel("كلمة المرور الحالية", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("كلمة المرور الجديدة", { exact: true })).toHaveValue("");
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(current) })).status()).toBe(200);
  expect((await request.get(`${API_URL}/account/me`, { headers: headers(other.access_token) })).status()).toBe(401);
});
