"use client";

import { ArrowRight, ChevronDown, Pencil, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ApiError, getFood } from "@/lib/api";
import {
  calculateServingNutrition,
  defaultServingText,
  defaultUnitText,
  formatNutrientNumber,
  formatServingCalories,
  formatServingMacro,
  nutritionBasisLabels,
  perBasisNutrition,
  type FoodNutritionValues
} from "@/lib/food";
import type { FoodResponse } from "@/lib/types";
import { additionalNutrients, nutrientValue } from "@/lib/nutrients";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { useFoodDelete } from "./useFoodDelete";

const FOOD_READ_ERROR = "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.";

type NutritionMode = "serving" | "basis";
type NutrientSpec = {
  key: keyof FoodNutritionValues;
  label: string;
  unit: "سعرة" | "جم" | "ملجم" | "مكجم";
};

const coreNutrients: NutrientSpec[] = [
  { key: "calories", label: "السعرات", unit: "سعرة" },
  { key: "protein_g", label: "البروتين", unit: "جم" },
  { key: "carb_g", label: "الكربوهيدرات", unit: "جم" },
  { key: "fat_g", label: "الدهون", unit: "جم" },
  { key: "fiber_g", label: "الألياف", unit: "جم" },
  { key: "net_carbs_g", label: "صافي الكارب", unit: "جم" }
];

const sugarFatNutrients: NutrientSpec[] = [
  { key: "sugar_g", label: "إجمالي السكر", unit: "جم" },
  { key: "added_sugar_g", label: "السكر المضاف", unit: "جم" },
  { key: "saturated_fat_g", label: "الدهون المشبعة", unit: "جم" },
  { key: "trans_fat_g", label: "الدهون المتحولة", unit: "جم" },
  { key: "cholesterol_mg", label: "الكوليسترول", unit: "ملجم" }
];

const mineralNutrients: NutrientSpec[] = [
  { key: "sodium_mg", label: "الصوديوم", unit: "ملجم" },
  { key: "potassium_mg", label: "البوتاسيوم", unit: "ملجم" },
  { key: "calcium_mg", label: "الكالسيوم", unit: "ملجم" },
  { key: "iron_mg", label: "الحديد", unit: "ملجم" },
  { key: "magnesium_mg", label: "المغنيسيوم", unit: "ملجم" },
  { key: "zinc_mg", label: "الزنك", unit: "ملجم" }
];

const vitaminNutrients: NutrientSpec[] = [
  { key: "vitamin_d_mcg", label: "فيتامين D", unit: "مكجم" },
  { key: "vitamin_b12_mcg", label: "فيتامين B12", unit: "مكجم" },
  { key: "vitamin_c_mg", label: "فيتامين C", unit: "ملجم" },
  { key: "vitamin_a_mcg", label: "فيتامين A", unit: "مكجم" },
  { key: "folate_mcg", label: "الفولات", unit: "مكجم" },
  { key: "vitamin_k_mcg", label: "فيتامين K", unit: "مكجم" }
];

