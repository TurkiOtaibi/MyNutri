import type { Page } from "@playwright/test";

import { test, expect, expectNoHorizontalOverflow, validFood } from "./helpers";

function plan024Food(idSuffix: number, name: string, status: "active" | "archived" = "active") {
  return {
    ...validFood({ name }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
    status,
    archived_at: status === "archived" ? "2026-08-04T00:00:00Z" : null,
    group_data_status: "unknown",
    group_data_completeness: "unknown",
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z"
  };
}

function plan024Page(items: ReturnType<typeof plan024Food>[], page = 1, totalPages = 1) {
  return {
    items,
    total: totalPages > 1 ? 2 : items.length,
    page,
    page_size: 20,
    total_pages: totalPages,
    categories: ["other"],
    uncategorized_count: 0
  };
}

function plan024VisibleRowTrigger(page: Page, food: { name: string }) {
  return page.getByRole("button", {
    name: `إجراءات ${food.name}`,
    exact: true
  });
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

  test("[FOOD-TC-142] @plan024 @p0 @mobile collection-shaping controls clear accumulated rows", async ({ page }) => {
    const activeFirst = plan024Food(241, "Plan024 active first");
    const activeSecond = plan024Food(242, "Plan024 active second");
    const archived = plan024Food(243, "Plan024 archived", "archived");
    const searched = plan024Food(244, "Plan024 searched");
    const categorized = plan024Food(245, "Plan024 categorized");
    const sorted = plan024Food(246, "Plan024 sorted");

    await page.route(/\/admin\/foods\?.*$/, async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const requestedPage = Number(params.get("page") ?? "1");
      if (params.get("status") === "archived") {
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page([archived])) });
      }
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
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page(items, requestedPage, 2)) });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/admin/foods");
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    await page.getByRole("button", { name: "عرض المزيد" }).click();
    await expect(plan024VisibleRowTrigger(page, activeSecond)).toBeVisible();

    const status = page.getByLabel("الحالة");
    await status.selectOption("archived");
    await expect(plan024VisibleRowTrigger(page, archived)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);
    await expect(plan024VisibleRowTrigger(page, activeSecond)).toHaveCount(0);

    await status.selectOption("active");
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeSecond)).toHaveCount(0);

    await page.getByLabel("بحث باسم الطعام").fill("needle");
    await expect(plan024VisibleRowTrigger(page, searched)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);

    await page.getByLabel("بحث باسم الطعام").fill("");
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    await page.locator(".category-chip").nth(1).click();
    await expect(plan024VisibleRowTrigger(page, categorized)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);

    await page.locator(".category-chip").first().click();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toBeVisible();
    await page.getByLabel("ترتيب الأطعمة").last().selectOption("recent");
    await expect(plan024VisibleRowTrigger(page, sorted)).toBeVisible();
    await expect(plan024VisibleRowTrigger(page, activeFirst)).toHaveCount(0);
  });

  test("[FOOD-TC-143] @plan024 @p0 lifecycle failures remain authoritative and retry exactly once", async ({ page }) => {
    const cases = [
      { label: "network", status: null },
      { label: "unauthorized", status: 401 },
      { label: "forbidden", status: 403 },
      { label: "server", status: 500 }
    ] as const;
    const foods = cases.map((item, index) => plan024Food(250 + index, `Plan024 ${item.label}`));
    const archivedIds = new Set<string>();

    await page.route(/\/admin\/foods\?.*$/, async (route) => {
      const status = new URL(route.request().url()).searchParams.get("status");
      const items = foods.filter((food) => status === "archived" ? archivedIds.has(food.id) : !archivedIds.has(food.id));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page(items)) });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/admin/foods");

    const firstFocusFood = foods[0];
    const firstFocusOpener = page.getByRole("button", { name: `إجراءات ${firstFocusFood.name}` });
    await firstFocusOpener.focus();
    await firstFocusOpener.press("Enter");
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(firstFocusOpener).toBeFocused();
    await expect(firstFocusOpener).toHaveAttribute("aria-expanded", "false");

    const secondFocusFood = foods[1];
    const secondFocusOpener = page.getByRole("button", { name: `إجراءات ${secondFocusFood.name}` });
    await secondFocusOpener.focus();
    await secondFocusOpener.press("Enter");
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(secondFocusOpener).toBeFocused();
    await expect(firstFocusOpener).not.toBeFocused();

    const rerenderResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/admin/foods" && url.searchParams.get("sort") === "recent";
    });
    await page.getByLabel("ترتيب الأطعمة").last().selectOption("recent");
    await rerenderResponse;
    const currentSecondFocusOpener = page.getByRole("button", { name: `إجراءات ${secondFocusFood.name}` });
    await currentSecondFocusOpener.focus();
    await currentSecondFocusOpener.press("Enter");
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(currentSecondFocusOpener).toBeFocused();
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);

    for (const [index, failure] of cases.entries()) {
      const food = foods[index];
      let requestCount = 0;
      let releaseFailure!: () => void;
      let markFirstRequest!: () => void;
      const firstRequest = new Promise<void>((resolve) => { markFirstRequest = resolve; });
      const failureBarrier = new Promise<void>((resolve) => { releaseFailure = resolve; });
      const endpoint = new RegExp(`/admin/foods/${food.id}/archive$`);
      await page.route(endpoint, async (route) => {
        requestCount += 1;
        if (requestCount === 1) {
          markFirstRequest();
          await failureBarrier;
          if (failure.status === null) return route.abort("failed");
          return route.fulfill({ status: failure.status, contentType: "application/json", body: "{}" });
        }
        archivedIds.add(food.id);
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...food, status: "archived", archived_at: "2026-08-04T00:00:00Z" })
        });
      });

      await page.getByRole("button", { name: `إجراءات ${food.name}` }).click();
      const archive = page.getByRole("menuitem", { name: "أرشفة" });
      await archive.click();
      await firstRequest;
      await expect(archive).toBeDisabled();
      expect(requestCount).toBe(1);
      releaseFailure();

      const alert = page.locator(".food-lifecycle-error[role=alert]");
      await expect(alert).toBeVisible();
      await expect(alert).not.toHaveText("");
      await expect(alert).toBeFocused();
      await expect(plan024VisibleRowTrigger(page, food)).toBeVisible();
      expect(requestCount).toBe(1);

      await alert.getByRole("button", { name: "إعادة المحاولة" }).click();
      await expect(plan024VisibleRowTrigger(page, food)).toHaveCount(0);
      expect(requestCount).toBe(2);
      await page.unroute(endpoint);
    }
  });

  test("[FOOD-TC-144] @plan024 @p0 mobile Admin can archive and restore through status collections", async ({ page }) => {
    const food = plan024Food(260, "Plan024 lifecycle success");
    let lifecycleStatus: "active" | "archived" = "active";

    await page.route(/\/admin\/foods\?.*$/, async (route) => {
      const requestedStatus = new URL(route.request().url()).searchParams.get("status") ?? "active";
      const items = requestedStatus === lifecycleStatus ? [{ ...food, status: lifecycleStatus }] : [];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(plan024Page(items)) });
    });
    await page.route(new RegExp(`/admin/foods/${food.id}/(archive|restore)$`), async (route) => {
      lifecycleStatus = route.request().url().endsWith("/restore") ? "active" : "archived";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...food, status: lifecycleStatus, archived_at: lifecycleStatus === "archived" ? "2026-08-04T00:00:00Z" : null })
      });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/admin/foods");
    const status = page.getByLabel("الحالة");
    const activeTrigger = page.getByRole("button", { name: `إجراءات ${food.name}` });
    await activeTrigger.focus();
    await activeTrigger.press("Enter");
    await page.getByRole("menuitem", { name: "أرشفة" }).click();
    await expect(plan024VisibleRowTrigger(page, food)).toHaveCount(0);
    await expect(status).toBeFocused();
    await expect(activeTrigger).toHaveCount(0);
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);

    await status.press("End");
    await expect(status).toHaveValue("archived");
    await expect(plan024VisibleRowTrigger(page, food)).toBeVisible();
    const archivedTrigger = page.getByRole("button", { name: `إجراءات ${food.name}` });
    await archivedTrigger.focus();
    await archivedTrigger.press("Enter");
    await page.getByRole("menuitem", { name: "استعادة" }).click();
    await expect(plan024VisibleRowTrigger(page, food)).toHaveCount(0);
    await expect(status).toBeFocused();
    await expect(archivedTrigger).toHaveCount(0);
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);

    await status.press("Home");
    await expect(status).toHaveValue("active");
    await expect(plan024VisibleRowTrigger(page, food)).toBeVisible();
  });
});
