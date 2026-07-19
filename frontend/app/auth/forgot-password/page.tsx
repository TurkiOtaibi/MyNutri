"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    await createClient().auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/auth/reset-password`
    });
    setPending(false);
    setSent(true);
  }
  return (
    <section className="auth-page"><form className="auth-panel" onSubmit={submit}>
      <h1>استعادة كلمة المرور</h1>
      <p>أدخل بريدك وسنرسل تعليمات الاستعادة إن كان الحساب موجودًا.</p>
      <label><span>البريد الإلكتروني</span><input type="email" dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      {sent ? <div className="auth-message" role="status">تحقق من بريدك لإكمال العملية.</div> : null}
      <button className="btn primary" disabled={pending}>{pending ? "جارٍ الإرسال..." : "إرسال رابط الاستعادة"}</button>
      <Link href="/auth/login">العودة لتسجيل الدخول</Link>
    </form></section>
  );
}
