import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const API_ORIGIN = new URL(API_URL).origin;

test.describe("@plan033 closed and inactive boundary", () => {
  test("the active Progress surface neither requests nor renders PLAN 033 V1", async ({ page }) => {
    const plan033Requests: string[] = [];
    await page.route(
      (url) =>
        url.origin === API_ORIGIN &&
        (url.pathname.startsWith("/progress/weekly-priorities") ||
          url.pathname.startsWith("/progress/behavior-goals")),
      async (route) => {
        plan033Requests.push(route.request().url());
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          json: {
            error: {
              code: "FEATURE_DISABLED",
              message_ar: "الميزة غير مفعلة.",
              details: {},
              request_id: "plan033-off",
            },
          },
        });
      },
    );
    await page.route(
      (url) =>
        url.origin === API_ORIGIN &&
        url.pathname === "/progress/nutrition-analysis/v2/current",
      (route) =>
        route.fulfill({
          status: 404,
          contentType: "application/json",
          json: {
            error: {
              code: "NOVA_RETIREMENT_V2_ANALYSIS_NOT_FOUND",
              message_ar: "لا يوجد تحليل محفوظ بعد.",
              details: {},
              request_id: "analysis-empty",
            },
          },
        }),
    );
    await page.route(
      (url) =>
        url.origin === API_ORIGIN &&
        url.pathname === "/progress/nutrition-analysis/v2/history",
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          json: { items: [], next_cursor: null },
        }),
    );

    await page.goto("/progress");

    await expect(page.getByRole("heading", { name: "تحليل نمط التغذية" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /زيادة الفواكه|تقليل الصوديوم|الهدف الأسبوعي/ }),
    ).toHaveCount(0);
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    expect(plan033Requests).toEqual([]);

    const accessibility = await new AxeBuilder({ page })
      .include('main [dir="rtl"]')
      .analyze();
    expect(accessibility.violations).toEqual([]);
  });
});
