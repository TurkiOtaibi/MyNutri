"use client";

import { ChevronDown } from "lucide-react";

import type { FoodNutrientSpec } from "@/features/foods/food-nutrients";
import {
  formatNutrientNumber,
  formatServingCalories,
  formatServingMacro,
  type FoodNutritionValues,
} from "@/lib/food";
import { nutrientValue, type NutrientDefinition } from "@/lib/nutrients";
import type { FoodResponse } from "@/lib/types";

export type NutritionMode = "serving" | "basis";

export function DetailServingMetric({ value, label, prominent = false }: { value: string; label: string; prominent?: boolean }) {
  return (
    <div className={`detail-serving-metric ${prominent ? "prominent" : ""}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export function NutritionCompleteness({ food, nutrients, open, onToggle }: { food: FoodResponse; nutrients: NutrientDefinition[]; open: boolean; onToggle: () => void }) {
  const coreKeys = ["calories", "protein_g", "carb_g", "fat_g"] as const;
  const coreAvailable = coreKeys.filter((key) => food[key] != null).length;
  const tracked = nutrients.filter((item) => item.foodCompleteness);
  const available = tracked.filter((item) => nutrientValue(food, item.key) !== null);
  const totalAvailable = coreAvailable + available.length;
  const totalFields = coreKeys.length + tracked.length;
  const overall = Math.round(totalAvailable / totalFields * 100);
  const corePercent = Math.round(coreAvailable / coreKeys.length * 100);
  const additionalPercent = Math.round(available.length / tracked.length * 100);
  const status = overall >= 90 ? "مكتملة جدًا" : overall >= 75 ? "جيدة" : overall >= 50 ? "جزئية" : "محدودة";
  const missing = tracked.filter((item) => nutrientValue(food, item.key) === null);
  return (
    <section className="food-completeness" aria-labelledby="food-completeness-title">
      <header>
        <div><h2 id="food-completeness-title">اكتمال البيانات الغذائية</h2><strong>{overall}% · {status}</strong></div>
        <span>{totalAvailable} من {totalFields} قيمة غذائية متوفرة</span>
      </header>
      <div className="food-completeness-bar" role="progressbar" aria-label={`اكتمال البيانات الغذائية لهذا الطعام: ${overall}%، ${totalAvailable} من ${totalFields} قيمة متوفرة`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={overall}><span style={{ width: `${overall}%` }} /></div>
      <div className="food-completeness-breakdown"><span>البيانات الأساسية <bdi>{corePercent}%</bdi></span><span>المغذيات الإضافية <bdi>{additionalPercent}%</bdi></span></div>
      <button type="button" className="food-completeness-toggle" aria-expanded={open} onClick={onToggle}>عرض التفاصيل <ChevronDown size={18} aria-hidden="true" /></button>
      {open ? <div className="food-completeness-missing"><h3>القيم غير المتوفرة</h3>{missing.length ? <ul>{missing.map((item) => <li key={item.key}>{item.label}</li>)}</ul> : <p>جميع القيم المتتبعة متوفرة.</p>}</div> : null}
    </section>
  );
}

export function NutrientGroup({
  title,
  nutrients,
  values,
  mode,
  optional = false,
}: {
  title: string;
  nutrients: FoodNutrientSpec[];
  values: FoodNutritionValues;
  mode: NutritionMode;
  optional?: boolean;
}) {
  const available = nutrients.filter((nutrient) => values[nutrient.key] != null);
  if (optional && available.length === 0) return null;
  return (
    <section className="nutrition-group">
      <h3>{title}</h3>
      <dl className="nutrition-rows">
        {available.map((nutrient) => {
          const value = values[nutrient.key];
          if (value == null) return null;
          const formatted = mode === "basis"
            ? formatNutrientNumber(value, nutrient.precision)
            : nutrient.key === "calories"
              ? formatServingCalories(value)
              : nutrient.key === "protein_g" || nutrient.key === "carb_g" || nutrient.key === "fat_g"
                ? formatServingMacro(value)
                : formatNutrientNumber(value, nutrient.precision);
          return (
            <div className="nutrition-row" key={nutrient.key}>
              <dt>{nutrient.label}</dt>
              <dd><bdi dir="ltr">{formatted} {nutrient.unit}</bdi></dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

export function MetadataRow({ label, value, multiline = false, autoDirection = false }: { label: string; value: string; multiline?: boolean; autoDirection?: boolean }) {
  return (
    <div className={`metadata-row ${multiline ? "multiline" : ""}`}>
      <dt>{label}</dt>
      <dd dir={autoDirection ? "auto" : undefined}>{value}</dd>
    </div>
  );
}

export function FoodDetailsLoading() {
  return (
    <div className="detail-loading" role="status" aria-live="polite">
      <span className="sr-only">جاري تحميل تفاصيل الطعام.</span>
      <span className="detail-skeleton title" />
      <span className="detail-skeleton hero" />
      <span className="detail-skeleton body" />
    </div>
  );
}

export function formatFoodDate(value: string): string {
  return new Intl.DateTimeFormat("ar-SA-u-nu-latn", { dateStyle: "medium" }).format(new Date(value));
}
