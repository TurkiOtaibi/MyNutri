import { expect, test } from "@playwright/test";
import { ADMIN_EMAIL, fixtureUsername, SESSION_TOKEN_KEY } from "./internal-auth";
import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext, Locator, Page } from "@playwright/test";


const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
async function createInternal(page: Page, request: APIRequestContext, username: string, displayName: string) {
  const token = await page.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY);
  const response = await request.post(`${API}/admin/accounts`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() },
    data: { username, display_name: displayName, initial_password: "Initial-password-2026!" },
  });
  expect(response.status()).toBe(201);
  return await response.json() as { principal_id: string };
}

async function openCreateDialog(page: Page): Promise<Locator> {
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة مستخدم" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("اسم المستخدم", { exact: true })).toBeFocused();
  return dialog;
}

async function chooseRowAction(page: Page, row: Locator, action: string) {
  await row.getByRole("button", { name: /^إجراءات / }).click();
  await page.getByRole("menuitem", { name: action }).click();
}

test("@p0 Admin manages a user and confirms permanent deletion by username", async ({ page }) => {
  const email = `lifecycle-${Date.now()}`;
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "إدارة المستخدمين" })).toBeVisible();
  const form = await openCreateDialog(page);
  await form.getByLabel("اسم المستخدم", { exact: true }).fill(email);
  await form.getByLabel("الاسم المعروض").fill("اختبار دورة الحياة");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(form).toHaveCount(0);
  await expect(page.getByRole("status")).toHaveText("تم إنشاء المستخدم.");
  const row = page.locator(".account-row").filter({ hasText: email });
  await expect(row).toContainText("نشط");

  await row.getByRole("button", { name: /^إجراءات / }).click();
  await row.getByRole("menuitem", { name: "تعديل المستخدم" }).click();
  const editor = page.locator(".account-editor");
  await expect(editor.getByLabel("الاسم المعروض")).toBeFocused();
  await editor.getByLabel("الاسم المعروض").fill("اسم جديد");
  await editor.getByRole("button", { name: "حفظ التغييرات" }).click();
  await expect(row).toContainText("اسم جديد");

  await chooseRowAction(page, row, "إعادة تعيين كلمة المرور");
  await editor.getByLabel("كلمة المرور الجديدة").fill("New-password-2026!");
  await editor.getByRole("button", { name: "إعادة تعيين كلمة المرور" }).click();
  await expect(editor).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "تمت إعادة تعيين كلمة المرور." })).toHaveText("تمت إعادة تعيين كلمة المرور.");

  await chooseRowAction(page, row, "تعطيل المستخدم");
  await page.getByRole("dialog", { name: "تعطيل المستخدم؟" }).getByRole("button", { name: "تعطيل المستخدم", exact: true }).click();
  await expect(row).toContainText("معطّل منذ");
  await chooseRowAction(page, row, "تفعيل المستخدم");
  await expect(row).toContainText("نشط");

  await chooseRowAction(page, row, "حذف المستخدم نهائيًا");
  const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
  await expect(dialog).toBeVisible();
  const confirmation = dialog.getByLabel("اكتب اسم المستخدم لتأكيد الحذف النهائي.");
  await expect(confirmation).toBeFocused();
  await confirmation.fill("wrong@example.test");
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("اسم المستخدم المدخل لا يطابق هذا الحساب.");
  await expect(row).toBeVisible();
  await confirmation.fill(email.toUpperCase());
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(row).toHaveCount(0);
});

