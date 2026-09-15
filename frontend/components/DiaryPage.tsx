"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  deleteDiaryEntry,
  getCalendarAuthority,
  getNutritionRegistry,
  getWeekSummary,
  listDiaryEntries
} from "@/lib/api";
import { weekStartSunday } from "@/lib/dates";
import type {
  DiaryEntryResponse,
  MealType
} from "@/lib/types";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { CompactWeekNavigator, DailyNutritionDetails, DailyProgressSummary, MealSections } from "@/features/diary/diary-summary";
import { AddEntrySheet, ConfirmDialog, DiaryEntriesSkeleton, EditEntryDialog, RetryState } from "@/features/diary/diary-entry-dialogs";
import { emptyNutritionTotals, standardMeals } from "@/features/diary/diary-model";
import { invalidateDiary, useCalendarAuthorityRefresh } from "@/features/diary/diary-hooks";
import "@/features/diary/diary.module.css";

const DIARY_DAY_READ_ERROR = "تعذر تحميل بيانات هذا اليوم";
const WEEK_READ_ERROR = "تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.";

export function DiaryPage() {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [addMeal, setAddMeal] = useState<MealType | null>(null);
  const [editingEntry, setEditingEntry] = useState<DiaryEntryResponse | null>(null);
  const [deletingEntry, setDeletingEntry] = useState<DiaryEntryResponse | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [nutritionDetailsOpen, setNutritionDetailsOpen] = useState(false);
  const [expandedMeals, setExpandedMeals] = useState<Set<MealType>>(new Set());
  const expandedMealsByDateRef = useRef(new Map<string, Set<MealType>>());
  const previousAuthoritativeDateRef = useRef<string | null>(null);
  const previousSubjectRef = useRef(session?.user.id ?? null);

  const authorityQuery = useQuery({
    queryKey: ["calendar-authority"],
    queryFn: () => getCalendarAuthority({ accessToken: accessToken!, signal: sessionSignal }),
    enabled: Boolean(accessToken),
    refetchOnWindowFocus: false,
    retry: 1
  });
  const today = authorityQuery.data?.current_diary_date ?? null;
  const activeDate = selectedDate ?? today;
  const weekStart = useMemo(() => activeDate ? weekStartSunday(activeDate) : null, [activeDate]);

  const registryQuery = useQuery({ queryKey: ["nutrition-registry"], queryFn: getNutritionRegistry });
  const weekQuery = useQuery({
    queryKey: ["week", session?.user.id, weekStart],
    queryFn: () => getWeekSummary(weekStart!),
    enabled: weekStart !== null && today !== null
  });
  const entriesQuery = useQuery({
    queryKey: ["entries", session?.user.id, activeDate],
    queryFn: () => listDiaryEntries(activeDate!),
    enabled: activeDate !== null && today !== null
  });
  const selectedDay = weekQuery.data?.days.find((day) => day.date === activeDate);
  const summaryIntegrityError = weekQuery.error instanceof ApiError && weekQuery.error.code === "DIARY_SUMMARY_DATA_INTEGRITY_ERROR";
  const targets = selectedDay?.targets ?? null;
  const entries = entriesQuery.data ?? [];
  const totals = selectedDay?.totals ?? emptyNutritionTotals();
  useCalendarAuthorityRefresh(authorityQuery.data, authorityQuery.refetch);

  useEffect(() => {
    const subject = session?.user.id ?? null;
    if (previousSubjectRef.current === subject) return;
    previousSubjectRef.current = subject;
    setAddOpen(false);
    setEditingEntry(null);
    setDeletingEntry(null);
    setOpenMenuId(null);
  }, [session?.user.id]);

  useEffect(() => {
    if (!today) return;
    const previousToday = previousAuthoritativeDateRef.current;
    setSelectedDate((current) => current === null || current === previousToday ? today : current);
    previousAuthoritativeDateRef.current = today;
  }, [today]);

  useEffect(() => {
    if (!entriesQuery.isSuccess || entriesQuery.isFetching) return;
    if (!activeDate) return;
    const stored = expandedMealsByDateRef.current.get(activeDate);
    if (stored) {
      setExpandedMeals(new Set(stored));
      return;
    }
    const first = standardMeals.find((meal) => entries.some((entry) => entry.meal_type === meal));
    const legacy = entries.some((entry) => (entry.meal_type ?? "unspecified") === "unspecified");
    const initial = new Set<MealType>(first ? [first] : legacy ? ["unspecified"] : []);
    expandedMealsByDateRef.current.set(activeDate, initial);
    setExpandedMeals(initial);
  }, [activeDate, entries, entriesQuery.isSuccess, entriesQuery.isFetching]);

  useEffect(() => {
    if (!openMenuId) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenMenuId(null);
    };
    const closeOutside = (event: PointerEvent) => {
      if (!(event.target as Element).closest(".entry-menu-wrap")) setOpenMenuId(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOutside);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOutside);
    };
  }, [openMenuId]);

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => deleteDiaryEntry(entryId, accessToken, sessionSignal),
    onSuccess: async () => {
      if (sessionSignal.aborted) return;
      setDeleteError("");
      setDeletingEntry(null);
      await invalidateDiary(queryClient);
      if (sessionSignal.aborted) return;
    },
    onError: () => {
      if (sessionSignal.aborted) return;
      setDeleteError("تعذر حذف الطعام");
    }
  });

  function chooseDate(nextDate: string) {
    setSelectedDate(nextDate);
  }

  if (!today || !activeDate) {
    return authorityQuery.isError
      ? <RetryState message="تعذر تحميل تقويم اليوميات" description="تحقق من الاتصال ثم أعد المحاولة" onRetry={() => authorityQuery.refetch()} />
      : <DiaryEntriesSkeleton message="جارٍ تحميل تقويم اليوميات" />;
  }

  function openAdd(meal: MealType | null = null) {
    setAddMeal(meal);
    setAddOpen(true);
  }

  function closeAdd() {
    setAddOpen(false);
  }

  return (
    <div className="diary-page">
      <h1 className="sr-only">اليوميات</h1>

      <CompactWeekNavigator
        week={weekQuery.data}
        pending={weekQuery.isPending}
        error={weekQuery.isError}
        selectedDate={activeDate}
        today={today}
        onSelect={chooseDate}
        onRetry={() => weekQuery.refetch()}
      />

      <div className="diary-layout">
        <main className="diary-log" aria-labelledby="daily-log-title">
          <div className="diary-section-heading">
            <h2 id="daily-log-title">وجبات اليوم</h2>
          </div>

          {entriesQuery.isPending ? <DiaryEntriesSkeleton message="جارٍ تحميل وجبات اليوم" /> : null}
          {entriesQuery.isError ? (
            <RetryState message={DIARY_DAY_READ_ERROR} description="تحقق من الاتصال ثم أعد المحاولة" onRetry={() => entriesQuery.refetch()} />
          ) : null}
          {!entriesQuery.isPending && !entriesQuery.isError ? (
            <>
            {entries.length === 0 ? <div className="diary-empty-note"><strong>لا توجد أطعمة مسجلة اليوم</strong><span>أضف طعامًا من زر + بجانب الوجبة المناسبة</span></div> : null}
            <MealSections
              entries={entries}
              expanded={expandedMeals}
              openMenuId={openMenuId}
              onToggleMeal={(meal) => setExpandedMeals((current) => {
                const next = new Set(current);
                if (next.has(meal)) next.delete(meal); else next.add(meal);
                expandedMealsByDateRef.current.set(activeDate, new Set(next));
                return next;
              })}
              onAdd={openAdd}
              onToggleMenu={(id) => setOpenMenuId((current) => current === id ? null : id)}
              onEdit={(entry) => {
                setOpenMenuId(null);
                setEditingEntry(entry);
              }}
              deletingId={deleteMutation.isPending ? deletingEntry?.id ?? null : null}
              onDelete={(entry) => {
                setOpenMenuId(null);
                setDeleteError("");
                setDeletingEntry(entry);
              }}
            />
            </>
          ) : null}
        </main>

        <aside className="diary-summary-column" aria-label="ملخص تقدم اليوم">
          {weekQuery.isError ? (
            <RetryState
              message={summaryIntegrityError ? "تعذر حساب الملخص بسبب مشكلة في بيانات يوميات محفوظة" : WEEK_READ_ERROR}
              description={summaryIntegrityError ? "المجاميع غير متاحة ولن تُعرض كقيم ناقصة. أعد المحاولة أو تواصل مع الدعم." : ""}
              onRetry={() => weekQuery.refetch()}
              compact
            />
          ) : (
            <DailyProgressSummary totals={totals} targets={targets} pending={weekQuery.isPending || entriesQuery.isPending} failed={entriesQuery.isError} onOpenNutrition={() => setNutritionDetailsOpen(true)} />
          )}
        </aside>
      </div>

      {nutritionDetailsOpen ? <DailyNutritionDetails day={selectedDay} registry={registryQuery.data} registryPending={registryQuery.isPending} registryFailed={registryQuery.isError} onRetryRegistry={() => registryQuery.refetch()} onClose={() => setNutritionDetailsOpen(false)} /> : null}

      {addOpen ? (
        <AddEntrySheet
          selectedDate={activeDate}
          initialMeal={addMeal}
          onClose={closeAdd}
          onSaved={async (savedMeal) => {
            if (sessionSignal.aborted) return;
            setAddOpen(false);
            setExpandedMeals((current) => {
              const next = new Set(current).add(savedMeal);
              expandedMealsByDateRef.current.set(activeDate, new Set(next));
              return next;
            });
            await invalidateDiary(queryClient);
            if (sessionSignal.aborted) return;
            requestAnimationFrame(() => {
              if (!sessionSignal.aborted) document.getElementById(`meal-section-${savedMeal}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
            });
          }}
        />
      ) : null}

      {editingEntry ? (
        <EditEntryDialog
          entry={editingEntry}
          onClose={() => setEditingEntry(null)}
          onSaved={async (savedMeal) => {
            if (sessionSignal.aborted) return;
            setEditingEntry(null);
            setExpandedMeals((current) => {
              const next = new Set(current).add(savedMeal);
              expandedMealsByDateRef.current.set(activeDate, new Set(next));
              return next;
            });
            await invalidateDiary(queryClient);
            if (sessionSignal.aborted) return;
          }}
        />
      ) : null}

      {deletingEntry ? (
        <ConfirmDialog
          title="حذف الطعام؟"
          description="سيُحذف هذا الطعام من سجل اليوم."
          confirmLabel={deleteMutation.isPending ? "جارٍ الحذف…" : "حذف"}
          cancelLabel="إبقاء الطعام"
          error={deleteError}
          pending={deleteMutation.isPending}
          onClose={() => { setDeleteError(""); setDeletingEntry(null); }}
          onConfirm={() => {
            if (!deleteMutation.isPending) deleteMutation.mutate(deletingEntry.id);
          }}
        />
      ) : null}

    </div>
  );
}
