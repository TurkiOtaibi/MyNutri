import { describe, expect, it } from "vitest";

import { createFoodNutrientAdapter } from "@/features/foods/food-nutrients";
import type { NutritionRegistryResponse } from "@/lib/types";

const registryDefinitions = [
  ["added_sugar_g", 5, "g", 1],
  ["trans_fat_g", 10, "g", 1],
  ["saturated_fat_g", 15, "g", 1],
  ["fiber_g", 20, "registry-unit", 4],
  ["potassium_mg", 25, "mg", 0],
  ["sodium_mg", 30, "mcg", 2],
  ["cholesterol_mg", 35, "mg", 0],
  ["calcium_mg", 40, "mg", 0],
  ["iron_mg", 45, "mg", 0],
  ["magnesium_mg", 50, "mg", 0],
  ["zinc_mg", 55, "mg", 0],
  ["selenium_mcg", 60, "mcg", 0],
  ["folate_dfe_mcg", 65, "mcg_dfe", 3],
  ["vitamin_b12_mcg", 70, "mcg", 1],
  ["iodine_mcg", 75, "mcg", 0],
  ["vitamin_a_rae_mcg", 80, "mcg_rae", 0],
] as const;

function registry(): NutritionRegistryResponse {
  return {
    rules_manifest_hash: "a".repeat(64),
    calculation_policy: {},
    nutrients: [...registryDefinitions].reverse().map(([field, order, unit, precision]) => ({
      key: `registry-${field}`,
      storage_field: field,
      label_ar: `registry:${field}`,
      unit,
      display_precision: precision,
      display_order: order,
      target_type: "recommended",
      target_source: "registry",
      target_rule: {},
      completeness_participation: true,
      diary_coverage_participation: true,
    })),
    target_types: ["recommended"],
    primary_categories: ["other"],
    food_taxonomy: [{ key: "other", label_ar: "أخرى", subcategories: [{ key: "other", label_ar: "أخرى" }] }],
    nutrition_data_sources: [{ key: "official", label_ar: "رسمي" }],
  } as NutritionRegistryResponse;
}

