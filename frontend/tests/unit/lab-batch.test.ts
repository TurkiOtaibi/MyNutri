import { describe, expect, it } from "vitest";

import {
  buildLabRows,
  mapLabErrors,
  normalizeLabNumber,
  selectedTestKeys,
  batchReducer, batchErrorTarget, createBatchDraft, freezeBatch, populatedCount,
  type BatchPhase,
} from "@/features/labs/lab-batch-model";
import { catalogFixture, draftFixture } from "./fixtures/labs";

describe("Labs batch model", () => {
  it("returns profile errors to the earlier step without losing the form and maps unit focus", () => {
    expect(batchErrorTarget({ loc: ["body"], code: "LAB_PROFILE_REQUIRED", msg: "أكمل الملف", type: "LAB_PROFILE_REQUIRED" }))
      .toEqual({ step: "date", id: "lab-batch-errors" });
    expect(batchErrorTarget({ loc: ["body", "results", 0, "entered_unit"], test_key: "hba1c", msg: "وحدة", type: "value_error" }))
      .toEqual({ step: "values", id: "lab-hba1c-unit" });
  });

  it("ignores later opening defaults while a draft exists and keeps all values during step navigation", () => {
    const editing: BatchPhase = { kind: "editing", draft: draftFixture };
    expect(batchReducer(editing, { type: "OPEN", draft: createBatchDraft("actor-a", "2026-09-21", catalogFixture) })).toBe(editing);
    const back = batchReducer(editing, { type: "BACK" });
    expect(back).toMatchObject({ draft: { ...draftFixture, step: "selection" } });
    expect(batchReducer(back, { type: "NEXT" })).toEqual(editing);
    expect(batchReducer(editing, { type: "SUBMIT", pending: { ...freezeBatch(draftFixture, "k"), actorId: "other" } })).toBe(editing);
  });
  it("keeps invalid separator-only input populated while omitting raw whitespace", () => {
    expect(buildLabRows([{ testKey: "hba1c", value: "٬", unit: "%" }, { testKey: "ferritin", value: " \t", unit: "ng/mL" }]))
      .toEqual([{ test_key: "hba1c", entered_value: "٬", entered_unit: "%" }]);
  });

  it("initializes at date with server today and fixed defaults; overlapping ownership retains edits", () => {
    const catalog = { ...catalogFixture, panels: [...catalogFixture.panels, { key: "overlap", name_ar: "مشترك", name_en: "Overlap", test_keys: ["ferritin"] }] };
    let state: BatchPhase | null = { kind: "editing", draft: createBatchDraft("a", "2026-09-20", catalog, ["ferritin"]) };
    expect(state.draft).toMatchObject({ date: "2026-09-20", step: "date", rows: { ferritin: { value: "", unit: "ng/mL" } } });
    state = batchReducer(state, { type: "PANEL", key: "iron_studies", selected: true, catalog });
    state = batchReducer(state, { type: "PANEL", key: "overlap", selected: true, catalog });
    state = batchReducer(state, { type: "EDIT_VALUE", testKey: "ferritin", value: "7.00" });
    state = batchReducer(state, { type: "EDIT_UNIT", testKey: "ferritin", unit: "µg/L" });
    state = batchReducer(state, { type: "PANEL", key: "iron_studies", selected: false, catalog });
    state = batchReducer(state, { type: "INDIVIDUAL", key: "ferritin", selected: false, catalog });
    expect(state && "draft" in state && state.draft.rows.ferritin).toEqual({ value: "7.00", unit: "µg/L" });
    expect(createBatchDraft("a", "2026-09-21", catalog, ["ferritin"]).rows.ferritin.unit).toBe("ng/mL");
  });

  it("counts zero and invalid nonblank rows, rejects all-blank, and freezes a shared-date exact payload", () => {
    const draft = createBatchDraft("a", "2026-09-20", catalogFixture, ["hba1c", "ferritin"]);
    expect(populatedCount(draft)).toBe(0);
    expect(() => freezeBatch(draft, "k")).toThrow("أدخل نتيجة واحدة على الأقل.");
    draft.rows.hba1c.value = "٠";
    draft.rows.ferritin.value = "٬";
    expect(populatedCount(draft)).toBe(2);
    const pending = freezeBatch(draft, "k");
    expect(pending.payload).toEqual({ test_date: "2026-09-20", results: [
      { test_key: "hba1c", entered_value: "0", entered_unit: "%" },
      { test_key: "ferritin", entered_value: "٬", entered_unit: "ng/mL" },
    ] });
    draft.rows.hba1c.value = "9";
    expect(pending.payload.results[0].entered_value).toBe("0");
    expect(Object.isFrozen(pending.payload.results[0])).toBe(true);
    expect(Object.isFrozen(pending.payload.results)).toBe(true);
    expect(Object.isFrozen(pending.payload)).toBe(true);
  });

  it("locks editing and dismissal until the same ambiguous operation resolves, but always resets on takeover", () => {
    const pending = freezeBatch(draftFixture, "request-1");
    const submitting: BatchPhase = { kind: "submitting", draft: draftFixture, pending };
    const ambiguous = batchReducer(submitting, { type: "NETWORK_AMBIGUOUS" });
    expect(ambiguous).toMatchObject({ kind: "ambiguous", pending });
    if (!ambiguous || !("pending" in ambiguous)) throw Error("Expected pending");
    expect(ambiguous.pending).toBe(pending);
    for (const state of [submitting, ambiguous]) {
      expect(batchReducer(state, { type: "EDIT_VALUE", testKey: "hba1c", value: "7" })).toBe(state);
      expect(batchReducer(state, { type: "CANCEL" })).toBe(state);
      expect(batchReducer(state, { type: "NEXT" })).toBe(state);
      expect(batchReducer(state, { type: "RESET" })).toBeNull();
    }
    expect(batchReducer(ambiguous, { type: "RETRY" })).toEqual(submitting);
    const errors = [{ loc: ["body", "test_date"], field: "test_date", msg: "تاريخ غير صالح", type: "value_error" }];
    const rejected = batchReducer(submitting, { type: "VALIDATION_ERROR", errors });
    expect(rejected).toMatchObject({ kind: "validation_error", draft: { ...draftFixture, step: "date" }, errors });
    expect(batchReducer(rejected, { type: "EDIT_VALUE", testKey: "hba1c", value: "7" })).toMatchObject({ kind: "editing", draft: { rows: { hba1c: { value: "7" } } } });
  });
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

  it("preserves malformed grouping so the backend rejects it instead of changing the value", () => {
    expect(normalizeLabNumber("١٬٢")).toBe("1٬2");
    expect(normalizeLabNumber("١٢٬٣٤")).toBe("12٬34");
    expect(normalizeLabNumber("١٬٢٣٤٫٥٬٦")).toBe("1٬234.5٬6");
    expect(normalizeLabNumber("١٢٬٣٤٥٫٦")).toBe("12345.6");
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
