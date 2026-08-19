import { describe, expect, it, vi } from "vitest";

import {
  ANALYSIS_COPY,
  displayState,
  formatMetricValue,
  metricStatusText,
  stableAnalysisAttempt,
  visibleMetrics
} from "@/features/progress/progress-model";
import type { PatternAnalysisMetric, PatternAnalysisResponse } from "@/lib/types";

const metric = (overrides: Partial<PatternAnalysisMetric> = {}): PatternAnalysisMetric => ({
  metric_key: "nutrient:fiber_g",
  metric_kind: "daily_average",
  unit: "g/day",
  aggregation: "average_numeric_days",
  direction: "minimum",
  target: { type: "minimum", value: 25, lower: null, upper: null, source_plan_ids: [] },
  current: {
    value: 18,
    value_state: "known",
    amount_qualifier: "exact",
    complete_day_count: 5,
    numeric_day_count: 5,
    known_entry_count: 8,
    total_entry_count: 8,
    coverage_percent: 100,
    confidence: "strong",
    status: "below_target",
    evidence_refs: []
  },
  previous: {
    value: 16,
    value_state: "known",
    amount_qualifier: "exact",
    complete_day_count: 5,
    numeric_day_count: 5,
    known_entry_count: 8,
    total_entry_count: 8,
    coverage_percent: 100,
    confidence: "strong",
    status: "below_target",
    evidence_refs: []
  },
  comparison: { status: "improved", reason: "comparable", difference: 2, normalized_adverse_delta: -0.08 },
  persistence: { kind: "same_direction_two_period", qualifies: true, reason: "qualified" },
  contributors: { current: [], previous: [] },
  ...overrides
});

const analysis = (overrides: Partial<PatternAnalysisResponse> = {}): PatternAnalysisResponse => ({
  source_analysis_id: "00000000-0000-0000-0000-000000000321",
  source_analysis_revision: 1,
  lifecycle_status: "current",
  stale_reasons: [],
  as_of_diary_date: "2026-08-17",
  period_start: "2026-08-11",
  period_end: "2026-08-17",
  previous_period_start: "2026-08-04",
  previous_period_end: "2026-08-10",
  complete_day_count: 5,
  previous_complete_day_count: 5,
  metric_summaries: [metric()],
  source_versions: {} as PatternAnalysisResponse["source_versions"],
  priority_input: { safety_flags: [] } as unknown as PatternAnalysisResponse["priority_input"],
  generated_at: "2026-08-17T09:00:00Z",
  finalized_at: "2026-08-17T09:00:00Z",
  etag: '"analysis-00000000-0000-0000-0000-000000000321-r1"',
  ...overrides
});

describe("PLAN 032 progress domain", () => {
  it("maps empty, stale, safety, and limited evidence deterministically", () => {
    expect(displayState(null)).toBe("empty");
    expect(displayState(analysis({ lifecycle_status: "stale" }))).toBe("stale");
    expect(displayState(analysis({ priority_input: { safety_flags: ["missing_target"] } as unknown as PatternAnalysisResponse["priority_input"] }))).toBe("unsafe");
    expect(displayState(analysis({ metric_summaries: [metric({ current: { ...metric().current, confidence: "limited" } })] }))).toBe("limited");
  });

  it("uses exact Arabic copy and non-color semantic status text", () => {
    expect(ANALYSIS_COPY.heading).toBe("تحليل نمط التغذية");
    expect(ANALYSIS_COPY.insufficient).toBe("التحليل غير متاح لعدم كفاية الأيام المكتملة");
    expect(metricStatusText(metric())).toBe("أقل من النطاق المستهدف");
    expect(formatMetricValue(metric())).toContain("g/day");
  });

  it("sorts visible facts and excludes unavailable values", () => {
    const unavailable = metric({ metric_key: "a", current: { ...metric().current, value: null, value_state: "unknown" } });
    const later = metric({ metric_key: "z" });
    expect(visibleMetrics(analysis({ metric_summaries: [later, unavailable, metric()] })).map((item) => item.metric_key)).toEqual(["nutrient:fiber_g", "z"]);
  });

  it("reuses the same idempotency command until the attempt is resolved", () => {
    vi.spyOn(crypto, "randomUUID").mockReturnValue("00000000-0000-4000-8000-000000000032");
    const first = stableAnalysisAttempt(null, analysis());
    expect(stableAnalysisAttempt(first, null)).toBe(first);
    expect(first).toEqual({ key: "00000000-0000-4000-8000-000000000032", expectedRevision: 1, etag: analysis().etag });
  });
});
