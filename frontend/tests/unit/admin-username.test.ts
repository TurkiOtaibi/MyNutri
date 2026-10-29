import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { formatAdminDateTime } from "@/lib/admin-display";
import { passwordValidationMessage, usernameValidationMessage, deletionConfirmationMessage } from "@/lib/admin-account-messages";
import { AdminUserDetailsPage } from "@/components/AdminUserDetailsPage";
import { AdminUsersPage } from "@/components/AdminUsersPage";

const state = vi.hoisted(() => ({ search: "", data: {
  counts: { active: 2, disabled: 0, provisioning: 0, deleting: 0 }, total: 2, page_size: 20,
  self: { principal_id: "self", display_name: "المشرف", username: "admin", email: null, role: "admin", status: "active", created_at: "2026-08-15T22:30:00Z", last_login_at: "2026-08-16T06:05:00Z", is_locked: false },
  items: [
    { principal_id: "internal", display_name: "مستخدم داخلي", username: "test.user", email: null, role: "user", status: "active", created_at: "2026-08-15T22:30:00Z", last_login_at: null, is_locked: true },
    { principal_id: "legacy", display_name: "مستخدم سابق", username: null, email: "legacy@example.test", role: "user", status: "active", created_at: "2026-08-15T22:30:00Z", last_login_at: null, is_locked: false },
  ],
} }));
vi.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({}), useQuery: () => ({ data: state.data }), useInfiniteQuery: ({ queryKey }: { queryKey: string[] }) => ({ data: { pages: queryKey[0] === "admin-user" ? [{
  account: { ...state.data.items[0], username: "active" }, profile: null, current_target: null, plan_history: { items: [] }
}] : [] } }) }));
vi.mock("@/components/AuthProvider", () => ({ useAuth: () => ({ account: state.data.self }) }));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(state.search), usePathname: () => "/admin/users", useRouter: () => ({ replace: vi.fn() }) }));

describe("username admin presentation", () => {
  it("shows Gregorian Riyadh date and time, including midnight rollover", () => {
    expect(formatAdminDateTime("2026-08-15T22:30:00Z")).toBe("16 أغسطس 2026، 01:30");
    expect(formatAdminDateTime("bad-date")).toBeNull();
  });
  it("counts Unicode code points for the eight-character password minimum", () => {
    expect(passwordValidationMessage("🔒".repeat(7))).toBe("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.");
    expect(passwordValidationMessage("🔒".repeat(8))).toBe("");
    expect(passwordValidationMessage("")).toBe("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.");
  });
  it("validates ASCII username boundaries with governed Arabic copy", () => {
    expect(usernameValidationMessage("")).toBe("أدخل اسم المستخدم.");
    for (const invalid of ["ab", "a".repeat(33), "اسم", "ab cd", "ab@cd"]) {
      expect(usernameValidationMessage(invalid)).toBe("استخدم من 3 إلى 32 حرفًا لاسم المستخدم: أحرف إنجليزية أو أرقام أو . أو _ أو - فقط.");
    }
    for (const valid of ["Ab_", "test.user-1", "a".repeat(32)]) expect(usernameValidationMessage(valid)).toBe("");
  });
  it("renders compact rows with username, legacy identity, lock status and last login including self", () => {
    state.search = "";
    const html = renderToStaticMarkup(createElement(AdminUsersPage));
    expect(html).toContain('placeholder="ابحث بالاسم أو اسم المستخدم..."');
    expect(html).toContain('<option value="locked">مقفل</option>');
    expect(html).toContain('<bdi dir="ltr">test.user</bdi>');
    expect(html).toContain('<bdi dir="ltr">legacy@example.test</bdi>');
    expect(html).toContain("حساب قديم");
    expect(html).toContain('class="account-status-badge">مقفل</span>');
    expect(html).not.toContain("تاريخ التسجيل");
    expect(html.match(/آخر دخول:/g)).toHaveLength(3);
    expect(html).toContain("لم يسجل الدخول بعد.");
    expect(html).toContain("16 أغسطس 2026، 09:05");
    expect(html).not.toContain("إجراءات المشرف");
  });
  it("preserves locked filter and return URL while suppressing the self row", () => {
    state.search = "status=locked&search=test&page=2";
    const html = renderToStaticMarkup(createElement(AdminUsersPage));
    expect(html).toContain('<option value="locked" selected="">مقفل</option>');
    expect(html).toContain('/admin/users/internal?status=locked&amp;search=test&amp;page=2');
    expect(html).not.toContain("(أنت)");
  });
});

it("validates the target identity while preserving legacy email confirmation", () => {
  expect(deletionConfirmationMessage("OTHER", { username: "test.user", email: null })).toBe("اسم المستخدم المدخل لا يطابق هذا الحساب.");
  expect(deletionConfirmationMessage(" TEST.User ", { username: "test.user", email: "legacy@example.test" })).toBe("");
  expect(deletionConfirmationMessage("legacy@example.test", { username: "test.user", email: "legacy@example.test" })).toBe("اسم المستخدم المدخل لا يطابق هذا الحساب.");
  expect(deletionConfirmationMessage(" LEGACY@example.test ", { username: null, email: "legacy@example.test" })).toBe("");
  expect(deletionConfirmationMessage("other@example.test", { username: null, email: "legacy@example.test" })).toBe("البريد الإلكتروني المدخل لا يطابق بريد المستخدم.");
});

it("shows immutable usernames verbatim in details even when they match a status token", () => {
  const html = renderToStaticMarkup(createElement(AdminUserDetailsPage, { principalId: "internal" }));
  expect(html).toContain('<dt>اسم المستخدم</dt><dd><bdi dir="ltr">active</bdi>');
  expect(html).not.toContain('<dt>البريد الإلكتروني</dt>');
  expect(html).toContain("آخر دخول");
  expect(html).toContain("لم يسجل الدخول بعد.");
});
