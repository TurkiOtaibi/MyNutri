import { describe, expect, it } from "vitest";
import { chartGeometry } from "@/features/labs/lab-chart-model";
import { ferritinAge51Segments, ferritinFemaleHistory, historyFixture, zoneFixture } from "./fixtures/labs";

describe("Lab chart geometry", () => {
  it("sorts a copy of newest-first history and retains all 120 results", () => {
    const ascending = historyFixture(120);
    const input = [...ascending].reverse();
    const before = structuredClone(input);
    const g = chartGeometry(input, zoneFixture, 360, 240);
    expect(g.points.map(p => p.id)).toEqual(ascending.map(p => p.id));
    expect(input).toEqual(before);
    expect(g.points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y))).toBe(true);
  });
  it("returns empty geometry without results", () => {
    expect(chartGeometry([], [], 360, 240)).toEqual({ points: [], bands: [], ticks: [] });
  });
  it("centers one point with deterministic padding and full-width one-day bands", () => {
    const point = ferritinFemaleHistory[0];
    const segments = [{ ...ferritinAge51Segments[0], to_date_exclusive: "2020-01-02" }];
    const g = chartGeometry([point], segments, 360, 240);
    expect(g).toEqual(chartGeometry([point], segments, 360, 240));
    expect(g.points).toHaveLength(1);
    expect(g.points[0].x).toBe((g.bands[0].fromX + g.bands[0].toX) / 2);
    expect(g.bands[0].fromX).toBeLessThan(g.bands[0].toX);
  });
  it.each(["9".repeat(128), `0.${"0".repeat(125)}1`, "0", "1.0000000000000000000000000001"])("keeps finite coordinates for extreme or collapsed decimal %s", value => {
    const points = historyFixture(2).map(p => ({ ...p, display_value: value }));
    const original = structuredClone(points);
    for (const [width, height] of [[360, 240], [0, 0]]) {
      const g = chartGeometry(points, [], width, height);
      expect(g.points).toHaveLength(2);
      expect(g.points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y))).toBe(true);
      expect(g.ticks.every(t => Number.isFinite(t.position) && t.label.length <= 16)).toBe(true);
    }
    expect(points).toEqual(original);
  });
  it("changes bands at exact supplied half-open dates and keeps historical finite bounds", () => {
    const g = chartGeometry(ferritinFemaleHistory, ferritinAge51Segments, 360, 240);
    const ratio = (Date.UTC(2021, 0, 1) - Date.UTC(2020, 0, 1)) / (Date.UTC(2022, 0, 1) - Date.UTC(2020, 0, 1));
    const x = g.points[0].x + ratio * (g.points[1].x - g.points[0].x);
    expect(g.bands).toHaveLength(6);
    for (const b of g.bands.slice(0, 3)) expect(b.toX).toBeCloseTo(x, 8);
    for (const b of g.bands.slice(3)) expect(b.fromX).toBeCloseTo(x, 8);
    expect(g.bands.map(b => b.statusCode)).toEqual(["low", "in_range", "high", "low", "in_range", "high"]);
    expect(g.bands[5].lowY).toBeGreaterThan(g.bands[5].highY);
    expect(g.bands[2].lowY).toBeGreaterThan(g.bands[5].lowY);
    // Unbounded zones terminate at the numeric axis edges, not invented thresholds.
    const ys = g.ticks.filter(t => t.axis === "y").map(t => t.position);
    expect(g.bands[0].lowY).toBe(Math.max(...ys));
    expect(g.bands[2].highY).toBe(Math.min(...ys));
  });
  it("includes a larger bound in an older segment even when latest bounds shrink", () => {
    const segments = structuredClone(ferritinAge51Segments);
    segments[0].zones[1].high = "9999";
    segments[0].zones[2].low = "9999";
    const g = chartGeometry(ferritinFemaleHistory, segments, 360, 240);
    expect(g.bands[2].lowY).toBeGreaterThan(g.bands[2].highY);
    expect(g.bands[2].lowY).toBeLessThan(g.bands[5].lowY);
  });
  it("gives the final birthday segment its full positive calendar width when the newest point starts it", () => {
    const points = ferritinFemaleHistory.map((point, index) => ({ ...point, test_date: index ? "2021-01-01" : "2020-12-31" }));
    const segments = [
      { ...ferritinAge51Segments[0], from_date: "2020-12-31" },
      { ...ferritinAge51Segments[1], to_date_exclusive: "2021-01-02" },
    ];
    const g = chartGeometry(points, segments, 360, 240);
    expect(g.bands).toHaveLength(6);
    for (const band of g.bands.slice(3)) {
      expect(band.fromX).toBe(g.points[1].x);
      expect(band.toX).toBeGreaterThan(band.fromX);
      // Both neighboring spans are exactly one supplied calendar day.
      expect(band.toX - band.fromX).toBeCloseTo(g.points[1].x - g.points[0].x, 8);
    }
  });
});
