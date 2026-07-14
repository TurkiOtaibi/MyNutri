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
  vitamin_d_mcg: number | null;
  vitamin_b12_mcg: number | null;
  vitamin_c_mg: number | null;
  vitamin_a_mcg: number | null;
  folate_mcg: number | null;
  vitamin_k_mcg: number | null;
  net_carbs_g: number;
};

export type FoodFormValues = Omit<
  FoodInput,
  "calories" | "protein_g" | "carb_g" | "fat_g" | "unit_amount"
> & {
  calories: number | null;
  protein_g: number | null;
  carb_g: number | null;
  fat_g: number | null;
  unit_amount: number | null;
};

export type FoodFormErrors = Partial<Record<keyof FoodFormValues | "form", string>>;

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
  "vitamin_d_mcg",
  "vitamin_b12_mcg",
  "vitamin_c_mg",
  "vitamin_a_mcg",
  "folate_mcg",
  "vitamin_k_mcg"
] as const;

export const defaultUnitOptions: DefaultUnitType[] = [
  "g",
  "ml",
  "cup",
  "slice",
  "piece",
  "scoop",
  "serving",
  "tablespoon",
  "teaspoon"
];

export const emptyFoodForm: FoodFormValues = {
  name: "",
  brand: null,
  category: null,
  nutrition_basis: "per_100g",
  default_unit_type: "serving",
  unit_amount: 100,
  unit_basis: "g",
  calories: null,
  protein_g: null,
  carb_g: null,
  fat_g: null,
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
  vitamin_d_mcg: null,
  vitamin_b12_mcg: null,
  vitamin_c_mg: null,
  vitamin_a_mcg: null,
  folate_mcg: null,
  vitamin_k_mcg: null,
  notes: null,
  data_source: null
};

const REQUIRED_MESSAGE = "هذا الحقل مطلوب.";
const INVALID_NUMBER_MESSAGE = "أدخل رقمًا صحيحًا.";
const BELOW_MIN_MESSAGE = "القيمة أقل من الحد المسموح.";
const ABOVE_MAX_MESSAGE = "القيمة أعلى من الحد المسموح.";

export const foodTextMax = {
  name: 120,
  brand: 80,
  category: 80,
  notes: 500,
  data_source: 120
} as const satisfies Partial<Record<keyof FoodFormValues, number>>;

const optionalMax: Partial<Record<keyof FoodFormValues, number>> = {
  fiber_g: 100,
  sugar_g: 100,
  added_sugar_g: 100,
  saturated_fat_g: 100,
  trans_fat_g: 100,
  sodium_mg: 50000,
  cholesterol_mg: 2000,
  potassium_mg: 10000,
  calcium_mg: 5000,
  iron_mg: 100,
  magnesium_mg: 1000,
  zinc_mg: 100,
  vitamin_d_mcg: 250,
  vitamin_b12_mcg: 1000,
  vitamin_c_mg: 5000,
  vitamin_a_mcg: 3000,
  folate_mcg: 2000,
  vitamin_k_mcg: 2000
};

export function foodToForm(food: FoodResponse): FoodFormValues {
  return {
    ...emptyFoodForm,
    ...food
  };
}

export function cleanOptionalText(value: string | null): string | null {
  if (value == null) return null;
  const cleaned = value.trim().replace(/\s+/g, " ");
  return cleaned || null;
}

export function normalizeFoodForm(values: FoodFormValues): FoodInput {
  return {
    ...values,
    name: values.name.trim().replace(/\s+/g, " "),
    brand: cleanOptionalText(values.brand),
    category: cleanOptionalText(values.category),
    notes: cleanOptionalText(values.notes),
    data_source: cleanOptionalText(values.data_source),
    calories: values.calories ?? 0,
    protein_g: values.protein_g ?? 0,
    carb_g: values.carb_g ?? 0,
    fat_g: values.fat_g ?? 0,
    unit_amount: values.unit_amount ?? 0
  };
}

