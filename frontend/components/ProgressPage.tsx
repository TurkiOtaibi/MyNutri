"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ProgressView } from "@/features/progress/progress-view";
import {
  ANALYSIS_COPY,
  stableAnalysisAttempt,
  type AnalysisAttempt
} from "@/features/progress/progress-model";
import {
  ApiError,
  evaluatePatternAnalysis,
  getCurrentPatternAnalysis,
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
  const attemptRef = useRef<AnalysisAttempt | null>(null);
  const previousSubjectRef = useRef(subject);
  const [actionError, setActionError] = useState("");

  const analysisQuery = useQuery({
    queryKey: ["pattern-analysis", subject],
    queryFn: () => getCurrentPatternAnalysis(accessToken, signal),
    enabled: Boolean(accessToken && subject),
    retry: 1
  });
  const historyQuery = useQuery({
    queryKey: ["pattern-analysis-history", subject],
    queryFn: () => listPatternAnalysisHistory(accessToken, null, 20, signal),
    enabled: Boolean(accessToken && subject)
  });

  useEffect(() => {
    if (previousSubjectRef.current === subject) return;
    previousSubjectRef.current = subject;
    attemptRef.current = null;
    setActionError("");
  }, [subject]);

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

  return (
    <ProgressView
      analysis={analysisQuery.data ?? null}
      history={historyQuery.data}
      loading={analysisQuery.isPending}
      loadError={analysisQuery.isError}
      evaluating={evaluation.isPending}
      actionError={actionError}
      headingRef={headingRef}
      errorRef={errorRef}
      onEvaluate={() => evaluation.mutate()}
      onRetryLoad={() => void analysisQuery.refetch()}
    />
  );
}
