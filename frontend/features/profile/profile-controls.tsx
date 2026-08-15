import { Check, ChevronLeft } from "lucide-react";
import type { ReactNode, RefObject } from "react";
import type { CutIntensity } from "@/lib/types";

export function SettingsButton({ icon, label, value, onClick, ariaLabel }: { icon: ReactNode; label: string; value: string; onClick: () => void; ariaLabel: string }) {
  return <button className="profile-setting-row" type="button" onClick={onClick} aria-label={ariaLabel}>{icon}<span className="profile-setting-copy"><strong>{label}</strong><bdi>{value}</bdi></span><ChevronLeft size={18} aria-hidden="true" /></button>;
}

export function NumericSettingsRow({ ref, icon, label, value, unit, step, min, max, error, help, onChange }: { ref: RefObject<HTMLInputElement | null>; icon?: ReactNode; label: string; value: string; unit: string; step: string; min?: number; max?: number; error?: string; help?: string; onChange: (value: string) => void }) {
  const id = `profile-${label.replaceAll(" ", "-")}`;
  return (
    <label className={`profile-setting-row profile-number-row ${error ? "has-error" : ""}`}>
      {icon ?? <span className="profile-row-spacer" />}
      <span className="profile-setting-copy"><strong>{label}</strong>{help ? <small>{help}</small> : null}</span>
      <span className="profile-number-control" dir="ltr"><input ref={ref} id={id} type="text" inputMode="decimal" value={value} min={min} max={max} step={step} onChange={(event) => onChange(event.target.value)} aria-label={label} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : help ? `${id}-help` : undefined} /><bdi>{unit}</bdi></span>
      {error ? <small id={`${id}-error`} className="profile-field-error">{error}</small> : null}
      {help ? <span id={`${id}-help`} className="sr-only">{help}</span> : null}
    </label>
  );
}

export function SelectionCard({ icon, title, value, description, onClick, ariaLabel }: { icon: ReactNode; title: string; value: string; description: string; onClick: () => void; ariaLabel: string }) {
  return (
    <section className="profile-selection-card">
      <h2>{title}</h2>
      <button type="button" onClick={onClick} aria-label={ariaLabel}>{icon}<span><strong>{value}</strong><small>{description}</small></span><ChevronLeft size={19} aria-hidden="true" /></button>
    </section>
  );
}

export const cutIntensityOptions: Array<{ value: CutIntensity; label: string; percent: string; recommended?: boolean }> = [
  { value: 0.15, label: "خفيف", percent: "15%" },
  { value: 0.2, label: "عادي", percent: "20%", recommended: true },
  { value: 0.25, label: "قوي", percent: "25%" }
];

export function CutIntensitySelector({ value, onChange }: { value: CutIntensity; onChange: (value: CutIntensity) => void }) {
  return (
    <fieldset className="profile-cut-intensity" role="radiogroup">
      <legend>شدة خفض الوزن</legend>
      <div className="profile-cut-intensity-options">
        {cutIntensityOptions.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name="profile-cut-intensity"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span>
              <strong>{option.label}</strong>
              <bdi dir="ltr">{option.percent}</bdi>
              {option.recommended ? <small>موصى به</small> : null}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function OptionList({ value, options, onChoose }: { value: string; options: Array<{ value: string; label: string; description?: string }>; onChoose: (value: string) => void }) {
  return <div className="profile-option-list" role="radiogroup">{options.map((option) => <button key={option.value} type="button" role="radio" aria-checked={value === option.value} onClick={() => onChoose(option.value)}><span><strong>{option.label}</strong>{option.description ? <small>{option.description}</small> : null}</span>{value === option.value ? <Check size={19} aria-label="محدد" /> : <span className="profile-radio-dot" />}</button>)}</div>;
}
