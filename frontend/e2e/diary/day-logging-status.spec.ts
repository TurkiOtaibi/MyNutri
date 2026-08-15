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
          "Idempotency-Key": `e2e-reopen-${crypto.randomUUID()}`
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
      headers: { Authorization: `Bearer ${API_TOKEN}`, "Idempotency-Key": key },
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
      headers: { Authorization: `Bearer ${API_TOKEN}`, "Idempotency-Key": key },
      data: { expected_version: readyStatus.logging_status_version }
    });
    expect(replay.ok()).toBe(true);
    expect(replay.headers()["idempotent-replayed"]).toBe("true");
    expect(await replay.json()).toEqual(completed);

    const reopened = await request.put(`${API_URL}/diary/days/${diaryDate}/reopen`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        "Idempotency-Key": `e2e-reopen-${crypto.randomUUID()}`
      },
      data: { expected_version: completed.logging_status_version }
    });
    expect(reopened.ok()).toBe(true);
    expect(await reopened.json()).toMatchObject({
      logging_status: "partial",
      analysis_eligible: false
    });
  });

  test("@p0 Arabic status UI is reachable and mobile-safe", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto("/diary");
    await expect(page.getByRole("heading", { name: "حالة تسجيل اليوم" })).toBeVisible();
    await expect(page.getByText(/غير مسجل|التسجيل غير مكتمل|تم تسجيل اليوم/)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });
});
