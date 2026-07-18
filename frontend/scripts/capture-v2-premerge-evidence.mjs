import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const output = path.resolve("..", "docs", "implementation", "v2", "evidence", "premerge");
const widths = [320, 390, 430];
await mkdir(output, { recursive: true });

async function login(page, email, password) {
  await page.goto(`${baseURL}/auth/login`);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/diary$/);
}

async function capture(page, name, width) {
  await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: false });
}

const browser = await chromium.launch();
try {
  for (const width of widths) {
    const publicContext = await browser.newContext({ viewport: { width, height: 844 }, locale: "ar-SA", timezoneId: "Asia/Riyadh" });
    const publicPage = await publicContext.newPage();
    for (const [name, route] of [
      ["auth-login", "/auth/login"],
      ["auth-sign-up", "/auth/sign-up"],
      ["auth-forgot-password", "/auth/forgot-password"],
      ["auth-reset-password", "/auth/reset-password"]
    ]) {
      await publicPage.goto(`${baseURL}${route}`);
      await publicPage.locator("main, form").first().waitFor({ state: "visible" });
      await capture(publicPage, name, width);
    }
    await publicContext.close();

    const userContext = await browser.newContext({ viewport: { width, height: 844 }, locale: "ar-SA", timezoneId: "Asia/Riyadh" });
    const userPage = await userContext.newPage();
    await login(userPage, "visual-user@example.test", "Acceptance-only-password-2026!");
    await userPage.goto(`${baseURL}/foods`);
    await userPage.getByRole("heading", { name: "الأطعمة" }).waitFor();
    await capture(userPage, "user-food-catalog", width);
    await userContext.close();

    const adminContext = await browser.newContext({ viewport: { width, height: 844 }, locale: "ar-SA", timezoneId: "Asia/Riyadh" });
    const adminPage = await adminContext.newPage();
    await login(adminPage, "admin.e2e@example.test", "E2e-only-password-2026!");
    await adminPage.goto(`${baseURL}/admin/users`);
    await adminPage.locator(".admin-user-row").first().waitFor();
    await adminPage.evaluate(() => scrollTo(0, 0));
    await capture(adminPage, "admin-users", width);
    const detailHref = await adminPage.locator(".admin-user-row").first().getAttribute("href");
    await adminPage.goto(`${baseURL}${detailHref}`);
    await adminPage.locator(".selected-user-banner").waitFor();
    await adminPage.evaluate(() => scrollTo(0, 0));
    await capture(adminPage, "admin-user-detail", width);
    await adminPage.goto(`${baseURL}/admin/foods`);
    await adminPage.getByRole("heading", { name: "الأطعمة" }).waitFor();
    await adminPage.evaluate(() => scrollTo(0, 0));
    await capture(adminPage, "admin-food-management", width);

    await adminPage.goto(`${baseURL}/foods/new`);
    const category = adminPage.getByLabel(/فئة الطعام/);
    await category.waitFor();
    await category.selectOption("baked_goods");
    await adminPage.getByLabel(/نوع المخبوزات/).waitFor();
    await capture(adminPage, "baked-goods-fields", width);

    const advanced = adminPage.locator("details.advanced-analysis");
    await advanced.scrollIntoViewIfNeeded();
    await advanced.locator("summary").click();
    await advanced.scrollIntoViewIfNeeded();
    await capture(adminPage, "advanced-nutrition-analysis", width);

    const sticky = adminPage.locator(".form-actions-sticky");
    await adminPage.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
    const geometry = await adminPage.evaluate(() => {
      const bar = document.querySelector(".form-actions-sticky")?.getBoundingClientRect();
      const content = document.querySelector("details.advanced-analysis")?.getBoundingClientRect();
      const controls = [...document.querySelectorAll(".form-actions-sticky .btn")].map((element) => ({
        clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth
      }));
      return {
        horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        barTop: bar?.top ?? -1,
        barBottom: bar?.bottom ?? -1,
        contentBottom: content?.bottom ?? -1,
        viewportHeight: innerHeight,
        controls
      };
    });
    if (
      geometry.horizontalOverflow > 1 || geometry.barTop < 0 ||
      geometry.barBottom > geometry.viewportHeight + 1 || geometry.contentBottom > geometry.barTop ||
      geometry.controls.some((control) => control.scrollWidth > control.clientWidth)
    ) {
      throw new Error(`Unsafe sticky layout at ${width}px: ${JSON.stringify(geometry)}`);
    }
    await capture(adminPage, "sticky-save-safe-area", width);
    await adminContext.close();
  }
} finally {
  await browser.close();
}

console.log(`Captured ${widths.length * 11} visual states in ${output}`);
