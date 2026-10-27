import { expect, test, type Page } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const id = "00000000-0000-4000-8000-000000000108";
const account = { principal_id: id, display_name: "مستخدم تجريبي", email: "issue108@example.test", status: "active", role: "user", created_at: "2026-10-17T12:00:00Z", disabled_at: null };
const counts = { active: 35, disabled: 2, provisioning: 0, deleting: 0 };
async function list(page: Page) {
  await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: [account], total: 35, page_size: 20, page: Number(new URL(route.request().url()).searchParams.get("page") ?? 1), counts } }));
}
async function detail(page: Page) {
  await page.route(`${API}/admin/users/${id}`, route => route.fulfill({ json: {
    account, age: 36, profile: { sex: "female", weight_kg: 65, height_cm: 165, goal: "maintain", activity_level: "light" },
    current_target: { targets: { calories: 2000, protein_g: 100, carb_g: 250, fat_g: 67 }, plan: { effective_from: "2026-10-17", revision: 2, created_at: "2026-10-16T12:00:00Z" } },
    plan_history: { items: [{ id: "plan", effective_from: "2026-10-17", revision: 2, created_at: "2026-10-16T12:00:00Z" }], next_cursor: null }
  } }));
  await page.route(`${API}/admin/users/${id}/diary?*`, route => route.fulfill({ json: {
    items: [{ id: "entry", entry_date: new URL(route.request().url()).searchParams.get("entry_date") ?? "2026-10-17", meal_type: "breakfast", quantity: 1, food_name: "حليب", recorded_unit_type: "cup", recorded_unit_amount: 240, recorded_unit_basis: "ml", recorded_unit_label: null }], next_cursor: null
  } }));
  await page.route(`${API}/admin/users/${id}/diary/summaries?*`, route => route.fulfill({ json: [{ date: new URL(route.request().url()).searchParams.get("dates"), totals: { calories: 120, protein_g: 8, carb_g: 12, fat_g: 4 }, targets: { calories: 2000, protein_g: 100, carb_g: 250, fat_g: 67 } }] }));
}

test("Admin list debounces search and preserves search filter page through details", async ({ page }) => {
  await list(page); await detail(page);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin\/users$/);
  await expect(page.getByRole("link", { name: "الإدارة", exact: true })).toHaveAttribute("href", "/admin/users");
  await expect(page.locator(".account-self-row")).toBeVisible();
  await expect(page.locator(".admin-results-count")).toHaveText("عرض 1-20 من 35 مستخدمًا");
  await expect(page.locator(".admin-account-counts")).toContainText("نشط: 35");
  await expect(page.locator(".admin-account-counts .account-status-provisioning")).toHaveCount(0);
  await page.getByLabel("البحث بالاسم أو البريد").fill("تجريبي");
  await expect(page).toHaveURL(/search=/);
  await expect(page.locator(".account-self-row")).toHaveCount(0);
  await page.getByLabel("حالة الحساب").selectOption("active");
  await page.getByRole("button", { name: "التالي", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.locator(".admin-results-count")).toHaveText("عرض 21-35 من 35 مستخدمًا");
  const rowLink = page.locator("a.account-identity");
  await expect(rowLink.locator("svg")).toHaveCount(1);
  await rowLink.click();
  await expect(page.getByRole("heading", { name: "تفاصيل المستخدم" })).toBeVisible();
  await page.getByRole("link", { name: "رجوع", exact: true }).click();
  await expect(page).toHaveURL(/status=active&page=2/);
  await expect(page.getByLabel("البحث بالاسم أو البريد")).toHaveValue("تجريبي");
  await page.getByRole("button", { name: "مسح البحث" }).click();
  await expect(page).toHaveURL(/users\?status=active$/);
  await expect(page.locator(".account-self-row")).toHaveCount(0);
  await page.getByLabel("حالة الحساب").selectOption("");
  await expect(page.locator(".account-self-row")).toBeVisible();
});

