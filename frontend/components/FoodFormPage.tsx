"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFood, getFood, getNutritionRegistry, updateFood } from "@/lib/api";
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
import type { FoodResponse } from "@/lib/types";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { FoodFormActions, FormSection, NumberField, SelectField, TextAreaField, TextField } from "@/features/foods/food-form-fields";
import { mapFoodApiError } from "@/features/foods/food-form-model";
import { createFoodNutrientAdapter } from "@/features/foods/food-nutrients";
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
    queryFn: () => getFood(foodId ?? ""),
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

  const nutrientAdapter = useMemo(
    () => createFoodNutrientAdapter(registryQuery.data),
    [registryQuery.data],
  );
  const optionalHasErrors = useMemo(
    () => nutrientAdapter.editable.some(({ field }) => errors[field]),
    [errors, nutrientAdapter],
  );

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
    const definition = registryQuery.data?.food_taxonomy.find((item) => item.key === value);
    const fallbackSubcategory = definition?.subcategories.find((item) => item.key === "other")?.key ?? "other";
    setForm((current) => ({
      ...current,
      primary_category: value,
      subcategory: definition?.subcategories.some((item) => item.key === current.subcategory)
        ? current.subcategory
        : fallbackSubcategory
    }));
    setErrors((current) => {
      const next = { ...current };
      delete next.primary_category;
      delete next.subcategory;
      delete next.form;
      return next;
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saveMutation.isPending || !registryQuery.data) return;
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

  function updateNutritionBasis(value: FoodFormValues["nutrition_basis"]) {
    setForm((current) => ({
      ...current,
      nutrition_basis: value,
      unit_basis: value === "per_100ml" ? "ml" : "g"
    }));
    setErrors((current) => {
      const next = { ...current };
      delete next.nutrition_basis;
      delete next.unit_basis;
      delete next.form;
      return next;
    });
  }

  const registry = registryQuery.data;
  const selectedCategory = registry.food_taxonomy.find((item) => item.key === form.primary_category);

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
          <TextField field="name" label="اسم الطعام" value={form.name} required maxLength={foodTextMax.name} error={errors.name} onChange={(value) => update("name", value)} />
          <TextField field="brand" label="العلامة التجارية" value={form.brand ?? ""} maxLength={foodTextMax.brand} error={errors.brand} onChange={(value) => update("brand", value)} />
          <SelectField
            field="primary_category"
            label="التصنيف الرئيسي"
            value={form.primary_category}
            required
            error={errors.primary_category}
            onChange={updateFoodCategory}
            options={registry.food_taxonomy.map((item) => [item.key, item.label_ar])}
          />
          <SelectField
            field="subcategory"
            label="التصنيف الفرعي"
            value={form.subcategory}
            required
            error={errors.subcategory}
            onChange={(value) => update("subcategory", value)}
            options={(selectedCategory?.subcategories ?? []).map((item) => [item.key, item.label_ar])}
          />
        </FormSection>

        <FormSection title="أساس القيم الغذائية">
          <SelectField
            field="nutrition_basis"
            label="أساس القيم"
            value={form.nutrition_basis}
            required
            error={errors.nutrition_basis}
            onChange={(value) => updateNutritionBasis(value as FoodFormValues["nutrition_basis"])}
            options={Object.entries(nutritionBasisLabels)}
          />
        </FormSection>

        <FormSection title="القيم الغذائية الأساسية">
          <NumberField field="calories" label="السعرات" value={form.calories} required error={errors.calories} onChange={(value) => update("calories", value)} />
          <NumberField field="protein_g" label="البروتين g" value={form.protein_g} required error={errors.protein_g} onChange={(value) => update("protein_g", value)} />
          <NumberField field="carb_g" label="الكارب g" value={form.carb_g} required error={errors.carb_g} onChange={(value) => update("carb_g", value)} />
          <NumberField field="fat_g" label="الدهون g" value={form.fat_g} required error={errors.fat_g} onChange={(value) => update("fat_g", value)} />
        </FormSection>

        <FormSection title="الوحدة الافتراضية">
          <SelectField
            field="default_unit_type"
            label="الوحدة الافتراضية"
            value={form.default_unit_type}
            required
            error={errors.default_unit_type}
            onChange={(value) => update("default_unit_type", value as FoodFormValues["default_unit_type"])}
            options={defaultUnitOptions.map((option) => [option, defaultUnitLabels[option]])}
          />
          <NumberField field="unit_amount" label="مقدار الوحدة" value={form.unit_amount} required error={errors.unit_amount} onChange={(value) => update("unit_amount", value)} />
          <SelectField
            field="unit_basis"
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
            {nutrientAdapter.editable.map(({ field, label, unit }) => (
              <NumberField
                key={field}
                field={field}
                label={`${label} ${unit}`}
                value={form[field]}
                error={errors[field]}
                onChange={(value) => update(field, value)}
              />
            ))}
          </div>
        </details>

        <FormSection title="مصدر البيانات الغذائية">
          <SelectField
            field="nutrition_data_source"
            label="مصدر البيانات الغذائية"
            value={form.nutrition_data_source}
            required
            error={errors.nutrition_data_source}
            onChange={(value) => update("nutrition_data_source", value as FoodFormValues["nutrition_data_source"])}
            options={registry.nutrition_data_sources.map((item) => [item.key, item.label_ar])}
          />
        </FormSection>

        <FormSection title="المكونات">
          <TextAreaField field="ingredients" label="المكونات" value={form.ingredients ?? ""} error={errors.ingredients} onChange={(value) => update("ingredients", value)} />
        </FormSection>

        <FormSection title="ملاحظات">
          <TextAreaField field="notes" label="ملاحظات" value={form.notes ?? ""} maxLength={foodTextMax.notes} error={errors.notes} onChange={(value) => update("notes", value)} />
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