test("Admin account page is RTL, keyboard reachable, and accessible on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin/users");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("button", { name: "إضافة مستخدم" })).toBeVisible();
  const findings = await new AxeBuilder({ page }).analyze();
  expect(findings.violations).toEqual([]);

  // CI shards start from an empty database, so create the row whose menu this test exercises.
  const email = `mobile-${Date.now()}`;
  const createForm = await openCreateDialog(page);
  await createForm.getByLabel("اسم المستخدم", { exact: true }).fill(email);
  await createForm.getByLabel("الاسم المعروض").fill("اختبار القائمة");
  await createForm.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await createForm.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(createForm).toHaveCount(0);
  const row = page.locator(".account-row").filter({ hasText: email });
  const menuButton = row.getByRole("button", { name: /^إجراءات / });
  await menuButton.click();
  await expect(page.getByRole("menuitem").first()).toBeFocused();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menu")).toHaveCount(0);
  await expect(menuButton).toBeFocused();

  const dialog = await openCreateDialog(page);
  await expect(dialog.getByLabel("اسم المستخدم", { exact: true })).toHaveAccessibleDescription("لا يمكن تغيير اسم المستخدم بعد إنشاء الحساب.");
  await expect(dialog.getByLabel("كلمة المرور الأولية")).toHaveAccessibleDescription("استخدم 8 أحرف على الأقل.");
  const box = await dialog.boundingBox();
  expect(box && box.x >= 0 && box.x + box.width <= 390).toBe(true);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("changing create identity rotates the idempotency key", async ({ page }) => {
  const keys: string[] = [];
  await page.route("**/admin/accounts", async route => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    await route.fulfill({ status: 503, json: { error: { code: "SERVICE_UNAVAILABLE", message_ar: "تعذر إكمال إنشاء المستخدم. أعد المحاولة." } } });
  });
  await page.goto("/admin/users");
  const form = await openCreateDialog(page);
  await form.getByLabel("اسم المستخدم", { exact: true }).fill("first.user");
  await form.getByLabel("الاسم المعروض").fill("First");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(1);
  await form.getByLabel("اسم المستخدم", { exact: true }).fill("second.user");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(2);
  await form.getByLabel("الاسم المعروض").fill("Second");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(3);
  expect(new Set(keys).size).toBe(3);
});

test("merged Users list redirects, searches, filters by status and marks the Admin's own row", async ({ page, request }) => {
  const suffix = Date.now();
  const activeUsername = `merged-active-${suffix}`;
  const disabledUsername = `merged-disabled-${suffix}`;
  await page.goto("/admin/accounts");
  await page.waitForURL(/\/admin\/users$/);
  await expect(page.getByRole("heading", { name: "إدارة المستخدمين" })).toBeVisible();

  const self = page.locator(".account-self-row");
  await expect(self).toContainText("(أنت)");
  await expect(self).toContainText(fixtureUsername(ADMIN_EMAIL));
  await expect(self.getByRole("button")).toHaveCount(0);
  await expect(self.getByRole("link")).toHaveCount(0);

  await createInternal(page, request, activeUsername, "بحث مدمج");
  const disabled = await createInternal(page, request, disabledUsername, "بحث مدمج معلق");
  const token = await page.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY);
  const response = await request.put(`${API}/admin/accounts/${disabled.principal_id}/status`, {
    headers: { Authorization: `Bearer ${token}` }, data: { enabled: false },
  });
  expect(response.status()).toBe(200);
  await page.reload();

  await page.getByPlaceholder("ابحث بالاسم أو اسم المستخدم...").fill(`merged-active-${suffix}`);

  await expect(page.locator(".account-row")).toHaveCount(1);
  const activeRow = page.locator(".account-row").filter({ hasText: activeUsername });
  await expect(activeRow).toContainText("آخر دخول");
  await expect(activeRow).not.toContainText("تاريخ التسجيل");
  await expect(self).toHaveCount(0);

  await page.getByPlaceholder("ابحث بالاسم أو اسم المستخدم...").fill(String(suffix));

  await expect(page.locator(".account-row")).toHaveCount(2);
  await page.getByLabel("حالة الحساب").selectOption("disabled");
  await expect(page.locator(".account-row")).toHaveCount(1);
  const disabledRow = page.locator(".account-row").filter({ hasText: disabledUsername });
  await expect(disabledRow).toContainText("معطّل");

  await page.getByLabel("حالة الحساب").selectOption("active");
  await activeRow.getByRole("link").click();
  await page.waitForURL(/\/admin\/users\/[^/]+$/);
  await expect(page.getByText("وضع قراءة فقط")).toBeVisible();
  const sections = page.getByRole("navigation", { name: "أقسام الصفحة" });
  await expect(sections.getByRole("link")).toHaveText(["ملخص الحساب", "الملف", "الأهداف المطبقة اليوم", "سجل الخطط", "اليوميات"]);
  await sections.getByRole("link", { name: "اليوميات" }).click();
  await expect(page).toHaveURL(/#admin-section-diary$/);
  await expect(page.getByRole("heading", { name: "اليوميات", exact: true })).toBeInViewport();
});

test("Admin home redirects directly to Users with account counts", async ({ page, request }) => {
  await page.goto("/admin/users");
  await createInternal(page, request, `home-${Date.now()}`, "اختبار القائمة");
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin\/users$/);
  await expect(page.getByRole("heading", { name: "إدارة المستخدمين" })).toBeVisible();
  await expect(page.locator(".admin-account-counts")).toContainText("نشط:");
});
