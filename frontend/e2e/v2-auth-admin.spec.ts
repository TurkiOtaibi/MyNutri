import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

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

const PLAN025_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000025";
const plan025Detail = {
  account: { display_name: "مستخدم الاختبار", email: "plan025@example.test", status: "active", role: "user", created_at: "2026-08-01T12:00:00Z" },
  profile: null,
  current_target: null,
  pending_plan: null,
  plan_history: { items: [], next_cursor: null }
};
const plan025FirstPage = {
  items: [
    { id: "00000000-0000-0000-0000-000000000101", entry_date: "2026-08-01", meal_type: "breakfast", quantity: 1, food_name: "وجبة أولى" },
    { id: "00000000-0000-0000-0000-000000000102", entry_date: "2026-07-31", meal_type: "lunch", quantity: 2, food_name: "وجبة ثانية" }
  ],
  next_cursor: "cursor-plan025"
};
const plan025FinalPage = {
  items: [{ id: "00000000-0000-0000-0000-000000000103", entry_date: "2026-07-30", meal_type: "dinner", quantity: 3, food_name: "وجبة أخيرة" }],
  next_cursor: null
};

async function mockPlan025Detail(page: import("@playwright/test").Page, failNextPage = false) {
  let nextPageAttempts = 0;
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}`, (route) => route.fulfill({ json: plan025Detail }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, (route) => route.fulfill({ json: plan025FirstPage }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50&cursor=cursor-plan025`, (route) => {
    nextPageAttempts += 1;
    if (failNextPage && nextPageAttempts === 1) return route.fulfill({ status: 500, json: { detail: "failed" } });
    return route.fulfill({ json: plan025FinalPage });
  });
}

async function assertDiaryViewport(page: import("@playwright/test").Page) {
  const layout = await page.evaluate(() => {
    const root = document.documentElement;
    const visible = [...document.querySelectorAll<HTMLElement>(".section-panel button, .admin-readonly-list li, .state-note, [role='alert']")]
      .filter((element) => element.offsetParent !== null)
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return { left: rect.left, right: rect.right, width: rect.width, height: rect.height, tag: element.tagName };
      });
    const targets = [...document.querySelectorAll<HTMLButtonElement>(".section-panel button")]
      .filter((element) => element.offsetParent !== null)
      .map((element) => ({ width: element.getBoundingClientRect().width, height: element.getBoundingClientRect().height }));
    const hiddenFocusable = document.querySelectorAll("[aria-hidden='true'] button, [aria-hidden='true'] a, [hidden] button, [hidden] a").length;
    return { overflow: root.scrollWidth - root.clientWidth, viewport: innerWidth, visible, targets, hiddenFocusable };
  });
  expect(layout.overflow).toBeLessThanOrEqual(1);
  expect(layout.visible.every((box) => box.left >= -1 && box.right <= layout.viewport + 1)).toBe(true);
  expect(layout.targets.every((target) => target.width >= 44 && target.height >= 44)).toBe(true);
  expect(layout.hiddenFocusable).toBe(0);
}

async function assertAxe(page: import("@playwright/test").Page) {
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.filter((violation) => ["moderate", "serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
}

function plan025DiarySection(page: Page) {
  const heading = page.getByRole("heading", { name: "اليوميات", exact: true });
  return page.locator("section").filter({ has: heading });
}

function plan025DiaryAlert(page: Page) {
  return plan025DiarySection(page).getByRole("alert");
}

test("@plan025 admin diary renders bounded pages and keyboard load more", async ({ page }) => {
  await mockPlan025Detail(page);
  await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}`);
  await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
  await expect(plan025DiarySection(page)).toHaveCount(1);
  await expect(plan025DiarySection(page)).toBeVisible();
  const loadMore = page.getByRole("button", { name: "عرض المزيد" });
  await expect(loadMore).toBeVisible();
  await loadMore.click();
  await expect(page.getByText("وجبة أخيرة", { exact: true })).toBeVisible();
  await expect(page.getByText("لا توجد إدخالات أخرى.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /حفظ|تعديل|حذف/ })).toHaveCount(0);
});

test("@plan025 next-page failure retains entries and offers keyboard retry", async ({ page }) => {
  let nextPageAttempts = 0;
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}`, (route) => route.fulfill({ json: plan025Detail }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, (route) => route.fulfill({ json: plan025FirstPage }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50&cursor=cursor-plan025`, (route) => {
    nextPageAttempts += 1;
    if (nextPageAttempts === 1) return route.fulfill({ status: 500, json: { detail: "failed" } });
    return route.fulfill({ json: plan025FinalPage });
  });
  await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}`);
  const diarySection = plan025DiarySection(page);
  await expect(diarySection).toHaveCount(1);
  await expect(diarySection).toBeVisible();
  const loadMore = diarySection.getByRole("button", { name: "عرض المزيد", exact: true });
  await loadMore.press("Enter");
  await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
  const diaryAlert = plan025DiaryAlert(page);
  await expect(diaryAlert).toHaveCount(1);
  await expect(diaryAlert).toBeVisible();
  await expect(diaryAlert.getByText("تعذر تحميل المزيد من اليوميات.", { exact: true })).toBeVisible();
  const retry = diarySection.getByRole("button", { name: "إعادة محاولة تحميل المزيد", exact: true });
  await expect(retry).toBeFocused();
  await page.keyboard.press("Enter");
  await expect.poll(() => nextPageAttempts).toBe(2);
  await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
  await expect(page.getByText("وجبة أخيرة", { exact: true })).toBeVisible();
  await expect(diaryAlert).toHaveCount(0);
  await expect(diarySection.getByRole("button", { name: "إعادة محاولة تحميل المزيد", exact: true })).toHaveCount(0);
});

test("@plan025 initial failure focuses its retry and keyboard retry makes one request", async ({ page }) => {
  let initialAttempts = 0;
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}`, (route) => route.fulfill({ json: plan025Detail }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, (route) => {
    initialAttempts += 1;
    if (initialAttempts === 1) return route.fulfill({ status: 500, json: { detail: "failed" } });
    return route.fulfill({ json: { items: [], next_cursor: null } });
  });
  await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}`);
  const diarySection = plan025DiarySection(page);
  await expect(diarySection).toHaveCount(1);
  await expect(diarySection).toBeVisible();
  const diaryAlert = plan025DiaryAlert(page);
  await expect(diaryAlert).toHaveCount(1);
  await expect(diaryAlert).toBeVisible();
  await expect(diaryAlert).toHaveText("تعذر تحميل اليوميات.");
  const retry = diarySection.getByRole("button", { name: "إعادة المحاولة", exact: true });
  await expect(retry).toBeFocused();
  await page.keyboard.press("Enter");
  await expect.poll(() => initialAttempts).toBe(2);
  await expect(page.getByText("لا توجد إدخالات يومية.", { exact: true })).toBeVisible();
  await expect(diaryAlert).toHaveCount(0);
});

