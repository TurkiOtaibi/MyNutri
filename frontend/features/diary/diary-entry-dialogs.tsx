import { AlertCircle, Check, LoaderCircle, RotateCcw, Search, X } from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { createDiaryEntry, listFoodPicker, updateDiaryEntry } from "@/lib/api";
import { formatLongArabicDate } from "@/lib/dates";
import { defaultServingText, defaultUnitLabels, formatServingMacro, unitBasisLabels } from "@/lib/food";
import type { DiaryEntryInput, DiaryEntryResponse, FoodPickerItem, MealType } from "@/lib/types";
import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { mealAddLabels, mealLabels, multiplyServing, parseQuantity, pickerServingNutrition, scaleEntryPreview, standardMeals, validateQuantity } from "./diary-model";
import { useDebouncedValue } from "./diary-hooks";

const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";

export function AddEntrySheet({ selectedDate, initialMeal, onClose, onSaved }: { selectedDate: string; initialMeal: MealType | null; onClose: () => void; onSaved: (meal: MealType) => Promise<void> }) {
  const [search, setSearch] = useState("");
  const [selectedFood, setSelectedFood] = useState<FoodPickerItem | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [mealType, setMealType] = useState<MealType | null>(initialMeal);
  const [error, setError] = useState("");
  const [discardOpen, setDiscardOpen] = useState(false);
  const [saveSucceeded, setSaveSucceeded] = useState(false);
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const searchRef = useRef<HTMLInputElement>(null);
  const dragStartRef = useRef<number | null>(null);
  const submitLockRef = useRef(false);
  const debouncedSearch = useDebouncedValue(search, 275);
  const normalizedSearch = debouncedSearch.trim();
  const foodsQuery = useInfiniteQuery({
    queryKey: ["diary-food-picker", session?.user.id, normalizedSearch],
    queryFn: ({ pageParam, signal }) => listFoodPicker({
      accessToken,
      search: normalizedSearch,
      cursor: pageParam,
      limit: 30,
      signal: AbortSignal.any([signal, sessionSignal])
    }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: Boolean(accessToken),
    staleTime: 30_000
  });

  const mutation = useMutation({
    mutationFn: (payload: DiaryEntryInput) => createDiaryEntry(payload, accessToken, sessionSignal),
    onSuccess: async () => {
      if (sessionSignal.aborted) return;
      setSaveSucceeded(true);
      setError("");
      await new Promise((resolve) => window.setTimeout(resolve, 320));
      if (sessionSignal.aborted) return;
      await onSaved(mealType as MealType);
      if (sessionSignal.aborted) return;
    },
    onError: () => {
      if (sessionSignal.aborted) return;
      submitLockRef.current = false;
      setError("تعذر إضافة الطعام");
    }
  });
  const amount = parseQuantity(quantity);
  const quantityError = selectedFood ? validateQuantity(quantity) : "";
  const preview = selectedFood && amount != null ? multiplyServing(selectedFood, amount) : null;
  const equivalentAmount = selectedFood && amount != null ? selectedFood.unit_amount * amount : null;
  const allFoods = useMemo(() => {
    const seen = new Set<string>();
    return (foodsQuery.data?.pages ?? []).flatMap((page) =>
      page.items.filter((food) => {
        if (seen.has(food.id)) return false;
        seen.add(food.id);
        return true;
      })
    );
  }, [foodsQuery.data]);
  const recentFoods = normalizedSearch ? [] : foodsQuery.data?.pages[0]?.recent_items ?? [];
  const recentIds = new Set(recentFoods.map((food) => food.id));
  const visibleFoods = debouncedSearch.trim() ? allFoods : allFoods.filter((food) => !recentIds.has(food.id));
  const hasMeaningfulChanges = Boolean(selectedFood) || quantity !== "1" || mealType !== initialMeal;

  function requestClose() {
    if (mutation.isPending || saveSucceeded) return;
    if (hasMeaningfulChanges) {
      setDiscardOpen(true);
      return;
    }
    onClose();
  }

  function chooseFood(food: FoodPickerItem) {
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
    <ModalFrame className="entry-sheet" labelledBy="add-entry-title" describedBy="add-entry-description" onClose={requestClose} pending={mutation.isPending || saveSucceeded}>
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
              <p id="add-entry-description">{formatLongArabicDate(selectedDate)}</p>
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
                {!foodsQuery.isError && foodsQuery.hasNextPage ? (
                  <button
                    className="btn"
                    type="button"
                    onClick={() => foodsQuery.fetchNextPage()}
                    disabled={foodsQuery.isFetchingNextPage}
                  >
                    {foodsQuery.isFetchingNextPage ? "جاري التحميل…" : "عرض المزيد"}
                  </button>
                ) : null}
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
          <ModalFrame
            className="discard-confirm-backdrop"
            panelClassName="discard-confirm"
            role="alertdialog"
            labelledBy="discard-title"
            describedBy="discard-description"
            onClose={() => setDiscardOpen(false)}
            pending={false}
          >
            <h3 id="discard-title">إلغاء إضافة الطعام؟</h3>
            <p id="discard-description">ستفقد التغييرات الحالية.</p>
            <button data-initial-focus className="btn primary" type="button" onClick={() => setDiscardOpen(false)}>متابعة التعديل</button>
            <button className="btn" type="button" onClick={onClose}>إلغاء الإضافة</button>
          </ModalFrame>
        ) : null}
      </form>
    </ModalFrame>
  );
}

