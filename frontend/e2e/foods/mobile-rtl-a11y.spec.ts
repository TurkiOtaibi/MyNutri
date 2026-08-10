import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { test, expect, expectNoHorizontalOverflow, fillRequiredFoodForm, submitFoodForm, validFood } from "./helpers";

function plan024AccessibleFood(idSuffix: number, name: string, status: "active" | "archived") {
  return {
    ...validFood({
      name,
      brand: "علامة طويلة Mixed Latin Brand Name"
    }),
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

function plan024AccessiblePage(items: ReturnType<typeof plan024AccessibleFood>[]) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 20,
    total_pages: 1,
    categories: ["other"],
    uncategorized_count: 0
  };
}

async function expectPlan024AxePass(page: Page, stateLabel: string) {
  const results = await new AxeBuilder({ page }).include(".foods-catalog").analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["moderate", "serious", "critical"].includes(violation.impact ?? "")
  );
  expect(blockingViolations, `${stateLabel}: moderate-or-higher axe violations`).toEqual([]);
}

test.describe("Foods mobile, RTL, and accessibility @foods", () => {
  test("[FOOD-TC-135] @p1 @a11y field errors are associated with invalid inputs", async ({ page }) => {
    await page.goto("/foods/new");
    await submitFoodForm(page);
    const name = page.getByLabel(/اسم الطعام/);
    await expect(name).toHaveAttribute("aria-invalid", "true");
    const errorId = await name.getAttribute("aria-describedby");
    expect(errorId).toBeTruthy();
    await expect(page.locator(`#${errorId}`)).toHaveText("هذا الحقل مطلوب.");
    await expect(page.locator(".state-note[role=alert]")).toBeVisible();
  });

  test("[FOOD-TC-136] @p1 @a11y icon actions have contextual accessible names", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Accessible-Actions-${Date.now()}` });
    await page.goto("/admin/foods");
    await expect(page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first()).toBeVisible();
    const actions = page.getByRole("button", { name: `إجراءات ${food.name}` });
    await expect(actions).toBeVisible();
    await actions.click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
  });

  test("[FOOD-TC-139] @p1 @mobile required viewport matrix has no horizontal page overflow", async ({ page, foodsApi }) => {
    await foodsApi.create({ name: `طعام E2E Mixed Long ${"اسم ".repeat(15)}`.slice(0, 120) });
    for (const width of [360, 390, 430, 768, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/foods");
      await expectNoHorizontalOverflow(page);
      expect(await page.locator("html").getAttribute("dir")).toBe("rtl");
      if (width <= 920) await expect(page.locator(".food-card-list")).toBeVisible();
      else await expect(page.locator(".food-table-wrap")).toBeVisible();
    }
  });

  test("[FOOD-TC-145] @plan024 @p0 @mobile @a11y Admin status control is keyboard and touch safe", async ({ page }) => {
    test.setTimeout(120_000);

    const activeFood = plan024AccessibleFood(
      271,
      `طعام عربي طويل ${"اسم ".repeat(12)}Mixed Latin Food`,
      "active"
    );
    const archivedFood = plan024AccessibleFood(272, "طعام مؤرشف Mixed Archive", "archived");
    let responseMode: "normal" | "loading" | "error" | "empty" = "normal";
    let releaseLoading: () => void = () => undefined;
    let loadingGate: Promise<void> | null = null;

    await page.route(/\/admin\/foods\?.*$/, async (route) => {
      const params = new URL(route.request().url()).searchParams;
      if (responseMode === "loading" && loadingGate) await loadingGate;
      if (responseMode === "error") {
        return route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
      }
      if (responseMode === "empty" || params.get("search")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(plan024AccessiblePage([]))
        });
      }
      const food = params.get("status") === "archived" ? archivedFood : activeFood;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(plan024AccessiblePage([food]))
      });
    });

    for (const width of [320, 360, 375, 390, 430, 1280]) {
      await page.setViewportSize({ width, height: 844 });
      responseMode = "normal";
      await page.goto("/admin/foods");
      const status = page.getByLabel("الحالة");
      await expect(status).toBeVisible();
      await expect(status).toHaveCount(1);
      await expect(page.locator(".foods-admin-status-control > span")).toHaveText("الحالة");
      const box = await status.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box && box.x >= 0 && box.x + box.width <= width).toBe(true);

      const activeTrigger = page.getByRole("button", { name: `إجراءات ${activeFood.name}` });
      await expect(activeTrigger).toBeVisible();
      const triggerBox = await activeTrigger.boundingBox();
      expect(triggerBox && triggerBox.x >= 0 && triggerBox.x + triggerBox.width <= width).toBe(true);
      const activeName = width <= 920
        ? page.locator(".food-card-title", { hasText: activeFood.name })
        : page.locator(".food-table-name", { hasText: activeFood.name });
      await expect(activeName).toBeVisible();
      await expect(activeName).toHaveAttribute("dir", "auto");
      const activeBrand = width <= 920
        ? page.locator(".food-card-secondary", { hasText: activeFood.brand! })
        : page.locator(".food-table-brand", { hasText: activeFood.brand! });
      await expect(activeBrand).toBeVisible();

      if (width === 320) {
        await status.focus();
        await status.press("End");
        await expect(status).toHaveValue("archived");
        await status.press("Home");
        await expect(status).toHaveValue("active");
      } else {
        await status.click();
        await expect(status).toBeFocused();
        await status.selectOption("archived");
        await expect(status).toHaveValue("archived");
        await status.selectOption("active");
        await expect(status).toHaveValue("active");
      }

      await expectNoHorizontalOverflow(page);
    }

    await page.setViewportSize({ width: 375, height: 844 });
    responseMode = "normal";
    await page.goto("/admin/foods");
    const status = page.getByLabel("الحالة");
    await expect(status).toHaveValue("active");
    await expect(page.locator(".food-card-title", { hasText: activeFood.name })).toBeVisible();
    await expectPlan024AxePass(page, "375 active menu closed");

    await page.getByRole("button", { name: `إجراءات ${activeFood.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "أرشفة" })).toBeVisible();
    await expectPlan024AxePass(page, "375 active menu open");
    await page.keyboard.press("Escape");

    await status.selectOption("archived");
    await expect(status.locator("option:checked")).toHaveText("مؤرشف");
    await expect(page.locator(".food-card-title", { hasText: archivedFood.name })).toBeVisible();
    await expectPlan024AxePass(page, "375 archived menu closed");
    await page.getByRole("button", { name: `إجراءات ${archivedFood.name}` }).click();
    await expect(page.getByRole("menuitem", { name: "استعادة" })).toBeVisible();
    await expectPlan024AxePass(page, "375 archived menu open");
    await page.keyboard.press("Escape");

    loadingGate = new Promise<void>((resolve) => { releaseLoading = resolve; });
    responseMode = "loading";
    await page.reload();
    await expect(page.locator(".foods-loading")).toBeVisible();
    await expect(page.locator(".foods-loading")).toHaveAttribute("role", "status");
    await expect(page.getByRole("button", { name: /إجراءات/ })).toHaveCount(0);
    await expect(page.getByLabel("الحالة")).toBeVisible();
    await expectPlan024AxePass(page, "375 loading");
    responseMode = "normal";
    releaseLoading();
    await expect(page.locator(".food-card-title", { hasText: activeFood.name })).toBeVisible();

    responseMode = "error";
    await page.reload();
    const requestError = page.locator(".catalog-state[role=alert]");
    await expect(requestError).toContainText("تعذر تحميل الأطعمة");
    await expect(requestError.getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
    await expect(page.getByRole("button", { name: /إجراءات/ })).toHaveCount(0);
    await expectPlan024AxePass(page, "375 request error");

    responseMode = "empty";
    await page.reload();
    await expect(page.getByText("لا توجد أطعمة بعد.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /إجراءات/ })).toHaveCount(0);
    await expectPlan024AxePass(page, "375 empty catalog");

    responseMode = "normal";
    await page.reload();
    await expect(page.locator(".food-card-title", { hasText: activeFood.name })).toBeVisible();
    await page.getByLabel("بحث باسم الطعام").fill("لا-تطابق");
    await expect(page.getByText("لا توجد نتائج مطابقة للبحث.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /إجراءات/ })).toHaveCount(0);
    await expectPlan024AxePass(page, "375 search no results");

    for (const width of [320, 430]) {
      await page.setViewportSize({ width, height: 844 });
      responseMode = "normal";
      await page.goto("/admin/foods");
      await page.getByRole("button", { name: `إجراءات ${activeFood.name}` }).click();
      await expect(page.getByRole("menuitem", { name: "أرشفة" })).toBeVisible();
      await expectPlan024AxePass(page, `${width} active menu open`);
      await page.keyboard.press("Escape");
      await page.getByLabel("الحالة").selectOption("archived");
      await page.getByRole("button", { name: `إجراءات ${archivedFood.name}` }).click();
      await expect(page.getByRole("menuitem", { name: "استعادة" })).toBeVisible();
      await expectPlan024AxePass(page, `${width} archived menu open`);
      await page.keyboard.press("Escape");
      await expectNoHorizontalOverflow(page);
    }
  });
});
