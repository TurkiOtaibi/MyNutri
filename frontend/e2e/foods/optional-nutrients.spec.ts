import { test, expect, fillRequiredFoodForm, submitFoodForm, validFood } from "./helpers";

const nutrientCases = [
  { id: "FOOD-TC-076", field: "fiber_g", max: 100, supporting: { carb_g: 100 } },
  { id: "FOOD-TC-077", field: "sugar_g", max: 100, supporting: {} },
  { id: "FOOD-TC-078", field: "added_sugar_g", max: 100, supporting: {} },
  { id: "FOOD-TC-079", field: "saturated_fat_g", max: 100, supporting: { fat_g: 100 } },
  { id: "FOOD-TC-080", field: "trans_fat_g", max: 100, supporting: { fat_g: 100 } },
  { id: "FOOD-TC-081", field: "cholesterol_mg", max: 2000, supporting: {} },
  { id: "FOOD-TC-082", field: "sodium_mg", max: 50000, supporting: {} },
  { id: "FOOD-TC-083", field: "potassium_mg", max: 10000, supporting: {} },
  { id: "FOOD-TC-084", field: "calcium_mg", max: 5000, supporting: {} },
  { id: "FOOD-TC-085", field: "iron_mg", max: 100, supporting: {} },
  { id: "FOOD-TC-086", field: "magnesium_mg", max: 1000, supporting: {} },
  { id: "FOOD-TC-087", field: "zinc_mg", max: 100, supporting: {} },
  { id: "FOOD-TC-088", field: "vitamin_d_mcg", max: 250, supporting: {} },
  { id: "FOOD-TC-089", field: "vitamin_b12_mcg", max: 1000, supporting: {} },
  { id: "FOOD-TC-090", field: "vitamin_c_mg", max: 5000, supporting: {} },
  { id: "FOOD-TC-091", field: "vitamin_a_mcg", max: 3000, supporting: {} },
  { id: "FOOD-TC-092", field: "folate_mcg", max: 2000, supporting: {} },
  { id: "FOOD-TC-093", field: "vitamin_k_mcg", max: 2000, supporting: {} }
] as const;