export function FoodResultGroup({ title, foods, onChoose, emptyText }: { title?: string; foods: FoodPickerItem[]; onChoose: (food: FoodPickerItem) => void; emptyText?: string }) {
  return (
    <section className="food-result-group">
      {title ? <h4>{title}</h4> : null}
      {foods.length === 0 && emptyText ? <p className="recent-foods-empty">{emptyText}</p> : null}
      <div className="food-result-list">
        {foods.map((food) => <FoodResultRow key={food.id} food={food} onChoose={onChoose} />)}
      </div>
    </section>
  );
}

export function FoodResultRow({ food, onChoose }: { food: FoodPickerItem; onChoose: (food: FoodPickerItem) => void }) {
  const serving = pickerServingNutrition(food);
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

export function FoodResultSkeletons() {
  return <div className="food-result-skeletons" aria-label="جارٍ تحميل الأطعمة" role="status">{[1, 2, 3, 4].map((item) => <span key={item} />)}</div>;
}

export function SelectedFoodSummary({ food, onChange }: { food: FoodPickerItem; onChange: () => void }) {
  const serving = pickerServingNutrition(food);
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

export function EditEntryDialog({ entry, onClose, onSaved }: { entry: DiaryEntryResponse; onClose: () => void; onSaved: (meal: MealType) => Promise<void> }) {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const [quantity, setQuantity] = useState(String(entry.quantity));
  const [mealType, setMealType] = useState<MealType>(entry.meal_type ?? "unspecified");
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: (amount: number) => updateDiaryEntry(entry.id, amount, mealType, accessToken, sessionSignal),
    onSuccess: async () => {
      if (sessionSignal.aborted) return;
      await onSaved(mealType);
      if (sessionSignal.aborted) return;
    },
    onError: () => {
      if (sessionSignal.aborted) return;
      setError(WRITE_ERROR);
    }
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

export function MealTypeSelector({ value, onChange }: { value: MealType | null; onChange: (value: MealType) => void }) {
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

export function QuantityStepper({
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

export function ConfirmDialog({ title, description, confirmLabel, cancelLabel = "إلغاء", error = "", pending, onClose, onConfirm }: { title: string; description: string; confirmLabel: string; cancelLabel?: string; error?: string; pending: boolean; onClose: () => void; onConfirm: () => void }) {
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

export type ModalFocusScope = {
  panel: HTMLDivElement;
  opener: HTMLElement | null;
  fallbackOpener: HTMLElement | null;
  onCloseRef: { current: () => void };
  pendingRef: { current: boolean };
};

export const modalFocusScopes: ModalFocusScope[] = [];

export function focusableElements(panel: HTMLElement): HTMLElement[] {
  return Array.from(panel.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter((element) => element.getClientRects().length > 0 && !element.closest("[inert]"));
}

export function topModalScope(): ModalFocusScope | undefined {
  return modalFocusScopes[modalFocusScopes.length - 1];
}

export function syncModalFocusOwnership() {
  const top = topModalScope();
  for (const scope of modalFocusScopes) {
    if (scope === top) {
      scope.panel.removeAttribute("inert");
      scope.panel.removeAttribute("aria-hidden");
    } else {
      scope.panel.setAttribute("inert", "");
      scope.panel.setAttribute("aria-hidden", "true");
    }
  }
}

export function handleModalKeyDown(event: KeyboardEvent) {
  const scope = topModalScope();
  if (!scope) return;
  if (event.key === "Escape") {
    if (!scope.pendingRef.current) {
      event.preventDefault();
      scope.onCloseRef.current();
    }
    return;
  }
  if (event.key !== "Tab") return;
  const items = focusableElements(scope.panel);
  if (!items.length) {
    event.preventDefault();
    scope.panel.focus();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  if (!scope.panel.contains(active)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  } else if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

export function registerModalFocusScope(scope: ModalFocusScope) {
  if (modalFocusScopes.length === 0) {
    document.addEventListener("keydown", handleModalKeyDown);
    document.body.classList.add("modal-open");
  }
  modalFocusScopes.push(scope);
  syncModalFocusOwnership();
  (scope.panel.querySelector<HTMLElement>("[data-initial-focus]") ?? focusableElements(scope.panel)[0] ?? scope.panel).focus();
}

export function unregisterModalFocusScope(scope: ModalFocusScope) {
  const wasTop = topModalScope() === scope;
  const index = modalFocusScopes.indexOf(scope);
  if (index >= 0) modalFocusScopes.splice(index, 1);
  syncModalFocusOwnership();
  if (modalFocusScopes.length === 0) {
    document.removeEventListener("keydown", handleModalKeyDown);
    document.body.classList.remove("modal-open");
  }
  if (!wasTop) return;
  const restoreTarget = scope.opener?.isConnected && !scope.opener.closest("[inert]") ? scope.opener : scope.fallbackOpener;
  if (restoreTarget?.isConnected && !restoreTarget.closest("[inert]")) restoreTarget.focus();
}

export function ModalFrame({
  children,
  labelledBy,
  describedBy,
  onClose,
  pending,
  className = "",
  panelClassName = "",
  role = "dialog"
}: {
  children: ReactNode;
  labelledBy: string;
  describedBy?: string;
  onClose: () => void;
  pending: boolean;
  className?: string;
  panelClassName?: string;
  role?: "dialog" | "alertdialog";
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const pendingRef = useRef(pending);

  useEffect(() => {
    onCloseRef.current = onClose;
    pendingRef.current = pending;
  }, [onClose, pending]);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    const parentScope = topModalScope();
    const opener = document.activeElement as HTMLElement | null;
    const scope: ModalFocusScope = {
      panel,
      opener,
      fallbackOpener: parentScope?.fallbackOpener ?? parentScope?.opener ?? opener,
      onCloseRef,
      pendingRef
    };
    registerModalFocusScope(scope);
    return () => unregisterModalFocusScope(scope);
  }, []);

  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!pending || !panel || topModalScope()?.panel !== panel) return;
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const activeRemainsUsable = Boolean(
      active
      && active.isConnected
      && panel.contains(active)
      && active.getClientRects().length > 0
      && !active.matches(":disabled")
      && active.getAttribute("aria-disabled") !== "true"
      && !active.closest("[inert]")
      && !active.closest('[aria-hidden="true"]')
    );
    if (!activeRemainsUsable) panel.focus();
  }, [pending]);

  return createPortal(
    <div className={`diary-modal-backdrop ${className}`} role="presentation" onMouseDown={(event) => {
      if (event.target !== event.currentTarget) return;
      if (pendingRef.current) {
        event.preventDefault();
        return;
      }
      onCloseRef.current();
    }}>
      <div
        ref={panelRef}
        className={`diary-modal-panel ${panelClassName}`}
        role={role}
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}

export function RetryState({ message, description = "", onRetry, compact = false }: { message: string; description?: string; onRetry: () => void; compact?: boolean }) {
  return (
    <div className={`diary-error-state ${compact ? "compact" : ""}`} role="alert">
      <AlertCircle size={20} />
      <span><strong>{message}</strong>{description ? <small>{description}</small> : null}</span>
      <button className="btn" type="button" onClick={onRetry}><RotateCcw size={16} /> إعادة المحاولة</button>
    </div>
  );
}

export function DiaryEntriesSkeleton({ message }: { message: string }) {
  return (
    <div className="diary-entry-list">
      <span className="sr-only" role="status">{message}</span>
      {[1, 2, 3].map((item) => <div aria-hidden="true" className="diary-entry-skeleton" key={item} />)}
    </div>
  );
}
