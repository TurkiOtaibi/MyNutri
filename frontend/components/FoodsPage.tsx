"use client";

import { Plus, RotateCcw, Search, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

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
  const isAdmin = account?.role === "admin";
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<FoodSort>("name");
  const [page, setPage] = useState(1);
  const [mobileItems, setMobileItems] = useState<FoodResponse[]>([]);
  const [knownCategories, setKnownCategories] = useState<string[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [note, setNote] = useState("");

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
    if (!data) return;
    // The paged query is the external source for the accumulated mobile collection.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setKnownCategories(data.categories);
    setMobileItems((current) => {
      if (data.page === 1) return data.items;
      const ids = new Set(current.map((food) => food.id));
      return [...current, ...data.items.filter((food) => !ids.has(food.id))];
    });
    if (data.total_pages > 0 && page > data.total_pages) setPage(data.total_pages);
  }, [foodsQuery.dataUpdatedAt]);

  const deleteMutation = useFoodDelete({
    onDeleted: () => {
      setDeleteTarget(null);
      setOpenMenuId(null);
      setNote("تم حذف الطعام نهائيًا.");
    },
    onError: setNote
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
        label: registryQuery.data?.food_taxonomy.find((item) => item.key === value)?.label_ar ?? value
      })),
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
  }

  return (
    <>
      <div className="foods-page-head">
        <div>
          <h1 className="page-title">الأطعمة</h1>
          <p className="page-kicker">ابحث بسرعة واعرض القيم الغذائية حسب الحصة التي تستخدمها يوميًا.</p>
        </div>
        {isAdmin ? (
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
                      isAdmin={isAdmin}
                      categoryLabel={categoryLabels.get(food.primary_category) ?? food.primary_category}
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
                  categoryLabel={categoryLabels.get(food.primary_category) ?? food.primary_category}
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
