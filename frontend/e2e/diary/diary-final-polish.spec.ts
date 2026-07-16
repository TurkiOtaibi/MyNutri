import { API_TOKEN, API_URL, expect, test, uniqueName } from "../foods/helpers";

function localDate(days = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

async function selectDate(page: import("@playwright/test").Page, value: string) {
  const picker = page.getByLabel("اختيار تاريخ اليوميات");
  await page.waitForFunction(() => {
    const input = document.querySelector('input[aria-label="اختيار تاريخ اليوميات"]');
    return input != null && Object.keys(input).some((key) => key.startsWith("__reactProps$"));
  });
  await picker.fill(value);
  await expect(picker).toHaveValue(value);
  await expect(page.locator(".diary-entry-skeleton")).toHaveCount(0);
}

test.describe("@diary @final-polish compact visual refinements", () => {
  test("@p0 date controls stay symmetric and the title stays centered with and without Today", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    const topline = page.locator(".compact-week-topline");
    const previous = page.getByRole("button", { name: "اليوم السابق" });
    const next = page.getByRole("button", { name: "اليوم التالي" });
    const title = page.locator(".compact-selected-date");

    const assertGeometry = async () => {
      const [lineBox, previousBox, nextBox, titleBox] = await Promise.all([
        topline.boundingBox(), previous.boundingBox(), next.boundingBox(), title.boundingBox()
      ]);
      expect(previousBox?.width).toBeCloseTo(nextBox?.width ?? 0, 0);
      expect(previousBox?.height).toBeCloseTo(nextBox?.height ?? 0, 0);
      expect(previousBox?.width).toBeGreaterThanOrEqual(44);
      expect(Math.abs((titleBox!.x + titleBox!.width / 2) - (lineBox!.x + lineBox!.width / 2))).toBeLessThanOrEqual(1.5);
    };

    await expect(page.getByRole("button", { name: "اليوم", exact: true })).toHaveCount(0);
    await assertGeometry();
    await selectDate(page, localDate(-10));
    await expect(page.getByRole("button", { name: "اليوم", exact: true })).toBeVisible();
    await assertGeometry();
  });

  test("@p0 compact meal controls and Food rows retain accessible targets", async ({ page, foodsApi }) => {
    const date = localDate(-301);
    const food = await foodsApi.create({ name: uniqueName("Compact row"), calories: 78, default_unit_type: "piece", unit_amount: 50 });
    await foodsApi.createDiary(food.id, date, 1, "breakfast");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/diary");
    await selectDate(page, date);

    const header = page.locator("#meal-section-breakfast .meal-section-header");
    const add = page.getByRole("button", { name: "إضافة طعام إلى فطور" });
    const toggle = page.locator("#meal-section-breakfast .meal-toggle");
    const row = page.locator("#meal-breakfast .diary-entry-row");
    const [headerBox, addBox, rowBox] = await Promise.all([header.boundingBox(), add.boundingBox(), row.boundingBox()]);
    expect(headerBox!.height).toBeLessThanOrEqual(78);
    expect(addBox!.width).toBeGreaterThanOrEqual(44);
    expect(addBox!.height).toBeGreaterThanOrEqual(44);
    expect(rowBox!.height).toBeGreaterThanOrEqual(64);
    expect(rowBox!.height).toBeLessThanOrEqual(72.5);
    await expect(toggle).toContainText("طعام واحد");

    const expanded = await toggle.getAttribute("aria-expanded");
    await add.click();
    await expect(page.getByRole("dialog", { name: "إضافة طعام" })).toBeVisible();
    await page.getByRole("dialog", { name: "إضافة طعام" }).getByRole("button", { name: "إلغاء" }).click();
    await expect(toggle).toHaveAttribute("aria-expanded", expanded!);
  });

  test("@p0 macro copy is RTL-safe and progress widths represent 1%, 9%, and 22%", async ({ page, request, foodsApi }) => {
    const date = localDate(-302);
    const profile = await request.get(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
    const targets = (await profile.json()).targets as { protein_g: number; carb_g: number; fat_g: number };
    const food = await foodsApi.create({
      name: uniqueName("Macro polish"),
      calories: 100,
      protein_g: targets.protein_g * 0.01,
      carb_g: targets.carb_g * 0.09,
      fat_g: targets.fat_g * 0.22
    });
    await foodsApi.createDiary(food.id, date, 1, "breakfast");
    await page.goto("/diary");
    await selectDate(page, date);

    const rows = page.locator(".macro-progress-row");
    await expect(rows).toHaveCount(3);
    for (const row of await rows.all()) {
      await expect(row.locator(".macro-value-expression")).toContainText("من");
      await expect(row.locator(".macro-value-expression")).not.toContainText("/");
    }
    await page.waitForTimeout(250);
    const bars = rows.locator(".macro-progress-track > span");
    const widths = await bars.evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().width));
    expect(widths[0]).toBeGreaterThanOrEqual(3);
    expect(widths[1]).toBeGreaterThan(widths[0]);
    expect(widths[2]).toBeGreaterThan(widths[1]);
    await expect(rows.nth(0).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
    await expect(rows.nth(1).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "9");
    await expect(rows.nth(2).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "22");
  });

  test("@p1 macro progress handles 0%, 100%, and over-target truthfully", async ({ page, request, foodsApi }) => {
    const zeroDate = localDate(-303);
    await page.goto("/diary");
    await selectDate(page, zeroDate);
    const zeroBars = page.locator(".macro-progress-track > span");
    for (const bar of await zeroBars.all()) expect((await bar.boundingBox())!.width).toBe(0);

    const profile = await request.get(`${API_URL}/profile`, { headers: { Authorization: `Bearer ${API_TOKEN}` } });
    const targets = (await profile.json()).targets as { protein_g: number; carb_g: number; fat_g: number };
    const date = localDate(-304);
    const food = await foodsApi.create({
      name: uniqueName("Macro bounds"), calories: 100,
      protein_g: targets.protein_g,
      carb_g: Math.min(500, targets.carb_g * 1.1),
      fat_g: targets.fat_g
    });
    await foodsApi.createDiary(food.id, date, 1, "breakfast");
    await selectDate(page, date);
    const rows = page.locator(".macro-progress-row");
    await expect(rows.nth(0).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
    await expect(rows.nth(1)).toHaveClass(/over/);
    const overTrack = rows.nth(1).locator(".macro-progress-track");
    const [trackBox, fillBox] = await Promise.all([overTrack.boundingBox(), overTrack.locator("> span").boundingBox()]);
    expect(fillBox!.width).toBeLessThanOrEqual(trackBox!.width + 0.5);
    await expect(overTrack).toHaveAttribute("aria-valuetext", /فوق الهدف/);
  });

  test("@p1 meal item count uses natural Arabic forms", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: uniqueName("Arabic count"), calories: 10 });
    const cases = [[1, "طعام واحد"], [2, "طعامان"], [3, "3 أطعمة"], [11, "11 طعامًا"]] as const;
    for (let index = 0; index < cases.length; index += 1) {
      const [count, label] = cases[index];
      const date = localDate(-310 - index);
      for (let item = 0; item < count; item += 1) await foodsApi.createDiary(food.id, date, 1, "breakfast");
      await page.goto("/diary");
      await selectDate(page, date);
      await expect(page.locator("#meal-section-breakfast .meal-toggle")).toContainText(label);
    }
    await selectDate(page, localDate(-320));
    await expect(page.locator("#meal-section-breakfast .meal-toggle")).toContainText("لا توجد أطعمة");
  });

  test("@p1 mobile widths remain overflow-free with compact selected day and primary meal title", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/diary");
      const selectedNumber = page.locator(".compact-week-day.selected strong");
      const box = await selectedNumber.boundingBox();
      expect(box!.width).toBeGreaterThanOrEqual(36);
      expect(box!.width).toBeLessThanOrEqual(40);
      const mealName = page.locator(".meal-title-copy strong").first();
      const mealMeta = page.locator(".meal-title-copy small").first();
      await expect(mealName).toBeVisible();
      expect(await mealName.evaluate((element) => getComputedStyle(element).color)).not.toBe(await mealMeta.evaluate((element) => getComputedStyle(element).color));
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    }
  });
});
