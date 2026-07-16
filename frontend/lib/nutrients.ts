import type { FoodResponse, NutrientTargetType, NutritionRegistryResponse, NutritionTotals, TargetResponse } from "./types";

export type AdditionalNutrientKey = string;

export interface NutrientDefinition {
  key: AdditionalNutrientKey;
  label: string;
  unit: string;
  precision: number;
  order: number;
  targetType: NutrientTargetType;
  targetSource: string;
  targetValue: number | null;
  foodCompleteness: boolean;
  profileTargets: boolean;
  diaryDetails: boolean;
}

function localizedUnit(unit: string): string {
  if (unit === "g") return "جم";
  if (unit === "mg") return "ملجم";
  if (unit === "mcg" || unit === "mcg_dfe" || unit === "mcg_rae") return "مكجم";
  return unit;
}

export function definitionsForTargets(targets: TargetResponse | null): NutrientDefinition[] {
  return (targets?.additional_targets ?? []).map((target) => ({
    key: target.key,
    label: target.label_ar,
    unit: localizedUnit(target.unit),
    precision: target.precision,
    order: target.order,
    targetType: target.target_type,
    targetSource: target.target_source,
    targetValue: target.target_value,
    foodCompleteness: true,
    profileTargets: true,
    diaryDetails: true
  }));
}

export function definitionsFromRegistry(registry: NutritionRegistryResponse): NutrientDefinition[] {
  return registry.nutrients.map((item) => ({
    key: item.key,
    label: item.label_ar,
    unit: localizedUnit(item.unit),
    precision: item.display_precision,
    order: item.display_order,
    targetType: item.target_type,
    targetSource: item.target_source,
    targetValue: null,
    foodCompleteness: item.completeness_participation,
    profileTargets: true,
    diaryDetails: item.diary_coverage_participation
  }));
}

export function nutrientValue(
  source: FoodResponse | NutritionTotals,
  key: AdditionalNutrientKey
): number | null {
  const value = (source as unknown as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatNutrientValue(value: number, precision: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: precision }).format(value);
}

export const targetTypeLabels: Record<NutrientTargetType, string> = {
  minimum: "حد أدنى",
  maximum: "حد أقصى",
  adequate: "كمية كافية",
  recommended: "كمية موصى بها",
  range: "نطاق مستهدف",
  monitor_only: "متابعة فقط",
  minimize: "يُفضّل التقليل"
};
