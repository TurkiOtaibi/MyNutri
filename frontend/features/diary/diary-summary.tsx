import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Cookie, MoreVertical, Moon, Pencil, Plus, Sun, Sunrise, Trash2, X } from "lucide-react";
import type { CSSProperties, MouseEvent as ReactMouseEvent, SyntheticEvent } from "react";
import { addDays, formatDayNumber, formatLongArabicDate, formatShortDate, weekStartSunday } from "@/lib/dates";
import { formatServingMacro } from "@/lib/food";
import { weekdays } from "@/lib/labels";
import { definitionsFromRegistry, formatNutrientValue, targetTypeLabels, type NutrientDefinition } from "@/lib/nutrients";
import type { DaySummary, DiaryDayStatusResponse, DiaryEntryResponse, DiaryNutrientAggregate, MealType, NutritionRegistryResponse, NutritionTotals, TargetResponse, WeekSummary } from "@/lib/types";
import { dayLoggingStatusLabels, emptyNutritionTotals, entryQuantityLabel, formatDiarySelectedDate, isFutureDiaryStatus, mealItemCountLabel, mealLabels, shortWeekdays, standardMeals } from "./diary-model";
import { ModalFrame } from "./diary-entry-dialogs";

const WEEK_READ_ERROR = "تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.";

export function CompactWeekNavigator({
  week,
  pending,
  error,
  selectedDate,
  today,
  dateError,
  onSelect,
  onRetry
}: {
  week: WeekSummary | undefined;
  pending: boolean;
  error: boolean;
  selectedDate: string;
  today: string;
  dateError: string;
  onSelect: (date: string) => void;
  onRetry: () => void;
}) {
  const fallbackStart = weekStartSunday(selectedDate);
  const days: Array<Pick<DaySummary, "date" | "totals" | "targets" | "logging_status">> = week?.days ?? Array.from({ length: 7 }, (_, index) => ({
    date: addDays(fallbackStart, index),
    totals: emptyNutritionTotals(),
    targets: null,
    logging_status: "unregistered"
  }));
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
          const dayTarget = day.targets?.target_calories;
          const progress = typeof dayTarget === "number" && Number.isFinite(dayTarget) && dayTarget > 0
            ? Math.min(100, Math.max(0, day.totals.calories / dayTarget * 100))
            : null;
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
              aria-label={`${weekdays[index]}، ${formatShortDate(day.date)}، ${Math.round(day.totals.calories)} سعرة، ${dayLoggingStatusLabels[day.logging_status]}`}
            >
              <span>{shortWeekdays[index]}</span>
              <strong>{formatDayNumber(day.date)}</strong>
              <small><span aria-hidden="true">{day.logging_status === "complete" ? "✓" : day.logging_status === "partial" ? "◐" : "○"}</span> {hasIntake ? `${Math.round(day.totals.calories)} · ` : ""}{dayLoggingStatusLabels[day.logging_status]}</small>
              {hasIntake && progress !== null ? <i style={{ "--day-progress": `${progress}%` } as CSSProperties} /> : null}
            </button>
          );
        })}
      </div>
      {error ? <div className="week-inline-error"><span>{WEEK_READ_ERROR}</span><button type="button" onClick={onRetry}>إعادة المحاولة</button></div> : null}
      {dateError ? <p className="field-error date-error" role="alert">{dateError}</p> : null}
    </section>
  );
}

export function DayLoggingStatusCard({
  status,
  pending,
  failed,
  stale,
  commandPending,
  onComplete,
  onReopen,
  onRetry
}: {
  status: DiaryDayStatusResponse | undefined;
  pending: boolean;
  failed: boolean;
  stale: boolean;
  commandPending: boolean;
  onComplete: () => void;
  onReopen: () => void;
  onRetry: () => void;
}) {
  if (pending) return <section className="day-status-card is-loading" role="status" aria-busy="true">جارٍ تحميل حالة اليوم</section>;
  if (failed || !status) return <section className="day-status-card" role="alert">تعذر تحميل حالة تسجيل اليوم <button type="button" onClick={onRetry}>إعادة المحاولة</button></section>;
  const future = isFutureDiaryStatus(status);
  return (
    <section className={`day-status-card status-${status.logging_status}`} aria-labelledby="day-status-title" aria-label={`${formatLongArabicDate(status.date)}، ${dayLoggingStatusLabels[status.logging_status]}`}>
      <div>
        <h2 id="day-status-title" tabIndex={-1}>حالة تسجيل اليوم<span className="sr-only">، {formatLongArabicDate(status.date)}، {dayLoggingStatusLabels[status.logging_status]}</span></h2>
        <strong><span aria-hidden="true">{status.logging_status === "complete" ? "✓" : status.logging_status === "partial" ? "◐" : "○"}</span> {dayLoggingStatusLabels[status.logging_status]}</strong>
      </div>
      {stale ? <p role="status">قد تكون الحالة المعروضة قديمة. تعذر تحديثها الآن. <button type="button" onClick={onRetry}>إعادة المحاولة</button></p> : null}
      {status.logging_status === "partial" ? <p>لن يُعامل هذا اليوم كاستهلاك صفري، ولن يدخل في التحليل حتى تنهي تسجيله.</p> : null}
      {future ? <p>لا يمكن إنهاء تسجيل يوم مستقبلي.</p> : null}
      {status.logging_status === "complete" ? (
        <button type="button" disabled={commandPending || future} onClick={onReopen}>إعادة فتح اليوم</button>
      ) : (
        <button type="button" disabled={commandPending || future} onClick={onComplete}>إنهاء تسجيل اليوم</button>
      )}
    </section>
  );
}

