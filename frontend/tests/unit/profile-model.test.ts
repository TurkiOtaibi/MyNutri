import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import {
  UNKNOWN_SAFETY_MESSAGE,
  blankDraft,
  blockingSafetyMessage,
  mapProfileApiErrors,
  validateDraft,
} from "@/features/profile/profile-model";

describe("profile feature model", () => {
  it("keeps local and API field validation on the same governed messages", () => {
    const draft = {
      ...blankDraft(),
      birth_date: "2030-01-01",
      height_cm: "99",
      weight_kg: "19",
      protein_per_kg: "0.9",
      fat_percent: "14",
    };
    const local = validateDraft(draft, "2026-09-18", "2026-09-17").errors;
    const api = mapProfileApiErrors(new ApiError("invalid", 422, [
      { loc: ["body", "birth_date"] },
      { loc: ["body", "height_cm"] },
      { loc: ["body", "weight_kg"] },
      { loc: ["body", "protein_per_kg"] },
      { loc: ["body", "fat_pct"] },
      { loc: ["body", "effective_from"] },
    ]));

    expect(api).toEqual({
      birth_date: local.birth_date,
      height_cm: local.height_cm,
      weight_kg: local.weight_kg,
      protein_per_kg: local.protein_per_kg,
      fat_percent: local.fat_percent,
      effective_from: local.effective_from,
    });
  });

  it("uses one fail-closed safety message for unknown outcomes", () => {
    expect(blockingSafetyMessage("unknown")).toBe(UNKNOWN_SAFETY_MESSAGE);
  });
});
