import { describe, expect, it } from "vitest";
import { adminResultsLabel } from "@/lib/admin-display";
import { accountActionErrorMessage } from "@/lib/admin-account-messages";
import { reconcileAdminSearch } from "@/lib/admin-search";
import { ApiError } from "@/lib/api";

describe("BR-USM list copy", () => {
  it.each([[0, "عرض 0-0 من 0 مستخدمين"], [1, "عرض 1-1 من مستخدم واحد"], [2, "عرض 1-2 من مستخدمين اثنين"], [3, "عرض 1-3 من 3 مستخدمين"], [35, "عرض 1-20 من 35 مستخدمًا"], [100, "عرض 1-20 من 100 مستخدم"]])("agrees with %s results", (total, expected) => {
    expect(adminResultsLabel(1, 20, Number(total))).toBe(expected);
  });
  it("uses the current result range", () => {
    expect(adminResultsLabel(2, 20, 35)).toBe("عرض 21-35 من 35 مستخدمًا");
  });
  it("maps deletion failures to exact governed copy", () => {
    expect(accountActionErrorMessage(new ApiError("server", 503, undefined, "DELETION_INCOMPLETE"), "delete")).toBe("تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة.");
  });
});


it("preserves newer typing across delayed own URL commits and restores external navigation", () => {
  expect(reconcileAdminSearch("a", "ab", ["a"])).toEqual({ draft: "ab", pending: [] });
  expect(reconcileAdminSearch("a", "abc", ["a", "ab"])).toEqual({ draft: "abc", pending: ["ab"] });
  expect(reconcileAdminSearch("back", "abc", [])).toEqual({ draft: "back", pending: [] });
});
