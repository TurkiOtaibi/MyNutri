import { API_TOKEN, API_URL, expect, test, uniqueName } from "../foods/helpers";

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

async function selectDate(page: import("@playwright/test").Page, value: string) {
  const picker = page.getByLabel("اختيار تاريخ اليوميات");
  await expect(picker).toBeVisible();
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
  await picker.fill(value);
  await expect(picker).toHaveValue(value);
}

async function targetsForDate(request: import("@playwright/test").APIRequestContext, value: string) {
  const response = await request.get(`${API_URL}/target-plans/current?date=${value}`, {
    headers: { Authorization: `Bearer ${API_TOKEN}` }
  });
  expect(response.status()).toBe(200);
  const body = await response.json() as { targets: { target_calories: number; protein_g: number; carb_g: number; fat_g: number } | null };
  expect(body.targets).not.toBeNull();
  return body.targets!;
}

test.describe("@diary @page-refinement compact Diary page", () => {
  test("@p0 removes the repeated visible page title and keeps the compact current-date card first", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: "اليوميات", exact: true })).toHaveClass(/sr-only/);
    const week = page.locator(".compact-week-nav");
    await expect(week).toBeVisible();
    await expect(week.locator("h2")).not.toContainText(/\d{4}/);
    await expect(page.getByRole("button", { name: "اليوم", exact: true })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "التقدم اليومي" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "سجل اليوم" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "وجبات اليوم" })).toBeVisible();
    await expect(page.getByRole("button", { name: "إضافة طعام", exact: true })).toHaveCount(0);
    const navBox = await page.locator(".top-nav").boundingBox();
    const weekBox = await week.boundingBox();
    expect(navBox && weekBox && weekBox.y - (navBox.y + navBox.height)).toBeLessThanOrEqual(20);
  });

  test("@p0 another-year date includes year, Today returns home, and day arrows cross a Sunday boundary", async ({ page }) => {
    await page.goto("/diary");
    const picker = page.getByLabel("اختيار تاريخ اليوميات");
    await selectDate(page, "2025-12-31");
    await expect(page.locator(".compact-selected-date h2")).toContainText("2025");
    await expect(page.getByRole("button", { name: "اليوم", exact: true })).toBeVisible();
    await selectDate(page, "2026-07-05");
    await page.getByRole("button", { name: "اليوم السابق" }).click();
    await expect(picker).toHaveValue("2026-07-04");
    await expect(page.locator('[role="tab"][aria-current="date"]')).toHaveAttribute("aria-label", /السبت/);
    await page.getByRole("button", { name: "اليوم", exact: true }).click();
    await expect(picker).toHaveValue(localDate());
  });

  test("@p0 exact and above-target summaries use non-negative, clamped, accessible states", async ({ page, request, foodsApi }) => {
    const exactDate = localDate();
    const overDate = exactDate;
    const exactTargets = await targetsForDate(request, exactDate);
    const overTargets = await targetsForDate(request, overDate);
    const exact = await foodsApi.create({ name: uniqueName("Exact target"), calories: exactTargets.target_calories, protein_g: exactTargets.protein_g, carb_g: exactTargets.carb_g, fat_g: exactTargets.fat_g });
    const over = await foodsApi.create({ name: uniqueName("Over target"), calories: Math.min(3000, overTargets.target_calories + 300), protein_g: Math.min(300, overTargets.protein_g + 50), carb_g: Math.min(500, overTargets.carb_g + 50), fat_g: Math.min(300, overTargets.fat_g + 20) });
    const exactEntry = await foodsApi.createDiary(exact.id, exactDate, 1, "breakfast");
    await page.goto("/diary");
    await selectDate(page, exactDate);
    const summary = page.getByLabel("ملخص تقدم اليوم");
    await expect(summary.getByText("تم الوصول إلى الهدف")).toBeVisible();
    await expect(summary.getByRole("progressbar", { name: /100% من هدف السعرات/ })).toHaveAttribute("aria-valuenow", "100");
    await request.delete(`${API_URL}/diary/${exactEntry.id}`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
    await foodsApi.createDiary(over.id, overDate, 1, "lunch");
    await page.reload();
    await selectDate(page, overDate);
    await expect(summary.getByText(/\+\d+ فوق الهدف/)).toBeVisible();
    await expect(summary.getByText(/المتبقي -/)).toHaveCount(0);
    await expect(summary.getByRole("progressbar", { name: /هدف السعرات/ })).toHaveAttribute("aria-valuenow", "100");
    await expect(summary.getByLabel(/البروتين:.*فوق الهدف/)).toBeVisible();
    const width = await summary.locator(".diary-progress-track > span").evaluate((element) => getComputedStyle(element).width);
    expect(Number.parseFloat(width)).toBeLessThanOrEqual((await summary.locator(".diary-progress-track").boundingBox())!.width + 0.5);
  });

  test("@p0 empty day is compact, all meals are closed, and plus does not toggle its meal", async ({ page }) => {
    await page.goto("/diary");
    await selectDate(page, localDate(-240));
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toBeVisible();
    await expect(page.getByText("أضف طعامًا من زر + بجانب الوجبة المناسبة")).toBeVisible();
    const toggles = page.locator(".meal-toggle");
    await expect(toggles).toHaveCount(4);
    for (const toggle of await toggles.all()) await expect(toggle).toHaveAttribute("aria-expanded", "false");
    const breakfast = page.getByRole("button", { name: "فتح قسم فطور" });
    await expect(breakfast).toContainText("لا توجد أطعمة");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    await expect(page.getByRole("dialog", { name: "إضافة طعام" }).getByRole("heading", { name: "اختر الطعام" })).toBeVisible();
    await page.getByRole("dialog", { name: "إضافة طعام" }).getByRole("button", { name: "إلغاء" }).click();
    await expect(breakfast).toHaveAttribute("aria-expanded", "false");
  });

  test("@p0 expansion state is retained per date and first populated meal opens by default", async ({ page, foodsApi }) => {
    const firstDate = localDate(-220);
    const secondDate = localDate(-221);
    const food = await foodsApi.create({ name: uniqueName("Expansion") });
    await foodsApi.createDiary(food.id, firstDate, 1, "lunch");
    await page.goto("/diary");
    const picker = page.getByLabel("اختيار تاريخ اليوميات");
    await selectDate(page, firstDate);
    const lunch = page.getByRole("button", { name: "إغلاق قسم غداء" });
    await expect(lunch).toHaveAttribute("aria-expanded", "true");
    await page.getByRole("button", { name: "فتح قسم عشاء" }).click();
    await selectDate(page, secondDate);
    await expect(page.getByRole("button", { name: "فتح قسم غداء" })).toHaveAttribute("aria-expanded", "false");
    await selectDate(page, firstDate);
    await expect(page.getByRole("button", { name: "إغلاق قسم عشاء" })).toHaveAttribute("aria-expanded", "true");
  });

  test("@p0 compact Food row omits brand/macros, supports row edit, options, and delete failure recovery", async ({ page, foodsApi }) => {
    const date = localDate(-230);
    const food = await foodsApi.create({ name: uniqueName("Compact row mixed عربي"), brand: "Hidden Diary Brand", calories: 200 });
    await foodsApi.createDiary(food.id, date, 1, "breakfast");
    await page.goto("/diary");
    await selectDate(page, date);
    const breakfastToggle = page.locator("#meal-section-breakfast .meal-toggle");
    await expect(breakfastToggle).toContainText("طعام واحد");
    if ((await breakfastToggle.getAttribute("aria-expanded")) !== "true") await breakfastToggle.click();
    const row = page.locator(".diary-entry-row", { hasText: food.name });
    await expect(row).toContainText("200 سعرة");
    await expect(row).not.toContainText("Hidden Diary Brand");
    await expect(row).not.toContainText("بروتين");
    await row.click();
    await expect(page.getByRole("dialog", { name: "تعديل الكمية والقسم" })).toBeVisible();
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: `خيارات ${food.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await page.getByRole("menuitem", { name: "حذف" }).click();
    const dialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
    await expect(dialog).toContainText("سيُحذف هذا الطعام من سجل اليوم.");
    await dialog.getByRole("button", { name: "إبقاء الطعام" }).click();
    await expect(row).toBeVisible();
    await page.route("**/diary/*", (route) => route.request().method() === "DELETE" ? route.abort("failed") : route.continue());
    await page.getByRole("button", { name: `خيارات ${food.name}` }).click();
    await page.getByRole("menuitem", { name: "حذف" }).click();
    const failedDialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
    await failedDialog.getByRole("button", { name: "حذف" }).click();
    await expect(failedDialog.getByText("تعذر حذف الطعام")).toBeVisible();
    await expect(row).toBeVisible();
  });

  test("@p1 date loading and error states preserve navigation and avoid mismatched empty data", async ({ page }) => {
    let fail = false;
    await page.route("**/diary?entry_date=*", async (route) => {
      if (fail) return route.abort("failed");
      await new Promise((resolve) => setTimeout(resolve, 500));
      return route.continue();
    });
    await page.goto("/diary");
    await selectDate(page, localDate(-250));
    await expect(page.locator(".diary-entry-skeleton").first()).toBeVisible();
    await expect(page.locator(".compact-week-nav")).toBeVisible();
    await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
    fail = true;
    await selectDate(page, localDate(-251));
    await expect(page.getByText("تعذر تحميل بيانات هذا اليوم")).toBeVisible();
    await expect(page.getByText("تحقق من الاتصال ثم أعد المحاولة")).toBeVisible();
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "اليوم السابق" })).toBeEnabled();
    fail = false;
    await page.getByRole("button", { name: "إعادة المحاولة" }).last().click();
    await expect(page.getByText("تعذر تحميل بيانات هذا اليوم")).toHaveCount(0);
  });

  test("@p1 responsive Diary remains compact and overflow-free at supported mobile widths", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/diary");
      await expect(page.locator(".compact-week-day")).toHaveCount(7);
      await expect(page.locator(".macro-progress-row")).toHaveCount(3);
      await expect(page.getByRole("button", { name: "إضافة طعام إلى فطور" })).toHaveAttribute("aria-label", "إضافة طعام إلى فطور");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
      expect(await page.locator(".meal-add").first().evaluate((element) => Math.min(element.getBoundingClientRect().width, element.getBoundingClientRect().height))).toBeGreaterThanOrEqual(44);
    }
  });
});
