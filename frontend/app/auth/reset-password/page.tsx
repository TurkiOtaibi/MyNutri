"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) return setMessage("كلمة المرور يجب أن تتكون من 8 أحرف على الأقل.");
    const { error } = await createClient().auth.updateUser({ password });
    if (error) return setMessage("انتهت صلاحية الرابط أو تعذر تحديث كلمة المرور.");
    router.replace("/diary");
  }
  return (
    <section className="auth-page"><form className="auth-panel" onSubmit={submit}>
      <h1>تعيين كلمة مرور جديدة</h1>
      <label><span>كلمة المرور الجديدة</span><input type="password" dir="ltr" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      {message ? <div className="auth-message" role="alert">{message}</div> : null}
      <button className="btn primary">حفظ كلمة المرور</button>
    </form></section>
  );
}
