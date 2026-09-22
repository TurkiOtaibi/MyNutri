import { ApiError } from "@/lib/api";
import type { DefaultUnitType, FoodInput, FoodResponse } from "@/lib/types";

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
  primary_category: "other",
  subcategory: "other",
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
  notes: null,
  nutrition_data_source: "estimated",
  ingredients: null
};

const REQUIRED_MESSAGE = "هذا الحقل مطلوب.";
const INVALID_NUMBER_MESSAGE = "أدخل رقمًا صحيحًا.";
const BELOW_MIN_MESSAGE = "القيمة أقل من الحد المسموح.";
const ABOVE_MAX_MESSAGE = "القيمة أعلى من الحد المسموح.";

export const foodTextMax = {
  name: 120,
  brand: 80,
  notes: 500
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
  selenium_mcg: 9_999_999.999,
  vitamin_d_mcg: 250,
  vitamin_b12_mcg: 1000,
  vitamin_c_mg: 5000,
  vitamin_a_mcg: 3000,
  vitamin_a_rae_mcg: 9_999_999.999,
  folate_mcg: 2000,
  folate_dfe_mcg: 9_999_999.999,
  vitamin_k_mcg: 2000,
  iodine_mcg: 9_999_999.999
};

export function foodToForm(food: FoodResponse): FoodFormValues {
  return {
    name: food.name,
    brand: food.brand,
    primary_category: food.primary_category,
    subcategory: food.subcategory,
    nutrition_basis: food.nutrition_basis,
    default_unit_type: food.default_unit_type,
    unit_amount: food.unit_amount,
    unit_basis: food.unit_basis,
    calories: food.calories,
    protein_g: food.protein_g,
    carb_g: food.carb_g,
    fat_g: food.fat_g,
    fiber_g: food.fiber_g,
    sugar_g: food.sugar_g,
    added_sugar_g: food.added_sugar_g,
    saturated_fat_g: food.saturated_fat_g,
    trans_fat_g: food.trans_fat_g,
    sodium_mg: food.sodium_mg,
    cholesterol_mg: food.cholesterol_mg,
    potassium_mg: food.potassium_mg,
    calcium_mg: food.calcium_mg,
    iron_mg: food.iron_mg,
    magnesium_mg: food.magnesium_mg,
    zinc_mg: food.zinc_mg,
    selenium_mcg: food.selenium_mcg,
    vitamin_d_mcg: food.vitamin_d_mcg,
    vitamin_b12_mcg: food.vitamin_b12_mcg,
    vitamin_c_mg: food.vitamin_c_mg,
    vitamin_a_mcg: food.vitamin_a_mcg,
    vitamin_a_rae_mcg: food.vitamin_a_rae_mcg,
    folate_mcg: food.folate_mcg,
    folate_dfe_mcg: food.folate_dfe_mcg,
    vitamin_k_mcg: food.vitamin_k_mcg,
    iodine_mcg: food.iodine_mcg,
    notes: food.notes,
    nutrition_data_source: food.nutrition_data_source,
    ingredients: food.ingredients
  };
}

function cleanOptionalText(value: string | null): string | null {
  if (value == null) return null;
  const cleaned = value.trim().replace(/\s+/g, " ");
  return cleaned || null;
}

export function normalizeFoodForm(values: FoodFormValues): FoodInput {
  return {
    ...values,
    name: values.name.trim().replace(/\s+/g, " "),
    brand: cleanOptionalText(values.brand),
    notes: cleanOptionalText(values.notes),
    ingredients: cleanOptionalText(values.ingredients),
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

  for (const field of ["brand", "notes"] as const) {
    const value = cleanOptionalText(values[field]);
    if (value != null && value.length > foodTextMax[field]) errors[field] = ABOVE_MAX_MESSAGE;
  }
  if (!values.nutrition_basis) errors.nutrition_basis = REQUIRED_MESSAGE;
  if (!values.default_unit_type) errors.default_unit_type = REQUIRED_MESSAGE;
  if (!values.unit_basis) errors.unit_basis = REQUIRED_MESSAGE;
  const expectedUnitBasis = values.nutrition_basis === "per_100ml" ? "ml" : "g";
  if (values.nutrition_basis && values.unit_basis && values.unit_basis !== expectedUnitBasis) {
    errors.unit_basis = "أساس الوحدة يجب أن يطابق أساس القيم الغذائية.";
  }
  if (!values.primary_category) errors.primary_category = REQUIRED_MESSAGE;
  if (!values.subcategory) errors.subcategory = REQUIRED_MESSAGE;
  if (!values.nutrition_data_source) errors.nutrition_data_source = REQUIRED_MESSAGE;

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

const VALIDATION_ERROR = "راجع الحقول المحددة ثم حاول مرة أخرى.";

export function mapFoodApiError(error: unknown): FoodFormErrors {
  if (!(error instanceof ApiError)) return {};
  if (error.status === 404) return { form: "لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى." };
  if (error.status === 409 && error.code === "FOOD_MEASUREMENT_DIMENSION_IN_USE") {
    return { form: "لا يمكن تغيير أساس القياس بين الوزن والحجم بعد تسجيل الطعام في اليومية." };
  }
  if (error.status !== 422 || !Array.isArray(error.detail)) return {};

  const next: FoodFormErrors = {};
  for (const item of error.detail) {
    if (!item || typeof item !== "object") continue;
    const explicitField = "field" in item && typeof item.field === "string" ? item.field : undefined;
    const loc = "loc" in item && Array.isArray(item.loc) ? item.loc : [];
    const field = (explicitField ?? loc[loc.length - 1]) as keyof FoodFormValues | undefined;
    const msg = "msg" in item && typeof item.msg === "string" ? item.msg : VALIDATION_ERROR;
    if (field && field in emptyFoodForm) next[field] = msg;
    else next.form = msg;
  }
  return next;
}

export function fieldId(field: keyof FoodFormValues): string {
  return `food-${field.replaceAll("_", "-")}`;
}
