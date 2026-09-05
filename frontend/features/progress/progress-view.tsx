import { AlertTriangle, BarChart3, CheckCircle2, History, RefreshCw } from "lucide-react";
import type { RefObject } from "react";

import type { PatternAnalysisHistory, PatternAnalysisResponse } from "@/lib/types";
import {
  ANALYSIS_COPY,
  displayState,
  formatMetricValue,
  metricLabel,
  metricStatusText,
  visibleMetrics
} from "./progress-model";
import styles from "./progress.module.css";

type ProgressViewProps = {
  analysis: PatternAnalysisResponse | null;
  history: PatternAnalysisHistory | undefined;
  historyLoading: boolean;
  historyError: boolean;
  loading: boolean;
  loadError: boolean;
  evaluating: boolean;
  actionError: string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  errorRef: RefObject<HTMLDivElement | null>;
  historyErrorRef: RefObject<HTMLDivElement | null>;
  historyHeadingRef: RefObject<HTMLHeadingElement | null>;
  onEvaluate: () => void;
  onRetryLoad: () => void;
  onRetryHistory: () => void;
};

export function ProgressView({
  analysis,
  history,
  historyLoading,
  historyError,
  loading,
  loadError,
  evaluating,
  actionError,
  headingRef,
  errorRef,
  historyErrorRef,
  historyHeadingRef,
  onEvaluate,
  onRetryLoad,
  onRetryHistory
}: ProgressViewProps) {
  const state = displayState(analysis);
  const metrics = analysis ? visibleMetrics(analysis) : [];
  return (
    <div className={styles.page} dir="rtl" aria-busy={loading || evaluating}>
      <section className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>التقدم</p>
          <h1 ref={headingRef} tabIndex={-1}>{ANALYSIS_COPY.heading}</h1>
          <p>عرض يعتمد على الأيام المكتملة وحقائق التغذية المحفوظة.</p>
        </div>
        <button className={styles.primaryAction} type="button" onClick={onEvaluate} disabled={evaluating}>
          <RefreshCw aria-hidden="true" size={20} className={evaluating ? styles.spinning : undefined} />
          {evaluating ? ANALYSIS_COPY.loading : ANALYSIS_COPY.evaluate}
        </button>
      </section>

      {loading ? <div className={styles.stateCard} role="status">{ANALYSIS_COPY.loading}</div> : null}
      {loadError ? (
        <div className={styles.errorCard} role="alert" ref={errorRef} tabIndex={-1}>
          <AlertTriangle aria-hidden="true" />
          <p>{ANALYSIS_COPY.failure}</p>
          <button type="button" onClick={onRetryLoad}>إعادة المحاولة</button>
        </div>
      ) : null}
      {actionError ? (
        <div className={styles.errorCard} role="alert" ref={errorRef} tabIndex={-1}>
          <AlertTriangle aria-hidden="true" />
          <p>{actionError}</p>
        </div>
      ) : null}

      {!loading && !loadError && state === "empty" ? (
        <div className={styles.stateCard}>
          <BarChart3 aria-hidden="true" />
          <h2>{ANALYSIS_COPY.insufficient}</h2>
          <p>أكمل أربعة أيام على الأقل ثم حدّث التحليل.</p>
        </div>
      ) : null}

      {analysis ? (
        <>
          {state === "stale" ? (
            <div className={styles.notice} role="status">
              <AlertTriangle aria-hidden="true" />
              <span>{ANALYSIS_COPY.stale}</span>
            </div>
          ) : null}
          {state === "unsafe" ? (
            <div className={styles.notice} role="status">
              <AlertTriangle aria-hidden="true" />
              <span>تعذر استخدام بعض النتائج بأمان. راجع حالة البيانات والهدف.</span>
            </div>
          ) : null}
          <section aria-labelledby="analysis-period-heading" className={styles.summaryCard}>
            <div>
              <h2 id="analysis-period-heading">الفترة الحالية</h2>
              <p><bdi>{analysis.period_start}</bdi> — <bdi>{analysis.period_end}</bdi></p>
            </div>
            <div className={styles.completeCount}>
              <CheckCircle2 aria-hidden="true" />
              <span><bdi>{analysis.complete_day_count}</bdi> من ٧ أيام مكتملة</span>
            </div>
          </section>
          <section className={styles.metricGrid} aria-label="حقائق تحليل نمط التغذية">
            {metrics.map((metric) => (
              <article className={styles.metricCard} key={metric.metric_key}>
                <h2>{metricLabel(metric.metric_key)}</h2>
                <p className={styles.metricValue}><bdi>{formatMetricValue(metric)}</bdi></p>
                <p className={styles.metricStatus}><span aria-hidden="true">●</span> {metricStatusText(metric)}</p>
                <p className={styles.metricEvidence}>تغطية الدليل <bdi>{metric.current.coverage_percent ?? 0}%</bdi></p>
              </article>
            ))}
          </section>
          <section className={styles.history} aria-labelledby="analysis-history-heading">
            <h2 id="analysis-history-heading" ref={historyHeadingRef} tabIndex={-1}>
              <History aria-hidden="true" /> {ANALYSIS_COPY.history}
            </h2>
            {historyLoading ? <p role="status">جارٍ تحميل سجل التحليلات…</p> : null}
            {historyError ? (
              <div role="alert" ref={historyErrorRef} tabIndex={-1}>
                <p>تعذر تحميل سجل التحليلات.</p>
                <button type="button" onClick={onRetryHistory}>إعادة المحاولة</button>
              </div>
            ) : null}
            {!historyLoading && !historyError && history?.items.length ? (
              <ol>
                {history.items.map((item) => (
                  <li key={`${item.source_analysis_id}-${item.source_analysis_revision}`}>
                    <span>نسخة <bdi>{item.source_analysis_revision}</bdi></span>
                    <span><bdi>{item.period_start}</bdi> — <bdi>{item.period_end}</bdi></span>
                    <span>{item.lifecycle_status === "stale" ? ANALYSIS_COPY.stale : "نسخة محفوظة"}</span>
                  </li>
                ))}
              </ol>
            ) : null}
            {!historyLoading && !historyError && history?.items.length === 0 ? <p>لا توجد نسخ سابقة.</p> : null}
          </section>
        </>
      ) : null}
      <span className="sr-only" aria-live="polite">
        {evaluating ? ANALYSIS_COPY.loading : actionError || (analysis ? "تم تحديث التحليل" : "")}
      </span>
    </div>
  );
}
