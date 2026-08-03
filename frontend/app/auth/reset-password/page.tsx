"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/components/AuthProvider";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { recoveryStatus } = useAuth();
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const updateInFlightRef = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (recoveryStatus !== "ready" || updateInFlightRef.current) return;
    if (password.length < 8) return setMessage("كلمة المرور يجب أن تتكون من 8 أحرف على الأقل.");
    updateInFlightRef.current = true;
    setPending(true);
    setMessage("");
    try {
      const { error } = await createClient().auth.updateUser({ password });
      if (error) {
        setMessage("تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.");
        return;
      }
      router.replace("/diary");
    } catch {
      setMessage("تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.");
    } finally {
      updateInFlightRef.current = false;
      setPending(false);
    }
  }

  if (recoveryStatus === "checking") {
    return <section className="auth-page"><div className="auth-panel" role="status">جارٍ التحميل...</div></section>;
  }
  if (recoveryStatus === "invalid") {
    return <section className="auth-page"><div className="auth-panel"><h1>تعيين كلمة مرور جديدة</h1><div className="auth-message" role="alert">انتهت صلاحية الرابط أو تعذر تحديث كلمة المرور.</div></div></section>;
  }
  return (
    <section className="auth-page"><form className="auth-panel" onSubmit={submit}>
      <h1>تعيين كلمة مرور جديدة</h1>
      <label><span>كلمة المرور الجديدة</span><input type="password" dir="ltr" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required /></label>
      {message ? <div className="auth-message" role="alert">{message}</div> : null}
      <button className="btn primary" disabled={pending} type="submit">{pending ? "جارٍ الإرسال..." : "حفظ كلمة المرور"}</button>
    </form></section>
  );
}
