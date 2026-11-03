"use client";

import { Eye, EyeOff, LogIn, Salad } from "lucide-react";
import { FormEvent, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";
import { useAuth } from "./AuthProvider";

const GENERIC_ERROR = "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى.";
const USERNAME_REQUIRED = "أدخل اسم المستخدم.";
const PASSWORD_SHORT = "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.";

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
  const usernameRef = useRef<HTMLInputElement>(null);
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
    if (!username.trim()) {
      setMessage(USERNAME_REQUIRED);
      usernameRef.current?.focus();
      return;
    }
    if (Array.from(password).length < 8) {
      setMessage(PASSWORD_SHORT);
      passwordRef.current?.focus();
      return;
    }
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

  const reason = search.get("reason");
  const sessionNotice = reason === "expired" ? "انتهت جلستك. سجّل الدخول مرة أخرى."
    : reason === "disabled" ? "حسابك موقوف. تواصل مع المشرف." : null;
  const showSessionNotice = Boolean(sessionNotice && !message);

  return (
    <section className="auth-page login-page" aria-labelledby="login-title">
      <form ref={formRef} className="auth-panel" onSubmit={submit} noValidate>
        <header className="login-heading">
          <div className="auth-brand"><span className="brand-mark"><Salad size={21} aria-hidden="true" /></span><bdi>myNutri</bdi></div>
          <h1 id="login-title">تسجيل الدخول</h1>
          <p>ادخل إلى بياناتك الغذائية بأمان.</p>
        </header>
        {showSessionNotice ? <div className="auth-message" id="session-notice" role="status">{sessionNotice}</div> : null}
        <label>
          <span>اسم المستخدم</span>
          <input ref={usernameRef} value={username} onChange={(e) => {
            setUsername(e.target.value);
            if (message === USERNAME_REQUIRED) setMessage("");
          }} aria-invalid={message === USERNAME_REQUIRED || undefined} aria-describedby={message === USERNAME_REQUIRED ? "login-message" : showSessionNotice ? "session-notice" : undefined} type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={32} required dir="ltr" />
        </label>
        <div className="login-password">
          <label htmlFor="login-password">كلمة المرور</label>
          <div className="password-field" dir="ltr">
            <input id="login-password" ref={passwordRef} value={password} onChange={(e) => {
              setPassword(e.target.value);
              if (message === PASSWORD_SHORT) setMessage("");
            }} aria-invalid={message === PASSWORD_SHORT || undefined} aria-describedby={message === PASSWORD_SHORT ? "login-message" : undefined} type={visible ? "text" : "password"} autoComplete="current-password" required dir="ltr" />
            <button type="button" onClick={() => setVisible((value) => !value)} aria-label={visible ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}>
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>
        {message ? <div className="auth-message" id="login-message" role="status">{message}</div> : null}
        <button className="btn primary" disabled={pending} type="submit">
          <LogIn size={18} />
          {pending ? "جارٍ الإرسال..." : "دخول"}
        </button>
        <p className="login-help">ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف.</p>
      </form>
    </section>
  );
}
