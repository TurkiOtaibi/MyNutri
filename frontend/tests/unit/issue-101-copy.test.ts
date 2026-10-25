import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { shortWeekdays, validateQuantity } from "@/features/diary/diary-model";
import { resultCountLabel, labErrorMessage, mapLabErrors } from "@/features/labs/lab-batch-model";
import { TargetPlanHistory } from "@/features/profile/profile-targets";
import type { TargetResponse } from "@/lib/types";

describe("issue 101 governed Arabic copy", () => {
  it("BR-DRY-001 uses the seven full approved weekday labels", () => {
    expect(shortWeekdays).toEqual(["أحد", "إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"]);
  });

  it.each(["كوب", "ملعقة", "قطعة مخصصة"])("BR-DRY-020 names the actual unit %s without changing limits", (unit) => {
    expect(validateQuantity("51", unit)).toBe(`الكمية يجب ألا تتجاوز 50 ${unit}`);
    expect(validateQuantity("50", unit)).toBe("");
    expect(validateQuantity("0.01", unit)).toBe("");
    expect(validateQuantity("0", unit)).toBe("أدخل كمية أكبر من 0");
    expect(validateQuantity("invalid", unit)).toBe("أدخل كمية صحيحة");
  });

  it.each([[0, "0 نتائج"], [1, "نتيجة واحدة"], [2, "نتيجتين"], [3, "3 نتائج"], [10, "10 نتائج"], [11, "11 نتيجة"], [51, "51 نتيجة"]])(
    "BR-LAB-018 formats %s results", (count, expected) => {
      expect(resultCountLabel(Number(count))).toBe(expected);
    },
  );

  it("BR-LAB-020 presents the approved copy for the backend decimal error only", () => {
    const error = { loc: ["body", "entered_value"], type: "value_error", code: "LAB_DECIMAL_INVALID", msg: "أدخل قيمة رقمية صريحة غير سالبة." };
    expect(labErrorMessage(error)).toBe("أدخل رقمًا صحيحًا يساوي صفرًا أو أكبر.");
    expect(mapLabErrors([{ ...error, test_key: "ferritin" }]).rows.ferritin.entered_value)
      .toBe("أدخل رقمًا صحيحًا يساوي صفرًا أو أكبر.");
    expect(labErrorMessage({ ...error, code: "LAB_UNIT_UNSUPPORTED", msg: "اختر وحدة مدعومة لهذا التحليل." })).toBe("اختر وحدة مدعومة لهذا التحليل.");
  });

  it("BR-PRF-022/027 renders history calories and Gregorian dates with bidi isolation", () => {
    const html = renderToStaticMarkup(createElement(TargetPlanHistory, {
      plans: [{ id: "synthetic-plan", revision: 1, effective_from: "2026-10-17", created_at: "2026-10-17T00:00:00Z", targets: { target_calories: 2000 } as TargetResponse }],
      pending: false, failed: false, hasMore: false, loadingMore: false, onRetry: () => {}, onLoadMore: () => {},
    }));
    expect(html).toContain('<time dateTime="2026-10-17">17 أكتوبر 2026</time>');
    expect(html).toContain('<bdi dir="ltr">2000</bdi> سعرة');
    expect(html).not.toContain("kcal");
  });
});
