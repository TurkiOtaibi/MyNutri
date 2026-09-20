import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LabTestView } from "@/features/labs/lab-test-view";
import type { LabTestDetailResponse } from "@/lib/types";
import { catalogFixture, ferritinAge51Segments, historyFixture } from "./fixtures/labs";

const results = historyFixture(2).reverse().map((p, index) => ({ ...p,
  display_value: index ? "8.0000000000000000000001" : "12.00", display_unit: "ng/mL",
  status: { code: "in_range", label_ar: "ضمن النطاق", tone: "within" },
  reference_zones: ferritinAge51Segments[index].zones,
}));
const detail: LabTestDetailResponse = {
  test: catalogFixture.tests[0], results, chart_zones: [], reference_at_date: "2026-09-19",
  reference_zones: [], eligibility: { allowed: true, reason: null }, server_today: "2026-09-20",
  medical_rules_version: "labs-v1", read_only: false,
};
const render = (data = detail, selectedResultId: string | null = null) => renderToStaticMarkup(createElement(LabTestView, {
  detail: data, selectedResultId, onSelectResult: () => undefined,
  ownerActions: createElement("button", null, "owner-add"),
}));

describe("shared Lab detail presentation", () => {
  it("uses selected result exact reference/date and canonical unit outside SVG", () => {
    const html = render(detail, results[1].id);
    expect(html).toContain('data-reference-date="2026-09-18"');
    expect(html).toContain("8.0000000000000000000001");
    expect(html).toContain("328");
    expect(html).toContain("≥");
    expect(html).toContain("≤");
    expect(html).toContain("بلا حد أدنى");
    expect(html).toContain("بلا حد أعلى");
    expect(html).toContain('aria-label="القيمة (ng/mL)"');
    expect(html.match(/data-history-result=/g)).toHaveLength(2);
    expect(html.match(/data-chart-point=/g)).toHaveLength(2);
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
  });
  it("defaults missing selection to latest and hides supplied actions when read-only", () => {
    const html = render({ ...detail, read_only: true }, "deleted-id");
    expect(html).toContain('data-reference-date="2026-09-19"');
    expect(html).not.toContain("owner-add");
    expect(html).toContain("للقراءة فقط");
  });
  it("uses server empty reference and does not invent zones for ineligible profiles", () => {
    const html = render({ ...detail, results: [], chart_zones: [], reference_at_date: "2026-09-20" });
    expect(html).toContain('data-reference-date="2026-09-20"');
    expect(html).toContain("لا توجد نتائج مسجلة لهذا التحليل.");
    expect(html).not.toContain("data-reference-zone");
  });
  it("renders one point without a connecting line and confines fasting to flagged tests", () => {
    expect(render({ ...detail, results: results.slice(0, 1) })).not.toContain("polyline");
    expect(render()).toContain("يفترض هذا التحليل الصيام.");
    expect(render({ ...detail, test: catalogFixture.tests[2] })).not.toContain("يفترض هذا التحليل الصيام.");
  });
});
