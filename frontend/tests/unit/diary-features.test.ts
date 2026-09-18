import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { invalidateDiary } from "@/features/diary/diary-hooks";

describe("diary feature query ownership", () => {
  it("invalidates every cached Diary projection after a mutation", async () => {
    const queryClient = new QueryClient();
    const queryKeys = [
      ["entries", "principal", "2026-09-18"],
      ["week", "principal", "2026-09-14"],
      ["diary-food-picker", "principal", "rice"],
    ] as const;

    for (const queryKey of queryKeys) queryClient.setQueryData(queryKey, {});

    await invalidateDiary(queryClient);

    for (const queryKey of queryKeys) {
      expect(queryClient.getQueryState(queryKey)?.isInvalidated).toBe(true);
    }
  });
});
