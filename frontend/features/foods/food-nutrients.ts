import type { FoodFormValues, FoodNutritionValues } from "@/lib/food";
import { definitionsFromRegistry } from "@/lib/nutrients";
import type { NutritionRegistryResponse } from "@/lib/types";

type OptionalFoodNutrientField = Extract<keyof FoodFormValues, keyof FoodNutritionValues>;
type FoodNutrientGroupKey = "sugar-fat" | "minerals" | "vitamins";

interface EditableFoodNutrient {
  field: OptionalFoodNutrientField;
  label: string;
  unit: string;
  precision: number;
  order: number;
  registryKey: string | null;
}

export interface FoodNutrientSpec {
  key: keyof FoodNutritionValues;
  label: string;
  unit: string;
  precision: number;
  order: number;
  registryKey: string | null;
}

interface FoodNutrientGroup {
  title: string;
  optional: boolean;
  nutrients: FoodNutrientSpec[];
}

interface FoodNutrientAdapter {
  editable: EditableFoodNutrient[];
  groups: FoodNutrientGroup[];
}

interface NutrientPlacement {
  field: OptionalFoodNutrientField;
  group: FoodNutrientGroupKey;
}

interface CompatibilityNutrient extends NutrientPlacement {
  label: string;
  inputUnit: string;
  detailUnit: string;
  precision: number;
  order: number;
}

const nutrientPlacements = [
  { field: "fiber_g", group: "sugar-fat" },
  { field: "sugar_g", group: "sugar-fat" },
  { field: "added_sugar_g", group: "sugar-fat" },
  { field: "saturated_fat_g", group: "sugar-fat" },
  { field: "trans_fat_g", group: "sugar-fat" },
  { field: "sodium_mg", group: "minerals" },
  { field: "cholesterol_mg", group: "sugar-fat" },
  { field: "potassium_mg", group: "minerals" },
  { field: "calcium_mg", group: "minerals" },
  { field: "iron_mg", group: "minerals" },
  { field: "magnesium_mg", group: "minerals" },
  { field: "zinc_mg", group: "minerals" },
  { field: "selenium_mcg", group: "minerals" },
  { field: "vitamin_d_mcg", group: "vitamins" },
  { field: "vitamin_b12_mcg", group: "vitamins" },
  { field: "vitamin_c_mg", group: "vitamins" },
  { field: "vitamin_a_rae_mcg", group: "vitamins" },
  { field: "folate_dfe_mcg", group: "vitamins" },
  { field: "vitamin_k_mcg", group: "vitamins" },
  { field: "iodine_mcg", group: "minerals" },
] as const satisfies readonly NutrientPlacement[];

const compatibilityNutrients = [
  { field: "sugar_g", label: "إجمالي السكر", inputUnit: "g", detailUnit: "جم", precision: 2, order: 1.5, group: "sugar-fat" },
  { field: "vitamin_d_mcg", label: "فيتامين D", inputUnit: "mcg", detailUnit: "مكجم", precision: 2, order: 12.5, group: "vitamins" },
  { field: "vitamin_c_mg", label: "فيتامين C", inputUnit: "mg", detailUnit: "ملجم", precision: 2, order: 13.5, group: "vitamins" },
  { field: "vitamin_k_mcg", label: "فيتامين K", inputUnit: "mcg", detailUnit: "مكجم", precision: 2, order: 15.5, group: "vitamins" },
] as const satisfies readonly CompatibilityNutrient[];

const fixedCoreNutrients: FoodNutrientSpec[] = [
  { key: "calories", label: "السعرات", unit: "سعرة", precision: 2, order: 0, registryKey: null },
  { key: "protein_g", label: "البروتين", unit: "جم", precision: 2, order: 0, registryKey: null },
  { key: "carb_g", label: "الكربوهيدرات", unit: "جم", precision: 2, order: 0, registryKey: null },
  { key: "fat_g", label: "الدهون", unit: "جم", precision: 2, order: 0, registryKey: null },
];

