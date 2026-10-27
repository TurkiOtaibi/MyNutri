"use client";

import { DirectionProvider } from "@base-ui-components/react/direction-provider";
import { useEffect } from "react";

import { InstallPrompt } from "./InstallPrompt";
import { AuthGate, AuthProvider } from "./AuthProvider";
import { SessionQueryProvider } from "./SessionQueryProvider";
import { UnsavedChangesProvider } from "./UnsavedChangesProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").catch(() => undefined);
    }
  }, []);

  return (
    <DirectionProvider direction="rtl">
      <AuthProvider>
        <UnsavedChangesProvider>
          <SessionQueryProvider>
            <AuthGate>{children}<InstallPrompt /></AuthGate>
          </SessionQueryProvider>
        </UnsavedChangesProvider>
      </AuthProvider>
    </DirectionProvider>
  );
}
