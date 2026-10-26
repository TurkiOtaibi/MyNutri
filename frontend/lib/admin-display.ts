import type { AdminAccount } from "./api";

type AccountStatus = AdminAccount["status"];

// Approved Admin status copy (docs/ba/04_FIELD_DICTIONARY.md).
export const accountStatusLabels: Record<AccountStatus, string> = {
  active: "نشط", disabled: "معطّل", provisioning: "قيد الإنشاء",
  deleting: "حذف غير مكتمل", deleted: "مستخدم محذوف"
};

const dateOnly = /^\d{4}-\d{2}-\d{2}$/;
const gregorianDate = (timeZone: string) => new Intl.DateTimeFormat("ar-SA-u-ca-gregory-nu-latn", {
  day: "numeric", month: "long", year: "numeric", timeZone
});

// Admin dates are always Gregorian. Date-only values are calendar dates and are
// formatted as-is; timestamps are shown on the Riyadh calendar day.
export function formatAdminDate(value: string): string | null {
  const isDateOnly = dateOnly.test(value);
  const parsed = new Date(isDateOnly ? `${value}T00:00:00Z` : value);
  if (Number.isNaN(parsed.getTime())) return null;
  return gregorianDate(isDateOnly ? "UTC" : "Asia/Riyadh").format(parsed);
}

export function adminResultsLabel(page: number, pageSize: number, total: number): string {
  const first = total ? Math.min((page - 1) * pageSize + 1, total) : 0;
  const last = Math.min(page * pageSize, total);
  const suffix = total % 100;
  const users = total === 1 ? "مستخدم واحد" : total === 2 ? "مستخدمين اثنين"
    : `${total} ${total === 0 || (suffix >= 3 && suffix <= 10) ? "مستخدمين" : suffix >= 11 && suffix <= 99 ? "مستخدمًا" : "مستخدم"}`;
  return `عرض ${first}-${last} من ${users}`;
}
