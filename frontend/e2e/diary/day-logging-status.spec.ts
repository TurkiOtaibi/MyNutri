import { API_TOKEN, API_URL, expect, offsetIsoDate, test } from "../foods/helpers";

test.describe("@diary day logging status", () => {
  test("@p0 explicit empty completion, write guard, replay, and reopen", async ({ request }) => {
    const calendar = await request.get(`${API_URL}/account/calendar`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` }
    });
    expect(calendar.ok()).toBe(true);
    const currentDate = (await calendar.json()).current_diary_date as string;
    const diaryDate = offsetIsoDate(currentDate, -2_000);
    const initial = await request.get(`${API_URL}/diary/days/${diaryDate}/status`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` }
    });
    expect(initial.ok()).toBe(true);
    const before = await initial.json();

    if (before.logging_status === "complete") {
      const reopen = await request.put(`${API_URL}/diary/days/${diaryDate}/reopen`, {
        headers: {
          Authorization: `Bearer ${API_TOKEN}`,
          "Idempotency-Key": `e2e-reopen-${crypto.randomUUID()}`,
          "If-Match": `"day-${before.logging_status_version}"`
        },
        data: { expected_version: before.logging_status_version }
      });
      expect(reopen.ok()).toBe(true);
    }

    const ready = await request.get(`${API_URL}/diary/days/${diaryDate}/status`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` }
    });
    const readyStatus = await ready.json();
    const key = `e2e-complete-${crypto.randomUUID()}`;
    const complete = await request.put(`${API_URL}/diary/days/${diaryDate}/complete`, {
      headers: { Authorization: `Bearer ${API_TOKEN}`, "Idempotency-Key": key, "If-Match": `"day-${readyStatus.logging_status_version}"` },
      data: { expected_version: readyStatus.logging_status_version }
    });
    expect(complete.ok()).toBe(true);
    const completed = await complete.json();
    expect(completed).toMatchObject({
      logging_status: "complete",
      analysis_eligible: true,
      date: diaryDate
    });

    const replay = await request.put(`${API_URL}/diary/days/${diaryDate}/complete`, {
      headers: { Authorization: `Bearer ${API_TOKEN}`, "Idempotency-Key": key, "If-Match": `"day-${readyStatus.logging_status_version}"` },
      data: { expected_version: readyStatus.logging_status_version }
    });
    expect(replay.ok()).toBe(true);
    expect(replay.headers()["idempotent-replayed"]).toBe("true");
    expect(await replay.json()).toEqual(completed);

    const reopened = await request.put(`${API_URL}/diary/days/${diaryDate}/reopen`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        "Idempotency-Key": `e2e-reopen-${crypto.randomUUID()}`,
        "If-Match": `"day-${completed.logging_status_version}"`
      },
      data: { expected_version: completed.logging_status_version }
    });
    expect(reopened.ok()).toBe(true);
    expect(await reopened.json()).toMatchObject({
      logging_status: "partial",
      analysis_eligible: false
    });
  });

  test("@p0 Arabic status UI is reachable, non-color, and mobile-safe", async ({ page }) => {
    const dayStatusResponse = page.waitForResponse((response) =>
      response.request().method() === "GET"
      && /\/diary\/days\/\d{4}-\d{2}-\d{2}\/status$/.test(new URL(response.url()).pathname)
    );
    await Promise.all([page.goto("/diary"), dayStatusResponse]);
    await expect(page.getByRole("heading", { name: "حالة تسجيل اليوم" })).toBeVisible();
    await expect(page.locator(".day-status-card strong")).toHaveText(/غير مسجل|التسجيل غير مكتمل|تم تسجيل اليوم/);
    await expect(page.locator(".day-status-card strong span[aria-hidden=true]")).toBeVisible();
    await expect(page.locator(".day-status-card")).toHaveAttribute("aria-label", /، (غير مسجل|التسجيل غير مكتمل|تم تسجيل اليوم)$/);
    for (const width of [320, 360, 390, 430]) {
      await page.setViewportSize({ width, height: 800 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    }
  });

  test("@p0 an ambiguous command retry preserves its idempotency key and body", async ({ page }) => {
    const requests: Array<{ key: string | null; body: string | null }> = [];
    let attempt = 0;
    await page.route(/\/diary\/days\/\d{4}-\d{2}-\d{2}\/(complete|reopen)$/, async (route) => {
      requests.push({
        key: route.request().headers()["idempotency-key"] ?? null,
        body: route.request().postData()
      });
      const response = await route.fetch();
      attempt += 1;
      if (attempt === 1) await route.abort("connectionfailed");
      else await route.fulfill({ response });
    });

    await page.goto("/diary");
    await page.locator(".day-status-card button").click();
    const dialog = page.locator(".diary-modal-panel");
    await dialog.locator(".btn.danger").click();
    await expect(dialog.getByText("تعذر حفظ حالة اليوم. لم تُفقد بياناتك؛ حاول مجددًا.")).toBeVisible();
    await dialog.locator(".btn.danger").click();
    await expect(dialog).toBeHidden();
    expect(requests).toHaveLength(2);
    expect(requests[1]).toEqual(requests[0]);
  });
});
