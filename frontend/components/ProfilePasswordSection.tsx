"use client";

import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, changeAccountPassword } from "@/lib/api";

const SHORT_PASSWORD = "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل.";
const WRONG_PASSWORD = "كلمة المرور الحالية غير صحيحة.";

export function useProfilePassword(subjectId: string | null, accessToken: string | undefined) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: "current" | "new" | null; message: string } | null>(null);
  const [success, setSuccess] = useState(false);
  const currentRef = useRef<HTMLInputElement>(null);
  const newRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLParagraphElement>(null);
  const sequence = useRef(0);
  const submitting = useRef(false);
  const subject = useRef(subjectId);

  function discard() {
    sequence.current += 1;
    submitting.current = false;
    setCurrentPassword("");
    setNewPassword("");
    setPending(false);
    setError(null);
    setSuccess(false);
  }

  useLayoutEffect(() => {
    if (subject.current === subjectId) return;
    subject.current = subjectId;
    discard();
  }, [subjectId]);

  useEffect(() => () => { sequence.current += 1; }, []);
  useEffect(() => {
    if (error?.field === "current") currentRef.current?.focus();
    else if (error?.field === "new") newRef.current?.focus();
    else if (error || success) resultRef.current?.focus();
  }, [error, success]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current || !accessToken) return;
    setSuccess(false);
    if (!currentPassword) {
      setError({ field: "current", message: WRONG_PASSWORD });
      return;
    }
    if (Array.from(newPassword).length < 8) {
      setError({ field: "new", message: SHORT_PASSWORD });
      return;
    }
    const attempt = ++sequence.current;
    submitting.current = true;
    setPending(true);
    setError(null);
    try {
      await changeAccountPassword({ current_password: currentPassword, new_password: newPassword }, accessToken);
      if (attempt !== sequence.current) return;
      setCurrentPassword("");
      setNewPassword("");
      setSuccess(true);
    } catch (cause) {
      if (attempt !== sequence.current) return;
      if (cause instanceof ApiError && cause.code === "CURRENT_PASSWORD_INCORRECT") {
        setError({ field: "current", message: WRONG_PASSWORD });
      } else if (cause instanceof ApiError && cause.message === SHORT_PASSWORD) {
        setError({ field: "new", message: SHORT_PASSWORD });
      } else {
        setError({ field: null, message: "تعذر حفظ التغييرات" });
      }
    } finally {
      if (attempt === sequence.current) {
        submitting.current = false;
        setPending(false);
      }
    }
  }

  return {
    currentPassword, newPassword, pending, error, success, currentRef, newRef, resultRef,
    dirty: Boolean(currentPassword || newPassword), discard, submit,
    updateCurrent(value: string) { setCurrentPassword(value); setError(null); setSuccess(false); },
    updateNew(value: string) { setNewPassword(value); setError(null); setSuccess(false); },
  };
}

export function ProfilePasswordSection({ password }: { password: ReturnType<typeof useProfilePassword> }) {
  const { currentPassword, newPassword, pending, error, success, currentRef, newRef, resultRef, submit, updateCurrent, updateNew } = password;
  return (
    <section className="card" dir="rtl" aria-labelledby="profile-password-title">
      <h2 id="profile-password-title">تغيير كلمة المرور</h2>
      <form className="account-form" onSubmit={(event) => void submit(event)} noValidate aria-busy={pending}>
        <div className="field">
          <label htmlFor="profile-current-password">كلمة المرور الحالية</label>
          <input id="profile-current-password" ref={currentRef} className="input" type="password" autoComplete="current-password"
            required disabled={pending} value={currentPassword}
            aria-invalid={error?.field === "current"} aria-describedby={error?.field === "current" ? "profile-password-result" : undefined}
            onChange={(event) => updateCurrent(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="profile-new-password">كلمة المرور الجديدة</label>
          <input id="profile-new-password" ref={newRef} className="input" type="password" autoComplete="new-password"
            required disabled={pending} value={newPassword}
            aria-invalid={error?.field === "new"} aria-describedby={`profile-password-hint${error?.field === "new" ? " profile-password-result" : ""}`}
            onChange={(event) => updateNew(event.target.value)} />
          <p id="profile-password-hint">استخدم 8 أحرف على الأقل.</p>
        </div>
        {error || success ? (
          <p id="profile-password-result" ref={resultRef} tabIndex={-1} role={error ? "alert" : "status"} className={error ? "field-error" : undefined}>
            {error?.message ?? "تم تغيير كلمة المرور."}
          </p>
        ) : null}
        <div className="actions"><button className="btn primary" type="submit" disabled={pending}>تغيير كلمة المرور</button></div>
      </form>
    </section>
  );
}
