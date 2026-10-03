import { describe, expect, it } from "vitest";
import { accountStatusLabels, formatAdminDate } from "@/lib/admin-display";

describe("Admin display helpers", () => {
  it("formats timestamps as Gregorian dates on the Riyadh calendar day", () => {
    const formatted = formatAdminDate("2026-08-15T22:30:00Z");
    expect(formatted).toContain("2026");
    expect(formatted).toContain("16");
    expect(formatted).toContain("أغسطس");
    expect(formatted).not.toMatch(/هـ|[٠-٩]/);
  });

  it("formats date-only values without shifting the calendar day", () => {
    const formatted = formatAdminDate("2026-07-30");
    expect(formatted).toContain("30");
    expect(formatted).toContain("يوليو");
    expect(formatted).toContain("2026");
  });

  it("returns null for unparseable values", () => {
    expect(formatAdminDate("not-a-date")).toBeNull();
  });

  it("labels every account status with approved copy", () => {
    expect(accountStatusLabels).toEqual({
      active: "نشط", disabled: "معطّل", provisioning: "قيد الإنشاء",
      deleting: "حذف غير مكتمل", deleted: "مستخدم محذوف"
    });
  });
});
