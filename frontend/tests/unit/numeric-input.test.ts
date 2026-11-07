import { describe, expect, it } from "vitest";
import { normalizeNumber } from "@/features/profile/profile-model";
import { convertDiaryQuantity, parseQuantity } from "@/features/diary/diary-model";

describe("localized numeric input", () => {
  it("accepts all three digit sets and the explicit Arabic decimal separator", () => {
    for (const value of ["1.25", "١٫٢٥", "۱٫۲۵"]) {
      expect(normalizeNumber(value)).toBe(1.25);
      expect(parseQuantity(value)).toBe(1.25);
    }
    expect(convertDiaryQuantity("١٢٥", 100)).toBe(1.25);
  });
  it("rejects ambiguous and malformed separators without reinterpreting values", () => {
    for (const value of ["1,25", "١٬٢٥٠", "1٫2.3", "1e2", "", ".", "-1"]) {
      expect(normalizeNumber(value)).toBeNull();
      expect(parseQuantity(value)).toBeNull();
    }
  });
});
