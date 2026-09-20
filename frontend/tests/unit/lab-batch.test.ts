import { describe, expect, it } from "vitest";

import {
  buildLabRows,
  mapLabErrors,
  normalizeLabNumber,
  selectedTestKeys,
} from "@/features/labs/lab-batch-model";
import { catalogFixture } from "./fixtures/labs";

describe("Labs batch model", () => {
  it("keeps blank and zero distinct", () => {
    expect(normalizeLabNumber(" ٥.٢٧٠ ")).toBe("5.270");
    expect(buildLabRows([
      { testKey: "eosinophils_pct", value: "0", unit: "%" },
      { testKey: "hba1c", value: "", unit: "%" },
    ])).toEqual([
      { test_key: "eosinophils_pct", entered_value: "0", entered_unit: "%" },
    ]);
  });

  it("normalizes Arabic and Persian digits and decimal separators as strings", () => {
    expect(normalizeLabNumber(" ١٬٢٣٤٫٥٠ ")).toBe("1234.50");
    expect(normalizeLabNumber("۰۱۲.۳۰")).toBe("012.30");
    expect(normalizeLabNumber("  ")).toBe("");
  });

  it("unions panels and individual selections in catalog order without duplicates", () => {
    expect(selectedTestKeys(["iron_studies", "cbc"], ["hba1c", "ferritin", "unknown"], catalogFixture))
      .toEqual(["hba1c", "eosinophils_pct", "ferritin"]);
  });

  it("maps structured field errors to their row and leaves general errors at form scope", () => {
    expect(mapLabErrors([
      { loc: ["body", "test_date"], field: "test_date", msg: "تاريخ غير صالح", type: "value_error" },
      { loc: ["body", "results", 0, "entered_value"], field: "entered_value", test_key: "hba1c", code: "LAB_VALUE_INVALID", msg: "قيمة غير صالحة", type: "value_error" },
      { loc: ["body", "results", 0, "entered_unit"], test_key: "hba1c", msg: "وحدة غير مدعومة", type: "value_error" },
      { loc: ["body", "results"], test_key: "ferritin", msg: "نتيجة مكررة", type: "value_error" },
      { loc: ["body"], msg: "تعذر الحفظ", type: "value_error" },
    ])).toEqual({
      test_date: "تاريخ غير صالح",
      rows: {
        hba1c: { entered_value: "قيمة غير صالحة", entered_unit: "وحدة غير مدعومة" },
        ferritin: { form: "نتيجة مكررة" },
      },
      form: "تعذر الحفظ",
    });
  });
});
