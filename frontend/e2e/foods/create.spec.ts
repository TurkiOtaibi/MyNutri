import { test, expect, fillRequiredFoodForm, submitFoodForm, expectNoHorizontalOverflow } from "./helpers";

test.describe("Food creation @foods", () => {
  for (const testCase of [
    { id: "FOOD-TC-036", basis: "per_100g" as const, unit: "g" as const, amount: 100, priority: "@p0" },
    { id: "FOOD-TC-037", basis: "per_100ml" as const, unit: "ml" as const, amount: 250, priority: "@p0" }
  ]) {
    test(`[${testCase.id}] ${testCase.priority} creates a valid ${testCase.basis} Food`, async ({ page, foodsApi }) => {
      await page.goto("/foods/new");
      const payload = await fillRequiredFoodForm(page, {
        name: `E2E-${testCase.id}-${Date.now()}`,
        nutrition_basis: testCase.basis,
        unit_basis: testCase.unit,
        default_unit_type: testCase.unit,
        unit_amount: testCase.amount,
        calories: 123.45,
        protein_g: 4.5,
        carb_g: 20.25,
        fat_g: 3.75
      });
      await submitFoodForm(page);
      await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
      const id = page.url().split("/").pop()!;
      const saved = await foodsApi.get(id);
      expect(saved.nutrition_basis).toBe(testCase.basis);
      expect(saved.unit_basis).toBe(testCase.unit);
      expect(saved.name).toBe(payload.name);
      await foodsApi.remove(id);
    });
  }

  test("[FOOD-TC-038] @p1 form has the approved grouped sections", async ({ page }) => {
    await page.goto("/foods/new");
    for (const title of ["معلومات الطعام الأساسية", "أساس القيم الغذائية", "القيم الغذائية الأساسية", "الوحدة الافتراضية", "ملاحظات ومصدر البيانات"]) {
      await expect(page.getByRole("heading", { name: title })).toBeVisible();
    }
    await expect(page.getByText("القيم الغذائية الإضافية", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-039] @p1 optional nutrients are collapsed by default", async ({ page }) => {
    await page.goto("/foods/new");
    const details = page.locator("details.food-optional-section");
    await expect(details).not.toHaveAttribute("open", "");
    await details.locator("summary").click();
    await expect(page.getByLabel("ألياف g")).toBeVisible();
  });

  test("[FOOD-TC-040] @p0 blank optional nutrients do not block save", async ({ page, foodsApi }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: `E2E-Blank-Optional-${Date.now()}` });
    await submitFoodForm(page);
    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    await foodsApi.remove(page.url().split("/").pop()!);
  });

  test("[FOOD-TC-041] @p0 duplicate click submits one create request", async ({ page, foodsApi }) => {
    let posts = 0;
    page.on("request", (request) => {
      if (request.method() === "POST" && new URL(request.url()).pathname === "/foods") posts += 1;
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: `E2E-One-Submit-${Date.now()}` });
    const save = page.getByRole("button", { name: "حفظ الطعام" });
    await save.dblclick();
    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    expect(posts).toBe(1);
    await foodsApi.remove(page.url().split("/").pop()!);
  });

  test("[FOOD-TC-042] @p0 network failure preserves the draft and creates no Food", async ({ page, foodsApi }) => {
    const name = `E2E-Network-Fail-${Date.now()}`;
    await page.route("**/foods", (route) => route.abort("failed"));
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);
    await expect(page.getByRole("status")).toContainText("تعذر الاتصال بالخادم");
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(name);
    expect((await foodsApi.list()).some((food) => food.name === name)).toBeFalsy();
  });

  test("[FOOD-TC-043] @p0 structured API field error maps to the Food name", async ({ page }) => {
    await page.route("**/foods", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: [{ field: "name", code: "required", msg: "هذا الحقل مطلوب.", loc: ["body", "name"], type: "value_error" }] })
      });
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: `E2E-API-Field-${Date.now()}` });
    await submitFoodForm(page);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveAttribute("aria-invalid", "true");
    await expect(page.getByText("هذا الحقل مطلوب.", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-044] @p1 server failure preserves entered data", async ({ page }) => {
    const name = `E2E-Server-Fail-${Date.now()}`;
    await page.route("**/foods", async (route) => {
      if (route.request().method() === "POST") return route.fulfill({ status: 500, body: "server failure" });
      return route.continue();
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);
    await expect(page.getByRole("status")).toContainText("تعذر الاتصال بالخادم");
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(name);
  });

  test("[FOOD-TC-045] @p0 unauthorized create is not treated as saved", async ({ page, foodsApi }) => {
    const name = `E2E-Unauthorized-${Date.now()}`;
    await page.route("**/foods", async (route) => {
      if (route.request().method() === "POST") return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Unauthorized" }) });
      return route.continue();
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(name);
    expect((await foodsApi.list()).some((food) => food.name === name)).toBeFalsy();
  });

  test("[FOOD-TC-046] @p1 @mobile Add Food is usable at 390px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods/new");
    await expect(page.getByRole("button", { name: "حفظ الطعام" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-047] @p0 source of truth is per-100 and no legacy serving fields appear", async ({ page }) => {
    await page.goto("/foods/new");
    await expect(page.getByLabel(/أساس القيم/)).toBeVisible();
    await expect(page.getByLabel(/الوحدة الافتراضية/)).toBeVisible();
    await expect(page.getByLabel(/مقدار الوحدة/)).toBeVisible();
    await expect(page.getByText(/serving_grams|serving_label|القيم لكل حصة/)).toHaveCount(0);
  });
});
