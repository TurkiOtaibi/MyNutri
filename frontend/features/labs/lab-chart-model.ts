import type { LabChartZoneSegment, LabResultResponse } from "@/lib/types";

type LabZone = LabResultResponse["reference_zones"][number];

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
  // Preserve the final supplied half-open interval even when it starts at the newest result.
  const domainEnd = segments.reduce((end, segment) => Math.max(end, date(segment.to_date_exclusive)), last);
  const x = (value: number) => singleDate ? (left + right) / 2 : left + (value - first) / (domainEnd - first) * (right - left);
  // Number is confined to linear drawing coordinates; these are never medical decisions.
  let min = Number(ordered[0].display_value), max = min;
  const include = (value: string) => { min = Math.min(min, Number(value)); max = Math.max(max, Number(value)); };
  for (const result of ordered) include(result.display_value);
  for (const segment of segments) for (const zone of segment.zones) {
    if (zone.low !== null) include(zone.low);
    if (zone.high !== null) include(zone.high);
  }
  const nonNegative = min >= 0;
  const padding = (max - min || Math.abs(max) || 1) * 0.1;
  min -= padding; max += padding;
  // Lab values here are never negative; padding must not invent a negative axis.
  if (nonNegative) min = Math.max(0, min);
  const y = (value: number) => bottom - (value - min) / (max - min) * (bottom - top);
  const bands = segments.flatMap(segment => {
    const start = date(segment.from_date), end = date(segment.to_date_exclusive);
    if (singleDate ? start > first || end <= first : start > last || end <= first) return [];
    const fromX = singleDate ? left : x(Math.max(first, start));
    const toX = singleDate ? right : x(Math.min(domainEnd, end));
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

export type RangeBarGeometry = {
  segments: { from: number; to: number; tone: string }[];
  marker: number | null;
};

// Equal-width segments keep narrow clinical zones readable; the marker is placed
// proportionally inside its own zone. Open-ended zones extend by the widest closed span.
export function rangeBarGeometry(zones: LabZone[], value: string | null): RangeBarGeometry | null {
  if (!zones.length) return null;
  const ordered = [...zones].sort((a, b) => (a.low === null ? -Infinity : Number(a.low)) - (b.low === null ? -Infinity : Number(b.low)));
  const width = 100 / ordered.length;
  const bounds = ordered.flatMap(zone => [zone.low, zone.high]).filter((bound): bound is string => bound !== null).map(Number);
  const span = bounds.length > 1 ? Math.max(...bounds) - Math.min(...bounds) : Math.abs(bounds[0] ?? 1) || 1;
  const segments = ordered.map((zone, index) => ({ from: index * width, to: (index + 1) * width, tone: zone.status.tone }));
  if (value === null) return { segments, marker: null };
  const number = Number(value);
  if (!Number.isFinite(number)) return { segments, marker: null };
  const index = ordered.findIndex(zone => (zone.low === null || number >= Number(zone.low)) && (zone.high === null || number <= Number(zone.high)));
  if (index < 0) return { segments, marker: null };
  const zone = ordered[index];
  const low = zone.low === null ? Number(zone.high) - span : Number(zone.low);
  const high = zone.high === null ? Number(zone.low) + span : Number(zone.high);
  const fraction = high > low ? Math.min(1, Math.max(0, (number - low) / (high - low))) : 0.5;
  // Keep the marker inside the bar so it never touches the rounded ends.
  return { segments, marker: Math.min(97, Math.max(3, index * width + fraction * width)) };
}
