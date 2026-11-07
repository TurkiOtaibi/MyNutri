import { expect, it } from "vitest";
import { emptyFoodForm, foodFormFingerprint, normalizeFoodForm, validateFoodForm, type FoodFormValues } from "@/features/foods/food-form-model";

it("normalizes localized raw Food drafts only at the API boundary", () => {
  const draft = { ...emptyFoodForm, name: "طعام", calories: "١٢٫٥", protein_g: "۰", carb_g: "10", fat_g: "2", fiber_g: "", sodium_mg: "٠" } as unknown as FoodFormValues;
  expect(validateFoodForm(draft)).toEqual({});
  expect(normalizeFoodForm(draft)).toMatchObject({ calories: 12.5, protein_g: 0, fiber_g: null, sodium_mg: 0 });
  expect(draft.calories).toBe("١٢٫٥");
});

it("rejects malformed optional numbers instead of saving them as unknown or zero", () => {
  const draft = { ...emptyFoodForm, sodium_mg: "١٬٢٥٠", calories: "." } as unknown as FoodFormValues;
  expect(validateFoodForm(draft).sodium_mg).toBe("أدخل رقمًا صحيحًا.");
  expect(validateFoodForm(draft).calories).toBe("أدخل رقمًا صحيحًا.");
});

it("returns numeric and unknown drafts to a clean semantic baseline", () => {
  const baseline = foodFormFingerprint(emptyFoodForm);
  expect(foodFormFingerprint({ ...emptyFoodForm, unit_amount: "101" })).not.toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, unit_amount: "100" })).toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, unit_amount: "١٠٠٫٠٠" })).toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "5" })).not.toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "" })).toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "  " })).toBe(baseline);
  expect(foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "0" })).not.toBe(baseline);
});

it("keeps malformed drafts distinct from unknown and from each other", () => {
  const malformed = foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "." });
  expect(malformed).not.toBe(foodFormFingerprint(emptyFoodForm));
  expect(malformed).not.toBe(foodFormFingerprint({ ...emptyFoodForm, sodium_mg: "١٬٠" }));
});