const calculatedNutrients: FoodNutrientSpec[] = [
  { key: "net_carbs_g", label: "صافي الكارب", unit: "جم", precision: 2, order: 0, registryKey: null },
];

const groupDefinitions: Array<{ key: FoodNutrientGroupKey; title: string }> = [
  { key: "sugar-fat", title: "السكريات والدهون" },
  { key: "minerals", title: "المعادن" },
  { key: "vitamins", title: "الفيتامينات" },
];

const placementByField = new Map<string, NutrientPlacement>(
  nutrientPlacements.map((item) => [item.field, item]),
);

function isOptionalFoodNutrientField(field: string): field is OptionalFoodNutrientField {
  return placementByField.has(field);
}

function inputUnit(unit: string): string {
  if (unit === "mcg_dfe" || unit === "mcg_rae") return "mcg";
  return unit;
}

function foodDetailLabel(label: string): string {
  return label
    .replace(/\(([A-Z][A-Z0-9]*)\)/g, "$1")
    .replace(/ب(?=\d)/g, "B")
    .replace(/أ(?=\s+RAE\b)/g, "A");
}

function foodInputLabel(label: string): string {
  return foodDetailLabel(label)
    .split(" ")
    .map((word) => word.startsWith("ال") ? word.slice(2) : word)
    .join(" ");
}

function byOrder<T extends { order: number }>(left: T, right: T): number {
  return left.order - right.order;
}

export function createFoodNutrientAdapter(registry?: NutritionRegistryResponse | null): FoodNutrientAdapter {
  const definitionByKey = new Map(
    registry ? definitionsFromRegistry(registry).map((item) => [item.key, item]) : [],
  );
  const registered = (registry?.nutrients ?? [])
    .filter((item) => isOptionalFoodNutrientField(item.storage_field))
    .map((item) => {
      const field = item.storage_field as OptionalFoodNutrientField;
      const placement = placementByField.get(field)!;
      const definition = definitionByKey.get(item.key)!;
      return {
        group: placement.group,
        editable: {
          field,
          label: foodInputLabel(item.label_ar),
          unit: inputUnit(item.unit),
          precision: item.display_precision,
          order: item.display_order,
          registryKey: item.key,
        } satisfies EditableFoodNutrient,
        detail: {
          key: field,
          label: foodDetailLabel(definition.label),
          unit: definition.unit,
          precision: definition.precision,
          order: definition.order,
          registryKey: item.key,
        } satisfies FoodNutrientSpec,
      };
    })
    .sort((left, right) => byOrder(left.editable, right.editable));

  const registeredFields = new Set(registered.map((item) => item.editable.field));
  const compatibility = compatibilityNutrients
    .filter((item) => !registeredFields.has(item.field))
    .map((item) => ({
      group: item.group,
      editable: {
        field: item.field,
        label: item.label,
        unit: item.inputUnit,
        precision: item.precision,
        order: item.order,
        registryKey: null,
      } satisfies EditableFoodNutrient,
      detail: {
        key: item.field,
        label: item.label,
        unit: item.detailUnit,
        precision: item.precision,
        order: item.order,
        registryKey: null,
      } satisfies FoodNutrientSpec,
    }));
  const all = [...registered, ...compatibility];
  const fiber = registered.find((item) => item.editable.field === "fiber_g")?.detail;

  return {
    editable: all.map((item) => item.editable).sort(byOrder),
    groups: [
      {
        title: "القيم الأساسية",
        optional: false,
        nutrients: [...fixedCoreNutrients, ...(fiber ? [fiber] : []), ...calculatedNutrients],
      },
      ...groupDefinitions.map(({ key, title }) => ({
        title,
        optional: true,
        nutrients: all
          .filter((item) => item.group === key && item.editable.field !== "fiber_g")
          .map((item) => item.detail)
          .sort(byOrder),
      })),
    ],
  };
}
