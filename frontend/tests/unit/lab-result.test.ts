import { describe, expect, it } from "vitest";
import { enteredTriplet, freezeResultPatch, isChangedResultConflict, readbackResult, resultErrorTarget, resultFieldErrors } from "@/features/labs/lab-result-model";
import { historyFixture } from "./fixtures/labs";

const result = { ...historyFixture(1)[0], id: "original", entered_value: "38.797950", entered_unit: "mmol/mol", display_value: "5.7", display_unit: "%" };
describe("owner result facts and reconciliation", () => {
  it("seeds only the immutable result's entered triplet with full scale", () => {
    expect(enteredTriplet(result)).toEqual({ test_date: "2026-09-19", entered_value: "38.797950", entered_unit: "mmol/mol", expected_updated_at: result.updated_at });
  });
  it("freezes a normalized payload without changing the visible draft or leaking identity", () => {
    const draft = { ...enteredTriplet(result), entered_value: " ٣٨٫٧٩٧٩٥٠ " };
    const payload = freezeResultPatch(draft);
    expect(payload).toEqual({ test_date: "2026-09-19", entered_value: "38.797950", entered_unit: "mmol/mol", expected_updated_at: result.updated_at });
    expect(Object.isFrozen(payload)).toBe(true);
    draft.entered_value = "9";
    expect(payload.entered_value).toBe("38.797950");
  });
  it.each([
    [{ field: "test_date", test_key: "hba1c", loc: ["body", "entered_value"] }, "lab-edit-date"],
    [{ loc: ["body", "entered_value"], test_key: "hba1c" }, "lab-edit-value"],
    [{ field: "entered_unit", loc: ["body"] }, "lab-edit-unit"],
    [{ field: "unknown", loc: ["body", "test_date"] }, "lab-edit-errors"],
  ])("prioritizes the backend field then location for focus: %j", (partial, id) => {
    expect(resultErrorTarget({ ...partial, msg: "رسالة", type: "value_error" })).toBe(id);
  });
  it("narrows structured errors, preserving server priority and rejecting malformed entries", () => {
    const unit = { loc: ["body", "entered_unit"], msg: "اختر وحدة مدعومة لهذا التحليل.", type: "value_error", field: "entered_unit" };
    const value = { loc: ["body", "entered_value"], msg: "أدخل قيمة رقمية صريحة غير سالبة.", type: "value_error" };
    expect(resultFieldErrors([unit, { ...value, loc: [{}] }, value, { ...value, code: 6 }], "تعذر الحفظ")).toEqual([unit, value]);
    expect(resultFieldErrors({ detail: "private input" }, "تعذر الحفظ")).toEqual([{ loc: ["body"], msg: "تعذر الحفظ", type: "request_error" }]);
  });
  it("routes only a 409 result-version conflict into current-result readback", () => {
    const changed = [{ loc: ["body", "expected_updated_at"], field: "expected_updated_at", code: "LAB_RESULT_CHANGED", msg: "تغيّرت هذه النتيجة منذ فتحها.", type: "LAB_RESULT_CHANGED" }];
    expect(isChangedResultConflict(409, changed)).toBe(true);
    expect(isChangedResultConflict(422, changed)).toBe(false);
    expect(isChangedResultConflict(409, [{ ...changed[0], code: "LAB_DUPLICATE" }])).toBe(false);
    expect(isChangedResultConflict(409, "private input")).toBe(false);
  });
  it("reports an exact same-id entered match as current state, never a receipt", () => {
    expect(readbackResult([result], "original", { test_date: "2026-09-19", entered_value: "38.797950", entered_unit: "mmol/mol" })).toEqual({ kind: "matches", current: result });
  });
  it.each([
    { entered_value: "38.79795" }, { entered_unit: "%" }, { test_date: "2026-09-18" },
  ])("detects changed entered facts including scale: %j", (change) => {
    expect(readbackResult([{ ...result, ...change }], "original", { test_date: "2026-09-19", entered_value: "38.797950", entered_unit: "mmol/mol" }).kind).toBe("different");
  });
  it("proves absence only for the original id, never matching a substitute test/date", () => {
    expect(readbackResult([{ ...result, id: "replacement" }], "original", result)).toEqual({ kind: "absent" });
    expect(readbackResult([result], "original").kind).toBe("different");
  });
});
