import React, { type ReactNode } from "react";
import type { LabTestDetailResponse } from "@/lib/types";
import { LabHistoryChart } from "./lab-history-chart";
import { LabHistoryList } from "./lab-history-list";
import styles from "./labs.module.css";

export function LabTestView(props: { detail: LabTestDetailResponse; selectedResultId: string | null; onSelectResult: (id: string) => void; ownerActions?: ReactNode }) {
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
      <p role="status" aria-live="polite" className={styles.exactValue}><time dateTime={date} dir="ltr">{date}</time>
        {selected ? <> — <bdi dir="ltr">{selected.display_is_approximate ? "≈ " : ""}{selected.display_value} {selected.display_unit}</bdi> — {selected.status.label_ar}</> : null}
      </p>
      <ul className={styles.referenceZones}>{zones.map((zone, index) => <li key={index} data-reference-zone={zone.status.code}>
        <span className={styles.status} data-tone={zone.status.tone}>{zone.status.label_ar}</span>
        <span className={styles.exactValue}>{zone.low === null ? "بلا حد أدنى" : <bdi dir="ltr">{zone.low_inclusive ? "≥" : ">"} {zone.low} {detail.test.canonical_unit}</bdi>}
          {" ؛ "}{zone.high === null ? "بلا حد أعلى" : <bdi dir="ltr">{zone.high_inclusive ? "≤" : "<"} {zone.high} {detail.test.canonical_unit}</bdi>}</span>
      </li>)}</ul>
      {detail.test.fasting_assumption === "fasting" ? <p>يفترض هذا التحليل الصيام.</p> : null}
    </section>
    <LabHistoryList results={detail.results} selectedResultId={selectedId} onSelectResult={onSelectResult} />
  </div>;
}
