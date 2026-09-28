"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ApiError, type AdminAccount, createAdminAccount, deleteAdminAccount, editAdminAccount,
  listAdminAccounts, resetAdminAccountPassword, retryAdminAccountCreation,
  retryAdminAccountDeletion, setAdminAccountEnabled
} from "@/lib/api";

const statusLabels: Record<AdminAccount["status"], string> = {
  active: "نشط", disabled: "معطّل", provisioning: "قيد الإنشاء",
  deleting: "حذف غير مكتمل", deleted: "مستخدم محذوف"
};

function message(error: unknown): string {
  if (error instanceof ApiError && error.message && !error.message.startsWith("API request")) return error.message;
  return "تعذر إكمال إنشاء المستخدم. أعد المحاولة.";
}

function DeleteDialog({ account, onClose, onDelete }: {
  account: AdminAccount;
  onClose: () => void;
  onDelete: (email: string) => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    emailInput.current?.focus();
    return () => element?.close();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (email.trim().toLowerCase() !== account.email?.toLowerCase()) {
      setError("البريد الإلكتروني المدخل لا يطابق بريد المستخدم.");
      emailInput.current?.focus();
      return;
    }
    setBusy(true);
    try { await onDelete(email.trim()); }
    catch (failure) { setError(message(failure)); setBusy(false); emailInput.current?.focus(); }
  }
  return <dialog ref={dialog} className="account-delete-dialog" onClose={onClose} aria-labelledby="delete-account-title" aria-describedby="delete-account-body">
    <form onSubmit={submit}>
      <h2 id="delete-account-title">حذف المستخدم نهائيًا؟</h2>
      <p id="delete-account-body">سيُحذف حساب هذا المستخدم وجميع بياناته الخاصة نهائيًا. لا يمكن التراجع عن هذا الإجراء.</p>
      <label htmlFor="delete-account-email">اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.</label>
      <input ref={emailInput} id="delete-account-email" type="email" dir="ltr" autoComplete="off" value={email} onChange={event => { setEmail(event.target.value); setError(""); }} aria-invalid={Boolean(error)} aria-describedby={error ? "delete-account-error" : undefined} />
      {error && <p id="delete-account-error" role="alert">{error}</p>}
      <div className="actions"><button type="button" className="btn" disabled={busy} onClick={onClose}>إلغاء</button><button className="btn primary" disabled={busy} type="submit">حذف المستخدم نهائيًا</button></div>
    </form>
  </dialog>;
}

