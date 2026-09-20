import { readFileSync } from "node:fs";
import path from "node:path";
import type { LabTestDetailResponse } from "../../lib/types";

import { API_URL, expect, offsetIsoDate, test, waitForLabsGet } from "./helpers";

const TOKEN_FILE = path.join(process.cwd(), "e2e", ".auth", "access-token.txt");
const adminHeaders = () => ({ Authorization: `Bearer ${readFileSync(TOKEN_FILE, "utf8").trim()}` });

test("admin opens selected user's complete detail through scoped overview link without writes", async ({ page, labsApi }) => {
  const today = (await labsApi.overview()).server_today;
  for (const [offset, value, unit] of [[-1, "42", "mmol/mol"], [0, "5.2", "%"]] as const) await labsApi.create(offsetIsoDate(today, offset), [{ test_key: "hba1c", entered_value: value, entered_unit: unit }]);
  const detail = await labsApi.detail("hba1c");
  const base = `/admin/users/${labsApi.actor.principalId}/labs`;
  const overview = waitForLabsGet(page, base);
  await page.goto(base);
  expect((await overview).status()).toBe(200);
  const read = waitForLabsGet(page, `${base}/tests/hba1c`);
  await page.locator('[data-test-key="hba1c"]').getByRole("link").click();
  const response = await read;
  expect(response.status()).toBe(200);
  expect((await response.json() as LabTestDetailResponse).read_only).toBe(true);
  await expect(page).toHaveURL(new RegExp(`${base}/tests/hba1c$`));
  await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
  await expect(page.locator("[data-chart-point]")).toHaveCount(detail.results.length);
  await expect(page.locator("[data-history-result]")).toHaveCount(detail.results.length);
  for (const result of detail.results) {
    const row = page.locator(`[data-history-result="${result.id}"]`);
    await expect(row).toContainText(`${result.display_value} ${result.display_unit}`);
    await expect(row).toContainText(result.status.label_ar);
  }
  await page.locator(`[data-chart-point="${detail.results[0].id}"]`).focus();
  await page.keyboard.press("Home");
  await expect(page.locator(`[data-reference-date="${detail.results[1].test_date}"]`)).toContainText(detail.results[1].status.label_ar);
  await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
  const refresh = waitForLabsGet(page, `${base}/tests/hba1c`);
  await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
  expect((await refresh).status()).toBe(200);
});

test("switching admin detail subject uses that subject's API results", async ({ page, labsApi, request }) => {
  await labsApi.create((await labsApi.overview()).server_today, [{ test_key: "hba1c", entered_value: "5.2", entered_unit: "%" }]);
  const owner = await labsApi.detail("hba1c");
  const ownerPath = `/admin/users/${labsApi.actor.principalId}/labs/tests/hba1c`;
  const first = waitForLabsGet(page, ownerPath);
  await page.goto(ownerPath);
  expect((await first).status()).toBe(200);
  await expect(page.locator(`[data-history-result="${owner.results[0].id}"]`)).toBeVisible();
  const account = await request.get(`${API_URL}/account/me`, { headers: adminHeaders() });
  expect(account.status()).toBe(200);
  const { principal_id: principalId } = await account.json() as { principal_id: string };
  const nextPath = `/admin/users/${principalId}/labs/tests/hba1c`;
  const second = waitForLabsGet(page, nextPath);
  await page.goto(nextPath);
  const response = await second;
  expect(response.status()).toBe(200);
  const detail = await response.json() as LabTestDetailResponse;
  await expect(page.locator("[data-history-result]")).toHaveCount(detail.results.length);
  await expect(page.locator(`[data-history-result="${owner.results[0].id}"]`)).toHaveCount(0);
  await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
});

test("admin's owner detail URL remains explicitly read-only", async ({ page }) => {
  const read = waitForLabsGet(page, "/labs/tests/hba1c");
  await page.goto("/labs/tests/hba1c");
  const response = await read;
  expect(response.status()).toBe(200);
  expect((await response.json() as LabTestDetailResponse).read_only).toBe(true);
  await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
});

test("admin can open the selected user's full Labs overview in read-only mode", async ({ page, labsApi }) => {
  const ownerOverview = await labsApi.overview();
  const date = offsetIsoDate(ownerOverview.server_today, -1);
  await labsApi.create(date, [
    { test_key: "hba1c", entered_value: "5.20", entered_unit: "%" },
  ]);

  const userPath = `/admin/users/${labsApi.actor.principalId}`;
  const accountResponse = waitForLabsGet(page, "/account/me");
  const userResponse = waitForLabsGet(page, userPath);
  await page.goto(userPath);
  const [account, user] = await Promise.all([accountResponse, userResponse]);
  expect(account.status()).toBe(200);
  expect(user.status()).toBe(200);

  const catalogResponse = waitForLabsGet(page, "/labs/catalog");
  const labsResponse = waitForLabsGet(page, `${userPath}/labs`);
  await page.getByRole("link", { name: "عرض التحاليل" }).click();
  const [catalog, labs] = await Promise.all([catalogResponse, labsResponse]);
  expect(catalog.status()).toBe(200);
  expect(labs.status()).toBe(200);
  await expect(page).toHaveURL(new RegExp(`/admin/users/${labsApi.actor.principalId}/labs$`));
  await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
  const row = page.locator('[data-test-key="hba1c"]');
  await expect(row).toContainText("5.2");
  await expect(row).toContainText("طبيعي");
  await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
});

test("admin own Labs route is read-only and exposes no mutation controls", async ({ page }) => {
  const accountResponse = waitForLabsGet(page, "/account/me");
  const catalogResponse = waitForLabsGet(page, "/labs/catalog");
  const labsResponse = waitForLabsGet(page, "/labs");
  await page.goto("/labs");
  const [account, catalog, labs] = await Promise.all([accountResponse, catalogResponse, labsResponse]);
  expect(account.status()).toBe(200);
  expect(catalog.status()).toBe(200);
  expect(labs.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "تحاليلك" })).toBeVisible();
  await expect(page.getByText("للقراءة فقط", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /إضافة|تعديل|حذف/ })).toHaveCount(0);
});

test("admin direct Labs POST is forbidden", async ({ request }) => {
  const overview = await request.get(`${API_URL}/labs`, { headers: adminHeaders() });
  expect(overview.status(), await overview.text()).toBe(200);
  const { server_today: date } = await overview.json() as { server_today: string };
  const response = await request.post(`${API_URL}/labs/results`, {
    headers: { ...adminHeaders(), "Idempotency-Key": `admin-denied-${Date.now()}` },
    data: {
      test_date: offsetIsoDate(date, -1),
      results: [{ test_key: "hba1c", entered_value: "5.20", entered_unit: "%" }],
    },
  });
  expect(response.status()).toBe(403);
  expect(await response.text()).toContain("LAB_READ_ONLY");
});
