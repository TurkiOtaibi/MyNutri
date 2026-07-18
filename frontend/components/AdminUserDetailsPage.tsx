"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getAdminUser, getAdminUserDiary } from "@/lib/api";

type Detail = {
  account: Record<string, unknown>;
  profile: Record<string, unknown> | null;
  current_target: Record<string, unknown> | null;
  pending_plan: Record<string, unknown> | null;
  plan_history: { items?: Array<Record<string, unknown>> };
};

const labels: Record<string, string> = {
  display_name: "الاسم", email: "البريد الإلكتروني", status: "حالة الحساب",
  role: "الدور", created_at: "تاريخ التسجيل", goal: "الهدف", weight_kg: "الوزن",
  height_cm: "الطول", activity_level: "مستوى النشاط", effective_from: "يبدأ في",
  effective_to: "ينتهي في", lifecycle_status: "حالة الخطة", entry_date: "التاريخ",
  meal_type: "الوجبة", quantity: "الكمية"
};

function displayValue(value: unknown): string {
  if (value == null || value === "") return "غير متوفر";
  if (typeof value === "boolean") return value ? "نعم" : "لا";
  if (typeof value === "object") return "متوفر ضمن السجل";
  return String(value);
}

function ReadOnlyFields({ data, keys }: { data: Record<string, unknown> | null; keys: string[] }) {
  if (!data) return <p className="state-note">غير متوفر.</p>;
  return <dl className="admin-readonly-grid">{keys.map((key) => (
    <div key={key}><dt>{labels[key] ?? key}</dt><dd dir={key === "email" ? "ltr" : "auto"}>{displayValue(data[key])}</dd></div>
  ))}</dl>;
}

export function AdminUserDetailsPage({ principalId }: { principalId: string }) {
  const detail = useQuery<Detail>({ queryKey: ["admin-user", principalId], queryFn: () => getAdminUser(principalId) as Promise<Detail> });
  const diary = useQuery({ queryKey: ["admin-user-diary", principalId], queryFn: () => getAdminUserDiary(principalId) });
  if (detail.isPending) return <div className="state-note">جارٍ تحميل بيانات المستخدم...</div>;
  if (detail.isError) return <div className="state-note" role="alert">تعذر تحميل بيانات المستخدم.</div>;
  const { account, profile, current_target: target, pending_plan: pending, plan_history: history } = detail.data;
  const selectedName = String(account.display_name || account.email || principalId);
  return <>
    <div className="selected-user-banner"><strong>عرض مستخدم آخر: {selectedName}</strong><span>وضع قراءة فقط</span></div>
    <div className="page-head"><div><h1 className="page-title">تفاصيل المستخدم</h1><p className="page-kicker">بيانات الحساب والتغذية المعروضة للمراقبة دون صلاحية تعديل.</p></div><Link className="btn" href="/admin/users">رجوع</Link></div>
    <section className="section-panel"><h2>ملخص الحساب</h2><ReadOnlyFields data={account} keys={["display_name", "email", "status", "role", "created_at"]} /></section>
    <section className="section-panel"><h2>الملف</h2><ReadOnlyFields data={profile} keys={["goal", "weight_kg", "height_cm", "activity_level"]} /></section>
    <section className="section-panel"><h2>المصدر الحالي للأهداف</h2><ReadOnlyFields data={target} keys={["source", "effective_from", "calendar_timezone"]} /></section>
    <section className="section-panel"><h2>الخطة المجدولة</h2><ReadOnlyFields data={pending} keys={["lifecycle_status", "effective_from", "effective_to"]} /></section>
    <section className="section-panel"><h2>سجل الخطط</h2>{history.items?.length ? <ul className="admin-readonly-list">{history.items.map((plan, index) => <li key={String(plan.id ?? index)}><ReadOnlyFields data={plan} keys={["lifecycle_status", "effective_from", "effective_to"]} /></li>)}</ul> : <p className="state-note">لا توجد خطط محفوظة.</p>}</section>
    <section className="section-panel"><h2>اليوميات</h2>{diary.isPending ? <p>جارٍ التحميل...</p> : diary.isError ? <p role="alert">تعذر تحميل اليوميات.</p> : diary.data?.length ? <ul className="admin-readonly-list">{diary.data.map((entry) => <li key={entry.id}><strong>{entry.nutrition_snapshot.name}</strong><span>{entry.entry_date} · {entry.meal_type} · {entry.quantity}</span></li>)}</ul> : <p className="state-note">لا توجد إدخالات يومية.</p>}</section>
  </>;
}
