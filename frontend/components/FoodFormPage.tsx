"use client";

import { ArrowRight, Save, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, createFood, getFood, updateFood } from "@/lib/api";
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
import { useFoodDelete } from "./useFoodDelete";

const FOOD_READ_ERROR = "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.";
const WRITE_ERROR = "تعذر الاتصال بالخادم. لم يتم حفظ التغييرات.";
const VALIDATION_ERROR = "راجع الحقول المحددة ثم حاول مرة أخرى.";

const optionalFields: (keyof FoodFormValues)[] = [
  "fiber_g",
  "sugar_g",
  "added_sugar_g",
  "saturated_fat_g",
  "trans_fat_g",
  "sodium_mg",
  "cholesterol_mg",
  "potassium_mg",
  "calcium_mg",
  "iron_mg",
  "magnesium_mg",
  "zinc_mg",
  "vitamin_d_mcg",
  "vitamin_b12_mcg",
  "vitamin_c_mg",
  "vitamin_a_mcg",
  "folate_mcg",
  "vitamin_k_mcg"
];

export function FoodFormPage({ mode, foodId }: { mode: "create" | "edit"; foodId?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FoodFormValues>(emptyFoodForm);
  const [errors, setErrors] = useState<FoodFormErrors>({});
  const [note, setNote] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const isEdit = mode === "edit";

  const foodQuery = useQuery({
    queryKey: ["food", foodId],
    queryFn: () => getFood(foodId ?? ""),
    enabled: isEdit && Boolean(foodId)
  });

  useEffect(() => {
    if (foodQuery.data) setForm(foodToForm(foodQuery.data));
  }, [foodQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = normalizeFoodForm(form);
      if (isEdit && foodId) return updateFood(foodId, payload);
      return createFood(payload);
    },
    onSuccess: async (food) => {
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
      await queryClient.invalidateQueries({ queryKey: ["food", food.id] });
      router.push(`/foods/${food.id}`);
    },
    onError: (error) => {
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
    onDeleted: () => router.push("/foods"),
    onError: (message) => setNote(message)
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

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saveMutation.isPending) return;
    const nextErrors = validateFoodForm(form);
    setErrors(nextErrors);
    if (hasFoodErrors(nextErrors)) {
      setNote(VALIDATION_ERROR);
      return;
    }
    setNote("");
    saveMutation.mutate();
  }

  if (isEdit && foodQuery.isPending) {
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
        {note ? (
          <div className="state-note" role={hasFoodErrors(errors) ? "alert" : "status"} aria-live="polite">
            {note}
          </div>
        ) : null}

        <FormSection title="معلومات الطعام الأساسية">
          <TextField label="اسم الطعام" value={form.name} required maxLength={foodTextMax.name} error={errors.name} onChange={(value) => update("name", value)} />
          <TextField label="العلامة التجارية" value={form.brand ?? ""} maxLength={foodTextMax.brand} error={errors.brand} onChange={(value) => update("brand", value)} />
          <TextField label="التصنيف" value={form.category ?? ""} maxLength={foodTextMax.category} error={errors.category} onChange={(value) => update("category", value)} />
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
            <NumberField label="فيتامين D mcg" value={form.vitamin_d_mcg} error={errors.vitamin_d_mcg} onChange={(value) => update("vitamin_d_mcg", value)} />
            <NumberField label="فيتامين B12 mcg" value={form.vitamin_b12_mcg} error={errors.vitamin_b12_mcg} onChange={(value) => update("vitamin_b12_mcg", value)} />
            <NumberField label="فيتامين C mg" value={form.vitamin_c_mg} error={errors.vitamin_c_mg} onChange={(value) => update("vitamin_c_mg", value)} />
            <NumberField label="فيتامين A mcg" value={form.vitamin_a_mcg} error={errors.vitamin_a_mcg} onChange={(value) => update("vitamin_a_mcg", value)} />
            <NumberField label="فولات mcg" value={form.folate_mcg} error={errors.folate_mcg} onChange={(value) => update("folate_mcg", value)} />
            <NumberField label="فيتامين K mcg" value={form.vitamin_k_mcg} error={errors.vitamin_k_mcg} onChange={(value) => update("vitamin_k_mcg", value)} />
          </div>
        </details>

        <FormSection title="ملاحظات ومصدر البيانات">
          <TextAreaField label="ملاحظات" value={form.notes ?? ""} maxLength={foodTextMax.notes} error={errors.notes} onChange={(value) => update("notes", value)} />
          <TextField label="مصدر البيانات" value={form.data_source ?? ""} maxLength={foodTextMax.data_source} error={errors.data_source} onChange={(value) => update("data_source", value)} />
        </FormSection>

        <div className="form-actions-sticky">
          <button className="btn primary" type="submit" disabled={saveMutation.isPending}>
            <Save size={18} />
            {saveMutation.isPending ? "جاري الحفظ..." : isEdit ? "حفظ التعديل" : "حفظ الطعام"}
          </button>
          <Link className="btn" href={isEdit && foodId ? `/foods/${foodId}` : "/foods"}>
            <X size={18} />
            إلغاء
          </Link>
          {isEdit && foodQuery.data ? (
            <button className="btn danger" type="button" onClick={() => setDeleteTarget(foodQuery.data ?? null)}>
              <Trash2 size={18} />
              حذف
            </button>
          ) : null}
        </div>
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

function mapFoodApiError(error: unknown): FoodFormErrors {
  if (!(error instanceof ApiError)) return {};
  if (error.status === 404) return { form: "لم يتم العثور على الطعام. حدّث القائمة وحاول مرة أخرى." };
  if (error.status !== 422 || !Array.isArray(error.detail)) return {};

  const next: FoodFormErrors = {};
  for (const item of error.detail) {
    if (!item || typeof item !== "object") continue;
    const explicitField = "field" in item && typeof item.field === "string" ? item.field : undefined;
    const loc = "loc" in item && Array.isArray(item.loc) ? item.loc : [];
    const field = (explicitField ?? loc[loc.length - 1]) as keyof FoodFormValues | undefined;
    const msg = "msg" in item && typeof item.msg === "string" ? item.msg : VALIDATION_ERROR;
    if (field && field in emptyFoodForm) next[field] = msg;
    else next.form = msg;
  }
  return next;
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="form-panel food-form-section">
      <h2 className="panel-title">{title}</h2>
      <div className="form-grid">{children}</div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  error,
  required = false,
  maxLength
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  maxLength?: number;
}) {
  const id = fieldId(label);
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label} {required ? <b aria-label="مطلوب">*</b> : null}
      </span>
      <input
        id={id}
        className="input"
        value={value}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error ? <span id={`${id}-error`} className="field-error">{error}</span> : null}
    </label>
  );
}

function TextAreaField({ label, value, onChange, error, maxLength }: { label: string; value: string; onChange: (value: string) => void; error?: string; maxLength?: number }) {
  const id = fieldId(label);
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      <textarea
        id={id}
        className="input textarea"
        value={value}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error ? <span id={`${id}-error`} className="field-error">{error}</span> : null}
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
  error,
  required = false
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  error?: string;
  required?: boolean;
}) {
  const id = fieldId(label);
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label} {required ? <b aria-label="مطلوب">*</b> : null}
      </span>
      <input
        id={id}
        className="input"
        type="number"
        min="0"
        step="0.01"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error ? <span id={`${id}-error`} className="field-error">{error}</span> : null}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  error,
  required = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
  error?: string;
  required?: boolean;
}) {
  const id = fieldId(label);
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label} {required ? <b aria-label="مطلوب">*</b> : null}
      </span>
      <select
        id={id}
        className="select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
      {error ? <span id={`${id}-error`} className="field-error">{error}</span> : null}
    </label>
  );
}

function fieldId(label: string): string {
  return `food-${label.replace(/\s+/g, "-")}`;
}
