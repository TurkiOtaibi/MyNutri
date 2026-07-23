"use client";

import { DirectionProvider } from "@base-ui-components/react/direction-provider";
import { useEffect } from "react";

import { InstallPrompt } from "./InstallPrompt";
import { AuthProvider } from "./AuthProvider";
import { SessionQueryProvider } from "./SessionQueryProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").catch(() => undefined);
    }
  }, []);

  return (
    <DirectionProvider direction="rtl">
      <AuthProvider>
        <SessionQueryProvider>
          {children}
          <InstallPrompt />
        </SessionQueryProvider>
      </AuthProvider>
    </DirectionProvider>
  );
}
