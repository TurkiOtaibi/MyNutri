import { readFileSync } from "node:fs";
import path from "node:path";

import { API_URL, expect, offsetIsoDate, test, waitForLabsGet } from "./helpers";

const TOKEN_FILE = path.join(process.cwd(), "e2e", ".auth", "access-token.txt");
const adminHeaders = () => ({ Authorization: `Bearer ${readFileSync(TOKEN_FILE, "utf8").trim()}` });

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
