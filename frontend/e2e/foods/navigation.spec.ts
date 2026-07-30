import { test, expect, expectNoHorizontalOverflow } from "./helpers";

test.describe("Foods navigation and standalone pages @foods", () => {
  test("[FOOD-TC-001] @p0 navigates list, add, details, and edit routes", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E Navigation Rice" });
    await page.goto("/admin/foods");
    await page.getByRole("link", { name: "إضافة طعام" }).click();
    await expect(page).toHaveURL(/\/foods\/new$/);
    await page.goto("/admin/foods");
    await page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first().click();
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}$`));
    await page.getByRole("link", { name: "تعديل" }).click();
    await expect(page).toHaveURL(new RegExp(`/foods/${food.id}/edit$`));
  });

  test("[FOOD-TC-002] @p0 add page has save/cancel/back and no delete", async ({ page }) => {
    await page.goto("/foods/new");
    await expect(page.getByRole("button", { name: "حفظ الطعام" })).toBeVisible();
    await expect(page.getByRole("link", { name: "إلغاء" })).toBeVisible();
    await expect(page.getByRole("link", { name: "رجوع" })).toBeVisible();
    await expect(page.getByRole("button", { name: /حذف/ })).toHaveCount(0);
  });

  test("[FOOD-TC-003] @p0 list page does not contain the Add Food form", async ({ page }) => {
    await page.goto("/foods");
    await expect(page.getByRole("heading", { name: "الأطعمة" })).toBeVisible();
    await expect(page.getByRole("link", { name: "إضافة طعام" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "حفظ الطعام" })).toHaveCount(0);
    await expect(page.locator("form.food-form-layout")).toHaveCount(0);
  });

  test("[FOOD-TC-004] @p1 edit reuses grouped Add Food structure", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E Edit Structure" });
    await page.goto(`/foods/${food.id}/edit`);
    await expect(page.getByRole("heading", { name: "تعديل الطعام" })).toBeVisible();
    for (const heading of ["معلومات الطعام الأساسية", "أساس القيم الغذائية", "القيم الغذائية الأساسية", "الوحدة الافتراضية", "ملاحظات ومصدر البيانات"]) {
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(food.name);
    await expect(page.getByRole("button", { name: "حفظ التعديل" })).toBeVisible();
    await expect(page.getByRole("button", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-005] @p1 @mobile standalone pages fit a 360px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    for (const route of ["/foods/new", "/foods"]) {
      await page.goto(route);
      await expectNoHorizontalOverflow(page);
    }
  });

  test("[FOOD-TC-006] @p1 @plan016 cancel returns without saving after explicit discard", async ({ page, foodsApi }) => {
    const draft = `E2E-Draft-${Date.now()}`;
    await page.goto("/foods/new");
    await page.getByLabel(/اسم الطعام/).fill(draft);
    await page.getByRole("link", { name: "إلغاء" }).click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page.getByLabel(/اسم الطعام/)).toHaveValue(draft);
    await page.getByRole("link", { name: "إلغاء" }).click();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/foods$/);
    expect((await foodsApi.list()).some((food) => food.name === draft)).toBeFalsy();
  });

  test("[FOOD-TC-008] @plan016 dirty edit keeps draft across refetch and loads server only after discard", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: "E2E Plan016 Original" });
    let reads = 0;
    await page.route((url) => url.pathname === `/foods/${food.id}`, async (route) => {
      if (route.request().method() !== "GET") return route.continue();
      reads += 1;
      if (reads === 1) return route.continue();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        json: { ...food, name: "E2E Plan016 Server" }
      });
    });
    await page.goto(`/foods/${food.id}/edit`);
    const input = page.getByLabel(/اسم الطعام/);
    await input.fill("E2E Plan016 Draft");
    await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
    await expect(page.getByText("توجد نسخة أحدث من هذا الطعام على الخادم. احتفظنا بتعديلاتك الحالية.")).toBeVisible();
    await expect(input).toHaveValue("E2E Plan016 Draft");
    await page.getByRole("button", { name: "تحميل نسخة الخادم" }).click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(input).toHaveValue("E2E Plan016 Draft");
    await page.getByRole("button", { name: "تحميل نسخة الخادم" }).click();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(input).toHaveValue("E2E Plan016 Server");
  });

  test("[FOOD-TC-009] @plan016 Food brand and AppNav navigation share cancel and discard", async ({ page }) => {
    await page.goto("/foods/new");
    const input = page.getByLabel(/اسم الطعام/);
    await input.fill("E2E Plan016 shared navigation");
    await page.locator("a.brand").click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/foods\/new$/);
    await expect(input).toHaveValue("E2E Plan016 shared navigation");
    await page.getByRole("link", { name: "اليوميات" }).click();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/diary$/);
  });

  test("[FOOD-TC-010] @plan016 Food Back repeatedly cancels without a loop and discards once", async ({ page }) => {
    await page.goto("/diary");
    await page.getByRole("link", { name: "الأطعمة" }).click();
    await page.getByRole("link", { name: "إضافة طعام" }).click();
    const input = page.getByLabel(/اسم الطعام/);
    await input.fill("E2E Plan016 Back draft");
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    for (let attempt = 0; attempt < 2; attempt += 1) {
      await page.evaluate(() => history.back());
      await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
      await expect(page).toHaveURL(/\/foods\/new$/);
      await expect(input).toHaveValue("E2E Plan016 Back draft");
    }
    await page.evaluate(() => history.back());
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/foods$/);
    await page.goBack();
    await expect(page).toHaveURL(/\/diary$/);
  });

  test("[FOOD-TC-011] @plan016 Food Forward cancel has no destination exposure and discard preserves order", async ({ page }) => {
    await page.goto("/foods");
    await page.getByRole("link", { name: "إضافة طعام" }).click();
    await page.getByRole("link", { name: "اليوميات" }).click();
    await page.goBack();
    const input = page.getByLabel(/اسم الطعام/);
    await input.fill("E2E Plan016 Forward draft");
    await page.evaluate(() => {
      const exposures: string[] = [];
      new MutationObserver(() => {
        if (document.querySelector("h1")?.textContent?.includes("اليوميات")) exposures.push(document.body.innerText);
      }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
      (window as Window & { __plan016DestinationExposures?: string[] }).__plan016DestinationExposures = exposures;
    });
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await page.evaluate(() => history.forward());
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    await expect(page).toHaveURL(/\/foods\/new$/);
    await expect(input).toHaveValue("E2E Plan016 Forward draft");
    expect(await page.evaluate(() => (window as Window & { __plan016DestinationExposures?: string[] }).__plan016DestinationExposures ?? [])).toEqual([]);
    await page.evaluate(() => history.forward());
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/diary$/);
    await page.goBack();
    await expect(page).toHaveURL(/\/foods\/new$/);
  });

  test("[FOOD-TC-012] @plan016 dirty Food sign-out cancel is zero calls and confirm is one call", async ({ page }) => {
    let logoutCalls = 0;
    await page.route("**/auth/v1/logout**", async (route) => {
      logoutCalls += 1;
      await route.continue();
    });
    await page.goto("/foods/new");
    await page.getByLabel(/اسم الطعام/).fill("E2E Plan016 sign-out draft");
    await page.locator(".nav-signout").click();
    const dialog = page.getByRole("dialog", { name: "تغييرات غير محفوظة" });
    await dialog.getByRole("button", { name: "متابعة التعديل" }).click();
    expect(logoutCalls).toBe(0);
    await page.locator(".nav-signout").click();
    await dialog.getByRole("button", { name: "تجاهل التغييرات والمغادرة" }).click();
    await expect(page).toHaveURL(/\/auth\/login/);
    expect(logoutCalls).toBe(1);
  });

  test("[FOOD-TC-007] @p0 unauthorized Foods read exposes no catalog data", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Unauthorized" }) });
    });
    await page.goto("/foods");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(0);
  });
});
