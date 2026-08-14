import { ApiError } from "@/lib/api";
import { emptyFoodForm, type FoodFormErrors, type FoodFormValues } from "@/lib/food";
import type { NutritionRegistryResponse } from "@/lib/types";

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
  if (error.status !== 422 || !Array.isArray(error.detail)) return {};

  const next: FoodFormErrors = {};
  for (const item of error.detail) {
    if (!item || typeof item !== "object") continue;
    const explicitField = "field" in item && typeof item.field === "string" ? item.field : undefined;
    const loc = "loc" in item && Array.isArray(item.loc) ? item.loc : [];
    const field = (explicitField ?? loc[loc.length - 1]) as keyof FoodFormValues | undefined;
    const msg = "msg" in item && typeof item.msg === "string" ? item.msg : VALIDATION_ERROR;
    const code = "code" in item && typeof item.code === "string" ? item.code : "";
    if (code.startsWith("source_")) next.nutrition_source = msg;
    else if (code.startsWith("ingredients_")) next.ingredients = msg;
    else if (code.includes("food_group") || code.includes("group_data")) next.group_contributions = msg;
    else if (code.includes("analytical_trait")) next.analytical_traits = msg;
    else if (field && field in emptyFoodForm) next[field] = msg;
    else next.form = msg;
  }
  return next;
}

export const traitGroups = [
  { label: "المنشأ", keys: ["omega3_rich_seafood", "fruit_liquid_100_percent", "dried_fruit", "starchy_root"] },
  { label: "المعالجة", keys: ["processed", "smoked", "salted"] },
  { label: "الخصائص الغذائية", keys: ["sweetened", "non_nutritive_sweetened", "calcium_fortified", "unsaturated_fat_source"] }
];

export const traitHelp: Record<string, string> = {
  non_nutritive_sweetened: "يحتوي على مُحلٍ لا يضيف سكرًا غذائيًا.",
  omega3_rich_seafood: "صفة تحليلية للمأكولات البحرية المثبت غناها بأوميغا 3.",
  fruit_liquid_100_percent: "عصير أو سموذي فواكه كامل دون تخمين من الاسم."
};

export function relevantTraitKeys(category: string): string[] {
  if (category === "seafood") return ["omega3_rich_seafood"];
  if (category === "dairy_fortified_alternatives") return ["calcium_fortified"];
  if (category === "fruits") return ["fruit_liquid_100_percent", "dried_fruit"];
  if (["nuts_seeds", "added_oils_fats"].includes(category)) return ["unsaturated_fat_source"];
  if (["sweets", "sugar_sweetened_beverages"].includes(category)) return ["sweetened", "non_nutritive_sweetened"];
  if (["processed_meat", "red_meat"].includes(category)) return ["processed", "smoked", "salted"];
  return [];
}

export function suggestedGroupKey(form: FoodFormValues): string | null {
  if (["baked_goods", "grains_starches"].includes(form.food_category_key)) {
    if (form.grain_type === "whole") return "whole_grains";
    if (form.grain_type === "refined") return "refined_grains";
    return null;
  }
  const direct = new Set(["vegetables", "fruits", "legumes", "nuts_seeds", "seafood", "dairy_fortified_alternatives", "eggs", "poultry", "red_meat", "processed_meat", "added_oils_fats", "sweets", "sugar_sweetened_beverages", "unsweetened_beverages", "mixed_dish"]);
  return direct.has(form.food_category_key) ? form.food_category_key : null;
}

export function subtypeKeys(definition: NutritionRegistryResponse["food_group_definitions"][number] | undefined): string[] {
  if (!definition?.subtypes) return [];
  return Array.isArray(definition.subtypes) ? definition.subtypes : Object.keys(definition.subtypes);
}

export function fieldId(label: string): string {
  return `food-${label.replace(/\s+/g, "-")}`;
}
