import { test, expect, expectNoHorizontalOverflow, validFood } from "./helpers";

test.describe("Foods list, search, and states @foods", () => {
  test("[FOOD-TC-008] @p0 desktop table shows approved columns", async ({ page, foodsApi }) => {
    await foodsApi.create({ name: `E2E-Desktop-Table-${Date.now()}` });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/foods");
    for (const column of ["الطعام", "التصنيف", "الحصة الافتراضية", "السعرات", "البروتين", "الكارب", "الدهون"]) {
      await expect(page.getByRole("columnheader", { name: column })).toBeVisible();
    }
  });

  test("[FOOD-TC-009] @p0 @mobile mobile uses cards with core Food values", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Mobile-Card-${Date.now()}`, calories: 222, protein_g: 11, carb_g: 33, fat_g: 7 });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");
    await expect(page.locator(".food-table-wrap")).toBeHidden();
    const card = page.locator(".food-card", { hasText: food.name });
    await expect(card).toBeVisible();
    await expect(card).toContainText("222");
    await expect(card).toContainText("11");
    await expect(card).toContainText("33");
    await expect(card).toContainText("7");
  });

  test("[FOOD-TC-010] @p1 main list omits optional micronutrients", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-No-Micros-${Date.now()}`, vitamin_d_mcg: 12, sodium_mg: 50 });
    await page.goto("/foods");
    const row = page.getByRole("row", { name: new RegExp(food.name) });
    await expect(row).toBeVisible();
    await expect(row).not.toContainText("Vitamin");
    await expect(row).not.toContainText("فيتامين");
    await expect(row).not.toContainText("صوديوم");
  });

  test("[FOOD-TC-011] @p1 @mobile long names clamp to two lines without overflow", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `طعام E2E Mixed ${"طويل ".repeat(15)}Name` });
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/foods");
    const title = page.locator(".food-card-title", { hasText: "E2E Mixed" });
    await expect(title).toBeVisible();
    expect(await title.evaluate((element) => getComputedStyle(element).webkitLineClamp)).toBe("2");
    await expectNoHorizontalOverflow(page);
    expect(food.name.length).toBeGreaterThan(40);
  });

  test("[FOOD-TC-012] @p0 list has no archive/status UI", async ({ page }) => {
    await page.goto("/foods");
    for (const text of ["Status", "Archived", "Active", "is_active", "archived_at", "استعادة", "مؤرشف", "غير نشط"]) {
      await expect(page.getByText(text, { exact: false })).toHaveCount(0);
    }
  });

  test("[FOOD-TC-013] @p0 hard-deleted Food is absent from list", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Deleted-List-${Date.now()}` });
    await foodsApi.remove(food.id);
    await page.goto("/foods");
    await expect(page.getByText(food.name, { exact: true })).toHaveCount(0);
  });

  test("[FOOD-TC-014] @p0 saved Food exposes View, Edit, and Delete actions", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Actions-${Date.now()}` });
    await page.goto("/admin/foods");
    await expect(page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first()).toBeVisible();
    await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-015] @p0 current Food appears in future Diary selection", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Diary-Picker-${Date.now()}` });
    await page.goto("/diary");
    await page.getByRole("button", { name: "إضافة طعام إلى فطور" }).click();
    const dialog = page.getByRole("dialog", { name: "إضافة طعام" });
    await dialog.getByPlaceholder("ابحث باسم الطعام أو العلامة التجارية").fill(food.name);
    await expect(dialog.getByRole("button", { name: new RegExp(food.name) })).toBeVisible();
  });

  test("[FOOD-TC-016] @p1 mixed Arabic/English list text remains RTL-readable", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `شوفان E2E Oats 100 ${Date.now()}` });
    await page.goto("/foods");
    await expect(page.getByText(food.name, { exact: true }).first()).toBeVisible();
    expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
  });

  const searchCases = [
    { id: "FOOD-TC-017", priority: "@p0", term: "ExactSearch", name: "ExactSearch Food" },
    { id: "FOOD-TC-018", priority: "@p0", term: "Partial", name: "E2E Partial Match Food" },
    { id: "FOOD-TC-019", priority: "@p1", term: "Mix 100", name: "طعام Mix 100 Test" },
    { id: "FOOD-TC-020", priority: "@p0", term: "شوفان", name: "شوفان عضوي" }
  ];

  for (const item of searchCases) {
    test(`[${item.id}] ${item.priority} search finds matching current Food`, async ({ page, foodsApi }) => {
      const match = await foodsApi.create({ name: `${item.name} ${Date.now()}` });
      const other = await foodsApi.create({ name: `E2E-Unrelated-${Date.now()}` });
      await page.goto("/foods");
      await page.getByLabel("بحث باسم الطعام").fill(item.term);
      await expect(page.getByText(match.name, { exact: true }).first()).toBeVisible();
      await expect(page.getByText(other.name, { exact: true })).toHaveCount(0);
    });
  }

  test("[FOOD-TC-021] @p1 search trims whitespace", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E Trim Search ${Date.now()}` });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill("   Trim Search   ");
    await expect(page.getByText(food.name, { exact: true }).first()).toBeVisible();
  });

  test("[FOOD-TC-022] @p0 no-results state is shown", async ({ page, foodsApi }) => {
    await foodsApi.create({ name: `E2E-Existing-${Date.now()}` });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill(`NoMatch-${Date.now()}`);
    await expect(page.getByText("لا توجد نتائج مطابقة للبحث.", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-023] @p1 clearing search restores full catalog", async ({ page, foodsApi }) => {
    const first = await foodsApi.create({ name: `E2E-Clear-One-${Date.now()}` });
    const second = await foodsApi.create({ name: `E2E-Clear-Two-${Date.now()}` });
    await page.goto("/foods");
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill("Clear-One");
    await expect(page.getByText(second.name, { exact: true })).toHaveCount(0);
    await search.fill("");
    await expect(page.getByText(first.name, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(second.name, { exact: true }).first()).toBeVisible();
  });

  test("[FOOD-TC-024] @p0 deleted Food is absent from search", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Deleted-Search-${Date.now()}` });
    await foodsApi.remove(food.id);
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill("Deleted-Search");
    await expect(page.getByText(food.name, { exact: true })).toHaveCount(0);
  });

  test("[FOOD-TC-025] @p0 search read failure shows Arabic error", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 500, body: "failure" });
    });
    await page.goto("/foods");
    await expect(page.locator(".catalog-state[role=alert]")).toContainText("تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.");
  });

  test("[FOOD-TC-026] @p1 @mobile search remains usable at 360px", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/foods");
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill("شوفان Oats");
    await expect(search).toHaveValue("شوفان Oats");
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-027] @p0 loading state is visible while Foods request is pending", async ({ page }) => {
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await pending;
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/foods");
    await expect(page.getByText("جاري تحميل الأطعمة.", { exact: true })).toBeVisible();
    release();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-028] @p0 empty catalog state links to Add Food", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/foods");
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "إضافة أول طعام" })).toHaveCount(0);
  });

  test("[FOOD-TC-029] @p1 no-results differs from empty catalog state", async ({ page, foodsApi }) => {
    await foodsApi.create({ name: `E2E-State-Distinction-${Date.now()}` });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill("No-Match");
    await expect(page.getByText("لا توجد نتائج مطابقة للبحث.", { exact: true })).toBeVisible();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toHaveCount(0);
  });

  test("[FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry", async ({ page }) => {
    let failing = true;
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      if (failing) return route.fulfill({ status: 500, body: "failure" });
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/foods");
    await expect(page.locator(".catalog-state[role=alert]")).toBeVisible();
    failing = false;
    await page.reload();
    await expect(page.locator(".catalog-state[role=alert]")).toHaveCount(0);
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-034] @p1 @mobile state messages do not overflow", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/foods");
    await expect(page.locator(".catalog-state")).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-035] @p1 @a11y read failure is exposed as an alert", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 500, body: "failure" });
    });
    await page.goto("/foods");
    const alert = page.locator(".catalog-state[role=alert]");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.");
  });

  test("[FOOD-TC-140] @p2 renders a 200-Food catalog without broken layout", async ({ page }) => {
    const foods = Array.from({ length: 200 }, (_, index) => ({
      ...validFood({ name: index < 20 ? `E2E Rice ${index}` : `E2E Food ${index}` }),
      id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
      net_carbs_g: 20,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z"
    }));
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      const query = new URL(route.request().url()).searchParams.get("q")?.toLowerCase();
      const result = query ? foods.filter((food) => food.name.toLowerCase().includes(query)) : foods;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
    });
    await page.goto("/foods");
    await page.getByLabel("بحث باسم الطعام").fill("rice");
    await expect(page.locator("tbody tr")).toHaveCount(20);
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-141] @p1 archive controls stay absent while catalog sort/filter are available", async ({ page }) => {
    await page.goto("/foods");
    await expect(page.getByLabel("بحث باسم الطعام")).toBeVisible();
    await expect(page.getByLabel("ترتيب الأطعمة").first()).toBeVisible();
    await expect(page.getByLabel("تصفية حسب التصنيف")).toBeVisible();
    for (const label of ["الحالة", "مؤرشف", "نشط", "استعادة"]) {
      await expect(page.getByRole("button", { name: label })).toHaveCount(0);
      await expect(page.getByRole("combobox", { name: label })).toHaveCount(0);
    }
  });
});
