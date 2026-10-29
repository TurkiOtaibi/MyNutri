import { describe, expect, it } from "vitest";

import { chartGeometry, rangeBarGeometry } from "@/features/labs/lab-chart-model";
import type { LabChartZoneSegment, LabResultResponse } from "@/lib/types";

type Zone = LabResultResponse["reference_zones"][number];
const zone = (low: string | null, high: string | null, tone: "within" | "caution" | "outside", code: string): Zone => ({
  low, high, low_inclusive: true, high_inclusive: true, status: { code, label_ar: code, tone },
}) as Zone;
const ferritin = [zone(null, "11", "outside", "low"), zone("11", "328", "within", "normal"), zone("328", null, "outside", "high")];

describe("issue #151 Labs range presentation", () => {
  it("splits the reference zones into equal ordered segments", () => {
    const geometry = rangeBarGeometry([ferritin[2], ferritin[0], ferritin[1]], null)!;
    expect(geometry.segments.map(segment => segment.tone)).toEqual(["outside", "within", "outside"]);
    expect(geometry.segments[1]).toMatchObject({ from: 100 / 3, to: 200 / 3 });
    expect(geometry.marker).toBeNull();
  });

  it("places the marker inside the zone that holds the value", () => {
    const low = rangeBarGeometry(ferritin, "5.9")!.marker!;
    const normal = rangeBarGeometry(ferritin, "12.4")!.marker!;
    const high = rangeBarGeometry(ferritin, "900")!.marker!;
    expect(low).toBeLessThan(100 / 3);
    expect(normal).toBeGreaterThan(100 / 3);
    expect(normal).toBeLessThan(200 / 3);
    expect(high).toBeGreaterThan(200 / 3);
    expect(high).toBeLessThanOrEqual(97);
  });

  it("does not draw a negative value axis for non-negative results", () => {
    const results = [
      { id: "a", test_date: "2020-01-01", display_value: "5.9" },
      { id: "b", test_date: "2022-01-01", display_value: "12.4" },
    ] as LabResultResponse[];
    const segments = [{ from_date: "2000-01-01", to_date_exclusive: "2100-01-01", age_min: 18, zones: ferritin }] as unknown as LabChartZoneSegment[];
    const labels = chartGeometry(results, segments, 360, 240).ticks.filter(tick => tick.axis === "y").map(tick => Number(tick.label));
    expect(Math.min(...labels)).toBe(0);
  });
});
