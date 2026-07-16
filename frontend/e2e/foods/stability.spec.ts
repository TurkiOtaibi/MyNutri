import { expect, fillRequiredFoodForm, submitFoodForm, test } from "./helpers";

test.describe("Add Food form stability @foods @stability", () => {
  test("keeps the populated form mounted for 60 seconds without navigation or reload", async ({ page }) => {
    test.setTimeout(90_000);
    let documentRequests = 0;
    let mainFrameNavigations = 0;
    const hmrErrors: string[] = [];

    page.on("request", (request) => {
      if (request.resourceType() === "document") documentRequests += 1;
    });
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) mainFrameNavigations += 1;
    });
    page.on("console", (message) => {
      if (message.type() === "error" && message.text().includes("webpack-hmr")) hmrErrors.push(message.text());
    });

    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, {
      name: "E2E Stable Draft",
      brand: "Stable Brand",
      category: "Stable Category",
      calories: 321,
      protein_g: 12,
      carb_g: 34,
      fat_g: 5
    });
    await page.locator("details.food-optional-section summary").click();
    await page.getByLabel("ألياف g").fill("3.5");

    const form = page.locator("form.food-form-layout");
    await form.evaluate((element) => {
      (element as HTMLFormElement & { __qaInstance?: string }).__qaInstance = "stable-add-food-form";
    });
    const documentId = await page.evaluate(() => {
      const currentWindow = window as typeof window & { __qaDocumentId?: string };
      currentWindow.__qaDocumentId ??= `${Date.now()}-${Math.random()}`;
      return currentWindow.__qaDocumentId;
    });
    const documentRequestBaseline = documentRequests;
    const navigationBaseline = mainFrameNavigations;

    await page.waitForTimeout(60_000);
    await page.getByLabel("العلامة التجارية").fill("Stable Brand Continued");

    await expect(page).toHaveURL(/\/foods\/new$/);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue("E2E Stable Draft");
    await expect(page.getByLabel("العلامة التجارية")).toHaveValue("Stable Brand Continued");
    await expect(page.getByLabel("الفئة القديمة (للتوافق)")).toHaveValue("Stable Category");
    await expect(page.getByLabel(/السعرات/)).toHaveValue("321");
    await expect(page.getByLabel("ألياف g")).toHaveValue("3.5");
    await expect(page.locator("details.food-optional-section")).toHaveAttribute("open", "");
    expect(await form.evaluate((element) => (element as HTMLFormElement & { __qaInstance?: string }).__qaInstance)).toBe("stable-add-food-form");
    expect(await page.evaluate(() => (window as typeof window & { __qaDocumentId?: string }).__qaDocumentId)).toBe(documentId);
    expect(documentRequests).toBe(documentRequestBaseline);
    expect(mainFrameNavigations).toBe(navigationBaseline);
    expect(hmrErrors).toEqual([]);
  });

  test("preserves all entered values when the create request fails", async ({ page, foodsApi }) => {
    const name = `E2E-Stability-Failed-Write-${Date.now()}`;
    await page.route("**/foods", async (route) => {
      if (route.request().method() === "POST") return route.abort("failed");
      return route.continue();
    });
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name, brand: "Failure Brand", calories: 222 });
    await submitFoodForm(page);

    await expect(page).toHaveURL(/\/foods\/new$/);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(name);
    await expect(page.getByLabel("العلامة التجارية")).toHaveValue("Failure Brand");
    await expect(page.getByLabel(/السعرات/)).toHaveValue("222");
    await expect(page.getByRole("status")).toContainText("تعذر الاتصال بالخادم");
    expect((await foodsApi.list()).some((food) => food.name === name)).toBeFalsy();
  });

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
    await expect(form.locator('button[type="submit"]')).toHaveCount(1);
    const commandButtons = form.locator('button:not([type="submit"])');
    await expect(commandButtons).toHaveCount(1);
    await expect(commandButtons).toHaveAccessibleName("إضافة مساهمة");
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

  test("successful Save is the only tested path that leaves and clears the form", async ({ page, foodsApi }) => {
    const name = `E2E-Stability-Success-${Date.now()}`;
    await page.goto("/foods/new");
    await fillRequiredFoodForm(page, { name });
    await submitFoodForm(page);

    await expect(page).toHaveURL(/\/foods\/[0-9a-f-]+$/);
    await expect(page.locator("form.food-form-layout")).toHaveCount(0);
    const id = page.url().split("/").pop()!;
    expect((await foodsApi.get(id)).name).toBe(name);
    await foodsApi.remove(id);
  });
});
