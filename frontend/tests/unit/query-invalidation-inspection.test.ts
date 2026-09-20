import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { installQueryInvalidationInspection } from "@/features/session/query-invalidation-inspection";

describe("generic E2E query invalidation inspection", () => {
  it("records bounded key-only invocations, including repeated invalidation of an already-invalid query", async () => {
    const client = new QueryClient();
    const inspection = installQueryInvalidationInspection(client, 2);

    await client.invalidateQueries({ queryKey: ["labs", "actor-a", "owner"] });
    await client.invalidateQueries({ queryKey: ["labs", "actor-a", "owner"] });
    await client.invalidateQueries();

    expect(inspection.inspect()).toEqual([
      JSON.stringify(["labs", "actor-a", "owner"]),
      JSON.stringify(null),
    ]);
  });

  it("does not stack wrappers and transparently preserves arguments, this, and the returned promise", async () => {
    const client = new QueryClient();
    const returned = Promise.resolve();
    const original = vi.fn(function (this: QueryClient) {
      expect(this).toBe(client);
      return returned;
    });
    client.invalidateQueries = original as typeof client.invalidateQueries;

    const first = installQueryInvalidationInspection(client);
    const wrapped = client.invalidateQueries;
    const second = installQueryInvalidationInspection(client);
    const filters = { queryKey: ["profile", "actor-a"] as const, exact: true };
    const options = { throwOnError: true };
    const actual = client.invalidateQueries(filters, options);

    expect(second).toBe(first);
    expect(client.invalidateQueries).toBe(wrapped);
    expect(actual).toBe(returned);
    expect(original).toHaveBeenCalledWith(filters, options);
    await actual;
    expect(first.inspect()).toEqual([JSON.stringify(filters.queryKey)]);
  });

  it("clears on abort, stops stale recording, and restores the original method on cleanup", async () => {
    const client = new QueryClient();
    const original = client.invalidateQueries;
    const controller = new AbortController();
    const inspection = installQueryInvalidationInspection(client, 20, controller.signal);

    await client.invalidateQueries({ queryKey: ["profile", "actor-a"] });
    controller.abort();
    expect(inspection.inspect()).toEqual([]);

    await client.invalidateQueries({ queryKey: ["labs", "actor-a"] });
    expect(inspection.inspect()).toEqual([]);
    inspection.dispose();
    expect(inspection.inspect()).toEqual([]);
    expect(client.invalidateQueries).toBe(original);
  });
});
