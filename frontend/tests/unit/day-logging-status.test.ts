import { describe, expect, it } from "vitest";

import { dayLoggingStatusLabels, isDayAnalysisEligible, isFutureDiaryStatus } from "@/features/diary/diary-model";

describe("Diary day logging status", () => {
  it("keeps the frozen Arabic vocabulary", () => {
    expect(dayLoggingStatusLabels).toEqual({
      unregistered: "غير مسجل",
      partial: "التسجيل غير مكتمل",
      complete: "تم تسجيل اليوم"
    });
  });

  it("includes only explicitly complete days in analysis", () => {
    expect(isDayAnalysisEligible("unregistered")).toBe(false);
    expect(isDayAnalysisEligible("partial")).toBe(false);
    expect(isDayAnalysisEligible("complete")).toBe(true);
  });

  it("disables status commands only for a projected future day", () => {
    const status = {
      date: "2026-08-16",
      logging_status: "unregistered" as const,
      logging_status_version: 0,
      entry_count: 0,
      analysis_eligible: false,
      completed_at: null,
      calendar: {
        current_diary_date: "2026-08-15",
        calendar_timezone: "Asia/Riyadh",
        next_rollover_at: "2026-08-15T21:00:00Z"
      }
    };
    expect(isFutureDiaryStatus(status)).toBe(true);
    expect(isFutureDiaryStatus({ ...status, date: "2026-08-15" })).toBe(false);
  });
});
