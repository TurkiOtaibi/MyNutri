import { expect, navigateToOwnerLabs, test } from "./helpers";

test("Labs is a preserved top-nav destination", async ({ labsPage: page }) => {
  await navigateToOwnerLabs(page);
  const nav = page.getByRole("navigation", { name: "التنقل الرئيسي" });
  await expect(nav.getByRole("link", { name: "التحاليل" })).toHaveAttribute("aria-current", "page");
  for (const label of ["اليوميات", "الأطعمة", "الملف"]) {
    await expect(nav.getByRole("link", { name: label })).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "تحاليلك" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "كل التحاليل" })).toBeVisible();
});

test("Labs navigation remains active beneath the future detail route", async ({ labsPage: page }) => {
  await page.goto("/labs/hba1c");
  await expect(page.getByRole("navigation", { name: "التنقل الرئيسي" })
    .getByRole("link", { name: "التحاليل" }))
    .toHaveAttribute("aria-current", "page");
});
