import { expect, test } from "@playwright/test";

test("own-password validation, backend rejection, success and independent profile draft", async ({ page }) => {
  let requests = 0;
  await page.route("**/auth/change-password", async (route) => {
    requests += 1;
    expect(route.request().postDataJSON()).toEqual({
      current_password: "Synthetic-current-password!",
      new_password: "Synthetic-new-password!",
    });
    await route.fulfill(requests === 1 ? {
      status: 422, json: { error: { code: "CURRENT_PASSWORD_INCORRECT", message_ar: "كلمة المرور الحالية غير صحيحة." } },
    } : { status: 200, json: { message: "تم تغيير كلمة المرور." } });
  });
  await page.goto("/profile");
  const current = page.getByLabel("كلمة المرور الحالية", { exact: true });
  const next = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  const submit = page.getByRole("button", { name: "تغيير كلمة المرور", exact: true });
  await current.fill("Synthetic-current-password!");
  await next.fill("short");
  await submit.click();
  await expect(page.getByText("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.", { exact: true })).toBeVisible();
  await expect(next).toBeFocused();
  expect(requests).toBe(0);
  await next.fill("Synthetic-new-password!");
  await submit.click();
  await expect(page.getByText("كلمة المرور الحالية غير صحيحة.", { exact: true })).toBeVisible();
  await expect(current).toBeFocused();
  const weight = page.getByLabel("الوزن", { exact: true });
  const previousWeight = await weight.inputValue();
  await weight.fill(String(Number(previousWeight || 70) + 1));
  await submit.click();
  await expect(page.getByText("تم تغيير كلمة المرور.", { exact: true })).toBeFocused();
  await expect(current).toHaveValue("");
  await expect(next).toHaveValue("");
  await page.getByRole("link", { name: "اليوميات", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toBeVisible();
  await page.getByRole("button", { name: "متابعة التعديل", exact: true }).click();
  await expect(weight).toHaveValue(String(Number(previousWeight || 70) + 1));
});

test("password-only draft guards navigation and discard clears both fields", async ({ page }) => {
  await page.goto("/profile");
  const current = page.getByLabel("كلمة المرور الحالية", { exact: true });
  const next = page.getByLabel("كلمة المرور الجديدة", { exact: true });
  await current.fill("Synthetic-current-password!");
  await next.fill("Synthetic-new-password!");
  await page.getByRole("link", { name: "اليوميات", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "تغييرات غير محفوظة" })).toBeVisible();
  await page.getByRole("button", { name: "متابعة التعديل", exact: true }).click();
  await expect(current).toHaveValue("Synthetic-current-password!");
  await page.getByRole("link", { name: "اليوميات", exact: true }).click();
  await page.getByRole("button", { name: "تجاهل التغييرات والمغادرة", exact: true }).click();
  await expect(page).not.toHaveURL(/\/profile$/);
  await page.getByRole("link", { name: "بياناتي", exact: true }).click();
  await expect(current).toHaveValue("");
  await expect(next).toHaveValue("");
});

for (const width of [320, 390, 1280]) {
  test(`password action stays above the dirty Profile save bar at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/profile");
    const weight = page.getByLabel("الوزن", { exact: true });
    const preview = page.waitForResponse(response => new URL(response.url()).pathname === "/profile/preview" && response.request().method() === "POST" && response.ok());
    await weight.fill(String(Number(await weight.inputValue() || 70) + 1));
    const saveBar = page.getByRole("region", { name: "حفظ تغييرات الملف الشخصي" });
    await expect(saveBar).toBeVisible();
    await preview;
    await expect(saveBar.getByRole("button")).toBeEnabled();
    const submit = page.getByRole("button", { name: "تغيير كلمة المرور", exact: true });
    await submit.scrollIntoViewIfNeeded();
    await expect(submit).toBeInViewport();
    // A visible element can still be covered by the fixed save bar or mobile tabs.
    await expect.poll(() => submit.evaluate((button) => {
      const bounds = button.getBoundingClientRect();
      const hit = document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
      return hit !== null && button.contains(hit);
    })).toBe(true);
    await submit.click({ trial: true });
    const actionBounds = await submit.boundingBox();
    const barBounds = await saveBar.boundingBox();
    expect(actionBounds).not.toBeNull();
    expect(barBounds).not.toBeNull();
    expect(actionBounds!.y + actionBounds!.height).toBeLessThanOrEqual(barBounds!.y);
    await expect(page.getByRole("region", { name: "تغيير كلمة المرور", exact: true })).toHaveAttribute("dir", "rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
