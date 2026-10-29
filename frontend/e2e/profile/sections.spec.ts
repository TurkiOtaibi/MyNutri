import { expect, test } from "@playwright/test";

// BR-PRF-029 to BR-PRF-031: «بياناتي» sections, linked tabs and the account section.
test.describe("@issue149 Profile sections", () => {
  test("BR-PRF-029 opens «أهدافي» by default and keeps each section in the URL", async ({ page }) => {
    await page.goto("/profile");
    const tabs = page.getByRole("tablist", { name: "أقسام بياناتي" }).getByRole("tab");
    await expect(tabs).toHaveText(["أهدافي", "سجل الخطط", "الحساب"]);
    await expect(page.getByRole("tab", { name: "أهدافي", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("الوزن", { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "سجل الخطط" })).toHaveCount(0);

    await page.getByRole("tab", { name: "سجل الخطط", exact: true }).click();
    await expect(page).toHaveURL(/\/profile\?tab=history$/);
    await expect(page.getByRole("region", { name: "سجل الخطط" })).toBeVisible();
    await expect(page.getByLabel("الوزن", { exact: true })).toBeHidden();

    await page.reload();
    await expect(page.getByRole("tab", { name: "سجل الخطط", exact: true })).toHaveAttribute("aria-selected", "true");

    await page.getByRole("tab", { name: "أهدافي", exact: true }).click();
    await expect(page).toHaveURL(/\/profile$/);
  });

  test("BR-PRF-029 tabs follow RTL arrow-key order", async ({ page }) => {
    await page.goto("/profile");
    const goals = page.getByRole("tab", { name: "أهدافي", exact: true });
    await goals.focus();
    await page.keyboard.press("ArrowLeft");
    await expect(page.getByRole("tab", { name: "سجل الخطط", exact: true })).toBeFocused();
    await expect(page.getByRole("tab", { name: "سجل الخطط", exact: true })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: "الحساب", exact: true })).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "سجل الخطط", exact: true })).toBeFocused();
    await page.keyboard.press("Home");
    await expect(goals).toBeFocused();
  });

  test("BR-PRF-030 keeps an unsaved Profile draft while another section is open", async ({ page }) => {
    await page.goto("/profile");
    const weight = page.getByLabel("الوزن", { exact: true });
    const edited = String(Number(await weight.inputValue() || 70) + 1);
    await weight.fill(edited);
    const saveBar = page.getByRole("region", { name: "حفظ تغييرات الملف الشخصي" });
    await expect(saveBar).toBeVisible();
    await page.getByRole("tab", { name: "سجل الخطط", exact: true }).click();
    await expect(saveBar).toHaveCount(0);
    await page.getByRole("tab", { name: "أهدافي", exact: true }).click();
    await expect(weight).toHaveValue(edited);
    await expect(saveBar).toBeVisible();
  });

  test("BR-PRF-031 «الحساب» shows the username and signs out on phones", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/profile?tab=account");
    const account = page.getByRole("region", { name: "الحساب", exact: true });
    await expect(account).toContainText("اسم المستخدم");
    await expect(account.locator("bdi")).not.toHaveText("");
    // Phones keep a single sign-out entry, inside «الحساب».
    await expect(page.locator(".nav-signout")).toBeHidden();
    const signOut = page.getByRole("button", { name: "تسجيل الخروج", exact: true });
    await expect(signOut).toHaveCount(1);
    await expect(signOut).toBeVisible();
  });

  test("BR-NAV-008 desktop keeps sign-out in the top bar", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/profile");
    await expect(page.locator(".nav-signout")).toBeVisible();
  });
});
