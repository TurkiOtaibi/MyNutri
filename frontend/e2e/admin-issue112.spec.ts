import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { ADMIN_EMAIL, ADMIN_PASSWORD, internalLogin, SESSION_TOKEN_KEY } from "./internal-auth";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const initialPassword = "Initial-password-2026!";
async function adminHeaders() {
  return { Authorization: `Bearer ${(await internalLogin(ADMIN_EMAIL, ADMIN_PASSWORD)).access_token}` };
}
async function create(request: APIRequestContext, username: string, name = "مستخدم اسم الدخول") {
  const response = await request.post(`${API}/admin/accounts`, {
    headers: { ...await adminHeaders(), "Idempotency-Key": crypto.randomUUID() },
    data: { username, display_name: name, initial_password: initialPassword },
  });
  expect(response.status()).toBe(201);
  return await response.json() as { principal_id: string };
}
async function action(page: Page, username: string, label: string) {
  const row = page.locator(".account-row").filter({ hasText: username });
  await row.getByRole("button", { name: /^إجراءات/ }).click();
  await page.getByRole("menuitem", { name: label, exact: true }).click();
}

test("internal Admin creation requires initial change and records last login in Riyadh", async ({ page, browser, request }) => {
  const username = `user_${Date.now()}`;
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة مستخدم" });
  await dialog.getByLabel("اسم المستخدم", { exact: true }).fill(username);
  await dialog.getByLabel("الاسم المعروض").fill("حساب داخلي جديد");
  await expect(dialog.getByLabel("الاسم المعروض")).toHaveAccessibleDescription("120 حرفًا كحد أقصى");
  await dialog.getByLabel("كلمة المرور الأولية").fill(initialPassword);
  await dialog.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(dialog).toHaveCount(0);
  const row = page.locator(".account-row").filter({ hasText: username });
  await expect(row).toContainText("لم يسجل الدخول بعد.");
  await expect(row).not.toContainText("حساب قديم");
  const context = await browser.newContext({ storageState: undefined });
  try {
    const owner = await context.newPage();
    await owner.goto("/auth/login?next=%2Ffoods");
    await owner.getByLabel("اسم المستخدم", { exact: true }).fill(username.toUpperCase());
    await owner.getByLabel("كلمة المرور", { exact: true }).fill(initialPassword);
    await owner.getByRole("button", { name: "دخول", exact: true }).click();
    await expect(owner.getByRole("heading", { name: "تغيير كلمة المرور" })).toBeVisible();
    await expect(owner.getByRole("link", { name: "الإدارة", exact: true })).toHaveCount(0);
    await owner.getByLabel("كلمة المرور الجديدة").fill("Changed-password-2026!");
    await owner.getByRole("button", { name: "حفظ كلمة المرور" }).click();
    await expect(owner).toHaveURL(/\/foods$/);
    const token = await owner.evaluate(key => localStorage.getItem(key), SESSION_TOKEN_KEY);
    expect((await request.get(`${API}/admin/accounts`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(403);
    await page.reload();
    await expect(row).toContainText("آخر دخول");
    await expect(row).not.toContainText("لم يسجل الدخول بعد.");
    await expect(row.locator("time")).toHaveCount(2);
  } finally { await context.close(); }
});

test("locked filter and reset unlock internal users and revoke all sessions", async ({ page, request }) => {
  const username = `lock_${Date.now()}`;
  await create(request, username);
  const session = await request.post(`${API}/auth/login`, { data: { username, password: initialPassword } });
  expect(session.status()).toBe(200);
  const token = (await session.json()).access_token as string;
  for (let i = 0; i < 5; i++) {
    const failure = await request.post(`${API}/auth/login`, { data: { username, password: "wrong-password" } });
    expect(failure.status()).toBe(401);
  }
  await page.goto(`/admin/users?search=${username}&status=locked`);
  const row = page.locator(".account-row").filter({ hasText: username });
  await expect(row).toContainText("مقفل");
  await expect(page.getByLabel("حالة الحساب")).toHaveValue("locked");
  await expect(page.locator(".account-self-row")).toHaveCount(0);
  await action(page, username, "إعادة تعيين كلمة المرور");
  const dialog = page.getByRole("dialog", { name: "إعادة تعيين كلمة المرور" });
  await expect(dialog).toContainText("سيخرج المستخدم من كل أجهزته.");
  await dialog.getByLabel("كلمة المرور الجديدة").fill("Reset-password-2026!");
  await dialog.getByRole("button", { name: "إعادة تعيين كلمة المرور", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(row).toHaveCount(0);
  await expect(page.getByLabel("حالة الحساب")).toBeFocused();
  expect((await request.get(`${API}/account/me`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(401);
  const login = await request.post(`${API}/auth/login`, { data: { username, password: "Reset-password-2026!" } });
  expect(login.status()).toBe(200);
  expect((await login.json()).account.must_change_password).toBe(false);
});

test("username search details immutable identity and uppercase deletion permit username reuse", async ({ page, request }) => {
  const username = `MiXeD_${Date.now()}`;
  const created = await create(request, username, "عرض فريد للحساب");
  await page.goto(`/admin/users?search=${username.toLowerCase()}`);
  const row = page.locator(".account-row").filter({ hasText: username });
  await expect(row).toBeVisible();
  await page.getByPlaceholder("ابحث بالاسم أو اسم المستخدم...").fill("عرض فريد");
  await expect(row).toBeVisible();
  await row.getByRole("link").click();
  const summary = page.locator("#admin-section-account");
  await expect(summary).toContainText("اسم المستخدم");
  await expect(summary).toContainText(username);
  await page.getByRole("button", { name: "تعديل المستخدم", exact: true }).click();
  const editor = page.getByRole("dialog", { name: "تعديل المستخدم" });
  await expect(editor.getByLabel("اسم المستخدم", { exact: true })).toHaveCount(0);
  await editor.getByRole("button", { name: "إلغاء" }).click();
  await page.getByRole("button", { name: /^إجراءات/ }).click();
  await page.getByRole("menuitem", { name: "حذف المستخدم نهائيًا" }).click();
  const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
  const confirm = dialog.getByLabel("اكتب اسم المستخدم لتأكيد الحذف النهائي.");
  await expect(dialog).toContainText("اكتب اسم المستخدم لتأكيد الحذف النهائي.");
  await confirm.fill("does-not-match");
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("اسم المستخدم المدخل لا يطابق هذا الحساب.");
  await confirm.fill(username.toUpperCase());
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(page).toHaveURL(/\/admin\/users/);
  await expect(dialog).toHaveCount(0);
  const replacement = await create(request, username.toLowerCase());
  expect(replacement.principal_id).not.toBe(created.principal_id);
});

test("create displays exact duplicate and short password errors without creating a pending account", async ({ page, request }) => {
  const username = `dup_${Date.now()}`;
  await create(request, username);
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة مستخدم" });
  await dialog.getByLabel("اسم المستخدم", { exact: true }).fill(username.toUpperCase());
  await dialog.getByLabel("الاسم المعروض").fill("اسم مكرر");
  await dialog.getByLabel("كلمة المرور الأولية").fill("short");
  await dialog.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.");
  await dialog.getByLabel("كلمة المرور الأولية").fill(initialPassword);
  await dialog.getByRole("button", { name: "إنشاء المستخدم" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("اسم المستخدم هذا مستخدم بالفعل.");
  await dialog.getByRole("button", { name: "إلغاء" }).click();
  await expect(page.locator(".account-row").filter({ hasText: username })).not.toContainText("قيد الإنشاء");
});
