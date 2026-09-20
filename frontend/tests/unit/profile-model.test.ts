import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import type { ProfileInput, ProfileResponse, TargetPlanWriteResponse, TargetResponse } from "@/lib/types";
import {
  blankDraft,
  blockingSafetyMessage,
  isPreviewActivatable,
  mapProfileApiErrors,
  profileMatchesAcceptedPlan,
  validateDraft,
  type DraftProfile,
  type TargetPlanSubmission,
} from "@/features/profile/profile-model";

function validDraft(overrides: Partial<DraftProfile> = {}): DraftProfile {
  return {
    ...blankDraft(),
    birth_date: "1990-01-01",
    height_cm: "180",
    weight_kg: "80",
    protein_per_kg: "1.2",
    fat_percent: "25",
    ...overrides,
  };
}

describe("profile feature model", () => {
  it("keeps local and API field validation on the exact governed messages", () => {
    const draft = validDraft({
      birth_date: "2030-01-01",
      height_cm: "99",
      weight_kg: "19",
      protein_per_kg: "0.9",
      fat_percent: "14",
    });
    const local = validateDraft(draft, "2026-09-18", "2026-09-17").errors;
    const api = mapProfileApiErrors(new ApiError("invalid", 422, [
      { loc: ["body", "birth_date"] },
      { loc: ["body", "height_cm"] },
      { loc: ["body", "weight_kg"] },
      { loc: ["body", "protein_per_kg"] },
      { loc: ["body", "fat_pct"] },
      { loc: ["body", "effective_from"] },
    ]));
    const expected = {
      birth_date: "اختر تاريخ ميلاد صحيحًا",
      height_cm: "أدخل طولًا صحيحًا",
      weight_kg: "أدخل وزنًا صحيحًا",
      protein_per_kg: "أدخل قيمة صحيحة للبروتين لكل كجم",
      fat_percent: "أدخل نسبة دهون صحيحة",
      effective_from: "اختر تاريخًا يبدأ من اليوم",
    };

    expect(local).toEqual(expected);
    expect(api).toEqual(expected);
  });

  it("builds a valid Profile payload and accepts inclusive field boundaries", () => {
    const result = validateDraft(validDraft({
      height_cm: "100",
      weight_kg: "20",
      protein_per_kg: "1",
      fat_percent: "15",
    }), "2026-09-20", "2026-09-20");

    expect(result).toEqual({
      errors: {},
      payload: {
        sex: "male",
        birth_date: "1990-01-01",
        height_cm: 100,
        weight_kg: 20,
        activity_level: "moderate",
        goal: "cut",
        selected_cut_intensity: 0.2,
        protein_per_kg: 1,
        fat_pct: 0.15,
      },
    });
  });

  it("rejects unsupported cut intensity without producing a payload", () => {
    const result = validateDraft(
      validDraft({ selected_cut_intensity: 0.3 as DraftProfile["selected_cut_intensity"] }),
      "2026-09-20",
      "2026-09-20",
    );

    expect(result.payload).toBeNull();
    expect(result.errors.selected_cut_intensity).toBe("اختر شدة خفض صحيحة");
  });

  it("maps every safety outcome to the exact fail-closed message", () => {
    expect(blockingSafetyMessage("specialist_review_required")).toBe(
      "لا يمكن حفظ هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.",
    );
    expect(blockingSafetyMessage("very_low_energy_blocked")).toBe(
      "لا يمكن حفظ هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.",
    );
    expect(blockingSafetyMessage("unknown")).toBe(
      "تعذر التحقق من إمكانية حفظ هذا الهدف. حدّث المعاينة قبل المتابعة.",
    );
    expect(blockingSafetyMessage("normal")).toBeNull();
  });

  it("activates only normal, allowed previews with a hash", () => {
    const activatable = {
      preview_hash: "preview-hash",
      can_activate: true,
      safety_outcome: "normal",
    } as TargetResponse;

    expect(isPreviewActivatable(activatable)).toBe(true);
    expect(isPreviewActivatable({ ...activatable, preview_hash: null })).toBe(false);
    expect(isPreviewActivatable({ ...activatable, can_activate: false })).toBe(false);
    expect(isPreviewActivatable({ ...activatable, safety_outcome: "specialist_review_required" })).toBe(false);
    expect(isPreviewActivatable(null)).toBe(false);
  });

  it("reconciles only the accepted effective date and normalized Profile payload", () => {
    const payload = validateDraft(validDraft(), "2026-09-20", "2026-09-20").payload as ProfileInput;
    const submission: TargetPlanSubmission = {
      payload,
      effectiveFrom: "2026-09-20",
      preview: { preview_hash: "preview-hash" } as TargetResponse & { preview_hash: string },
      idempotencyKey: "idempotency-key",
    };
    const serverProfile = { ...payload } as ProfileResponse;
    const accepted = { plan: { effective_from: "2026-09-20" } } as TargetPlanWriteResponse;

    expect(profileMatchesAcceptedPlan(serverProfile, submission, accepted)).toBe(true);
    expect(profileMatchesAcceptedPlan(
      { ...serverProfile, weight_kg: 81 },
      submission,
      accepted,
    )).toBe(false);
    expect(profileMatchesAcceptedPlan(
      serverProfile,
      submission,
      { plan: { effective_from: "2026-09-21" } } as TargetPlanWriteResponse,
    )).toBe(false);
  });
});
