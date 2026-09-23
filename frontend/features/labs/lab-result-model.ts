import type { LabFieldError, LabResultPatch, LabResultResponse } from "@/lib/types";
import { normalizeLabNumber } from "./lab-batch-model";

export type ResultReadback = { kind: "matches" | "different"; current: LabResultResponse } | { kind: "absent" };
export function enteredTriplet(result: LabResultPatch | LabResultResponse): LabResultPatch {
  return { test_date: result.test_date, entered_value: result.entered_value, entered_unit: result.entered_unit,
    expected_updated_at: "updated_at" in result ? result.updated_at : result.expected_updated_at };
}
export function freezeResultPatch(draft: LabResultPatch): LabResultPatch {
  return Object.freeze({ ...enteredTriplet(draft), entered_value: normalizeLabNumber(draft.entered_value) });
}
export function resultErrorTarget(error: LabFieldError): string {
  const field = error.field ?? [...error.loc].reverse().find(part => typeof part === "string");
  return field === "test_date" ? "lab-edit-date" : field === "entered_value" ? "lab-edit-value"
    : field === "entered_unit" ? "lab-edit-unit" : "lab-edit-errors";
}
export function resultFieldErrors(detail: unknown, fallback: string): LabFieldError[] {
  if (Array.isArray(detail)) {
    const errors = detail.filter((item): item is LabFieldError => (
      typeof item === "object" && item !== null && Array.isArray(item.loc)
      && item.loc.every((part: unknown) => typeof part === "string" || typeof part === "number")
      && typeof item.msg === "string" && typeof item.type === "string"
      && (item.field == null || typeof item.field === "string")
      && (item.test_key == null || typeof item.test_key === "string")
      && (item.code == null || typeof item.code === "string")
    ));
    if (errors.length) return errors;
  }
  return [{ loc: ["body"], msg: fallback, type: "request_error" }];
}
export function isChangedResultConflict(status: number, detail: unknown): boolean {
  return status === 409 && resultFieldErrors(detail, "").some(item => item.code === "LAB_RESULT_CHANGED");
}
export function readbackResult(results: LabResultResponse[], id: string, submitted?: Pick<LabResultPatch, "test_date" | "entered_value" | "entered_unit">): ResultReadback {
  const current = results.find(result => result.id === id);
  if (!current) return { kind: "absent" };
  return { kind: submitted && current.entered_value === submitted.entered_value
    && current.entered_unit === submitted.entered_unit && current.test_date === submitted.test_date ? "matches" : "different", current };
}
