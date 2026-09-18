"use client";

import { ArrowRight, Pencil, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ApiError, getFood, getNutritionRegistry } from "@/lib/api";
import {
  DetailServingMetric,
  FoodDetailsLoading,
  MetadataRow,
  NutrientGroup,
  NutritionCompleteness,
  formatFoodDate,
  type NutritionMode,
} from "@/features/foods/food-details-view";
import { createFoodNutrientAdapter } from "@/features/foods/food-nutrients";
import {
  calculateServingNutrition,
  defaultServingText,
  defaultUnitText,
  formatServingCalories,
  formatServingMacro,
  nutritionBasisLabels,
  perBasisNutrition,
} from "@/lib/food";
import type { FoodResponse } from "@/lib/types";
import { definitionsFromRegistry } from "@/lib/nutrients";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { useFoodDelete } from "./useFoodDelete";
import { useAuth } from "./AuthProvider";

const FOOD_READ_ERROR = "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.";

export function FoodDetailsPage({ foodId }: { foodId: string }) {
  const router = useRouter();
  const [mode, setMode] = useState<NutritionMode>("serving");
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [note, setNote] = useState("");
  const [completenessOpen, setCompletenessOpen] = useState(false);
  const { account } = useAuth();
  const foodQuery = useQuery({
    queryKey: ["food", foodId],
    queryFn: () => getFood(foodId),
    enabled: account !== null
  });
  const registryQuery = useQuery({
    queryKey: ["nutrition-registry"],
    queryFn: getNutritionRegistry,
    staleTime: 300_000
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
  const registry = registryQuery.data;
  const servingNutrition = calculateServingNutrition(food);
  const basisNutrition = perBasisNutrition(food);
  const displayedNutrition = mode === "serving" ? servingNutrition : basisNutrition;
  const basisLabel = nutritionBasisLabels[food.nutrition_basis];
  const registryNutrients = registry ? definitionsFromRegistry(registry) : null;
  const nutrientGroups = createFoodNutrientAdapter(registry).groups;
  const category = registry?.food_taxonomy.find((item) => item.key === food.primary_category);
  const categoryLabel = category?.label_ar;
  const subcategoryLabel = category?.subcategories.find((item) => item.key === food.subcategory)?.label_ar;
  const nutritionSourceLabel = registry?.nutrition_data_sources.find(
    (item) => item.key === food.nutrition_data_source
  )?.label_ar;

  return (
    <>
      <header className="food-detail-header">
        <Link className="icon-button detail-back" href="/foods" aria-label="رجوع إلى الأطعمة">
          <ArrowRight size={21} aria-hidden="true" />
        </Link>
        <div className="food-detail-identity">
          <h1 className="food-detail-name" dir="auto">{food.name}</h1>
          <p className="food-detail-secondary" dir="auto">
            {[food.brand, categoryLabel || food.primary_category].filter(Boolean).join(" · ")}
          </p>
          <span className="serving-badge detail-serving-badge">{defaultServingText(food)}</span>
        </div>
        {account?.role === "admin" ? <div className="food-detail-actions">
          <Link className="btn primary" href={`/foods/${food.id}/edit`}>
            <Pencil size={18} aria-hidden="true" />
            تعديل
          </Link>
          <button className="btn danger" type="button" onClick={() => setDeleteTarget(food)}>
            <Trash2 size={18} aria-hidden="true" />
            حذف
          </button>
        </div> : null}
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

      {registryNutrients ? (
        <NutritionCompleteness food={food} nutrients={registryNutrients} open={completenessOpen} onToggle={() => setCompletenessOpen((value) => !value)} />
      ) : (
        <section className="catalog-state" role={registryQuery.isError ? "alert" : "status"}>
          <strong>{registryQuery.isError ? "تعذر تحميل البيانات الغذائية" : "جارٍ تحميل سجل المغذيات"}</strong>
          {registryQuery.isError ? <button className="btn" type="button" onClick={() => registryQuery.refetch()}><RotateCcw size={18} /> إعادة المحاولة</button> : null}
        </section>
      )}

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
            {nutrientGroups.map((group) => (
              <NutrientGroup
                key={group.title}
                title={group.title}
                nutrients={group.nutrients}
                values={displayedNutrition}
                mode={mode}
                optional={group.optional}
              />
            ))}
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
          <MetadataRow label="التصنيف الرئيسي" value={categoryLabel ?? food.primary_category} />
          <MetadataRow label="التصنيف الفرعي" value={subcategoryLabel ?? food.subcategory} />
          <MetadataRow label="أساس القيم" value={basisLabel} />
          <MetadataRow label="تعريف الوحدة الافتراضية" value={defaultUnitText(food)} />
          {food.notes ? <MetadataRow label="ملاحظات" value={food.notes} multiline autoDirection /> : null}
          <MetadataRow label="مصدر البيانات الغذائية" value={nutritionSourceLabel ?? food.nutrition_data_source} />
          {food.ingredients ? <MetadataRow label="المكونات" value={food.ingredients} multiline autoDirection /> : null}
          {food.legacy_nutrition.folate_mcg != null ? <MetadataRow label="فولات قديم" value={`${food.legacy_nutrition.folate_mcg} مكجم · ${food.legacy_nutrition.meaning_ar}`} /> : null}
          {food.legacy_nutrition.vitamin_a_mcg != null ? <MetadataRow label="فيتامين A قديم" value={`${food.legacy_nutrition.vitamin_a_mcg} مكجم · ${food.legacy_nutrition.meaning_ar}`} /> : null}
          <MetadataRow label="تاريخ الإنشاء" value={formatFoodDate(food.created_at)} />
          <MetadataRow label="آخر تحديث" value={formatFoodDate(food.updated_at)} />
        </dl>
      </section>

      {account?.role === "admin" ? <FoodDeleteDialog
        food={deleteTarget}
        pending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      /> : null}
    </>
  );
}
