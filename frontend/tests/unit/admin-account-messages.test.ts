import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { accountActionErrorMessage, accountActionSuccessMessage } from "@/lib/admin-account-messages";

describe("Admin account action messages", () => {
  it.each([
    ["edit", "تعذر حفظ تغييرات المستخدم. حاول مرة أخرى."],
    ["status", "تعذر تحديث حالة المستخدم. حاول مرة أخرى."],
    ["password", "تعذر إعادة تعيين كلمة المرور. حاول مرة أخرى."],
    ["delete", "تعذر إكمال حذف المستخدم. حسابه معطّل ويمكنك إعادة المحاولة."],
  ] as const)("does not show creation-incomplete for %s failures", (action, expected) => {
    expect(accountActionErrorMessage(new ApiError("تعذر إكمال إنشاء المستخدم. أعد المحاولة.", 409, undefined, "CREATION_INCOMPLETE"), action)).toBe(expected);
  });

  it.each(["create", "edit", "status", "password", "delete", "retry-create", "retry-delete"] as const)("shows approved network copy for %s", action => {
    expect(accountActionErrorMessage(new TypeError("Failed to fetch"), action)).toBe("تعذر الاتصال بالخادم. حاول مرة أخرى.");
  });

  it("uses the action failure for an unclassified API response", () => {
    expect(accountActionErrorMessage(new ApiError("API request failed with 500", 500), "edit")).toBe("تعذر حفظ تغييرات المستخدم. حاول مرة أخرى.");
    expect(accountActionErrorMessage(new ApiError("API request failed with 500", 500), "status")).toBe("تعذر تحديث حالة المستخدم. حاول مرة أخرى.");
    expect(accountActionErrorMessage(new ApiError("تعذر إكمال إنشاء المستخدم. أعد المحاولة.", 409), "status")).toBe("تعذر تحديث حالة المستخدم. حاول مرة أخرى.");
  });

  it("preserves approved server-side validation copy", () => {
    const rejected = "كلمة المرور غير مقبولة. اختر كلمة مرور أقوى وحاول مرة أخرى.";
    expect(accountActionErrorMessage(new ApiError(rejected, 422, undefined, "PASSWORD_REJECTED"), "password")).toBe(rejected);
  });

  it("uses the approved password-reset success copy", () => {
    expect(accountActionSuccessMessage("password")).toBe("تمت إعادة تعيين كلمة المرور.");
  });
});
