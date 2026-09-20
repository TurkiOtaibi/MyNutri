import React, { useId, useRef } from "react";
import type { LabTestDetailResponse } from "@/lib/types";
import { chartGeometry } from "./lab-chart-model";
import styles from "./labs.module.css";

export function LabHistoryChart({ detail, selectedResultId, onSelectResult }: {
  detail: LabTestDetailResponse; selectedResultId: string | null; onSelectResult: (id: string) => void;
}) {
  const labelId = useId(), captionId = useId();
  const controls = useRef(new Map<string, HTMLButtonElement>());
  const geometry = chartGeometry(detail.results, detail.chart_zones, 360, 240);
  const results = new Map(detail.results.map(result => [result.id, result]));
  const statuses = new Map(detail.chart_zones.flatMap(segment => segment.zones.map(zone => [zone.status.code, zone.status] as const)));
  const selected = selectedResultId ?? detail.results[0]?.id;
  return <figure className={styles.historyFigure} aria-labelledby={labelId} aria-describedby={captionId}>
    <h2 id={labelId}>سجل النتائج عبر الزمن</h2>
    {geometry.points.length ? <>
      <div className={styles.chartUnit} aria-label={`القيمة (${detail.test.canonical_unit})`}>القيمة (<bdi dir="ltr">{detail.test.canonical_unit}</bdi>)</div>
      <div className={styles.chartPlot} dir="ltr">
        <svg viewBox="0 0 360 240" preserveAspectRatio="none" role="img" aria-label="الرسم التاريخي للنتائج والقيم المرجعية للنظام">
          <g role="group" aria-label="نقاط النتائج ونطاقات القيم المرجعية">
            {geometry.bands.map((band, index) => <rect key={index} data-chart-band={band.statusCode} data-tone={statuses.get(band.statusCode)?.tone} className={styles.chartBand}
              x={band.fromX} y={band.highY} width={band.toX - band.fromX} height={band.lowY - band.highY} />)}
            {geometry.ticks.map((tick, index) => <g key={index}>
              {tick.axis === "y" ? <><line x1="60" x2="336" y1={tick.position} y2={tick.position} className={styles.chartGrid} /><text x="54" y={tick.position + 4} textAnchor="end">{tick.label}</text></>
                : <text x={tick.position} y="226" textAnchor={index === geometry.ticks.length - 1 && geometry.points.length > 1 ? "end" : "middle"}>{tick.label}</text>}
            </g>)}
            {geometry.points.length > 1 ? <polyline className={styles.chartLine} points={geometry.points.map(point => `${point.x},${point.y}`).join(" ")} /> : null}
          </g>
        </svg>
        {geometry.points.map((point, index) => {
          const result = results.get(point.id)!;
          return <button key={point.id} type="button" data-chart-point={point.id} className={styles.chartPoint}
            ref={node => { if (node) controls.current.set(point.id, node); else controls.current.delete(point.id); }}
            style={{ left: `${point.x / 360 * 100}%`, top: `${point.y / 240 * 100}%` }}
            aria-label={`${result.test_date}، ${result.display_value} ${result.display_unit}، ${result.status.label_ar}`}
            aria-pressed={point.id === selected} tabIndex={point.id === selected ? 0 : -1}
            onClick={() => onSelectResult(point.id)} onFocus={() => onSelectResult(point.id)}
            onKeyDown={event => {
              const target = event.key === "Home" ? 0 : event.key === "End" ? geometry.points.length - 1
                : event.key === "ArrowLeft" ? Math.max(0, index - 1) : event.key === "ArrowRight" ? Math.min(geometry.points.length - 1, index + 1) : null;
              if (target !== null) { event.preventDefault(); controls.current.get(geometry.points[target].id)?.focus(); }
            }}><span aria-hidden="true" /></button>;
        })}
      </div>
    </> : <p className={styles.empty}>لا توجد نتائج مسجلة لهذا التحليل.</p>}
    <figcaption id={captionId}>التاريخ من الأقدم يسارًا إلى الأحدث يمينًا. اختر نقطة لعرض القيم المرجعية في تاريخها. السجل الكامل متاح أدناه.</figcaption>
  </figure>;
}
