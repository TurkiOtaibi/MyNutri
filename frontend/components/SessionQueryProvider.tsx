"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Fragment, useEffect, useMemo } from "react";

import { useAuth } from "./AuthProvider";

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
  const client = useMemo(() => createQueryClient(), [subjectKey]);

  useEffect(() => {
    return () => {
      void client.cancelQueries().catch(() => undefined).finally(() => client.clear());
    };
  }, [client]);

  return (
    <QueryClientProvider client={client}>
      <Fragment key={subjectKey}>{children}</Fragment>
    </QueryClientProvider>
  );
}
