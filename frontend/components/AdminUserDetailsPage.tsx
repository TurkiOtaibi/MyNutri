"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AdminAccountActions, AdminAccountActionsProvider } from "./AdminAccountActions";
import type { DaySummary, TargetResponse } from "@/lib/types";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { entryQuantityLabel, mealLabels } from "@/features/diary/diary-model";
import { accountStatusLabels, formatAdminDate, formatAdminDateTime } from "@/lib/admin-display";
import { type AdminAccount, getAdminUser, getAdminUserDiary, getAdminDiarySummaries } from "@/lib/api";

const labels: Record<string, string> = {
  display_name: "الاسم", email: "البريد الإلكتروني", username: "اسم المستخدم", last_login_at: "آخر دخول", status: "حالة الحساب",
  created_at: "تاريخ التسجيل", goal: "الهدف", weight_kg: "الوزن",
  height_cm: "الطول", activity_level: "مستوى النشاط", effective_from: "تاريخ السريان",
  revision: "النسخة", entry_date: "التاريخ", sex: "الجنس", age: "العمر", plan_created_at: "تاريخ إنشاء الخطة",
  meal_type: "الوجبة", quantity: "الكمية"
};

const detailSections = [
  ["account", "ملخص الحساب"], ["profile", "الملف"], ["target", "الأهداف المطبقة اليوم"],
  ["plans", "سجل الخطط"], ["diary", "اليوميات"]
] as const;

const semanticLabels: Record<string, string> = {
  male: "ذكر", female: "أنثى",
  active: "نشط", disabled: "معطل", user: "مستخدم", admin: "مشرف",
  cut: "خفض الوزن", maintain: "المحافظة على الوزن", bulk: "زيادة الوزن",
  sedentary: "خامل", light: "خفيف", moderate: "متوسط", active_activity: "نشط", very_active: "نشط جدًا"
};

function displayValue(key: string, value: unknown): string {
  if (key === "last_login_at") return value ? formatAdminDateTime(String(value)) ?? "غير متوفر" : "لم يسجل الدخول بعد.";
  if (value == null || value === "") return "غير متوفر";
  if (key === "username") return String(value);
  if (typeof value === "boolean") return value ? "نعم" : "لا";
  if (typeof value === "object") return "متوفر ضمن السجل";
  if (["created_at", "plan_created_at", "effective_from", "entry_date"].includes(key)) {
    const formatted = formatAdminDate(String(value));
    if (formatted) return formatted;
  }
  if (key === "weight_kg") return `${value} كجم`;
  if (key === "height_cm") return `${value} سم`;
  if (key === "age") return `${value} سنة`;
  if (key === "status" && String(value) in accountStatusLabels) return accountStatusLabels[value as AdminAccount["status"]];
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
    <div key={key} className={`admin-field-${key}`}><dt>{labels[key] ?? key}</dt><dd><bdi dir={["email", "username"].includes(key) ? "ltr" : "auto"}>{displayValue(key, readField(data, key === "plan_created_at" ? "created_at" : key))}</bdi></dd></div>
  ))}</dl>;
}

const macroFields = [["calories", "السعرات", "سعرة"], ["protein_g", "البروتين", "جم"], ["carb_g", "الكربوهيدرات", "جم"], ["fat_g", "الدهون", "جم"]] as const;
function MacroValues({ targets, day }: { targets: Pick<TargetResponse, "calories" | "protein_g" | "carb_g" | "fat_g"> | null; day?: DaySummary }) {
  return <dl className="admin-readonly-grid">{macroFields.map(([key, label, unit]) => <div key={key}><dt>{label}</dt><dd>
    {day ? <><bdi dir="ltr">{day.totals[key]}</bdi> / </> : null}<bdi dir="ltr">{targets?.[key] ?? "—"}</bdi> {unit}
  </dd></div>)}</dl>;
}

function useErrorOccurrenceFocus(
  active: boolean,
  occurrence: number,
  targetRef: { current: HTMLButtonElement | null },
) {
  const lastFocusedErrorRef = useRef<number | null>(null);
  useEffect(() => {
    if (!active || !occurrence || lastFocusedErrorRef.current === occurrence) return;
    const target = targetRef.current;
    if (!target?.isConnected || target.disabled) return;
    lastFocusedErrorRef.current = occurrence;
    target.focus({ preventScroll: true });
  }, [active, occurrence, targetRef]);
}