export function AdminAccountsPage() {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["admin-accounts", page], queryFn: () => listAdminAccounts(page) });
  const [email, setEmail] = useState("");
  const [createName, setCreateName] = useState("");
  const [createPassword, setCreatePassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [selected, setSelected] = useState<AdminAccount | null>(null);
  const [mode, setMode] = useState<"edit" | "password" | "retry-create" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminAccount | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function execute(action: () => Promise<unknown>, success: string) {
    setBusy(true); setNotice("");
    try { await action(); await client.invalidateQueries({ queryKey: ["admin-accounts"] }); setNotice(success); setMode(null); setSelected(null); setPassword(""); }
    catch (error) { setNotice(message(error)); }
    finally { setBusy(false); }
  }
  function select(account: AdminAccount, nextMode: "edit" | "password" | "retry-create") {
    setSelected(account); setMode(nextMode); setDisplayName(account.display_name ?? ""); setPassword(""); setNotice("");
  }
  return <div className="account-management">
    <div className="page-head"><div><h1 className="page-title">إدارة المستخدمين</h1></div></div>
    <section className="section-panel">
      <h2>إضافة مستخدم</h2>
      <form className="account-form" onSubmit={async event => {
        event.preventDefault(); setBusy(true); setNotice("");
        try {
          await createAdminAccount({ email, display_name: createName, initial_password: createPassword }, key);
          await client.invalidateQueries({ queryKey: ["admin-accounts"] });
          setEmail(""); setCreateName(""); setCreatePassword(""); setKey(crypto.randomUUID()); setNotice("تم إنشاء المستخدم.");
        } catch (error) { setNotice(message(error)); }
        finally { setBusy(false); }
      }}>
        <label>البريد الإلكتروني<input type="email" dir="ltr" autoComplete="off" required value={email} onChange={event => setEmail(event.target.value)} /></label>
        <label>الاسم المعروض<input required value={createName} onChange={event => setCreateName(event.target.value)} /></label>
        <label>كلمة المرور الأولية<input type="password" autoComplete="new-password" required value={createPassword} onChange={event => setCreatePassword(event.target.value)} /></label>
        <button className="btn primary" type="submit" disabled={busy}>إنشاء المستخدم</button>
      </form>
    </section>
    {notice && <p role="status" className="state-note">{notice}</p>}
    <section className="section-panel" aria-label="إدارة المستخدمين">
      {query.isPending && <p className="state-note">جارٍ تحميل المستخدمين...</p>}
      {query.isError && <p role="alert" className="state-note">تعذر تحميل المستخدمين. <button className="btn" onClick={() => query.refetch()}>إعادة المحاولة</button></p>}
      {query.data?.items.map(account => <article className="admin-user-row account-row" key={account.principal_id}>
        <div><strong>{account.display_name}</strong><span dir="ltr">{account.email}</span></div>
        <div><span>{statusLabels[account.status]}</span>
          <div className="actions">
            {account.status === "provisioning" && <button className="btn" onClick={() => select(account, "retry-create")}>إعادة محاولة الإنشاء</button>}
            {account.status === "deleting" && <button className="btn" disabled={busy} onClick={() => execute(() => retryAdminAccountDeletion(account.principal_id), "تم حذف المستخدم نهائيًا.")}>إعادة محاولة الحذف</button>}
            {(account.status === "active" || account.status === "disabled") && <>
              <button className="btn" onClick={() => select(account, "edit")}>تعديل المستخدم</button>
              <button className="btn" onClick={() => select(account, "password")}>إعادة تعيين كلمة المرور</button>
              <button className="btn" disabled={busy} onClick={() => execute(() => setAdminAccountEnabled(account.principal_id, account.status !== "active"), "تم تحديث حالة المستخدم.")}>{account.status === "active" ? "تعطيل المستخدم" : "تفعيل المستخدم"}</button>
            </>}
            {account.status !== "deleting" && <button className="btn" onClick={() => setDeleteTarget(account)}>حذف المستخدم نهائيًا</button>}
          </div>
        </div>
      </article>)}
      {query.data && query.data.total > query.data.page_size && <div className="actions">
        <button className="btn" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>السابق</button>
        <span>{page} / {Math.ceil(query.data.total / query.data.page_size)}</span>
        <button className="btn" disabled={page * query.data.page_size >= query.data.total} onClick={() => setPage(value => value + 1)}>التالي</button>
      </div>}
    </section>
    {selected && mode && <section className="section-panel account-editor" aria-label={mode === "edit" ? "تعديل المستخدم" : mode === "password" ? "إعادة تعيين كلمة المرور" : "إعادة محاولة الإنشاء"}>
      <h2>{mode === "edit" ? "تعديل المستخدم" : mode === "password" ? "إعادة تعيين كلمة المرور" : "إعادة محاولة الإنشاء"}</h2>
      <form className="account-form" onSubmit={event => {
        event.preventDefault();
        if (mode === "edit") void execute(() => editAdminAccount(selected.principal_id, { display_name: displayName }), "تم حفظ تغييرات المستخدم.");
        else if (mode === "password") void execute(() => resetAdminAccountPassword(selected.principal_id, password), "تم حفظ تغييرات المستخدم.");
        else void execute(() => retryAdminAccountCreation(selected.principal_id, password), "تم إنشاء المستخدم.");
      }}>
        {mode === "edit" ? <label>الاسم المعروض<input required value={displayName} onChange={event => setDisplayName(event.target.value)} /></label>
          : <label>{mode === "password" ? "كلمة المرور الجديدة" : "كلمة المرور الأولية"}<input type="password" autoComplete="new-password" required value={password} onChange={event => setPassword(event.target.value)} /></label>}
        <div className="actions"><button type="button" className="btn" onClick={() => { setMode(null); setSelected(null); }}>إلغاء</button><button type="submit" className="btn primary" disabled={busy}>{mode === "edit" ? "حفظ التغييرات" : mode === "password" ? "إعادة تعيين كلمة المرور" : "إعادة محاولة الإنشاء"}</button></div>
      </form>
    </section>}
    {deleteTarget && <DeleteDialog account={deleteTarget} onClose={() => setDeleteTarget(null)} onDelete={async confirmedEmail => {
      await deleteAdminAccount(deleteTarget.principal_id, confirmedEmail);
      setDeleteTarget(null); setNotice("تم حذف المستخدم نهائيًا.");
      await client.invalidateQueries({ queryKey: ["admin-accounts"] });
    }} />}
  </div>;
}