export function FoodDetailsPage({ foodId }: { foodId: string }) {
  const router = useRouter();
  const [mode, setMode] = useState<NutritionMode>("serving");
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [note, setNote] = useState("");
  const [completenessOpen, setCompletenessOpen] = useState(false);
  const foodQuery = useQuery({
    queryKey: ["food", foodId],
    queryFn: () => getFood(foodId)
  });

  const deleteMutation = useFoodDelete({
    onDeleted: () => router.push("/foods"),
    onError: (message) => setNote(message)
  });

  if (foodQuery.isPending) return <FoodDetailsLoading />;

  if (foodQuery.isError || !foodQuery.data) {
    const notFound = foodQuery.error instanceof ApiError && foodQuery.error.status === 404;
    return (
      <section className="catalog-state food-detail-error" role="alert">
        <strong>{notFound ? "الطعام غير موجود" : "تعذر تحميل تفاصيل الطعام"}</strong>
        <span>{notFound ? "قد يكون الطعام حُذف. ارجع إلى القائمة وحدّث النتائج." : FOOD_READ_ERROR}</span>
        <div className="actions">
          {!notFound ? (
            <button className="btn" type="button" onClick={() => foodQuery.refetch()}>
              <RotateCcw size={18} aria-hidden="true" />
              إعادة المحاولة
            </button>
          ) : null}
          <Link className="btn" href="/foods">
            <ArrowRight size={18} aria-hidden="true" />
            رجوع إلى الأطعمة
          </Link>
        </div>
      </section>
    );
  }

  const food = foodQuery.data;
  const servingNutrition = calculateServingNutrition(food);
  const basisNutrition = perBasisNutrition(food);
  const displayedNutrition = mode === "serving" ? servingNutrition : basisNutrition;
  const basisLabel = nutritionBasisLabels[food.nutrition_basis];

  return (
    <>
      <header className="food-detail-header">
        <Link className="icon-button detail-back" href="/foods" aria-label="رجوع إلى الأطعمة">
          <ArrowRight size={21} aria-hidden="true" />
        </Link>
        <div className="food-detail-identity">
          <h1 className="food-detail-name" dir="auto">{food.name}</h1>
          <p className="food-detail-secondary" dir="auto">
            {[food.brand, food.category || "غير مصنف"].filter(Boolean).join(" · ")}
          </p>
          <span className="serving-badge detail-serving-badge">{defaultServingText(food)}</span>
        </div>
        <div className="food-detail-actions">
          <Link className="btn primary" href={`/foods/${food.id}/edit`}>
            <Pencil size={18} aria-hidden="true" />
            تعديل
          </Link>
          <button className="btn danger" type="button" onClick={() => setDeleteTarget(food)}>
            <Trash2 size={18} aria-hidden="true" />
            حذف
          </button>
        </div>
      </header>

      {note ? <div className="catalog-notice" role="alert">{note}</div> : null}

      <section className="serving-summary" aria-labelledby="serving-summary-title">
        <div className="detail-section-heading">
          <div>
            <p className="section-eyebrow">الحصة الافتراضية</p>
            <h2 id="serving-summary-title">{defaultServingText(food)}</h2>
          </div>
          <span className="basis-reference">القيم محسوبة من بيانات {basisLabel}</span>
        </div>
        {servingNutrition ? (
          <div className="detail-serving-grid">
            <DetailServingMetric value={formatServingCalories(servingNutrition.calories)} label="سعرة" prominent />
            <DetailServingMetric value={formatServingMacro(servingNutrition.protein_g)} label="بروتين" />
            <DetailServingMetric value={formatServingMacro(servingNutrition.carb_g)} label="كارب" />
            <DetailServingMetric value={formatServingMacro(servingNutrition.fat_g)} label="دهون" />
          </div>
        ) : (
          <p className="nutrition-unavailable">تعذر حساب القيم الغذائية للحصة الافتراضية.</p>
        )}
      </section>

      <NutritionCompleteness food={food} open={completenessOpen} onToggle={() => setCompletenessOpen((value) => !value)} />

      {displayedNutrition ? <AdditionalFoodNutrients values={displayedNutrition} /> : null}

      <section className="nutrition-details-surface" aria-labelledby="nutrition-details-title">
        <div className="nutrition-details-toolbar">
          <div>
            <p className="section-eyebrow">البيانات الغذائية الكاملة</p>
            <h2 id="nutrition-details-title">تفاصيل القيم الغذائية</h2>
          </div>
          <div className="nutrition-mode-control" role="group" aria-label="طريقة عرض القيم الغذائية">
            <button type="button" className={mode === "serving" ? "active" : ""} aria-pressed={mode === "serving"} onClick={() => setMode("serving")}>
              الحصة الافتراضية
            </button>
            <button type="button" className={mode === "basis" ? "active" : ""} aria-pressed={mode === "basis"} onClick={() => setMode("basis")}>
              {basisLabel}
            </button>
          </div>
        </div>

        {displayedNutrition ? (
          <div className="nutrition-groups">
            <NutrientGroup title="القيم الأساسية" nutrients={coreNutrients} values={displayedNutrition} mode={mode} />
            <NutrientGroup title="السكريات والدهون" nutrients={sugarFatNutrients} values={displayedNutrition} mode={mode} optional />
            <NutrientGroup title="المعادن" nutrients={mineralNutrients} values={displayedNutrition} mode={mode} optional />
            <NutrientGroup title="الفيتامينات" nutrients={vitaminNutrients} values={displayedNutrition} mode={mode} optional />
          </div>
        ) : (
          <p className="nutrition-unavailable">القيم غير متوفرة لهذا العرض.</p>
        )}
      </section>

      <section className="food-metadata" aria-labelledby="food-metadata-title">
        <div className="detail-section-heading">
          <div>
            <p className="section-eyebrow">معلومات الطعام</p>
            <h2 id="food-metadata-title">المصدر والتعريف</h2>
          </div>
        </div>
        <dl className="metadata-rows">
          {food.brand ? <MetadataRow label="العلامة التجارية" value={food.brand} autoDirection /> : null}
          {food.category ? <MetadataRow label="التصنيف" value={food.category} autoDirection /> : null}
          <MetadataRow label="أساس القيم" value={basisLabel} />
          <MetadataRow label="تعريف الوحدة الافتراضية" value={defaultUnitText(food)} />
          {food.notes ? <MetadataRow label="ملاحظات" value={food.notes} multiline autoDirection /> : null}
          {food.data_source ? <MetadataRow label="مصدر البيانات" value={food.data_source} multiline autoDirection /> : null}
          <MetadataRow label="تاريخ الإنشاء" value={formatDate(food.created_at)} />
          <MetadataRow label="آخر تحديث" value={formatDate(food.updated_at)} />
        </dl>
      </section>

      <FoodDeleteDialog
        food={deleteTarget}
        pending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </>
  );
}

