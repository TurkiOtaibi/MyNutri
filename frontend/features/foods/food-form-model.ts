import { ApiError } from "@/lib/api";
import { emptyFoodForm, type FoodFormErrors, type FoodFormValues } from "@/lib/food";

const VALIDATION_ERROR = "راجع الحقول المحددة ثم حاول مرة أخرى.";

export const optionalFields: (keyof FoodFormValues)[] = [
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
  "vitamin_a_rae_mcg",
  "folate_dfe_mcg",
  "vitamin_k_mcg",
  "iodine_mcg"
];

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

export function fieldId(label: string): string {
  return `food-${label.replace(/\s+/g, "-")}`;
}
