"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [outcome, setOutcome] = useState<"idle" | "sent" | "failed">("idle");
  const mountedRef = useRef(true);
  const requestInFlightRef = useRef(false);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (requestInFlightRef.current) return;
    const form = event.currentTarget as HTMLFormElement;
    if (!form.reportValidity()) return;
    const normalizedEmail = email.trim();
    if (!normalizedEmail) return;
    requestInFlightRef.current = true;
    setPending(true);
    setOutcome("idle");
    try {
      const { error } = await createClient().auth.resetPasswordForEmail(normalizedEmail, {
        redirectTo: `${window.location.origin}/auth/reset-password`
      });
      if (mountedRef.current) setOutcome(error ? "failed" : "sent");
    } catch {
      if (mountedRef.current) setOutcome("failed");
    } finally {
      requestInFlightRef.current = false;
      if (mountedRef.current) setPending(false);
    }
  }
  return (
    <section className="auth-page"><form className="auth-panel" onSubmit={submit}>
      <h1>استعادة كلمة المرور</h1>
      <p>أدخل بريدك وسنرسل تعليمات الاستعادة إن كان الحساب موجودًا.</p>
      <label><span>البريد الإلكتروني</span><input type="email" dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      {outcome === "sent" ? <div className="auth-message" role="status">تحقق من بريدك لإكمال العملية.</div> : null}
      {outcome === "failed" ? <div className="auth-message" role="alert">تعذر إكمال الطلب. تحقق من الاتصال وحاول مرة أخرى.</div> : null}
      <button className="btn primary" disabled={pending} type="submit">{pending ? "جارٍ الإرسال..." : "إرسال رابط الاستعادة"}</button>
      <Link href="/auth/login">العودة لتسجيل الدخول</Link>
    </form></section>
  );
}
