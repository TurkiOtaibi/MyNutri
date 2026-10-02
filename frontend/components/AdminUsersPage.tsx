"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, MoreVertical, Plus, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, type ReactNode, useEffect, useId, useRef, useState } from "react";
import {
  type AdminAccount, createAdminAccount, deleteAdminAccount, editAdminAccount,
  listAdminAccounts, resetAdminAccountPassword, retryAdminAccountCreation,
  retryAdminAccountDeletion, setAdminAccountEnabled
} from "@/lib/api";
import { accountActionErrorMessage, accountActionSuccessMessage, type AccountAction } from "@/lib/admin-account-messages";
import { accountStatusLabels, formatAdminDate } from "@/lib/admin-display";
import { AdminStatusBadge } from "./AdminStatusBadge";
import { useAuth } from "./AuthProvider";

type AccountStatus = AdminAccount["status"];
const filterStatuses: AccountStatus[] = ["active", "disabled", "provisioning", "deleting"];
// Only these states have read-only monitoring details; lifecycle-incomplete accounts have no data to monitor.
const monitoredStatuses: AccountStatus[] = ["active", "disabled"];

function matchesSearch(search: string, ...values: (string | null | undefined)[]) {
  const needle = search.trim().toLowerCase();
  return !needle || values.some(value => value?.toLowerCase().includes(needle));
}

type EditorMode = "edit" | "password" | "retry-create";

const editorTitles: Record<EditorMode, string> = {
  edit: "تعديل المستخدم", password: "إعادة تعيين كلمة المرور", "retry-create": "إعادة محاولة الإنشاء"
};

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
    catch (failure) { setError(accountActionErrorMessage(failure, "delete")); setBusy(false); emailInput.current?.focus(); }
  }
  return <dialog ref={dialog} className="account-delete-dialog" onClose={onClose} aria-labelledby="delete-account-title" aria-describedby="delete-account-body">
    <form onSubmit={submit}>
      <h2 id="delete-account-title">حذف المستخدم نهائيًا؟</h2>
      <p id="delete-account-body">سيُحذف حساب هذا المستخدم وجميع بياناته الخاصة نهائيًا. لا يمكن التراجع عن هذا الإجراء.</p>
      <label htmlFor="delete-account-email">اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي.</label>
      <input ref={emailInput} id="delete-account-email" type="email" dir="ltr" autoComplete="off" value={email} onChange={event => { setEmail(event.target.value); setError(""); }} aria-invalid={Boolean(error)} aria-describedby={error ? "delete-account-error" : undefined} />
      {error && <p id="delete-account-error" role="alert">{error}</p>}
      <div className="actions"><button type="button" className="btn" disabled={busy} onClick={onClose}>إلغاء</button><button className="btn danger" disabled={busy} type="submit">حذف المستخدم نهائيًا</button></div>
    </form>
  </dialog>;
}

function FormDialog({ title, className, onClose, children }: {
  title: string;
  className?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    element?.querySelector("input")?.focus();
    return () => element?.close();
  }, []);
  return <dialog ref={dialog} className={`account-delete-dialog account-form-dialog ${className ?? ""}`} onClose={onClose} aria-label={title}>
    <h2>{title}</h2>
    {children}
  </dialog>;
}

const passwordHint = "استخدم 8 أحرف على الأقل.";

function PasswordInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [visible, setVisible] = useState(false);
  const hintId = useId();
  return <div className="account-field"><label>{label}
    <span className="password-field">
      <input type={visible ? "text" : "password"} dir="ltr" autoComplete="new-password" required aria-describedby={hintId} value={value} onChange={event => onChange(event.target.value)} />
      <button type="button" onClick={() => setVisible(current => !current)} aria-label={visible ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}>
        {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
      </button>
    </span>
  </label>
  <small id={hintId} className="account-field-hint">{passwordHint}</small></div>;
}

type MenuItem = { label: string; onSelect: () => void; danger?: boolean; disabled?: boolean };

