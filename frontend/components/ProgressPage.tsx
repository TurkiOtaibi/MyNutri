"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ProgressView } from "@/features/progress/progress-view";
import {
  ANALYSIS_COPY,
  stableAnalysisAttempt,
  stableGoalCommandAttempt,
  type AnalysisAttempt,
  type GoalEditTerms,
  type GoalCommandAttempt
} from "@/features/progress/progress-model";
import {
  ApiError,
  commandBehaviorGoal,
  evaluatePatternAnalysis,
  getCurrentBehaviorGoal,
  getCurrentPatternAnalysis,
  getCurrentWeeklyPriority,
  listBehaviorGoalHistory,
  listPatternAnalysisHistory
} from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";

export function ProgressPage() {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const subject = session?.user.id ?? null;
  const signal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const historyErrorRef = useRef<HTMLDivElement>(null);
  const historyHeadingRef = useRef<HTMLHeadingElement>(null);
  const goalHeadingRef = useRef<HTMLHeadingElement>(null);
  const goalErrorRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const attemptRef = useRef<AnalysisAttempt | null>(null);
  const goalAttemptRef = useRef<GoalCommandAttempt | null>(null);
  const previousSubjectRef = useRef(subject);
  const [actionError, setActionError] = useState("");
  const [goalError, setGoalError] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const [pendingGoalAction, setPendingGoalAction] = useState<
    import("@/lib/types").BehaviorGoal["allowed_actions"][number] | null
  >(null);
  const [goalTerms, setGoalTerms] = useState<GoalEditTerms>({
    weeklyTargetCount: 3,
    scheduledDayMask: [],
    reminderPreference: "disabled",
    note: ""
  });

  const analysisQuery = useQuery({
    queryKey: ["pattern-analysis", subject],
    queryFn: () => getCurrentPatternAnalysis(accessToken, signal),
    enabled: Boolean(accessToken && subject),
    retry: 1
  });
  const historyQuery = useQuery({
    queryKey: ["pattern-analysis-history", subject],
    queryFn: () => listPatternAnalysisHistory(accessToken, null, 20, signal),
    enabled: Boolean(accessToken && subject),
    retry: false
  });
  const priorityQuery = useQuery({
    queryKey: ["weekly-priority", subject],
    queryFn: () => getCurrentWeeklyPriority(accessToken, signal),
    enabled: Boolean(accessToken && subject),
    retry: false
  });
  const goalQuery = useQuery({
    queryKey: ["behavior-goal", subject],
    queryFn: () => getCurrentBehaviorGoal(accessToken, signal),
    enabled: Boolean(accessToken && subject),
    retry: false
  });
  const goalHistoryQuery = useQuery({
    queryKey: ["behavior-goal-history", subject],
    queryFn: () => listBehaviorGoalHistory(accessToken, null, 20, signal),
    enabled: Boolean(accessToken && subject),
    retry: false
  });

  useEffect(() => {
    if (previousSubjectRef.current === subject) return;
    previousSubjectRef.current = subject;
    attemptRef.current = null;
    goalAttemptRef.current = null;
    setActionError("");
    setGoalError("");
    setAnnouncement("");
    setPendingGoalAction(null);
  }, [subject]);

  useEffect(() => {
    if (historyQuery.isError && analysisQuery.data) {
      requestAnimationFrame(() => historyErrorRef.current?.focus());
    }
  }, [analysisQuery.data, historyQuery.isError]);

  useEffect(() => {
    if (pendingGoalAction) requestAnimationFrame(() => cancelRef.current?.focus());
  }, [pendingGoalAction]);

  const requestGoalCommand = (action: import("@/lib/types").BehaviorGoal["allowed_actions"][number]) => {
    const goal = goalQuery.data?.goal;
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    setGoalTerms({
      weeklyTargetCount: action === "reduce"
        ? Math.max(1, (goal?.weekly_target_count ?? 2) - 1)
        : goal?.weekly_target_count ?? 3,
      scheduledDayMask: goal?.scheduled_day_mask ?? [],
      reminderPreference: goal?.reminder_preference ?? "disabled",
      note: goal?.owner_note ?? ""
    });
    setPendingGoalAction(action);
  };
  const cancelGoalCommand = () => {
    setPendingGoalAction(null);
    requestAnimationFrame(() => returnFocusRef.current?.focus());
  };
  const trapDialogFocus = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelGoalCommand();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])"
      ) ?? []
    );
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const evaluation = useMutation({
    mutationFn: async () => {
      const attempt = stableAnalysisAttempt(attemptRef.current, analysisQuery.data ?? null);
      attemptRef.current = attempt;
      return evaluatePatternAnalysis(
        attempt.expectedRevision,
        attempt.etag,
        attempt.key,
        accessToken,
        signal
      );
    },
    onSuccess: async (analysis) => {
      attemptRef.current = null;
      setActionError("");
      queryClient.setQueryData(["pattern-analysis", subject], analysis);
      await queryClient.invalidateQueries({ queryKey: ["pattern-analysis-history", subject] });
      headingRef.current?.focus();
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.code === "ANALYSIS_VERSION_CONFLICT") {
        attemptRef.current = null;
        await analysisQuery.refetch();
      }
      setActionError(
        error instanceof ApiError && error.code === "INSUFFICIENT_ANALYSIS_EVIDENCE"
          ? ANALYSIS_COPY.insufficient
          : error instanceof ApiError && error.code === "UNSUPPORTED_HISTORICAL_VERSION"
            ? ANALYSIS_COPY.unsupported
            : ANALYSIS_COPY.failure
      );
      requestAnimationFrame(() => errorRef.current?.focus());
    }
  });

  const goalCommand = useMutation({
    mutationFn: async ({ action, terms }: { action: import("@/lib/types").BehaviorGoal["allowed_actions"][number]; terms?: GoalEditTerms }) => {
      const goal = goalQuery.data?.goal;
      if (!goal) throw new Error("goal unavailable");
      const attempt = stableGoalCommandAttempt(goalAttemptRef.current, goal, action, terms);
      goalAttemptRef.current = attempt;
      return commandBehaviorGoal(attempt.goalId, attempt.command, attempt.key, accessToken, signal);
    },
    onSuccess: async (response) => {
      const replayed = response.idempotent_replayed;
      const unavailableReason = response.recommendation?.main?.goal_unavailable_reason ?? null;
      goalAttemptRef.current = null;
      setGoalError("");
      queryClient.setQueryData(["behavior-goal", subject], {
        goal: unavailableReason === "action_not_observable" ? null : response.goal,
        recommendation: response.recommendation,
        goal_unavailable_reason: unavailableReason
      });
      await queryClient.invalidateQueries({ queryKey: ["behavior-goal-history", subject] });
      if (!replayed) {
        setAnnouncement(response.result === "repeated" || response.result === "reduced_and_repeated"
          ? "بدأ أسبوع جديد للهدف مع الاحتفاظ بنتيجة الأسبوع السابق."
          : "تم تحديث الهدف.");
      }
      goalHeadingRef.current?.focus();
      setPendingGoalAction(null);
    },
    onError: (error) => {
      if (!(error instanceof ApiError && error.code === "IDEMPOTENCY_KEY_REUSED")) {
        goalAttemptRef.current = null;
      }
      setGoalError(error instanceof ApiError ? error.message : "تعذر حفظ الهدف. لم تُفقد بياناتك؛ حاول مجددًا.");
      requestAnimationFrame(() => goalErrorRef.current?.focus());
    }
  });

  return (
    <ProgressView
      analysis={analysisQuery.data ?? null}
      history={historyQuery.data}
      historyLoading={historyQuery.isPending}
      historyError={historyQuery.isError}
      loading={analysisQuery.isPending}
      loadError={analysisQuery.isError}
      evaluating={evaluation.isPending}
      actionError={actionError}
      headingRef={headingRef}
      errorRef={errorRef}
      historyErrorRef={historyErrorRef}
      historyHeadingRef={historyHeadingRef}
      priority={priorityQuery.data ?? goalQuery.data?.recommendation ?? null}
      priorityLoading={priorityQuery.isPending || goalQuery.isPending}
      priorityError={priorityQuery.isError || goalQuery.isError}
      displayWeeklyPriority={
        !(
          priorityQuery.error instanceof ApiError
          && priorityQuery.error.code === "FEATURE_DISABLED"
        )
      }
      goalUnavailableReason={goalQuery.data?.goal_unavailable_reason ?? null}
      goal={goalQuery.data?.goal ?? null}
      goalHistory={goalHistoryQuery.data}
      goalHistoryLoading={goalHistoryQuery.isPending}
      goalHistoryError={goalHistoryQuery.isError}
      goalCommandPending={goalCommand.isPending}
      goalError={goalError}
      goalHeadingRef={goalHeadingRef}
      goalErrorRef={goalErrorRef}
      announcement={announcement}
      pendingGoalAction={pendingGoalAction}
      goalTerms={goalTerms}
      dialogRef={dialogRef}
      cancelRef={cancelRef}
      onEvaluate={() => evaluation.mutate()}
      onRetryLoad={() => void analysisQuery.refetch()}
      onRetryHistory={() => {
        void historyQuery.refetch().then((result) => {
          if (!result.isError) historyHeadingRef.current?.focus();
        });
      }}
      onRetryPriority={() => {
        void Promise.all([priorityQuery.refetch(), goalQuery.refetch(), goalHistoryQuery.refetch()]);
      }}
      onRequestGoalCommand={requestGoalCommand}
      onCancelGoalCommand={cancelGoalCommand}
      onGoalTermsChange={setGoalTerms}
      onDialogKeyDown={trapDialogFocus}
      onConfirmGoalCommand={(terms) => {
        const action = pendingGoalAction;
        const goal = goalQuery.data?.goal;
        if (!action || !goal) return;
        goalCommand.mutate({
          action,
          terms
        });
      }}
    />
  );
}
