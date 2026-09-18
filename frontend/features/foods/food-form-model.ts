import { ApiError } from "@/lib/api";
import { emptyFoodForm, type FoodFormErrors, type FoodFormValues } from "@/lib/food";

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

export function fieldId(label: string): string {
  return `food-${label.replace(/\s+/g, "-")}`;
}
