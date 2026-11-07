import { test, expect, API_URL } from "./helpers";

test.describe("Food UX remediation", () => {
  test("empty search never displays a reversed result range", async ({ page }) => {
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام أو العلامة التجارية").fill("ux-no-food-match-999999999999");
    await expect(page.locator(".foods-result-count-range")).toContainText("0-0 من 0");
  });

  test("return from details retains catalog search and sort", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "UX retained catalog context" });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await page.getByLabel("ترتيب الأطعمة").first().selectOption("recent");
    await page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first().click();
    await page.getByRole("link", { name: "رجوع إلى الأطعمة" }).click();
    await expect(page.getByLabel("بحث باسم الطعام أو العلامة التجارية")).toHaveValue(food.name);
    await expect(page.getByLabel("ترتيب الأطعمة").first()).toHaveValue("recent");
  });

  test("failed registry does not expose internal taxonomy or provenance keys", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "UX registry recovery", primary_category: "other", subcategory: "other", nutrition_data_source: "estimated" });
    await page.route(`${API_URL}/nutrition/registry`, route => route.fulfill({ status: 503, body: "{}", contentType: "application/json" }));
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByRole("heading", { name: food.name })).toBeVisible();
    await expect(page.getByText("estimated", { exact: true })).toHaveCount(0);
    await expect(page.getByText("other", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "إعادة المحاولة" }).first()).toBeVisible();
  });
});
