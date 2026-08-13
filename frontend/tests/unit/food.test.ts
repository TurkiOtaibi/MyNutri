import { describe, expect, it } from "vitest";

import {
  cleanOptionalText,
  defaultServingText,
  emptyFoodForm,
  formatOptionalValue,
  normalizeFoodForm
} from "@/lib/food";

describe("food normalization and presentation", () => {
  it("normalizes required and nullable text without mutating the source", () => {
    const source = {
      ...emptyFoodForm,
      name: "  Brown   rice  ",
      brand: "   ",
      notes: "  cooked   without salt ",
      calories: null,
      protein_g: null,
      carb_g: null,
      fat_g: null,
      unit_amount: null
    };

    const normalized = normalizeFoodForm(source);

    expect(normalized).toMatchObject({
      name: "Brown rice",
      brand: null,
      notes: "cooked without salt",
      calories: 0,
      protein_g: 0,
      carb_g: 0,
      fat_g: 0,
      unit_amount: 0
    });
    expect(source.name).toBe("  Brown   rice  ");
  });

  it("preserves established nullable and serving presentation", () => {
    expect(cleanOptionalText(null)).toBeNull();
    expect(cleanOptionalText("  a   b ")).toBe("a b");
    expect(formatOptionalValue(null, "mg")).toBe("-");
    expect(formatOptionalValue(12, "mg")).toBe("12 mg");
    expect(defaultServingText({ default_unit_type: "g", unit_amount: 37.5, unit_basis: "g" }))
      .toContain("37.5");
  });
});
