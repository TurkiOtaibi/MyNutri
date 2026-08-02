import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./foods/helpers";

const majorStates = [
  { path: "/profile", name: "Profile" },
  { path: "/foods", name: "Foods" },
  { path: "/foods/new", name: "Add Food" },
  { path: "/diary", name: "Diary" }
];

for (const state of majorStates) {
  test(`@certification ${state.name} has no serious or critical axe violations`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(state.path);
    await expect(page.locator("main").first()).toBeVisible();

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blocking = result.violations.filter((violation) =>
      violation.impact === "serious" || violation.impact === "critical"
    );

    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}
