import { expect, expectNoHorizontalOverflow, test, uniqueName, validFood } from "./helpers";

test("Wave 1 Food API preserves exact values and derives source reliability", async ({ foodsApi }) => {
  const food = await foodsApi.create({
    name: uniqueName("Quality-contract"),
    primary_category_key: "dairy_fortified_alternatives",
    food_kind: "composite",
    group_data_status: "estimated",
    group_data_completeness: "partial",
    selenium_mcg: 0,
    iodine_mcg: null,
    folate_dfe_mcg: 425.125,
    vitamin_a_rae_mcg: 700,
    nutrition_source: {
      type: "multiple_sources",
      name: "بطاقة وقاعدة بيانات",
      reference: null
    },
    ingredients: {
      text: "حليب، سكر",
      source_type: "official_product_label",
      source_name: "البطاقة",
      source_reference: null
    },
    nova: { classification: "unknown" },
    group_contributions: [
      {
        group_key: "dairy_fortified_alternatives",
        subtype_key: "yogurt",
        amount_per_100_basis: 80,
        data_status: "estimated"
      }
    ],
    analytical_traits: ["sweetened"]
  });

  expect(food.selenium_mcg).toBe(0);
  expect(food.iodine_mcg).toBeNull();
  expect(food.folate_dfe_mcg).toBe(425.125);
  expect(food.nutrition_source).toMatchObject({ type: "multiple_sources", reliability: "mixed" });
  expect(food.nova).toMatchObject({ classification: "unknown", review_status: "reviewed" });
  expect(food.group_contributions).toHaveLength(1);
  expect(food.analytical_traits).toEqual(["sweetened"]);
});

test("new Food UI consumes Registry controls and saves controlled fields", async ({ page }) => {
  await page.goto("/foods/new");
  await expect(page.getByLabel("فيتامين A mcg", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("فولات mcg", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel(/RAE/)).toHaveCount(1);
  await expect(page.getByLabel(/DFE/)).toHaveCount(1);
  await page.getByLabel(/اسم الطعام/).fill(uniqueName("Registry-form"));
  await page.getByLabel(/التصنيف الأساسي/).selectOption("fruits");
  await page.getByLabel(/نوع الطعام/).selectOption("simple");
  await page.getByLabel(/السعرات/).fill("80");
  await page.getByLabel(/البروتين g/).fill("1");
  await page.getByLabel(/الكارب g/).fill("18");
  await page.getByLabel(/الدهون g/).fill("0");
  await page.getByLabel(/نوع المصدر/).selectOption("official_food_database");
  await page.getByLabel(/اسم المصدر/).fill("قاعدة رسمية");
  await expect(page.getByText("مرتفعة", { exact: true })).toBeVisible();
  const createResponse = page.waitForResponse(
    (response) => response.url().endsWith("/foods") && response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "حفظ الطعام" }).click();
  expect((await createResponse).status()).toBe(201);

  await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
  await expect(page.getByText("الفواكه", { exact: true })).toBeVisible();
  await expect(page.getByText("مرتفعة", { exact: true })).toBeVisible();
});

test("unknown source is explicit and cannot accept client reliability", async ({ foodsApi }) => {
  const payload = validFood({ name: uniqueName("No-client-reliability") }) as unknown as Record<string, unknown>;
  payload.nutrition_source = {
    type: "unknown",
    name: null,
    reference: null,
    reliability: "high"
  };

  const response = await foodsApi.createRaw(payload);

  expect(response.status()).toBe(422);
});

test("group and trait controls remain usable at 320px in RTL", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/foods/new");
  await page.getByRole("button", { name: "إضافة مساهمة" }).click();

  await expect(page.getByLabel("المجموعة 1")).toBeVisible();
  await expect(page.getByLabel("محلى", { exact: true })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
