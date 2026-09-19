import { expect, fillRequiredFoodForm, submitFoodForm, test } from "./helpers";

test.describe("Add Food form stability @foods @stability", () => {
  test("opening and closing optional nutrients does not reset the form", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: "E2E Optional Toggle", brand: "Toggle Brand" });
    const details = page.locator("details.food-optional-section");
    await details.locator("summary").click();
    await page.getByLabel("ألياف g").fill("4.25");
    await details.locator("summary").click();
    await details.locator("summary").click();

    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue("E2E Optional Toggle");
    await expect(page.getByLabel("العلامة التجارية")).toHaveValue("Toggle Brand");
    await expect(page.getByLabel("ألياف g")).toHaveValue("4.25");
  });

  test("only Save is a submit control and explicit navigation remains links", async ({ page }) => {
    await page.goto("/foods/new");
    const form = page.locator("form.food-form-layout");
    const formButtons = form.getByRole("button");
    await expect(formButtons).toHaveCount(1);
    await expect(formButtons).toHaveAttribute("type", "submit");
    await expect(form.getByText("التحليل الغذائي المتقدم")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "رجوع" })).toHaveAttribute("href", "/foods");
    await expect(page.getByRole("link", { name: "إلغاء" })).toHaveAttribute("href", "/foods");
  });

  test("validation errors preserve previously entered values", async ({ page }) => {
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name: "E2E Validation Stability", brand: "Validation Brand", calories: 123 });
    await page.getByLabel(/السعرات/).fill("");
    await submitFoodForm(page);

    await expect(page).toHaveURL(/\/foods\/new$/);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue("E2E Validation Stability");
    await expect(page.getByLabel("العلامة التجارية")).toHaveValue("Validation Brand");
    await expect(page.getByLabel(/السعرات/)).toHaveValue("");
    await expect(page.getByLabel(/السعرات/)).toHaveAttribute("aria-invalid", "true");
  });

  test("@plan016 successful Save leaves once without an unsaved dialog", async ({ page, foodsApi }) => {
    const name = `E2E-Stability-Success-${Date.now()}`;
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);

    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toHaveCount(0);
    await expect(page.locator("form.food-form-layout")).toHaveCount(0);
    const id = page.url().split("/").pop()!;
    expect((await foodsApi.get(id)).name).toBe(name);
    await foodsApi.remove(id);
  });
});
