import { expect, expectNoHorizontalOverflow, test, uniqueName, validFood } from "./helpers";

test("Food API preserves exact nullable nutrients and simplified source metadata", async ({ foodsApi }) => {
  const food = await foodsApi.create({
    name: uniqueName("Quality-contract"),
    brand: "Quality Foods",
    primary_category: "dairy_products",
    subcategory: "yogurt",
    selenium_mcg: 0,
    iodine_mcg: null,
    folate_dfe_mcg: 425.125,
    vitamin_a_rae_mcg: 700,
    nutrition_data_source: "official",
    ingredients: "حليب، سكر"
  });

  expect(food.selenium_mcg).toBe(0);
  expect(food.iodine_mcg).toBeNull();
  expect(food.folate_dfe_mcg).toBe(425.125);
  expect(food.nutrition_data_source).toBe("official");
  expect(food.ingredients).toBe("حليب، سكر");
  expect(food.primary_category).toBe("dairy_products");
  expect(food.subcategory).toBe("yogurt");
});

test("new Food UI consumes the approved taxonomy and source registry", async ({ page }) => {
  await page.goto("/foods/new");
  await expect(page.getByLabel("فيتامين A mcg", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("فولات mcg", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel(/RAE/)).toHaveCount(1);
  await expect(page.getByLabel(/DFE/)).toHaveCount(1);
  await page.getByLabel(/اسم الطعام/).fill(uniqueName("Registry-form"));
  await page.getByLabel("التصنيف الرئيسي").selectOption("fruits");
  await page.getByLabel("التصنيف الفرعي").selectOption("berries");
  await page.getByLabel(/السعرات/).fill("80");
  await page.getByLabel(/البروتين g/).fill("1");
  await page.getByLabel(/الكارب g/).fill("18");
  await page.getByLabel(/الدهون g/).fill("0");
  await page.getByLabel("مصدر البيانات الغذائية").selectOption("official");
  const createResponse = page.waitForResponse(
    (response) => response.url().endsWith("/foods") && response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "حفظ الطعام" }).click();
  expect((await createResponse).status()).toBe(201);

  await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
  await expect(page.getByText("الفواكه", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("التوت", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("رسمي", { exact: true })).toBeVisible();
});

test("retired nutrition-source metadata is rejected", async ({ foodsApi }) => {
  const payload = validFood({ name: uniqueName("No-retired-source") }) as unknown as Record<string, unknown>;
  payload.nutrition_source = { type: "unknown", reliability: "high" };

  const response = await foodsApi.createRaw(payload);

  expect(response.status()).toBe(422);
});

test("two-level taxonomy controls remain usable at 320px in RTL", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/foods/new");
  await page.getByLabel("التصنيف الرئيسي").selectOption("grains_and_starches");
  await page.getByLabel("التصنيف الفرعي").selectOption("jareesh");
  await expect(page.getByLabel("التصنيف الفرعي")).toHaveValue("jareesh");
  await expectNoHorizontalOverflow(page);
});
