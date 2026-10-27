"use client";

import { Eye, EyeOff, LogIn } from "lucide-react";
import { FormEvent, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";
import { useAuth } from "./AuthProvider";

const GENERIC_ERROR = "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى.";

export function AuthShell() {
  const { signIn } = useAuth();
  const search = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
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
    if (submitting.current) return;
    setMessage("");
    if (!username.trim()) { setMessage("أدخل اسم المستخدم."); return; }
    if (Array.from(password).length < 8) { setMessage("كلمة المرور قصيرة. استخدم 8 أحرف على الأقل."); return; }
    setPending(true);
    submitting.current = true;
    try {
      await signIn(username.trim(), password, search.get("next") ?? "/diary");
      setPassword("");
    } catch (error) {
      focusPasswordAfterFailureRef.current = true;
      const code = error instanceof ApiError ? error.code : undefined;
      setMessage(code === "ACCOUNT_DISABLED" ? "حسابك موقوف. تواصل مع المشرف."
        : code === "USER_LOCKED" ? "تم قفل الحساب بعد 5 محاولات دخول فاشلة. تواصل مع المشرف لفتحه."
        : code === "ADMIN_LOCKED" ? "تم قفل الحساب بعد 5 محاولات دخول فاشلة. حاول مرة أخرى بعد 30 دقيقة."
        : error instanceof ApiError ? GENERIC_ERROR : "تعذر الاتصال بالخادم. حاول مرة أخرى.");
    } finally { submitting.current = false; setPending(false); }
  }

  return (
    <section className="auth-page">
      <form ref={formRef} className="auth-panel" onSubmit={submit} noValidate>
        <div className="auth-brand">myNutri</div>
        <h1>تسجيل الدخول</h1>
        <p>ادخل إلى بياناتك الغذائية بأمان.</p>
        <label>
          <span>اسم المستخدم</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={32} required dir="ltr" />
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
        {message || search.get("reason") ? <div className="auth-message" role="status">{message || (search.get("reason") === "disabled" ? "حسابك موقوف. تواصل مع المشرف." : "انتهت جلستك. سجّل الدخول مرة أخرى.")}</div> : null}
        <button className="btn primary" disabled={pending} type="submit">
          <LogIn size={18} />
          {pending ? "جارٍ الإرسال..." : "دخول"}
        </button>
        <p>ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف.</p>
      </form>
    </section>
  );
}
