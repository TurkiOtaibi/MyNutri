import { test, expect, expectNoHorizontalOverflow, type FoodRecord, validFood } from "./helpers";

test.describe("Foods serving-first catalog and details @foods", () => {
  test("[SERVING-001] @p0 @mobile card uses correctly rounded serving values", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: `E2E Serving Oats ${Date.now()}`,
      default_unit_type: "piece",
      unit_amount: 14,
      calories: 492.86,
      protein_g: 7.86,
      carb_g: 67.86,
      fat_g: 22.14
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");

    const card = page.locator(".food-card", { hasText: food.name });
    await expect(card).toBeVisible();
    await expect(card).toContainText("قطعة واحدة · 14 جم");
    await expect(card.locator(".serving-metric").nth(0)).toContainText("69");
    await expect(card.locator(".serving-metric").nth(1)).toContainText("1.1");
    await expect(card.locator(".serving-metric").nth(2)).toContainText("9.5");
    await expect(card.locator(".serving-metric").nth(3)).toContainText("3.1");
    await expect(card).not.toContainText("492.86");
  });

  test("[SERVING-002] @p0 details expose serving and exact per-basis modes", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: `E2E Complete Nutrition ${Date.now()}`,
      default_unit_type: "piece",
      unit_amount: 14,
      calories: 492.86,
      protein_g: 7.86,
      carb_g: 67.86,
      fat_g: 22.14,
      fiber_g: 8.93,
      sugar_g: null,
      added_sugar_g: 0,
      saturated_fat_g: 7.14,
      trans_fat_g: 0,
      sodium_mg: 214.29,
      vitamin_d_mcg: 0
    });
    await page.goto(`/foods/${food.id}`);

    await expect(page.locator(".serving-summary")).toContainText("69");
    await expect(page.locator(".serving-summary")).toContainText("1.1");
    await expect(page.getByRole("button", { name: "الحصة الافتراضية" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("إجمالي السكر", { exact: true })).toHaveCount(0);
    await expect(page.getByText("الدهون المتحولة", { exact: true })).toBeVisible();
    await expect(page.getByText("فيتامين D", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "لكل 100 جم" }).click();
    await expect(page.getByRole("button", { name: "لكل 100 جم" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".nutrition-group", { hasText: "القيم الأساسية" })).toContainText("492.86");
    await expect(page.locator(".nutrition-group", { hasText: "القيم الأساسية" })).toContainText("7.86");
  });

  test("[SERVING-003] @p0 search and category filter work together", async ({ page, foodsApi }) => {
    const stamp = Date.now();
    const match = await foodsApi.create({ name: `E2E Filter Oats ${stamp}`, category: `Breakfast ${stamp}` });
    const wrongCategory = await foodsApi.create({ name: `E2E Filter Oats Other ${stamp}`, category: `Snacks ${stamp}` });
    const wrongName = await foodsApi.create({ name: `E2E Filter Rice ${stamp}`, category: `Breakfast ${stamp}` });

    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill(`Oats ${stamp}`);
    await page.getByLabel("تصفية حسب التصنيف").selectOption(`Breakfast ${stamp}`);

    await expect(page.getByText(match.name, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(wrongCategory.name, { exact: true })).toHaveCount(0);
    await expect(page.getByText(wrongName.name, { exact: true })).toHaveCount(0);
  });

  test("[SERVING-004] @p0 serving-calorie sort uses derived serving amount", async ({ page, foodsApi }) => {
    const stamp = Date.now();
    const small = await foodsApi.create({ name: `E2E Sort ${stamp} Small`, calories: 500, unit_amount: 10 });
    const large = await foodsApi.create({ name: `E2E Sort ${stamp} Large`, calories: 100, unit_amount: 100 });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill(`E2E Sort ${stamp}`);
    await page.getByLabel("ترتيب الأطعمة").first().selectOption("calories");
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText(large.name);
    await expect(rows.nth(1)).toContainText(small.name);
  });

  test("[SERVING-005] @p0 desktop uses numbered pagination", async ({ page }) => {
    const foods = mockFoods(25);
    await mockPagedCatalog(page, foods);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/foods");

    await expect(page.locator("tbody tr")).toHaveCount(20);
    await page.getByRole("button", { name: "الصفحة 2" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(5);
    await expect(page.getByText(foods[20].name, { exact: true }).first()).toBeVisible();
  });

  test("[SERVING-006] @p0 @mobile Load More appends the next page", async ({ page }) => {
    const foods = mockFoods(25);
    await mockPagedCatalog(page, foods);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");

    await expect(page.locator(".food-card")).toHaveCount(20);
    await page.getByRole("button", { name: "عرض المزيد" }).click();
    await expect(page.locator(".food-card")).toHaveCount(25);
    await expect(page.getByText("عرض 25 من 25 طعامًا", { exact: true })).toBeVisible();
  });

  test("[SERVING-007] @p0 @mobile card opens details and menu exposes secondary actions", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E Card Menu ${Date.now()}` });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");

    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
    await expect(page.locator(".food-card", { hasText: food.name }).locator(".row-actions")).toHaveCount(0);
    await page.keyboard.press("Escape");
    await page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).click();
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
  });

  test("[SERVING-008] @p1 mixed RTL text and compact card remain within 390px", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: `بسكويت الشوفان بالشوكولاتة الداكنة بدون سكر - Gullón Oaty ${Date.now()}`.slice(0, 120),
      brand: "Gullón Oaty",
      category: "حلويات وبسكويت"
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");
    const card = page.locator(".food-card", { hasText: food.name });
    await expect(card).toBeVisible();
    expect(await card.locator(".food-card-title").getAttribute("dir")).toBe("auto");
    await expectNoHorizontalOverflow(page);
  });
});

function mockFoods(count: number): FoodRecord[] {
  return Array.from({ length: count }, (_, index) => ({
    ...validFood({
      name: `Mock Food ${String(index + 1).padStart(2, "0")}`,
      category: index % 2 === 0 ? "Breakfast" : null,
      unit_amount: 25,
      calories: 200 + index,
      protein_g: 10 + index / 10
    }),
    id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    net_carbs_g: 20,
    nutrition_source: {
      type: "unknown",
      name: null,
      reference: null,
      reliability: "unknown",
      reliability_rules_version: "1.0.0"
    },
    nova: {
      classification: "unknown",
      review_status: "unreviewed",
      rules_version: "1.0.0"
    },
    group_contributions: [],
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z"
  }));
}

async function mockPagedCatalog(page: import("@playwright/test").Page, foods: FoodRecord[]) {
  await page.route(/\/foods\?.*page=/, async (route) => {
    const url = new URL(route.request().url());
    const current = Number(url.searchParams.get("page") ?? "1");
    const size = Number(url.searchParams.get("page_size") ?? "20");
    const start = (current - 1) * size;
    const items = foods.slice(start, start + size);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items,
        total: foods.length,
        page: current,
        page_size: size,
        total_pages: Math.ceil(foods.length / size),
        categories: ["Breakfast"],
        uncategorized_count: foods.filter((food) => !food.category).length
      })
    });
  });
}
