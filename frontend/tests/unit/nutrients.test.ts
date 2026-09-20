import { describe, expect, it } from "vitest";

import {
  definitionsFromRegistry,
  formatNutrientValue,
  nutrientValue,
  parseNutritionRegistry,
} from "@/lib/nutrients";

function registryFixture() {
  return {
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
      diary_coverage_participation: false,
    }],
    target_types: ["recommended"],
    primary_categories: ["other"],
    food_taxonomy: [{
      key: "other",
      label_ar: "أخرى",
      subcategories: [{ key: "other", label_ar: "أخرى" }],
    }],
    nutrition_data_sources: [{ key: "official", label_ar: "رسمي" }],
  };
}

describe("nutrient definitions and values", () => {
  it("maps Registry coverage and exact localized presentation metadata", () => {
    const definitions = definitionsFromRegistry(parseNutritionRegistry(registryFixture()));

    expect(definitions).toEqual([{
      key: "vitamin_c_mg",
      label: "فيتامين ج",
      unit: "ملجم",
      precision: 1,
      order: 8,
      targetType: "recommended",
      targetValue: null,
      foodCompleteness: true,
    }]);
  });

  it.each([
    ["invalid manifest hash", () => ({ ...registryFixture(), rules_manifest_hash: "bad" })],
    ["duplicate nutrient key", () => {
      const registry = registryFixture();
      return { ...registry, nutrients: [...registry.nutrients, { ...registry.nutrients[0] }] };
    }],
    ["duplicate taxonomy child", () => {
      const registry = registryFixture();
      return {
        ...registry,
        food_taxonomy: [{
          ...registry.food_taxonomy[0],
          subcategories: [
            registry.food_taxonomy[0].subcategories[0],
            { ...registry.food_taxonomy[0].subcategories[0] },
          ],
        }],
      };
    }],
    ["target type outside the generated union", () => {
      const registry = registryFixture();
      return {
        ...registry,
        target_types: ["future_type"],
        nutrients: [{ ...registry.nutrients[0], target_type: "future_type" }],
      };
    }],
    ["nutrient target type absent from Registry target types", () => ({
      ...registryFixture(),
      target_types: ["minimum"],
    })],
  ])("rejects %s", (_name, buildInvalidRegistry) => {
    expect(() => parseNutritionRegistry(buildInvalidRegistry())).toThrow();
  });

  it("rejects missing and non-finite nutrient values and formats finite values", () => {
    expect(nutrientValue({ sodium_mg: 12.5 } as never, "sodium_mg")).toBe(12.5);
    expect(nutrientValue({ sodium_mg: Number.POSITIVE_INFINITY } as never, "sodium_mg")).toBeNull();
    expect(nutrientValue({} as never, "sodium_mg")).toBeNull();
    expect(formatNutrientValue(1234.56, 1)).toBe("1,234.6");
  });
});
