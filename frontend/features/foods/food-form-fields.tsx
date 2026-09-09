import { Save, Trash2, X } from "lucide-react";
import Link from "next/link";

import type { FoodResponse } from "@/lib/types";
import { fieldId } from "./food-form-model";

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
