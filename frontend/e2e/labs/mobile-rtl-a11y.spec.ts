import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, navigateToOwnerLabs, offsetIsoDate, test } from "./helpers";

async function assertMobileSurface(page: Page) {
  const layout = await page.evaluate(() => {
    const root = document.documentElement;
    const visibleTargets = [...document.querySelectorAll<HTMLElement>("button, a, input, select")]
      .filter((element) => element.offsetParent !== null)
      .map((element) => {
        const label = element.matches('input[type="checkbox"], input[type="radio"]') ? element.closest("label") : null;
        const box = (label ?? element).getBoundingClientRect();
        return { width: box.width, height: box.height, left: box.left, right: box.right };
      });
    return {
      dir: root.dir,
      overflow: root.scrollWidth - root.clientWidth,
      viewport: innerWidth,
      visibleTargets,
    };
  });
  expect(layout.dir).toBe("rtl");
  expect(layout.overflow).toBeLessThanOrEqual(1);
  expect(layout.visibleTargets.every(({ left, right }) => left >= -1 && right <= layout.viewport + 1)).toBe(true);
  expect(layout.visibleTargets.every(({ width, height }) => width >= 44 && height >= 44)).toBe(true);
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations.filter((violation) =>
    ["moderate", "serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
}

test("Labs overview is responsive and exposes a complete RTL roving-tab pattern", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "hba1c", entered_value: "5.27", entered_unit: "%" }]);
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 760 });
    await navigateToOwnerLabs(page);
    const owned = page.getByRole("tab", { name: "تحاليلك", exact: true });
    const all = page.getByRole("tab", { name: "كل التحاليل", exact: true });
    await expect(owned).toHaveAttribute("aria-controls", "labs-panel-owned");
    await expect(owned).toHaveAttribute("tabindex", "0");
    await owned.focus();
    await page.keyboard.press("ArrowLeft");
    await expect(all).toBeFocused();
    await expect(all).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#labs-panel-all")).toBeVisible();
    await page.keyboard.press("Home");
    await expect(owned).toBeFocused();
    await page.keyboard.press("End");
    await expect(all).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(owned).toBeFocused();
    await expect(page.locator("#labs-panel-owned")).toHaveAttribute("aria-labelledby", "labs-tab-owned");
    const row = page.locator('[data-testid="lab-row"][data-test-key="hba1c"]');
    await expect(row.locator("bdi, [dir='ltr']")).not.toHaveCount(0);
    const status = row.locator("[data-tone]");
    await expect(status).not.toHaveText("");
    expect(await status.evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe("rgba(0, 0, 0, 0)");
    await assertMobileSurface(page);
  }
});

test("the CBC value step names all twenty groups and wraps focus at the modal boundary", async ({ labsPage: page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 320, height: 760 });
  await navigateToOwnerLabs(page);
  const opener = page.getByRole("button", { name: "إضافة نتائج", exact: true });
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "إضافة نتائج" });
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator('[data-panel-key="cbc"]').check();
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  const rows = dialog.getByTestId("lab-batch-row");
  await expect(rows).toHaveCount(20);
  for (const row of await rows.all()) {
    await expect(row).toHaveRole("group");
    await expect(row).toHaveAccessibleName(/.+/);
    await expect(row.getByRole("textbox", { name: "القيمة" })).toHaveCount(1);
    await expect(row.getByRole("combobox", { name: "الوحدة" })).toHaveCount(1);
  }
  const first = rows.first().getByRole("textbox", { name: "القيمة" });
  const last = dialog.getByRole("button", { name: "حفظ النتائج", exact: true });
  await last.focus();
  await page.keyboard.press("Tab");
  await expect(first).toBeFocused();
  await first.focus();
  await page.keyboard.press("Shift+Tab");
  await expect(last).toBeFocused();
  expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
  await assertMobileSurface(page);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("extreme converted history remains readable and chart points support keyboard navigation", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  for (let offset = 20; offset >= 1; offset -= 1) {
    await labsApi.create(offsetIsoDate(today, -offset), [{
      test_key: "hba1c",
      entered_value: offset === 20 ? "9".repeat(128) : `${30 + offset}.000`,
      entered_unit: "mmol/mol",
    }]);
  }
  await page.setViewportSize({ width: 320, height: 760 });
  await page.goto("/labs/hba1c");
  const points = page.locator("[data-chart-point]");
  await expect(points).toHaveCount(20);
  await expect(page.locator("[data-history-result]")).toHaveCount(20);
  await expect(page.getByRole("heading", { name: "السجل الكامل" })).toBeVisible();
  await expect(page.getByRole("region", { name: "القيم المرجعية للنظام" })).toBeVisible();
  await points.locator('[tabindex="0"]').focus();
  await page.keyboard.press("Home");
  await expect(points.first()).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(points.nth(1)).toBeFocused();
  await page.keyboard.press("End");
  await expect(points.last()).toBeFocused();
  await expect(page.locator("bdi").filter({ hasText: /mmol\/mol|%/ }).first()).toBeVisible();
  expect(await page.locator("[data-history-result] span").evaluateAll((spans) =>
    spans.some((span) => (span.textContent?.trim().length ?? 0) >= 100))).toBe(true);
  await assertMobileSurface(page);
});

test("selected-user admin Labs stays read-only and mobile safe", async ({ page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "hba1c", entered_value: "5.27", entered_unit: "%" }]);
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 760 });
    await page.goto(`/admin/users/${labsApi.actor.principalId}/labs`);
    await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
    await page.getByRole("link", { name: /السكر التراكمي/ }).click();
    await expect(page.getByTestId("lab-detail")).toContainText("للقراءة فقط");
    await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
    await assertMobileSurface(page);
  }
});
