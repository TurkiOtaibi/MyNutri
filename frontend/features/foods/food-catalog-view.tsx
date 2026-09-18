"use client";

import { ChevronLeft, ChevronRight, MoreVertical, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import {
  calculateServingNutrition,
  defaultServingText,
  formatServingCalories,
  formatServingMacro,
} from "@/lib/food";
import type { FoodResponse } from "@/lib/types";

interface FoodItemProps {
  food: FoodResponse;
  menuOpen: boolean;
  onMenuChange: (open: boolean) => void;
  onDelete: () => void;
  isAdmin: boolean;
  categoryLabel: string;
}

export function FoodTableRow({
  food,
  menuOpen,
  onMenuChange,
  onDelete,
  isAdmin,
  categoryLabel,
}: FoodItemProps) {
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
        {isAdmin ? <FoodActionsMenu food={food} open={menuOpen} onOpenChange={onMenuChange} onDelete={onDelete} /> : null}
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

export function FoodCard({
  food,
  menuOpen,
  onMenuChange,
  onDelete,
  isAdmin,
  categoryLabel,
}: FoodItemProps) {
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
        {isAdmin ? <FoodActionsMenu food={food} open={menuOpen} onOpenChange={onMenuChange} onDelete={onDelete} /> : null}
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
  onDelete,
}: {
  food: FoodResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete: () => void;
}) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const firstItemRef = useRef<HTMLAnchorElement | null>(null);

  useEffect(() => {
    if (open) firstItemRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
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
        <div className="food-actions-popover">
          <div className="food-actions-list" role="menu">
            <Link ref={firstItemRef} href={`/foods/${food.id}/edit`} role="menuitem" onClick={() => onOpenChange(false)}>
              <Pencil size={17} aria-hidden="true" />
              تعديل
            </Link>
            <button type="button" role="menuitem" className="danger-menu-item" onClick={onDelete}>
              <Trash2 size={17} aria-hidden="true" />
              حذف
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function DesktopPagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (page: number) => void }) {
  const pages = pageNumbers(page, totalPages);
  return (
    <nav className="foods-pagination" aria-label="صفحات الأطعمة">
      <button type="button" className="pagination-button" disabled={page === 1} onClick={() => onChange(page - 1)} aria-label="الصفحة السابقة">
        <ChevronRight size={18} aria-hidden="true" />
        السابق
      </button>
      <div className="pagination-pages">
        {pages.map((value, index) => value === "ellipsis" ? (
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
        ))}
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

export function FoodsLoading() {
  return (
    <div className="foods-loading" role="status" aria-live="polite">
      <span className="sr-only">جاري تحميل الأطعمة.</span>
      {Array.from({ length: 5 }, (_, index) => <span className="food-skeleton" key={index} />)}
    </div>
  );
}

export function EmptyFoodsState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
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
    </div>
  );
}
