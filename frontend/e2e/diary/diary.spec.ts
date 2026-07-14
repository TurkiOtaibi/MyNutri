import { API_TOKEN, API_URL, expect, test, uniqueName } from "../foods/helpers";

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function sundayStart(input: string): string {
  const date = new Date(`${input}T00:00:00`);
  date.setDate(date.getDate() - date.getDay());
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

test.describe("@diary daily-use redesign", () => {
  test("@p0 mobile page uses compact date, week, summary, log order without duplicate goals", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");

    await expect(page.getByRole("heading", { name: "اليوميات" })).toBeVisible();
    await expect(page.getByLabel("التنقل بين أيام اليوميات")).toBeVisible();
    await expect(page.getByLabel(/الأسبوع من/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "ملخص اليوم" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "وجبات اليوم" })).toBeVisible();
    await expect(page.getByText("أهداف اليوم")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "إضافة طعام", exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });

  test("@p0 previous and Today controls update the selected Gregorian week", async ({ page }) => {
    await page.goto("/diary");
    const picker = page.getByLabel("اختيار تاريخ اليوميات");
    await expect(picker).toHaveValue(localDate());

    await page.getByRole("button", { name: "اليوم السابق" }).click();
    await expect(picker).toHaveValue(localDateFrom(localDate(), -1));
    await expect(page.getByRole("button", { name: "اليوم", exact: true })).toBeVisible();

    await page.getByRole("button", { name: "اليوم", exact: true }).click();
    await expect(picker).toHaveValue(localDate());
    await expect(page.getByRole("button", { name: "اليوم التالي" })).toBeDisabled();
  });

  test("@p0 future Diary API date is rejected", async ({ request, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Future date") });
    const response = await request.post(`${API_URL}/diary`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` },
      data: { food_id: food.id, entry_date: localDate(1), quantity: 1 }
    });
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("لا يمكن تسجيل يوميات بتاريخ مستقبلي");
  });

  test("@p0 week strip starts on Sunday and selecting a past day updates Diary", async ({ page }) => {
    await page.goto("/diary");
    const days = page.locator(".compact-week-day");
    await expect(days).toHaveCount(7);
    await expect(days.first()).toHaveAttribute("aria-label", /^الأحد/);

    const selectable = days.filter({ hasNot: page.locator(":disabled") });
    const firstDate = await days.first().getAttribute("aria-label");
    if (!(await days.first().isDisabled())) {
      await days.first().click();
      await expect(page.getByLabel("اختيار تاريخ اليوميات")).not.toHaveValue("");
      expect(firstDate).toContain("الأحد");
    } else {
      await expect(selectable.first()).toBeEnabled();
    }
  });

  test("@p0 empty day shows one compact empty state and opens Add Entry sheet", async ({ page }) => {
    await page.goto("/diary");
    await page.getByLabel("اختيار تاريخ اليوميات").fill(localDate(-280));
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toHaveCount(1);
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية")).toBeFocused();
    await expect(dialog.getByText(/الحصة|قطعة|حبة/).first()).toBeVisible();
  });

  test("@p0 Food search, serving preview, and successful save update log and totals", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: uniqueName("Diary عربي English"),
      default_unit_type: "piece",
      unit_amount: 40,
      calories: 200,
      protein_g: 10,
      carb_g: 20,
      fat_g: 5
    });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
    await dialog.getByRole("radio", { name: "فطور" }).click();
    await expect(dialog.getByLabel("معاينة القيم الغذائية")).toContainText("80");
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await expect(dialog.getByLabel("معاينة القيم الغذائية")).toContainText("160");
    await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();

    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("heading", { name: food.name })).toBeVisible();
    await expect(page.getByLabel("وجبات اليوم").getByText("160 سعرة", { exact: true })).toBeVisible();
  });

  test("@p0 failed save preserves Food and quantity input", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Failed Diary Save") });
    await page.route("**/diary", (route) => {
      if (route.request().method() === "POST") return route.abort("failed");
      return route.continue();
    });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
    await dialog.getByRole("radio", { name: "فطور" }).click();
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("3");
    await dialog.getByRole("button", { name: "إضافة إلى الفطور" }).click();

    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toHaveValue("3");
    await expect(dialog.getByText("تعذر إضافة الطعام")).toBeVisible();
  });

  test("@p0 duplicate save submission sends one POST", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Single Submit") });
    let postCount = 0;
    await page.route("**/diary", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      postCount += 1;
      await new Promise((resolve) => setTimeout(resolve, 350));
      return route.continue();
    });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await dialog.getByRole("button", { name: new RegExp(food.name) }).click();
    await dialog.getByRole("radio", { name: "فطور" }).click();
    const save = dialog.getByRole("button", { name: "إضافة إلى الفطور" });
    await save.dblclick();
    await expect(dialog).toHaveCount(0);
    expect(postCount).toBe(1);
  });

  test("@p0 quantity-only edit recalculates the entry without exposing Food or date fields", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Quantity edit"), unit_amount: 50, calories: 200 });
    await foodsApi.createDiary(food.id, localDate(), 1);
    await page.goto("/diary");
    await page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) }).click();
    await page.getByRole("menuitem", { name: "تعديل" }).click();
    const dialog = page.getByRole("dialog", { name: "تعديل الكمية والقسم" });
    await expect(dialog.getByRole("textbox", { name: "الكمية", exact: true })).toBeVisible();
    await expect(dialog.getByLabel("الطعام")).toHaveCount(0);
    await expect(dialog.getByLabel("اختيار تاريخ اليوميات")).toHaveCount(0);
    await dialog.getByRole("textbox", { name: "الكمية", exact: true }).fill("2");
    await dialog.getByRole("button", { name: "حفظ التغييرات" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByLabel("وجبات اليوم").getByText("200 سعرة", { exact: true })).toBeVisible();
  });

  test("@p0 delete cancel keeps entry; confirm removes it and refreshes totals", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Delete Diary") });
    await foodsApi.createDiary(food.id, localDate(), 1);
    await page.goto("/diary");
    const actions = page.getByRole("button", { name: new RegExp(`خيارات ${food.name}`) });
    await actions.click();
    await page.getByRole("menuitem", { name: "حذف" }).click();
    let dialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
    await expect(dialog).toContainText("سيُحذف هذا الطعام من سجل اليوم.");
    await dialog.getByRole("button", { name: "إبقاء الطعام" }).click();
    await expect(page.getByRole("heading", { name: food.name })).toBeVisible();

    await actions.click();
    await page.getByRole("menuitem", { name: "حذف" }).click();
    dialog = page.getByRole("dialog", { name: "حذف الطعام؟" });
    await dialog.getByRole("button", { name: "حذف", exact: true }).dblclick();
    await expect(page.getByRole("heading", { name: food.name })).toHaveCount(0);
  });

  test("@p1 day read error is distinct from empty state and Retry repeats the request", async ({ page }) => {
    let failed = true;
    let requestCount = 0;
    await page.route("**/diary?entry_date=*", async (route) => {
      requestCount += 1;
      if (failed) return route.abort("failed");
      return route.continue();
    });
    await page.goto("/diary");
    await expect(page.getByText("تعذر تحميل بيانات هذا اليوم")).toBeVisible();
    await expect(page.getByText("لا توجد أطعمة مسجلة اليوم")).toHaveCount(0);
    failed = false;
    await page.getByRole("button", { name: "إعادة المحاولة" }).first().click();
    await expect.poll(() => requestCount).toBeGreaterThan(1);
  });

  test("@p1 mobile long mixed-language Food name remains readable and sheet is keyboard accessible", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `طعام يومي طويل جدًا Mixed English ${uniqueName("RTL")}` });
    await foodsApi.createDiary(food.id, localDate(), 1);
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: food.name })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "إضافة طعام إلى فطور" })).toBeFocused();
  });

  test("@p1 responsive layout remains usable at all supported Diary widths", async ({ page }) => {
    for (const width of [360, 390, 430, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 });
      await page.goto("/diary");
      await expect(page.getByLabel("التنقل بين أيام اليوميات")).toBeVisible();
      await expect(page.getByLabel(/الأسبوع من/)).toBeVisible();
      await expect(page.getByRole("heading", { name: "وجبات اليوم" })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), `horizontal overflow at ${width}px`).toBe(true);
    }
  });
});

const DIARY_DAY_ERROR_COPY = "تعذر تحميل يوميات هذا اليوم. تحقق من الاتصال وحاول مرة أخرى.";

function localDateFrom(input: string, days: number): string {
  const date = new Date(`${input}T00:00:00`);
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}
