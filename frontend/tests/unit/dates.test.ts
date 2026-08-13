import { describe, expect, it } from "vitest";

import { addDays, formatDayNumber, weekStartSunday } from "@/lib/dates";

describe("Gregorian diary dates", () => {
  it("crosses month, year, and leap-day boundaries in UTC", () => {
    expect(addDays("2024-02-28", 1)).toBe("2024-02-29");
    expect(addDays("2024-02-29", 1)).toBe("2024-03-01");
    expect(addDays("2025-12-31", 1)).toBe("2026-01-01");
    expect(addDays("2026-01-01", -1)).toBe("2025-12-31");
  });

  it("finds the Sunday boundary without depending on the host timezone", () => {
    expect(weekStartSunday("2026-08-13")).toBe("2026-08-09");
    expect(weekStartSunday("2026-08-09")).toBe("2026-08-09");
  });

  it("rejects non-ISO inputs and keeps day presentation unpadded", () => {
    expect(() => addDays("13-08-2026", 1)).toThrow("Invalid ISO date");
    expect(formatDayNumber("2026-08-03")).toBe("3");
  });
});
