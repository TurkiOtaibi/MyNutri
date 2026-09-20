"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Dialog } from "@base-ui-components/react/dialog";
import { AlertDialog } from "@base-ui-components/react/alert-dialog";
import type { LabCatalogTest, LabFieldError, LabResultPatch, LabResultResponse } from "@/lib/types";
import { enteredTriplet, freezeResultPatch, resultErrorTarget } from "./lab-result-model";
import styles from "./labs.module.css";

type DialogFocus = { returnFocus?: () => HTMLElement | false | null; isCurrent?: () => boolean };
type LabEditDialogProps = DialogFocus & {
  result: LabResultResponse; test: LabCatalogTest; serverToday: string;
  onSubmit: (payload: LabResultPatch) => Promise<void>; onCancel: () => void;
  errors: LabFieldError[]; pending: boolean;
  recovery?: ReactNode; onReread?: () => void; writeBlocked?: boolean;
};

export function LabEditDialog(props: LabEditDialogProps) {
  const { result, test, pending, errors, isCurrent } = props;
  // Parent keys by opened session/id: query refreshes never replace a live draft.
  const [draft, setDraft] = useState(() => enteredTriplet(result));
  const submitted = useRef(false);
  const firstError = errors[0];
  useEffect(() => {
    if (!firstError) return;
    const frame = requestAnimationFrame(() => {
      if (isCurrent && !isCurrent()) return;
      const field = document.getElementById(resultErrorTarget(firstError));
      field?.focus({ preventScroll: true });
      field?.scrollIntoView({ block: "nearest" });
    });
    return () => cancelAnimationFrame(frame);
  }, [firstError, isCurrent]);
  const locked = pending || props.writeBlocked;
  const fieldError = (id: string) => errors.find(error => resultErrorTarget(error) === id)?.msg;
  const valueError = fieldError("lab-edit-value"), unitError = fieldError("lab-edit-unit"), dateError = fieldError("lab-edit-date");
  return <Dialog.Root open disablePointerDismissal={pending} onOpenChange={(open, event) => {
    if (!open) { if (pending || submitted.current) event.cancel(); else props.onCancel(); }
  }}>
    <Dialog.Portal><Dialog.Backdrop className={styles.batchBackdrop} />
      <Dialog.Popup className={styles.batchDialog} dir="rtl" initialFocus={() => props.isCurrent?.() === false ? false : document.getElementById("lab-edit-value")} finalFocus={props.returnFocus}>
        <Dialog.Title>تعديل النتيجة</Dialog.Title>
        <Dialog.Description>{test.name_ar} <bdi dir="ltr">{test.abbreviation ?? test.name_en}</bdi></Dialog.Description>
        <form noValidate onSubmit={event => {
          event.preventDefault();
          if (locked || submitted.current || props.isCurrent?.() === false) return;
          submitted.current = true;
          void props.onSubmit(freezeResultPatch(draft)).finally(() => { if (isCurrent?.() !== false) submitted.current = false; });
        }}>
          {errors.length ? <div id="lab-edit-errors" role="alert" tabIndex={-1} className={styles.batchError}>{errors.map((error, index) => <p key={index}>{error.msg}</p>)}</div> : null}
          {props.recovery}
          <fieldset className={styles.batchFields} disabled={locked}>
            <legend className="sr-only">بيانات النتيجة</legend>
            <label>القيمة<input id="lab-edit-value" type="text" inputMode="decimal" dir="ltr" value={draft.entered_value} aria-invalid={Boolean(valueError)} aria-describedby={valueError ? "lab-edit-value-error" : undefined} onChange={event => setDraft({ ...draft, entered_value: event.target.value })} />
              {valueError ? <span id="lab-edit-value-error" className={styles.batchError}>{valueError}</span> : null}</label>
            <label>الوحدة<select id="lab-edit-unit" dir="ltr" value={draft.entered_unit} aria-invalid={Boolean(unitError)} aria-describedby={unitError ? "lab-edit-unit-error" : undefined} onChange={event => setDraft({ ...draft, entered_unit: event.target.value })}>
              {test.supported_units.map(unit => <option key={unit} value={unit}>{unit}</option>)}
            </select>{unitError ? <span id="lab-edit-unit-error" className={styles.batchError}>{unitError}</span> : null}</label>
            <label>تاريخ التحليل<input id="lab-edit-date" type="date" dir="ltr" value={draft.test_date} aria-invalid={Boolean(dateError)} aria-describedby={dateError ? "lab-edit-date-error" : "lab-edit-today"} onChange={event => setDraft({ ...draft, test_date: event.target.value })} />
              {dateError ? <span id="lab-edit-date-error" className={styles.batchError}>{dateError}</span> : null}</label>
            <p id="lab-edit-today">تاريخ اليوم: <bdi dir="ltr">{props.serverToday}</bdi></p>
          </fieldset>
          <footer className={styles.batchActions}>
            <button type="button" className="btn" disabled={pending} onClick={() => { if (!submitted.current) props.onCancel(); }}>{props.writeBlocked ? "إغلاق" : "إلغاء"}</button>
            {props.onReread ? <button type="button" className="btn" disabled={pending} onClick={props.onReread}>إعادة قراءة النتيجة</button> : null}
            {!props.writeBlocked ? <button type="submit" className="btn primary" disabled={pending}>{pending ? "جارٍ الحفظ..." : "حفظ التعديل"}</button> : null}
          </footer>
        </form>
      </Dialog.Popup>
    </Dialog.Portal>
  </Dialog.Root>;
}

