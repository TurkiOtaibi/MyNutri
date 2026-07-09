"use client";

import { RefreshCw, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { flushQueuedMutations, getPendingMutationCount } from "@/lib/db";

export function SyncStatus() {
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState(0);
  const [syncing, setSyncing] = useState(false);

  async function refreshPending() {
    try {
      setPending(await getPendingMutationCount());
    } catch {
      setPending(0);
    }
  }

  async function flush() {
    if (!navigator.onLine || syncing) return;
    setSyncing(true);
    try {
      await flushQueuedMutations();
      await refreshPending();
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    setOnline(navigator.onLine);
    refreshPending();
    if (navigator.onLine) {
      flush();
    }
    const onOnline = () => {
      setOnline(true);
      flush();
    };
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    const interval = window.setInterval(refreshPending, 5_000);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.clearInterval(interval);
    };
  }, []);

  const className = `sync-status ${!online ? "offline" : pending > 0 ? "pending" : ""}`;
  const label = syncing
    ? "جاري المزامنة"
    : online
      ? pending > 0
        ? `${pending} بانتظار المزامنة`
        : "متزامن"
      : "دون اتصال";

  return (
    <div className={className} role="status">
      {online ? <Wifi size={16} /> : <WifiOff size={16} />}
      <span>{label}</span>
      {pending > 0 && online ? (
        <button className="btn icon" type="button" title="مزامنة الآن" onClick={flush} disabled={syncing}>
          <RefreshCw size={16} />
        </button>
      ) : null}
    </div>
  );
}
