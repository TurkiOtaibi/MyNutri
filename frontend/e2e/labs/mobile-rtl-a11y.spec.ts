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
        return { width: box.width, height: box.height, left: box.left, right: box.right,
          control: element.tagName.toLowerCase(), label: element.getAttribute("aria-label") ?? element.textContent?.trim().slice(0, 50) ?? "" };
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
  expect(layout.visibleTargets.filter(({ width, height }) => width < 44 || height < 44)).toEqual([]);
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations.filter((violation) =>
    ["moderate", "serious", "critical"].includes(violation.impact ?? ""))).toEqual([]);
}

test("Labs overview is responsive and exposes a complete RTL roving-tab pattern", async ({ labsPage: page, labsApi }, testInfo) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "hba1c", entered_value: "5.27", entered_unit: "%" }]);
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "ferritin", entered_value: "9".repeat(128), entered_unit: "ng/mL" }]);
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
    if (width === 320) await testInfo.attach("labs-owner-overview-320", {
      body: await page.screenshot({ fullPage: true }), contentType: "image/png",
    });
  }
  for (const width of [375, 1440]) {
    for (const colorScheme of ["light", "dark"] as const) {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme });
      const row = page.locator('[data-testid="lab-row"][data-test-key="hba1c"]');
      const result = row.locator("strong:has(> bdi)");
      await expect(result).toHaveText("5.27 %");
      await expect(result.locator("small")).toHaveText("%");
      const valueSize = await result.evaluate((element) => parseFloat(getComputedStyle(element).fontSize));
      const unitSize = await result.locator("small").evaluate((element) => parseFloat(getComputedStyle(element).fontSize));
      expect(valueSize).toBeGreaterThan(unitSize);
      const link = row.getByRole("link");
      expect((await link.boundingBox())!.y).toBeLessThan((await result.boundingBox())!.y);
      expect(await row.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
      await expect(row.locator("time")).toHaveAttribute("datetime", offsetIsoDate(today, -1));
      const longRow = page.locator('[data-testid="lab-row"][data-test-key="ferritin"]');
      const longValue = longRow.locator("strong:has(> bdi)");
      expect(await longValue.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
      if (width === 1440) {
        const firstBox = (await row.boundingBox())!;
        const secondBox = (await longRow.boundingBox())!;
        expect(Math.abs(firstBox.y - secondBox.y)).toBeLessThan(2);
        expect(Math.abs(firstBox.x - secondBox.x)).toBeGreaterThan(firstBox.width);
      }
    }
  }
  const detailLink = page.locator('[data-testid="lab-row"][data-test-key="hba1c"]').getByRole("link");
  await detailLink.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/labs\/hba1c$/);
  await expect(page.getByRole("region", { name: "القيم المرجعية للنظام" })).toBeVisible();
});

test("the CBC value step names all twenty groups and wraps focus at the modal boundary", async ({ labsPage: page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [320, 375, 390, 430, 1440]) {
    await page.setViewportSize({ width, height: 760 });
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
    const summary = dialog.getByTestId("lab-values-summary");
    await expect(last).toBeDisabled();
    await expect(first).toHaveAttribute("aria-describedby", "lab-values-hint");
    await expect(dialog.locator("#lab-values-hint")).toContainText("تُحفظ القيم المدخلة فقط.");
    await first.fill("1");
    await expect(last).toBeEnabled();
    await expect(summary).toContainText("سيتم حفظ نتيجة واحدة");
    for (const colorScheme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme });
      const finalValue = rows.last().getByRole("textbox", { name: "القيمة" });
      await first.focus();
      await finalValue.focus();
      await expect(finalValue).toBeInViewport();
      await expect(last).toBeInViewport();
      await expect(summary).toBeInViewport();
      const valueBox = (await finalValue.boundingBox())!;
      expect(valueBox.y + valueBox.height).toBeLessThan((await summary.boundingBox())!.y);
      await expect(finalValue).toHaveAttribute("dir", "ltr");
      await expect(rows.last().getByRole("combobox", { name: "الوحدة" })).toHaveAttribute("dir", "ltr");
      expect(await rows.evaluateAll((elements) => elements.every(element => element.scrollWidth <= element.clientWidth))).toBe(true);
    }
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
  }
});