function DetailServingMetric({ value, label, prominent = false }: { value: string; label: string; prominent?: boolean }) {
  return (
    <div className={`detail-serving-metric ${prominent ? "prominent" : ""}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function NutritionCompleteness({ food, open, onToggle }: { food: FoodResponse; open: boolean; onToggle: () => void }) {
  const coreKeys = ["calories", "protein_g", "carb_g", "fat_g"] as const;
  const coreAvailable = coreKeys.filter((key) => food[key] != null).length;
  const tracked = additionalNutrients.filter((item) => item.foodCompleteness);
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

function AdditionalFoodNutrients({ values }: { values: FoodNutritionValues }) {
  return (
    <section className="food-additional-nutrients" aria-labelledby="food-additional-title">
      <h2 id="food-additional-title">المغذيات الإضافية</h2>
      <dl>{additionalNutrients.map((item) => {
        const raw = values[item.key];
        const value = typeof raw === "number" ? raw : null;
        const percentage = value != null && item.targetValue ? Math.round(value / item.targetValue * 100) : null;
        return <div key={item.key}><dt>{item.label}</dt><dd>{value == null ? <span>غير متوفر</span> : <><bdi dir="ltr">{formatNutrientNumber(value)} {item.unit}</bdi>{percentage != null ? <small>{percentage}% من هدفك اليومي</small> : null}</>}</dd></div>;
      })}</dl>
    </section>
  );
}

function NutrientGroup({
  title,
  nutrients,
  values,
  mode,
  optional = false
}: {
  title: string;
  nutrients: NutrientSpec[];
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
            ? formatNutrientNumber(value)
            : nutrient.key === "calories"
              ? formatServingCalories(value)
              : nutrient.key === "protein_g" || nutrient.key === "carb_g" || nutrient.key === "fat_g"
                ? formatServingMacro(value)
                : formatNutrientNumber(value);
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

function MetadataRow({ label, value, multiline = false, autoDirection = false }: { label: string; value: string; multiline?: boolean; autoDirection?: boolean }) {
  return (
    <div className={`metadata-row ${multiline ? "multiline" : ""}`}>
      <dt>{label}</dt>
      <dd dir={autoDirection ? "auto" : undefined}>{value}</dd>
    </div>
  );
}

function FoodDetailsLoading() {
  return (
    <div className="detail-loading" role="status" aria-live="polite">
      <span className="sr-only">جاري تحميل تفاصيل الطعام.</span>
      <span className="detail-skeleton title" />
      <span className="detail-skeleton hero" />
      <span className="detail-skeleton body" />
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ar-SA-u-nu-latn", { dateStyle: "medium" }).format(new Date(value));
}
