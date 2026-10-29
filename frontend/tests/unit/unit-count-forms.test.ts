import { describe, expect, it } from "vitest";
import { countedUnitText } from "@/lib/food";

describe("Arabic count forms for food units", () => {
  it.each([
    [1, "piece", "1 قطعة"],
    [2, "piece", "قطعتان"],
    [3, "piece", "3 قطع"],
    [10, "piece", "10 قطع"],
    [11, "piece", "11 قطعة"],
    [1.5, "piece", "1.5 قطعة"],
    [0.5, "serving", "0.5 حصة"],
    [2, "serving", "حصتان"],
    [4, "cup", "4 أكواب"],
    [3, "slice", "3 شرائح"],
    [5, "scoop", "5 مكاييل"],
    [3, "tablespoon", "3 ملاعق كبيرة"],
    [2, "teaspoon", "ملعقتان صغيرتان"],
    [103, "piece", "103 قطع"],
    [101, "piece", "101 قطعة"],
    [250, "g", "250 جم"],
    [2, "ml", "2 مل"]
  ] as const)("%s %s → %s", (quantity, unit, expected) => {
    expect(countedUnitText(quantity, unit)).toBe(expected);
  });

  it("uses the genitive dual after a preposition", () => {
    expect(countedUnitText(2, "piece", { genitive: true })).toBe("قطعتين");
    expect(countedUnitText(2, "tablespoon", { genitive: true })).toBe("ملعقتين كبيرتين");
    expect(countedUnitText(3, "piece", { genitive: true })).toBe("3 قطع");
  });
});
