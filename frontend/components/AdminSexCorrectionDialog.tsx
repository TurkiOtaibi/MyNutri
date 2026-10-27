"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { getAdminUser } from "@/lib/api";
import type { Sex } from "@/lib/types";
import { FormDialog } from "./AdminAccountActions";

export function AdminSexCorrectionDialog({ principalId, busy, error, onClose, onSave }: {
  principalId: string;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: (sex: Sex) => Promise<void>;
}) {
  const profile = useQuery({ queryKey: ["admin-profile-sex", principalId], queryFn: () => getAdminUser(principalId), retry: false, staleTime: 0, gcTime: 0 });
  const [selected, setSelected] = useState<Sex | null>(null);
  const warningId = useId();
  const errorRef = useRef<HTMLParagraphElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const current = profile.data?.profile?.sex;
  useEffect(() => { if (current && !profile.isError) inputRef.current?.focus(); }, [current, profile.isError]);
  useEffect(() => { if (error && !busy) errorRef.current?.focus(); }, [error, busy]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (current) await onSave(selected ?? current);
  }
  return <FormDialog busy={busy} title="تصحيح الجنس" className="account-sex-dialog" descriptionId={warningId} onClose={onClose}>
    <p id={warningId}>تصحيح الجنس يغيّر حساب الأهداف وتقييم نتائج التحاليل.</p>
    {profile.isPending ? <p role="status">جارٍ تحميل بيانات المستخدم...</p>
      : profile.isError ? <p role="alert">تعذر تحميل بيانات المستخدم.</p>
        : !current ? <p role="alert">لا يمكن تصحيح الجنس قبل حفظ الملف الشخصي للمستخدم.</p>
          : <form onSubmit={submit}>
            <p>الجنس الحالي: {current === "male" ? "ذكر" : "أنثى"}</p>
            <fieldset disabled={busy}><legend>الجنس</legend>
              {([ ["male", "ذكر"], ["female", "أنثى"] ] as const).map(([value, label]) => <label key={value}>
                <input ref={value === current ? inputRef : undefined} type="radio" name="corrected-sex" value={value} checked={(selected ?? current) === value} onChange={() => setSelected(value)} />{label}
              </label>)}
            </fieldset>
            {error && <p ref={errorRef} tabIndex={-1} role="alert">{error}</p>}
            <div className="actions"><button type="button" className="btn" disabled={busy} onClick={onClose}>إلغاء</button><button className="btn primary" type="submit" disabled={busy}>حفظ التغييرات</button></div>
          </form>}
    {(!current || profile.isError || profile.isPending) && <button className="btn" type="button" onClick={onClose}>إلغاء</button>}
  </FormDialog>;
}
