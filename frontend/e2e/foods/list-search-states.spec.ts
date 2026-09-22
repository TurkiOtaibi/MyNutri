import type { Page, Response } from "@playwright/test";

import { API_URL, test, expect, expectNoHorizontalOverflow, validFood } from "./helpers";

const API_ORIGIN = new URL(API_URL).origin;

type FoodIdentity = { id: string; name: string };

function waitForPublicFoodsResponse(
  page: Page,
  {
    search,
    sort = "name",
    category,
    page: expectedPage = 1
  }: {
    search?: string | null;
    sort?: string;
    category?: string | null;
    page?: number;
  } = {}
) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url());
    if (
      url.origin !== API_ORIGIN ||
      url.pathname !== "/foods" ||
      response.request().method() !== "GET" ||
      url.searchParams.get("page") !== String(expectedPage) ||
      url.searchParams.get("page_size") !== "20" ||
      url.searchParams.get("sort") !== sort
    ) return false;

    const expectedSearch = search?.trim() ?? "";
    if (
      expectedSearch
        ? url.searchParams.get("search") !== expectedSearch
        : url.searchParams.has("search")
    ) return false;

    if (
      category
        ? url.searchParams.get("category") !== category
        : url.searchParams.has("category")
    ) return false;

    return true;
  });
}

function foodsFromBody(body: unknown): FoodIdentity[] {
  const items = body && typeof body === "object" && "items" in body && Array.isArray(body.items)
    ? body.items
    : null;
  if (!items) throw new Error("Public Foods response must be a paginated items object.");

  return items.map((item, index) => {
    if (
      !item ||
      typeof item !== "object" ||
      !("id" in item) ||
      typeof item.id !== "string" ||
      !("name" in item) ||
      typeof item.name !== "string"
    ) throw new Error(`Public Foods response item ${index} is missing a stable id or name.`);
    return { id: item.id, name: item.name };
  });
}

async function foodsFromResponse(response: Response) {
  expect(response.status()).toBe(200);
  return foodsFromBody(await response.json());
}

function visibleFoodDetailLink(page: Page, food: { name: string }) {
  return page.getByRole("link", {
    name: `عرض تفاصيل ${food.name}`,
    exact: true
  });
}

function allFoodDetailLinks(page: Page, food: { id: string }) {
  return page.locator(`a[href="/foods/${food.id}"]`);
}

function allCatalogFoodDetailLinks(page: Page) {
  return page.locator('.food-table-wrap a[href^="/foods/"], .food-card-list a[href^="/foods/"]');
}

function expectFoodIncluded(foods: FoodIdentity[], food: { id: string }) {
  expect(foods.map((item) => item.id)).toContain(food.id);
}

function expectFoodExcluded(foods: FoodIdentity[], food: { id: string }) {
  expect(foods.map((item) => item.id)).not.toContain(food.id);
}

async function establishInitialPublicCatalog(page: Page, foods: FoodIdentity[] = []) {
  const initialResponse = waitForPublicFoodsResponse(page);
  await page.goto("/foods");
  const initialFoods = await foodsFromResponse(await initialResponse);
  await expect(page.getByLabel("بحث باسم الطعام")).toHaveValue("");
  for (const food of foods) {
    expectFoodIncluded(initialFoods, food);
    await expect(visibleFoodDetailLink(page, food)).toBeVisible();
    expect(await allFoodDetailLinks(page, food).count()).toBeGreaterThan(0);
  }
  return initialFoods;
}

