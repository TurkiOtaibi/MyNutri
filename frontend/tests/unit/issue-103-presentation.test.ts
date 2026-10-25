import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { CalculationExplanation } from "@/features/profile/profile-targets";
import { FoodDetailsPage } from "@/components/FoodDetailsPage";
import { emptyFoodForm } from "@/features/foods/food-form-model";

const state = vi.hoisted(() => ({ role: "user", food: {} }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/components/AuthProvider", () => ({ useAuth: () => ({ account: { role: state.role } }) }));
vi.mock("@/components/useFoodDelete", () => ({ useFoodDelete: () => ({ isPending: false, mutate: vi.fn() }) }));
vi.mock("@/components/SessionQueryProvider", () => ({ useSessionAbortSignal: () => new AbortController().signal }));
vi.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({ invalidateQueries: vi.fn() }), useQuery: ({ queryKey }: { queryKey: string[] }) =>
  queryKey[0] === "food" ? { data: state.food, isPending: false } : { data: undefined, isPending: true } }));

describe("issue 103 presentation", () => {
  it.each(["user", "admin"])("BR-FOD-021 hides attribution and archived values for %s", (role) => {
    state.role = role;
    state.food = { ...emptyFoodForm, id: "synthetic-food", name: "طعام تجريبي", calories: 100,
      protein_g: 5, carb_g: 20, fat_g: 2, unit_amount: 100, net_carbs_g: 15,
      created_by_label: "منشئ تجريبي", updated_by_label: "مستخدم محذوف",
      legacy_nutrition: { folate_mcg: 123, vitamin_a_mcg: 456, meaning_ar: "أرشيف تجريبي" },
      created_at: "2026-10-17T00:00:00Z", updated_at: "2026-10-18T00:00:00Z" };
    const html = renderToStaticMarkup(createElement(FoodDetailsPage, { foodId: "synthetic-food" }));
    for (const hidden of ["منشئ تجريبي", "مستخدم محذوف", "فولات قديم", "فيتامين A قديم", "أرشيف تجريبي"]) {
      expect(html).not.toContain(hidden);
    }
    expect(html).toContain("تاريخ الإنشاء");
    expect(html).toContain("آخر تحديث");
    expect(html).toContain("إضافة إلى اليوميات");
    expect(html.includes('href="/foods/synthetic-food/edit"')).toBe(role === "admin");
  });

  it("BR-PRF-011 explains each term beneath its label with the exact approved BMR example", () => {
    const html = renderToStaticMarkup(createElement(CalculationExplanation));
    for (const term of ["معدل الأيض الأساسي", "أساس الحساب", "وزن الحساب", "الوزن الفعلي", "الوزن المعدل",
      "مؤشر كتلة الجسم المستخدم", "العجز المطلوب", "العجز المطبق", "شدة الخفض المختارة", "تفاصيل حساب البروتين"]) {
      expect(html).toMatch(new RegExp(`<dt>${term}</dt><dd>${term}: [^<]+</dd>`));
    }
    expect(html).toContain("معدل الأيض الأساسي: السعرات التي يحرقها جسمك وأنت مرتاح");
  });

  it("BR-PRF-010 leaves no abbreviated carbohydrate copy in UI sources, including accessible labels", () => {
    function scan(directory: string): string[] {
      return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const path = join(directory, entry.name);
        return entry.isDirectory() ? scan(path) : /\.(tsx?|json|html|js)$/.test(path) && readFileSync(path, "utf8").includes("كارب") ? [path] : [];
      });
    }
    expect(["components", "features", "lib", "app", "public"].flatMap(scan)).toEqual([]);
  });
});