test.describe("Optional nutrient validation @foods @validation", () => {
  for (const item of nutrientCases) {
    test(`[${item.id}] @p1 validates optional ${item.field} blank, zero, max, negative, and above max`, async ({ foodsApi }) => {
      const blank = await foodsApi.create({ name: `${item.id}-blank-${Date.now()}`, ...item.supporting, [item.field]: null } as never);
      expect(blank[item.field]).toBeNull();
      const zero = await foodsApi.create({ name: `${item.id}-zero-${Date.now()}`, ...item.supporting, [item.field]: 0 } as never);
      expect(zero[item.field]).toBe(0);
      const max = await foodsApi.create({ name: `${item.id}-max-${Date.now()}`, ...item.supporting, [item.field]: item.max } as never);
      expect(max[item.field]).toBe(item.max);

      const negative = await foodsApi.createRaw(validFood({ name: `${item.id}-negative-${Date.now()}`, ...item.supporting, [item.field]: -0.01 } as never));
      expect(negative.status()).toBe(422);
      expect(await negative.text()).toContain("القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.");

      const above = await foodsApi.createRaw(validFood({ name: `${item.id}-above-${Date.now()}`, ...item.supporting, [item.field]: item.max + 0.01 } as never));
      expect(above.status()).toBe(422);
      expect(await above.text()).toContain("القيمة الغذائية الإضافية أعلى من الحد المسموح.");
    });
  }

  test("[FOOD-TC-094] @p0 rejects fiber greater than carbs", async ({ foodsApi }) => {
    const response = await foodsApi.createRaw(validFood({ carb_g: 10, fiber_g: 11 }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.");
  });

  test("[FOOD-TC-095] @p0 rejects added sugar greater than total sugar", async ({ foodsApi }) => {
    const response = await foodsApi.createRaw(validFood({ sugar_g: 5, added_sugar_g: 6 }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.");
  });

  test("[FOOD-TC-096] @p1 permits added sugar when total sugar is blank", async ({ foodsApi }) => {
    const food = await foodsApi.create({ sugar_g: null, added_sugar_g: 4 });
    expect(food.sugar_g).toBeNull();
    expect(food.added_sugar_g).toBe(4);
  });

  test("[FOOD-TC-097] @p0 rejects saturated fat greater than fat", async ({ foodsApi }) => {
    const response = await foodsApi.createRaw(validFood({ fat_g: 2, saturated_fat_g: 3 }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.");
  });

  test("[FOOD-TC-098] @p0 rejects trans fat greater than fat", async ({ foodsApi }) => {
    const response = await foodsApi.createRaw(validFood({ fat_g: 2, trans_fat_g: 3 }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.");
  });

  test("[FOOD-TC-099] @p0 rejects saturated plus trans fat greater than total fat", async ({ foodsApi }) => {
    const response = await foodsApi.createRaw(validFood({ fat_g: 5, saturated_fat_g: 3, trans_fat_g: 3 }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.");
  });

  test("[FOOD-TC-100] @p1 invalid optional nutrient opens section and associates error", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page);
    await page.getByText("القيم الغذائية الإضافية", { exact: true }).click();
    await page.getByLabel("صوديوم mg").fill("50001");
    await page.getByText("القيم الغذائية الإضافية", { exact: true }).click();
    await submitFoodForm(page);
    const details = page.locator("details.food-optional-section");
    await expect(details).toHaveAttribute("open", "");
    const input = page.getByLabel("صوديوم mg");
    await expect(input).toHaveAttribute("aria-invalid", "true");
    const errorId = await input.getAttribute("aria-describedby");
    await expect(page.locator(`#${errorId}`)).toHaveText("القيمة أعلى من الحد المسموح.");
  });

  test("[FOOD-TC-144] @p1 accepts decimal gram nutrients", async ({ foodsApi }) => {
    const food = await foodsApi.create({
      carb_g: 30,
      fat_g: 10,
      fiber_g: 2.5,
      sugar_g: 5.5,
      added_sugar_g: 1.25,
      saturated_fat_g: 0.5,
      trans_fat_g: 0.1
    });
    expect(food.fiber_g).toBe(2.5);
    expect(food.added_sugar_g).toBe(1.25);
  });

  test("[FOOD-TC-145] @p1 accepts decimal minerals", async ({ foodsApi }) => {
    const food = await foodsApi.create({
      sodium_mg: 123.45,
      cholesterol_mg: 12.5,
      potassium_mg: 350.75,
      calcium_mg: 120.5,
      iron_mg: 3.25,
      magnesium_mg: 45.5,
      zinc_mg: 1.5
    });
    expect(food.sodium_mg).toBe(123.45);
    expect(food.potassium_mg).toBe(350.75);
  });

  test("[FOOD-TC-146] @p1 accepts decimal vitamins", async ({ foodsApi }) => {
    const food = await foodsApi.create({
      vitamin_d_mcg: 12.5,
      vitamin_b12_mcg: 2.4,
      vitamin_c_mg: 55.5,
      vitamin_a_mcg: 300.25,
      folate_mcg: 120.5,
      vitamin_k_mcg: 20.75
    });
    expect(food.vitamin_d_mcg).toBe(12.5);
    expect(food.vitamin_b12_mcg).toBe(2.4);
  });

  test("[FOOD-TC-152] @p1 structured optional nutrient errors identify the field", async ({ foodsApi }) => {
    const negative = await foodsApi.createRaw(validFood({ fiber_g: -0.1 }));
    const negativeBody = await negative.json();
    expect(negative.status()).toBe(422);
    expect(JSON.stringify(negativeBody)).toContain("fiber_g");
    expect(JSON.stringify(negativeBody)).toContain("القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.");

    const above = await foodsApi.createRaw(validFood({ vitamin_d_mcg: 250.01 }));
    const aboveBody = await above.json();
    expect(above.status()).toBe(422);
    expect(JSON.stringify(aboveBody)).toContain("vitamin_d_mcg");
    expect(JSON.stringify(aboveBody)).toContain("القيمة الغذائية الإضافية أعلى من الحد المسموح.");
  });
});
