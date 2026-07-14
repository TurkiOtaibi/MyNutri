import type { FoodResponse, NutritionTotals, TargetResponse } from "./types";

export type NutrientTargetType = "minimum" | "maximum" | "range" | "monitor_only";
export type NutrientTargetSource = "fixed" | "calculated" | "reference" | "manual" | "clinical";
export type AdditionalNutrientKey = "fiber_g" | "sodium_mg" | "saturated_fat_g" | "added_sugar_g" | "potassium_mg" | "cholesterol_mg";

export interface NutrientDefinition {
  key: AdditionalNutrientKey;
  label: string;
  unit: "جم" | "ملجم";
  precision: number;
  order: number;
  targetType: NutrientTargetType;
  targetSource: NutrientTargetSource;
  targetValue: number | null;
  foodCompleteness: boolean;
  profileTargets: boolean;
  diaryDetails: boolean;
}

export const additionalNutrients: readonly NutrientDefinition[] = [
  { key: "fiber_g", label: "الألياف", unit: "جم", precision: 1, order: 1, targetType: "minimum", targetSource: "fixed", targetValue: 30, foodCompleteness: true, profileTargets: true, diaryDetails: true },
  { key: "sodium_mg", label: "الصوديوم", unit: "ملجم", precision: 0, order: 2, targetType: "maximum", targetSource: "reference", targetValue: null, foodCompleteness: true, profileTargets: true, diaryDetails: true },
  { key: "saturated_fat_g", label: "الدهون المشبعة", unit: "جم", precision: 1, order: 3, targetType: "maximum", targetSource: "reference", targetValue: null, foodCompleteness: true, profileTargets: true, diaryDetails: true },
  { key: "added_sugar_g", label: "السكر المضاف", unit: "جم", precision: 1, order: 4, targetType: "maximum", targetSource: "reference", targetValue: null, foodCompleteness: true, profileTargets: true, diaryDetails: true },
  { key: "potassium_mg", label: "البوتاسيوم", unit: "ملجم", precision: 0, order: 5, targetType: "minimum", targetSource: "reference", targetValue: null, foodCompleteness: true, profileTargets: true, diaryDetails: true },
  { key: "cholesterol_mg", label: "الكوليسترول", unit: "ملجم", precision: 0, order: 6, targetType: "monitor_only", targetSource: "reference", targetValue: null, foodCompleteness: true, profileTargets: true, diaryDetails: true }
] as const;

export function definitionsForTargets(targets: TargetResponse | null): NutrientDefinition[] {
  const api = new Map(targets?.additional_targets?.map((item) => [item.key, item]));
  return additionalNutrients.map((definition) => {
    const target = api.get(definition.key);
    return target ? { ...definition, targetType: target.target_type, targetSource: target.target_source, targetValue: target.target_value } : definition;
  });
}

export function nutrientValue(source: FoodResponse | NutritionTotals, key: AdditionalNutrientKey): number | null {
  const value = source[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatNutrientValue(value: number, precision: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: precision }).format(value);
}

export const targetTypeLabels: Record<NutrientTargetType, string> = {
  minimum: "حد أدنى",
  maximum: "حد أقصى",
  range: "نطاق مستهدف",
  monitor_only: "متابعة فقط"
};
