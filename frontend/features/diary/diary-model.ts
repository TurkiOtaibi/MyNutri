import { formatLongArabicDate } from "@/lib/dates";
import { defaultUnitLabels, formatServingMacro, unitBasisLabels } from "@/lib/food";
import type { DiaryDayStatusResponse, DiaryEntryResponse, DiaryLoggingStatus, FoodPickerItem, MealType, NutritionSnapshot, NutritionTotals } from "@/lib/types";

export const dayLoggingStatusLabels: Record<DiaryLoggingStatus, string> = {
  unregistered: "غير مسجل",
  partial: "التسجيل غير مكتمل",
  complete: "تم تسجيل اليوم"
};

export function isDayAnalysisEligible(status: DiaryLoggingStatus): boolean {
  return status === "complete";
}

export function isFutureDiaryStatus(status: DiaryDayStatusResponse): boolean {
  return status.date > status.calendar.current_diary_date;
}

export const mealLabels: Record<MealType, string> = {
  breakfast: "فطور",
  lunch: "غداء",
  dinner: "عشاء",
  snack: "سناك",
  unspecified: "غير مصنف"
};
export const standardMeals: MealType[] = ["breakfast", "lunch", "dinner", "snack"];
export const shortWeekdays = ["أحد", "اثن", "ثلا", "أرب", "خمي", "جمع", "سبت"];
export const mealAddLabels: Record<Exclude<MealType, "unspecified">, string> = {
  breakfast: "إضافة إلى الفطور",
  lunch: "إضافة إلى الغداء",
  dinner: "إضافة إلى العشاء",
  snack: "إضافة إلى السناك"
};

export function mealItemCountLabel(count: number): string {
  if (count === 0) return "لا توجد أطعمة";
  if (count === 1) return "طعام واحد";
  if (count === 2) return "طعامان";
  if (count >= 3 && count <= 10) return `${count} أطعمة`;
  return `${count} طعامًا`;
}

export function emptyNutritionTotals(): NutritionTotals {
  return {
    calories: 0, protein_g: 0, carb_g: 0, fat_g: 0, net_carbs_g: 0,
    saturated_fat_g: null, trans_fat_g: null, cholesterol_mg: null, sodium_mg: null,
    fiber_g: null, sugar_g: null, added_sugar_g: null, potassium_mg: null, calcium_mg: null,
    iron_mg: null, magnesium_mg: null, zinc_mg: null, selenium_mcg: null,
    vitamin_d_mcg: null, vitamin_b12_mcg: null, vitamin_c_mg: null,
    vitamin_a_mcg: null, vitamin_a_rae_mcg: null, folate_mcg: null,
    folate_dfe_mcg: null, vitamin_k_mcg: null, iodine_mcg: null
  };
}

export function formatDiarySelectedDate(input: string, today: string): string {
  const full = formatLongArabicDate(input);
  return input.slice(0, 4) === today.slice(0, 4) ? full.replace(/\s\d{4}$/, "") : full;
}

export function pickerServingNutrition(food: FoodPickerItem) {
  const factor = Number(food.unit_amount) / 100;
  if (!Number.isFinite(factor) || factor <= 0) return null;
  return {
    calories: Number(food.calories) * factor,
    protein_g: Number(food.protein_g) * factor,
    carb_g: Number(food.carb_g) * factor,
    fat_g: Number(food.fat_g) * factor
  };
}

export function multiplyServing(food: FoodPickerItem, quantity: number) {
  const serving = pickerServingNutrition(food);
  if (!serving) return null;
  return {
    calories: serving.calories * quantity,
    protein_g: serving.protein_g * quantity,
    carb_g: serving.carb_g * quantity,
    fat_g: serving.fat_g * quantity
  };
}

export function scaleEntryPreview(entry: DiaryEntryResponse, quantity: number) {
  const factor = quantity / entry.quantity;
  return {
    calories: entry.totals.calories * factor,
    protein_g: entry.totals.protein_g * factor,
    carb_g: entry.totals.carb_g * factor,
    fat_g: entry.totals.fat_g * factor
  };
}

export function parseQuantity(value: string): number | null {
  const trimmed = value.trim();
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return null;
  const amount = Number(trimmed);
  return Number.isFinite(amount) && amount >= 0.01 && amount <= 50 ? amount : null;
}

export function validateQuantity(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "أدخل كمية صحيحة";
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return "أدخل كمية صحيحة";
  const amount = Number(trimmed);
  if (!Number.isFinite(amount)) return "أدخل كمية صحيحة";
  if (amount < 0.01) return "أدخل كمية أكبر من 0";
  if (amount > 50) return "الكمية يجب ألا تتجاوز 50 حصة";
  return "";
}

export function entryQuantityLabel(entry: DiaryEntryResponse): string {
  const snapshot = entry.nutrition_snapshot;
  const unit = snapshot.default_unit_type ? defaultUnitLabels[snapshot.default_unit_type] : "حصة";
  const basis = snapshot.unit_basis ? unitBasisLabels[snapshot.unit_basis] : "جم";
  const amount = snapshot.unit_amount ? Number(snapshot.unit_amount) * entry.quantity : null;
  return amount ? `${formatServingMacro(entry.quantity)} ${unit} · ${formatServingMacro(amount)} ${basis}` : `${formatServingMacro(entry.quantity)} ${snapshotUnitLabel(snapshot)}`;
}

export function snapshotUnitLabel(snapshot: NutritionSnapshot): string {
  if (snapshot.default_unit_type && snapshot.unit_amount && snapshot.unit_basis) {
    return `${defaultUnitLabels[snapshot.default_unit_type]} (${snapshot.unit_amount} ${unitBasisLabels[snapshot.unit_basis]})`;
  }
  return snapshot.serving_label ?? "حصة";
}
