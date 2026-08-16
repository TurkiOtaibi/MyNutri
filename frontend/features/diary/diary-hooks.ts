import { useEffect, useState } from "react";
import type { QueryClient } from "@tanstack/react-query";
import type { CalendarAuthorityResponse } from "@/lib/types";

const ROLLOVER_RECHECK_DELAY_MS = 1_000;
const MAX_ROLLOVER_RECHECKS = 5;

export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

export async function invalidateDiary(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["entries"] }),
    queryClient.invalidateQueries({ queryKey: ["week"] }),
    queryClient.invalidateQueries({ queryKey: ["diary-day-status"] })
  ]);
}

export function useCalendarAuthorityRefresh(
  authority: CalendarAuthorityResponse | undefined,
  refetch: () => Promise<{ data: CalendarAuthorityResponse | undefined }>
) {
  useEffect(() => {
    const currentDiaryDate = authority?.current_diary_date;
    const nextRollover = authority?.next_rollover_at;
    if (!currentDiaryDate || !nextRollover) return;
    const rolloverTime = Date.parse(nextRollover);
    if (!Number.isFinite(rolloverTime)) return;
    let cancelled = false;
    let timer: number | undefined;
    const schedule = (delay: number, rechecks: number) => {
      timer = window.setTimeout(async () => {
        const refreshed = (await refetch()).data;
        if (cancelled || (refreshed && (refreshed.current_diary_date !== currentDiaryDate || refreshed.next_rollover_at !== nextRollover))) return;
        const refreshedRollover = refreshed ? Date.parse(refreshed.next_rollover_at) : Number.NaN;
        if (Number.isFinite(refreshedRollover) && refreshedRollover > Date.now()) schedule(Math.min(refreshedRollover - Date.now(), 2_147_483_647), 0);
        else if (rechecks < MAX_ROLLOVER_RECHECKS) schedule(ROLLOVER_RECHECK_DELAY_MS, rechecks + 1);
      }, Math.max(0, Math.min(delay, 2_147_483_647)));
    };
    schedule(rolloverTime - Date.now(), 0);
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [authority?.current_diary_date, authority?.next_rollover_at, refetch]);

  useEffect(() => {
    const refresh = () => { void refetch(); };
    const refreshWhenVisible = () => { if (document.visibilityState === "visible") refresh(); };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [refetch]);
}

export type ReopenInvoker =
  | { kind: "element"; element: HTMLElement }
  | { kind: "entry"; action: "edit" | "delete"; entryId: string };

export function restoreReopenFocus(invoker: ReopenInvoker, openEntryMenu: (entryId: string) => void) {
  if (invoker.kind === "element") {
    requestAnimationFrame(() => {
      if (invoker.element.isConnected) invoker.element.focus();
    });
    return;
  }
  openEntryMenu(invoker.entryId);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelector<HTMLElement>(`[data-diary-entry-action="${invoker.action}-${invoker.entryId}"]`)?.focus();
  }));
}
