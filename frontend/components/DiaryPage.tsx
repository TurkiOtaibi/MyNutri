"use client";

import { MouseEvent as ReactMouseEvent, useEffect, useMemo, useRef, useState } from "react";
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
import { invalidateDiary } from "@/features/diary/diary-hooks";
import "@/features/diary/diary.module.css";


const DIARY_DAY_READ_ERROR = "تعذر تحميل بيانات هذا اليوم";
const WEEK_READ_ERROR = "تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.";
const FUTURE_DATE_ERROR = "لا يمكن تسجيل يوميات بتاريخ مستقبلي.";
const ROLLOVER_RECHECK_DELAY_MS = 1_000;
const MAX_ROLLOVER_RECHECKS = 5;

export function DiaryPage() {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dateError, setDateError] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [addMeal, setAddMeal] = useState<MealType | null>(null);
  const [editingEntry, setEditingEntry] = useState<DiaryEntryResponse | null>(null);
  const [deletingEntry, setDeletingEntry] = useState<DiaryEntryResponse | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [nutritionDetailsOpen, setNutritionDetailsOpen] = useState(false);
  const [expandedMeals, setExpandedMeals] = useState<Set<MealType>>(new Set());
  const expandedMealsByDateRef = useRef(new Map<string, Set<MealType>>());
  const previousAuthoritativeDateRef = useRef<string | null>(null);

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
    queryKey: ["week", weekStart],
    queryFn: () => getWeekSummary(weekStart!),
    enabled: weekStart !== null && today !== null
  });
  const entriesQuery = useQuery({
    queryKey: ["entries", activeDate],
    queryFn: () => listDiaryEntries(activeDate!),
    enabled: activeDate !== null && today !== null
  });

  const selectedDay = weekQuery.data?.days.find((day) => day.date === activeDate);
  const summaryIntegrityError = weekQuery.error instanceof ApiError && weekQuery.error.code === "DIARY_SUMMARY_DATA_INTEGRITY_ERROR";
  const targets = selectedDay?.targets ?? null;
  const entries = entriesQuery.data ?? [];
  const totals = selectedDay?.totals ?? emptyNutritionTotals();

  useEffect(() => {
    if (!today) return;
    const previousToday = previousAuthoritativeDateRef.current;
    setSelectedDate((current) => current === null || current === previousToday ? today : current);
    previousAuthoritativeDateRef.current = today;
  }, [today]);

  useEffect(() => {
    const currentDiaryDate = authorityQuery.data?.current_diary_date;
    const nextRollover = authorityQuery.data?.next_rollover_at;
    if (!currentDiaryDate || !nextRollover) return;
    const rolloverTime = Date.parse(nextRollover);
    if (!Number.isFinite(rolloverTime)) return;
    let cancelled = false;
    let timer: number | undefined;

    const schedule = (delay: number, rechecks: number) => {
      timer = window.setTimeout(async () => {
        const result = await authorityQuery.refetch();
        if (cancelled) return;
        const refreshed = result.data;
        if (
          refreshed &&
          (refreshed.current_diary_date !== currentDiaryDate || refreshed.next_rollover_at !== nextRollover)
        ) {
          return;
        }

        const refreshedRollover = refreshed ? Date.parse(refreshed.next_rollover_at) : Number.NaN;
        if (Number.isFinite(refreshedRollover) && refreshedRollover > Date.now()) {
          schedule(Math.min(refreshedRollover - Date.now(), 2_147_483_647), 0);
          return;
        }
        if (rechecks < MAX_ROLLOVER_RECHECKS) {
          schedule(ROLLOVER_RECHECK_DELAY_MS, rechecks + 1);
        }
      }, Math.max(0, Math.min(delay, 2_147_483_647)));
    };

    schedule(rolloverTime - Date.now(), 0);
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [authorityQuery.data?.current_diary_date, authorityQuery.data?.next_rollover_at, authorityQuery.refetch]);

  useEffect(() => {
    const refresh = () => { void authorityQuery.refetch(); };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [authorityQuery.refetch]);

  useEffect(() => {
    if (!statusMessage) return;
    const timer = window.setTimeout(() => setStatusMessage(""), 3800);
    return () => window.clearTimeout(timer);
  }, [statusMessage]);

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
    if (!today || nextDate > today) {
      setDateError(FUTURE_DATE_ERROR);
      return;
    }
    setDateError("");
    setStatusMessage("");
    setSelectedDate(nextDate);
  }

  if (!today || !activeDate) {
    return authorityQuery.isError
      ? <RetryState message="تعذر تحميل تقويم اليوميات" description="تحقق من الاتصال ثم أعد المحاولة" onRetry={() => authorityQuery.refetch()} />
      : <DiaryEntriesSkeleton message="جارٍ تحميل تقويم اليوميات" />;
  }

  function openAdd(_event: ReactMouseEvent<HTMLButtonElement>, meal: MealType | null = null) {
    setStatusMessage("");
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
        dateError={dateError}
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
              onAdd={(event, meal) => openAdd(event, meal)}
              onToggleMenu={(id) => setOpenMenuId((current) => current === id ? null : id)}
              onEdit={(entry) => { setOpenMenuId(null); setEditingEntry(entry); }}
              deletingId={deleteMutation.isPending ? deletingEntry?.id ?? null : null}
              onDelete={(entry) => { setOpenMenuId(null); setDeleteError(""); setDeletingEntry(entry); }}
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
            <DailyProgressSummary totals={totals} targets={targets} targetProvenance={selectedDay?.target_provenance ?? "no_target_source"} pending={weekQuery.isPending || entriesQuery.isPending} failed={entriesQuery.isError} onOpenNutrition={() => setNutritionDetailsOpen(true)} />
          )}
        </aside>
      </div>

      {statusMessage ? <div className="diary-status" role="status" aria-live="polite">{statusMessage}</div> : null}

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
