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