test("cancel clears all add fields and disable requires confirmation with date fallback", async ({ page }) => {
  let disabled = false, writes = 0;
  await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: [{ ...account, status: disabled ? "disabled" : "active", disabled_at: disabled ? "2026-10-17T12:00:00Z" : null }, { ...account, principal_id: `${id}-legacy`, email: "legacy@example.test", status: "disabled" }], total: 2, page_size: 20, page: 1, counts } }));
  await page.route(`${API}/admin/accounts/${id}/status`, route => { writes++; disabled = route.request().postDataJSON().enabled === false; return route.fulfill({ json: { ...account, status: disabled ? "disabled" : "active" } }); });
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  const add = page.getByRole("dialog", { name: "إضافة مستخدم" });
  await add.getByLabel("البريد الإلكتروني").fill("discard@example.test");
  await add.getByLabel("الاسم المعروض").fill("مؤقت");
  await add.getByLabel("كلمة المرور الأولية").fill("discard-password");
  await add.getByRole("button", { name: "إلغاء", exact: true }).click();
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  for (const label of ["البريد الإلكتروني", "الاسم المعروض", "كلمة المرور الأولية"]) await expect(add.getByLabel(label)).toHaveValue("");
  await add.getByRole("button", { name: "إلغاء", exact: true }).click();
  const row = page.locator(".account-row").filter({ hasText: account.email });
  await row.getByRole("button", { name: /^إجراءات/ }).click();
  await page.getByRole("menuitem", { name: "تعطيل المستخدم", exact: true }).click();
  const confirm = page.getByRole("dialog", { name: "تعطيل المستخدم؟" });
  await expect(confirm).toBeVisible(); expect(writes).toBe(0);
  await confirm.getByRole("button", { name: "إلغاء", exact: true }).click();
  expect(writes).toBe(0);
  await expect(row.getByRole("button", { name: /^إجراءات/ })).toBeFocused();
  await row.getByRole("button", { name: /^إجراءات/ }).click();
  await page.getByRole("menuitem", { name: "تعطيل المستخدم", exact: true }).click();
  await confirm.getByRole("button", { name: "تعطيل المستخدم", exact: true }).click();
  await expect(row).toContainText("معطّل منذ 17 أكتوبر 2026");
  await expect(page.locator(".account-row").filter({ hasText: "legacy@example.test" })).not.toContainText("معطّل منذ");
  expect(writes).toBe(1);
});

test("stuck accounts show counts guidance and the exact early-deletion error", async ({ page }) => {
  await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: [{ ...account, status: "provisioning" }], total: 1, page_size: 20, page: 1, counts: { ...counts, provisioning: 1, deleting: 2 } } }));
  await page.route(`${API}/admin/accounts/${id}`, route => route.fulfill({ status: 409, json: { error: { code: "CREATION_IN_PROGRESS" } } }));
  await page.goto("/admin/users");
  await expect(page.locator(".admin-account-counts .account-status-provisioning")).toContainText("قيد الإنشاء: 1 · تنتظر إعادة المحاولة");
  await expect(page.locator(".admin-account-counts .account-status-deleting")).toContainText("حذف غير مكتمل: 2 · تنتظر إعادة المحاولة");
  const row = page.locator(".account-row").filter({ hasText: account.email });
  await expect(row).toContainText("أعد المحاولة، أو احذف الحساب وأنشئه من جديد");
  await row.getByRole("button", { name: /^إجراءات/ }).click();
  await page.getByRole("menuitem", { name: "حذف المستخدم نهائيًا" }).click();
  const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
  await dialog.getByLabel("اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.").fill(account.email);
  await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
  await expect(dialog.getByRole("alert")).toHaveText("لا يمكن حذف المستخدم الآن لأن إنشاءه ما زال جاريًا. حاول بعد 5 دقائق.");
});

