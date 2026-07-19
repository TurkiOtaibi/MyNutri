"use client";

import {
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  X
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, archiveFood, deleteFood, getNutritionRegistry, listAdminFoodsPage, listFoodsPage, restoreFood } from "@/lib/api";
import {
  calculateServingNutrition,
  defaultServingText,
  formatServingCalories,
  formatServingMacro
} from "@/lib/food";
import type { FoodResponse, FoodSort } from "@/lib/types";

import { FoodDeleteDialog } from "./FoodDeleteDialog";

const FOODS_READ_ERROR = "تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.";
const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";
const UNCATEGORIZED = "__uncategorized__";
const PAGE_SIZE = 20;

const sortLabels: Record<FoodSort, string> = {
  name: "الاسم",
  recent: "الأحدث إضافة",
  calories: "السعرات للحصة",
  protein: "البروتين للحصة"
};

export function FoodsPage({ adminMode = false }: { adminMode?: boolean }) {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<FoodSort>("name");
  const [page, setPage] = useState(1);
  const [mobileItems, setMobileItems] = useState<FoodResponse[]>([]);
  const [knownCategories, setKnownCategories] = useState<string[]>([]);
  const [uncategorizedCount, setUncategorizedCount] = useState(0);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"active" | "archived">("active");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const nextSearch = searchInput.trim();
      if (nextSearch === search) return;
      setSearch(nextSearch);
      setPage(1);
      setMobileItems([]);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput, search]);

  const foodsQuery = useQuery({
    queryKey: ["foods", adminMode ? "admin" : "catalog", search, category, sort, page, status],
    queryFn: () => (adminMode ? listAdminFoodsPage : listFoodsPage)({ search, category, sort, page, pageSize: PAGE_SIZE, status })
  });
  const registryQuery = useQuery({ queryKey: ["nutrition-registry"], queryFn: getNutritionRegistry });

  useEffect(() => {
    const data = foodsQuery.data;
    if (!data) return;
    setKnownCategories(data.categories);
    setUncategorizedCount(data.uncategorized_count);
    setMobileItems((current) => {
      if (data.page === 1) return data.items;
      const ids = new Set(current.map((food) => food.id));
      return [...current, ...data.items.filter((food) => !ids.has(food.id))];
    });
    if (data.total_pages > 0 && page > data.total_pages) setPage(data.total_pages);
  }, [foodsQuery.dataUpdatedAt]);

  const deleteMutation = useMutation({
    mutationFn: deleteFood,
    onSuccess: async (result) => {
      setDeleteTarget(null);
      setOpenMenuId(null);
      setNote(result.disposition === "deleted" ? "تم حذف الطعام نهائيًا." : "الطعام مستخدم تاريخيًا، لذلك تمت أرشفته بدل حذفه.");
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        setNote("لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى.");
      } else {
        setNote(WRITE_ERROR);
      }
    }
  });

  const data = foodsQuery.data;
  const hasFilters = Boolean(search || category);
  const desktopFoods = data?.items ?? [];
  const canLoadMore = Boolean(data && page < data.total_pages);
  const shownMobileCount = Math.min(mobileItems.length, data?.total ?? mobileItems.length);
  const categoryOptions = useMemo(
    () => [
      { value: "", label: "الكل" },
      ...knownCategories.map((value) => ({
        value,
        label: registryQuery.data?.food_category_definitions.find((item) => item.key === value)?.label_ar ?? value
      })),
      ...(uncategorizedCount > 0 ? [{ value: UNCATEGORIZED, label: "غير مصنف" }] : [])
    ],
    [knownCategories, uncategorizedCount, registryQuery.data]
  );
  const categoryLabels = useMemo(
    () => new Map(registryQuery.data?.food_category_definitions.map((item) => [item.key, item.label_ar]) ?? []),
    [registryQuery.data]
  );

  function resetCollection(next: { category?: string; sort?: FoodSort }) {
    if (next.category !== undefined) setCategory(next.category);
    if (next.sort !== undefined) setSort(next.sort);
    setPage(1);
    setMobileItems([]);
    setOpenMenuId(null);
  }

  function clearFilters() {
    setSearchInput("");
    setSearch("");
    setCategory("");
    setPage(1);
    setMobileItems([]);
  }

  return (
    <>
      <div className="foods-page-head">
        <div>
          <h1 className="page-title">الأطعمة</h1>
          <p className="page-kicker">ابحث بسرعة واعرض القيم الغذائية حسب الحصة التي تستخدمها يوميًا.</p>
        </div>
        {adminMode ? (
          <Link className="btn primary foods-add-button" href="/foods/new">
            <Plus size={18} aria-hidden="true" />
            إضافة طعام
          </Link>
        ) : null}
      </div>

      <section className="foods-catalog" aria-label="كتالوج الأطعمة">
        <div className="foods-search-row">
          <label className="foods-search-field">
            <span className="sr-only">بحث باسم الطعام</span>
            <Search size={19} aria-hidden="true" />
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="ابحث عن طعام..."
              aria-label="بحث باسم الطعام"
            />
            {searchInput ? (
              <button type="button" className="search-clear" onClick={() => setSearchInput("")} aria-label="مسح البحث">
                <X size={17} aria-hidden="true" />
              </button>
            ) : null}
          </label>

          <div className="foods-desktop-controls">
            {adminMode ? (
              <label className="compact-control"><span>الحالة</span><select value={status} onChange={(event) => { setStatus(event.target.value as "active" | "archived"); setPage(1); }}><option value="active">نشط</option><option value="archived">مؤرشف</option></select></label>
            ) : null}
            <label className="compact-control">
              <span>التصنيف</span>
              <select
                value={category}
                onChange={(event) => resetCollection({ category: event.target.value })}
                aria-label="تصفية حسب التصنيف"
              >
                {categoryOptions.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="compact-control">
              <span>الترتيب</span>
              <select
                value={sort}
                onChange={(event) => resetCollection({ sort: event.target.value as FoodSort })}
                aria-label="ترتيب الأطعمة"
              >
                {Object.entries(sortLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="foods-mobile-filters" aria-label="تصنيفات الأطعمة">
          {categoryOptions.map((option) => (
            <button
              key={option.value || "all"}
              type="button"
              className={`category-chip ${category === option.value ? "active" : ""}`}
              aria-pressed={category === option.value}
              onClick={() => resetCollection({ category: option.value })}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="foods-result-bar">
          {data && !foodsQuery.isError ? (
            <span className="foods-result-count">
              عرض {(data.page - 1) * data.page_size + 1}-
              {Math.min(data.page * data.page_size, data.total)} من {data.total} طعامًا
            </span>
          ) : (
            <span />
          )}
          <label className="foods-mobile-sort">
            <span className="sr-only">ترتيب الأطعمة</span>
            <select
              value={sort}
              onChange={(event) => resetCollection({ sort: event.target.value as FoodSort })}
              aria-label="ترتيب الأطعمة"
            >
              {Object.entries(sortLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  ترتيب: {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {note ? (
          <div className="catalog-notice" role={note === WRITE_ERROR ? "alert" : "status"} aria-live="polite">
            {note}
          </div>
        ) : null}

        {foodsQuery.isPending && page === 1 ? <FoodsLoading /> : null}

        {foodsQuery.isError ? (
          <div className="catalog-state" role="alert">
            <strong>تعذر تحميل الأطعمة</strong>
            <span>{FOODS_READ_ERROR}</span>
            <button className="btn" type="button" onClick={() => foodsQuery.refetch()}>
              <RotateCcw size={18} aria-hidden="true" />
              إعادة المحاولة
            </button>
          </div>
        ) : null}

        {!foodsQuery.isPending && !foodsQuery.isError && data?.total === 0 ? (
          <EmptyFoodsState hasFilters={hasFilters} onClear={clearFilters} />
        ) : null}

        {!foodsQuery.isError && (desktopFoods.length > 0 || mobileItems.length > 0) ? (
          <>
            <div className="food-table-wrap">
              <table className="food-table serving-first-table">
                <caption className="sr-only">قائمة الأطعمة والقيم الغذائية للحصة الافتراضية</caption>
                <thead>
                  <tr>
                    <th scope="col">الطعام</th>
                    <th scope="col">التصنيف</th>
                    <th scope="col">الحصة الافتراضية</th>
                    <th scope="col">السعرات</th>
                    <th scope="col">البروتين</th>
                    <th scope="col">الكارب</th>
                    <th scope="col">الدهون</th>
                    <th scope="col"><span className="sr-only">الإجراءات</span></th>
                  </tr>
                </thead>
                <tbody>
                  {desktopFoods.map((food) => (
                    <FoodTableRow
                      key={food.id}
                      food={food}
                      menuOpen={openMenuId === `table:${food.id}`}
                      onMenuChange={(open) => setOpenMenuId(open ? `table:${food.id}` : null)}
                      onDelete={() => setDeleteTarget(food)}
                      adminMode={adminMode}
                      categoryLabel={categoryLabels.get(food.food_category_key) ?? food.food_category_key}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <div className="food-card-list">
              {mobileItems.map((food) => (
                <FoodCard
                  key={food.id}
                  food={food}
                  menuOpen={openMenuId === `card:${food.id}`}
                  onMenuChange={(open) => setOpenMenuId(open ? `card:${food.id}` : null)}
                  onDelete={() => setDeleteTarget(food)}
                  adminMode={adminMode}
                  categoryLabel={categoryLabels.get(food.food_category_key) ?? food.food_category_key}
                />
              ))}
              {foodsQuery.isPending && page > 1 ? <div className="loading-more" role="status">جاري تحميل المزيد...</div> : null}
              {canLoadMore ? (
                <button className="btn load-more" type="button" onClick={() => setPage((current) => current + 1)}>
                  عرض المزيد
                </button>
              ) : null}
              {data && mobileItems.length > 0 ? (
                <p className="mobile-result-count">عرض {shownMobileCount} من {data.total} طعامًا</p>
              ) : null}
            </div>

            {data && data.total_pages > 1 ? (
              <DesktopPagination page={data.page} totalPages={data.total_pages} onChange={setPage} />
            ) : null}
          </>
        ) : null}
      </section>

      {adminMode ? <FoodDeleteDialog
        food={deleteTarget}
        pending={deleteMutation.isPending}
        onCancel={() => {
          setDeleteTarget(null);
          setOpenMenuId(null);
        }}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      /> : null}
    </>
  );
}

function FoodTableRow({
  food,
  menuOpen,
  onMenuChange,
  onDelete,
  adminMode
  ,categoryLabel
}: {
  food: FoodResponse;
  menuOpen: boolean;
  onMenuChange: (open: boolean) => void;
  onDelete: () => void;
  adminMode: boolean;
  categoryLabel: string;
}) {
  const nutrition = calculateServingNutrition(food);
  return (
    <tr>
      <td>
        <Link className="food-table-name" href={`/foods/${food.id}`} dir="auto" aria-label={`عرض تفاصيل ${food.name}`}>
          {food.name}
        </Link>
        {food.brand ? <span className="food-table-brand" dir="auto">{food.brand}</span> : null}
      </td>
      <td>{categoryLabel}</td>
      <td><span className="serving-label">{defaultServingText(food)}</span></td>
      <NutritionCells nutrition={nutrition} />
      <td className="table-actions-cell">
        {adminMode ? <FoodActionsMenu food={food} open={menuOpen} onOpenChange={onMenuChange} onDelete={onDelete} /> : null}
      </td>
    </tr>
  );
}

function NutritionCells({ nutrition }: { nutrition: ReturnType<typeof calculateServingNutrition> }) {
  if (!nutrition) {
    return <td colSpan={4}><span className="nutrition-unavailable">غير متوفر</span></td>;
  }
  return (
    <>
      <td><strong>{formatServingCalories(nutrition.calories)}</strong><span className="cell-unit">سعرة</span></td>
      <td><strong>{formatServingMacro(nutrition.protein_g)}</strong><span className="cell-unit">جم</span></td>
      <td><strong>{formatServingMacro(nutrition.carb_g)}</strong><span className="cell-unit">جم</span></td>
      <td><strong>{formatServingMacro(nutrition.fat_g)}</strong><span className="cell-unit">جم</span></td>
    </>
  );
}

function FoodCard({
  food,
  menuOpen,
  onMenuChange,
  onDelete,
  adminMode
  ,categoryLabel
}: {
  food: FoodResponse;
  menuOpen: boolean;
  onMenuChange: (open: boolean) => void;
  onDelete: () => void;
  adminMode: boolean;
  categoryLabel: string;
}) {
  const nutrition = calculateServingNutrition(food);
  const secondary = [food.brand, categoryLabel].filter(Boolean).join(" · ");
  return (
    <article className="food-card">
      <Link className="food-card-overlay" href={`/foods/${food.id}`} aria-label={`عرض تفاصيل ${food.name}`} />
      <div className="food-card-heading">
        <div>
          <h2 className="food-card-title" title={food.name} dir="auto">{food.name}</h2>
          <p className="food-card-secondary" dir="auto">{secondary}</p>
        </div>
        {adminMode ? <FoodActionsMenu food={food} open={menuOpen} onOpenChange={onMenuChange} onDelete={onDelete} /> : null}
      </div>
      <span className="serving-badge">{defaultServingText(food)}</span>
      {nutrition ? (
        <div className="serving-macro-grid" aria-label="القيم الغذائية للحصة الافتراضية">
          <ServingMetric value={formatServingCalories(nutrition.calories)} label="سعرة" />
          <ServingMetric value={formatServingMacro(nutrition.protein_g)} label="بروتين" />
          <ServingMetric value={formatServingMacro(nutrition.carb_g)} label="كارب" />
          <ServingMetric value={formatServingMacro(nutrition.fat_g)} label="دهون" />
        </div>
      ) : (
        <span className="nutrition-unavailable">تعذر حساب قيم الحصة</span>
      )}
    </article>
  );
}

function ServingMetric({ value, label }: { value: string; label: string }) {
  return (
    <span className="serving-metric">
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  );
}

function FoodActionsMenu({
  food,
  open,
  onOpenChange,
  onDelete
}: {
  food: FoodResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete: () => void;
}) {
  const queryClient = useQueryClient();
  const statusMutation = useMutation({
    mutationFn: () => food.status === "archived" ? restoreFood(food.id) : archiveFood(food.id),
    onSuccess: async () => {
      onOpenChange(false);
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    }
  });
  const rootRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const firstItemRef = useRef<HTMLAnchorElement | null>(null);

  useEffect(() => {
    if (!open) return;
    firstItemRef.current?.focus();
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) onOpenChange(false);
    };
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", keydown);
    };
  }, [open, onOpenChange]);

  return (
    <div className="food-actions-menu" ref={rootRef}>
      <button
        ref={buttonRef}
        className="icon-button"
        type="button"
        aria-label={`إجراءات ${food.name}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => onOpenChange(!open)}
      >
        <MoreVertical size={20} aria-hidden="true" />
      </button>
      {open ? (
        <div className="food-actions-popover" role="menu">
          <Link ref={firstItemRef} href={`/foods/${food.id}/edit`} role="menuitem" onClick={() => onOpenChange(false)}>
            <Pencil size={17} aria-hidden="true" />
            تعديل
          </Link>
          <button
            type="button"
            role="menuitem"
            disabled={statusMutation.isPending}
            onClick={() => statusMutation.mutate()}
          >
            <RotateCcw size={17} aria-hidden="true" />
            {food.status === "archived" ? "استعادة" : "أرشفة"}
          </button>
          <button
            type="button"
            role="menuitem"
            className="danger-menu-item"
            onClick={onDelete}
          >
            <Trash2 size={17} aria-hidden="true" />
            حذف
          </button>
        </div>
      ) : null}
    </div>
  );
}

function DesktopPagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (page: number) => void }) {
  const pages = pageNumbers(page, totalPages);
  return (
    <nav className="foods-pagination" aria-label="صفحات الأطعمة">
      <button type="button" className="pagination-button" disabled={page === 1} onClick={() => onChange(page - 1)} aria-label="الصفحة السابقة">
        <ChevronRight size={18} aria-hidden="true" />
        السابق
      </button>
      <div className="pagination-pages">
        {pages.map((value, index) =>
          value === "ellipsis" ? (
            <span key={`ellipsis-${index}`} aria-hidden="true">…</span>
          ) : (
            <button
              key={value}
              type="button"
              className={`pagination-number ${page === value ? "active" : ""}`}
              aria-current={page === value ? "page" : undefined}
              aria-label={`الصفحة ${value}`}
              onClick={() => onChange(value)}
            >
              {value}
            </button>
          )
        )}
      </div>
      <button type="button" className="pagination-button" disabled={page === totalPages} onClick={() => onChange(page + 1)} aria-label="الصفحة التالية">
        التالي
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
    </nav>
  );
}

function pageNumbers(page: number, totalPages: number): Array<number | "ellipsis"> {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);
  const values = new Set([1, totalPages, page - 1, page, page + 1]);
  const sorted = [...values].filter((value) => value > 0 && value <= totalPages).sort((a, b) => a - b);
  const result: Array<number | "ellipsis"> = [];
  sorted.forEach((value, index) => {
    if (index > 0 && value - sorted[index - 1] > 1) result.push("ellipsis");
    result.push(value);
  });
  return result;
}

function FoodsLoading() {
  return (
    <div className="foods-loading" role="status" aria-live="polite">
      <span className="sr-only">جاري تحميل الأطعمة.</span>
      {Array.from({ length: 5 }, (_, index) => <span className="food-skeleton" key={index} />)}
    </div>
  );
}

function EmptyFoodsState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  if (hasFilters) {
    return (
      <div className="catalog-state">
        <strong>لا توجد نتائج مطابقة للبحث.</strong>
        <span>جرّب اسمًا آخر أو امسح عوامل التصفية.</span>
        <button className="btn" type="button" onClick={onClear}>مسح البحث والتصفية</button>
      </div>
    );
  }
  return (
    <div className="catalog-state">
      <strong>لا توجد أطعمة بعد.</strong>
      <span>لا توجد أطعمة نشطة في الكتالوج حاليًا.</span>
    </div>
  );
}
