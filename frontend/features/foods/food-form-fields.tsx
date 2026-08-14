import { ChevronDown, Plus, Save, Trash2, X } from "lucide-react";
import Link from "next/link";
import type { Dispatch, SetStateAction } from "react";
import { useEffect, useRef, useState } from "react";

import type { FoodFormValues } from "@/lib/food";
import type { FoodResponse } from "@/lib/types";
import type { NutritionRegistryResponse } from "@/lib/types";
import { fieldId, relevantTraitKeys, suggestedGroupKey, subtypeKeys, traitGroups, traitHelp } from "./food-form-model";

export function FoodFormActions({ isEdit, foodId, pending, food, onDelete }: { isEdit: boolean; foodId?: string; pending: boolean; food: FoodResponse | null; onDelete: (food: FoodResponse) => void }) {
  return (
    <div className="form-actions-sticky">
      <button className="btn primary" type="submit" disabled={pending}>
        <Save size={18} />
        {pending ? "جاري الحفظ..." : isEdit ? "حفظ التعديل" : "حفظ الطعام"}
      </button>
      <Link className="btn" href={isEdit && foodId ? `/foods/${foodId}` : "/foods"}>
        <X size={18} />
        إلغاء
      </Link>
      {isEdit && food ? (
        <button className="btn danger" type="button" onClick={() => onDelete(food)}>
          <Trash2 size={18} />
          حذف
        </button>
      ) : null}
    </div>
  );
}

export function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="form-panel food-form-section">
      <h2 className="panel-title">{title}</h2>
      <div className="form-grid">{children}</div>
    </section>
  );
}

export function FoodGroupFields({
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

export function TextField({
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

export function TextAreaField({ label, value, onChange, error, maxLength }: { label: string; value: string; onChange: (value: string) => void; error?: string; maxLength?: number }) {
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

export function NumberField({
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

export function SelectField({
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
