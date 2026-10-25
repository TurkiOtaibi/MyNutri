import { describe, expect, it } from "vitest";
import { convertDiaryQuantity, validateMeasuredQuantity } from "@/features/diary/diary-model";

describe("BR-DRY-019 measured quantities", () => {
  it("converts grams or ml into the existing stored food-unit quantity", () => {
    expect(convertDiaryQuantity("150", 100)).toBe(1.5);
    expect(convertDiaryQuantity("125", 250)).toBe(0.5);
    expect(convertDiaryQuantity("100", 30)).toBe(3.333);
    expect(convertDiaryQuantity("0.29", 29)).toBe(0.01);
    expect(convertDiaryQuantity("14.5", 0.29)).toBe(50);
  });
  it("enforces equivalent 0.01–50 unit limits before rounding", () => {
    expect(convertDiaryQuantity("1", 100)).toBe(0.01);
    expect(convertDiaryQuantity("5000", 100)).toBe(50);
    for (const value of ["0.999", "5000.001", "-1", "NaN", "1e2", ""]) {
      expect(convertDiaryQuantity(value, 100)).toBeNull();
    }
    expect(validateMeasuredQuantity("5001", 100, "كوب")).toBe("الكمية يجب ألا تتجاوز 50 كوب");
    expect(validateMeasuredQuantity("0", 100, "كوب")).toBe("أدخل كمية أكبر من 0");
  });
});