const targetProvenanceLabels: Record<DaySummary["target_provenance"], string> = {
  versioned_plan: "أهداف خطة محفوظة",
  legacy_unversioned: "أهداف قديمة غير محدثة",
  no_target_source: "دون مصدر هدف محفوظ"
};

export function DailyProgressSummary({ totals, targets, targetProvenance, pending, failed, onOpenNutrition }: { totals: NutritionTotals; targets: TargetResponse | null; targetProvenance: DaySummary["target_provenance"]; pending: boolean; failed: boolean; onOpenNutrition: () => void }) {
  if (pending) return (
    <div className="diary-summary diary-summary-loading">
      <span className="sr-only" role="status">جارٍ تحميل ملخص اليوم</span>
    </div>
  );
  if (failed) return <section className="diary-summary diary-summary-unavailable" aria-label="ملخص اليوم غير متاح">تعذر تحميل ملخص هذا اليوم</section>;
  if (!targets) return (
    <section className="diary-summary state-note" aria-label="ملخص اليوم دون مصدر هدف">
      <h2>ملخص اليوم</h2>
      <span className="target-provenance-label">{targetProvenanceLabels[targetProvenance]}</span>
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
        <span className="target-provenance-label">{targetProvenanceLabels[targetProvenance]}</span>
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

export function MacroProgress({ label, value, max }: { label: string; value: number; max: number }) {
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

export function MealSections({
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
  onEdit: (event: SyntheticEvent<HTMLElement>, entry: DiaryEntryResponse) => void;
  onDelete: (event: ReactMouseEvent<HTMLButtonElement>, entry: DiaryEntryResponse) => void;
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
                  onEdit={(event) => onEdit(event, entry)}
                  onDelete={(event) => onDelete(event, entry)}
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

export function DiaryEntryRow({
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
  onEdit: (event: SyntheticEvent<HTMLElement>) => void;
  onDelete: (event: ReactMouseEvent<HTMLButtonElement>) => void;
  deleting: boolean;
}) {
  return (
    <article className={`diary-entry-row ${deleting ? "is-deleting" : ""}`} role="button" tabIndex={deleting ? -1 : 0} aria-label={`تعديل ${entry.nutrition_snapshot.name}`} onClick={(event) => { if (!deleting) onEdit(event); }} onKeyDown={(event) => { if (!deleting && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onEdit(event); } }}>
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
            <button type="button" role="menuitem" data-diary-entry-action={`edit-${entry.id}`} onClick={onEdit}><Pencil size={16} /> تعديل</button>
            <button type="button" role="menuitem" data-diary-entry-action={`delete-${entry.id}`} className="danger-text" onClick={onDelete}><Trash2 size={16} /> حذف</button>
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function DailyNutritionDetails({ day, registry, registryPending, registryFailed, onRetryRegistry, onClose }: { day: DaySummary | undefined; registry: NutritionRegistryResponse | undefined; registryPending: boolean; registryFailed: boolean; onRetryRegistry: () => void; onClose: () => void }) {
  const definitions = new Map((registry ? definitionsFromRegistry(registry) : []).map((item) => [item.key, item]));
  const overallCoverage = day?.overall_nutrient_coverage_percent ?? null;
  const empty = day?.nutrient_aggregates.every((item) => item.coverage_state === "no_entries") ?? false;
  return (
    <ModalFrame labelledBy="daily-nutrition-details-title" onClose={onClose} pending={false} className="nutrition-details-modal">
      <div className="daily-nutrition-sheet">
        <div className="add-sheet-handle" aria-hidden="true" />
        <header><h2 id="daily-nutrition-details-title">التفاصيل الغذائية لليوم</h2><button type="button" onClick={onClose} aria-label="إغلاق التفاصيل الغذائية"><X size={20} /></button></header>
        <div className="daily-nutrition-sheet-content">
          {registryPending ? <div className="daily-nutrition-empty" role="status">جارٍ تحميل سجل المغذيات</div> : registryFailed || !registry ? <div className="daily-nutrition-empty" role="alert">تعذر تحميل البيانات الغذائية<button className="btn" type="button" onClick={onRetryRegistry}>إعادة المحاولة</button></div> : registry.registry_schema_version !== 2 ? <div className="daily-nutrition-empty" role="alert">إصدار سجل التغذية غير متوافق. لا يمكن عرض تفاصيل مغذيات غير موثوقة.<button className="btn" type="button" onClick={onRetryRegistry}>إعادة المحاولة</button></div> : !day ? <div className="daily-nutrition-empty">تعذر تحميل ملخص المغذيات لهذا اليوم.</div> : empty ? <div className="daily-nutrition-empty">لا توجد أطعمة مسجلة لهذا اليوم</div> : <>
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

export function DailyNutrientRow({ aggregate, definition }: { aggregate: DiaryNutrientAggregate; definition: NutrientDefinition | undefined }) {
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
