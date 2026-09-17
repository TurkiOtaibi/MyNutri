import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { test, expect, expectNoHorizontalOverflow, submitFoodForm, validFood } from "./helpers";

function accessibleFood(idSuffix: number, name: string) {
  return {
    ...validFood({ name, brand: "علامة طويلة Mixed Latin Brand Name" }),
    id: `00000000-0000-4000-8000-${String(idSuffix).padStart(12, "0")}`,
    net_carbs_g: 20,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z"
  };
}

function accessiblePage(items: ReturnType<typeof accessibleFood>[]) {
  return { items, total: items.length, page: 1, page_size: 20, total_pages: 1, categories: ["other"] };
}

async function expectAxePass(page: Page, stateLabel: string) {
  const results = await new AxeBuilder({ page }).include(".foods-catalog").analyze();
  const blocking = results.violations.filter((violation) =>
    ["moderate", "serious", "critical"].includes(violation.impact ?? "")
  );
  expect(blocking, `${stateLabel}: moderate-or-higher axe violations`).toEqual([]);
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

  test("[FOOD-TC-136] @p1 @a11y admin icon actions have contextual names", async ({ page, foodsApi }) => {
    const food = await foodsApi.create({ name: `E2E-Accessible-Actions-${Date.now()}` });
    await page.goto("/foods");
    await expect(page.getByRole("link", { name: `عرض تفاصيل ${food.name}` }).first()).toBeVisible();
    const actions = page.getByRole("button", { name: `إجراءات ${food.name}` });
    await actions.click();
    await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: /(أرشفة|استعادة)/ })).toHaveCount(0);
  });

  test("[FOOD-TC-139] @p1 @mobile required viewport matrix has no horizontal overflow", async ({ page, foodsApi }) => {
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

  test("[FOOD-TC-145] @p0 @mobile @a11y unified admin actions are keyboard and touch safe", async ({ page }) => {
    const food = accessibleFood(271, `طعام عربي طويل ${"اسم ".repeat(12)}Mixed Latin Food`);
    await page.route(/\/foods\?.*$/, (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(accessiblePage([food]))
    }));
    for (const width of [320, 360, 375, 390, 430, 1280]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/foods");
      await expect(page.getByLabel("عرض الأرشيف")).toHaveCount(0);
      const trigger = page.getByRole("button", { name: `إجراءات ${food.name}` });
      const box = await trigger.boundingBox();
      expect(box && box.x >= 0 && box.x + box.width <= width).toBe(true);
      await trigger.focus();
      await trigger.press("Enter");
      await expect(page.getByRole("menuitem", { name: "تعديل" })).toBeFocused();
      await expect(page.getByRole("menuitem", { name: "حذف" })).toBeVisible();
      await expectAxePass(page, `${width} admin actions`);
      await page.keyboard.press("Escape");
      await expect(trigger).toBeFocused();
      await expectNoHorizontalOverflow(page);
    }
  });
});
