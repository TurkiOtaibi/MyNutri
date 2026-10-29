import { formatGregorianArabicDate } from "../../lib/dates";
import type { Page } from "@playwright/test";
import type { LabOverviewResponse } from "../../lib/types";
import { API_URL, expect, navigateToOwnerLabs, offsetIsoDate, test } from "./helpers";

const CATEGORY_KEYS = [
  "glycemic",
  "lipids",
  "blood",
  "iron",
  "vitamins_minerals",
  "electrolytes",
  "liver",
  "kidney",
  "thyroid",
  "hormones",
  "inflammation",
  "coagulation",
  "pancreas",
  "cardiac",
  "other",
] as const;

const CATEGORY_COUNTS: Record<(typeof CATEGORY_KEYS)[number], number> = {
  glycemic: 1,
  lipids: 4,
  blood: 20,
  iron: 4,
  vitamins_minerals: 7,
  electrolytes: 4,
  liver: 5,
  kidney: 2,
  thyroid: 3,
  hormones: 0,
  inflammation: 0,
  coagulation: 0,
  pancreas: 0,
  cardiac: 0,
  other: 1,
};

const SORTS = ["newest_updated", "oldest_updated", "name_asc", "name_desc", "category"] as const;


// «التصنيف» and «الترتيب» sit behind one toggle beside the always-visible search (issue #151).
async function openFilters(page: Page) {
  const toggle = page.getByRole("button", { name: "التصنيف والترتيب", exact: true });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
}

test("empty owner overview and the complete 51-test catalog remain distinct", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await expect(page.getByText("لم تسجل أي نتائج بعد.", { exact: true })).toBeVisible();
  await expect(page.getByTestId("lab-row")).toHaveCount(0);

  await page.getByRole("tab", { name: "كل التحاليل" }).click();
  await expect(page.getByTestId("lab-row")).toHaveCount(51);
  await expect(page.getByText("51 تحليلاً", { exact: true })).toBeVisible();
});

test("catalog search accepts Arabic, English, and abbreviation", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  await page.getByRole("tab", { name: "كل التحاليل" }).click();
  const search = page.getByRole("searchbox", { name: "البحث في التحاليل" });

  for (const term of ["السكر التراكمي", "Hemoglobin A1c", "HbA1c"]) {
    await search.fill(term);
    await expect(page.getByTestId("lab-row")).toHaveCount(1);
    await expect(page.getByTestId("lab-row")).toContainText("HbA1c");
  }
});

test("all 15 categories and five sorts control the rendered catalog order", async ({ labsPage: page, labsApi }) => {
  const overview = await labsApi.overview();
  const date = offsetIsoDate(overview.server_today, -1);
  await labsApi.create(date, [
    { test_key: "hba1c", entered_value: "5.20", entered_unit: "%" },
  ]);
  await labsApi.create(date, [
    { test_key: "ferritin", entered_value: "80", entered_unit: "ng/mL" },
  ]);
  await navigateToOwnerLabs(page);
  await page.getByRole("tab", { name: "كل التحاليل" }).click();
  await openFilters(page);
  const category = page.locator("label").filter({ hasText: /^التصنيف/ }).locator("select");
  const sort = page.locator("label").filter({ hasText: /^الترتيب/ }).locator("select");
  const renderedKeys = () => page.getByTestId("lab-row").evaluateAll((rows) => (
    rows.map((row) => row.getAttribute("data-test-key"))
  ));

  for (const key of CATEGORY_KEYS) {
    await category.selectOption(key);
    await expect(category).toHaveValue(key);
    await expect(page.getByTestId("lab-row")).toHaveCount(CATEGORY_COUNTS[key]);
    if (CATEGORY_COUNTS[key] === 0) {
      await expect(page.getByText("لا توجد تحاليل ضمن هذا التصنيف.", { exact: true })).toBeVisible();
    } else {
      await expect(page.locator(`[data-category="${key}"]`)).toHaveCount(CATEGORY_COUNTS[key]);
    }
  }
  await category.selectOption("");
  const expectedStarts: Record<(typeof SORTS)[number], string[]> = {
    newest_updated: ["ferritin", "hba1c"],
    oldest_updated: ["hba1c", "ferritin"],
    name_asc: ["basophils_abs"],
    name_desc: ["bun"],
    category: ["hba1c", "total_cholesterol"],
  };
  for (const value of SORTS) {
    await sort.selectOption(value);
    await expect(sort).toHaveValue(value);
    await expect(page.getByTestId("lab-row")).toHaveCount(51);
    await expect.poll(async () => (await renderedKeys()).slice(0, expectedStarts[value].length))
      .toEqual(expectedStarts[value]);
  }
  await expect(page).toHaveURL(/\/labs$/);
});

test("owned filters retain a clear empty-category state", async ({ labsPage: page, labsApi }) => {
  const overview = await labsApi.overview();
  await labsApi.create(offsetIsoDate(overview.server_today, -1), [
    { test_key: "hba1c", entered_value: "5.20", entered_unit: "%" },
  ]);
  await navigateToOwnerLabs(page);
  await openFilters(page);
  await page.locator("label").filter({ hasText: /^التصنيف/ }).locator("select").selectOption("iron");
  await expect(page.getByText("لا توجد نتائج ضمن هذا التصنيف.", { exact: true })).toBeVisible();
});

test("latest owned result shows canonical value, status, and date", async ({ labsPage: page, labsApi }) => {
  const overview = await labsApi.overview();
  const date = offsetIsoDate(overview.server_today, -1);
  await labsApi.create(date, [
    { test_key: "hba1c", entered_value: "5.20", entered_unit: "%" },
  ]);

  await navigateToOwnerLabs(page);
  const row = page.locator('[data-test-key="hba1c"]');
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("5.2");
  await expect(row).toContainText("%");
  await expect(row).toContainText("طبيعي");
  await expect(row).toContainText(formatGregorianArabicDate(date));
});

test("profile-required overview presents the Profile completion action", async ({ labsPage: page, labsApi }) => {
  const current = await labsApi.overview();
  const profileRequired: LabOverviewResponse = {
    ...current,
    items: [],
    eligibility: { allowed: false, reason: "profile_required" },
    read_only: false,
  };
  await page.route(`${API_URL}/labs`, (route) => route.fulfill({ json: profileRequired }));
  await navigateToOwnerLabs(page);
  await expect(page.getByRole("link", { name: "إكمال الملف" })).toHaveAttribute("href", "/profile");
  await page.getByRole("link", { name: "إكمال الملف" }).click();
  await expect(page.getByRole("link", { name: "بياناتي", exact: true })).toHaveAttribute("aria-current", "page");
});


test("initial overview failure offers the governed retry and reloads current results", async ({ labsPage: page }) => {
  let fail = true;
  let reads = 0;
  await page.route(`${API_URL}/labs`, async route => {
    reads += 1;
    if (fail) return route.fulfill({ status: 503, json: { detail: "unavailable" } });
    return route.continue();
  });
  await page.goto("/labs");
  const alert = page.getByRole("alert").filter({ hasText: "تعذر تحميل التحاليل الحالية. حاول مرة أخرى." });
  await expect(alert).toBeVisible();
  const beforeRetry = reads;
  fail = false;
  await alert.getByRole("button", { name: "إعادة تحميل التحاليل", exact: true }).click();
  await expect(page.getByRole("tab", { name: "تحاليلك", exact: true })).toBeVisible();
  await expect(alert).toHaveCount(0);
  expect(reads).toBeGreaterThan(beforeRetry);
  await expect(page.getByText("لم تسجل أي نتائج بعد.", { exact: true })).toBeVisible();
});
