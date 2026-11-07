"use client";

import { ChevronLeft, ChevronRight, MoreVertical, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef } from "react";

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
  const id = useId();
  return (
    <tr>
      <td>
        <Link className="food-table-name" href={`/foods/${food.id}`} dir="auto" aria-label={`عرض تفاصيل ${food.name}`} aria-describedby={food.brand ? `${id}-brand ${id}-serving` : `${id}-serving`}>
          {food.name}
        </Link>
        {food.brand ? <span className="food-table-brand" id={`${id}-brand`}><bdi dir="auto">{food.brand}</bdi></span> : null}
      </td>
      <td>{categoryLabel}</td>
      <td><span className="serving-label" id={`${id}-serving`}>{defaultServingText(food)}</span></td>
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
  const id = useId();
  return (
    <article className="food-card">
      <Link className="food-card-overlay" href={`/foods/${food.id}`} aria-label={`عرض تفاصيل ${food.name}`} aria-describedby={`${id}-identity ${id}-serving`} />
      <div className="food-card-heading">
        <div>
          {/* Lines stay right-aligned (RTL); only the names are isolated so Latin text keeps its own order. */}
          <h2 className="food-card-title" title={food.name}><bdi dir="auto">{food.name}</bdi></h2>
          <p className="food-card-secondary" id={`${id}-identity`}>{food.brand ? <><bdi dir="auto">{food.brand}</bdi>{categoryLabel ? " · " : null}</> : null}{categoryLabel}</p>
        </div>
        {isAdmin ? <FoodActionsMenu food={food} open={menuOpen} onOpenChange={onMenuChange} onDelete={onDelete} /> : null}
      </div>
      <span className="serving-badge" id={`${id}-serving`}>{defaultServingText(food)}</span>
      {nutrition ? (
        <div className="serving-macro-grid" aria-label="القيم الغذائية للحصة الافتراضية">
          <ServingMetric value={formatServingCalories(nutrition.calories)} label="سعرة" />
          <ServingMetric value={formatServingMacro(nutrition.protein_g)} label="بروتين" unit="جم" />
          <ServingMetric value={formatServingMacro(nutrition.carb_g)} label="كربوهيدرات" unit="جم" />
          <ServingMetric value={formatServingMacro(nutrition.fat_g)} label="دهون" unit="جم" />
        </div>
      ) : (
        <span className="nutrition-unavailable">تعذر حساب قيم الحصة</span>
      )}
    </article>
  );
}

function ServingMetric({ value, label, unit }: { value: string; label: string; unit?: string }) {
  return (
    <span className="serving-metric">
      <strong><bdi dir="ltr">{value}</bdi>{unit && <span className="serving-unit"> {unit}</span>}</strong>
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
  const openAtEnd = useRef(false);
  const menuId = useId();

  useEffect(() => {
    if (open) {
      const last = rootRef.current?.querySelector<HTMLElement>('[role="menuitem"]:last-child');
      (openAtEnd.current ? last : firstItemRef.current)?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) onOpenChange(false);
    };
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
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
    <div className="food-actions-menu" ref={rootRef} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) onOpenChange(false);
    }}>
      <button
        ref={buttonRef}
        className="icon-button"
        type="button"
        aria-label={`إجراءات ${food.name}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => { openAtEnd.current = false; onOpenChange(!open); }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            openAtEnd.current = event.key === "ArrowUp";
            onOpenChange(true);
          }
        }}
      >
        <MoreVertical size={20} aria-hidden="true" />
      </button>
      {open ? (
        <div className="food-actions-popover">
          <div id={menuId} className="food-actions-list" role="menu" aria-label={`إجراءات ${food.name}`} onKeyDown={(event) => {
            const items = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitem"]'));
            const index = items.indexOf(document.activeElement as HTMLElement);
            const next = event.key === "ArrowDown" ? (index + 1) % items.length
              : event.key === "ArrowUp" ? (index - 1 + items.length) % items.length
              : event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : null;
            if (next !== null) { event.preventDefault(); items[next]?.focus(); }
            if (event.key === "Tab") { onOpenChange(false); buttonRef.current?.focus(); }
          }}>
            <Link ref={firstItemRef} href={`/foods/${food.id}/edit`} role="menuitem" tabIndex={-1} onClick={() => onOpenChange(false)}>
              <Pencil size={17} aria-hidden="true" />
              تعديل
            </Link>
            <button type="button" role="menuitem" tabIndex={-1} className="danger-menu-item" onClick={() => {
              buttonRef.current?.focus();
              onOpenChange(false);
              onDelete();
            }}>
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

export function EmptyFoodsState({ hasSearch, categoryLabel, onClear, onClearCategory }: {
  hasSearch: boolean;
  categoryLabel?: string;
  onClear: () => void;
  onClearCategory: () => void;
}) {
  if (hasSearch || categoryLabel) {
    return (
      <div className="catalog-state">
        {categoryLabel && <span>التصنيف الحالي: <bdi>{categoryLabel}</bdi></span>}
        <strong>{hasSearch ? "لا توجد نتائج مطابقة للبحث." : "لا توجد أطعمة ضمن هذا التصنيف."}</strong>
        {hasSearch && <span>جرّب اسمًا آخر أو امسح عوامل التصفية.</span>}
        {categoryLabel && <button className="btn" type="button" onClick={onClearCategory}>عرض كل التصنيفات</button>}
        {hasSearch && <button className="btn" type="button" onClick={onClear}>مسح البحث والتصفية</button>}
      </div>
    );
  }
  return (
    <div className="catalog-state">
      <strong>لا توجد أطعمة بعد.</strong>
    </div>
  );
}
