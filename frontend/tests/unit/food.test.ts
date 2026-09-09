import { describe, expect, it } from "vitest";

import {
  calculateServingNutrition,
  cleanOptionalText,
  defaultServingText,
  emptyFoodForm,
  formatOptionalValue,
  normalizeFoodForm,
  validateFoodForm
} from "@/lib/food";
import { ApiError } from "@/lib/api";
import { mapFoodApiError } from "@/features/foods/food-form-model";
import type { FoodResponse } from "@/lib/types";

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

  it("preserves unknown net carbohydrates instead of inventing zero", () => {
    const nutrition = calculateServingNutrition({
      ...emptyFoodForm,
      id: "00000000-0000-0000-0000-000000000001",
      calories: 100,
      protein_g: 5,
      carb_g: 20,
      fat_g: 2,
      unit_amount: 100,
      net_carbs_g: null,
      legacy_nutrition: { folate_mcg: null, vitamin_a_mcg: null, meaning_ar: "قديم" },
      created_at: "2026-09-01T00:00:00Z",
      updated_at: "2026-09-01T00:00:00Z",
      archived_at: null
    } as FoodResponse);

    expect(nutrition?.net_carbs_g).toBeNull();
  });

  it("rejects mismatched measurement dimensions and maps the referenced-food conflict", () => {
    expect(validateFoodForm({
      ...emptyFoodForm,
      nutrition_basis: "per_100ml",
      unit_basis: "g"
    }).unit_basis).toBe("أساس الوحدة يجب أن يطابق أساس القيم الغذائية.");

    expect(mapFoodApiError(new ApiError("conflict", 409, undefined, "FOOD_MEASUREMENT_DIMENSION_IN_USE")))
      .toEqual({ form: "لا يمكن تغيير أساس القياس بين الوزن والحجم بعد تسجيل الطعام في اليومية." });
  });
});
