"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFood, getAdminFood, getNutritionRegistry, updateFood } from "@/lib/api";
import {
  defaultUnitLabels,
  defaultUnitOptions,
  emptyFoodForm,
  foodToForm,
  foodTextMax,
  hasFoodErrors,
  normalizeFoodForm,
  nutritionBasisLabels,
  unitBasisLabels,
  validateFoodForm,
  type FoodFormErrors,
  type FoodFormValues
} from "@/lib/food";
import type { FoodResponse, NovaClassification } from "@/lib/types";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { FoodFormActions, FoodGroupFields, FormSection, NumberField, SelectField, TextAreaField, TextField } from "@/features/foods/food-form-fields";
import { mapFoodApiError, optionalFields } from "@/features/foods/food-form-model";
import "@/features/foods/food-form.module.css";
import { useFoodDelete } from "./useFoodDelete";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { useUnsavedChanges } from "./UnsavedChangesProvider";

const FOOD_READ_ERROR = "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.";
const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";
const VALIDATION_ERROR = "راجع الحقول المحددة ثم حاول مرة أخرى.";

export function FoodFormPage({ mode, foodId }: { mode: "create" | "edit"; foodId?: string }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FoodFormValues>(emptyFoodForm);
  const [errors, setErrors] = useState<FoodFormErrors>({});
  const [note, setNote] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [hydratedFoodId, setHydratedFoodId] = useState<string | null>(null);
  const [pendingServerFood, setPendingServerFood] = useState<FoodResponse | null>(null);
  const [initialForm, setInitialForm] = useState(JSON.stringify(emptyFoodForm));
  const isEdit = mode === "edit";
  const { account, session, loading: authLoading } = useAuth();
  const accessToken = session?.access_token;
  const subjectId = session?.user.id ?? null;
  const formSubjectRef = useRef(subjectId);
  const sessionSignal = useSessionAbortSignal();
  const dirty = JSON.stringify(form) !== initialForm;

  const foodQuery = useQuery({
    queryKey: ["food", foodId],
    queryFn: () => getAdminFood(foodId ?? ""),
    enabled: isEdit && Boolean(foodId) && account?.role === "admin"
  });
  const registryQuery = useQuery({
    queryKey: ["nutrition-registry"],
    queryFn: getNutritionRegistry,
    staleTime: 300_000
  });

  useEffect(() => {
    if (foodQuery.data) {
      const loaded = foodToForm(foodQuery.data);
      if (dirty && hydratedFoodId === foodQuery.data.id) {
        // Preserve an in-progress form when a newer server response arrives.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        if (JSON.stringify(loaded) !== initialForm) setPendingServerFood(foodQuery.data);
        return;
      }
      if (dirty) {
        setPendingServerFood(foodQuery.data);
        return;
      }
      setForm(loaded);
      setInitialForm(JSON.stringify(loaded));
      setHydratedFoodId(foodQuery.data.id);
      setPendingServerFood(null);
    }
    // Dirty state is intentionally observed at response time so a refetch cannot
    // replace a user's in-progress values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [foodQuery.data]);

  useLayoutEffect(() => {
    if (formSubjectRef.current === subjectId) return;
    formSubjectRef.current = subjectId;
    setForm(emptyFoodForm);
    setInitialForm(JSON.stringify(emptyFoodForm));
    setHydratedFoodId(null);
    setPendingServerFood(null);
    setErrors({});
    setNote("");
  }, [subjectId]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = normalizeFoodForm(form);
      if (isEdit && foodId) return updateFood(foodId, payload, accessToken, sessionSignal);
      return createFood(payload, accessToken, sessionSignal);
    },
    onSuccess: async (food) => {
      if (sessionSignal.aborted) return;
      const saved = foodToForm(food);
      setInitialForm(JSON.stringify(saved));
      setForm(saved);
      setPendingServerFood(null);
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
      if (sessionSignal.aborted) return;
      await queryClient.invalidateQueries({ queryKey: ["food", food.id] });
      if (sessionSignal.aborted) return;
      completeAndNavigate(`/foods/${food.id}`);
    },
    onError: (error) => {
      if (sessionSignal.aborted) return;
      const apiErrors = mapFoodApiError(error);
      if (hasFoodErrors(apiErrors)) {
        setErrors(apiErrors);
        setNote(VALIDATION_ERROR);
      } else {
        setNote(WRITE_ERROR);
      }
    }
  });

  const deleteMutation = useFoodDelete({
    onDeleted: () => {
      if (!sessionSignal.aborted) {
        setInitialForm(JSON.stringify(form));
        completeAndNavigate("/foods");
      }
    },
    onError: (message) => {
      if (!sessionSignal.aborted) setNote(message);
    }
  });

  const { completeAndNavigate, requestDiscard } = useUnsavedChanges({
    identity: `food:${mode}:${foodId ?? "new"}`,
    dirty,
    enabled: !saveMutation.isPending && !deleteMutation.isPending,
    discard: () => {
      setInitialForm(JSON.stringify(form));
      setPendingServerFood(null);
    }
  });

  const optionalHasErrors = useMemo(() => optionalFields.some((field) => errors[field]), [errors]);

  function update<K extends keyof FoodFormValues>(key: K, value: FoodFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[key];
      delete next.form;
      return next;
    });
  }

  function updateFoodCategory(value: string) {
    setForm((current) => ({
      ...current,
      food_category_key: value,
      grain_type: ["baked_goods", "grains_starches"].includes(value) ? current.grain_type ?? "unknown" : null,
      baked_good_type: value === "baked_goods" ? current.baked_good_type : null,
      grain_starch_type: value === "grains_starches" ? current.grain_starch_type : null
    }));
    setErrors((current) => {
      const next = { ...current };
      delete next.food_category_key;
      delete next.baked_good_type;
      delete next.grain_starch_type;
      delete next.grain_type;
      delete next.form;
      return next;
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saveMutation.isPending || !registryQuery.data || registryQuery.data.registry_schema_version !== 2) return;
    const nextErrors = validateFoodForm(form);
    setErrors(nextErrors);
    if (hasFoodErrors(nextErrors)) {
      setNote(VALIDATION_ERROR);
      window.requestAnimationFrame(() => {
        document.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
      });
      return;
    }
    setNote("");
    saveMutation.mutate();
  }

  if (authLoading) return <div className="state-note">جارٍ التحقق من الصلاحية...</div>;
  if (account?.role !== "admin") {
    return <div className="state-note" role="alert">إدارة الأطعمة متاحة للمشرف فقط.</div>;
  }

  if (isEdit && (foodQuery.isPending || (foodQuery.data && hydratedFoodId !== foodQuery.data.id && !dirty))) {
    return <div className="state-note">جاري تحميل تفاصيل الطعام.</div>;
  }

  if (isEdit && foodQuery.isError) {
    return (
      <section className="section-panel">
        <div className="state-note" role="alert">
          {FOOD_READ_ERROR}
        </div>
        <div className="actions">
          <Link className="btn" href="/foods">
            <ArrowRight size={18} />
            رجوع
          </Link>
        </div>
      </section>
    );
  }

  if (registryQuery.isPending) {
    return <div className="state-note" role="status">جاري تحميل سجل التغذية.</div>;
  }

  if (registryQuery.isError) {
    return (
      <section className="section-panel">
        <div className="state-note" role="alert">تعذر تحميل البيانات الغذائية. لا يمكن حفظ بيانات طعام دون السجل المعتمد.</div>
        <div className="actions">
          <button className="btn" type="button" onClick={() => registryQuery.refetch()}>إعادة المحاولة</button>
          <Link className="btn" href="/foods"><ArrowRight size={18} />رجوع</Link>
        </div>
      </section>
    );
  }

  if (registryQuery.data.registry_schema_version !== 2) {
    return (
      <section className="section-panel">
        <div className="state-note" role="alert">إصدار سجل التغذية غير متوافق. يلزم تحديث التطبيق أو التواصل مع الدعم قبل حفظ الطعام.</div>
        <div className="actions">
          <button className="btn" type="button" onClick={() => registryQuery.refetch()}>إعادة المحاولة</button>
          <Link className="btn" href="/foods"><ArrowRight size={18} />رجوع</Link>
        </div>
      </section>
    );
  }

  const registry = registryQuery.data;
  const selectedSource = registry.source_types.find((item) => item.type === form.nutrition_source.type);
  const reliabilityLabel = registry.reliability_levels.find((item) => item.key === selectedSource?.reliability)?.label_ar ?? "غير معروفة";

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">{isEdit ? "تعديل الطعام" : "إضافة طعام"}</h1>
          <p className="page-kicker">القيم الغذائية تحفظ لكل 100 جم أو 100 مل، والوحدة الافتراضية تستخدم للتسجيل اليومي.</p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn" href={isEdit && foodId ? `/foods/${foodId}` : "/foods"}>
            <ArrowRight size={18} />
            رجوع
          </Link>
        </div>
      </div>

      <form className="food-form-layout" onSubmit={submit} noValidate>
        {pendingServerFood ? (
          <div className="unsaved-conflict" role="status">
            <p>توجد نسخة أحدث من هذا الطعام على الخادم. احتفظنا بتعديلاتك الحالية.</p>
            <div className="actions">
              <button className="btn" type="button" onClick={() => setPendingServerFood(null)}>الاحتفاظ بتعديلاتي</button>
              <button className="btn danger" type="button" onClick={() => requestDiscard(() => {
                const loaded = foodToForm(pendingServerFood);
                setForm(loaded);
                setInitialForm(JSON.stringify(loaded));
                setHydratedFoodId(pendingServerFood.id);
                setPendingServerFood(null);
              })}>تحميل نسخة الخادم</button>
            </div>
          </div>
        ) : null}
        {note ? (
          <div className="state-note" role={hasFoodErrors(errors) ? "alert" : "status"} aria-live="polite">
            {note}
          </div>
        ) : null}

        <FormSection title="معلومات الطعام الأساسية">
          <TextField label="اسم الطعام" value={form.name} required maxLength={foodTextMax.name} error={errors.name} onChange={(value) => update("name", value)} />
          <TextField label="العلامة التجارية" value={form.brand ?? ""} maxLength={foodTextMax.brand} error={errors.brand} onChange={(value) => update("brand", value)} />
          <SelectField
            label="فئة الطعام"
            value={form.food_category_key}
            required
            error={errors.food_category_key}
            onChange={updateFoodCategory}
            options={registry.food_category_definitions.map((item) => [item.key, item.label_ar])}
          />
          {form.food_category_key === "baked_goods" ? (
            <SelectField label="نوع المخبوزات" value={form.baked_good_type ?? ""} placeholder="اختر نوع المخبوزات" required error={errors.baked_good_type} onChange={(value) => update("baked_good_type", value as FoodFormValues["baked_good_type"])} options={registry.baked_good_type_definitions.map((item) => [item.key, item.label_ar])} />
          ) : null}
          {form.food_category_key === "grains_starches" ? (
            <SelectField label="نوع الحبوب أو النشويات" value={form.grain_starch_type ?? ""} placeholder="اختر نوع الحبوب أو النشويات" required error={errors.grain_starch_type} onChange={(value) => update("grain_starch_type", value as FoodFormValues["grain_starch_type"])} options={registry.grain_starch_type_definitions.map((item) => [item.key, item.label_ar])} />
          ) : null}
          {["baked_goods", "grains_starches"].includes(form.food_category_key) ? (
            <SelectField label="نوع الحبوب" value={form.grain_type ?? "unknown"} required error={errors.grain_type} onChange={(value) => update("grain_type", value as FoodFormValues["grain_type"])} options={registry.grain_type_definitions.map((item) => [item.key, item.label_ar])} />
          ) : null}
          <SelectField
            label="نوع الطعام"
            value={form.food_kind}
            required
            error={errors.food_kind}
            onChange={(value) => update("food_kind", value as FoodFormValues["food_kind"])}
            options={[
              ["simple", "بسيط"],
              ["composite", "مركب"],
              ...(form.food_kind === "unknown" ? [["unknown", "قديم غير مصنف"] as [string, string]] : [])
            ]}
          />
        </FormSection>

        <FormSection title="أساس القيم الغذائية">
          <SelectField
            label="أساس القيم"
            value={form.nutrition_basis}
            required
            error={errors.nutrition_basis}
            onChange={(value) => update("nutrition_basis", value as FoodFormValues["nutrition_basis"])}
            options={Object.entries(nutritionBasisLabels)}
          />
        </FormSection>

        <FormSection title="القيم الغذائية الأساسية">
          <NumberField label="السعرات" value={form.calories} required error={errors.calories} onChange={(value) => update("calories", value)} />
          <NumberField label="البروتين g" value={form.protein_g} required error={errors.protein_g} onChange={(value) => update("protein_g", value)} />
          <NumberField label="الكارب g" value={form.carb_g} required error={errors.carb_g} onChange={(value) => update("carb_g", value)} />
          <NumberField label="الدهون g" value={form.fat_g} required error={errors.fat_g} onChange={(value) => update("fat_g", value)} />
        </FormSection>

        <FormSection title="الوحدة الافتراضية">
          <SelectField
            label="الوحدة الافتراضية"
            value={form.default_unit_type}
            required
            error={errors.default_unit_type}
            onChange={(value) => update("default_unit_type", value as FoodFormValues["default_unit_type"])}
            options={defaultUnitOptions.map((option) => [option, defaultUnitLabels[option]])}
          />
          <NumberField label="مقدار الوحدة" value={form.unit_amount} required error={errors.unit_amount} onChange={(value) => update("unit_amount", value)} />
          <SelectField
            label="أساس الوحدة"
            value={form.unit_basis}
            required
            error={errors.unit_basis}
            onChange={(value) => update("unit_basis", value as FoodFormValues["unit_basis"])}
            options={Object.entries(unitBasisLabels)}
          />
        </FormSection>

        <details className="details-block food-optional-section" open={optionalHasErrors ? true : undefined}>
          <summary>القيم الغذائية الإضافية</summary>
          <div className="form-grid" style={{ marginTop: 12 }}>
            <NumberField label="ألياف g" value={form.fiber_g} error={errors.fiber_g} onChange={(value) => update("fiber_g", value)} />
            <NumberField label="إجمالي السكر g" value={form.sugar_g} error={errors.sugar_g} onChange={(value) => update("sugar_g", value)} />
            <NumberField label="سكر مضاف g" value={form.added_sugar_g} error={errors.added_sugar_g} onChange={(value) => update("added_sugar_g", value)} />
            <NumberField label="دهون مشبعة g" value={form.saturated_fat_g} error={errors.saturated_fat_g} onChange={(value) => update("saturated_fat_g", value)} />
            <NumberField label="دهون متحولة g" value={form.trans_fat_g} error={errors.trans_fat_g} onChange={(value) => update("trans_fat_g", value)} />
            <NumberField label="صوديوم mg" value={form.sodium_mg} error={errors.sodium_mg} onChange={(value) => update("sodium_mg", value)} />
            <NumberField label="كوليسترول mg" value={form.cholesterol_mg} error={errors.cholesterol_mg} onChange={(value) => update("cholesterol_mg", value)} />
            <NumberField label="بوتاسيوم mg" value={form.potassium_mg} error={errors.potassium_mg} onChange={(value) => update("potassium_mg", value)} />
            <NumberField label="كالسيوم mg" value={form.calcium_mg} error={errors.calcium_mg} onChange={(value) => update("calcium_mg", value)} />
            <NumberField label="حديد mg" value={form.iron_mg} error={errors.iron_mg} onChange={(value) => update("iron_mg", value)} />
            <NumberField label="مغنيسيوم mg" value={form.magnesium_mg} error={errors.magnesium_mg} onChange={(value) => update("magnesium_mg", value)} />
            <NumberField label="زنك mg" value={form.zinc_mg} error={errors.zinc_mg} onChange={(value) => update("zinc_mg", value)} />
            <NumberField label="سيلينيوم mcg" value={form.selenium_mcg} error={errors.selenium_mcg} onChange={(value) => update("selenium_mcg", value)} />
            <NumberField label="فيتامين D mcg" value={form.vitamin_d_mcg} error={errors.vitamin_d_mcg} onChange={(value) => update("vitamin_d_mcg", value)} />
            <NumberField label="فيتامين B12 mcg" value={form.vitamin_b12_mcg} error={errors.vitamin_b12_mcg} onChange={(value) => update("vitamin_b12_mcg", value)} />
            <NumberField label="فيتامين C mg" value={form.vitamin_c_mg} error={errors.vitamin_c_mg} onChange={(value) => update("vitamin_c_mg", value)} />
            <NumberField label="فيتامين A RAE mcg" value={form.vitamin_a_rae_mcg} error={errors.vitamin_a_rae_mcg} onChange={(value) => update("vitamin_a_rae_mcg", value)} />
            <NumberField label="فولات DFE mcg" value={form.folate_dfe_mcg} error={errors.folate_dfe_mcg} onChange={(value) => update("folate_dfe_mcg", value)} />
            <NumberField label="فيتامين K mcg" value={form.vitamin_k_mcg} error={errors.vitamin_k_mcg} onChange={(value) => update("vitamin_k_mcg", value)} />
            <NumberField label="يود mcg" value={form.iodine_mcg} error={errors.iodine_mcg} onChange={(value) => update("iodine_mcg", value)} />
          </div>
        </details>

        <FormSection title="مصدر البيانات الغذائية">
          {errors.nutrition_source ? <div className="field-error" role="alert">{errors.nutrition_source}</div> : null}
          <SelectField
            label="نوع المصدر"
            value={form.nutrition_source.type}
            required
            error={errors.nutrition_source}
            onChange={(value) => setForm((current) => ({ ...current, nutrition_source: { ...current.nutrition_source, type: value as FoodFormValues["nutrition_source"]["type"] } }))}
            options={registry.source_types.map((item) => [item.type, item.label_ar])}
          />
          <TextField label="اسم المصدر" value={form.nutrition_source.name ?? ""} required={form.nutrition_source.type !== "unknown"} onChange={(value) => setForm((current) => ({ ...current, nutrition_source: { ...current.nutrition_source, name: value } }))} />
          <TextField label="مرجع المصدر" value={form.nutrition_source.reference ?? ""} onChange={(value) => setForm((current) => ({ ...current, nutrition_source: { ...current.nutrition_source, reference: value } }))} />
          <div className="field"><span>موثوقية المصدر</span><div className="input" aria-label="موثوقية المصدر الحالية">{reliabilityLabel}</div></div>
        </FormSection>

        <FormSection title="المكونات وتصنيف NOVA">
          {errors.ingredients ? <div className="field-error" role="alert">{errors.ingredients}</div> : null}
          <TextAreaField label="المكونات" value={form.ingredients.text ?? ""} onChange={(value) => setForm((current) => ({ ...current, ingredients: { ...current.ingredients, text: value } }))} />
          <SelectField
            label="نوع مصدر المكونات"
            value={form.ingredients.source_type ?? ""}
            onChange={(value) => setForm((current) => ({ ...current, ingredients: { ...current.ingredients, source_type: (value || null) as FoodFormValues["ingredients"]["source_type"] } }))}
            options={[["", "غير محدد"], ...registry.ingredient_source_definitions.map((item) => [item.type, item.label_ar] as [string, string])]}
          />
          <TextField label="اسم مصدر المكونات" value={form.ingredients.source_name ?? ""} onChange={(value) => setForm((current) => ({ ...current, ingredients: { ...current.ingredients, source_name: value } }))} />
          <TextField label="مرجع مصدر المكونات" value={form.ingredients.source_reference ?? ""} onChange={(value) => setForm((current) => ({ ...current, ingredients: { ...current.ingredients, source_reference: value } }))} />
          <SelectField
            label="تصنيف NOVA"
            value={form.nova?.classification ?? ""}
            onChange={(value) => setForm((current) => ({ ...current, nova: value ? { classification: value as NovaClassification } : null }))}
            options={[["", "غير مراجع"], ...registry.nova.classifications.map((item) => [String(item), registry.nova.labels_ar[String(item)]] as [string, string])]}
          />
        </FormSection>

        <FoodGroupFields form={form} setForm={setForm} registry={registry} error={errors.group_contributions ?? errors.analytical_traits} />

        <FormSection title="ملاحظات ومصدر البيانات">
          <TextAreaField label="ملاحظات" value={form.notes ?? ""} maxLength={foodTextMax.notes} error={errors.notes} onChange={(value) => update("notes", value)} />
          <TextField label="مصدر البيانات" value={form.data_source ?? ""} maxLength={foodTextMax.data_source} error={errors.data_source} onChange={(value) => update("data_source", value)} />
        </FormSection>

        <FoodFormActions isEdit={isEdit} foodId={foodId} pending={saveMutation.isPending} food={foodQuery.data ?? null} onDelete={setDeleteTarget} />
      </form>

      <FoodDeleteDialog
        food={deleteTarget}
        pending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </>
  );
}
