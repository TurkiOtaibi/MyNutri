import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OwnedLabsView } from "@/features/labs/labs-overview-view";
import { catalogFixture } from "./fixtures/labs";

describe("selected-user Labs context", () => {
  it("never directs an administrator to their own profile for an incomplete selected-user profile", () => {
    const html = renderToStaticMarkup(createElement(OwnedLabsView, {
      adminSelected: true, catalog: catalogFixture, rows: [], eligibility: { allowed: false, reason: "profile_required" },
      search: "", category: catalogFixture.categories[0].key, sort: "name_asc", readOnly: true,
      filtersOpen: false, onToggleFilters() {}, onSearchChange() {}, onCategoryChange() {}, onSortChange() {}, onClearFilters() {},
    }));
    expect(html).not.toContain('href="/profile"');
    expect(html).toContain("ملف المستخدم غير مكتمل");
    expect(html).toContain('id="labs-filter-summary"');
    expect(html).toContain("مسح البحث والتصفية");
    expect(html).not.toContain("إضافة نتيجة");
  });
});
