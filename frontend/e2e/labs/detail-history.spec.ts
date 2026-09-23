import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import type { LabTestDetailResponse } from "../../lib/types";
import { API_URL, expect, navigateToOwnerLabs, offsetIsoDate, test, waitForLabsGet } from "./helpers";

const API_ORIGIN = new URL(API_URL).origin;

test.use({ labsHasTouch: true });

test.afterEach(async ({ labsApi }) => {
  // Include UI-created results; this API is scoped to this test's synthetic owner.
  for (const item of (await labsApi.overview()).items) {
    for (const result of (await labsApi.detail(item.test_key)).results) await labsApi.remove(result.id);
  }
});

async function openDetail(page: Page, key: string) {
  const read = waitForLabsGet(page, `/labs/tests/${key}`);
  await page.goto(`/labs/${key}`);
  expect((await read).status()).toBe(200);
  await expect(page.getByTestId("lab-detail")).toBeVisible();
}

async function ownerInvalidations(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const inspect = (window as Window & {
      __mynutriE2EQueryInvalidations?: () => string[];
    }).__mynutriE2EQueryInvalidations;
    if (!inspect) throw new Error("E2E query invalidation inspection hook is unavailable.");
    return inspect().filter((serialized) => {
      const key = JSON.parse(serialized) as unknown;
      return Array.isArray(key) && key.length === 3 && key[0] === "labs" && key[2] === "owner";
    });
  });
}

async function cachedOwnerQueries(page: Page): Promise<unknown[][]> {
  return page.evaluate(() => {
    const inspect = (window as Window & {
      __mynutriE2EQueryKeys?: () => string[];
    }).__mynutriE2EQueryKeys;
    if (!inspect) throw new Error("E2E query inspection hook is unavailable.");
    return inspect().map((serialized) => JSON.parse(serialized) as unknown[])
      .filter((key) => key[0] === "labs" && key[2] === "owner");
  });
}

async function expectFullDetail(page: Page, detail: LabTestDetailResponse) {
  await expect(page.getByRole("heading", { name: detail.test.name_ar, exact: true })).toHaveCount(1);
  await expect(page.locator("[data-chart-point]")).toHaveCount(detail.results.length);
  await expect(page.locator("[data-history-result]")).toHaveCount(detail.results.length);
  for (const result of detail.results) {
    const row = page.locator(`[data-history-result="${result.id}"]`);
    await expect(row).toContainText(result.display_value);
    await expect(row).toContainText(result.display_unit);
    await expect(row).toContainText(result.status.label_ar);
    await expect(row).toContainText(result.test_date);
  }
  await expect(page.getByRole("figure", { name: "سجل النتائج عبر الزمن" })).toBeVisible();
  await expect(page.getByRole("group", { name: "نقاط النتائج ونطاقات القيم المرجعية" })).toHaveCount(detail.results.length ? 1 : 0);
  // Only chart, reference and full-history sections; no duplicate latest-result card.
  await expect(page.getByTestId("lab-detail").locator(":scope > section")).toHaveCount(2);
  await expect(page.getByTestId("lab-detail").locator(":scope > figure")).toHaveCount(1);
}

async function expectReferences(page: Page, result: LabTestDetailResponse["results"][number]) {
  const panel = page.locator(`[data-reference-date="${result.test_date}"]`);
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("status")).toContainText(result.display_value);
  await expect(panel.getByRole("status")).toContainText(result.status.label_ar);
  await expect(panel.locator("[data-reference-zone]")).toHaveCount(result.reference_zones.length);
  for (const zone of result.reference_zones) {
    const legend = panel.locator(`[data-reference-zone="${zone.status.code}"]`);
    await expect(legend).toContainText(zone.status.label_ar);
    await expect(legend).toContainText(zone.low === null ? "بلا حد أدنى" : `${zone.low_inclusive ? "≥" : ">"} ${zone.low}`);
    await expect(legend).toContainText(zone.high === null ? "بلا حد أعلى" : `${zone.high_inclusive ? "≤" : "<"} ${zone.high}`);
  }
}

