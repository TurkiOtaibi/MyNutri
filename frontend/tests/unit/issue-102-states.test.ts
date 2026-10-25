import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import OfflinePage from "@/app/offline/page";
import { TargetsCard } from "@/features/profile/profile-targets";
import { DailyProgressSummary } from "@/features/diary/diary-summary";
import { emptyNutritionTotals } from "@/features/diary/diary-model";
import { OwnedLabsView } from "@/features/labs/labs-overview-view";
import { catalogFixture } from "./fixtures/labs";

describe("issue 102 missing UI states", () => {
  it("BR-DRY-039 explains missing targets and links the Diary to Profile", () => {
    const html = renderToStaticMarkup(createElement(DailyProgressSummary, {
      totals: emptyNutritionTotals(), targets: null, pending: false, failed: false, onOpenNutrition: () => {},
    }));
    expect(html).toContain("لم تحدد أهدافك بعد.");
    expect(html).toMatch(/href="\/profile"[^>]*>تحديد أهدافي<\/a>/);
    expect(renderToStaticMarkup(createElement(TargetsCard, { title: "الأهداف", badge: "اليوم", targets: null })))
      .toContain("لم تحدد أهدافك بعد.");
  });
  it("BR-NAV-016 supplies an Arabic installation description", () => {
    const manifest = JSON.parse(readFileSync("public/manifest.json", "utf8"));
    expect(manifest.description).toBe("متابعة التغذية واليوميات والتحاليل.");
    expect(manifest.start_url).toBe("/diary");
  });
  it("BR-NAV-019 offers a native retry without a product version or personal data", () => {
    const html = renderToStaticMarkup(createElement(OfflinePage));
    expect(html).toContain("الاتصال غير متاح");
    expect(html).not.toContain("myNutri v1");
    expect(html).toContain("لا يتم حفظ التغييرات محليًا");
    expect(html).toContain('action="/diary"');
    expect(html).toContain('type="submit">إعادة المحاولة</button>');
  });
  it("BR-LAB-011 distinguishes the Admin's own empty Labs from a monitored user's empty Labs", () => {
    const props = { catalog: catalogFixture, rows: [], eligibility: { allowed: false, reason: "read_only" as const },
      search: "", category: null, sort: "newest_updated" as const, readOnly: true,
      onSearchChange: () => {}, onCategoryChange: () => {}, onSortChange: () => {}, };
    const own = renderToStaticMarkup(createElement(OwnedLabsView, { ...props, adminOwn: true }));
    expect(own).toContain("تسجيل التحاليل غير متاح لحساب المشرف.");
    expect(own).not.toContain("لم تسجل أي نتائج بعد.");
    const monitored = renderToStaticMarkup(createElement(OwnedLabsView, props));
    expect(monitored).toContain("لم تسجل أي نتائج بعد.");
    expect(monitored).not.toContain("تسجيل التحاليل غير متاح لحساب المشرف.");
  });
});
