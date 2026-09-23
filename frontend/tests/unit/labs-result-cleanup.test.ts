import { describe, expect, it } from "vitest";

import { createResultCleanupRegistry } from "@/e2e/labs/result-cleanup";

describe("Labs result cleanup registry", () => {
  it("cleans a registered POST receipt after the browser DELETE fails", async () => {
    const committedResults = new Set(["committed-result"]);
    const cleanupAttempts: string[] = [];
    const registry = createResultCleanupRegistry(async (id) => {
      cleanupAttempts.push(id);
      if (!committedResults.delete(id)) throw new Error(`missing result: ${id}`);
    });
    registry.register({ result_ids: ["committed-result"] });

    const failedBrowserDelete = async () => { throw new Error("browser DELETE failed"); };
    await expect(failedBrowserDelete()).rejects.toThrow("browser DELETE failed");
    expect(committedResults).toEqual(new Set(["committed-result"]));
    await registry.cleanup();
    await registry.cleanup();

    expect(committedResults.size).toBe(0);
    expect(cleanupAttempts).toEqual(["committed-result"]);
  });

  it("attempts every registered result and retains each cleanup failure", async () => {
    const attempts: string[] = [];
    const registry = createResultCleanupRegistry(async (id) => {
      attempts.push(id);
      throw new Error(`delete failed: ${id}`);
    });
    registry.register({ result_ids: ["first", "second"] });

    await expect(registry.cleanup()).rejects.toMatchObject({
      name: "AggregateError",
      errors: [expect.objectContaining({ message: "delete failed: first" }), expect.objectContaining({ message: "delete failed: second" })],
    });
    expect(attempts).toEqual(["first", "second"]);
  });
});
