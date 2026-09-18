import type { FoodResponse, NutrientTargetType, NutritionRegistryResponse, NutritionTotals } from "./types";

type AdditionalNutrientKey = string;

export interface NutrientDefinition {
  key: AdditionalNutrientKey;
  label: string;
  unit: string;
  precision: number;
  order: number;
  targetType: NutrientTargetType;
  targetValue: number | null;
  foodCompleteness: boolean;
}

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

const approvedTargetTypeMap = {
  minimum: true,
  maximum: true,
  adequate: true,
  recommended: true,
  range: true,
  monitor_only: true,
  minimize: true
} as const satisfies Record<NutrientTargetType, true>;

const approvedTargetTypeSet = new Set<NutrientTargetType>(
  Object.keys(approvedTargetTypeMap) as NutrientTargetType[]
);

function isNutrientTargetType(value: unknown): value is NutrientTargetType {
  return typeof value === "string" && approvedTargetTypeSet.has(value as NutrientTargetType);
}

function hasUniqueStrings(values: string[]): boolean {
  return new Set(values).size === values.length;
}

function isLabelDefinition(value: unknown): value is { key: string; label_ar: string } {
  return isObject(value) && isNonEmptyString(value.key) && isNonEmptyString(value.label_ar);
}

function isNutrientDefinition(value: unknown): boolean {
  return isObject(value)
    && isNonEmptyString(value.key)
    && isNonEmptyString(value.storage_field)
    && isNonEmptyString(value.label_ar)
    && isNonEmptyString(value.unit)
    && typeof value.display_precision === "number"
    && Number.isInteger(value.display_precision)
    && value.display_precision >= 0
    && typeof value.display_order === "number"
    && Number.isInteger(value.display_order)
    && isNutrientTargetType(value.target_type)
    && isNonEmptyString(value.target_source)
    && isObject(value.target_rule)
    && typeof value.completeness_participation === "boolean"
    && typeof value.diary_coverage_participation === "boolean";
}

/**
 * Validate registry structure at the API boundary without duplicating its
 * server-owned nutrient catalogue or relying on a numeric schema version.
 */
export function parseNutritionRegistry(value: unknown): NutritionRegistryResponse {
  if (!isObject(value)
    || !isNonEmptyString(value.rules_manifest_hash)
    || !/^[0-9a-f]{64}$/.test(value.rules_manifest_hash)
    || !isObject(value.calculation_policy)
    || !Array.isArray(value.nutrients)
    || value.nutrients.length === 0
    || !value.nutrients.every(isNutrientDefinition)
    || !Array.isArray(value.target_types)
    || value.target_types.length === 0
    || !value.target_types.every(isNutrientTargetType)
    || !Array.isArray(value.primary_categories)
    || value.primary_categories.length === 0
    || !value.primary_categories.every(isNonEmptyString)
    || !Array.isArray(value.food_taxonomy)
    || value.food_taxonomy.length === 0
    || !Array.isArray(value.nutrition_data_sources)
    || value.nutrition_data_sources.length === 0
    || !value.nutrition_data_sources.every(isLabelDefinition)) {
    throw new Error("Invalid nutrition registry structure");
  }

  const nutrients = value.nutrients as JsonObject[];
  const targetTypes = value.target_types as NutrientTargetType[];
  const primaryCategories = value.primary_categories as string[];
  const taxonomy = value.food_taxonomy;
  const dataSources = value.nutrition_data_sources as Array<{ key: string; label_ar: string }>;
  if (!hasUniqueStrings(nutrients.map((item) => item.key as string))
    || !hasUniqueStrings(nutrients.map((item) => item.storage_field as string))
    || !hasUniqueStrings(targetTypes)
    || !hasUniqueStrings(primaryCategories)
    || !hasUniqueStrings(dataSources.map((item) => item.key))
    || !nutrients.every((item) => targetTypes.includes(item.target_type as NutrientTargetType))) {
    throw new Error("Invalid nutrition registry definitions");
  }

  const taxonomyKeys: string[] = [];
  for (const item of taxonomy) {
    if (!isObject(item)
      || !isNonEmptyString(item.key)
      || !isNonEmptyString(item.label_ar)
      || !Array.isArray(item.subcategories)
      || item.subcategories.length === 0
      || !item.subcategories.every(isLabelDefinition)) {
      throw new Error("Invalid nutrition registry taxonomy");
    }
    const subcategories = item.subcategories as Array<{ key: string; label_ar: string }>;
    const childKeys = subcategories.map((child) => child.key);
    if (!hasUniqueStrings(childKeys)) {
      throw new Error("Duplicate nutrition registry taxonomy definition");
    }
    taxonomyKeys.push(item.key);
  }
  if (!hasUniqueStrings(taxonomyKeys)
    || taxonomyKeys.length !== primaryCategories.length
    || taxonomyKeys.some((key) => !primaryCategories.includes(key))) {
    throw new Error("Invalid nutrition registry category definitions");
  }

  return value as unknown as NutritionRegistryResponse;
}

function localizedUnit(unit: string): string {
  if (unit === "g") return "جم";
  if (unit === "mg") return "ملجم";
  if (unit === "mcg" || unit === "mcg_dfe" || unit === "mcg_rae") return "مكجم";
  return unit;
}

export function definitionsFromRegistry(registry: NutritionRegistryResponse): NutrientDefinition[] {
  return registry.nutrients.map((item) => ({
    key: item.key,
    label: item.label_ar,
    unit: localizedUnit(item.unit),
    precision: item.display_precision,
    order: item.display_order,
    targetType: item.target_type,
    targetValue: null,
    foodCompleteness: item.completeness_participation
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