export function AdminUserDetailsPage({ principalId }: { principalId: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const returnQuery = new URLSearchParams();
  for (const key of ["search", "status", "page"]) { const value = params.get(key); if (value) returnQuery.set(key, value); }
  const backHref = `/admin/users${returnQuery.size ? `?${returnQuery}` : ""}`;
  const [selectedDate, setSelectedDate] = useState("");
  const detailRetryRef = useRef<HTMLButtonElement>(null);
  const planRetryRef = useRef<HTMLButtonElement>(null);
  const planHeadingRef = useRef<HTMLHeadingElement>(null);
  const previousPlanPages = useRef(0);
  const initialDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const nextDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const refetchDiaryRetryRef = useRef<HTMLButtonElement>(null);
  const detail = useInfiniteQuery({
    queryKey: ["admin-user", principalId],
    queryFn: ({ pageParam }) => getAdminUser(principalId, undefined, pageParam ? { plan_cursor: pageParam, plan_limit: 20 } : undefined),
    initialPageParam: null as string | null,
    getNextPageParam: page => page.plan_history.next_cursor,
    retry: false,
  });
  const planPageCount = detail.data?.pages.length ?? 0;
  useEffect(() => {
    if (planPageCount > previousPlanPages.current && planPageCount > 1 && !detail.hasNextPage) {
      planHeadingRef.current?.focus({ preventScroll: true });
      planHeadingRef.current?.scrollIntoView({ block: "center" });
    }
    previousPlanPages.current = planPageCount;
  }, [planPageCount, detail.hasNextPage]);
  const diaryQuery = useInfiniteQuery({
    queryKey: ["admin-user-diary", principalId, selectedDate],
    queryFn: ({ pageParam }) => getAdminUserDiary(principalId, pageParam, 50, selectedDate || undefined),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor,
    retry: false
  });
  const diaryEntries = diaryQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const dates = [...new Set(diaryEntries.map(entry => entry.entry_date))];
  if (selectedDate && !dates.includes(selectedDate)) dates.push(selectedDate);
  const summaries = useQuery({
    queryKey: ["admin-user-diary-summaries", principalId, dates],
    queryFn: async () => {
      const chunks: string[][] = [];
      for (let offset = 0; offset < dates.length; offset += 100) chunks.push(dates.slice(offset, offset + 100));
      return (await Promise.all(chunks.map(chunk => getAdminDiarySummaries(principalId, chunk)))).flat();
    },
    enabled: dates.length > 0 && diaryQuery.isSuccess,
  });
  const initialDiaryFailure = diaryQuery.isLoadingError;
  const nextPageFailure = diaryQuery.isFetchNextPageError;
  const refetchFailure = diaryQuery.isRefetchError;

  useErrorOccurrenceFocus(detail.isLoadingError, detail.errorUpdatedAt, detailRetryRef);
  useErrorOccurrenceFocus(detail.isFetchNextPageError || detail.isRefetchError, detail.errorUpdatedAt, planRetryRef);
  useErrorOccurrenceFocus(detail.isSuccess && initialDiaryFailure, diaryQuery.errorUpdatedAt, initialDiaryRetryRef);
  useErrorOccurrenceFocus(detail.isSuccess && nextPageFailure, diaryQuery.errorUpdatedAt, nextDiaryRetryRef);
  useErrorOccurrenceFocus(detail.isSuccess && refetchFailure, diaryQuery.errorUpdatedAt, refetchDiaryRetryRef);

  if (detail.isPending) return <div className="state-note">جارٍ تحميل بيانات المستخدم...</div>;
  if (!detail.data) return <div className="state-note" role="alert"><p>تعذر تحميل بيانات المستخدم.</p><button ref={detailRetryRef} className="btn" type="button" disabled={detail.isFetching} onClick={() => detail.refetch()}>{detail.isFetching ? "جارٍ إعادة تحميل بيانات المستخدم..." : "إعادة محاولة تحميل بيانات المستخدم"}</button></div>;
  const { account, profile, current_target: target } = detail.data.pages[0];
  const plans = detail.data.pages.flatMap(page => page.plan_history.items);
  const selectedName = String(account.display_name || account.username || account.email || principalId);

  return <AdminAccountActionsProvider onDeleted={() => router.push(backHref)}>
    <div className="selected-user-banner"><strong>عرض مستخدم آخر: {selectedName}</strong><span>وضع قراءة فقط</span></div>
    <div className="page-head admin-detail-head"><Link className="icon-button detail-back" href={backHref} aria-label="رجوع"><ArrowRight size={21} aria-hidden="true" /></Link><div><h1 className="page-title">تفاصيل المستخدم</h1><p className="page-kicker">بيانات الحساب والتغذية المعروضة للمراقبة دون صلاحية تعديل.</p></div><div className="actions"><AdminAccountActions account={account} /><Link className="btn" href={`/admin/users/${encodeURIComponent(principalId)}/labs`}>عرض التحاليل</Link></div></div>
    <nav className="admin-section-links" aria-label="أقسام الصفحة">{detailSections.map(([id, title]) => <a key={id} href={`#admin-section-${id}`}>{title}</a>)}</nav>
    <section id="admin-section-account" className="section-panel admin-detail-section"><h2>ملخص الحساب</h2><ReadOnlyFields data={{ ...account, username: account.username ?? account.email }} keys={["display_name", "username", "status", "created_at", "last_login_at"]} />{!account.username && <p>حساب قديم</p>}{account.role !== "admin" && account.is_locked && <span className="account-status-badge">مقفل</span>}</section>
    <section id="admin-section-profile" className="section-panel admin-detail-section"><h2>الملف</h2><ReadOnlyFields data={profile ? { ...profile, age: detail.data.pages[0].age } : null} keys={["sex", "age", "goal", "weight_kg", "height_cm", "activity_level"]} /></section>
    <section id="admin-section-target" className="section-panel admin-detail-section"><h2>الأهداف المطبقة اليوم</h2><MacroValues targets={target?.targets ?? null} /><ReadOnlyFields data={target?.plan ?? null} keys={["effective_from", "revision", "plan_created_at"]} /></section>
    <section id="admin-section-plans" className="section-panel admin-detail-section"><h2 ref={planHeadingRef} tabIndex={-1}>سجل الخطط</h2>{plans.length ? <ul className="admin-readonly-list">{plans.map(plan => <li key={plan.id}><ReadOnlyFields data={plan} keys={["effective_from", "revision", "plan_created_at"]} /></li>)}</ul> : <p className="state-note">لا توجد خطط محفوظة.</p>}
      {detail.isFetchNextPageError || detail.isRefetchError ? <div role="alert"><p>تعذر تحميل سجل الخطط</p><button ref={planRetryRef} className="btn" type="button" disabled={detail.isFetching} onClick={() => detail.isFetchNextPageError ? detail.fetchNextPage() : detail.refetch()}>إعادة المحاولة</button></div> : detail.hasNextPage ? <button className="btn" type="button" disabled={detail.isFetching} onClick={() => detail.fetchNextPage()}>{detail.isFetching ? "جارٍ التحميل…" : "عرض خطط أقدم"}</button> : null}
    </section>
    <section id="admin-section-diary" className="section-panel admin-detail-section"><h2>اليوميات</h2><label className="admin-diary-date">التاريخ<input type="date" value={selectedDate} onChange={event => setSelectedDate(event.target.value)} /></label>{diaryQuery.isPending ? <p aria-live="polite">جارٍ التحميل...</p> : initialDiaryFailure ? <><p role="alert">تعذر تحميل اليوميات.</p><button ref={initialDiaryRetryRef} className="btn" type="button" onClick={() => diaryQuery.refetch()}>إعادة المحاولة</button></> : <>{diaryEntries.length ? <>{summaries.isError && <p role="alert">تعذر تحميل مجاميع اليوميات. <button className="btn" onClick={() => summaries.refetch()}>إعادة المحاولة</button></p>}
      {dates.map(day => {
        const summary = summaries.data?.find(item => item.date === day);
        return <section key={day} className="admin-diary-day" aria-label={formatAdminDate(day) ?? day}>
          <h3><time dateTime={day}>{formatAdminDate(day)}</time></h3>
          {summary ? <><p>مجموع اليوم / الهدف</p><MacroValues targets={summary.targets} day={summary} /></> : summaries.isPending ? <p role="status">جارٍ التحميل...</p> : null}
          <ul className="admin-readonly-list">{diaryEntries.filter(entry => entry.entry_date === day).map(entry => <li key={entry.id}><strong>{entry.food_name}</strong><span>{mealLabels[entry.meal_type]} · {entryQuantityLabel(entry)}</span></li>)}</ul>
        </section>;
      })}{nextPageFailure ? <div role="alert"><p>تعذر تحميل المزيد من اليوميات.</p><button ref={nextDiaryRetryRef} className="btn" type="button" onClick={() => diaryQuery.fetchNextPage()}>إعادة محاولة تحميل المزيد</button></div> : null}{diaryQuery.hasNextPage && !nextPageFailure ? <button className="btn" type="button" onClick={() => diaryQuery.fetchNextPage()} disabled={diaryQuery.isFetchingNextPage}>{diaryQuery.isFetchingNextPage ? "جارٍ التحميل..." : "عرض المزيد"}</button> : null}{!diaryQuery.hasNextPage ? <p className="state-note">لا توجد إدخالات أخرى.</p> : null}</> : <p className="state-note">لا توجد إدخالات يومية.</p>}{refetchFailure ? <div role="alert"><p>تعذر تحديث اليوميات.</p><button ref={refetchDiaryRetryRef} className="btn" type="button" disabled={diaryQuery.isFetching} onClick={() => diaryQuery.refetch()}>{diaryQuery.isFetching ? "جارٍ إعادة تحديث اليوميات..." : "إعادة محاولة تحديث اليوميات"}</button></div> : null}</>}</section>
  </AdminAccountActionsProvider>;
}
