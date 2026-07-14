import { test, expect, fillRequiredFoodForm, submitFoodForm, validFood } from "./helpers";

test.describe("Duplicate Food handling @foods", () => {
  test("[FOOD-TC-101] @p0 blocks exact duplicate and shows Arabic error", async ({ page, foodsApi }) => {
    const original = await foodsApi.create({ name: `E2E-Duplicate-${Date.now()}`, unit_amount: 30, default_unit_type: "slice" });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, {
      name: original.name,
      nutrition_basis: original.nutrition_basis,
      default_unit_type: original.default_unit_type,
      unit_amount: original.unit_amount,
      unit_basis: original.unit_basis
    });
    await submitFoodForm(page);
    await expect(page.getByText("هذا الطعام موجود مسبقًا بنفس الوحدة.", { exact: true })).toBeVisible();
    await expect(page.getByLabel(/اسم الطعام/)).toHaveAttribute("aria-invalid", "true");
  });

  test("[FOOD-TC-102] @p0 normalizes spaces and English case for duplicate key", async ({ foodsApi }) => {
    const name = `E2E Case Food ${Date.now()}`;
    await foodsApi.create({ name, unit_amount: 25, default_unit_type: "piece" });
    const response = await foodsApi.createRaw(validFood({
      name: `  ${name.toUpperCase().replaceAll(" ", "   ")}  `,
      unit_amount: 25,
      default_unit_type: "piece"
    }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("هذا الطعام موجود مسبقًا بنفس الوحدة.");
  });

  test("[FOOD-TC-103] @p1 brand and category do not change duplicate identity", async ({ foodsApi }) => {
    const name = `E2E-Metadata-Duplicate-${Date.now()}`;
    await foodsApi.create({ name, brand: "Brand A", category: "Category A", unit_amount: 40 });
    const response = await foodsApi.createRaw(validFood({ name, brand: "Brand B", category: "Category B", unit_amount: 40 }));
    expect(response.status()).toBe(422);
  });

  test("[FOOD-TC-104] @p0 deleted Food can be created again", async ({ foodsApi }) => {
    const payload = validFood({ name: `E2E-Recreate-${Date.now()}`, unit_amount: 55 });
    const first = await foodsApi.create(payload);
    await foodsApi.remove(first.id);
    const recreated = await foodsApi.create(payload);
    expect(recreated.id).not.toBe(first.id);
  });

  test("[FOOD-TC-105] @p0 edit cannot collide with another Food", async ({ foodsApi }) => {
    const target = await foodsApi.create({ name: `E2E-Target-${Date.now()}`, unit_amount: 80 });
    const other = await foodsApi.create({ name: `E2E-Other-${Date.now()}`, unit_amount: 90 });
    const response = await foodsApi.update(other.id, {
      name: target.name,
      nutrition_basis: target.nutrition_basis,
      default_unit_type: target.default_unit_type,
      unit_amount: target.unit_amount,
      unit_basis: target.unit_basis
    });
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("هذا الطعام موجود مسبقًا بنفس الوحدة.");
  });
});
