"use client";

import { Eye, EyeOff } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";

export function ForcedPasswordChange({ onSave, onSignOut }: {
  onSave: (password: string) => Promise<void>; onSignOut: () => Promise<void>;
}) {
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
  const [message, setMessage] = useState("");
  const field = useRef<HTMLInputElement>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    if (Array.from(password).length < 8) {
      setMessage("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل."); field.current?.focus(); return;
    }
    submitting.current = true; setPending(true); setMessage("");
    try { await onSave(password); setPassword(""); }
    catch (error) {
      setMessage(error instanceof ApiError ? "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى." : "تعذر الاتصال بالخادم. حاول مرة أخرى.");
      field.current?.focus();
    } finally { submitting.current = false; setPending(false); }
  }
  return <main className="auth-page" dir="rtl"><form className="auth-panel" onSubmit={submit} noValidate>
    <h1>تغيير كلمة المرور</h1>
    <label><span>كلمة المرور الجديدة</span><div className="password-field">
      <input ref={field} value={password} onChange={event => setPassword(event.target.value)} type={visible ? "text" : "password"}
        autoComplete="new-password" dir="ltr" aria-describedby="initial-password-hint" />
      <button type="button" onClick={() => setVisible(value => !value)} aria-label={visible ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}>
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div></label>
    <p id="initial-password-hint">استخدم 8 أحرف على الأقل.</p>
    {message ? <p role="alert">{message}</p> : null}
    <button className="btn primary" disabled={pending} type="submit">حفظ كلمة المرور</button>
    <button className="btn" disabled={pending} type="button" onClick={() => void onSignOut()}>تسجيل الخروج</button>
  </form></main>;
}
