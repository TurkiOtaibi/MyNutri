import { test, expect, fillRequiredFoodForm, submitFoodForm, expectNoHorizontalOverflow } from "./helpers";

test.describe("Food details and editing @foods", () => {
  test("[FOOD-TC-032][FOOD-TC-131] @p0 detail read failure shows exact Arabic error", async ({ page }) => {
    const id = "00000000-0000-4000-8000-000000000032";
    await page.route(`**/foods/${id}`, (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      return route.fulfill({ status: 500, body: "failure" });
    });
    await page.goto(`/foods/${id}`);
    await expect(page.locator(".catalog-state[role=alert]")).toContainText("تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.");
    await expect(page.getByRole("link", { name: "تعديل" })).toHaveCount(0);
  });

  test("[FOOD-TC-033] @p0 edit read failure prevents editable form", async ({ page }) => {
    const id = "00000000-0000-4000-8000-000000000033";
    await page.route(`**/foods/${id}`, (route) => route.fulfill({ status: 500, body: "failure" }));
    await page.goto(`/foods/${id}/edit`);
    await expect(page.locator(".state-note[role=alert]")).toHaveText("تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.");
    await expect(page.getByRole("button", { name: "حفظ التعديل" })).toHaveCount(0);
  });

  test("[FOOD-TC-106] @p0 edit form loads current values", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Edit-Load-${Date.now()}`, brand: "Brand Load", calories: 321 });
    await page.goto(`/foods/${food.id}/edit`);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(food.name);
    await expect(page.getByLabel("العلامة التجارية")).toHaveValue("Brand Load");
    await expect(page.getByLabel(/السعرات/)).toHaveValue("321");
  });

  test("[FOOD-TC-107] @p0 valid edit saves and appears in details", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Edit-Save-${Date.now()}` });
    const editedName = `${food.name}-Updated`;
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByLabel(/اسم الطعام/).fill(editedName);
    await page.getByLabel(/السعرات/).fill("222.5");
    await submitFoodForm(page, "edit");
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
    await expect(page.getByRole("heading", { name: editedName })).toBeVisible();
    expect((await foodsApi.get(food.id)).calories).toBe(222.5);
  });

  test("[FOOD-TC-108] @p1 unchanged edit remains valid", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Unchanged-${Date.now()}` });
    await page.goto(`/foods/${food.id}/edit`);
    await submitFoodForm(page, "edit");
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
    expect((await foodsApi.get(food.id)).name).toBe(food.name);
  });

  test("[FOOD-TC-109] @p0 invalid edit is blocked and persisted Food is unchanged", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Invalid-Edit-${Date.now()}`, calories: 100 });
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByLabel(/السعرات/).fill("3001");
    await submitFoodForm(page, "edit");
    await expect(page.getByLabel(/السعرات/)).toHaveAttribute("aria-invalid", "true");
    expect((await foodsApi.get(food.id)).calories).toBe(100);
  });

  test("[FOOD-TC-110] @p0 failed edit preserves input", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Failed-Edit-${Date.now()}` });
    const draft = `${food.name}-Draft`;
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByLabel(/اسم الطعام/).fill(draft);
    await page.route(`**/foods/${food.id}`, async (route) => {
      if (route.request().method() === "PUT") return route.abort("failed");
      return route.continue();
    });
    await submitFoodForm(page, "edit");
    await expect(page.getByRole("status")).toContainText("تعذر الاتصال بالخادم");
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(draft);
    expect((await foodsApi.get(food.id)).name).toBe(food.name);
  });

  test("[FOOD-TC-111] @p0 unauthorized edit is rejected", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Unauthorized-Edit-${Date.now()}` });
    await page.goto(`/foods/${food.id}/edit`);
    await page.route(`**/foods/${food.id}`, async (route) => {
      if (route.request().method() === "PUT") return route.fulfill({ status: 401, body: "unauthorized" });
      return route.continue();
    });
    await page.getByLabel(/اسم الطعام/).fill(`${food.name}-Denied`);
    await submitFoodForm(page, "edit");
    expect((await foodsApi.get(food.id)).name).toBe(food.name);
  });

  test("[FOOD-TC-112] @p0 stale deleted Food cannot be edited", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Stale-Edit-${Date.now()}` });
    await page.goto(`/foods/${food.id}/edit`);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(food.name);
    await foodsApi.remove(food.id);
    await page.getByLabel(/اسم الطعام/).fill(`${food.name}-Stale`);
    await submitFoodForm(page, "edit");
    await expect(page.locator(".state-note[role=alert]")).toBeVisible();
    const listed = await foodsApi.list();
    expect(listed.some((item) => item.id === food.id)).toBeFalsy();
  });

  test("[FOOD-TC-113] @p1 conflict response preserves edit draft", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Conflict-${Date.now()}` });
    const draft = `${food.name}-Draft`;
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByLabel(/اسم الطعام/).fill(draft);
    await page.route(`**/foods/${food.id}`, async (route) => {
      if (route.request().method() === "PUT") return route.fulfill({ status: 409, body: "conflict" });
      return route.continue();
    });
    await submitFoodForm(page, "edit");
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(draft);
    expect((await foodsApi.get(food.id)).name).toBe(food.name);
  });

  test("[FOOD-TC-114] @p1 cancel edit persists no changes", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Cancel-Edit-${Date.now()}` });
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByLabel(/اسم الطعام/).fill(`${food.name}-Unsaved`);
    await page.getByRole("link", { name: "إلغاء" }).click();
    expect((await foodsApi.get(food.id)).name).toBe(food.name);
  });

  test("[FOOD-TC-115] @p0 old Diary snapshot does not change after Food edit", async ({ foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Snapshot-Edit-${Date.now()}`, calories: 100 });
    const date = new Date().toISOString().slice(0, 10);
    const entry = await foodsApi.createDiary(food.id, date, 1);
    const update = await foodsApi.update(food.id, { calories: 300, name: `${food.name}-Updated` });
    expect(update.status()).toBe(200);
    const current = (await foodsApi.listDiary(date)).find((item) => item.id === entry.id)!;
    expect(current.nutrition_snapshot.name).toBe(food.name);
    expect(current.totals.calories).toBe(100);
  });

  test("[FOOD-TC-116] @p1 @mobile edit supports RTL mixed text without overflow", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `طعام E2E Edit 100 ${Date.now()}` });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/foods/${food.id}/edit`);
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(food.name);
    expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-117] @p1 cross-field-invalid edit is blocked", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Cross-Edit-${Date.now()}`, carb_g: 10 });
    await page.goto(`/foods/${food.id}/edit`);
    await page.getByText("القيم الغذائية الإضافية", { exact: true }).click();
    await page.getByLabel("ألياف g").fill("11");
    await submitFoodForm(page, "edit");
    await expect(page.getByText("الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.", { exact: true })).toBeVisible();
    expect((await foodsApi.get(food.id)).fiber_g).toBeNull();
  });

  test("[FOOD-TC-128] @p0 details show full core, optional, and metadata values", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({
      name: `E2E-Full-Details-${Date.now()}`,
      brand: "Detail Brand",
      category: "Detail Category",
      fiber_g: 4,
      sugar_g: 8,
      added_sugar_g: 2,
      notes: "Detail notes",
      data_source: "USDA"
    });
    await page.goto(`/foods/${food.id}`);
    for (const value of [food.name, "Detail Brand", "Detail Category", "Detail notes", "USDA", "4 جم", "8 جم", "2 جم"]) {
      await expect(page.getByText(value, { exact: true }).first()).toBeVisible();
    }
  });

  test("[FOOD-TC-129] @p1 details handle blank optional nutrients without errors", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Blank-Details-${Date.now()}` });
    await page.goto(`/foods/${food.id}`);
    await expect(page.locator("main.main-surface").getByRole("alert")).toHaveCount(0);
    await expect(page.locator(".nutrition-row", { hasText: "-" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "الفيتامينات" })).toHaveCount(0);
  });

  test("[FOOD-TC-130] @p1 long full name is visible on details", async ({ page, foodsApi }) => {
    const name = `طعام E2E ${"طويل ".repeat(18)}`.slice(0, 120);
    const food = await foodsApi.create({ name });
    await page.goto(`/foods/${food.id}`);
    const title = page.getByRole("heading", { name: food.name });
    await expect(title).toBeVisible();
    expect(await title.evaluate((element) => getComputedStyle(element).webkitLineClamp)).not.toBe("2");
  });

  test("[FOOD-TC-132] @p0 deleted detail route shows not-found/read error", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Deleted-Detail-${Date.now()}` });
    await foodsApi.remove(food.id);
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("[FOOD-TC-133] @p1 details expose Edit and Delete actions", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Detail-Actions-${Date.now()}` });
    await page.goto(`/foods/${food.id}`);
    await expect(page.getByRole("link", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("button", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-134] @p0 unauthorized detail exposes no Food data", async ({ page }) => {
    const id = "00000000-0000-4000-8000-000000000134";
    await page.route(`**/foods/${id}`, (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      return route.fulfill({ status: 401, body: "unauthorized" });
    });
    await page.goto(`/foods/${id}`);
    await expect(page.locator(".catalog-state[role=alert]")).toBeVisible();
    await expect(page.getByRole("button", { name: "حذف" })).toHaveCount(0);
  });
});
