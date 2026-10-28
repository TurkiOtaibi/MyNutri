import { expect, test } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const id = "00000000-0000-4000-8000-000000000138";

for (const failNext of [false, true]) {
  test(`BR-USM-057 loads all older plans with preserved metadata and retry=${failNext}`, async ({ page }) => {
    let fail = failNext;
    const cursors: string[] = [];
    const writes: string[] = [];
    page.on("request", request => {
      if (request.url().startsWith(`${API}/admin/users/`) && request.method() !== "GET") writes.push(request.method());
    });
    await page.route(url => url.origin === new URL(API).origin && url.pathname === `/admin/users/${id}`, async route => {
      const cursor = new URL(route.request().url()).searchParams.get("plan_cursor");
      if (cursor) cursors.push(cursor);
      if (cursor && fail) { fail = false; return route.fulfill({ status: 503, json: { error: { message_ar: "unavailable" } } }); }
      const offset = Number(cursor ?? 0);
      return route.fulfill({ json: {
        account: { principal_id: id, display_name: "مستخدم خطط", username: "plans.user", status: "active", role: "user" },
        profile: null, current_target: { plan: null, targets: null },
        plan_history: { items: Array.from({ length: Math.min(20, 42 - offset) }, (_, i) => ({
          id: `plan-${offset + i}`, revision: 42 - offset - i,
          effective_from: "2026-10-17", created_at: "2026-10-16T12:00:00Z",
        })), next_cursor: offset < 40 ? String(offset + 20) : null },
      } });
    });
    await page.route(`${API}/admin/users/${id}/diary?*`, route => route.fulfill({ json: { items: [], next_cursor: null } }));
    await page.goto(`/admin/users/${id}`);
    const history = page.locator("#admin-section-plans");
    await expect(history.locator("li")).toHaveCount(20);
    const first = history.locator("li").first();
    await expect(first.locator(".admin-field-effective_from dd")).toHaveText("17 أكتوبر 2026");
    await expect(first.locator(".admin-field-revision dd")).toHaveText("42");
    await expect(first.locator(".admin-field-plan_created_at dt")).toHaveText("تاريخ إنشاء الخطة");
    await expect(first.locator(".admin-field-plan_created_at dd")).toHaveText("16 أكتوبر 2026");
    await history.getByRole("button", { name: "عرض خطط أقدم" }).click();
    if (failNext) {
      await expect(history.getByRole("alert")).toContainText("تعذر تحميل سجل الخطط");
      await expect(history.locator("li")).toHaveCount(20);
      await expect(history.getByRole("button", { name: "إعادة المحاولة" })).toBeFocused();
      await history.getByRole("button", { name: "إعادة المحاولة" }).click();
    }
    await expect(history.locator("li")).toHaveCount(40);
    await history.getByRole("button", { name: "عرض خطط أقدم" }).click();
    await expect(history.locator("li")).toHaveCount(42);
    await expect(history.locator("li").last().locator(".admin-field-revision dd")).toHaveText("1");
    await expect(history.getByRole("button", { name: "عرض خطط أقدم" })).toHaveCount(0);
    await expect(history.getByRole("heading", { name: "سجل الخطط" })).toBeFocused();
    expect(cursors).toEqual(failNext ? ["20", "20", "40"] : ["20", "40"]);
    expect(writes).toEqual([]);
  });
}

test("BR-USM-057 empty history has no older-plans action", async ({ page }) => {
  await page.route(`${API}/admin/users/${id}`, route => route.fulfill({ json: {
    account: { principal_id: id, display_name: "مستخدم خطط", username: "plans.user", status: "active", role: "user" },
    profile: null, current_target: { plan: null, targets: null }, plan_history: { items: [], next_cursor: null },
  } }));
  await page.route(`${API}/admin/users/${id}/diary?*`, route => route.fulfill({ json: { items: [], next_cursor: null } }));
  await page.goto(`/admin/users/${id}`);
  const history = page.locator("#admin-section-plans");
  await expect(history).toContainText("لا توجد خطط محفوظة.");
  await expect(history.getByRole("button")).toHaveCount(0);
});