function validateNumber(
  errors: FoodFormErrors,
  values: FoodFormValues,
  field: keyof FoodFormValues,
  options: { required?: boolean; min?: number; max?: number }
) {
  const value = values[field];
  if (value == null || value === "") {
    if (options.required) errors[field] = REQUIRED_MESSAGE;
    return;
  }
  if (typeof value !== "number" || Number.isNaN(value)) {
    errors[field] = INVALID_NUMBER_MESSAGE;
    return;
  }
  if (options.min != null && value < options.min) {
    errors[field] = BELOW_MIN_MESSAGE;
    return;
  }
  if (options.max != null && value > options.max) {
    errors[field] = ABOVE_MAX_MESSAGE;
  }
}

export function validateFoodForm(values: FoodFormValues): FoodFormErrors {
  const errors: FoodFormErrors = {};
  const normalizedName = values.name.trim().replace(/\s+/g, " ");
  if (!normalizedName) errors.name = REQUIRED_MESSAGE;
  else if (normalizedName.length > foodTextMax.name) errors.name = ABOVE_MAX_MESSAGE;

  for (const field of ["brand", "category", "notes", "data_source"] as const) {
    const value = cleanOptionalText(values[field]);
    if (value != null && value.length > foodTextMax[field]) errors[field] = ABOVE_MAX_MESSAGE;
  }
  if (!values.nutrition_basis) errors.nutrition_basis = REQUIRED_MESSAGE;
  if (!values.default_unit_type) errors.default_unit_type = REQUIRED_MESSAGE;
  if (!values.unit_basis) errors.unit_basis = REQUIRED_MESSAGE;

  validateNumber(errors, values, "unit_amount", { required: true, min: 1, max: 2000 });
  validateNumber(errors, values, "calories", { required: true, min: 0, max: 3000 });
  validateNumber(errors, values, "protein_g", { required: true, min: 0, max: 300 });
  validateNumber(errors, values, "carb_g", { required: true, min: 0, max: 500 });
  validateNumber(errors, values, "fat_g", { required: true, min: 0, max: 300 });

  for (const [field, max] of Object.entries(optionalMax) as [keyof FoodFormValues, number][]) {
    validateNumber(errors, values, field, { min: 0, max });
  }

  if (values.fiber_g != null && values.carb_g != null && values.fiber_g > values.carb_g) {
    errors.fiber_g = "الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.";
  }
  if (values.added_sugar_g != null && values.sugar_g != null && values.added_sugar_g > values.sugar_g) {
    errors.added_sugar_g = "السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.";
  }
  if (values.saturated_fat_g != null && values.fat_g != null && values.saturated_fat_g > values.fat_g) {
    errors.saturated_fat_g = "الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.";
  }
  if (values.trans_fat_g != null && values.fat_g != null && values.trans_fat_g > values.fat_g) {
    errors.trans_fat_g = "الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.";
  }
  if (
    values.saturated_fat_g != null &&
    values.trans_fat_g != null &&
    values.fat_g != null &&
    values.saturated_fat_g + values.trans_fat_g > values.fat_g
  ) {
    errors.trans_fat_g = "مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.";
  }

  return errors;
}

export function hasFoodErrors(errors: FoodFormErrors): boolean {
  return Object.keys(errors).length > 0;
}

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
    vitamin_d_mcg: null,
    vitamin_b12_mcg: null,
    vitamin_c_mg: null,
    vitamin_a_mcg: null,
    folate_mcg: null,
    vitamin_k_mcg: null,
    net_carbs_g: scale(food.net_carbs_g) ?? 0
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

export function formatNutrientNumber(value: number): string {
  return formatNumber(value, 2);
}

function formatNumber(value: number, maximumFractionDigits: number): string {
  return new Intl.NumberFormat("ar-SA-u-nu-latn", {
    maximumFractionDigits,
    useGrouping: false
  }).format(value);
}

export function formatOptionalValue(value: number | null | undefined, unit: string): string {
  return value == null ? "-" : `${value} ${unit}`;
}
