"use client";

import { Eye, EyeOff, LogIn } from "lucide-react";
import Link from "next/link";
import { FormEvent, useLayoutEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { createClient } from "@/lib/supabase/client";
import { normalizePostLoginPath } from "@/lib/auth-return-path";

const GENERIC_ERROR = "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى.";

export function AuthShell() {
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const pendingFocusHandledRef = useRef(false);
  const focusPasswordAfterFailureRef = useRef(false);

  useLayoutEffect(() => {
    if (!pending) {
      pendingFocusHandledRef.current = false;
      return;
    }
    if (pendingFocusHandledRef.current) return;

    const form = formRef.current;
    const passwordInput = passwordRef.current;
    const active = document.activeElement;
    const activeIsUsable =
      active instanceof HTMLElement &&
      form?.contains(active) === true &&
      active.isConnected &&
      !active.matches(":disabled") &&
      active.closest("[inert], [aria-hidden='true']") === null;

    pendingFocusHandledRef.current = true;
    if (!activeIsUsable && passwordInput?.isConnected && !passwordInput.disabled) {
      passwordInput.focus({ preventScroll: true });
    }
  }, [pending]);

  useLayoutEffect(() => {
    if (!focusPasswordAfterFailureRef.current || pending || !message) return;

    focusPasswordAfterFailureRef.current = false;
    const passwordInput = passwordRef.current;
    if (passwordInput?.isConnected && !passwordInput.disabled) {
      passwordInput.focus({ preventScroll: true });
    }
  }, [message, pending]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    if (!email.trim() || password.length < 8) {
      setMessage("أدخل بريدًا صحيحًا وكلمة مرور من 8 أحرف على الأقل.");
      return;
    }
    setPending(true);
    const supabase = createClient();
    const result = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    if (result.error) {
      focusPasswordAfterFailureRef.current = true;
      setPending(false);
      setMessage(GENERIC_ERROR);
      return;
    }
    setPending(false);
    router.replace(normalizePostLoginPath(search.get("next"), window.location.origin));
    router.refresh();
  }

  return (
    <section className="auth-page">
      <form ref={formRef} className="auth-panel" onSubmit={submit} noValidate>
        <div className="auth-brand">myNutri</div>
        <h1>تسجيل الدخول</h1>
        <p>ادخل إلى بياناتك الغذائية بأمان.</p>
        <label>
          <span>البريد الإلكتروني</span>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" inputMode="email" autoComplete="email" required dir="ltr" />
        </label>
        <label>
          <span>كلمة المرور</span>
          <div className="password-field">
            <input ref={passwordRef} value={password} onChange={(e) => setPassword(e.target.value)} type={visible ? "text" : "password"} autoComplete="current-password" required dir="ltr" />
            <button type="button" onClick={() => setVisible((value) => !value)} aria-label={visible ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}>
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </label>
        {message ? <div className="auth-message" role="status">{message}</div> : null}
        <button className="btn primary" disabled={pending} type="submit">
          <LogIn size={18} />
          {pending ? "جارٍ الإرسال..." : "دخول"}
        </button>
        <Link href="/auth/forgot-password">نسيت كلمة المرور؟</Link>
      </form>
    </section>
  );
}
