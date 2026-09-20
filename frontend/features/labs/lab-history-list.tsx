import React, { type ReactNode } from "react";
import type { LabResultResponse } from "@/lib/types";
import styles from "./labs.module.css";

export function LabHistoryList({ results, selectedResultId, onSelectResult, ownerResultActions }: {
  results: LabResultResponse[]; selectedResultId: string | null; onSelectResult: (id: string) => void;
  ownerResultActions?: (result: LabResultResponse) => ReactNode;
}) {
  return <section aria-label="السجل الكامل" className={styles.panel}><h2>السجل الكامل</h2>
    <ul className={styles.rows}>{results.map(result => <li key={result.id} className={styles.historyRow} data-history-result={result.id}>
      <button type="button" className="btn" aria-pressed={result.id === selectedResultId} onClick={() => onSelectResult(result.id)}><time dateTime={result.test_date} dir="ltr">{result.test_date}</time></button>
      <span className={styles.exactValue} dir="ltr">{result.display_is_approximate ? "≈ " : ""}{result.display_value} {result.display_unit}</span>
      <span className={styles.status} data-tone={result.status.tone}>{result.status.label_ar}</span>
      {ownerResultActions?.(result)}
    </li>)}</ul>
  </section>;
}
