import type { LabChartZoneSegment, LabResultResponse } from "@/lib/types";

export type ChartGeometry = {
  points: { id: string; x: number; y: number }[];
  bands: { fromX: number; toX: number; lowY: number; highY: number; statusCode: string }[];
  ticks: { axis: "x" | "y"; position: number; label: string }[];
};

export function chartGeometry(results: LabResultResponse[], segments: LabChartZoneSegment[], width: number, height: number): ChartGeometry {
  if (!results.length) return { points: [], bands: [], ticks: [] };
  const ordered = [...results].sort((a, b) => a.test_date.localeCompare(b.test_date) || a.id.localeCompare(b.id));
  const date = (value: string) => Date.parse(`${value}T00:00:00Z`);
  const left = 60, right = Math.max(160, width) - 24;
  const top = 20, bottom = Math.max(120, height) - 38;
  const first = date(ordered[0].test_date), last = date(ordered.at(-1)!.test_date);
  const singleDate = first === last;
  const x = (value: number) => singleDate ? (left + right) / 2 : left + (value - first) / (last - first) * (right - left);
  // Number is confined to linear drawing coordinates; these are never medical decisions.
  let min = Number(ordered[0].display_value), max = min;
  const include = (value: string) => { min = Math.min(min, Number(value)); max = Math.max(max, Number(value)); };
  for (const result of ordered) include(result.display_value);
  for (const segment of segments) for (const zone of segment.zones) {
    if (zone.low !== null) include(zone.low);
    if (zone.high !== null) include(zone.high);
  }
  const padding = (max - min || Math.abs(max) || 1) * 0.1;
  min -= padding; max += padding;
  const y = (value: number) => bottom - (value - min) / (max - min) * (bottom - top);
  const bands = segments.flatMap(segment => {
    const start = date(segment.from_date), end = date(segment.to_date_exclusive);
    if (singleDate ? start > first || end <= first : start > last || end <= first) return [];
    const fromX = singleDate ? left : x(Math.max(first, start));
    const toX = singleDate ? right : x(Math.min(last, end));
    return segment.zones.map(zone => ({ fromX, toX,
      lowY: zone.low === null ? bottom : y(Number(zone.low)),
      highY: zone.high === null ? top : y(Number(zone.high)), statusCode: zone.status.code,
    }));
  });
  const ticks: ChartGeometry["ticks"] = [0, 0.5, 1].map(ratio => {
    const value = min + (max - min) * ratio;
    const label = value === 0 ? "0" : Math.abs(value) >= 1e6 || Math.abs(value) < 0.001 ? value.toExponential(2) : Number(value.toPrecision(4)).toString();
    return { axis: "y", position: bottom - ratio * (bottom - top), label };
  });
  for (const time of singleDate ? [first] : [first, last]) ticks.push({ axis: "x", position: x(time), label: new Date(time).toISOString().slice(0, 10) });
  return { points: ordered.map(result => ({ id: result.id, x: x(date(result.test_date)), y: y(Number(result.display_value)) })), bands, ticks };
}
