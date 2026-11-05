"use client";

import { useEffect, useRef, type RefObject } from "react";
import { Dialog } from "@base-ui-components/react/dialog";

import type { LabCatalogResponse } from "@/lib/types";
import { batchErrorTarget, labErrorMessage, mapLabErrors, populatedCount, resultCountLabel, type BatchPhase } from "./lab-batch-model";
import { formatGregorianArabicDate } from "@/lib/dates";
import styles from "./labs.module.css";

type LabBatchDialogProps = {
  phase: BatchPhase | null;
  catalog: LabCatalogResponse | undefined;
  serverToday: string | undefined;
  returnFocusRef?: RefObject<HTMLElement | null>;
  onDate: (value: string) => void;
  onNote: (value: string) => void;
  onPanel: (key: string, selected: boolean) => void;
  onIndividual: (key: string, selected: boolean) => void;
  onValue: (key: string, value: string) => void;
  onUnit: (key: string, unit: string) => void;
  onNext: () => void; onBack: () => void; onSave: () => void;
  onRetry: () => void; onCancel: () => void;
};

export function LabBatchDialog(props: LabBatchDialogProps) {
  const { phase, catalog } = props;
  const popup = useRef<HTMLDivElement>(null);
  const step = phase && "draft" in phase ? phase.draft.step : null;
  const firstError = phase?.kind === "validation_error" ? phase.errors[0] : undefined;
  useEffect(() => {
    if (!step) return;
    const frame = requestAnimationFrame(() => {
      const fields = popup.current?.querySelector("fieldset");
      if (fields?.contains(document.activeElement)) return;
      const input = fields?.querySelector<HTMLInputElement>("input");
      input?.focus({ preventScroll: true });
      input?.scrollIntoView({ block: "nearest" });
    });
    return () => cancelAnimationFrame(frame);
  }, [step]);
  useEffect(() => {
    if (!firstError) return;
    const frame = requestAnimationFrame(() => {
      const element = document.getElementById(batchErrorTarget(firstError).id) ?? document.getElementById("lab-batch-errors");
      element?.focus({ preventScroll: true });
      element?.scrollIntoView({ block: "nearest" });
    });
    return () => cancelAnimationFrame(frame);
  }, [firstError]);
  const draft = phase && "draft" in phase ? phase.draft : null;
  const panelTestKeys = new Set(catalog?.panels.filter((panel) => draft?.panelKeys.includes(panel.key)).flatMap((panel) => panel.test_keys));
  const locked = phase?.kind === "submitting" || phase?.kind === "ambiguous";
  const errors = phase?.kind === "validation_error" ? mapLabErrors(phase.errors) : { rows: {} };
  return <Dialog.Root open={Boolean(draft)} disablePointerDismissal={locked} onOpenChange={(open, event) => {
    if (open) return;
    if (locked) event.cancel(); else props.onCancel();
  }}>
    <Dialog.Portal>
      <Dialog.Backdrop className={styles.batchBackdrop} />
      <Dialog.Popup ref={popup} className={styles.batchDialog} data-step={draft?.step} dir="rtl" initialFocus={false} finalFocus={props.returnFocusRef}>
        <Dialog.Title>إضافة نتائج</Dialog.Title>
        <Dialog.Description>التاريخ، ثم اختيار التحاليل، ثم إدخال القيم.</Dialog.Description>
        {draft && catalog ? <>
          <ol className={styles.batchSteps} aria-label="خطوات إضافة النتائج">
            {([ ["date", "التاريخ"], ["selection", "اختيار التحاليل"], ["values", "القيم"] ] as const).map(([key, label]) => <li key={key} aria-current={draft.step === key ? "step" : undefined}>{label}</li>)}
          </ol>
          {phase?.kind === "ambiguous" ? <p role="alert">لم نتأكد من حفظ النتائج. اضغط «إعادة المحاولة»، ولن تتكرر النتائج.</p> : null}
          <div className={styles.batchFieldViewport}>
          {phase?.kind === "validation_error" ? <div id="lab-batch-errors" role="alert" tabIndex={-1} className={styles.batchError}>
            {phase.errors.map((error, index) => <p key={index}>{labErrorMessage(error)}</p>)}
          </div> : null}
          <fieldset className={styles.batchFields} disabled={locked}>
            <legend className="sr-only">{draft.step === "date" ? "تاريخ النتائج" : draft.step === "selection" ? "اختيار التحاليل" : "قيم النتائج"}</legend>
            {draft.step === "date" ? <div className={styles.batchDate}>
              <label htmlFor="lab-batch-date">تاريخ التحليل</label>
              <input id="lab-batch-date" type="date" dir="ltr" value={draft.date} aria-invalid={Boolean(errors.test_date)} aria-describedby={errors.test_date ? "lab-date-error" : "lab-date-context"} onChange={(event) => props.onDate(event.target.value)} />
              <div id="lab-date-context" className={styles.batchDateContext}>
                {draft.date ? <span>التاريخ المحدد: <strong><time dateTime={draft.date}>{formatGregorianArabicDate(draft.date)}</time></strong></span> : null}
                {props.serverToday ? <span>تاريخ اليوم: <time dateTime={props.serverToday}>{formatGregorianArabicDate(props.serverToday)}</time></span> : null}
              </div>
              {errors.test_date ? <span id="lab-date-error" className={styles.batchError}>{errors.test_date}</span> : null}
            </div> : null}
            {draft.step === "date" ? <div className={styles.batchNote}>
              <label htmlFor="lab-batch-note">ملاحظة</label>
              <p id="lab-note-hint">الملاحظة اختيارية وتُحفظ مع كل نتيجة تضيفها في هذه الدفعة.</p>
              <textarea id="lab-batch-note" dir="auto" value={draft.note} aria-invalid={Boolean(errors.note)} aria-describedby={errors.note ? "lab-note-error lab-note-hint" : "lab-note-hint"} onChange={(event) => props.onNote(event.target.value)} />
              {errors.note ? <span id="lab-note-error" className={styles.batchError}>{errors.note}</span> : null}
            </div> : null}
            {draft.step === "selection" ? <>
              <h3>مجموعات التحاليل</h3>
              <p className={styles.batchSelectionHint}>اختيار المجموعة يضيف تحاليلها تلقائيًا بدون تكرار.</p>
              <div className={styles.batchChoiceGrid}>{catalog.panels.map((panel) => <label className={styles.batchChoice} data-selected={draft.panelKeys.includes(panel.key)} key={panel.key}>
                <input data-panel-key={panel.key} type="checkbox" checked={draft.panelKeys.includes(panel.key)} onChange={(event) => props.onPanel(panel.key, event.target.checked)} />
                <span className={styles.batchChoiceText}><strong>{panel.name_ar}</strong><bdi dir="ltr">{panel.name_en}</bdi><small>عدد التحاليل: {panel.test_keys.length}</small></span>
              </label>)}</div>
              <h3>تحاليل فردية</h3>
              {catalog.categories.map((category) => <div className={styles.batchCategory} key={category.key}><h4>{category.name_ar}</h4>
                <div className={styles.batchChoiceGrid}>{catalog.tests.filter((test) => test.primary_category === category.key).map((test) => <label className={styles.batchChoice} data-selected={Boolean(draft.rows[test.test_key])} key={test.test_key}>
                  <input data-individual-key={test.test_key} type="checkbox" checked={draft.individualKeys.includes(test.test_key)} onChange={(event) => props.onIndividual(test.test_key, event.target.checked)} />
                  <span className={styles.batchChoiceText}><strong>{test.name_ar}</strong><bdi dir="ltr">{test.abbreviation ?? test.name_en}</bdi>{panelTestKeys.has(test.test_key) ? <small>مضاف ضمن مجموعة</small> : null}</span>
                </label>)}</div>
              </div>)}
            </> : null}
            {draft.step === "values" ? <p id="lab-values-hint" className={styles.batchValuesHint}>أدخل القيمة واختر الوحدة كما تظهر في تقرير المختبر. اترك ما لا تتوفر له نتيجة فارغًا؛ تُحفظ القيم المدخلة فقط.</p> : null}
            {draft.step === "values" ? Object.entries(draft.rows).map(([key, row]) => {
              const test = catalog.tests.find((test) => test.test_key === key)!;
              const rowErrors = errors.rows[key];
              const valueError = rowErrors?.entered_value ?? rowErrors?.form;
              return <fieldset className={styles.batchRow} key={key} data-testid="lab-batch-row" data-test-key={key} aria-labelledby={`lab-${key}-name`}>
                <legend id={`lab-${key}-name`}><strong>{test.name_ar}</strong> <bdi dir="ltr">{test.abbreviation ?? test.name_en}</bdi></legend>
                <label>القيمة
                  <input id={`lab-${key}-value`} type="text" inputMode="decimal" dir="ltr" value={row.value} aria-invalid={Boolean(valueError)} aria-describedby={valueError ? `lab-${key}-value-error` : "lab-values-hint"} onChange={(event) => props.onValue(key, event.target.value)} />
                  {valueError ? <span id={`lab-${key}-value-error`} className={styles.batchError}>{valueError}</span> : null}
                </label>
                <label>الوحدة
                  <select id={`lab-${key}-unit`} dir="ltr" value={row.unit} aria-invalid={Boolean(rowErrors?.entered_unit)} aria-describedby={rowErrors?.entered_unit ? `lab-${key}-unit-error` : undefined} onChange={(event) => props.onUnit(key, event.target.value)}>
                    {test.supported_units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
                  </select>
                  {rowErrors?.entered_unit ? <span id={`lab-${key}-unit-error`} className={styles.batchError}>{rowErrors.entered_unit}</span> : null}
                </label>
              </fieldset>;
            }) : null}
          </fieldset></div>
          {draft.step === "selection" ? <div className={styles.batchSummary} data-testid="lab-selection-summary" aria-live="polite" aria-atomic="true">
            <strong>التحاليل المحددة: <bdi>{Object.keys(draft.rows).length}</bdi></strong>
          </div> : null}
          {draft.step === "values" ? <div className={styles.batchSummary} data-testid="lab-values-summary">
            <span>تاريخ التحليل: <time dateTime={draft.date}>{formatGregorianArabicDate(draft.date)}</time></span>
            <span aria-live="polite">سيتم حفظ <bdi dir="auto">{resultCountLabel(populatedCount(draft))}</bdi></span>
          </div> : null}
          <footer className={styles.batchActions}>
            <button className="btn" type="button" disabled={locked} onClick={props.onCancel}>إلغاء</button>
            {draft.step !== "date" ? <button className="btn" type="button" disabled={locked} onClick={props.onBack}>السابق</button> : null}
            {draft.step !== "values" ? <button className="btn primary" type="button" disabled={locked || (draft.step === "date" ? !draft.date : !Object.keys(draft.rows).length)} onClick={props.onNext}>التالي</button>
              : phase?.kind === "ambiguous" ? <button className="btn primary" type="button" onClick={props.onRetry}>إعادة المحاولة</button>
              : <button className="btn primary" type="button" disabled={locked || !populatedCount(draft)} onClick={props.onSave}>{phase?.kind === "submitting" ? "جارٍ الحفظ..." : "حفظ النتائج"}</button>}
          </footer>
        </> : null}
      </Dialog.Popup>
    </Dialog.Portal>
  </Dialog.Root>;
}
