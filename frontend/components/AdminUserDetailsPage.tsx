"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { getAdminUser, getAdminUserDiary } from "@/lib/api";

const labels: Record<string, string> = {
  display_name: "الاسم", email: "البريد الإلكتروني", status: "حالة الحساب",
  role: "الدور", created_at: "تاريخ التسجيل", goal: "الهدف", weight_kg: "الوزن",
  height_cm: "الطول", activity_level: "مستوى النشاط", effective_from: "يبدأ في",
  effective_to: "ينتهي في", lifecycle_status: "حالة الخطة", entry_date: "التاريخ",
  meal_type: "الوجبة", quantity: "الكمية"
};

const semanticLabels: Record<string, string> = {
  active: "نشط", disabled: "معطل", user: "مستخدم", admin: "مشرف",
  cut: "خفض الوزن", maintain: "المحافظة على الوزن", bulk: "زيادة الوزن",
  sedentary: "خامل", light: "خفيف", moderate: "متوسط", active_activity: "نشط", very_active: "نشط جدًا"
};

function displayValue(key: string, value: unknown): string {
  if (value == null || value === "") return "غير متوفر";
  if (typeof value === "boolean") return value ? "نعم" : "لا";
  if (typeof value === "object") return "متوفر ضمن السجل";
  if (["created_at", "effective_from", "effective_to", "entry_date"].includes(key)) {
    const parsed = new Date(String(value));
    if (!Number.isNaN(parsed.getTime())) return parsed.toLocaleDateString("ar-SA");
  }
  if (key === "activity_level" && value === "active") return semanticLabels.active_activity;
  if (semanticLabels[String(value)]) return semanticLabels[String(value)];
  return String(value);
}

function readField(data: object, key: string): unknown {
  return Object.entries(data).find(([entryKey]) => entryKey === key)?.[1];
}

function ReadOnlyFields({ data, keys }: { data: object | null; keys: string[] }) {
  if (!data) return <p className="state-note">غير متوفر.</p>;
  return <dl className="admin-readonly-grid">{keys.map((key) => (
    <div key={key}><dt>{labels[key] ?? key}</dt><dd dir={key === "email" ? "ltr" : "auto"}>{displayValue(key, readField(data, key))}</dd></div>
  ))}</dl>;
}

