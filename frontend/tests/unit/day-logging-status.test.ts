import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DayLoggingStatusCard } from "@/features/diary/diary-summary";
import { dayLoggingStatusLabels, isDayAnalysisEligible, isFutureDiaryStatus, stableStatusCommandAttempt } from "@/features/diary/diary-model";

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

  it("reuses one idempotency identity for an ambiguous retry", () => {
    const createKey = vi.fn(() => "stable-key");
    const first = stableStatusCommandAttempt(null, "complete", 4, createKey);
    const retry = stableStatusCommandAttempt(first, "complete", 5, createKey);
    expect(retry).toBe(first);
    expect(retry).toEqual({ action: "complete", expectedVersion: 4, idempotencyKey: "stable-key" });
    expect(createKey).toHaveBeenCalledOnce();
  });

  it("renders loading, stale, full-date, and non-color status semantics", () => {
    const pending = renderToStaticMarkup(createElement(DayLoggingStatusCard, {
      status: undefined,
      pending: true,
      failed: false,
      stale: false,
      commandPending: false,
      onComplete: vi.fn(),
      onReopen: vi.fn(),
      onRetry: vi.fn()
    }));
    expect(pending).toContain('aria-busy="true"');

    const status = {
      date: "2026-08-15",
      logging_status: "complete" as const,
      logging_status_version: 2,
      entry_count: 0,
      analysis_eligible: true,
      completed_at: "2026-08-15T18:20:00Z",
      calendar: {
        current_diary_date: "2026-08-15",
        calendar_timezone: "Asia/Riyadh",
        next_rollover_at: "2026-08-15T21:00:00Z"
      }
    };
    const stale = renderToStaticMarkup(createElement(DayLoggingStatusCard, {
      status,
      pending: false,
      failed: false,
      stale: true,
      commandPending: false,
      onComplete: vi.fn(),
      onReopen: vi.fn(),
      onRetry: vi.fn()
    }));
    expect(stale).toContain("تم تسجيل اليوم");
    expect(stale).toContain("قد تكون الحالة المعروضة قديمة");
    expect(stale).toContain('aria-hidden="true">✓');
    expect(stale).toContain("15 أغسطس 2026");
  });
});
