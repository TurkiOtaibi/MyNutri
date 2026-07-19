"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DirectionProvider } from "@base-ui-components/react/direction-provider";
import { useEffect, useState } from "react";

import { InstallPrompt } from "./InstallPrompt";
import { AuthProvider } from "./AuthProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 20_000
          }
        }
      })
  );

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").catch(() => undefined);
    }
  }, []);

  return (
    <DirectionProvider direction="rtl">
      <QueryClientProvider client={client}>
        <AuthProvider>
          {children}
          <InstallPrompt />
        </AuthProvider>
      </QueryClientProvider>
    </DirectionProvider>
  );
}
