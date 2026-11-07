"use client";

import { Plus, RotateCcw, Search, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { clearFoodDeletionNotice, readFoodDeletionNotice } from "@/features/foods/food-notices";
import { readFoodCatalogContext, rememberFoodCatalogContext } from "@/features/foods/food-catalog-context";

import {
  DesktopPagination,
  EmptyFoodsState,
  FoodCard,
  FoodsLoading,
  FoodTableRow,
} from "@/features/foods/food-catalog-view";
import { getNutritionRegistry, listFoodsPage } from "@/lib/api";
import type { FoodResponse, FoodSort } from "@/lib/types";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { useAuth } from "./AuthProvider";
import { useFoodDelete } from "./useFoodDelete";

const FOODS_READ_ERROR = "تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.";
const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";
const PAGE_SIZE = 20;

const sortLabels: Record<FoodSort, string> = {
  name: "الاسم",
  recent: "الأحدث إضافة",
  calories: "السعرات للحصة",
  protein: "البروتين للحصة"
};

export function FoodsPage() {
  const { account } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = account?.role === "admin";
  const [initialContext] = useState(() => readFoodCatalogContext(queryClient));
  const [searchInput, setSearchInput] = useState(initialContext.searchInput);
  const searchRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState(initialContext.search);
  const [category, setCategory] = useState(initialContext.category);
  const [sort, setSort] = useState<FoodSort>(initialContext.sort);
  const [page, setPage] = useState(initialContext.page);
  const [mobileItems, setMobileItems] = useState<FoodResponse[]>(() => {
    const items = new Map<string, FoodResponse>();
    for (let previousPage = 1; previousPage <= initialContext.page; previousPage += 1) {
      const key = ["foods", "catalog", initialContext.search, initialContext.category, initialContext.sort, previousPage];
      // Edits/deletions invalidate these pages. Never restore their old snapshots.
      if (queryClient.getQueryState(key)?.isInvalidated) continue;
      const cached = queryClient.getQueryData<{ items: FoodResponse[] }>(key);
      cached?.items.forEach(food => items.set(food.id, food));
    }
    return [...items.values()];
  });
  const [knownCategories, setKnownCategories] = useState<string[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [note, setNote] = useState(() => readFoodDeletionNotice(queryClient, account?.principal_id));

  useEffect(() => {
    rememberFoodCatalogContext(queryClient, { searchInput, search, category, sort, page });
  }, [queryClient, searchInput, search, category, sort, page]);

  useEffect(() => {
    clearFoodDeletionNotice(queryClient, account?.principal_id);
  }, [queryClient, account?.principal_id]);

  const resetCollection = useCallback((next: {
    search?: string;
    category?: string;
    sort?: FoodSort;
  }) => {
    if (next.search !== undefined) setSearch(next.search);
    if (next.category !== undefined) setCategory(next.category);
    if (next.sort !== undefined) setSort(next.sort);
    setPage(1);
    setMobileItems([]);
    setOpenMenuId(null);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const nextSearch = searchInput.trim();
      if (nextSearch === search) return;
      resetCollection({ search: nextSearch });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [resetCollection, searchInput, search]);

  const foodsQuery = useQuery({
    queryKey: ["foods", "catalog", search, category, sort, page],
    queryFn: () => listFoodsPage({
      search,
      category,
      sort,
      page,
      pageSize: PAGE_SIZE
    })
  });
  const registryQuery = useQuery({ queryKey: ["nutrition-registry"], queryFn: getNutritionRegistry });

  useEffect(() => {
    const data = foodsQuery.data;
    if (!data || foodsQuery.isFetching) return;
    // The paged query is the external source for the accumulated mobile collection.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setKnownCategories(data.categories);
    setMobileItems((current) => {
      if (data.page === 1) return data.items;
      const items = new Map(current.map((food) => [food.id, food]));
      data.items.forEach(food => items.set(food.id, food));
      return [...items.values()];
    });
    if (data.total_pages > 0 && page > data.total_pages) setPage(data.total_pages);
  }, [foodsQuery.data, foodsQuery.dataUpdatedAt, foodsQuery.isFetching, page]);

  const deleteMutation = useFoodDelete({
    onDeleted: () => {
      setDeleteTarget(null);
      setOpenMenuId(null);
      setNote("تم حذف الطعام نهائيًا.");
    },
    onError: setNote
  });

  const data = foodsQuery.data;
  const retainedPageError = foodsQuery.isError && page > 1 && mobileItems.length > 0;
  const desktopFoods = data?.items ?? [];
  const canLoadMore = Boolean(data && page < data.total_pages);
  const shownMobileCount = Math.min(mobileItems.length, data?.total ?? mobileItems.length);
  const categoryOptions = useMemo(
    () => [
      { value: "", label: "الكل" },
      ...knownCategories.flatMap((value) => {
        const label = registryQuery.data?.food_taxonomy.find((item) => item.key === value)?.label_ar;
        return label ? [{
        value,
        label
      }] : [];
      }),
    ],
    [knownCategories, registryQuery.data]
  );
  const categoryLabels = useMemo(
    () => new Map(registryQuery.data?.food_taxonomy.map((item) => [item.key, item.label_ar]) ?? []),
    [registryQuery.data]
  );

  function clearFilters() {
    setSearchInput("");
    resetCollection({ search: "", category: "" });
    searchRef.current?.focus();
  }

  return (
    <>
      <div className="foods-page-head">
        <div>
          <h1 className="page-title">الأطعمة</h1>
          <p className="page-kicker">ابحث بسرعة واعرض القيم الغذائية حسب الحصة التي تستخدمها يوميًا.</p>
        </div>
        {isAdmin ? (
          <Link className="btn foods-add-button" href="/foods/new">
            <Plus size={18} aria-hidden="true" />
            إضافة طعام
          </Link>
        ) : null}
      </div>

      <section className="foods-catalog" aria-label="كتالوج الأطعمة">
        <div className="foods-search-row">
          <div className="foods-search-field">
            <Search size={19} aria-hidden="true" />
            <input
              ref={searchRef}
              dir={searchInput ? "auto" : "rtl"}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="ابحث باسم الطعام أو العلامة التجارية..."
              aria-label="بحث باسم الطعام أو العلامة التجارية"
            />
            {searchInput ? (
              <button type="button" className="search-clear" onClick={() => {
                setSearchInput("");
                searchRef.current?.focus();
              }} aria-label="مسح البحث">
                <X size={17} aria-hidden="true" />
              </button>
            ) : null}
          </div>

          <div className="foods-controls">
            <div className="foods-desktop-controls">
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

        {registryQuery.isError ? <div className="state-note" role="alert">
          تعذر تحميل التصنيفات.
          <button className="btn" type="button" onClick={() => registryQuery.refetch()} disabled={registryQuery.isFetching}>إعادة المحاولة</button>
        </div> : null}

        <div className="foods-result-bar">
          {data && !foodsQuery.isError ? (
            <>
              <span className="foods-result-count foods-result-count-range">
                عرض {data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1}-
                {Math.min(data.page * data.page_size, data.total)} من {data.total} طعامًا
              </span>
              {/* Mobile appends pages with «عرض المزيد», so it shows the running total once, at the top. */}
              <span className="foods-result-count foods-result-count-loaded">عرض {shownMobileCount} من {data.total} طعامًا</span>
            </>
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
          <div className={retainedPageError ? "catalog-state foods-desktop-error" : "catalog-state"} role="alert">
            <strong>تعذر تحميل الأطعمة</strong>
            <span>{FOODS_READ_ERROR}</span>
            <button className="btn" type="button" onClick={() => foodsQuery.refetch()}>
              <RotateCcw size={18} aria-hidden="true" />
              إعادة المحاولة
            </button>
          </div>
        ) : null}

        {!foodsQuery.isPending && !foodsQuery.isError && data?.total === 0 ? (
          <EmptyFoodsState
            hasSearch={Boolean(search)}
            categoryLabel={category ? categoryLabels.get(category) ?? category : undefined}
            onClear={clearFilters}
            onClearCategory={() => {
              resetCollection({ category: "" });
              searchRef.current?.focus();
            }}
          />
        ) : null}

        {(!foodsQuery.isError || retainedPageError) && (desktopFoods.length > 0 || mobileItems.length > 0) ? (
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
                    <th scope="col">الكربوهيدرات</th>
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
                      isAdmin={isAdmin}
                      categoryLabel={categoryLabels.get(food.primary_category) ?? "غير متوفر"}
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
                  isAdmin={isAdmin}
                  categoryLabel={categoryLabels.get(food.primary_category) ?? "غير متوفر"}
                />
              ))}
              {foodsQuery.isPending && page > 1 ? <div className="loading-more" role="status">جاري تحميل المزيد...</div> : null}
              {retainedPageError ? (
                <div className="catalog-state" role="alert">
                  <strong>تعذّر تحميل المزيد من الأطعمة.</strong>
                  <button className="btn" type="button" onClick={() => foodsQuery.refetch()} disabled={foodsQuery.isFetching}>
                    إعادة المحاولة
                  </button>
                </div>
              ) : null}
              {canLoadMore && !foodsQuery.isError ? (
                <button className="btn load-more" type="button" onClick={() => setPage((current) => current + 1)}>
                  عرض المزيد
                </button>
              ) : null}
            </div>

            {data && data.total_pages > 1 ? (
              <DesktopPagination page={data.page} totalPages={data.total_pages} onChange={setPage} />
            ) : null}
          </>
        ) : null}
      </section>

      {isAdmin ? <FoodDeleteDialog
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