const transitions = [
  { key: "ferritin", sex: "female", birth_date: "1970-01-01", unit: "ng/mL", value: "8" },
  { key: "calcium_total", sex: "male", birth_date: "1961-01-01", unit: "mg/dL", value: "8.7" },
  { key: "alp", sex: "male", birth_date: "2002-01-01", unit: "U/L", value: "45" },
  { key: "tsh", sex: "male", birth_date: "2001-01-01", unit: "mIU/L", value: "0.4" },
  { key: "free_t4", sex: "male", birth_date: "2001-01-01", unit: "ng/dL", value: "0.95" },
  { key: "free_t3", sex: "male", birth_date: "2002-01-01", unit: "pg/mL", value: "2.5" },
] as const;

for (const scenario of transitions) test.describe(`historical ${scenario.key}`, () => {
  test.use({ initialLabsProfile: { sex: scenario.sex, birth_date: scenario.birth_date } });
  test("draws the API birthday transition and selects exact historical reference/status", async ({ labsPage: page, labsApi }) => {
    for (const date of ["2020-12-30", "2020-12-31", "2021-01-01"]) await labsApi.create(date, [{ test_key: scenario.key, entered_value: scenario.value, entered_unit: scenario.unit }]);
    const detail = await labsApi.detail(scenario.key);
    expect(detail.chart_zones).toHaveLength(2);
    expect(detail.chart_zones[0].to_date_exclusive).toBe("2021-01-01");
    expect(detail.chart_zones[1].from_date).toBe("2021-01-01");
    expect(detail.results[0].reference_zones).not.toEqual(detail.results[2].reference_zones);
    expect(detail.results[0].status.code).not.toBe(detail.results[2].status.code);
    await openDetail(page, scenario.key);
    await expectFullDetail(page, detail);
    await expect(page.locator("[data-chart-band]")).toHaveCount(detail.chart_zones.reduce((count, segment) => count + segment.zones.length, 0));
    for (const band of await page.locator("[data-chart-band]").all()) {
      expect(await band.evaluate(element => element.getBoundingClientRect().width)).toBeGreaterThan(0);
    }
    await expectReferences(page, detail.results[0]);
    await page.locator(`[data-chart-point="${detail.results[0].id}"]`).focus();
    await page.keyboard.press("Home");
    await expect(page.locator(`[data-chart-point="${detail.results[2].id}"]`)).toBeFocused();
    await expectReferences(page, detail.results[2]);
    await page.keyboard.press("ArrowRight");
    await expectReferences(page, detail.results[1]);
    await page.keyboard.press("ArrowLeft");
    await expectReferences(page, detail.results[2]);
    await page.keyboard.press("End");
    await expectReferences(page, detail.results[0]);
    await expect(page.locator('[data-chart-point][tabindex="0"]')).toHaveCount(1);
  });
});

for (const key of ["hba1c", "total_cholesterol", "ldl_c", "hdl_c", "triglycerides", "vitamin_d_25oh", "vitamin_b12"]) {
  test(`${key} exposes every API decision legend and inclusivity in one-point state`, async ({ labsPage: page, labsApi }) => {
    const empty = await labsApi.detail(key);
    await labsApi.create(empty.server_today, [{ test_key: key, entered_value: "5", entered_unit: empty.test.canonical_unit }]);
    const detail = await labsApi.detail(key);
    await openDetail(page, key);
    await expectFullDetail(page, detail);
    await expectReferences(page, detail.results[0]);
    await expect(page.locator("polyline")).toHaveCount(0);
    await expect(page.getByText("يفترض هذا التحليل الصيام.", { exact: true })).toHaveCount(detail.test.fasting_assumption === "fasting" ? 1 : 0);
  });
}