test("@plan025 Diary loading is a held request with no stale state", async ({ page }) => {
  let requestPending = false;
  let releaseRequest: (() => void) | undefined;
  const held = new Promise<void>((resolve) => { releaseRequest = resolve; });
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}`, (route) => route.fulfill({ json: plan025Detail }));
  await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, async (route) => {
    requestPending = true;
    await held;
    await route.fulfill({ json: plan025FirstPage });
  });
  try {
    await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}`);
    await expect.poll(() => requestPending).toBe(true);
    const diarySection = plan025DiarySection(page);
    await expect(diarySection).toHaveCount(1);
    await expect(diarySection).toBeVisible();
    await expect(page.getByText("جارٍ التحميل...", { exact: true })).toBeVisible();
    await expect(page.getByText("وجبة أولى", { exact: true })).toHaveCount(0);
    await expect(page.getByText("لا توجد إدخالات يومية.", { exact: true })).toHaveCount(0);
    await expect(plan025DiaryAlert(page)).toHaveCount(0);
    await assertAxe(page);
  } finally {
    releaseRequest?.();
  }
  await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
  await expect(plan025DiaryAlert(page)).toHaveCount(0);
});

test("@plan025 Diary accessibility matrix covers each applicable state and viewport", async ({ page }) => {
  test.setTimeout(120_000);
  const viewports = [320, 360, 390, 430, 1280];
  const states = ["loaded", "loading", "error", "empty"] as const;
  for (const state of states) {
    for (const width of viewports) {
      await page.unrouteAll({ behavior: "wait" });
      await page.setViewportSize({ width, height: 700 });
      await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}`, (route) => route.fulfill({ json: plan025Detail }));
      if (state === "loading") {
        let releaseRequest: (() => void) | undefined;
        const held = new Promise<void>((resolve) => { releaseRequest = resolve; });
        await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, async (route) => {
          await held;
          await route.fulfill({ json: plan025FirstPage });
        });
        try {
          await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}?matrix=${state}-${width}`);
          const diarySection = plan025DiarySection(page);
          await expect(diarySection).toHaveCount(1);
          await expect(diarySection).toBeVisible();
          await expect(page.getByText("جارٍ التحميل...", { exact: true })).toBeVisible();
          await expect(page.getByText("وجبة أولى", { exact: true })).toHaveCount(0);
          await expect(plan025DiaryAlert(page)).toHaveCount(0);
          await assertDiaryViewport(page);
          await assertAxe(page);
        } finally {
          releaseRequest?.();
        }
        await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
        await expect(plan025DiaryAlert(page)).toHaveCount(0);
      } else {
        const diaryResponse = state === "loaded" ? plan025FirstPage : state === "empty" ? { items: [], next_cursor: null } : undefined;
        await page.route(`${API_URL}/admin/users/${PLAN025_PRINCIPAL_ID}/diary?limit=50`, (route) => diaryResponse ? route.fulfill({ json: diaryResponse }) : route.fulfill({ status: 500, json: { detail: "failed" } }));
        await page.goto(`/admin/users/${PLAN025_PRINCIPAL_ID}?matrix=${state}-${width}`);
        const diarySection = plan025DiarySection(page);
        await expect(diarySection).toHaveCount(1);
        await expect(diarySection).toBeVisible();
        const diaryAlert = plan025DiaryAlert(page);
        if (state === "loaded") {
          await expect(page.getByText("وجبة أولى", { exact: true })).toBeVisible();
          await expect(diaryAlert).toHaveCount(0);
        } else if (state === "empty") {
          await expect(page.getByText("لا توجد إدخالات يومية.", { exact: true })).toBeVisible();
          await expect(diaryAlert).toHaveCount(0);
        } else {
          await expect(diaryAlert).toHaveCount(1);
          await expect(diaryAlert).toBeVisible();
          await expect(diaryAlert).toHaveText("تعذر تحميل اليوميات.");
          await expect(diarySection.getByRole("button", { name: "إعادة المحاولة", exact: true })).toBeFocused();
        }
        await assertDiaryViewport(page);
        await assertAxe(page);
      }
    }
  }
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
