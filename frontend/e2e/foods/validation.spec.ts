import { test, expect, field, fillRequiredFoodForm, submitFoodForm, validFood } from "./helpers";

const requiredUiCases = [
  { id: "FOOD-TC-048", label: /اسم الطعام/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/اسم الطعام/).fill("") },
  { id: "FOOD-TC-050", label: /السعرات/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/السعرات/).fill("") },
  { id: "FOOD-TC-051", label: /البروتين g/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/البروتين g/).fill("") },
  { id: "FOOD-TC-052", label: /الكارب g/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/الكارب g/).fill("") },
  { id: "FOOD-TC-053", label: /الدهون g/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/الدهون g/).fill("") },
  { id: "FOOD-TC-055", label: /مقدار الوحدة/, setup: async (page: import("@playwright/test").Page) => page.getByLabel(/مقدار الوحدة/).fill("") }
];

test.describe("Food field validation @foods @validation", () => {
  for (const item of requiredUiCases) {
    test(`[${item.id}] @p0 required field shows associated Arabic error`, async ({ page }) => {
      await page.goto("/foods/new");
      await fillRequiredFoodForm(page);
      await item.setup(page);
      await submitFoodForm(page);
      const input = field(page, item.label);
      await expect(input).toHaveAttribute("aria-invalid", "true");
      const describedBy = await input.getAttribute("aria-describedby");
      expect(describedBy).toBeTruthy();
      await expect(page.locator(`#${describedBy}`)).toHaveText("هذا الحقل مطلوب.");
    });
  }

  for (const item of [
    { id: "FOOD-TC-049", property: "nutrition_basis" },
    { id: "FOOD-TC-054", property: "default_unit_type" },
    { id: "FOOD-TC-056", property: "unit_basis" }
  ]) {
    test(`[${item.id}] @p0 API rejects missing ${item.property} with Arabic field error`, async ({ foodsApi }) => {
      const payload = validFood() as unknown as Record<string, unknown>;
      delete payload[item.property];
      const response = await foodsApi.createRaw(payload);
      expect(response.status()).toBe(422);
      const body = await response.json();
      expect(JSON.stringify(body)).toContain(item.property);
      expect(JSON.stringify(body)).not.toContain("Field required");
    });
  }

  test("[FOOD-TC-057] @p1 accepts an Arabic Food name", async ({ foodsApi }) => {
    const food = await foodsApi.create({ name: `شوفان تجريبي ${Date.now()}` });
    expect(food.name).toContain("شوفان تجريبي");
  });

  test("[FOOD-TC-058] @p0 trims and collapses Food name whitespace", async ({ foodsApi }) => {
    const food = await foodsApi.create({ name: `  E2E   Spaced   ${Date.now()}  ` });
    expect(food.name).not.toMatch(/^\s|\s$/);
    expect(food.name).not.toContain("  ");
  });

  test("[FOOD-TC-059] @p1 enforces Food name max 120", async ({ foodsApi }) => {
    const accepted = await foodsApi.create({ name: `E2E-${"a".repeat(116)}` });
    expect(accepted.name.length).toBe(120);
    const response = await foodsApi.createRaw(validFood({ name: `E2E-${"b".repeat(117)}` }));
    expect(response.status()).toBe(422);
    expect(await response.text()).toContain("القيمة أعلى من الحد المسموح.");
  });

  test("[FOOD-TC-060] @p0 script-like text never executes", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-XSS-${Date.now()}`, notes: '<script>window.__foodsXss="executed"</script>' });
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByText('<script>window.__foodsXss="executed"</script>', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => (window as typeof window & { __foodsXss?: string }).__foodsXss)).toBeUndefined();
  });

  const coreRanges = [
    { boundaryId: "FOOD-TC-061", invalidId: "FOOD-TC-062", field: "calories", max: 3000 },
    { boundaryId: "FOOD-TC-063", invalidId: "FOOD-TC-064", field: "protein_g", max: 300 },
    { boundaryId: "FOOD-TC-065", invalidId: "FOOD-TC-066", field: "carb_g", max: 500 },
    { boundaryId: "FOOD-TC-067", invalidId: "FOOD-TC-068", field: "fat_g", max: 300 }
  ] as const;

  for (const item of coreRanges) {
    test(`[${item.boundaryId}] @p0 accepts ${item.field} zero and max boundaries`, async ({ foodsApi }) => {
      const zero = await foodsApi.create({ name: `${item.boundaryId}-zero-${Date.now()}`, [item.field]: 0 });
      expect(zero[item.field]).toBe(0);
      const max = await foodsApi.create({ name: `${item.boundaryId}-max-${Date.now()}`, [item.field]: item.max });
      expect(max[item.field]).toBe(item.max);
    });

    test(`[${item.invalidId}] @p0 rejects ${item.field} negative, malformed, and above max`, async ({ foodsApi }) => {
      for (const value of [-1, "abc", item.max + 1]) {
        const response = await foodsApi.createRaw(validFood({ name: `${item.invalidId}-${value}-${Date.now()}`, [item.field]: value } as never));
        expect(response.status()).toBe(422);
        const text = await response.text();
        expect(text).toContain(item.field);
        expect(text).not.toContain("Input should be");
      }
    });
  }

  for (const item of [
    { id: "FOOD-TC-069", field: "nutrition_basis", value: "per_serving" },
    { id: "FOOD-TC-070", field: "default_unit_type", value: "bottle" },
    { id: "FOOD-TC-072", field: "unit_basis", value: "oz" },
    { id: "FOOD-TC-151", field: "nutrition_basis", value: "per_serving" }
  ]) {
    test(`[${item.id}] @p0 rejects tampered ${item.field}`, async ({ foodsApi }) => {
      const response = await foodsApi.createRaw(validFood({ [item.field]: item.value } as never));
      expect(response.status()).toBe(422);
      const text = await response.text();
      expect(text).toContain(item.field);
      expect(text).toContain("اختر قيمة صحيحة.");
    });
  }

  test("[FOOD-TC-071] @p0 validates unit amount boundaries and decimal", async ({ foodsApi }) => {
    for (const value of [1, 0.01, 2000, 32.5]) {
      const food = await foodsApi.create({ name: `E2E-Unit-${value}-${Date.now()}`, unit_amount: value });
      expect(food.unit_amount).toBe(value);
    }
    for (const value of [0, -1, 2001]) {
      const response = await foodsApi.createRaw(validFood({ name: `E2E-Bad-Unit-${value}-${Date.now()}`, unit_amount: value }));
      expect(response.status()).toBe(422);
    }
  });

  const optionalTextCases = [
    { id: "FOOD-TC-073", field: "brand", max: 80, values: [null, "نادك", "Acme Foods", "نادك Acme 100%", "Brand & Co."] },
    { id: "FOOD-TC-074", field: "category", max: 80, values: [null, "ألبان", "Dairy", "ألبان Dairy 2026", "Snacks & Drinks"] },
    { id: "FOOD-TC-149", field: "notes", max: 500, values: ["ملاحظات غذائية", "English notes", "ملاحظات USDA الغذائية"] },
    { id: "FOOD-TC-150", field: "data_source", max: 120, values: ["وزارة الصحة", "USDA", "USDA وزارة الصحة", "https://example.test/source"] }
  ] as const;

  for (const item of optionalTextCases) {
    test(`[${item.id}] @p2 validates ${item.field} language and max length`, async ({ foodsApi }) => {
      for (const value of item.values) {
        const food = await foodsApi.create({ name: `${item.id}-${Date.now()}-${Math.random()}`, [item.field]: value } as never);
        expect(food[item.field]).toBe(value);
      }
      const exact = await foodsApi.create({ name: `${item.id}-exact-${Date.now()}`, [item.field]: "a".repeat(item.max) } as never);
      expect((exact[item.field] as string).length).toBe(item.max);
      const response = await foodsApi.createRaw(validFood({ name: `${item.id}-over-${Date.now()}`, [item.field]: "b".repeat(item.max + 1) } as never));
      expect(response.status()).toBe(422);
      expect(await response.text()).toContain("القيمة أعلى من الحد المسموح.");
    });
  }

  test("[FOOD-TC-075] @p2 blank optional text is allowed and HTML stays inert", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ brand: null, category: null, notes: "<b>plain text</b>", data_source: null });
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByText("<b>plain text</b>", { exact: true })).toBeVisible();
    await expect(page.locator(".food-detail-grid b", { hasText: "plain text" })).toHaveCount(0);
  });

  test("[FOOD-TC-142] @p1 sugar_g is total sugar and legacy field is not user-facing", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ sugar_g: 12, added_sugar_g: 3 });
    expect(food.sugar_g).toBe(12);
    expect(food.added_sugar_g).toBe(3);
    expect(food).not.toHaveProperty("total_sugars_g");
    await page.goto("/foods/new");
    await page.getByText("القيم الغذائية الإضافية", { exact: true }).click();
    await expect(page.getByLabel("إجمالي السكر g")).toBeVisible();
    await expect(page.getByLabel("سكر مضاف g")).toBeVisible();
    await expect(page.getByText("total_sugars_g")).toHaveCount(0);
  });

  test("[FOOD-TC-143] @p1 accepts decimal calories", async ({ foodsApi }) => {
    const food = await foodsApi.create({ calories: 123.45 });
    expect(food.calories).toBe(123.45);
  });

  test("[FOOD-TC-147] @p2 brand accepts Arabic, English, mixed text, and punctuation", async ({ foodsApi }) => {
    for (const brand of ["Acme Foods", "نادك", "نادك Acme 100%", "Brand & Co."]) {
      const food = await foodsApi.create({ brand });
      expect(food.brand).toBe(brand);
    }
  });

  test("[FOOD-TC-148] @p2 category accepts Arabic, English, mixed text, and punctuation", async ({ foodsApi }) => {
    for (const category of ["Dairy", "ألبان", "ألبان Dairy 2026", "Snacks & Drinks"]) {
      const food = await foodsApi.create({ category });
      expect(food.category).toBe(category);
    }
  });

  test("[FOOD-TC-153] @p0 whitespace-only Food name is rejected with Arabic error", async ({ page, foodsApi }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page);
    await page.getByLabel(/اسم الطعام/).fill("     ");
    await submitFoodForm(page);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveAttribute("aria-invalid", "true");
    await expect(page.getByText("هذا الحقل مطلوب.", { exact: true })).toBeVisible();
    expect((await foodsApi.list()).some((food) => food.name.trim() === "")).toBeFalsy();
  });
});
