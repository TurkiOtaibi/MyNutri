import { describe, expect, it } from "vitest";
import { approvedSafetyCopy } from "./fixtures/profile-safety";
import { ApiError } from "@/lib/api";
import { blockingSafetyExplanation, safetyOutcomeFromError } from "@/features/profile/profile-model";

describe("BR-PRF-015 authoritative safety explanations", () => {
  it.each([
    ["SPECIALIST_REVIEW_REQUIRED", "specialist_review_required"],
    ["VERY_LOW_ENERGY_TARGET_BLOCKED", "very_low_energy_blocked"],
    ["NON_POSITIVE_CARBOHYDRATE_ALLOCATION", "non_positive_carbohydrate_allocation"],
  ])("maps %s to a reason and safe alternative without inventing low weight", (code, outcome) => {
    expect(safetyOutcomeFromError(new ApiError("server message", 422, undefined, code))).toBe(outcome);
    const explanation = blockingSafetyExplanation(outcome);
    expect(explanation).toEqual(approvedSafetyCopy[outcome as keyof typeof approvedSafetyCopy]);
    expect(JSON.stringify(explanation)).not.toMatch(/خفض الوزن|وزنك أقل/);
  });

  it("does not invent reasons for normal, unknown or network outcomes", () => {
    expect(blockingSafetyExplanation("normal")).toBeNull();
    expect(blockingSafetyExplanation("unknown")).toBeNull();
    expect(safetyOutcomeFromError(new Error("SPECIALIST_REVIEW_REQUIRED"))).toBeNull();
    expect(safetyOutcomeFromError(new ApiError("unknown", 422, undefined, "UNKNOWN"))).toBeNull();
  });
});
