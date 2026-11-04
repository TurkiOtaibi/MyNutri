import React, { type ReactNode } from "react";
import { Check } from "lucide-react";
import type { LabResultResponse } from "@/lib/types";
import { formatGregorianArabicDate } from "@/lib/dates";
import styles from "./labs.module.css";

export function LabHistoryList({ results, selectedResultId, onSelectResult, ownerResultActions }: {
  results: LabResultResponse[]; selectedResultId: string | null; onSelectResult: (id: string) => void;
  ownerResultActions?: (result: LabResultResponse) => ReactNode;
}) {
  return <section aria-label="السجل الكامل" className={styles.panel}><h2>السجل الكامل</h2>
    <ul className={styles.rows}>{results.map(result => <li key={result.id} className={styles.historyRow} data-history-result={result.id}>
      <button type="button" className={`btn ${styles.historySelection}`} aria-pressed={result.id === selectedResultId} onClick={() => onSelectResult(result.id)}><time dateTime={result.test_date}>{formatGregorianArabicDate(result.test_date)}</time><Check size={16} aria-hidden="true" /></button>
      <span className={`${styles.exactValue} ${styles.historyValue}`}><bdi dir="ltr">{result.display_is_approximate ? "≈ " : ""}{result.display_value} <small>{result.display_unit}</small></bdi></span>
      <span className={styles.status} data-tone={result.status.tone}>{result.status.label_ar}</span>
      {result.note ? <p className={styles.historyNote}><span>ملاحظة</span>{" "}{result.note}</p> : null}
      {ownerResultActions?.(result)}
    </li>)}</ul>
  </section>;
}