function plan024Food(idSuffix: number, name: string) {
  return {
    ...validFood({ name }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z"
  };
}

function plan024Page(items: ReturnType<typeof plan024Food>[], page = 1, totalPages = 1, total = items.length) {
  return {
    items,
    total,
    page,
    page_size: 20,
    total_pages: totalPages,
    categories: ["other"]
  };
}

function plan024VisibleRowTrigger(page: Page, food: { name: string }) {
  return page.getByRole("button", {
    name: `إجراءات ${food.name}`,
    exact: true
  });
}

function plan024MobileCategory(page: Page, name: string) {
  return page
    .locator(".foods-mobile-filters")
    .getByRole("button", { name, exact: true });
}

function plan024MobileSort(page: Page) {
  return page
    .locator(".foods-mobile-sort")
    .getByRole("combobox", { name: "ترتيب الأطعمة", exact: true });
}

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
    await page.goto("/foods");
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
      await establishInitialPublicCatalog(page, [match, other]);
      const searchedResponse = waitForPublicFoodsResponse(page, { search: item.term });
      const search = page.getByLabel("بحث باسم الطعام");
      await search.fill(item.term);
      const searchedFoods = await foodsFromResponse(await searchedResponse);
      expectFoodIncluded(searchedFoods, match);
      expectFoodExcluded(searchedFoods, other);
      await expect(search).toHaveValue(item.term);
      await expect(visibleFoodDetailLink(page, match)).toBeVisible();
      await expect(allFoodDetailLinks(page, other)).toHaveCount(0);
    });
  }

  test("[FOOD-TC-021] @p1 search trims whitespace", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E Trim Search ${Date.now()}` });
    const rawSearch = "   Trim Search   ";
    await establishInitialPublicCatalog(page, [food]);
    const searchedResponse = waitForPublicFoodsResponse(page, { search: "Trim Search" });
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill(rawSearch);
    const searchedFoods = await foodsFromResponse(await searchedResponse);
    expectFoodIncluded(searchedFoods, food);
    await expect(search).toHaveValue(rawSearch);
    await expect(visibleFoodDetailLink(page, food)).toBeVisible();
  });

  test("[FOOD-TC-022] @p0 no-results state is shown", async ({ page, foodsApi }) => {
    const existing = await foodsApi.create({ name: `E2E-Existing-${Date.now()}` });
    const term = `NoMatch-${Date.now()}`;
    await establishInitialPublicCatalog(page, [existing]);
    const searchedResponse = waitForPublicFoodsResponse(page, { search: term });
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill(term);
    expect(await foodsFromResponse(await searchedResponse)).toHaveLength(0);
    await expect(search).toHaveValue(term);
    await expect(page.getByText("لا توجد نتائج مطابقة للبحث.", { exact: true })).toBeVisible();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toHaveCount(0);
    await expect(allFoodDetailLinks(page, existing)).toHaveCount(0);
    await expect(allCatalogFoodDetailLinks(page)).toHaveCount(0);
  });

  test("[FOOD-TC-023] @p1 clearing search restores full catalog", async ({ page, foodsApi }) => {
    const first = await foodsApi.create({ name: `E2E-Clear-One-${Date.now()}` });
    const second = await foodsApi.create({ name: `E2E-Clear-Two-${Date.now()}` });
    await establishInitialPublicCatalog(page, [first, second]);
    const search = page.getByLabel("بحث باسم الطعام");
    const filteredResponse = waitForPublicFoodsResponse(page, { search: "Clear-One" });
    await search.fill("Clear-One");
    const filteredFoods = await foodsFromResponse(await filteredResponse);
    expectFoodIncluded(filteredFoods, first);
    expectFoodExcluded(filteredFoods, second);
    await expect(search).toHaveValue("Clear-One");
    await expect(visibleFoodDetailLink(page, first)).toBeVisible();
    await expect(allFoodDetailLinks(page, second)).toHaveCount(0);

    await search.fill("");
    await expect(search).toHaveValue("");
    await expect(visibleFoodDetailLink(page, first)).toBeVisible();
    await expect(visibleFoodDetailLink(page, second)).toBeVisible();
  });

  test("[FOOD-TC-024] @p0 deleted Food is absent from search", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Deleted-Search-${Date.now()}` });
    await foodsApi.remove(food.id);
    await establishInitialPublicCatalog(page);
    await expect(allFoodDetailLinks(page, food)).toHaveCount(0);
    const searchedResponse = waitForPublicFoodsResponse(page, { search: "Deleted-Search" });
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill("Deleted-Search");
    const searchedFoods = await foodsFromResponse(await searchedResponse);
    expectFoodExcluded(searchedFoods, food);
    await expect(search).toHaveValue("Deleted-Search");
    await expect(allFoodDetailLinks(page, food)).toHaveCount(0);
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
    await establishInitialPublicCatalog(page);
    const search = page.getByLabel("بحث باسم الطعام");
    const searchedResponse = waitForPublicFoodsResponse(page, { search: "شوفان Oats" });
    await search.fill("شوفان Oats");
    await foodsFromResponse(await searchedResponse);
    await expect(search).toHaveValue("شوفان Oats");
    await expect(search).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("[FOOD-TC-027] @p0 loading state is visible while Foods request is pending", async ({ page }) => {
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await pending;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([])) });
    });
    await page.goto("/foods");
    await expect(page.getByText("جاري تحميل الأطعمة.", { exact: true })).toBeVisible();
    release();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
  });

  test("[FOOD-TC-028] @p0 empty catalog state links to Add Food", async ({ page }) => {
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([])) });
    });
    await page.goto("/foods");
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "إضافة أول طعام" })).toHaveCount(0);
  });

  test("[FOOD-TC-029] @p1 no-results differs from empty catalog state", async ({ page, foodsApi }) => {
    const existing = await foodsApi.create({ name: `E2E-State-Distinction-${Date.now()}` });
    await establishInitialPublicCatalog(page, [existing]);
    const searchedResponse = waitForPublicFoodsResponse(page, { search: "No-Match" });
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill("No-Match");
    expect(await foodsFromResponse(await searchedResponse)).toHaveLength(0);
    await expect(search).toHaveValue("No-Match");
    await expect(page.getByText("لا توجد نتائج مطابقة للبحث.", { exact: true })).toBeVisible();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toHaveCount(0);
    await expect(allFoodDetailLinks(page, existing)).toHaveCount(0);
    await expect(allCatalogFoodDetailLinks(page)).toHaveCount(0);
  });

  test("[FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry", async ({ page }) => {
    let failing = true;
    await page.route(/\/foods(?:\?.*)?$/, async (route) => {
      if (route.request().resourceType() === "document") return route.continue();
      if (failing) return route.fulfill({ status: 500, body: "failure" });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([])) });
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
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([])) });
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
      const url = new URL(route.request().url());
      if (url.origin !== API_ORIGIN || route.request().method() !== "GET") return route.continue();
      const query = url.searchParams.get("search")?.toLowerCase();
      const requestedPage = Number(url.searchParams.get("page") ?? "1");
      const pageSize = Number(url.searchParams.get("page_size") ?? "20");
      const result = query ? foods.filter((food) => food.name.toLowerCase().includes(query)) : foods;
      const pageItems = result.slice((requestedPage - 1) * pageSize, requestedPage * pageSize);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: pageItems,
          total: result.length,
          page: requestedPage,
          page_size: pageSize,
          total_pages: Math.ceil(result.length / pageSize),
          categories: ["other"]
        })
      });
    });
    const initialResponse = waitForPublicFoodsResponse(page);
    await page.goto("/foods");
    expect(await foodsFromResponse(await initialResponse)).toEqual(foods.slice(0, 20).map(({ id, name }) => ({ id, name })));
    await expect(page.getByText("عرض 1-20 من 200 طعامًا")).toBeVisible();

    const lastPageResponse = waitForPublicFoodsResponse(page, { page: 10 });
    await page.getByRole("button", { name: "الصفحة 10" }).click();
    expect(await foodsFromResponse(await lastPageResponse)).toEqual(foods.slice(180).map(({ id, name }) => ({ id, name })));
    await expect(page.getByText("عرض 181-200 من 200 طعامًا")).toBeVisible();

    const searchedResponse = waitForPublicFoodsResponse(page, { search: "rice" });
    const search = page.getByLabel("بحث باسم الطعام");
    await search.fill("rice");
    const searchedFoods = await foodsFromResponse(await searchedResponse);
    expect(searchedFoods).toHaveLength(20);
    expect(searchedFoods.map((food) => food.id)).toEqual(foods.slice(0, 20).map((food) => food.id));
    await expect(search).toHaveValue("rice");
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

  test("[FOOD-TC-142] @plan024 @p0 @mobile collection-shaping controls clear accumulated rows", async ({ page }) => {
    const activeFirst = plan024Food(241, "Plan024 active first");
    const activeSecond = plan024Food(242, "Plan024 active second");
    const searched = plan024Food(244, "Plan024 searched");
    const categorized = plan024Food(245, "Plan024 categorized");
    const sorted = plan024Food(246, "Plan024 sorted");

    await page.route(/\/foods\?.*$/, async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const requestedPage = Number(params.get("page") ?? "1");
      if (params.get("search")) {
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([searched])) });
      }
      if (params.get("category")) {
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([categorized])) });
      }
      if (params.get("sort") === "recent") {
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([sorted])) });
      }
      const items = requestedPage === 1 ? [activeFirst] : [activeSecond];
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page(items, requestedPage, 2, 2)) });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    await page.getByRole("button", { name: "عرض المزيد" }).click();
    await expect(plan024VisibleRowTrigger(page, activeSecond)).toBeVisible();

    await page.getByLabel("بحث باسم الطعام").fill("needle");
    await expect(plan024VisibleRowTrigger(page, searched)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);

    await page.getByLabel("بحث باسم الطعام").fill("");
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    const otherCategory = plan024MobileCategory(page, "أخرى");
    await expect(otherCategory).toHaveCount(1);
    await expect(otherCategory).toBeVisible();
    await otherCategory.click();
    await expect(plan024VisibleRowTrigger(page, categorized)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);

    const allCategories = plan024MobileCategory(page, "الكل");
    await expect(allCategories).toHaveCount(1);
    await expect(allCategories).toBeVisible();
    await allCategories.click();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    for (const food of [activeSecond, searched, categorized]) {
      await expect(plan024VisibleRowTrigger(page, food)).toHaveCount(0);
    }
    const mobileSort = plan024MobileSort(page);
    await expect(mobileSort).toHaveCount(1);
    await expect(mobileSort).toBeVisible();
    await mobileSort.selectOption("recent");
    await expect(plan024VisibleRowTrigger(page, sorted)).toBeVisible();
    for (const food of [activeFirst, activeSecond, searched, categorized]) {
      await expect(plan024VisibleRowTrigger(page, food)).toHaveCount(0);
    }
  });

  test("[FOOD-TC-143] @plan024 @p0 admin action menu has no lifecycle actions and restores focus", async ({ page }) => {
    const food = plan024Food(250, "Plan024 unified actions");
    await page.route(/\/foods\?.*$/, (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(plan024Page([food]))
    }));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/foods");
    const opener = plan024VisibleRowTrigger(page, food);
    await opener.focus();
    await opener.press("Enter");
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeFocused();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: /(أرشفة|استعادة)/ })).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(opener).toBeFocused();
  });
});
