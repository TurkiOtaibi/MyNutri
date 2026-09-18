import type { DefaultUnitType, FoodInput, FoodResponse, NutritionBasis, UnitBasis } from "./types";

export type FoodNutritionValues = {
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  added_sugar_g: number | null;
  saturated_fat_g: number | null;
  trans_fat_g: number | null;
  sodium_mg: number | null;
  cholesterol_mg: number | null;
  potassium_mg: number | null;
  calcium_mg: number | null;
  iron_mg: number | null;
  magnesium_mg: number | null;
  zinc_mg: number | null;
  selenium_mcg: number | null;
  vitamin_d_mcg: number | null;
  vitamin_b12_mcg: number | null;
  vitamin_c_mg: number | null;
  vitamin_a_mcg: number | null;
  vitamin_a_rae_mcg: number | null;
  folate_mcg: number | null;
  folate_dfe_mcg: number | null;
  vitamin_k_mcg: number | null;
  iodine_mcg: number | null;
  net_carbs_g: number | null;
};

export const nutritionBasisLabels: Record<NutritionBasis, string> = {
  per_100g: "لكل 100 جم",
  per_100ml: "لكل 100 مل"
};

export const defaultUnitLabels: Record<DefaultUnitType, string> = {
  g: "جم",
  ml: "مل",
  cup: "كوب",
  slice: "شريحة",
  piece: "قطعة",
  scoop: "مكيال",
  serving: "حصة",
  tablespoon: "ملعقة كبيرة",
  teaspoon: "ملعقة صغيرة"
};

export const unitBasisLabels: Record<UnitBasis, string> = {
  g: "جم",
  ml: "مل"
};

const defaultServingLabels: Record<DefaultUnitType, string> = {
  g: "جرام",
  ml: "ملليلتر",
  cup: "كوب واحد",
  slice: "شريحة واحدة",
  piece: "قطعة واحدة",
  scoop: "مكيال واحد",
  serving: "حصة واحدة",
  tablespoon: "ملعقة كبيرة",
  teaspoon: "ملعقة صغيرة"
};

const optionalNutritionFields = [
  "fiber_g",
  "sugar_g",
  "added_sugar_g",
  "saturated_fat_g",
  "trans_fat_g",
  "sodium_mg",
  "cholesterol_mg",
  "potassium_mg",
  "calcium_mg",
  "iron_mg",
  "magnesium_mg",
  "zinc_mg",
  "selenium_mcg",
  "vitamin_d_mcg",
  "vitamin_b12_mcg",
  "vitamin_c_mg",
  "vitamin_a_mcg",
  "vitamin_a_rae_mcg",
  "folate_mcg",
  "folate_dfe_mcg",
  "vitamin_k_mcg",
  "iodine_mcg"
] as const;

export function defaultUnitText(food: Pick<FoodInput, "default_unit_type" | "unit_amount" | "unit_basis">): string {
  return `1 ${defaultUnitLabels[food.default_unit_type]} = ${food.unit_amount} ${unitBasisLabels[food.unit_basis]}`;
}

export function defaultServingText(
  food: Pick<FoodInput, "default_unit_type" | "unit_amount" | "unit_basis">
): string {
  const amount = formatNumber(food.unit_amount, 2);
  const basis = unitBasisLabels[food.unit_basis];
  if (food.default_unit_type === "g" || food.default_unit_type === "ml") {
    return `${amount} ${basis}`;
  }
  return `${defaultServingLabels[food.default_unit_type]} · ${amount} ${basis}`;
}

export function calculateServingNutrition(food: FoodResponse): FoodNutritionValues | null {
  const factor = Number(food.unit_amount) / 100;
  if (!Number.isFinite(factor) || factor <= 0) return null;

  const scale = (value: number | null | undefined): number | null => {
    if (value == null) return null;
    const result = Number(value) * factor;
    return Number.isFinite(result) ? Math.round(result * 10_000) / 10_000 : null;
  };

  const result: FoodNutritionValues = {
    calories: scale(food.calories) ?? 0,
    protein_g: scale(food.protein_g) ?? 0,
    carb_g: scale(food.carb_g) ?? 0,
    fat_g: scale(food.fat_g) ?? 0,
    fiber_g: null,
    sugar_g: null,
    added_sugar_g: null,
    saturated_fat_g: null,
    trans_fat_g: null,
    sodium_mg: null,
    cholesterol_mg: null,
    potassium_mg: null,
    calcium_mg: null,
    iron_mg: null,
    magnesium_mg: null,
    zinc_mg: null,
    selenium_mcg: null,
    vitamin_d_mcg: null,
    vitamin_b12_mcg: null,
    vitamin_c_mg: null,
    vitamin_a_mcg: null,
    vitamin_a_rae_mcg: null,
    folate_mcg: null,
    folate_dfe_mcg: null,
    vitamin_k_mcg: null,
    iodine_mcg: null,
    net_carbs_g: scale(food.net_carbs_g)
  };

  for (const field of optionalNutritionFields) result[field] = scale(food[field]);
  return result;
}

export function perBasisNutrition(food: FoodResponse): FoodNutritionValues {
  const values = calculateServingNutrition({ ...food, unit_amount: 100 });
  if (!values) throw new Error("Food nutrition values are unavailable.");
  return values;
}

export function formatServingCalories(value: number): string {
  return formatNumber(Math.round(value), 0);
}

export function formatServingMacro(value: number): string {
  return formatNumber(Math.round(value * 10) / 10, 1);
}

export function formatNutrientNumber(value: number, maximumFractionDigits = 2): string {
  return formatNumber(value, maximumFractionDigits);
}

function formatNumber(value: number, maximumFractionDigits: number): string {
  return new Intl.NumberFormat("ar-SA-u-nu-latn", {
    maximumFractionDigits,
    useGrouping: false
  }).format(value);
}
