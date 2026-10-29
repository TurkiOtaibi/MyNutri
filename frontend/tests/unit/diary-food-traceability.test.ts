import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CompactWeekNavigator, MealSections } from "@/features/diary/diary-summary";
import { emptyNutritionTotals, entryQuantityLabel, scaleEntryPreview } from "@/features/diary/diary-model";
import { EmptyFoodsState } from "@/features/foods/food-catalog-view";
import type { DiaryEntryResponse } from "@/lib/types";
import { QueryClient } from "@tanstack/react-query";
import { clearFoodDeletionNotice, readFoodDeletionNotice, rememberFoodDeletion } from "@/features/foods/food-notices";

const entry = {
  id: "synthetic-entry", meal_type: "unspecified", quantity: 2,
  food: { id: "synthetic-food", name: "طعام اختباري" },
  recorded_unit_type: "cup", recorded_unit_label: null, recorded_unit_amount: 150,
  recorded_unit_basis: "g",
  totals: { ...emptyNutritionTotals(), calories: 300, protein_g: 12, carb_g: 40, fat_g: 8 },
} as DiaryEntryResponse;

describe("Diary and Food clause traceability", () => {
  it("BR-FOD-036 carries exact deletion feedback only to the same actor and clears it after arrival", () => {
    const client = new QueryClient();
    rememberFoodDeletion(client, "admin-a");
    expect(readFoodDeletionNotice(client, "admin-a")).toBe("تم حذف الطعام نهائيًا.");
    expect(readFoodDeletionNotice(client, "other-user")).toBe("");
    expect(readFoodDeletionNotice(client, undefined)).toBe("");
    clearFoodDeletionNotice(client, "admin-a");
    expect(readFoodDeletionNotice(client, "admin-a")).toBe("");
  });

  it("BR-DRY-006 renders the exact week failure and retry control while retaining navigation", () => {
    const html = renderToStaticMarkup(createElement(CompactWeekNavigator, {
      week: undefined, pending: false, error: true, selectedDate: "2026-10-28", today: "2026-10-28",
      onSelect: () => {}, onRetry: () => {},
    }));
    expect(html).toContain("تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.");
    expect(html).toContain("إعادة المحاولة</button>");
    expect(html).toContain('aria-label="اليوم السابق"');
    expect(html).toContain('aria-label="اليوم التالي"');
  });

  it("BR-DRY-011 and BR-DRY-014 show legacy entries only when present without a legacy add action", () => {
    const props = { expanded: new Set<"unspecified">(["unspecified"]), openMenuId: null,
      onToggleMeal: () => {}, onAdd: () => {}, onToggleMenu: () => {}, onEdit: () => {}, onDelete: () => {}, deletingId: null };
    const populated = renderToStaticMarkup(createElement(MealSections, { ...props, entries: [entry] }));
    expect(populated).toContain('id="meal-section-unspecified"');
    expect(populated).toContain("غير مصنف");
    expect(populated).toContain("طعام اختباري");
    expect(populated).not.toContain("إضافة طعام إلى غير مصنف");
    const empty = renderToStaticMarkup(createElement(MealSections, { ...props, entries: [] }));
    expect(empty).not.toContain('id="meal-section-unspecified"');
  });

  it("BR-DRY-010 and BR-DRY-030 preserve recorded units and scale every edit preview macro", () => {
    expect(entryQuantityLabel(entry)).toBe("كوبان · 300 جم");
    expect(entryQuantityLabel({ ...entry, recorded_unit_basis: "ml" })).toBe("كوبان · 300 مل");
    expect(scaleEntryPreview(entry, 3)).toEqual({ calories: 450, protein_g: 18, carb_g: 60, fat_g: 12 });
  });

  it("BR-FOD-004 exposes both exact no-results messages and clear action", () => {
    const html = renderToStaticMarkup(createElement(EmptyFoodsState, { hasFilters: true, onClear: () => {} }));
    expect(html).toContain("لا توجد نتائج مطابقة للبحث.");
    expect(html).toContain("جرّب اسمًا آخر أو امسح عوامل التصفية.");
    expect(html).toContain("مسح البحث والتصفية</button>");
  });
});
