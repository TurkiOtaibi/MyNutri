import { expect, test } from "./foods/helpers";

function luminance(rgb: string) {
  const [r, g, b] = (rgb.match(/\d+(\.\d+)?/g) ?? []).slice(0, 3).map(Number);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

async function shellColors(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const body = getComputedStyle(document.body);
    return { scheme: getComputedStyle(document.documentElement).colorScheme, background: body.backgroundColor, color: body.color };
  });
}

test.describe("@issue155 dark device setting", () => {
  test.use({ colorScheme: "dark" });
  test("@p1 switches the shell to dark tokens with readable text", async ({ page }) => {
    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: "ملخص اليوم" })).toBeVisible();
    const colors = await shellColors(page);
    expect(colors.scheme).toBe("dark");
    expect(luminance(colors.background)).toBeLessThan(0.15);
    expect(luminance(colors.color)).toBeGreaterThan(0.8);
  });
});

test.describe("@issue155 light device setting", () => {
  test.use({ colorScheme: "light" });
  test("@p1 keeps the approved light palette", async ({ page }) => {
    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: "ملخص اليوم" })).toBeVisible();
    const colors = await shellColors(page);
    expect(colors.scheme).toBe("light");
    expect(colors.background).toBe("rgb(246, 247, 245)");
    expect(colors.color).toBe("rgb(28, 35, 33)");
  });
});
