type ResultReceipt = { result_ids: string[] };

export function createResultCleanupRegistry(removeResult: (id: string) => Promise<void>) {
  const resultIds = new Set<string>();
  return {
    register(receipt: ResultReceipt) {
      for (const id of receipt.result_ids) resultIds.add(id);
    },
    markRemoved(id: string) {
      resultIds.delete(id);
    },
    async cleanup() {
      const failures: unknown[] = [];
      for (const id of resultIds) {
        try {
          await removeResult(id);
          resultIds.delete(id);
        } catch (error) {
          failures.push(error);
        }
      }
      if (failures.length) throw new AggregateError(failures, "Labs fixture cleanup failed.");
    },
  };
}
