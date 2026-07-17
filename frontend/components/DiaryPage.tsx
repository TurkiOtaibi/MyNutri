"use client";

import {
  AlertCircle,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Cookie,
  LoaderCircle,
  MoreVertical,
  Moon,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Sun,
  Sunrise,
  Trash2,
  X
} from "lucide-react";
import { CSSProperties, FormEvent, MouseEvent as ReactMouseEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createDiaryEntry,
  deleteDiaryEntry,
  getNutritionRegistry,
  getWeekSummary,
  listDiaryEntries,
  listDiaryHistory,
  listFoods,
  updateDiaryEntry
} from "@/lib/api";
import { addDays, formatDayNumber, formatLongArabicDate, formatShortDate, todayInputValue, weekStartSunday } from "@/lib/dates";
import { calculateServingNutrition, defaultUnitLabels, defaultServingText, formatServingMacro, unitBasisLabels } from "@/lib/food";
import { weekdays } from "@/lib/labels";
import { definitionsFromRegistry, formatNutrientValue, targetTypeLabels, type NutrientDefinition } from "@/lib/nutrients";
import type {
  DaySummary,
  DiaryNutrientAggregate,
  DiaryEntryInput,
  DiaryEntryResponse,
  FoodResponse,
  MealType,
  NutritionSnapshot,
  NutritionRegistryResponse,
  NutritionTotals,
  TargetResponse,
  WeekSummary
} from "@/lib/types";


const FOODS_READ_ERROR = "تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.";
const DIARY_DAY_READ_ERROR = "تعذر تحميل بيانات هذا اليوم";
const WEEK_READ_ERROR = "تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.";
const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";
const FUTURE_DATE_ERROR = "لا يمكن تسجيل يوميات بتاريخ مستقبلي.";

const mealLabels: Record<MealType, string> = {
  breakfast: "فطور",
  lunch: "غداء",
  dinner: "عشاء",
  snack: "سناك",
  unspecified: "غير مصنف"
};
const standardMeals: MealType[] = ["breakfast", "lunch", "dinner", "snack"];
const shortWeekdays = ["أحد", "اثن", "ثلا", "أرب", "خمي", "جمع", "سبت"];
const mealAddLabels: Record<Exclude<MealType, "unspecified">, string> = {
  breakfast: "إضافة إلى الفطور",
  lunch: "إضافة إلى الغداء",
  dinner: "إضافة إلى العشاء",
  snack: "إضافة إلى السناك"
};