test("mixed entered units show complete canonical history with keyboard, touch, axe and no mobile overflow", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  for (let index = 0; index < 12; index += 1) await labsApi.create(offsetIsoDate(today, -index), [{ test_key: "hba1c", entered_value: index % 2 ? "42" : "5.20", entered_unit: index % 2 ? "mmol/mol" : "%" }]);
  const detail = await labsApi.detail("hba1c");
  await page.setViewportSize({ width: 375, height: 812 });
  await navigateToOwnerLabs(page);
  const read = waitForLabsGet(page, "/labs/tests/hba1c");
  await page.locator('[data-test-key="hba1c"]').getByRole("link").click();
  expect((await read).status()).toBe(200);
  await expectFullDetail(page, detail);
  await expect(page.getByTestId("lab-detail")).not.toContainText("mmol/mol");
  await page.locator(`[data-chart-point="${detail.results[0].id}"]`).focus();
  await page.keyboard.press("Home");
  await expectReferences(page, detail.results.at(-1)!);
  await page.locator(`[data-chart-point="${detail.results[0].id}"]`).tap();
  await expectReferences(page, detail.results[0]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect((await new AxeBuilder({ page }).include('[data-testid="lab-detail"]').analyze()).violations).toEqual([]);
});

test("very large exact values remain readable and all points survive", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  await labsApi.create(today, [{ test_key: "hba1c", entered_value: "9".repeat(128), entered_unit: "%" }]);
  await labsApi.create(offsetIsoDate(today, -1), [{ test_key: "hba1c", entered_value: "5.2", entered_unit: "%" }]);
  const detail = await labsApi.detail("hba1c");
  await page.setViewportSize({ width: 320, height: 740 });
  await openDetail(page, "hba1c");
  await expectFullDetail(page, detail);
  await expectReferences(page, detail.results[0]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  for (const element of await page.locator("[data-chart-point]").all()) {
    const box = await element.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
  }
});

test("empty detail uses today's server reference and preselects shared add wizard", async ({ labsPage: page, labsApi }) => {
  const empty = await labsApi.detail("hba1c");
  await openDetail(page, "hba1c");
  await expect(page.locator(`[data-reference-date="${empty.reference_at_date}"]`)).toBeVisible();
  await expect(page.getByText("لا توجد نتائج مسجلة لهذا التحليل.")).toBeVisible();
  const opener = page.getByRole("button", { name: "إضافة نتيجة", exact: true });
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "إضافة نتائج" });
  await expect(page.locator("#lab-batch-date")).toHaveValue(empty.server_today);
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await expect(page.locator('[data-individual-key="hba1c"]')).toBeChecked();
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
  await opener.click();
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await dialog.getByRole("button", { name: "التالي", exact: true }).click();
  await page.locator("#lab-hba1c-value").fill("5.2");
  const refresh = waitForLabsGet(page, "/labs/tests/hba1c");
  await dialog.getByRole("button", { name: "حفظ النتائج", exact: true }).click();
  expect((await refresh).status()).toBe(200);
  await expect(dialog).toHaveCount(0);
  await expectFullDetail(page, await labsApi.detail("hba1c"));
  await expect(page.getByText("تم حفظ النتائج.", { exact: true })).toBeVisible();
});

