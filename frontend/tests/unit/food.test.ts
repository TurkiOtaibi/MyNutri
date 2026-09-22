import { describe, expect, it } from "vitest";

import {
  calculateServingNutrition,
  defaultServingText,
  formatNutrientNumber
} from "@/lib/food";
import { ApiError } from "@/lib/api";
import {
  emptyFoodForm,
  fieldId,
  foodToForm,
  hasFoodErrors,
  mapFoodApiError,
  normalizeFoodForm,
  validateFoodForm,
  type FoodFormValues,
} from "@/features/foods/food-form-model";
import type { FoodResponse } from "@/lib/types";

function foodResponse(overrides: Partial<FoodResponse> = {}): FoodResponse {
  return {
    ...emptyFoodForm,
    id: "00000000-0000-0000-0000-000000000001",
    name: "Test food",
    calories: 100,
    protein_g: 5,
    carb_g: 20,
    fat_g: 2,
    unit_amount: 100,
    net_carbs_g: 15,
    legacy_nutrition: { folate_mcg: null, vitamin_a_mcg: null, meaning_ar: "قديم" },
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
    ...overrides,
  } as FoodResponse;
}

function validFoodForm(overrides: Partial<FoodFormValues> = {}): FoodFormValues {
  return {
    ...emptyFoodForm,
    name: "أرز بني",
    calories: 100,
    protein_g: 5,
    carb_g: 20,
    fat_g: 4,
    unit_amount: 100,
    ...overrides,
  };
}

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

  it("maps only editable fields from a Food response", () => {
    const form = foodToForm(foodResponse({
      future_server_field: "server-owned"
    } as Partial<FoodResponse> & { future_server_field: string }));

    expect(form).not.toHaveProperty("id");
    expect(form).not.toHaveProperty("net_carbs_g");
    expect(form).not.toHaveProperty("legacy_nutrition");
    expect(form).not.toHaveProperty("created_at");
    expect(form).not.toHaveProperty("updated_at");
    expect(form).not.toHaveProperty("future_server_field");
    expect(form).toMatchObject({ name: "Test food", calories: 100, unit_amount: 100 });
  });

  it("preserves established serving presentation", () => {
    expect(defaultServingText({ default_unit_type: "g", unit_amount: 37.5, unit_basis: "g" }))
      .toContain("37.5");
  });

  it("scales core and optional nutrients and rejects invalid serving amounts", () => {
    const nutrition = calculateServingNutrition(foodResponse({
      unit_amount: 37.5,
      calories: 200,
      protein_g: 8,
      sodium_mg: 400,
      net_carbs_g: 12,
    }));

    expect(nutrition).toMatchObject({
      calories: 75,
      protein_g: 3,
      sodium_mg: 150,
      net_carbs_g: 4.5,
    });
    expect(calculateServingNutrition(foodResponse({ unit_amount: 0 }))).toBeNull();
    expect(calculateServingNutrition(foodResponse({ unit_amount: Number.POSITIVE_INFINITY }))).toBeNull();
  });

  it("formats nutrient values with the supplied Registry precision", () => {
    expect(formatNutrientNumber(12.345, 1)).toBe("12.3");
    expect(formatNutrientNumber(12.345, 3)).toBe("12.345");
  });

  it("derives stable form control IDs from field keys rather than display labels", () => {
    expect(fieldId("vitamin_b12_mcg")).toBe("food-vitamin-b12-mcg");
    expect(fieldId("nutrition_data_source")).toBe("food-nutrition-data-source");
  });

  it("preserves unknown net carbohydrates instead of inventing zero", () => {
    const nutrition = calculateServingNutrition(foodResponse({ net_carbs_g: null }));

    expect(nutrition?.net_carbs_g).toBeNull();
  });

  it("enforces required, numeric, and relational Food validation boundaries", () => {
    expect(validateFoodForm(validFoodForm())).toEqual({});
    expect(hasFoodErrors(validateFoodForm(validFoodForm()))).toBe(false);

    const cases: Array<{
      overrides: Partial<FoodFormValues>;
      field: keyof FoodFormValues;
      message: string;
    }> = [
      { overrides: { name: "   " }, field: "name", message: "هذا الحقل مطلوب." },
      { overrides: { unit_amount: 0 }, field: "unit_amount", message: "القيمة أقل من الحد المسموح." },
      { overrides: { calories: 3001 }, field: "calories", message: "القيمة أعلى من الحد المسموح." },
      { overrides: { sodium_mg: -1 }, field: "sodium_mg", message: "القيمة أقل من الحد المسموح." },
      { overrides: { notes: "ا".repeat(501) }, field: "notes", message: "القيمة أعلى من الحد المسموح." },
      { overrides: { fiber_g: 21 }, field: "fiber_g", message: "الألياف لا يمكن أن تكون أكبر من الكربوهيدرات." },
      { overrides: { sugar_g: 5, added_sugar_g: 6 }, field: "added_sugar_g", message: "السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر." },
      {
        overrides: { fat_g: 5, saturated_fat_g: 3, trans_fat_g: 3 },
        field: "trans_fat_g",
        message: "مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.",
      },
    ];

    for (const { overrides, field, message } of cases) {
      const errors = validateFoodForm(validFoodForm(overrides));
      expect(errors[field], field).toBe(message);
      expect(hasFoodErrors(errors), field).toBe(true);
    }
  });

  it("rejects mismatched measurement dimensions", () => {
    expect(validateFoodForm({
      ...validFoodForm(),
      nutrition_basis: "per_100ml",
      unit_basis: "g"
    }).unit_basis).toBe("أساس الوحدة يجب أن يطابق أساس القيم الغذائية.");
  });

  it("maps Food conflicts, missing records, validation details, and unknown errors", () => {
    expect(mapFoodApiError(new ApiError("conflict", 409, undefined, "FOOD_MEASUREMENT_DIMENSION_IN_USE")))
      .toEqual({ form: "لا يمكن تغيير أساس القياس بين الوزن والحجم بعد تسجيل الطعام في اليومية." });
    expect(mapFoodApiError(new ApiError("missing", 404)))
      .toEqual({ form: "لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى." });
    expect(mapFoodApiError(new ApiError("invalid", 422, [
      { loc: ["body", "name"], msg: "اسم غير صالح" },
      { loc: ["body", "server_owned"], msg: "خطأ عام" },
    ]))).toEqual({ name: "اسم غير صالح", form: "خطأ عام" });
    expect(mapFoodApiError(new Error("network"))).toEqual({});
  });
});