describe("food nutrient presentation adapter", () => {
  it("derives registered editable labels, units, precision, and order from the Registry", () => {
    const registered = createFoodNutrientAdapter(registry()).editable
      .filter((item) => item.registryKey !== null);

    expect(registered.map((item) => item.field)).toEqual([
      "added_sugar_g",
      "trans_fat_g",
      "saturated_fat_g",
      "fiber_g",
      "potassium_mg",
      "sodium_mg",
      "cholesterol_mg",
      "calcium_mg",
      "iron_mg",
      "magnesium_mg",
      "zinc_mg",
      "selenium_mcg",
      "folate_dfe_mcg",
      "vitamin_b12_mcg",
      "iodine_mcg",
      "vitamin_a_rae_mcg",
    ]);
    expect(registered.find((item) => item.field === "fiber_g")).toEqual({
      field: "fiber_g",
      label: "registry:fiber_g",
      unit: "registry-unit",
      precision: 4,
      order: 20,
      registryKey: "registry-fiber_g",
    });
    expect(registered.find((item) => item.field === "sodium_mg")).toEqual({
      field: "sodium_mg",
      label: "registry:sodium_mg",
      unit: "mcg",
      precision: 2,
      order: 30,
      registryKey: "registry-sodium_mg",
    });
  });

  it("derives grouped detail metadata and registered order from the Registry", () => {
    const groups = createFoodNutrientAdapter(registry()).groups;
    const registeredIn = (title: string) => groups
      .find((group) => group.title === title)!
      .nutrients
      .filter((item) => item.registryKey !== null);

    expect(registeredIn("السكريات والدهون").map((item) => item.key)).toEqual([
      "added_sugar_g",
      "trans_fat_g",
      "saturated_fat_g",
      "cholesterol_mg",
    ]);
    expect(registeredIn("المعادن").map((item) => item.key)).toEqual([
      "potassium_mg",
      "sodium_mg",
      "calcium_mg",
      "iron_mg",
      "magnesium_mg",
      "zinc_mg",
      "selenium_mcg",
      "iodine_mcg",
    ]);
    expect(registeredIn("الفيتامينات").map((item) => item.key)).toEqual([
      "folate_dfe_mcg",
      "vitamin_b12_mcg",
      "vitamin_a_rae_mcg",
    ]);
    expect(registeredIn("المعادن").find((item) => item.key === "sodium_mg")).toEqual({
      key: "sodium_mg",
      label: "registry:sodium_mg",
      unit: "مكجم",
      precision: 2,
      order: 30,
      registryKey: "registry-sodium_mg",
    });
  });

  it("derives the established Food UI label variants from Registry Arabic labels", () => {
    const source = registry();
    const labels: Record<string, string> = {
      fiber_g: "الألياف",
      added_sugar_g: "السكر المضاف",
      vitamin_b12_mcg: "فيتامين ب12",
      folate_dfe_mcg: "الفولات (DFE)",
      vitamin_a_rae_mcg: "فيتامين أ (RAE)",
    };
    source.nutrients = source.nutrients.map((item) => ({
      ...item,
      label_ar: labels[item.storage_field] ?? item.label_ar,
    }));

    const adapter = createFoodNutrientAdapter(source);
    const editable = new Map(adapter.editable.map((item) => [item.field, item.label]));
    const details = new Map(adapter.groups.flatMap((group) => group.nutrients.map((item) => [item.key, item.label] as const)));

    expect(editable.get("fiber_g")).toBe("ألياف");
    expect(editable.get("added_sugar_g")).toBe("سكر مضاف");
    expect(editable.get("vitamin_b12_mcg")).toBe("فيتامين B12");
    expect(editable.get("folate_dfe_mcg")).toBe("فولات DFE");
    expect(editable.get("vitamin_a_rae_mcg")).toBe("فيتامين A RAE");
    expect(details.get("added_sugar_g")).toBe("السكر المضاف");
    expect(details.get("vitamin_b12_mcg")).toBe("فيتامين B12");
    expect(details.get("folate_dfe_mcg")).toBe("الفولات DFE");
    expect(details.get("vitamin_a_rae_mcg")).toBe("فيتامين A RAE");
  });

  it("keeps only core, calculated, and compatibility presentation outside the Registry", () => {
    const adapter = createFoodNutrientAdapter(registry());
    const compatibility = adapter.editable.filter((item) => item.registryKey === null);
    const core = adapter.groups[0].nutrients;

    expect(compatibility.map(({ field, label, unit, precision }) => [field, label, unit, precision])).toEqual([
      ["sugar_g", "إجمالي السكر", "g", 2],
      ["vitamin_d_mcg", "فيتامين D", "mcg", 2],
      ["vitamin_c_mg", "فيتامين C", "mg", 2],
      ["vitamin_k_mcg", "فيتامين K", "mcg", 2],
    ]);
    expect(core.filter((item) => item.registryKey === null).map(({ key, label, unit, precision }) => [key, label, unit, precision])).toEqual([
      ["calories", "السعرات", "سعرة", 2],
      ["protein_g", "البروتين", "جم", 2],
      ["carb_g", "الكربوهيدرات", "جم", 2],
      ["fat_g", "الدهون", "جم", 2],
      ["net_carbs_g", "صافي الكارب", "جم", 2],
    ]);
    expect(core.find((item) => item.key === "fiber_g")).toMatchObject({
      label: "registry:fiber_g",
      unit: "registry-unit",
      precision: 4,
      order: 20,
    });
  });

  it("lets Registry metadata replace a matching compatibility nutrient without duplication", () => {
    const source = registry();
    source.nutrients.push({
      key: "registry-sugar",
      storage_field: "sugar_g",
      label_ar: "سكر السجل",
      unit: "mg",
      display_precision: 3,
      display_order: 7,
      target_type: "recommended",
      target_source: "registry",
      target_rule: {},
      completeness_participation: true,
      diary_coverage_participation: true,
    });

    const adapter = createFoodNutrientAdapter(source);
    const editableSugar = adapter.editable.filter((item) => item.field === "sugar_g");
    const detailSugar = adapter.groups
      .flatMap((group) => group.nutrients)
      .filter((item) => item.key === "sugar_g");

    expect(editableSugar).toEqual([{
      field: "sugar_g",
      label: "سكر سجل",
      unit: "mg",
      precision: 3,
      order: 7,
      registryKey: "registry-sugar",
    }]);
    expect(detailSugar).toEqual([{
      key: "sugar_g",
      label: "سكر السجل",
      unit: "ملجم",
      precision: 3,
      order: 7,
      registryKey: "registry-sugar",
    }]);
  });
});
