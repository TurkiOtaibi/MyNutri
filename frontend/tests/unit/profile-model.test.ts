import { describe, expect, it } from "vitest";

import { blankDraft, didConfirmedBirthDateChange, mapProfileApiErrors, mappedProfileErrorFocusField, targetPlanSubmissionMatches, withUpdatedSex, withoutProfileFieldError } from "@/features/profile/profile-model";
import type { ProfileInput } from "@/lib/types";
import { ApiError } from "@/lib/api";

describe("Profile governed errors and confirmed DOB changes", () => {
  it.each([
    [
      "PROFILE_SEX_IMMUTABLE",
      { sex: "لا يمكن تعديل الجنس بعد حفظ الملف الشخصي." },
    ],
    [
      "LABS_ADULT_HISTORY_REQUIRED",
      { birth_date: "لا يمكن تعديل تاريخ الميلاد لأنه يجعل نتائج تحاليل مسجلة قبل عمر 18 سنة." },
    ],
  ])("maps top-level %s to its exact field copy", (code, expected) => {
    expect(mapProfileApiErrors(new ApiError("server copy is not authoritative", 409, undefined, code))).toEqual(expected);
  });

  it("preserves structured validation mapping and ignores unrelated top-level codes", () => {
    expect(mapProfileApiErrors(new ApiError("validation", 422, [
      { loc: ["body", "birth_date"] },
      { loc: ["body", "fat_pct"] },
    ]))).toEqual({ birth_date: "اختر تاريخ ميلاد صحيحًا", fat_percent: "أدخل نسبة دهون صحيحة" });
    expect(mapProfileApiErrors(new ApiError("conflict", 409, undefined, "IDEMPOTENCY_KEY_REUSED"))).toEqual({});
  });

  it("selects governed sex and DOB focus targets while retaining opener restoration for other fields", () => {
    expect(mappedProfileErrorFocusField({ height_cm: "height" })).toBeNull();
    expect(mappedProfileErrorFocusField({ birth_date: "dob", weight_kg: "weight" })).toBe("birth_date");
    expect(mappedProfileErrorFocusField({ sex: "sex", birth_date: "dob" })).toBe("sex");
  });

  it.each([
    ["1990-01-01", "1990-01-01", false],
    ["1990-01-01", "1991-01-01", true],
    [null, "1990-01-01", true],
  ])("compares prior confirmed DOB %s with accepted DOB %s", (previous, accepted, expected) => {
    expect(didConfirmedBirthDateChange(previous, accepted)).toBe(expected);
  });

  it("updates a sex-aware untouched fat default while preserving a customized value", () => {
    expect(withUpdatedSex(blankDraft(), "female")).toMatchObject({ sex: "female", fat_percent: "30" });
    expect(withUpdatedSex({ ...blankDraft(), fat_percent: "22" }, "female")).toMatchObject({
      sex: "female",
      fat_percent: "22",
    });
  });

  it("reuses a failed write identity only for the exact payload, date, and preview", () => {
    const payload: ProfileInput = {
      sex: "male", birth_date: "1990-01-01", height_cm: 170, weight_kg: 70,
      activity_level: "moderate", goal: "maintain", selected_cut_intensity: 0.2,
      protein_per_kg: 1.2, fat_pct: 0.25,
    };
    const submission = {
      payload, effectiveFrom: "2026-09-21", preview: { preview_hash: "hash-1" },
      idempotencyKey: "key-1", previouslyConfirmedBirthDate: "1990-01-01",
    };

    expect(targetPlanSubmissionMatches(submission, { ...payload }, "2026-09-21", "hash-1")).toBe(true);
    expect(targetPlanSubmissionMatches(submission, { ...payload, weight_kg: 71 }, "2026-09-21", "hash-1")).toBe(false);
    expect(targetPlanSubmissionMatches(submission, payload, "2026-09-22", "hash-1")).toBe(false);
    expect(targetPlanSubmissionMatches(submission, payload, "2026-09-21", "hash-2")).toBe(false);
  });

  it("clears only the edited field error", () => {
    const errors = { birth_date: "dob", weight_kg: "weight" };
    expect(withoutProfileFieldError(errors, "birth_date")).toEqual({ weight_kg: "weight" });
    expect(errors).toEqual({ birth_date: "dob", weight_kg: "weight" });
  });
});
