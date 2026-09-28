import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("@p0 Admin manages a user and confirms permanent deletion by email", async ({ page }) => {
  const email = `lifecycle-${Date.now()}@example.test`;
  await page.goto("/admin/accounts");
  await expect(page.getByRole("heading", { name: "إدارة المستخدمين" })).toBeVisible();
  const form = page.locator(".account-management > .section-panel form").first();
  await form.getByLabel("البريد الإلكتروني").fill(email);
  await form.getByLabel("الاسم المعروض").fill("اختبار دورة الحياة");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  const row = page.locator(".account-row").filter({ hasText: email });
  await expect(row).toContainText("نشط");

  await row.getByRole("button", { name: "تعديل المستخدم" }).click();
  const editor = page.locator(".account-editor");
  await editor.getByLabel("الاسم المعروض").fill("اسم جديد");
  await editor.getByRole("button", { name: "حفظ التغييرات" }).click();
  await expect(row).toContainText("اسم جديد");

  await row.getByRole("button", { name: "إعادة تعيين كلمة المرور" }).click();
  await editor.getByLabel("كلمة المرور الجديدة").fill("New-password-2026!");
  await editor.getByRole("button", { name: "إعادة تعيين كلمة المرور" }).click();
  await expect(editor).toHaveCount(0);
  await expect(page.getByRole("status")).toHaveText("تمت إعادة تعيين كلمة المرور.");

  await row.getByRole("button", { name: "تعطيل المستخدم" }).click();
  await expect(row).toContainText("معطّل");
  await row.getByRole("button", { name: "تفعيل المستخدم" }).click();
  await expect(row).toContainText("نشط");

  await row.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
  await expect(dialog).toBeVisible();
  const confirmation = dialog.getByLabel("اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.");
  await expect(confirmation).toBeFocused();
  await confirmation.fill("wrong@example.test");
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("البريد الإلكتروني المدخل لا يطابق بريد المستخدم.");
  await expect(row).toBeVisible();
  await confirmation.fill(email);
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(row).toHaveCount(0);
});

test("Admin account page is RTL, keyboard reachable, and accessible on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin/accounts");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("button", { name: "إنشاء المستخدم" })).toBeVisible();
  const findings = await new AxeBuilder({ page }).analyze();
  expect(findings.violations).toEqual([]);
});

test("incomplete creation and deletion have retry actions", async ({ page }) => {
  await page.goto("/admin/accounts");
  const form = page.locator(".account-management > .section-panel form").first();
  const createEmail = `incomplete-create-${Date.now()}@example.test`;
  await form.getByLabel("البريد الإلكتروني").fill(createEmail);
  await form.getByLabel("الاسم المعروض").fill("اختبار الإنشاء");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(page.getByRole("status")).toContainText("تعذر إكمال إنشاء المستخدم. أعد المحاولة.");
  await page.reload();
  const createRow = page.locator(".account-row").filter({ hasText: createEmail });
  await expect(createRow).toContainText("قيد الإنشاء");
  await createRow.getByRole("button", { name: "إعادة محاولة الإنشاء" }).click();
  await page.locator(".account-editor").getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await page.locator(".account-editor").getByRole("button", { name: "إعادة محاولة الإنشاء" }).click();
  await expect(createRow).toContainText("نشط");

  const deleteEmail = `incomplete-delete-${Date.now()}@example.test`;
  await form.getByLabel("البريد الإلكتروني").fill(deleteEmail);
  await form.getByLabel("الاسم المعروض").fill("اختبار الحذف");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  const deleteRow = page.locator(".account-row").filter({ hasText: deleteEmail });
  await expect(deleteRow).toContainText("نشط");
  await deleteRow.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
  await dialog.getByLabel("اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.").fill(deleteEmail);
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog.getByRole("alert")).toContainText("تعذر إكمال حذف المستخدم. حسابه معطّل ويمكنك إعادة المحاولة.");
  await dialog.getByRole("button", { name: "إلغاء" }).click();
  await page.reload();
  await expect(deleteRow).toContainText("حذف غير مكتمل");
  await deleteRow.getByRole("button", { name: "إعادة محاولة الحذف" }).click();
  await expect(deleteRow).toHaveCount(0);
});

test("changing create identity rotates the idempotency key", async ({ page }) => {
  const keys: string[] = [];
  await page.route("**/admin/accounts", async route => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    await route.fulfill({ status: 503, json: { error: { code: "CREATION_INCOMPLETE", message_ar: "تعذر إكمال إنشاء المستخدم. أعد المحاولة." } } });
  });
  await page.goto("/admin/accounts");
  const form = page.locator(".account-management > .section-panel form").first();
  await form.getByLabel("البريد الإلكتروني").fill("first@example.test");
  await form.getByLabel("الاسم المعروض").fill("First");
  await form.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(1);
  await form.getByLabel("البريد الإلكتروني").fill("second@example.test");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(2);
  await form.getByLabel("الاسم المعروض").fill("Second");
  await form.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect.poll(() => keys.length).toBe(3);
  expect(new Set(keys).size).toBe(3);
});
