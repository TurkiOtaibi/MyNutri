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
  const historyErrorRef = useRef<HTMLDivElement>(null);
  const historyHeadingRef = useRef<HTMLHeadingElement>(null);
  const attemptRef = useRef<AnalysisAttempt | null>(null);
  const previousSubjectRef = useRef(subject);
  const [actionError, setActionError] = useState("");

  const analysisQuery = useQuery({
    queryKey: ["pattern-analysis-v2", subject],
    queryFn: () => getCurrentPatternAnalysis(accessToken, signal),
    enabled: Boolean(accessToken && subject),
    retry: 1
  });
  const historyQuery = useQuery({
    queryKey: ["pattern-analysis-v2-history", subject],
    queryFn: () => listPatternAnalysisHistory(accessToken, null, 20, signal),
    enabled: Boolean(accessToken && subject),
    retry: false
  });

  useEffect(() => {
    if (previousSubjectRef.current === subject) return;
    previousSubjectRef.current = subject;
    attemptRef.current = null;
    setActionError("");
  }, [subject]);

  useEffect(() => {
    if (historyQuery.isError && analysisQuery.data) {
      requestAnimationFrame(() => historyErrorRef.current?.focus());
    }
  }, [analysisQuery.data, historyQuery.isError]);

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
      queryClient.setQueryData(["pattern-analysis-v2", subject], analysis);
      await queryClient.invalidateQueries({
        queryKey: ["pattern-analysis-v2-history", subject]
      });
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
      onEvaluate={() => evaluation.mutate()}
      onRetryLoad={() => void analysisQuery.refetch()}
      onRetryHistory={() => {
        void historyQuery.refetch().then((result) => {
          if (!result.isError) historyHeadingRef.current?.focus();
        });
      }}
    />
  );
}
