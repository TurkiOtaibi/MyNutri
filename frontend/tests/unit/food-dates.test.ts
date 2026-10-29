import { describe, expect, it } from "vitest";

import { formatFoodDate } from "@/features/foods/food-details-view";

describe("formatFoodDate", () => {
  it("shows food timestamps as readable Gregorian dates", () => {
    expect(formatFoodDate("2026-10-17T09:30:00Z")).toBe("17 أكتوبر 2026");
  });

  it("uses the Riyadh calendar day", () => {
    expect(formatFoodDate("2026-10-16T22:30:00Z")).toBe("17 أكتوبر 2026");
  });
});
