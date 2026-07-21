"use client";

import { ArrowRight, ChevronDown, Plus, Save, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Dispatch, FormEvent, MouseEvent, SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, createFood, getAdminFood, getNutritionRegistry, updateFood } from "@/lib/api";
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
import type { FoodResponse, NutritionRegistryResponse, NovaClassification } from "@/lib/types";

import { FoodDeleteDialog } from "./FoodDeleteDialog";
import { useFoodDelete } from "./useFoodDelete";
import { useAuth } from "./AuthProvider";

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
  "selenium_mcg",
  "vitamin_d_mcg",
  "vitamin_b12_mcg",
  "vitamin_c_mg",
  "vitamin_a_rae_mcg",
  "folate_dfe_mcg",
  "vitamin_k_mcg",
  "iodine_mcg"
];

export function FoodFormPage({ mode, foodId }: { mode: "create" | "edit"; foodId?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FoodFormValues>(emptyFoodForm);
  const [errors, setErrors] = useState<FoodFormErrors>({});
  const [note, setNote] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<FoodResponse | null>(null);
  const [hydratedFoodId, setHydratedFoodId] = useState<string | null>(null);
  const initialForm = useRef(JSON.stringify(emptyFoodForm));
  const isEdit = mode === "edit";
  const { account, session, loading: authLoading } = useAuth();
  const accessToken = session?.access_token;

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
      setForm(loaded);
      initialForm.current = JSON.stringify(loaded);
      setHydratedFoodId(foodQuery.data.id);
    }
  }, [foodQuery.data]);

  const dirty = JSON.stringify(form) !== initialForm.current;
  useEffect(() => {
    const protect = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, [dirty]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = normalizeFoodForm(form);
      if (isEdit && foodId) return updateFood(foodId, payload, accessToken);
      return createFood(payload, accessToken);
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

  function protectUnsaved(event: MouseEvent<HTMLAnchorElement>) {
    if (dirty && !window.confirm("لديك تغييرات غير محفوظة. هل تريد المغادرة؟")) {
      event.preventDefault();
    }
  }

  if (isEdit && (foodQuery.isPending || (foodQuery.data && hydratedFoodId !== foodQuery.data.id))) {
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
          <Link className="btn" href={isEdit && foodId ? `/foods/${foodId}` : "/foods"} onClick={protectUnsaved}>
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

        <div className="form-actions-sticky">
          <button className="btn primary" type="submit" disabled={saveMutation.isPending}>
            <Save size={18} />
            {saveMutation.isPending ? "جاري الحفظ..." : isEdit ? "حفظ التعديل" : "حفظ الطعام"}
          </button>
          <Link className="btn" href={isEdit && foodId ? `/foods/${foodId}` : "/foods"} onClick={protectUnsaved}>
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
    const code = "code" in item && typeof item.code === "string" ? item.code : "";
    if (code.startsWith("source_")) next.nutrition_source = msg;
    else if (code.startsWith("ingredients_")) next.ingredients = msg;
    else if (code.includes("food_group") || code.includes("group_data")) next.group_contributions = msg;
    else if (code.includes("analytical_trait")) next.analytical_traits = msg;
    else if (field && field in emptyFoodForm) next[field] = msg;
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

function FoodGroupFields({
  form,
  setForm,
  registry,
  error
}: {
  form: FoodFormValues;
  setForm: Dispatch<SetStateAction<FoodFormValues>>;
  registry: NutritionRegistryResponse;
  error?: string;
}) {
  const [showAllTraits, setShowAllTraits] = useState(false);
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const suggestedGroup = suggestedGroupKey(form);

  useEffect(() => {
    if (error && detailsRef.current) detailsRef.current.open = true;
  }, [error]);
  const addContribution = () => {
    const definition = registry.food_group_definitions.find(
      (item) => !form.group_contributions.some((entry) => entry.group_key === item.key)
    );
    if (!definition) return;
    const subtypes = subtypeKeys(definition);
    setForm((current) => ({
      ...current,
      group_contributions: [
        ...current.group_contributions,
        {
          group_key: definition.key,
          subtype_key: subtypes[0] ?? null,
          amount_per_100_basis: 1,
          data_status: "known"
        }
      ]
    }));
  };
  const confirmSuggestion = () => {
    if (!suggestedGroup || form.group_contributions.some((item) => item.group_key === suggestedGroup)) return;
    const definition = registry.food_group_definitions.find((item) => item.key === suggestedGroup);
    if (!definition) return;
    setForm((current) => ({
      ...current,
      group_contributions: [...current.group_contributions, {
        group_key: suggestedGroup,
        subtype_key: subtypeKeys(definition)[0] ?? null,
        amount_per_100_basis: 1,
        data_status: "estimated"
      }]
    }));
  };
  const relevantTraits = new Set([
    ...form.analytical_traits,
    ...relevantTraitKeys(form.food_category_key),
    "processed",
    "salted"
  ]);

  return (
    <details
      ref={detailsRef}
      className="form-panel food-form-section advanced-analysis"
      aria-labelledby="food-groups-title"
      onToggle={(event) => {
        if (error && !event.currentTarget.open) event.currentTarget.open = true;
      }}
    >
      <summary className="advanced-analysis-summary" id="food-groups-title">
        <span className="advanced-analysis-heading">
          <span className="panel-title">التحليل الغذائي المتقدم</span>
          <span className="advanced-analysis-optional">اختياري</span>
        </span>
        <span className="advanced-analysis-disclosure">
          <small>{form.group_contributions.length} مجموعة غذائية • {form.analytical_traits.length} سمات</small>
          <span className="advanced-analysis-action">
            <span className="advanced-analysis-action-open">فتح وإدارة التحليل</span>
            <span className="advanced-analysis-action-close">إغلاق التحليل</span>
          </span>
          <ChevronDown className="advanced-analysis-chevron" size={20} aria-hidden="true" />
        </span>
      </summary>
      {error ? <div className="field-error" role="alert">{error}</div> : null}
      <h3>المجموعات الغذائية</h3>
      <p className="page-kicker">حدد المجموعات التي يساهم فيها هذا الطعام لاستخدامها في التحليل الأسبوعي. المقادير لكل 100 جم أو 100 مل.</p>
      {suggestedGroup && !form.group_contributions.some((item) => item.group_key === suggestedGroup) ? (
        <div className="analysis-suggestion">
          <span>اقتراح حسب فئة الطعام: {registry.food_group_definitions.find((item) => item.key === suggestedGroup)?.label_ar}</span>
          <button className="btn" type="button" onClick={confirmSuggestion}>تأكيد الاقتراح</button>
        </div>
      ) : null}

      <div className="food-classification-list">
        {form.group_contributions.map((entry, index) => {
          const definition = registry.food_group_definitions.find((item) => item.key === entry.group_key);
          const subtypes = definition ? subtypeKeys(definition) : [];
          return (
            <fieldset className="form-grid contribution-card" key={`${entry.group_key}-${index}`}>
              <legend>مجموعة غذائية {index + 1}</legend>
              <SelectField
                label={`المجموعة ${index + 1}`}
                value={entry.group_key}
                onChange={(value) => setForm((current) => ({ ...current, group_contributions: current.group_contributions.map((item, itemIndex) => itemIndex === index ? { ...item, group_key: value, subtype_key: subtypeKeys(registry.food_group_definitions.find((definitionItem) => definitionItem.key === value))[0] ?? null } : item) }))}
                options={registry.food_group_definitions.map((item) => [item.key, item.label_ar])}
              />
              {subtypes.length ? (
                <SelectField label={`النوع الفرعي ${index + 1}`} value={entry.subtype_key ?? ""} onChange={(value) => setForm((current) => ({ ...current, group_contributions: current.group_contributions.map((item, itemIndex) => itemIndex === index ? { ...item, subtype_key: value } : item) }))} options={subtypes.map((item) => [item, definition?.subtype_labels_ar[item] ?? item])} />
              ) : null}
              <NumberField label={`المقدار من 100 (${index + 1})`} value={entry.amount_per_100_basis} onChange={(value) => setForm((current) => ({ ...current, group_contributions: current.group_contributions.map((item, itemIndex) => itemIndex === index ? { ...item, amount_per_100_basis: value ?? 0 } : item) }))} />
              <SelectField label={`يقين المساهمة ${index + 1}`} value={entry.data_status} onChange={(value) => setForm((current) => ({ ...current, group_contributions: current.group_contributions.map((item, itemIndex) => itemIndex === index ? { ...item, data_status: value as "known" | "estimated" } : item) }))} options={[["known", "مؤكدة"], ["estimated", "تقديرية"]]} />
              <button className="btn danger" type="button" onClick={() => setForm((current) => ({ ...current, group_contributions: current.group_contributions.filter((_, itemIndex) => itemIndex !== index) }))} aria-label={`حذف المساهمة ${index + 1}`}><Trash2 size={18} />حذف</button>
            </fieldset>
          );
        })}
        <button className="btn" type="button" onClick={addContribution} disabled={form.group_contributions.length >= registry.food_group_definitions.length}><Plus size={18} />إضافة مجموعة غذائية</button>
      </div>

      <fieldset className="food-traits-fieldset">
        <legend>السمات التحليلية</legend>
        <p className="page-kicker">اختر السمات المثبتة في المصدر فقط. لا تُحفظ الاقتراحات تلقائيًا.</p>
        {traitGroups.map((group) => {
          const traits = registry.traits.filter((trait) => group.keys.includes(trait.key) && (showAllTraits || relevantTraits.has(trait.key)));
          if (!traits.length) return null;
          return <div className="trait-group" key={group.label}><h4>{group.label}</h4><div className="food-traits-grid trait-chips">{traits.map((trait) => (
            <label key={trait.key} className="trait-chip" title={traitHelp[trait.key]}>
              <input type="checkbox" checked={form.analytical_traits.includes(trait.key)} onChange={(event) => setForm((current) => ({ ...current, analytical_traits: event.target.checked ? [...current.analytical_traits, trait.key] : current.analytical_traits.filter((item) => item !== trait.key) }))} />
              <span>{trait.label_ar}</span>
            </label>
          ))}</div></div>;
        })}
        <button className="btn" type="button" onClick={() => setShowAllTraits((value) => !value)}>{showAllTraits ? "عرض الأقل" : "عرض المزيد"}</button>
      </fieldset>
    </details>
  );
}

const traitGroups = [
  { label: "المنشأ", keys: ["omega3_rich_seafood", "fruit_liquid_100_percent", "dried_fruit", "starchy_root"] },
  { label: "المعالجة", keys: ["processed", "smoked", "salted"] },
  { label: "الخصائص الغذائية", keys: ["sweetened", "non_nutritive_sweetened", "calcium_fortified", "unsaturated_fat_source"] }
];

const traitHelp: Record<string, string> = {
  non_nutritive_sweetened: "يحتوي على مُحلٍ لا يضيف سكرًا غذائيًا.",
  omega3_rich_seafood: "صفة تحليلية للمأكولات البحرية المثبت غناها بأوميغا 3.",
  fruit_liquid_100_percent: "عصير أو سموذي فواكه كامل دون تخمين من الاسم."
};

function relevantTraitKeys(category: string): string[] {
  if (category === "seafood") return ["omega3_rich_seafood"];
  if (category === "dairy_fortified_alternatives") return ["calcium_fortified"];
  if (category === "fruits") return ["fruit_liquid_100_percent", "dried_fruit"];
  if (["nuts_seeds", "added_oils_fats"].includes(category)) return ["unsaturated_fat_source"];
  if (["sweets", "sugar_sweetened_beverages"].includes(category)) return ["sweetened", "non_nutritive_sweetened"];
  if (["processed_meat", "red_meat"].includes(category)) return ["processed", "smoked", "salted"];
  return [];
}

function suggestedGroupKey(form: FoodFormValues): string | null {
  if (["baked_goods", "grains_starches"].includes(form.food_category_key)) {
    if (form.grain_type === "whole") return "whole_grains";
    if (form.grain_type === "refined") return "refined_grains";
    return null;
  }
  const direct = new Set(["vegetables", "fruits", "legumes", "nuts_seeds", "seafood", "dairy_fortified_alternatives", "eggs", "poultry", "red_meat", "processed_meat", "added_oils_fats", "sweets", "sugar_sweetened_beverages", "unsweetened_beverages", "mixed_dish"]);
  return direct.has(form.food_category_key) ? form.food_category_key : null;
}

function subtypeKeys(definition: NutritionRegistryResponse["food_group_definitions"][number] | undefined): string[] {
  if (!definition?.subtypes) return [];
  return Array.isArray(definition.subtypes) ? definition.subtypes : Object.keys(definition.subtypes);
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
  placeholder,
  error,
  required = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
  placeholder?: string;
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
        {placeholder ? <option value="" disabled>{placeholder}</option> : null}
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
