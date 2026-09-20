import type { QueryClient } from "@tanstack/react-query";

export type QueryInvalidationInspection = {
  inspect: () => string[];
  dispose: () => void;
};

const installedInspections = new WeakMap<QueryClient, QueryInvalidationInspection>();

export function installQueryInvalidationInspection(
  client: QueryClient,
  limit = 20,
  signal?: AbortSignal,
): QueryInvalidationInspection {
  const installed = installedInspections.get(client);
  if (installed) return installed;

  const records: string[] = [];
  const original = client.invalidateQueries;
  const clear = () => { records.length = 0; };
  const wrapped = function (
    this: QueryClient,
    ...args: Parameters<QueryClient["invalidateQueries"]>
  ): ReturnType<QueryClient["invalidateQueries"]> {
    if (!signal?.aborted) {
      records.push(JSON.stringify(args[0]?.queryKey ?? null));
      if (records.length > limit) records.splice(0, records.length - limit);
    }
    return original.apply(this, args);
  } as QueryClient["invalidateQueries"];
  let active = true;

  const inspection: QueryInvalidationInspection = {
    inspect: () => [...records],
    dispose: () => {
      clear();
      if (!active) return;
      active = false;
      signal?.removeEventListener("abort", clear);
      if (client.invalidateQueries === wrapped) client.invalidateQueries = original;
      installedInspections.delete(client);
    },
  };
  client.invalidateQueries = wrapped;
  installedInspections.set(client, inspection);
  signal?.addEventListener("abort", clear, { once: true });
  if (signal?.aborted) clear();
  return inspection;
}
