"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";

import { useAuth } from "./AuthProvider";

const SessionAbortContext = createContext<AbortSignal | null>(null);

type SessionBoundaryRotation = {
  sequence: number;
  fromSubjectKey: string;
  toSubjectKey: string;
  previousAbortedBefore: boolean;
  previousAbortedAfter: boolean;
};

type SessionBoundaryInspection = {
  sequence: number;
  rotations: SessionBoundaryRotation[];
};

type E2eInspectionWindow = Window & {
  __mynutriE2EQueryKeys?: () => string[];
  __mynutriE2ESessionSignalAborted?: () => boolean;
  __mynutriE2ESessionSubjectKey?: () => string;
  __mynutriE2ESessionBoundaryRotations?: () => SessionBoundaryRotation[];
};

function e2eInspectionAllowed() {
  return (
    (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY === "e2e-public-key"
  );
}

export function useSessionAbortSignal() {
  const signal = useContext(SessionAbortContext);
  if (!signal) throw new Error("useSessionAbortSignal must be used within SessionQueryProvider.");
  return signal;
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        staleTime: 20_000
      }
    }
  });
}

export function SessionQueryProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const subjectKey = session?.user.id ?? "anonymous";
  const activeBoundaryRef = useRef<ActiveSubjectBoundary | null>(null);
  const inspectionRef = useRef<SessionBoundaryInspection>({ sequence: 0, rotations: [] });
  return (
    <SubjectQueryBoundary
      key={subjectKey}
      subjectKey={subjectKey}
      activeBoundaryRef={activeBoundaryRef}
      inspectionRef={inspectionRef}
    >
      {children}
    </SubjectQueryBoundary>
  );
}

type ActiveSubjectBoundary = {
  subjectKey: string;
  controller: AbortController;
};

type ActiveBoundaryRef = {
  current: ActiveSubjectBoundary | null;
};

type InspectionRef = {
  current: SessionBoundaryInspection;
};

function SubjectQueryBoundary({
  children,
  subjectKey,
  activeBoundaryRef,
  inspectionRef
}: {
  children: React.ReactNode;
  subjectKey: string;
  activeBoundaryRef: ActiveBoundaryRef;
  inspectionRef: InspectionRef;
}) {
  const [client] = useState(createQueryClient);
  const [controller] = useState(() => new AbortController());
  const effectGenerationRef = useRef(0);

  useLayoutEffect(() => {
    // A keyed subject takeover installs a different controller. Abort the old
    // boundary in the same commit, before passive effects or network tasks run.
    // StrictMode layout replay sees the same controller and leaves it active.
    const activeBoundary = activeBoundaryRef.current;
    if (activeBoundary?.controller === controller) return;
    if (activeBoundary) {
      const previousAbortedBefore = activeBoundary.controller.signal.aborted;
      activeBoundary.controller.abort();
      if (e2eInspectionAllowed()) {
        const inspection = inspectionRef.current;
        inspection.rotations.push({
          sequence: ++inspection.sequence,
          fromSubjectKey: activeBoundary.subjectKey,
          toSubjectKey: subjectKey,
          previousAbortedBefore,
          previousAbortedAfter: activeBoundary.controller.signal.aborted
        });
        if (inspection.rotations.length > 20) inspection.rotations.shift();
      }
    }
    activeBoundaryRef.current = { subjectKey, controller };
  }, [activeBoundaryRef, controller, inspectionRef, subjectKey]);

  useEffect(() => {
    const effectGeneration = ++effectGenerationRef.current;
    const allowE2eInspection = e2eInspectionAllowed();
    const e2eWindow = window as E2eInspectionWindow;
    const inspectQueryKeys = () => client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    const inspectSignalAborted = () => controller.signal.aborted;
    const inspectSubjectKey = () => subjectKey;
    const inspectRotations = () => inspectionRef.current.rotations.map((rotation) => ({ ...rotation }));
    if (allowE2eInspection) {
      e2eWindow.__mynutriE2EQueryKeys = inspectQueryKeys;
      e2eWindow.__mynutriE2ESessionSignalAborted = inspectSignalAborted;
      e2eWindow.__mynutriE2ESessionSubjectKey = inspectSubjectKey;
      e2eWindow.__mynutriE2ESessionBoundaryRotations = inspectRotations;
    }
    return () => {
      // StrictMode replays passive cleanup/setup in the same task while retaining
      // state. A newer setup supersedes that synthetic cleanup before this runs.
      queueMicrotask(() => {
        if (effectGenerationRef.current !== effectGeneration) return;
        if (activeBoundaryRef.current?.controller === controller) {
          controller.abort();
          activeBoundaryRef.current = null;
        }
        if (allowE2eInspection && e2eWindow.__mynutriE2EQueryKeys === inspectQueryKeys) {
          delete e2eWindow.__mynutriE2EQueryKeys;
        }
        if (allowE2eInspection && e2eWindow.__mynutriE2ESessionSignalAborted === inspectSignalAborted) {
          delete e2eWindow.__mynutriE2ESessionSignalAborted;
        }
        if (allowE2eInspection && e2eWindow.__mynutriE2ESessionSubjectKey === inspectSubjectKey) {
          delete e2eWindow.__mynutriE2ESessionSubjectKey;
        }
        if (allowE2eInspection && e2eWindow.__mynutriE2ESessionBoundaryRotations === inspectRotations) {
          delete e2eWindow.__mynutriE2ESessionBoundaryRotations;
        }
        void client.cancelQueries().catch(() => undefined).finally(() => client.clear());
      });
    };
  }, [activeBoundaryRef, client, controller, inspectionRef, subjectKey]);

  return <SessionAbortContext.Provider value={controller.signal}><QueryClientProvider client={client}>{children}</QueryClientProvider></SessionAbortContext.Provider>;
}