type LabDeleteDialogProps = DialogFocus & {
  result: LabResultResponse; test: LabCatalogTest; onConfirm: () => Promise<void>; onCancel: () => void;
  pending: boolean; error?: string; onReread?: () => void; retryAllowed?: boolean;
};
export function LabDeleteDialog(props: LabDeleteDialogProps) {
  const submitted = useRef(false);
  return <AlertDialog.Root open onOpenChange={(open, event) => {
    if (!open) { if (props.pending || submitted.current) event.cancel(); else props.onCancel(); }
  }}>
    <AlertDialog.Portal><AlertDialog.Backdrop className={styles.batchBackdrop} />
      <AlertDialog.Popup className={styles.batchDialog} dir="rtl" initialFocus={() => props.isCurrent?.() === false ? false : document.getElementById("lab-delete-cancel")} finalFocus={props.returnFocus}>
        <AlertDialog.Title>حذف النتيجة</AlertDialog.Title>
        <AlertDialog.Description>هل تريد حذف نتيجة {props.test.name_ar} <bdi dir="ltr">{props.test.abbreviation ?? props.test.name_en}</bdi> بتاريخ <time dateTime={props.result.test_date} dir="ltr">{props.result.test_date}</time>؟</AlertDialog.Description>
        {props.error ? <p role="alert">{props.error}</p> : null}
        <footer className={styles.batchActions}>
          <button id="lab-delete-cancel" type="button" className="btn" disabled={props.pending} onClick={() => { if (!submitted.current) props.onCancel(); }}>إلغاء</button>
          {props.onReread ? <button type="button" className="btn" disabled={props.pending} onClick={props.onReread}>إعادة قراءة النتيجة</button> : null}
          <button type="button" className="btn primary" disabled={props.pending || props.retryAllowed === false} onClick={() => {
            if (props.pending || submitted.current || props.retryAllowed === false || props.isCurrent?.() === false) return;
            submitted.current = true;
            void props.onConfirm().finally(() => { if (props.isCurrent?.() !== false) submitted.current = false; });
          }}>{props.pending ? "جارٍ الحذف..." : "حذف النتيجة"}</button>
        </footer>
      </AlertDialog.Popup>
    </AlertDialog.Portal>
  </AlertDialog.Root>;
}
