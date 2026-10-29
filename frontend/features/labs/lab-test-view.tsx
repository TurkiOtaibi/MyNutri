import React, { type ReactNode } from "react";
import type { LabResultResponse, LabTestDetailResponse } from "@/lib/types";
import { rangeBarGeometry } from "./lab-chart-model";
import { LabHistoryChart } from "./lab-history-chart";
import { LabHistoryList } from "./lab-history-list";
import { formatGregorianArabicDate } from "@/lib/dates";
import styles from "./labs.module.css";

export function LabTestView(props: { detail: LabTestDetailResponse; selectedResultId: string | null; onSelectResult: (id: string) => void; ownerActions?: ReactNode; ownerResultActions?: (result: LabResultResponse) => ReactNode }) {
  const { detail, onSelectResult, ownerActions } = props;
  const selected = detail.results.find(result => result.id === props.selectedResultId) ?? detail.results[0];
  const selectedId = selected?.id ?? null;
  const date = selected?.test_date ?? detail.reference_at_date;
  const zones = selected?.reference_zones ?? detail.reference_zones;
  return <div className={styles.labsPage} data-testid="lab-detail" dir="rtl">
    <header className={styles.heading}><div><h1>{detail.test.name_ar}</h1><p><bdi dir="ltr">{detail.test.name_en}</bdi></p></div>
      {detail.read_only ? <strong>للقراءة فقط</strong> : detail.eligibility.allowed ? ownerActions : null}
    </header>
    <LabHistoryChart detail={detail} selectedResultId={selectedId} onSelectResult={onSelectResult} />
    <section className={styles.referencePanel} aria-label="القيم المرجعية للنظام" data-reference-date={date}>
      <h2>القيم المرجعية للنظام</h2>
      <p role="status" aria-live="polite" className={styles.exactValue}><time dateTime={date}>{formatGregorianArabicDate(date)}</time>
        {selected ? <> — <bdi dir="ltr">{selected.display_is_approximate ? "≈ " : ""}{selected.display_value} {selected.display_unit}</bdi> — {selected.status.label_ar}</> : null}
      </p>
      {selected ? <LabRangeBar zones={zones} value={selected.display_unit === detail.test.canonical_unit ? selected.display_value : null} /> : null}
      {selected && (selected.status.tone === "outside" || selected.status.tone === "caution") ? <p>هذه القيم للمتابعة فقط، ولا تغني عن استشارة الطبيب.</p> : null}
      <ul className={styles.referenceZones}>{zones.map((zone, index) => <li key={index} data-reference-zone={zone.status.code}>
        <span className={styles.status} data-tone={zone.status.tone}>{zone.status.label_ar}</span>
        <span className={styles.exactValue}>{zone.low === null ? "بلا حد أدنى" : <bdi dir="ltr">{zone.low_inclusive ? "≥" : ">"} {zone.low} {detail.test.canonical_unit}</bdi>}
          {" ؛ "}{zone.high === null ? "بلا حد أعلى" : <bdi dir="ltr">{zone.high_inclusive ? "≤" : "<"} {zone.high} {detail.test.canonical_unit}</bdi>}</span>
      </li>)}</ul>
      {detail.test.fasting_assumption === "fasting" ? <p>يفترض هذا التحليل الصيام.</p> : null}
    </section>
    <LabHistoryList results={detail.results} selectedResultId={selectedId} onSelectResult={onSelectResult} ownerResultActions={detail.read_only ? undefined : props.ownerResultActions} />
  </div>;
}

// Decorative summary of the governed reference list below it; screen readers use the list.
function LabRangeBar({ zones, value }: { zones: LabResultResponse["reference_zones"]; value: string | null }) {
  const geometry = rangeBarGeometry(zones, value);
  if (!geometry) return null;
  return <div className={styles.rangeBar} aria-hidden="true" dir="ltr" data-testid="lab-range-bar">
    <span className={styles.rangeTrack}>{geometry.segments.map((segment, index) => <span key={index} className={styles.rangeSegment} data-tone={segment.tone}
      style={{ left: `${segment.from}%`, width: `${segment.to - segment.from}%` }} />)}</span>
    {geometry.marker === null ? null : <span className={styles.rangeMarker} style={{ left: `${geometry.marker}%` }} />}
  </div>;
}
