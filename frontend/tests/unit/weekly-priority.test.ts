import { describe, expect, it, vi } from "vitest";

import {
  goalActionCopy,
  goalStateCopy,
  priorityMessage,
  stableGoalCommandAttempt
} from "@/features/progress/progress-model";
import type { BehaviorGoal, WeeklyPriorityResult } from "@/lib/types";

const goal = {
  goal_id: "00000000-0000-4000-8000-000000000333",
  state: "incomplete",
  version: 4,
  weekly_target_count: 3,
  allowed_actions: ["repeat", "reduce", "change", "end"]
} as BehaviorGoal;

describe("PLAN 033 progress model", () => {
  it("keeps the governed Arabic state and action copy available", () => {
    expect(goalStateCopy.active).toBe("هدفك الأسبوعي نشط");
    expect(goalStateCopy.completed).toBe("اكتملت الخطوة وفق الأيام المسجلة.");
    expect(goalActionCopy.repeat).toBe("تكرار الهدف لأسبوع جديد");
    expect(goalActionCopy.reduce).toBe("تخفيف الخطوة للأسبوع الجديد");
  });

  it("keeps one stable idempotency key for a retry and maps reduce to repeat", () => {
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("00000000-0000-4000-8000-000000000001");
    const first = stableGoalCommandAttempt(null, goal, "reduce", 2);
    const retry = stableGoalCommandAttempt(first, goal, "reduce", 2);
    expect(retry).toBe(first);
    expect(first.command).toEqual({
      event: "repeat",
      expected_version: 4,
      repeat_mode: "reduce",
      weekly_target_count: 2
    });
  });

  it("renders none, stale, and safety states without inventing an offer", () => {
    const base = {
      status: "none",
      none_reason: "no_eligible_priority"
    } as WeeklyPriorityResult;
    expect(priorityMessage(base)).toContain("لا توجد أولوية واضحة");
    expect(priorityMessage({ ...base, status: "stale" })).toContain("تغيّرت بيانات اليوميات");
    expect(priorityMessage({ ...base, status: "safety_suppressed" })).toContain("أولوية آمنة");
  });
});