export function AdminUserDetailsPage({ principalId }: { principalId: string }) {
  const detailRetryRef = useRef<HTMLButtonElement>(null);
  const initialDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const nextDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const refetchDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const lastFocusedDetailErrorRef = useRef<number | null>(null);
  const lastFocusedInitialDiaryErrorRef = useRef<number | null>(null);
  const lastFocusedNextDiaryErrorRef = useRef<number | null>(null);
  const lastFocusedRefetchDiaryErrorRef = useRef<number | null>(null);
  const detail = useQuery({ queryKey: ["admin-user", principalId], queryFn: () => getAdminUser(principalId) });
  const diaryQuery = useInfiniteQuery({
    queryKey: ["admin-user-diary", principalId],
    queryFn: ({ pageParam }) => getAdminUserDiary(principalId, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor,
    retry: false
  });
  const diaryEntries = diaryQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const initialDiaryFailure = diaryQuery.isLoadingError;
  const nextPageFailure = diaryQuery.isFetchNextPageError;
  const refetchFailure = diaryQuery.isRefetchError;

  useEffect(() => {
    if (!detail.isError) return;
    const occurrence = detail.errorUpdatedAt;
    if (!occurrence || lastFocusedDetailErrorRef.current === occurrence) return;
    const target = detailRetryRef.current;
    if (!target?.isConnected || target.disabled) return;
    lastFocusedDetailErrorRef.current = occurrence;
    target.focus({ preventScroll: true });
  }, [detail.errorUpdatedAt, detail.isError]);

  useEffect(() => {
    if (!detail.isSuccess || !initialDiaryFailure) return;
    const occurrence = diaryQuery.errorUpdatedAt;
    if (!occurrence || lastFocusedInitialDiaryErrorRef.current === occurrence) return;
    const target = initialDiaryRetryRef.current;
    if (!target?.isConnected || target.disabled) return;
    lastFocusedInitialDiaryErrorRef.current = occurrence;
    target.focus({ preventScroll: true });
  }, [detail.isSuccess, diaryQuery.errorUpdatedAt, initialDiaryFailure]);

  useEffect(() => {
    if (!detail.isSuccess || !nextPageFailure) return;
    const occurrence = diaryQuery.errorUpdatedAt;
    if (!occurrence || lastFocusedNextDiaryErrorRef.current === occurrence) return;
    const target = nextDiaryRetryRef.current;
    if (!target?.isConnected || target.disabled) return;
    lastFocusedNextDiaryErrorRef.current = occurrence;
    target.focus({ preventScroll: true });
  }, [detail.isSuccess, diaryQuery.errorUpdatedAt, nextPageFailure]);

  useEffect(() => {
    if (!detail.isSuccess || !refetchFailure) return;
    const occurrence = diaryQuery.errorUpdatedAt;
    if (!occurrence || lastFocusedRefetchDiaryErrorRef.current === occurrence) return;
    const target = refetchDiaryRetryRef.current;
    if (!target?.isConnected || target.disabled) return;
    lastFocusedRefetchDiaryErrorRef.current = occurrence;
    target.focus({ preventScroll: true });
  }, [detail.isSuccess, diaryQuery.errorUpdatedAt, refetchFailure]);

  if (detail.isPending) return <div className="state-note">جارٍ تحميل بيانات المستخدم...</div>;
  if (detail.isError) return <div className="state-note" role="alert"><p>تعذر تحميل بيانات المستخدم.</p><button ref={detailRetryRef} className="btn" type="button" disabled={detail.isFetching} onClick={() => detail.refetch()}>{detail.isFetching ? "جارٍ إعادة تحميل بيانات المستخدم..." : "إعادة محاولة تحميل بيانات المستخدم"}</button></div>;
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
    <section className="section-panel"><h2>اليوميات</h2>{diaryQuery.isPending ? <p aria-live="polite">جارٍ التحميل...</p> : initialDiaryFailure ? <><p role="alert">تعذر تحميل اليوميات.</p><button ref={initialDiaryRetryRef} className="btn" type="button" onClick={() => diaryQuery.refetch()}>إعادة المحاولة</button></> : <>{diaryEntries.length ? <><ul className="admin-readonly-list">{diaryEntries.map((entry) => <li key={entry.id}><strong>{entry.food_name}</strong><span>{entry.entry_date} · {entry.meal_type} · {entry.quantity}</span></li>)}</ul>{nextPageFailure ? <div role="alert"><p>تعذر تحميل المزيد من اليوميات.</p><button ref={nextDiaryRetryRef} className="btn" type="button" onClick={() => diaryQuery.fetchNextPage()}>إعادة محاولة تحميل المزيد</button></div> : null}{diaryQuery.hasNextPage && !nextPageFailure ? <button className="btn" type="button" onClick={() => diaryQuery.fetchNextPage()} disabled={diaryQuery.isFetchingNextPage}>{diaryQuery.isFetchingNextPage ? "جارٍ التحميل..." : "عرض المزيد"}</button> : null}{!diaryQuery.hasNextPage ? <p className="state-note">لا توجد إدخالات أخرى.</p> : null}</> : <p className="state-note">لا توجد إدخالات يومية.</p>}{refetchFailure ? <div role="alert"><p>تعذر تحديث اليوميات.</p><button ref={refetchDiaryRetryRef} className="btn" type="button" disabled={diaryQuery.isFetching} onClick={() => diaryQuery.refetch()}>{diaryQuery.isFetching ? "جارٍ إعادة تحديث اليوميات..." : "إعادة محاولة تحديث اليوميات"}</button></div> : null}</>}</section>
  </>;
}
