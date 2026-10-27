import { expect, test } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const id = "00000000-0000-4000-8000-000000000109";
const account = { principal_id: id, display_name: "مستخدم تجريبي", email: "issue109@example.test", status: "active", profile_complete: true };

for (const location of ["list", "details"]) {
  test(`sex correction from ${location} preserves warning, error, refresh and focus`, async ({ page }) => {
    let sex = "female", attempts = 0;
    await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: [account], total: 1, page_size: 20, page: 1, counts: { active: 1, disabled: 0, provisioning: 0, deleting: 0 } } }));
    await page.route(`${API}/admin/users/${id}`, route => route.fulfill({ json: { account, profile: { sex }, current_target: { targets: null, plan: null }, plan_history: { items: [] } } }));
    await page.route(`${API}/admin/users/${id}/diary?*`, route => route.fulfill({ json: { items: [], next_cursor: null } }));
    await page.route(`${API}/admin/accounts/${id}/profile/sex`, route => {
      attempts++;
      expect(route.request().postDataJSON()).toEqual({ sex: "male" });
      if (attempts === 1) return route.fulfill({ status: 503, json: { error: { code: "FAILED" } } });
      sex = "male";
      return route.fulfill({ status: 204 });
    });
    await page.goto(location === "list" ? "/admin/users" : `/admin/users/${id}`);
    const opener = page.getByRole("button", { name: "إجراءات مستخدم تجريبي" });
    await opener.click();
    await page.getByRole("menuitem", { name: "تصحيح الجنس", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "تصحيح الجنس", exact: true });
    await expect(dialog).toContainText("تصحيح الجنس يغيّر حساب الأهداف وتقييم نتائج التحاليل.");
    await expect(dialog.getByLabel("أنثى", { exact: true })).toBeChecked();
    await dialog.getByLabel("ذكر", { exact: true }).check();
    await dialog.getByRole("button", { name: "حفظ التغييرات" }).click();
    await expect(dialog.getByRole("alert")).toHaveText("تعذر حفظ تغييرات المستخدم. حاول مرة أخرى.");
    await expect(dialog.getByRole("alert")).toBeFocused();
    await dialog.getByRole("button", { name: "حفظ التغييرات" }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole("status")).toContainText("تم حفظ تغييرات المستخدم.");
    await expect(opener).toBeFocused();
    if (location === "details") await expect(page.locator(".admin-field-sex dd")).toHaveText("ذكر");
  });
}

test("no Profile disables correction; cancel makes no write", async ({ page }) => {
  let writes = 0;
  await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: [{ ...account, profile_complete: false }, { ...account, principal_id: `${id}-saved`, display_name: "ملف محفوظ" }], total: 2, page_size: 20, page: 1, counts: { active: 2 } } }));
  await page.route(`${API}/admin/users/${id}-saved`, route => route.fulfill({ json: { profile: { sex: "female" } } }));
  await page.route(`${API}/admin/accounts/*/profile/sex`, route => { writes++; return route.fulfill({ status: 204 }); });
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "إجراءات مستخدم تجريبي" }).click();
  await expect(page.getByRole("menuitem", { name: "تصحيح الجنس" })).toBeDisabled();
  await expect(page.getByRole("menuitem", { name: "إعادة تعيين كلمة المرور" })).toBeFocused();
  await page.keyboard.press("Escape");
  const opener = page.getByRole("button", { name: "إجراءات ملف محفوظ" });
  await opener.click();
  await page.getByRole("menuitem", { name: "تصحيح الجنس" }).click();
  const dialog = page.getByRole("dialog", { name: "تصحيح الجنس" });
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  await expect(opener).toBeFocused();
  expect(writes).toBe(0);
});

test("Profile reload failure keeps the dialog dismissible and details visible", async ({ page }) => {
  let reads = 0;
  await page.route(`${API}/admin/users/${id}`, route => {
    reads++;
    return reads === 1
      ? route.fulfill({ json: { account, profile: { sex: "female" }, current_target: { targets: null, plan: null }, plan_history: { items: [] } } })
      : route.fulfill({ status: 503, json: { error: { code: "FAILED" } } });
  });
  await page.route(`${API}/admin/users/${id}/diary?*`, route => route.fulfill({ json: { items: [], next_cursor: null } }));
  await page.goto(`/admin/users/${id}`);
  await page.getByRole("button", { name: "إجراءات مستخدم تجريبي" }).click();
  await page.getByRole("menuitem", { name: "تصحيح الجنس" }).click();
  const dialog = page.getByRole("dialog", { name: "تصحيح الجنس" });
  await expect(dialog.getByRole("alert")).toHaveText("تعذر تحميل بيانات المستخدم.");
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "تفاصيل المستخدم" })).toBeVisible();
});