test("details display demographics targets dated totals and units without nutrition writes", async ({ page }) => {
  await detail(page);
  const writes: string[] = [];
  page.on("request", request => { if (request.url().startsWith(`${API}/admin/users/`) && request.method() !== "GET") writes.push(request.method()); });
  await page.goto(`/admin/users/${id}`);
  const profile = page.locator("#admin-section-profile");
  for (const text of ["الجنس", "أنثى", "العمر", "36 سنة", "65 كجم", "165 سم"]) await expect(profile).toContainText(text);
  const target = page.locator("#admin-section-target");
  for (const text of ["2000", "100", "250", "67", "الكربوهيدرات", "تاريخ السريان", "النسخة", "تاريخ إنشاء الخطة"]) await expect(target).toContainText(text);
  await expect(page.locator("#admin-section-plans")).toContainText("تاريخ إنشاء الخطة");
  const day = page.locator(".admin-diary-day");
  await expect(day).toContainText("1 كوب · 240 مل");
  await expect(day).toContainText("120 / 2000 سعرة");
  await expect(page.locator(".admin-detail-section").getByRole("button", { name: /حفظ|تعديل|حذف/ })).toHaveCount(0);
  await page.getByRole("button", { name: /^إجراءات/ }).click();
  await expect(page.getByRole("menuitem")).toHaveText(["إعادة تعيين كلمة المرور", "تعطيل المستخدم", "حذف المستخدم نهائيًا"]);
  await page.keyboard.press("Escape");
  await page.getByLabel("التاريخ", { exact: true }).fill("2026-10-18");
  await expect(day.locator("time")).toHaveAttribute("datetime", "2026-10-18");
  expect(writes).toEqual([]);
});


test("newer search text survives an earlier in-flight search response", async ({ page }) => {
  await list(page);
  await page.goto("/admin/users");
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const pending = new Promise<void>(resolve => { started = resolve; });
  await page.route(url => url.origin === new URL(API).origin && url.pathname === "/admin/accounts" && url.searchParams.get("search") === "a", async route => { started(); await held; await route.fulfill({ json: { items: [account], total: 1, page_size: 20, page: 1, counts } }); });
  try {
    const input = page.getByLabel("البحث بالاسم أو البريد");
    await input.fill("a");
    await pending;
    await input.fill("ab");
    release();
    await expect(page).toHaveURL(/search=ab/);
    await expect(input).toHaveValue("ab");
  } finally { release(); }
});

test("Escape keeps pending creation open and its failure visible", async ({ page }) => {
  await list(page);
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const pending = new Promise<void>(resolve => { started = resolve; });
  await page.route(`${API}/admin/accounts`, async route => { started(); await held; await route.fulfill({ status: 503, json: { error: { code: "CREATION_INCOMPLETE" } } }); });
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "إضافة مستخدم" }).click();
  const dialog = page.getByRole("dialog", { name: "إضافة مستخدم" });
  await dialog.getByLabel("البريد الإلكتروني").fill("pending@example.test");
  await dialog.getByLabel("الاسم المعروض").fill("قيد الإنشاء");
  await dialog.getByLabel("كلمة المرور الأولية").fill("Initial-password-2026!");
  try {
    await dialog.getByRole("button", { name: "إنشاء المستخدم" }).click();
    await pending;
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();
    release();
    await expect(dialog.getByRole("alert")).toHaveText("تعذر إكمال إنشاء المستخدم. أعد المحاولة.");
  } finally { release(); }
});

test("delete feedback survives the account leaving a filtered list", async ({ page }) => {
  let removed = false, fail = true;
  await page.route(`${API}/admin/accounts?*`, route => route.fulfill({ json: { items: removed ? [] : [account], total: removed ? 0 : 1, page_size: 20, page: 1, counts } }));
  await page.route(`${API}/admin/accounts/${id}`, route => {
    removed = true;
    return fail ? route.fulfill({ status: 503, json: { error: { code: "DELETION_INCOMPLETE" } } }) : route.fulfill({ json: { ...account, status: "deleted" } });
  });
  async function remove() {
    await page.getByRole("button", { name: /^إجراءات/ }).click();
    await page.getByRole("menuitem", { name: "حذف المستخدم نهائيًا" }).click();
    const dialog = page.getByRole("dialog", { name: "حذف المستخدم نهائيًا؟" });
    await dialog.getByLabel("اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.").fill(account.email);
    await dialog.getByRole("button", { name: "حذف المستخدم نهائيًا" }).click();
    return dialog;
  }
  await page.goto("/admin/users?status=active");
  const dialog = await remove();
  await expect(dialog.getByRole("alert")).toHaveText("تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة.");
  await expect(page.locator(".account-row")).toHaveCount(0);
  await dialog.getByRole("button", { name: "إلغاء", exact: true }).click();
  removed = false; fail = false;
  await page.reload();
  await remove();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("status")).toHaveText("تم حذف المستخدم نهائيًا.");
});
