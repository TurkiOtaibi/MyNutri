import { describe, expect, it } from "vitest";

import {
  definitionsForTargets,
  definitionsFromRegistry,
  formatNutrientValue,
  nutrientValue,
  parseNutritionRegistry
} from "@/lib/nutrients";

describe("nutrient definitions and values", () => {
  it("maps target metadata while preserving nullable targets", () => {
    const definitions = definitionsForTargets({
      calories: 2000,
      protein_g: 100,
      carb_g: 250,
      fat_g: 70,
      additional_targets: [{
        key: "sodium_mg",
        label_ar: "الصوديوم",
        unit: "mg",
        precision: 0,
        order: 4,
        target_type: "maximum",
        target_source: "profile",
        target_value: null
      }]
    } as never);

    expect(definitions).toHaveLength(1);
    expect(definitions[0]).toMatchObject({
      key: "sodium_mg",
      precision: 0,
      order: 4,
      targetType: "maximum",
      targetValue: null
    });
  });

  it("maps registry coverage and localizes known units", () => {
    const registry = {
      rules_manifest_hash: "a".repeat(64),
      calculation_policy: {},
      nutrients: [{
        key: "vitamin_c_mg",
        storage_field: "vitamin_c_mg",
        label_ar: "فيتامين ج",
        unit: "mg",
        display_precision: 1,
        display_order: 8,
        target_type: "recommended",
        target_source: "registry",
        target_rule: {},
        completeness_participation: true,
        diary_coverage_participation: false
      }],
      target_types: ["recommended"],
      primary_categories: ["other"],
      food_taxonomy: [{
        key: "other",
        label_ar: "أخرى",
        subcategories: [{ key: "other", label_ar: "أخرى" }]
      }],
      nutrition_data_sources: [{ key: "official", label_ar: "رسمي" }]
    };
    const definitions = definitionsFromRegistry(parseNutritionRegistry(registry));

    expect(definitions[0]).toMatchObject({
      key: "vitamin_c_mg",
      precision: 1,
      foodCompleteness: true,
      diaryDetails: false
    });
    expect(definitions[0].unit).not.toBe("mg");
    expect(() => parseNutritionRegistry({ ...registry, rules_manifest_hash: "bad" })).toThrow();
    expect(() => parseNutritionRegistry({
      ...registry,
      nutrients: [...registry.nutrients, { ...registry.nutrients[0] }]
    })).toThrow();
    expect(() => parseNutritionRegistry({
      ...registry,
      food_taxonomy: [{
        ...registry.food_taxonomy[0],
        subcategories: [
          registry.food_taxonomy[0].subcategories[0],
          { ...registry.food_taxonomy[0].subcategories[0] }
        ]
      }]
    })).toThrow();
  });

  it("rejects missing and non-finite nutrient values and formats finite values", () => {
    expect(nutrientValue({ sodium_mg: 12.5 } as never, "sodium_mg")).toBe(12.5);
    expect(nutrientValue({ sodium_mg: Number.POSITIVE_INFINITY } as never, "sodium_mg")).toBeNull();
    expect(nutrientValue({} as never, "sodium_mg")).toBeNull();
    expect(formatNutrientValue(1234.56, 1)).toBe("1,234.6");
  });
});