function AccountActionsMenu({ name, items }: { name: string; items: MenuItem[] }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    rootRef.current?.querySelector<HTMLButtonElement>("[role='menuitem']:not(:disabled)")?.focus();
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setOpen(false); buttonRef.current?.focus(); }
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", keydown);
    };
  }, [open]);
  return <div className="food-actions-menu" ref={rootRef}>
    <button ref={buttonRef} className="icon-button account-menu-button" type="button" aria-label={`إجراءات ${name}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(current => !current)}>
      <MoreVertical size={20} aria-hidden="true" />
    </button>
    {open && <div className="food-actions-popover">
      <div className="food-actions-list" role="menu">
        {items.map(item => <button key={item.label} type="button" role="menuitem" disabled={item.disabled} className={item.danger ? "danger-menu-item" : undefined} onClick={() => { setOpen(false); item.onSelect(); }}>{item.label}</button>)}
      </div>
    </div>}
  </div>;
}

export function AdminUsersPage() {
  const client = useQueryClient();
  const { account: self } = useAuth();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AccountStatus | "">("");
  const query = useQuery({
    queryKey: ["admin-users", "accounts", { page, search, status: statusFilter }],
    queryFn: () => listAdminAccounts({ page, search, status: statusFilter || undefined })
  });
  const showSelf = Boolean(self) && page === 1 && (!statusFilter || statusFilter === self?.status) && matchesSearch(search, self?.email, self?.display_name);
  async function refreshAccounts() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["admin-users"] }),
      client.invalidateQueries({ queryKey: ["admin-user"] })
    ]);
  }
  const [createOpen, setCreateOpen] = useState(false);
  const [createError, setCreateError] = useState("");
  const [email, setEmail] = useState("");
  const [createName, setCreateName] = useState("");
  const [createPassword, setCreatePassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [selected, setSelected] = useState<AdminAccount | null>(null);
  const [mode, setMode] = useState<EditorMode | null>(null);
  const [editorError, setEditorError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AdminAccount | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function execute(action: () => Promise<unknown>, kind: AccountAction, onError: (message: string) => void = setNotice): Promise<boolean> {
    setBusy(true); setNotice("");
    try { await action(); await refreshAccounts(); setNotice(accountActionSuccessMessage(kind)); return true; }
    catch (error) {
      onError(accountActionErrorMessage(error, kind));
      await refreshAccounts();
      return false;
    }
    finally { setBusy(false); }
  }
  function select(account: AdminAccount, nextMode: EditorMode) {
    setSelected(account); setMode(nextMode); setDisplayName(account.display_name ?? ""); setPassword(""); setEditorError(""); setNotice("");
  }
  function closeEditor() {
    setMode(null); setSelected(null); setPassword(""); setEditorError("");
  }
  async function submitCreate(event: FormEvent) {
    event.preventDefault(); setBusy(true); setNotice(""); setCreateError("");
    try {
      await createAdminAccount({ email, display_name: createName, initial_password: createPassword }, key);
      await refreshAccounts();
      setEmail(""); setCreateName(""); setCreatePassword(""); setKey(crypto.randomUUID()); setCreateOpen(false);
      setNotice(accountActionSuccessMessage("create"));
    } catch (error) {
      setCreateError(accountActionErrorMessage(error, "create"));
      await refreshAccounts();
    }
    finally { setBusy(false); }
  }
  async function submitEditor(event: FormEvent) {
    event.preventDefault();
    if (!selected || !mode) return;
    const id = selected.principal_id;
    const succeeded = mode === "edit" ? await execute(() => editAdminAccount(id, { display_name: displayName }), "edit", setEditorError)
      : mode === "password" ? await execute(() => resetAdminAccountPassword(id, password), "password", setEditorError)
        : await execute(() => retryAdminAccountCreation(id, password), "retry-create", setEditorError);
    if (succeeded) closeEditor();
  }
  function rowActions(account: AdminAccount): { primary: ReactNode; menu: MenuItem[] } {
    const remove: MenuItem = { label: "حذف المستخدم نهائيًا", danger: true, onSelect: () => setDeleteTarget(account) };
    if (account.status === "deleting") {
      return { primary: <button className="btn" disabled={busy} onClick={() => execute(() => retryAdminAccountDeletion(account.principal_id), "retry-delete")}>إعادة محاولة الحذف</button>, menu: [] };
    }
    if (account.status === "provisioning") {
      return { primary: <button className="btn" onClick={() => select(account, "retry-create")}>إعادة محاولة الإنشاء</button>, menu: [remove] };
    }
    if (account.status === "active" || account.status === "disabled") {
      return {
        primary: <button className="btn" onClick={() => select(account, "edit")}>تعديل المستخدم</button>,
        menu: [
          { label: "إعادة تعيين كلمة المرور", onSelect: () => select(account, "password") },
          { label: account.status === "active" ? "تعطيل المستخدم" : "تفعيل المستخدم", disabled: busy, onSelect: () => void execute(() => setAdminAccountEnabled(account.principal_id, account.status !== "active"), "status") },
          remove
        ]
      };
    }
    return { primary: null, menu: [remove] };
  }
  return <div className="account-management">
    <div className="page-head">
      <div><h1 className="page-title">إدارة المستخدمين</h1></div>
      <button className="btn primary" type="button" onClick={() => { setCreateError(""); setNotice(""); setCreateOpen(true); }}><Plus size={18} aria-hidden="true" />إضافة مستخدم</button>
    </div>
    <section className="section-panel" aria-label="إدارة المستخدمين">
      <div className="admin-list-controls">
        <form className="foods-search-field admin-search" onSubmit={event => { event.preventDefault(); setSearch(searchInput.trim()); setPage(1); }}>
          <Search size={18} aria-hidden="true" />
          <input aria-label="البحث بالاسم أو البريد" value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder="ابحث بالاسم أو البريد..." />
          <button className="btn" type="submit">بحث</button>
        </form>
        <select className="admin-status-filter" aria-label="حالة الحساب" value={statusFilter} onChange={event => { setStatusFilter(event.target.value as AccountStatus | ""); setPage(1); }}>
          <option value="">الكل</option>
          {filterStatuses.map(status => <option key={status} value={status}>{accountStatusLabels[status]}</option>)}
        </select>
      </div>
      {query.isPending && <p className="state-note">جارٍ تحميل المستخدمين...</p>}
      {query.isError && <p role="alert" className="state-note">تعذر تحميل المستخدمين. <button className="btn" onClick={() => query.refetch()}>إعادة المحاولة</button></p>}
      {query.data?.total === 0 && !showSelf && <p className="state-note">لا توجد نتائج.</p>}
      {showSelf && self && <article className="account-row account-self-row" key={self.principal_id}>
        <div className="account-identity">
          <span className="account-name-line"><strong>{self.display_name}</strong><span className="account-self-marker">(أنت)</span><AdminStatusBadge status={self.status} /></span>
          <span className="account-email"><bdi dir="ltr">{self.email}</bdi></span>
        </div>
      </article>}
      {query.data?.items.map(account => {
        const actions = rowActions(account);
        const name = account.display_name || account.email || "";
        const identity = <>
          <span className="account-name-line"><strong>{account.display_name}</strong><AdminStatusBadge status={account.status} /></span>
          <span className="account-email"><bdi dir="ltr">{account.email}</bdi></span>
          <span className="account-meta">تاريخ التسجيل: <time dateTime={account.created_at}>{formatAdminDate(account.created_at)}</time></span>
        </>;
        return <article className="account-row" key={account.principal_id}>
          {monitoredStatuses.includes(account.status)
            ? <Link className="account-identity" href={`/admin/users/${account.principal_id}`}>{identity}</Link>
            : <div className="account-identity">{identity}</div>}
          <div className="account-actions">
            {actions.primary}
            {actions.menu.length > 0 && <AccountActionsMenu name={name} items={actions.menu} />}
          </div>
        </article>;
      })}
      {query.data && query.data.total > query.data.page_size && <div className="actions">
        <button className="btn" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>السابق</button>
        <span>{page} / {Math.ceil(query.data.total / query.data.page_size)}</span>
        <button className="btn" disabled={page * query.data.page_size >= query.data.total} onClick={() => setPage(value => value + 1)}>التالي</button>
      </div>}
    </section>
    {notice && <p role="status" className="state-note account-notice">{notice}</p>}
    {createOpen && <FormDialog title="إضافة مستخدم" className="account-create-dialog" onClose={() => setCreateOpen(false)}>
      <form className="account-form" onSubmit={submitCreate}>
        <div className="account-field">
          <label>البريد الإلكتروني<input type="email" dir="ltr" autoComplete="off" required aria-describedby="account-email-note" value={email} onChange={event => { setEmail(event.target.value); setKey(crypto.randomUUID()); }} /></label>
          <small id="account-email-note" className="account-field-hint">لا يمكن تغيير البريد الإلكتروني بعد إنشاء المستخدم.</small>
        </div>
        <label>الاسم المعروض<input required value={createName} onChange={event => { setCreateName(event.target.value); setKey(crypto.randomUUID()); }} /></label>
        <PasswordInput label="كلمة المرور الأولية" value={createPassword} onChange={setCreatePassword} />
        {createError && <p role="alert" className="account-dialog-error">{createError}</p>}
        <div className="actions"><button type="button" className="btn" onClick={() => setCreateOpen(false)}>إلغاء</button><button className="btn primary" type="submit" disabled={busy}>إنشاء المستخدم</button></div>
      </form>
    </FormDialog>}
    {selected && mode && <FormDialog title={editorTitles[mode]} className="account-editor" onClose={closeEditor}>
      <form className="account-form" onSubmit={submitEditor}>
        {mode === "edit" ? <label>الاسم المعروض<input required value={displayName} onChange={event => setDisplayName(event.target.value)} /></label>
          : <PasswordInput label={mode === "password" ? "كلمة المرور الجديدة" : "كلمة المرور الأولية"} value={password} onChange={setPassword} />}
        {editorError && <p role="alert" className="account-dialog-error">{editorError}</p>}
        <div className="actions"><button type="button" className="btn" onClick={closeEditor}>إلغاء</button><button type="submit" className="btn primary" disabled={busy}>{mode === "edit" ? "حفظ التغييرات" : mode === "password" ? "إعادة تعيين كلمة المرور" : "إعادة محاولة الإنشاء"}</button></div>
      </form>
    </FormDialog>}
    {deleteTarget && <DeleteDialog account={deleteTarget} onClose={() => setDeleteTarget(null)} onDelete={async confirmedEmail => {
      try {
        await deleteAdminAccount(deleteTarget.principal_id, confirmedEmail);
        setDeleteTarget(null); setNotice(accountActionSuccessMessage("delete"));
      } finally {
        await refreshAccounts();
      }
    }} />}
  </div>;
}