export function DiaryPage() {
  const queryClient = useQueryClient();
  const today = todayInputValue();
  const [selectedDate, setSelectedDate] = useState(today);
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
  const addTriggerKindRef = useRef("desktop");
  const weekStart = useMemo(() => weekStartSunday(selectedDate), [selectedDate]);

  const registryQuery = useQuery({ queryKey: ["nutrition-registry"], queryFn: getNutritionRegistry });
  const weekQuery = useQuery({ queryKey: ["week", weekStart], queryFn: () => getWeekSummary(weekStart) });
  const entriesQuery = useQuery({ queryKey: ["entries", selectedDate], queryFn: () => listDiaryEntries(selectedDate) });

  const selectedDay = weekQuery.data?.days.find((day) => day.date === selectedDate);
  const targets = selectedDay?.targets ?? null;
  const entries = entriesQuery.data ?? [];
  const totals = selectedDay?.totals ?? emptyNutritionTotals();

  useEffect(() => {
    if (!statusMessage) return;
    const timer = window.setTimeout(() => setStatusMessage(""), 3800);
    return () => window.clearTimeout(timer);
  }, [statusMessage]);

  useEffect(() => {
    if (!entriesQuery.isSuccess || entriesQuery.isFetching) return;
    const stored = expandedMealsByDateRef.current.get(selectedDate);
    if (stored) {
      setExpandedMeals(new Set(stored));
      return;
    }
    const first = standardMeals.find((meal) => entries.some((entry) => entry.meal_type === meal));
    const legacy = entries.some((entry) => (entry.meal_type ?? "unspecified") === "unspecified");
    const initial = new Set<MealType>(first ? [first] : legacy ? ["unspecified"] : []);
    expandedMealsByDateRef.current.set(selectedDate, initial);
    setExpandedMeals(initial);
  }, [selectedDate, entries, entriesQuery.isSuccess, entriesQuery.isFetching]);

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
    mutationFn: deleteDiaryEntry,
    onSuccess: async () => {
      setDeleteError("");
      setDeletingEntry(null);
      await invalidateDiary(queryClient);
    },
    onError: () => setDeleteError("تعذر حذف الطعام")
  });

  function chooseDate(nextDate: string) {
    if (nextDate > today) {
      setDateError(FUTURE_DATE_ERROR);
      return;
    }
    setDateError("");
    setStatusMessage("");
    setSelectedDate(nextDate);
  }

  function openAdd(event: ReactMouseEvent<HTMLButtonElement>, meal: MealType | null = null) {
    addTriggerKindRef.current = event.currentTarget.dataset.diaryAddTrigger ?? "desktop";
    setStatusMessage("");
    setAddMeal(meal);
    setAddOpen(true);
  }

  function closeAdd() {
    const triggerKind = addTriggerKindRef.current;
    setAddOpen(false);
    requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(`[data-diary-add-trigger="${triggerKind}"]`)?.focus();
    });
  }

  return (
    <div className="diary-page">
      <h1 className="sr-only">اليوميات</h1>

      <CompactWeekNavigator
        week={weekQuery.data}
        pending={weekQuery.isPending}
        error={weekQuery.isError}
        selectedDate={selectedDate}
        today={today}
        target={targets?.target_calories ?? 0}
        dateError={dateError}
        onSelect={chooseDate}
        onRetry={() => weekQuery.refetch()}
      />

      <div className="diary-layout">
        <main className="diary-log" aria-labelledby="daily-log-title">
          <div className="diary-section-heading">
            <h2 id="daily-log-title">وجبات اليوم</h2>
          </div>

          {entriesQuery.isPending ? <DiaryEntriesSkeleton /> : null}
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
                expandedMealsByDateRef.current.set(selectedDate, new Set(next));
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
            <RetryState message={WEEK_READ_ERROR} onRetry={() => weekQuery.refetch()} compact />
          ) : (
            <DailyProgressSummary totals={totals} targets={targets} pending={weekQuery.isPending || entriesQuery.isPending} failed={entriesQuery.isError} onOpenNutrition={() => setNutritionDetailsOpen(true)} />
          )}
        </aside>
      </div>

      {statusMessage ? <div className="diary-status" role="status" aria-live="polite">{statusMessage}</div> : null}

      {nutritionDetailsOpen ? <DailyNutritionDetails day={selectedDay} registry={registryQuery.data} registryPending={registryQuery.isPending} registryFailed={registryQuery.isError} onRetryRegistry={() => registryQuery.refetch()} onClose={() => setNutritionDetailsOpen(false)} /> : null}

      {addOpen ? (
        <AddEntrySheet
          selectedDate={selectedDate}
          initialMeal={addMeal}
          onClose={closeAdd}
          onSaved={async (savedMeal) => {
            setAddOpen(false);
            setExpandedMeals((current) => {
              const next = new Set(current).add(savedMeal);
              expandedMealsByDateRef.current.set(selectedDate, new Set(next));
              return next;
            });
            await invalidateDiary(queryClient);
            requestAnimationFrame(() => document.getElementById(`meal-section-${savedMeal}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
          }}
        />
      ) : null}

      {editingEntry ? (
        <EditEntryDialog
          entry={editingEntry}
          onClose={() => setEditingEntry(null)}
          onSaved={async (savedMeal) => {
            setEditingEntry(null);
            setExpandedMeals((current) => {
              const next = new Set(current).add(savedMeal);
              expandedMealsByDateRef.current.set(selectedDate, new Set(next));
              return next;
            });
            await invalidateDiary(queryClient);
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

function CompactWeekNavigator({
  week,
  pending,
  error,
  selectedDate,
  today,
  target,
  dateError,
  onSelect,
  onRetry
}: {
  week: WeekSummary | undefined;
  pending: boolean;
  error: boolean;
  selectedDate: string;
  today: string;
  target: number;
  dateError: string;
  onSelect: (date: string) => void;
  onRetry: () => void;
}) {
  const fallbackStart = weekStartSunday(selectedDate);
  const days = week?.days ?? Array.from({ length: 7 }, (_, index) => ({ date: addDays(fallbackStart, index), totals: emptyNutritionTotals() }));
  const selectedLabel = formatDiarySelectedDate(selectedDate, today);

  return (
    <section className={`compact-week-nav ${pending ? "is-loading" : ""}`} aria-label={`التنقل بين أيام اليوميات، الأسبوع من ${formatShortDate(days[0].date)} إلى ${formatShortDate(days[6].date)}`}>
      <div className={`compact-week-topline ${selectedDate !== today ? "has-today" : ""}`}>
        <button className="week-day-arrow previous" type="button" onClick={() => onSelect(addDays(selectedDate, -1))} aria-label="اليوم السابق"><ChevronLeft size={19} /></button>
        <label className="compact-selected-date">
          <CalendarDays size={17} aria-hidden="true" />
          <h2>{selectedLabel}</h2>
          <input type="date" value={selectedDate} max={today} onChange={(event) => onSelect(event.target.value)} aria-label="اختيار تاريخ اليوميات" />
        </label>
        <button className="week-day-arrow next" type="button" disabled={selectedDate >= today} onClick={() => onSelect(addDays(selectedDate, 1))} aria-label="اليوم التالي"><ChevronRight size={19} /></button>
        {selectedDate !== today ? <button className="compact-today" type="button" onClick={() => onSelect(today)}>اليوم</button> : null}
      </div>
      <div className="compact-week-days" role="tablist" aria-label="أيام الأسبوع">
        {days.map((day, index) => {
          const selected = day.date === selectedDate;
          const future = day.date > today;
          const hasIntake = day.totals.calories > 0;
          return (
            <button
              className={`compact-week-day ${selected ? "selected" : ""}`}
              key={day.date}
              type="button"
              disabled={future}
              onClick={() => onSelect(day.date)}
              role="tab"
              aria-selected={selected}
              aria-current={selected ? "date" : undefined}
              aria-label={`${weekdays[index]}، ${formatShortDate(day.date)}، ${Math.round(day.totals.calories)} سعرة`}
            >
              <span>{shortWeekdays[index]}</span>
              <strong>{formatDayNumber(day.date)}</strong>
              <small>{hasIntake ? Math.round(day.totals.calories) : ""}</small>
              {hasIntake ? <i style={{ "--day-progress": `${Math.min(100, target > 0 ? day.totals.calories / target * 100 : 0)}%` } as CSSProperties} /> : null}
            </button>
          );
        })}
      </div>
      {error ? <div className="week-inline-error"><span>{WEEK_READ_ERROR}</span><button type="button" onClick={onRetry}>إعادة المحاولة</button></div> : null}
      {dateError ? <p className="field-error date-error" role="alert">{dateError}</p> : null}
    </section>
  );
}

function DailyProgressSummary({ totals, targets, pending, failed, onOpenNutrition }: { totals: NutritionTotals; targets: TargetResponse | null; pending: boolean; failed: boolean; onOpenNutrition: () => void }) {
  if (pending) return <div className="diary-summary diary-summary-loading" aria-label="جارٍ تحميل ملخص اليوم" />;
  if (failed) return <section className="diary-summary diary-summary-unavailable" aria-label="ملخص اليوم غير متاح">تعذر تحميل ملخص هذا اليوم</section>;
  if (!targets) return (
    <section className="diary-summary state-note" aria-label="ملخص اليوم دون مصدر هدف">
      <h2>ملخص اليوم</h2>
      <p>لا يوجد مصدر هدف محفوظ لهذا اليوم.</p>
      <button className="diary-nutrition-details-action" type="button" onClick={onOpenNutrition}>عرض التفاصيل الغذائية</button>
    </section>
  );

  const remaining = Math.max(targets.target_calories - totals.calories, 0);
  const exceeded = totals.calories > targets.target_calories;
  const reached = Math.round(totals.calories) === Math.round(targets.target_calories);
  const caloriePercent = targets.target_calories > 0 ? Math.round(totals.calories / targets.target_calories * 100) : 0;
  return (
    <section className="diary-summary">
      <div className="diary-summary-heading">
        <h2>ملخص اليوم</h2>
      </div>
      <div className="calorie-summary-primary">
        <strong aria-label={`${Math.round(totals.calories)} من ${targets.target_calories} سعرة`}>
          <bdi>{Math.round(totals.calories)}</bdi>
          <span> من </span>
          <bdi>{targets.target_calories}</bdi>
          <small> سعرة</small>
        </strong>
        <p className={exceeded ? "over" : reached ? "reached" : ""}>
          {exceeded ? `+${Math.round(totals.calories - targets.target_calories)} فوق الهدف` : reached ? "تم الوصول إلى الهدف" : `المتبقي ${Math.round(remaining)}`}
        </p>
      </div>
      <div className={`diary-progress-track ${exceeded ? "over" : reached ? "reached" : ""}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(caloriePercent, 100)} aria-label={`${caloriePercent}% من هدف السعرات`}>
        <span style={{ width: `${Math.min(caloriePercent, 100)}%` }} />
      </div>
      <div className="macro-progress-list">
        <MacroProgress label="البروتين" value={totals.protein_g} max={targets.protein_g} />
        <MacroProgress label="الكارب" value={totals.carb_g} max={targets.carb_g} />
        <MacroProgress label="الدهون" value={totals.fat_g} max={targets.fat_g} />
      </div>
      <button className="diary-nutrition-details-action" type="button" onClick={onOpenNutrition}>عرض التفاصيل الغذائية</button>
    </section>
  );
}

function MacroProgress({ label, value, max }: { label: string; value: number; max: number }) {
  const percent = max > 0 ? Math.round((value / max) * 100) : 0;
  const over = percent > 100;
  const visualPercent = Math.min(percent, 100);
  const minimumVisualPixels = visualPercent === 0 ? 0 : visualPercent < 5 ? 4 : visualPercent < 15 ? 8 : visualPercent < 30 ? 14 : 0;
  return (
    <div className={`macro-progress-row ${over ? "over" : ""}`} aria-label={`${label}: ${formatServingMacro(value)} من ${formatServingMacro(max)} جم، ${percent}%${over ? `، فوق الهدف بـ ${formatServingMacro(value - max)} جم` : ""}`}>
      <div>
        <strong>{label}</strong>
        <span className="macro-value-expression">
          <bdi dir="ltr">{formatServingMacro(value)}</bdi>
          <span> من </span>
          <bdi dir="ltr">{formatServingMacro(max)}</bdi>
          <span> جم</span>
        </span>
      </div>
      <div
        className={`macro-progress-track ${visualPercent > 0 ? "has-progress" : ""}`}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${formatServingMacro(value)} من ${formatServingMacro(max)} جم، ${percent}%${over ? `، فوق الهدف بـ ${formatServingMacro(value - max)} جم` : ""}`}
      >
        <span style={{ "--macro-progress": `${visualPercent}%`, "--macro-min-progress": `${minimumVisualPixels}px` } as CSSProperties} />
      </div>
      <small>{percent}%</small>
    </div>
  );
}

function mealItemCountLabel(count: number): string {
  if (count === 0) return "لا توجد أطعمة";
  if (count === 1) return "طعام واحد";
  if (count === 2) return "طعامان";
  if (count >= 3 && count <= 10) return `${count} أطعمة`;
  return `${count} طعامًا`;
}

function MealSections({
  entries,
  expanded,
  openMenuId,
  onToggleMeal,
  onAdd,
  onToggleMenu,
  onEdit,
  onDelete,
  deletingId
}: {
  entries: DiaryEntryResponse[];
  expanded: Set<MealType>;
  openMenuId: string | null;
  onToggleMeal: (meal: MealType) => void;
  onAdd: (event: ReactMouseEvent<HTMLButtonElement>, meal: MealType) => void;
  onToggleMenu: (id: string) => void;
  onEdit: (entry: DiaryEntryResponse) => void;
  onDelete: (entry: DiaryEntryResponse) => void;
  deletingId: string | null;
}) {
  const normalizedMeal = (entry: DiaryEntryResponse): MealType => entry.meal_type ?? "unspecified";
  const hasLegacy = entries.some((entry) => normalizedMeal(entry) === "unspecified");
  const meals = hasLegacy ? [...standardMeals, "unspecified" as MealType] : standardMeals;
  return (
    <div className="meal-sections" aria-label="سجل الطعام حسب الوجبة">
      {meals.map((meal) => {
        const items = entries.filter((entry) => normalizedMeal(entry) === meal);
        const calories = Math.round(items.reduce((sum, entry) => sum + entry.totals.calories, 0));
        const protein = items.reduce((sum, entry) => sum + entry.totals.protein_g, 0);
        const carbs = items.reduce((sum, entry) => sum + entry.totals.carb_g, 0);
        const fat = items.reduce((sum, entry) => sum + entry.totals.fat_g, 0);
        const isOpen = expanded.has(meal);
        const Icon = meal === "breakfast" ? Sunrise : meal === "lunch" ? Sun : meal === "dinner" ? Moon : Cookie;
        return (
          <section id={`meal-section-${meal}`} className={`meal-section ${isOpen ? "open" : ""}`} key={meal}>
            <div className="meal-section-header">
              <button className="meal-toggle" type="button" aria-expanded={isOpen} aria-controls={`meal-${meal}`} aria-label={`${isOpen ? "إغلاق" : "فتح"} قسم ${mealLabels[meal]}`} onClick={() => onToggleMeal(meal)}>
                <Icon size={21} aria-hidden="true" />
                <span className="meal-title-copy"><strong>{mealLabels[meal]}</strong><small>{items.length === 0 ? mealItemCountLabel(0) : <>{mealItemCountLabel(items.length)} · <bdi dir="ltr">{calories}</bdi> سعرة</>}</small>{items.length > 0 ? <small className="meal-macro-totals"><bdi dir="ltr">بروتين {formatServingMacro(protein)} جم</bdi><span> · </span><bdi dir="ltr">كارب {formatServingMacro(carbs)} جم</bdi><span> · </span><bdi dir="ltr">دهون {formatServingMacro(fat)} جم</bdi></small> : null}</span>
                <ChevronDown className="meal-chevron" size={18} aria-hidden="true" />
              </button>
              {meal !== "unspecified" ? (
                <button data-diary-add-trigger={`meal-${meal}`} className="btn icon meal-add" type="button" onClick={(event) => onAdd(event, meal)} aria-label={`إضافة طعام إلى ${mealLabels[meal]}`}><Plus size={18} /></button>
              ) : null}
            </div>
            <div id={`meal-${meal}`} className="meal-section-content" hidden={!isOpen}>
              {items.map((entry) => (
                <DiaryEntryRow
                  key={entry.id}
                  entry={entry}
                  menuOpen={openMenuId === entry.id}
                  onToggleMenu={() => onToggleMenu(entry.id)}
                  onEdit={() => onEdit(entry)}
                  onDelete={() => onDelete(entry)}
                  deleting={deletingId === entry.id}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function DiaryEntryRow({
  entry,
  menuOpen,
  onToggleMenu,
  onEdit,
  onDelete,
  deleting
}: {
  entry: DiaryEntryResponse;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onEdit: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <article className={`diary-entry-row ${deleting ? "is-deleting" : ""}`} role="button" tabIndex={deleting ? -1 : 0} aria-label={`تعديل ${entry.nutrition_snapshot.name}`} onClick={() => { if (!deleting) onEdit(); }} onKeyDown={(event) => { if (!deleting && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onEdit(); } }}>
      <div className="diary-entry-copy">
        <h3 dir="auto">{entry.nutrition_snapshot.name}</h3>
        <p>{entryQuantityLabel(entry)}</p>
      </div>
      <strong className="diary-entry-calories"><bdi dir="ltr">{Math.round(entry.totals.calories)}</bdi> سعرة</strong>
      <div className="entry-menu-wrap" onClick={(event) => event.stopPropagation()}>
        <button className="btn icon entry-menu-trigger" type="button" disabled={deleting} onClick={onToggleMenu} aria-label={`خيارات ${entry.nutrition_snapshot.name}`} aria-expanded={menuOpen}>
          <MoreVertical size={18} />
        </button>
        {menuOpen ? (
          <div className="entry-action-menu" role="menu">
            <button type="button" role="menuitem" onClick={onEdit}><Pencil size={16} /> تعديل</button>
            <button type="button" role="menuitem" className="danger-text" onClick={onDelete}><Trash2 size={16} /> حذف</button>
          </div>
        ) : null}
      </div>
    </article>
  );
}

function DailyNutritionDetails({ day, registry, registryPending, registryFailed, onRetryRegistry, onClose }: { day: DaySummary | undefined; registry: NutritionRegistryResponse | undefined; registryPending: boolean; registryFailed: boolean; onRetryRegistry: () => void; onClose: () => void }) {
  const definitions = new Map((registry ? definitionsFromRegistry(registry) : []).map((item) => [item.key, item]));
  const overallCoverage = day?.overall_nutrient_coverage_percent ?? null;
  const empty = day?.nutrient_aggregates.every((item) => item.coverage_state === "no_entries") ?? false;
  return (
    <ModalFrame labelledBy="daily-nutrition-details-title" onClose={onClose} pending={false} className="nutrition-details-modal">
      <div className="daily-nutrition-sheet">
        <div className="add-sheet-handle" aria-hidden="true" />
        <header><h2 id="daily-nutrition-details-title">التفاصيل الغذائية لليوم</h2><button type="button" onClick={onClose} aria-label="إغلاق التفاصيل الغذائية"><X size={20} /></button></header>
        <div className="daily-nutrition-sheet-content">
          {registryPending ? <div className="daily-nutrition-empty" role="status">جارٍ تحميل سجل المغذيات</div> : registryFailed || !registry ? <div className="daily-nutrition-empty" role="alert">تعذر تحميل سجل المغذيات<button className="btn" type="button" onClick={onRetryRegistry}>إعادة المحاولة</button></div> : !day ? <div className="daily-nutrition-empty">تعذر تحميل ملخص المغذيات لهذا اليوم.</div> : empty ? <div className="daily-nutrition-empty">لا توجد أطعمة مسجلة لهذا اليوم</div> : <>
            <section className="nutrition-coverage-notice" aria-label={`تغطية بيانات المغذيات الإضافية: ${overallCoverage}%`}><strong>تغطية بيانات المغذيات الإضافية: <bdi>{overallCoverage}%</bdi></strong>{overallCoverage !== 100 ? <p>بعض الأطعمة لا تحتوي بيانات كاملة لجميع المغذيات. هذه نسبة توفر البيانات وليست تقييمًا صحيًا، وقد تكون المجاميع المعروضة حدًا أدنى مؤكدًا.</p> : <p>تتوفر بيانات جميع المغذيات المتتبعة للأطعمة المسجلة.</p>}</section>
            <div className="daily-nutrient-list">{day.nutrient_aggregates.map((item) => <DailyNutrientRow key={item.key} aggregate={item} definition={definitions.get(item.key)} />)}</div>
          </>}
        </div>
      </div>
    </ModalFrame>
  );
}

const evaluationLabels: Record<string, string> = {
  met: "تم تحقيق الهدف",
  below_target: "أقل من الهدف",
  within_limit: "ضمن الحد",
  at_limit: "تم الوصول إلى الحد",
  exceeded: "تم تجاوز الحد",
  below_range: "أقل من النطاق",
  within_range: "ضمن النطاق",
  above_range: "أعلى من النطاق",
  met_at_least: "تم تحقيق الهدف بالقيمة المؤكدة",
  exceeded_at_least: "تم تجاوز الحد بالقيمة المؤكدة",
  above_range_at_least: "أعلى من النطاق بالقيمة المؤكدة",
  indeterminate_partial_coverage: "لا يمكن تحديد الحالة مع التغطية الجزئية"
};

function DailyNutrientRow({ aggregate, definition }: { aggregate: DiaryNutrientAggregate; definition: NutrientDefinition | undefined }) {
  const precision = definition?.precision ?? 1;
  const unit = definition?.unit ?? aggregate.target?.unit ?? "";
  if (!definition) return null;
  const label = definition.label;
  const targetType = aggregate.target?.type ?? definition?.targetType ?? "monitor_only";
  const targetValue = aggregate.target?.value ?? null;
  const amountText = aggregate.amount === null ? "غير متوفر" : `${formatNutrientValue(aggregate.amount, precision)} ${unit}`;
  const qualifier = aggregate.amount_qualifier === "at_least" ? "على الأقل" : "";
  const status = aggregate.evaluation ? evaluationLabels[aggregate.evaluation] ?? aggregate.evaluation : targetType === "monitor_only" ? "متابعة فقط" : aggregate.target ? "" : "لا يوجد مصدر هدف محفوظ";
  const overMaximum = aggregate.evaluation === "exceeded" || aggregate.evaluation === "exceeded_at_least";
  const showProgress = aggregate.progress_percent !== null;
  return (
    <section className={`daily-nutrient-row ${overMaximum ? "over" : ""}`} aria-label={`${label}: ${qualifier} ${amountText}، ${status}${aggregate.coverage_percent == null ? "" : `، تغطية البيانات ${aggregate.coverage_percent}%`}`}>
      <header><strong>{label}</strong><span>{targetValue == null ? targetTypeLabels[targetType] : `${targetTypeLabels[targetType]} ${formatNutrientValue(targetValue, precision)} ${unit}`}</span></header>
      <div className="daily-nutrient-value"><bdi dir={aggregate.amount === null ? "rtl" : "ltr"}>{amountText}</bdi>{qualifier ? <small>{qualifier}</small> : null}</div>
      {showProgress ? <div className="daily-nutrient-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(aggregate.progress_percent ?? 0, 100)} aria-valuetext={`${aggregate.progress_percent}%`}><span style={{ width: `${Math.min(aggregate.progress_percent ?? 0, 100)}%` }} /></div> : null}
      <footer><span>{status}</span>{aggregate.coverage_percent != null ? <small>تغطية البيانات <bdi>{aggregate.coverage_percent}%</bdi></small> : null}</footer>
      {aggregate.coverage_state === "partial" ? <p>بعض الأطعمة المسجلة لا تحتوي قيمة لهذا المغذي.</p> : null}
    </section>
  );
}

function AddEntrySheet({ selectedDate, initialMeal, onClose, onSaved }: { selectedDate: string; initialMeal: MealType | null; onClose: () => void; onSaved: (meal: MealType) => Promise<void> }) {
  const [search, setSearch] = useState("");
  const [selectedFood, setSelectedFood] = useState<FoodResponse | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [mealType, setMealType] = useState<MealType | null>(initialMeal);
  const [error, setError] = useState("");
  const [discardOpen, setDiscardOpen] = useState(false);
  const [saveSucceeded, setSaveSucceeded] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const dragStartRef = useRef<number | null>(null);
  const submitLockRef = useRef(false);
  const debouncedSearch = useDebouncedValue(search, 275);
  const foodsQuery = useQuery({
    queryKey: ["diary-food-search", debouncedSearch],
    queryFn: () => listFoods(debouncedSearch),
    staleTime: 30_000,
    placeholderData: (previous) => previous
  });
  const historyQuery = useQuery({
    queryKey: ["diary-history-for-recent-foods"],
    queryFn: listDiaryHistory,
    staleTime: 60_000
  });

  const mutation = useMutation({
    mutationFn: (payload: DiaryEntryInput) => createDiaryEntry(payload),
    onSuccess: async () => {
      setSaveSucceeded(true);
      setError("");
      await new Promise((resolve) => window.setTimeout(resolve, 320));
      await onSaved(mealType as MealType);
    },
    onError: () => {
      submitLockRef.current = false;
      setError("تعذر إضافة الطعام");
    }
  });
  const amount = parseQuantity(quantity);
  const quantityError = selectedFood ? validateQuantity(quantity) : "";
  const preview = selectedFood && amount != null ? multiplyServing(selectedFood, amount) : null;
  const equivalentAmount = selectedFood && amount != null ? selectedFood.unit_amount * amount : null;
  const allFoods = foodsQuery.data ?? [];
  const recentFoods = useMemo(() => {
    if (debouncedSearch.trim()) return [];
    const foodsById = new Map(allFoods.map((food) => [food.id, food]));
    const seen = new Set<string>();
    const recent: FoodResponse[] = [];
    for (const entry of historyQuery.data ?? []) {
      const id = entry.food_id ?? entry.nutrition_snapshot.food_id;
      if (!id || seen.has(id)) continue;
      const food = foodsById.get(id);
      if (!food) continue;
      seen.add(id);
      recent.push(food);
      if (recent.length === 5) break;
    }
    return recent;
  }, [allFoods, debouncedSearch, historyQuery.data]);
  const recentIds = new Set(recentFoods.map((food) => food.id));
  const visibleFoods = debouncedSearch.trim() ? allFoods : allFoods.filter((food) => !recentIds.has(food.id));
  const hasMeaningfulChanges = Boolean(selectedFood) || quantity !== "1" || mealType !== initialMeal;

  useEffect(() => {
    if (!discardOpen) return;
    requestAnimationFrame(() => document.querySelector<HTMLElement>(".discard-confirm [data-initial-focus]")?.focus());
  }, [discardOpen]);

  function requestClose() {
    if (mutation.isPending || saveSucceeded) return;
    if (hasMeaningfulChanges) {
      setDiscardOpen(true);
      return;
    }
    onClose();
  }

  function chooseFood(food: FoodResponse) {
    setSelectedFood(food);
    setQuantity("1");
    setError("");
  }

  function changeFood() {
    setSelectedFood(null);
    setQuantity("1");
    setError("");
    requestAnimationFrame(() => searchRef.current?.focus());
  }

  function saveCurrent() {
    if (submitLockRef.current || mutation.isPending || saveSucceeded || !selectedFood || !mealType || amount == null || quantityError) return;
    submitLockRef.current = true;
    setError("");
    mutation.mutate({ entry_date: selectedDate, food_id: selectedFood.id, quantity: amount, meal_type: mealType });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveCurrent();
  }

  return (
    <ModalFrame className="entry-sheet" labelledBy="add-entry-title" onClose={requestClose} pending={mutation.isPending || saveSucceeded}>
      <form className="add-food-sheet-form" onSubmit={submit}>
        <div className="add-sheet-header">
          <button
            className="sheet-drag-handle"
            type="button"
            aria-label="اسحب لأسفل لإغلاق إضافة الطعام"
            onTouchStart={(event) => { dragStartRef.current = event.touches[0]?.clientY ?? null; }}
            onTouchEnd={(event) => {
              const end = event.changedTouches[0]?.clientY;
              if (dragStartRef.current != null && end != null && end - dragStartRef.current > 80) requestClose();
              dragStartRef.current = null;
            }}
          ><span /></button>
          <div className="add-sheet-title-row">
            <div>
              <h2 id="add-entry-title">إضافة طعام</h2>
              <p>{formatLongArabicDate(selectedDate)}</p>
            </div>
            <button className="btn icon add-sheet-close" type="button" onClick={requestClose} aria-label="إغلاق إضافة الطعام"><X size={19} /></button>
          </div>
        </div>

        <div className={`add-sheet-content ${selectedFood ? "configure-state" : "search-state"}`}>
          {!selectedFood ? (
            <div className="add-food-search-state">
              <div className="add-search-sticky">
                <h3>اختر الطعام</h3>
                <label className="field diary-search-field">
                  <span className="sr-only">البحث عن طعام</span>
                  <div className="search-control">
                    <Search size={18} aria-hidden="true" />
                    <input ref={searchRef} data-initial-focus className="input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث باسم الطعام أو العلامة التجارية" dir="auto" />
                    {search ? <button className="search-clear" type="button" onClick={() => { setSearch(""); requestAnimationFrame(() => searchRef.current?.focus()); }} aria-label="مسح البحث"><X size={16} /></button> : null}
                  </div>
                </label>
              </div>
              <div className="diary-food-results" aria-label="نتائج بحث الأطعمة">
                {foodsQuery.isPending && !foodsQuery.data ? <FoodResultSkeletons /> : null}
                {foodsQuery.isError ? <RetryState message="تعذر تحميل الأطعمة" onRetry={() => foodsQuery.refetch()} compact /> : null}
                {!foodsQuery.isPending && !foodsQuery.isError && debouncedSearch.trim() && allFoods.length === 0 ? (
                  <div className="add-search-empty"><strong>لم نجد طعامًا مطابقًا</strong><span>جرّب اسمًا آخر أو ابحث بالعلامة التجارية</span></div>
                ) : null}
                {!foodsQuery.isError && !debouncedSearch.trim() ? (
                  <>
                    <FoodResultGroup title="المستخدمة مؤخرًا" foods={recentFoods} onChoose={chooseFood} emptyText="لا توجد أطعمة مستخدمة مؤخرًا." />
                    <FoodResultGroup title="جميع الأطعمة" foods={visibleFoods} onChoose={chooseFood} />
                  </>
                ) : null}
                {!foodsQuery.isError && debouncedSearch.trim() ? <FoodResultGroup foods={allFoods} onChoose={chooseFood} /> : null}
              </div>
            </div>
          ) : (
            <div className="add-food-configure-state">
              <SelectedFoodSummary food={selectedFood} onChange={changeFood} />
              <section className="add-config-section">
                <h3>قسم الوجبة</h3>
                <MealTypeSelector value={mealType} onChange={(value) => { setMealType(value); setError(""); }} />
              </section>
              <section className="add-config-section">
                <h3>الكمية</h3>
            <QuantityStepper
              value={quantity}
              unitLabel={defaultUnitLabels[selectedFood.default_unit_type]}
              errorId={quantityError || error ? "entry-form-error" : undefined}
              onChange={(value) => { setQuantity(value); setError(""); }}
            />
                {quantityError ? <p id="entry-form-error" className="field-error quantity-inline-error" role="alert">{quantityError}</p> : null}
              </section>
            {preview ? (
              <div className="add-nutrition-preview" aria-label="معاينة القيم الغذائية" aria-live="polite">
                <p>المجموع لـ <bdi dir="ltr">{formatServingMacro(amount ?? 0)}</bdi> {defaultUnitLabels[selectedFood.default_unit_type]}{equivalentAmount != null ? <> · <bdi dir="ltr">{formatServingMacro(equivalentAmount)}</bdi> {unitBasisLabels[selectedFood.unit_basis]}</> : null}</p>
                <div className="add-calorie-total"><strong>{Math.round(preview.calories)}</strong><span>سعرة حرارية</span></div>
                <div className="add-macro-row">
                  <span>بروتين <strong><bdi dir="ltr">{formatServingMacro(preview.protein_g)}</bdi> جم</strong></span>
                  <span>كارب <strong><bdi dir="ltr">{formatServingMacro(preview.carb_g)}</bdi> جم</strong></span>
                  <span>دهون <strong><bdi dir="ltr">{formatServingMacro(preview.fat_g)}</bdi> جم</strong></span>
                </div>
              </div>
            ) : null}
            </div>
          )}
        </div>

        <div className="add-sheet-footer">
          {selectedFood ? (
            <>
              {error && !quantityError ? <div className="add-save-error" role="alert"><strong>{error}</strong><span>حاول مرة أخرى.</span><button type="button" onClick={saveCurrent}>إعادة المحاولة</button></div> : null}
              <button className="btn primary add-food-submit" type="submit" disabled={mutation.isPending || saveSucceeded || Boolean(quantityError) || !mealType}>
                {mutation.isPending ? <><LoaderCircle className="spin" size={17} /> جارٍ الإضافة…</> : saveSucceeded ? <><Check size={18} /> تمت الإضافة</> : mealType && mealType !== "unspecified" ? mealAddLabels[mealType] : "إضافة الطعام"}
              </button>
              {!mealType ? <span className="add-action-helper">اختر قسم الوجبة للمتابعة</span> : null}
            </>
          ) : null}
          <button className="add-sheet-cancel" type="button" onClick={requestClose} disabled={mutation.isPending || saveSucceeded}>إلغاء</button>
        </div>

        {discardOpen ? (
          <div className="discard-confirm-backdrop" role="presentation">
            <section className="discard-confirm" role="alertdialog" aria-modal="true" aria-labelledby="discard-title" aria-describedby="discard-description">
              <h3 id="discard-title">إلغاء إضافة الطعام؟</h3>
              <p id="discard-description">ستفقد التغييرات الحالية.</p>
              <button data-initial-focus className="btn primary" type="button" onClick={() => setDiscardOpen(false)}>متابعة التعديل</button>
              <button className="btn" type="button" onClick={onClose}>إلغاء الإضافة</button>
            </section>
          </div>
        ) : null}
      </form>
    </ModalFrame>
  );
}

function FoodResultGroup({ title, foods, onChoose, emptyText }: { title?: string; foods: FoodResponse[]; onChoose: (food: FoodResponse) => void; emptyText?: string }) {
  return (
    <section className="food-result-group">
      {title ? <h4>{title}</h4> : null}
      {foods.length === 0 && emptyText ? <p className="recent-foods-empty">{emptyText}</p> : null}
      <div className="food-result-list">
        {foods.slice(0, 30).map((food) => <FoodResultRow key={food.id} food={food} onChoose={onChoose} />)}
      </div>
    </section>
  );
}

function FoodResultRow({ food, onChoose }: { food: FoodResponse; onChoose: (food: FoodResponse) => void }) {
  const serving = calculateServingNutrition(food);
  return (
    <button className="diary-food-option" type="button" onClick={() => onChoose(food)} aria-label={`${food.name}، ${defaultServingText(food)}، ${serving ? Math.round(serving.calories) : "غير متاح"} سعرة`}>
      <span className="diary-food-option-copy">
        <strong dir="auto">{food.name}</strong>
        {food.brand ? <small dir="auto">{food.brand}</small> : null}
        <small><span dir="auto">{defaultServingText(food)}</span> · {serving ? Math.round(serving.calories) : "—"} سعرة</small>
      </span>
    </button>
  );
}

function FoodResultSkeletons() {
  return <div className="food-result-skeletons" aria-label="جارٍ تحميل الأطعمة" role="status">{[1, 2, 3, 4].map((item) => <span key={item} />)}</div>;
}

function SelectedFoodSummary({ food, onChange }: { food: FoodResponse; onChange: () => void }) {
  const serving = calculateServingNutrition(food);
  return (
    <section className="selected-food-summary" aria-label={`الطعام المحدد: ${food.name}`}>
      <div>
        <h3 dir="auto">{food.name}</h3>
        {food.brand ? <p dir="auto">{food.brand}</p> : null}
        <p className="selected-food-serving"><bdi>{defaultServingText(food)}</bdi> · <bdi>{serving ? Math.round(serving.calories) : "—"} سعرة</bdi></p>
      </div>
      <button type="button" onClick={onChange}>تغيير الطعام</button>
    </section>
  );
}

function EditEntryDialog({ entry, onClose, onSaved }: { entry: DiaryEntryResponse; onClose: () => void; onSaved: (meal: MealType) => Promise<void> }) {
  const [quantity, setQuantity] = useState(String(entry.quantity));
  const [mealType, setMealType] = useState<MealType>(entry.meal_type ?? "unspecified");
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: (amount: number) => updateDiaryEntry(entry.id, amount, mealType),
    onSuccess: () => onSaved(mealType),
    onError: () => setError(WRITE_ERROR)
  });
  const amount = parseQuantity(quantity);
  const quantityError = validateQuantity(quantity);
  const preview = amount == null ? null : scaleEntryPreview(entry, amount);
  const equivalentAmount = amount != null && entry.nutrition_snapshot.unit_amount
    ? Number(entry.nutrition_snapshot.unit_amount) * amount
    : null;
  const unitLabel = entry.nutrition_snapshot.default_unit_type
    ? defaultUnitLabels[entry.nutrition_snapshot.default_unit_type]
    : "حصة";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (amount == null || quantityError) {
      setError(quantityError || "أدخل كمية صحيحة.");
      return;
    }
    if (!mutation.isPending) mutation.mutate(amount);
  }

  return (
    <ModalFrame labelledBy="edit-entry-title" onClose={onClose} pending={mutation.isPending}>
      <form onSubmit={submit}>
        <div className="sheet-header">
          <div><p className="section-eyebrow-text" dir="auto">{entry.nutrition_snapshot.name}</p><h2 id="edit-entry-title">تعديل الكمية والقسم</h2></div>
          <button className="btn icon" type="button" onClick={onClose} aria-label="إغلاق تعديل الكمية"><X size={19} /></button>
        </div>
        <p className="dialog-help">يمكن تعديل الكمية والقسم فقط. يبقى الطعام والتاريخ وبياناته الغذائية كما سُجلت.</p>
        <MealTypeSelector value={mealType} onChange={setMealType} />
        <QuantityStepper
          value={quantity}
          unitLabel={unitLabel}
          errorId={quantityError || error ? "edit-quantity-error" : undefined}
          initialFocus
          onChange={(value) => { setQuantity(value); setError(""); }}
        />
        {preview ? (
          <div className="entry-preview edit-entry-preview" aria-label="معاينة القيم الغذائية بعد التعديل" aria-live="polite">
            <p>
              <bdi dir="ltr">{formatServingMacro(amount ?? 0)}</bdi> {unitLabel}
              {equivalentAmount != null && entry.nutrition_snapshot.unit_basis ? <> · <bdi dir="ltr">{formatServingMacro(equivalentAmount)}</bdi> {unitBasisLabels[entry.nutrition_snapshot.unit_basis]}</> : null}
            </p>
            <div>
              <span><strong>{Math.round(preview.calories)}</strong> سعرة</span>
              <span><strong>{formatServingMacro(preview.protein_g)}</strong> بروتين</span>
              <span><strong>{formatServingMacro(preview.carb_g)}</strong> كارب</span>
              <span><strong>{formatServingMacro(preview.fat_g)}</strong> دهون</span>
            </div>
          </div>
        ) : null}
        {quantityError || error ? <p id="edit-quantity-error" className="field-error" role="alert">{error || quantityError}</p> : null}
        <div className="sheet-actions"><button className="btn" type="button" onClick={onClose}>إلغاء</button><button className="btn primary" type="submit" disabled={mutation.isPending || Boolean(quantityError)}>{mutation.isPending ? "جارٍ الحفظ…" : "حفظ التغييرات"}</button></div>
      </form>
    </ModalFrame>
  );
}

function MealTypeSelector({ value, onChange }: { value: MealType | null; onChange: (value: MealType) => void }) {
  return (
    <div className="meal-type-selector" role="radiogroup" aria-label="قسم الوجبة">
      {standardMeals.map((meal) => (
        <button key={meal} type="button" role="radio" aria-checked={value === meal} className={value === meal ? "selected" : ""} onClick={() => onChange(meal)}>
          {mealLabels[meal]}
        </button>
      ))}
    </div>
  );
}

function QuantityStepper({
  value,
  unitLabel,
  errorId,
  initialFocus = false,
  onChange
}: {
  value: string;
  unitLabel: string;
  errorId?: string;
  initialFocus?: boolean;
  onChange: (value: string) => void;
}) {
  const amount = parseQuantity(value);
  const invalid = Boolean(validateQuantity(value));

  function adjust(delta: number) {
    const current = amount ?? 1;
    const next = Math.min(50, Math.max(0.01, Math.round((current + delta) * 100) / 100));
    onChange(String(next));
  }

  return (
    <div className="quantity-stepper-field">
      <span className="quantity-stepper-label">الكمية</span>
      <div className={`quantity-stepper ${invalid ? "invalid" : ""}`}>
        <button
          type="button"
          onClick={() => adjust(-0.5)}
          disabled={amount != null && amount <= 0.01}
          aria-label="تقليل الكمية"
        >
          <span aria-hidden="true">−</span>
        </button>
        <label>
          <span className="sr-only">الكمية</span>
          <input
            data-initial-focus={initialFocus ? "true" : undefined}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            aria-label="الكمية"
            aria-invalid={invalid}
            aria-describedby={errorId}
          />
          <span className="quantity-unit">{unitLabel}</span>
        </label>
        <button type="button" onClick={() => adjust(0.5)} disabled={amount != null && amount >= 50} aria-label="زيادة الكمية">
          <span aria-hidden="true">+</span>
        </button>
      </div>
    </div>
  );
}

function ConfirmDialog({ title, description, confirmLabel, cancelLabel = "إلغاء", error = "", pending, onClose, onConfirm }: { title: string; description: string; confirmLabel: string; cancelLabel?: string; error?: string; pending: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <ModalFrame labelledBy="confirm-entry-title" onClose={onClose} pending={pending}>
      <div className="confirm-entry-dialog">
        <div className="dialog-danger-icon"><AlertCircle size={22} /></div>
        <h2 id="confirm-entry-title">{title}</h2>
        <p>{description}</p>
        {error ? <div className="delete-inline-error" role="alert"><strong>{error}</strong><span>حاول مرة أخرى</span></div> : null}
        <div className="sheet-actions">
          <button data-initial-focus className="btn" type="button" onClick={onClose} disabled={pending}>{cancelLabel}</button>
          <button className="btn danger" type="button" onClick={onConfirm} disabled={pending}>{confirmLabel}</button>
        </div>
      </div>
    </ModalFrame>
  );
}

function ModalFrame({ children, labelledBy, onClose, pending, className = "" }: { children: ReactNode; labelledBy: string; onClose: () => void; pending: boolean; className?: string }) {
  const panelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusable = () => Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])') ?? []);
    (panel?.querySelector<HTMLElement>("[data-initial-focus]") ?? focusable()[0])?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pending) onClose();
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", handleKey);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.classList.remove("modal-open");
      previous?.focus();
    };
  }, [onClose, pending]);

  return (
    <div className={`diary-modal-backdrop ${className}`} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !pending) onClose(); }}>
      <div ref={panelRef} className="diary-modal-panel" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>{children}</div>
    </div>
  );
}

function RetryState({ message, description = "", onRetry, compact = false }: { message: string; description?: string; onRetry: () => void; compact?: boolean }) {
  return (
    <div className={`diary-error-state ${compact ? "compact" : ""}`} role="alert">
      <AlertCircle size={20} />
      <span><strong>{message}</strong>{description ? <small>{description}</small> : null}</span>
      <button className="btn" type="button" onClick={onRetry}><RotateCcw size={16} /> إعادة المحاولة</button>
    </div>
  );
}

function DiaryEntriesSkeleton() {
  return <div className="diary-entry-list" aria-label="جارٍ تحميل يوميات اليوم">{[1, 2, 3].map((item) => <div className="diary-entry-skeleton" key={item} />)}</div>;
}

function emptyNutritionTotals(): NutritionTotals {
  return {
    calories: 0, protein_g: 0, carb_g: 0, fat_g: 0, net_carbs_g: 0,
    saturated_fat_g: null, trans_fat_g: null, cholesterol_mg: null, sodium_mg: null,
    fiber_g: null, sugar_g: null, added_sugar_g: null, potassium_mg: null, calcium_mg: null,
    iron_mg: null, magnesium_mg: null, zinc_mg: null, selenium_mcg: null,
    vitamin_d_mcg: null, vitamin_b12_mcg: null, vitamin_c_mg: null,
    vitamin_a_mcg: null, vitamin_a_rae_mcg: null, folate_mcg: null,
    folate_dfe_mcg: null, vitamin_k_mcg: null, iodine_mcg: null
  };
}

function formatDiarySelectedDate(input: string, today: string): string {
  const full = formatLongArabicDate(input);
  return input.slice(0, 4) === today.slice(0, 4) ? full.replace(/\s\d{4}$/, "") : full;
}

function multiplyServing(food: FoodResponse, quantity: number) {
  const serving = calculateServingNutrition(food);
  if (!serving) return null;
  return {
    calories: serving.calories * quantity,
    protein_g: serving.protein_g * quantity,
    carb_g: serving.carb_g * quantity,
    fat_g: serving.fat_g * quantity
  };
}

function scaleEntryPreview(entry: DiaryEntryResponse, quantity: number) {
  const factor = quantity / entry.quantity;
  return {
    calories: entry.totals.calories * factor,
    protein_g: entry.totals.protein_g * factor,
    carb_g: entry.totals.carb_g * factor,
    fat_g: entry.totals.fat_g * factor
  };
}

function parseQuantity(value: string): number | null {
  const trimmed = value.trim();
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return null;
  const amount = Number(trimmed);
  return Number.isFinite(amount) && amount >= 0.01 && amount <= 50 ? amount : null;
}

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

function validateQuantity(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "أدخل كمية صحيحة";
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return "أدخل كمية صحيحة";
  const amount = Number(trimmed);
  if (!Number.isFinite(amount)) return "أدخل كمية صحيحة";
  if (amount < 0.01) return "أدخل كمية أكبر من 0";
  if (amount > 50) return "الكمية يجب ألا تتجاوز 50 حصة";
  return "";
}

function entryQuantityLabel(entry: DiaryEntryResponse): string {
  const snapshot = entry.nutrition_snapshot;
  const unit = snapshot.default_unit_type ? defaultUnitLabels[snapshot.default_unit_type] : "حصة";
  const basis = snapshot.unit_basis ? unitBasisLabels[snapshot.unit_basis] : "جم";
  const amount = snapshot.unit_amount ? Number(snapshot.unit_amount) * entry.quantity : null;
  return amount ? `${formatServingMacro(entry.quantity)} ${unit} · ${formatServingMacro(amount)} ${basis}` : `${formatServingMacro(entry.quantity)} ${snapshotUnitLabel(snapshot)}`;
}

function snapshotUnitLabel(snapshot: NutritionSnapshot): string {
  if (snapshot.default_unit_type && snapshot.unit_amount && snapshot.unit_basis) {
    return `${defaultUnitLabels[snapshot.default_unit_type]} (${snapshot.unit_amount} ${unitBasisLabels[snapshot.unit_basis]})`;
  }
  return snapshot.serving_label ?? "حصة";
}

async function invalidateDiary(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["entries"] }),
    queryClient.invalidateQueries({ queryKey: ["week"] })
  ]);
}