test("extreme converted history remains readable and chart points support keyboard navigation", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  for (let offset = 20; offset >= 1; offset -= 1) {
    await labsApi.create(offsetIsoDate(today, -offset), [{
      test_key: "hba1c",
      entered_value: offset === 20 ? "9".repeat(128) : `${30 + offset}.000`,
      entered_unit: offset === 1 ? "%" : "mmol/mol",
    }]);
  }
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 760 });
    await page.goto("/labs/hba1c");
    const points = page.locator("[data-chart-point]");
    await expect(points).toHaveCount(20);
    await expect(page.locator("[data-history-result]")).toHaveCount(20);
    await expect(page.getByRole("heading", { name: "السجل الكامل" })).toBeVisible();
    await expect(page.getByRole("region", { name: "القيم المرجعية للنظام" })).toBeVisible();
    await page.locator('[data-chart-point][tabindex="0"]').focus();
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
  }
  const detail = await labsApi.detail("hba1c");
  const figure = page.getByRole("figure", { name: "سجل النتائج عبر الزمن" });
  const older = figure.getByRole("button", { name: "الأقدم", exact: true });
  const newer = figure.getByRole("button", { name: "الأحدث", exact: true });
  const reading = figure.getByTestId("chart-selected-reading");
  for (const width of [375, 1440]) {
    for (const colorScheme of ["light", "dark"] as const) {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme });
      await page.locator('[data-chart-point][tabindex="0"]').focus();
      await page.keyboard.press("End");
      await expect(newer).toBeDisabled();
      await older.click();
      await expect(reading.locator("time")).toHaveAttribute("datetime", detail.results[1].test_date);
      await expect(reading.locator("strong")).toContainText(detail.results[1].display_value);
      const original = reading.getByText("القيمة المُدخلة:", { exact: false });
      await expect(original.locator("bdi")).toHaveText(`${detail.results[1].entered_value} ${detail.results[1].entered_unit}`);
      await expect(original.locator("bdi")).toHaveAttribute("dir", "ltr");
      const summary = page.getByRole("region", { name: "القيم المرجعية للنظام" }).getByRole("status");
      await expect(summary).toContainText(`${detail.results[1].entered_value} ${detail.results[1].entered_unit}`);
      await expect(page.locator(`[data-chart-point="${detail.results[1].id}"]`)).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByRole("region", { name: "القيم المرجعية للنظام" })).toHaveAttribute("data-reference-date", detail.results[1].test_date);
      await newer.focus();
      await page.keyboard.press("Enter");
      await expect(reading.locator("time")).toHaveAttribute("datetime", detail.results[0].test_date);
      await expect(original).toHaveCount(0);
      await expect(summary).not.toContainText("القيمة المُدخلة");
      expect((await older.boundingBox())!.x).toBeLessThan((await newer.boundingBox())!.x);
      await page.locator('[data-chart-point][tabindex="0"]').focus();
      await page.keyboard.press("Home");
      await expect(older).toBeDisabled();
      await expect(reading.locator("strong")).toContainText(detail.results.at(-1)!.display_value);
      expect(await reading.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await newer.click();
      await expect(reading.locator("time")).toHaveAttribute("datetime", detail.results.at(-2)!.test_date);
    }
  }
});

test("selected-user admin Labs stays read-only and mobile safe", async ({ page, labsApi }, testInfo) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "hba1c", entered_value: "35.270", entered_unit: "mmol/mol" }]);
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 760 });
    await page.goto(`/admin/users/${labsApi.actor.principalId}/labs`);
    await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
    await assertMobileSurface(page);
    if (width === 320) await testInfo.attach("labs-admin-overview-navigation-320", {
      body: await page.screenshot({ fullPage: true }), contentType: "image/png",
    });
    await page.getByRole("link", { name: /السكر التراكمي/ }).click();
    await expect(page.getByTestId("lab-detail")).toContainText("للقراءة فقط");
    await expect(page.getByRole("region", { name: "القيم المرجعية للنظام" }).getByRole("status")).toContainText("35.270 mmol/mol");
    await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
    await assertMobileSurface(page);
  }
});