test("focus refetch removes deleted selected point and defaults to new latest", async ({ labsPage: page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  for (const date of [today, offsetIsoDate(today, -1)]) await labsApi.create(date, [{ test_key: "hba1c", entered_value: "5.2", entered_unit: "%" }]);
  const detail = await labsApi.detail("hba1c");
  await openDetail(page, "hba1c");
  await labsApi.remove(detail.results[0].id);
  const refresh = waitForLabsGet(page, "/labs/tests/hba1c");
  await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
  expect((await refresh).status()).toBe(200);
  await expect(page.locator("[data-chart-point]")).toHaveCount(1);
  await expectReferences(page, detail.results[1]);
  // A remount must read the current server response even within the cache lifetime.
  await page.goto("/labs");
  await labsApi.patch(detail.results[1].id, { test_date: detail.results[1].test_date, entered_unit: "%", entered_value: "6.7", expected_updated_at: detail.results[1].updated_at });
  await openDetail(page, "hba1c");
  await expectReferences(page, (await labsApi.detail("hba1c")).results[0]);
});

test.describe("accepted Profile DOB freshness", () => {
  test.use({ initialLabsProfile: { sex: "female", birth_date: "1970-01-01" } });

  test("accepted DOB survives failed reconciliation and retry, then refreshes age zones inside 20 seconds", async ({ labsPage: page, labsApi }) => {
    for (const date of ["2020-12-31", "2021-01-01", "2022-01-01"]) {
      await labsApi.create(date, [{ test_key: "ferritin", entered_value: "8", entered_unit: "ng/mL" }]);
    }
    const original = await labsApi.detail("ferritin");
    expect(original.results.map((result) => result.age_years)).toEqual([52, 51, 50]);
    expect(original.chart_zones[0].to_date_exclusive).toBe("2021-01-01");

    let detailReads = 0;
    let catalogReads = 0;
    let overviewReads = 0;
    let accepted = false;
    let allowProfileRead = false;
    let failedProfileReads = 0;
    let observeBlockedProfileRead!: () => void;
    let releaseBlockedProfileRead!: () => void;
    const blockedProfileRead = new Promise<void>((resolve) => { observeBlockedProfileRead = resolve; });
    const profileReadRelease = new Promise<void>((resolve) => { releaseBlockedProfileRead = resolve; });
    let targetPlanWrites = 0;
    await page.route("**/labs/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin === API_ORIGIN && route.request().method() === "GET" && url.pathname === "/labs/tests/ferritin") detailReads += 1;
      if (url.origin === API_ORIGIN && route.request().method() === "GET" && url.pathname === "/labs/catalog") catalogReads += 1;
      await route.continue();
    });
    await page.route("**/labs", async (route) => {
      if (new URL(route.request().url()).origin === API_ORIGIN && route.request().method() === "GET" && route.request().resourceType() === "fetch") overviewReads += 1;
      await route.continue();
    });
    await page.route("**/target-plans", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      targetPlanWrites += 1;
      const response = await route.fetch();
      accepted = response.status() === 201;
      await route.fulfill({ response });
    });
    await page.route("**/profile", async (route) => {
      if (route.request().method() === "GET" && route.request().resourceType() === "fetch" && accepted && !allowProfileRead) {
        failedProfileReads += 1;
        if (failedProfileReads === 1) {
          observeBlockedProfileRead();
          await profileReadRelease;
        }
        return route.fulfill({ status: 503, contentType: "application/json", json: { detail: "unavailable" } });
      }
      await route.continue();
    });

    await page.clock.setFixedTime(new Date());
    await navigateToOwnerLabs(page);
    const warmDetail = waitForLabsGet(page, "/labs/tests/ferritin");
    await page.getByRole("link", { name: "الفيريتين", exact: true }).click();
    expect((await warmDetail).status()).toBe(200);
    const warmDetailAt = await page.evaluate(() => Date.now());
    await expect(page.getByTestId("lab-detail")).toBeVisible();
    const warmedOwnerQueries = await cachedOwnerQueries(page);
    expect(warmedOwnerQueries.some((key) => key[3] === "overview")).toBe(true);
    expect(warmedOwnerQueries.some((key) => key[3] === "test" && key[4] === "ferritin")).toBe(true);
    const invalidationsBeforeChange = await ownerInvalidations(page);
    const readsBeforePreview = detailReads;
    await page.getByRole("link", { name: "الملف", exact: true }).click();
    await expect(page).toHaveURL(/\/profile$/);
    expect(await cachedOwnerQueries(page)).toEqual(warmedOwnerQueries);
    await expect(page.getByText("لا يمكن تعديل الجنس بعد حفظ الملف الشخصي.", { exact: true })).toBeVisible();
    await page.getByLabel("تاريخ الميلاد").fill("1971-01-01");
    await expect(page.getByRole("region", { name: "الأهداف المتوقعة بعد الحفظ" })).toBeVisible();
    expect(detailReads).toBe(readsBeforePreview);
    expect(await ownerInvalidations(page)).toEqual(invalidationsBeforeChange);
    await page.getByRole("button", { name: "مراجعة وتأكيد" }).click();
    await page.getByRole("dialog", { name: "تأكيد الأهداف الجديدة؟" }).getByRole("button", { name: "حفظ الخطة" }).click();
    await blockedProfileRead;
    const invalidationsAtBlockedRead = await ownerInvalidations(page);
    expect(invalidationsAtBlockedRead).toHaveLength(invalidationsBeforeChange.length + 1);
    const failedProfileRead = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.origin === API_ORIGIN && url.pathname === "/profile";
    });
    releaseBlockedProfileRead();
    expect((await failedProfileRead).status()).toBe(503);
    await expect(page.getByRole("status").filter({ hasText: "تعذر تحديث البيانات المعروضة" })).toBeVisible();
    expect(failedProfileReads).toBe(2);
    await expect(page.getByLabel("تاريخ الميلاد")).toHaveValue("1971-01-01");
    await expect(page.getByText("لا يمكن تعديل الجنس بعد حفظ الملف الشخصي.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /تغيير الجنس/ })).toHaveCount(0);
    expect(targetPlanWrites).toBe(1);

    allowProfileRead = true;
    const invalidationsAfterAcceptedWrite = await ownerInvalidations(page);
    const successfulProfileRead = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.origin === API_ORIGIN && url.pathname === "/profile";
    });
    await page.getByRole("button", { name: "إعادة تحديث البيانات" }).click();
    expect((await successfulProfileRead).status()).toBe(200);
    await expect(page.getByRole("status").filter({ hasText: "تعذر تحديث البيانات المعروضة" })).toHaveCount(0);
    await expect(page.getByText("تم حفظ التغييرات", { exact: true })).toBeVisible();
    const invalidationsAfterRecovery = await ownerInvalidations(page);
    expect(invalidationsAfterRecovery).toHaveLength(invalidationsAfterAcceptedWrite.length + 1);
    expect(invalidationsAfterRecovery.at(-1)).toBe(invalidationsAtBlockedRead.at(-1));
    expect(targetPlanWrites).toBe(1);
    expect(await page.evaluate((start) => Date.now() - start, warmDetailAt)).toBeLessThan(20_000);

    const revised = await labsApi.detail("ferritin");
    expect(revised.results.map((result) => result.age_years)).toEqual([51, 50, 49]);
    expect(revised.chart_zones[0].to_date_exclusive).toBe("2022-01-01");
    const readsBeforeOpen = detailReads;
    const overviewRefresh = waitForLabsGet(page, "/labs");
    await page.getByRole("link", { name: "التحاليل", exact: true }).click();
    expect((await overviewRefresh).status()).toBe(200);
    const detailRefresh = waitForLabsGet(page, "/labs/tests/ferritin");
    await page.getByRole("link", { name: "الفيريتين", exact: true }).click();
    expect((await detailRefresh).status()).toBe(200);
    const reopenedDetailAt = await page.evaluate(() => Date.now());
    expect(reopenedDetailAt - warmDetailAt).toBeLessThan(20_000);
    expect(detailReads).toBe(readsBeforeOpen + 1);
    await expectReferences(page, revised.results[0]);

    const focusRefresh = waitForLabsGet(page, "/labs/tests/ferritin");
    const readsBeforeFocus = detailReads;
    await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
    expect((await focusRefresh).status()).toBe(200);
    const focusRefreshAt = await page.evaluate(() => Date.now());
    expect(focusRefreshAt - reopenedDetailAt).toBeLessThan(20_000);
    expect(detailReads).toBe(readsBeforeFocus + 1);

    const readsBeforeMinute = { detailReads, catalogReads, overviewReads };
    await page.clock.fastForward(60_000);
    expect({ detailReads, catalogReads, overviewReads }).toEqual(readsBeforeMinute);
  });
});
