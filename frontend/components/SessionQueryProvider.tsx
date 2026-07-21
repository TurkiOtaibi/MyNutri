"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";

import { useAuth } from "./AuthProvider";

const SessionAbortContext = createContext<AbortSignal | null>(null);

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
  return <SubjectQueryBoundary key={subjectKey}>{children}</SubjectQueryBoundary>;
}

function SubjectQueryBoundary({ children }: { children: React.ReactNode }) {
  const [client] = useState(createQueryClient);
  const [controller] = useState(() => new AbortController());

  useEffect(() => {
    const allowE2eInspection =
      (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") &&
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY === "e2e-public-key";
    const e2eWindow = window as Window & { __mynutriE2EQueryKeys?: () => string[] };
    if (allowE2eInspection) {
      e2eWindow.__mynutriE2EQueryKeys = () => client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    }
    return () => {
      controller.abort();
      if (allowE2eInspection) delete e2eWindow.__mynutriE2EQueryKeys;
      void client.cancelQueries().catch(() => undefined).finally(() => client.clear());
    };
  }, [client, controller]);

  return <SessionAbortContext.Provider value={controller.signal}><QueryClientProvider client={client}>{children}</QueryClientProvider></SessionAbortContext.Provider>;
}
