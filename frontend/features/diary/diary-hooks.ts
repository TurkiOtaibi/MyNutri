import { useEffect, useState } from "react";
import type { QueryClient } from "@tanstack/react-query";

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
