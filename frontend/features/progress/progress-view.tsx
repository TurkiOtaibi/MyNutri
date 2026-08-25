import { AlertTriangle, BarChart3, CheckCircle2, Flag, History, RefreshCw } from "lucide-react";
import type { KeyboardEventHandler, RefObject } from "react";

import type {
  BehaviorGoal,
  BehaviorGoalHistory,
  PatternAnalysisHistory,
  PatternAnalysisResponse,
  WeeklyPriorityResult
} from "@/lib/types";
import {
  ANALYSIS_COPY,
  displayState,
  formatMetricValue,
  goalActionCopy,
  goalStateCopy,
  metricLabel,
  metricStatusText,
  PRIORITY_COPY,
  type GoalEditTerms,
  priorityMessage,
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
  priority: WeeklyPriorityResult | null;
  priorityLoading: boolean;
  priorityError: boolean;
  displayWeeklyPriority: boolean;
  goalUnavailableReason: "action_not_observable" | null;
  goal: BehaviorGoal | null;
  goalHistory: BehaviorGoalHistory | undefined;
  goalHistoryLoading: boolean;
  goalHistoryError: boolean;
  goalCommandPending: boolean;
  goalError: string;
  goalHeadingRef: RefObject<HTMLHeadingElement | null>;
  goalErrorRef: RefObject<HTMLDivElement | null>;
  announcement: string;
  pendingGoalAction: BehaviorGoal["allowed_actions"][number] | null;
  goalTerms: GoalEditTerms;
  dialogRef: RefObject<HTMLDivElement | null>;
  cancelRef: RefObject<HTMLButtonElement | null>;
  onEvaluate: () => void;
  onRetryLoad: () => void;
  onRetryHistory: () => void;
  onRetryPriority: () => void;
  onRequestGoalCommand: (action: BehaviorGoal["allowed_actions"][number]) => void;
  onCancelGoalCommand: () => void;
  onConfirmGoalCommand: (terms: GoalEditTerms) => void;
  onGoalTermsChange: (terms: GoalEditTerms) => void;
  onDialogKeyDown: KeyboardEventHandler<HTMLDivElement>;
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
  priority,
  priorityLoading,
  priorityError,
  displayWeeklyPriority,
  goalUnavailableReason,
  goal,
  goalHistory,
  goalHistoryLoading,
  goalHistoryError,
  goalCommandPending,
  goalError,
  goalHeadingRef,
  goalErrorRef,
  announcement,
  pendingGoalAction,
  goalTerms,
  dialogRef,
  cancelRef,
  onEvaluate,
  onRetryLoad,
  onRetryHistory,
  onRetryPriority,
  onRequestGoalCommand,
  onCancelGoalCommand,
  onConfirmGoalCommand,
  onGoalTermsChange,
  onDialogKeyDown
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

      {displayWeeklyPriority ? <section className={styles.prioritySection} aria-labelledby="weekly-priority-heading" aria-busy={priorityLoading}>
        <div className={styles.sectionHeading}>
          <Flag aria-hidden="true" />
          <h2 id="weekly-priority-heading">{PRIORITY_COPY.heading}</h2>
        </div>
        {priorityLoading ? <div className={styles.stateCard} role="status">{PRIORITY_COPY.loading}</div> : null}
        {priorityError ? (
          <div className={styles.errorCard} role="alert" tabIndex={-1}>
            <AlertTriangle aria-hidden="true" />
            <p>{PRIORITY_COPY.failure}</p>
            <button type="button" onClick={onRetryPriority}>إعادة المحاولة</button>
          </div>
        ) : null}
        {!priorityLoading && !priorityError && priority?.status === "selected" && priority.main ? (
          <article className={styles.priorityCard}>
            <p className={styles.eyebrow}>الأولوية الرئيسية</p>
            <h3>{priority.main.title_ar}</h3>
            <p>{priority.main.reason_ar}</p>
            <p className={styles.priorityAction}>{priority.main.action_ar}</p>
            <p className={styles.metricEvidence}>{PRIORITY_COPY.evidence}</p>
            {priority.secondary ? (
              <div className={styles.secondaryPriority}>
                <strong>أولوية مساندة: {priority.secondary.title_ar}</strong>
                <span>{priority.secondary.action_ar}</span>
              </div>
            ) : null}
          </article>
        ) : null}
        {!priorityLoading && !priorityError && (!priority || priority.status !== "selected") ? (
          <div className={styles.stateCard}><p>{priorityMessage(priority)}</p></div>
        ) : null}

        {goal ? (
          <article className={styles.goalCard} aria-labelledby="behavior-goal-heading">
            <h3 id="behavior-goal-heading" ref={goalHeadingRef} tabIndex={-1}>{goalStateCopy[goal.state]}</h3>
            <p>{PRIORITY_COPY.offer === goalStateCopy[goal.state] ? priority?.main?.action_ar : priority?.main?.action_ar ?? "خطوة أسبوعية محفوظة"}</p>
            <div className={styles.goalProgress} aria-label="تقدم الهدف">
              <span><bdi>{goal.progress.progress_count}</bdi> من <bdi>{goal.weekly_target_count}</bdi> أيام</span>
              <progress value={goal.progress.progress_percent ?? 0} max={100}>{goal.progress.progress_percent ?? 0}%</progress>
            </div>
            <p className={styles.metricEvidence}>
              <bdi>{goal.window_start}</bdi> — <bdi>{goal.window_end}</bdi>
            </p>
            {goalError && !pendingGoalAction ? (
              <div className={styles.goalError} role="alert" ref={goalErrorRef} tabIndex={-1}>
                <AlertTriangle aria-hidden="true" />
                <span>{goalError}</span>
              </div>
            ) : null}
            <div className={styles.goalActions}>
              {goal.allowed_actions.map((action) => (
                <button
                  key={action}
                  type="button"
                  disabled={goalCommandPending}
                  onClick={() => onRequestGoalCommand(action)}
                >
                  {goalActionCopy[action]}
                </button>
              ))}
            </div>
          </article>
        ) : null}
        {pendingGoalAction ? (
          <div
            className={styles.dialogBackdrop}
            role="presentation"
            onKeyDown={onDialogKeyDown}
          >
            <div
              className={styles.commandDialog}
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-labelledby="goal-command-dialog-title"
            >
              <h3 id="goal-command-dialog-title">تأكيد الإجراء</h3>
              <p>هل تريد {goalActionCopy[pendingGoalAction]}؟ يمكنك الإلغاء دون تغيير الهدف.</p>
              {pendingGoalAction === "change" && priority?.main?.goal_trackability === "informational_only" ? (
                <p className={styles.metricEvidence}>{PRIORITY_COPY.informationalOnly}</p>
              ) : null}
              {(["accept", "edit", "change", "reduce"].includes(pendingGoalAction)
                && !(pendingGoalAction === "change" && priority?.main?.goal_trackability === "informational_only")) ? (
                <div className={styles.goalEditor}>
                  <label>
                    عدد الأيام المستهدف
                    <input
                      type="number"
                      min={1}
                      max={pendingGoalAction === "reduce" ? Math.max(1, (goal?.weekly_target_count ?? 2) - 1) : 7}
                      value={goalTerms.weeklyTargetCount}
                      onChange={(event) => onGoalTermsChange({
                        ...goalTerms,
                        weeklyTargetCount: Number(event.target.value)
                      })}
                    />
                  </label>
                  <fieldset>
                    <legend>أيام المتابعة الاختيارية</legend>
                    {["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"].map((label, day) => (
                      <label key={label}>
                        <input
                          type="checkbox"
                          checked={goalTerms.scheduledDayMask.includes(day)}
                          onChange={() => onGoalTermsChange({
                            ...goalTerms,
                            scheduledDayMask: goalTerms.scheduledDayMask.includes(day)
                              ? goalTerms.scheduledDayMask.filter((value) => value !== day)
                              : [...goalTerms.scheduledDayMask, day].sort()
                          })}
                        />
                        {label}
                      </label>
                    ))}
                  </fieldset>
                  <label>
                    التذكير داخل التطبيق
                    <select
                      value={goalTerms.reminderPreference}
                      onChange={(event) => onGoalTermsChange({
                        ...goalTerms,
                        reminderPreference: event.target.value as "enabled" | "disabled"
                      })}
                    >
                      <option value="disabled">بدون تذكير</option>
                      <option value="enabled">تذكير محكوم</option>
                    </select>
                  </label>
                  <label>
                    ملاحظة خاصة
                    <textarea
                      maxLength={280}
                      value={goalTerms.note}
                      onChange={(event) => onGoalTermsChange({ ...goalTerms, note: event.target.value })}
                    />
                  </label>
                </div>
              ) : null}
              {goalError ? (
                <div className={styles.goalError} role="alert" ref={goalErrorRef} tabIndex={-1}>
                  <AlertTriangle aria-hidden="true" />
                  <span>{goalError}</span>
                </div>
              ) : null}
              <div className={styles.goalActions}>
                <button ref={cancelRef} type="button" onClick={onCancelGoalCommand}>إلغاء</button>
                <button type="button" onClick={() => onConfirmGoalCommand(goalTerms)} disabled={goalCommandPending}>تأكيد</button>
              </div>
            </div>
          </div>
        ) : null}
        {!goal && priority?.status === "selected" && !priorityLoading ? (
          <p className={styles.stateCard}>
            {goalUnavailableReason === "action_not_observable"
              ? priority.main?.goal_unavailable_copy_ar ?? PRIORITY_COPY.informationalOnly
              : PRIORITY_COPY.offer}
          </p>
        ) : null}

        <section className={styles.goalHistory} aria-labelledby="goal-history-heading">
          <h3 id="goal-history-heading">سجل الأهداف الأسبوعية</h3>
          {goalHistoryLoading ? <p role="status">جارٍ تحميل سجل الأهداف…</p> : null}
          {goalHistoryError ? <p role="alert">تعذر تحميل سجل الأهداف.</p> : null}
          {!goalHistoryLoading && !goalHistoryError && goalHistory?.items.length === 0 ? <p>لا توجد أهداف سابقة.</p> : null}
          {goalHistory?.items.length ? (
            <ol>
              {goalHistory.items.map((item) => (
                <li key={item.goal_id}>
                  <span>{goalStateCopy[item.state]}</span>
                  <bdi>{item.window_start} — {item.window_end}</bdi>
                </li>
              ))}
            </ol>
          ) : null}
        </section>
      </section> : null}

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
              <p>
                <bdi>{analysis.period_start}</bdi> — <bdi>{analysis.period_end}</bdi>
              </p>
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
                <p className={styles.metricStatus}>
                  <span aria-hidden="true">●</span> {metricStatusText(metric)}
                </p>
                <p className={styles.metricEvidence}>
                  تغطية الدليل <bdi>{metric.current.coverage_percent ?? 0}%</bdi>
                </p>
              </article>
            ))}
          </section>
          <section className={styles.history} aria-labelledby="analysis-history-heading">
            <h2 id="analysis-history-heading" ref={historyHeadingRef} tabIndex={-1}><History aria-hidden="true" /> {ANALYSIS_COPY.history}</h2>
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
        {announcement || (evaluating ? ANALYSIS_COPY.loading : actionError || (analysis ? "تم تحديث التحليل" : ""))}
      </span>
    </div>
  );
}
