"use client";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, MoreVertical } from "lucide-react";
import { createContext, useContext, FormEvent, type ReactNode, useEffect, useId, useRef, useState } from "react";
import { type AdminAccount, correctAdminProfileSex, deleteAdminAccount, editAdminAccount, resetAdminAccountPassword, retryAdminAccountCreation, retryAdminAccountDeletion, setAdminAccountEnabled } from "@/lib/api";
import { accountActionErrorMessage, accountActionSuccessMessage, type AccountAction } from "@/lib/admin-account-messages";
import { useAuth } from "./AuthProvider";
import { AdminSexCorrectionDialog } from "./AdminSexCorrectionDialog";
type ActionAccount = Pick<AdminAccount, "principal_id" | "email" | "display_name" | "status" | "profile_complete">;
type EditorMode = "edit" | "password" | "retry-create";

const editorTitles: Record<EditorMode, string> = {
  edit: "تعديل المستخدم", password: "إعادة تعيين كلمة المرور", "retry-create": "إعادة محاولة الإنشاء"
};

function DeleteDialog({ account, onClose, onDelete }: {
  account: ActionAccount;
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
    const opener = document.activeElement;
    element?.showModal();
    emailInput.current?.focus();
    return () => {
      element?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus({ preventScroll: true });
    };
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
  return <dialog ref={dialog} className="account-delete-dialog" onCancel={event => { if (busy) event.preventDefault(); }} onClose={onClose} aria-labelledby="delete-account-title" aria-describedby="delete-account-body">
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

export function FormDialog({ title, className, onClose, children, busy = false, descriptionId }: {
  busy?: boolean;
  title: string;
  className?: string;
  descriptionId?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    const opener = document.activeElement;
    element?.showModal();
    element?.querySelector("input")?.focus();
    return () => {
      element?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);
  return <dialog ref={dialog} className={`account-delete-dialog account-form-dialog ${className ?? ""}`} onCancel={event => { if (busy) event.preventDefault(); }} onClose={onClose} aria-label={title} aria-describedby={descriptionId}>
    <h2>{title}</h2>
    {children}
  </dialog>;
}

const passwordHint = "استخدم 8 أحرف على الأقل.";

export function PasswordInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
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
        {items.map(item => <button key={item.label} type="button" role="menuitem" disabled={item.disabled} className={item.danger ? "danger-menu-item" : undefined} onClick={() => { setOpen(false); buttonRef.current?.focus(); item.onSelect(); }}>{item.label}</button>)}
      </div>
    </div>}
  </div>;
}


const ActionsContext = createContext<((account: ActionAccount) => ReactNode) | null>(null);

export function AdminAccountActions({ account }: { account: ActionAccount }) {
  const renderActions = useContext(ActionsContext);
  const { account: self } = useAuth();
  if (account.principal_id === self?.principal_id) return null;
  if (!renderActions) throw new Error("AdminAccountActions requires its provider");
  return renderActions(account);
}

export function AdminAccountActionsProvider({ children, onDeleted, externalNotice, onActionStart }: { children: ReactNode; onDeleted?: () => void; externalNotice?: string; onActionStart?: () => void }) {
  const client = useQueryClient();
  const [disableTarget, setDisableTarget] = useState<ActionAccount | null>(null);
  const [disableError, setDisableError] = useState("");
  const [sexTarget, setSexTarget] = useState<ActionAccount | null>(null);
  const [sexError, setSexError] = useState("");
  async function refreshAccounts() {
    await Promise.all([client.invalidateQueries({ queryKey: ["admin-users"] }), client.invalidateQueries({ queryKey: ["admin-user"] })]);
  }
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [selected, setSelected] = useState<ActionAccount | null>(null);
  const [mode, setMode] = useState<EditorMode | null>(null);
  const [editorError, setEditorError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ActionAccount | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function execute(action: () => Promise<unknown>, kind: AccountAction, onError: (message: string) => void = setNotice): Promise<boolean> {
    onActionStart?.(); setBusy(true); setNotice("");
    try { await action(); await refreshAccounts(); setNotice(accountActionSuccessMessage(kind)); return true; }
    catch (error) {
      onError(accountActionErrorMessage(error, kind));
      await refreshAccounts();
      return false;
    }
    finally { setBusy(false); }
  }
  function select(account: ActionAccount, nextMode: EditorMode) {
    onActionStart?.(); setSelected(account); setMode(nextMode); setDisplayName(account.display_name ?? ""); setPassword(""); setEditorError(""); setNotice("");
  }
  function closeEditor() {
    setMode(null); setSelected(null); setPassword(""); setEditorError("");
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
  function rowActions(account: ActionAccount): { primary: ReactNode; menu: MenuItem[] } {
    const remove: MenuItem = { label: "حذف المستخدم نهائيًا", danger: true, onSelect: () => { onActionStart?.(); setNotice(""); setDeleteTarget(account); } };
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
          { label: "تصحيح الجنس", disabled: busy || !account.profile_complete, onSelect: () => { onActionStart?.(); setNotice(""); setSexError(""); setSexTarget(account); } },
          { label: account.status === "active" ? "تعطيل المستخدم" : "تفعيل المستخدم", disabled: busy, onSelect: () => account.status === "active" ? setDisableTarget(account) : void execute(() => setAdminAccountEnabled(account.principal_id, true), "status") },
          remove
        ]
      };
    }
    return { primary: null, menu: [remove] };
  }

  function renderActions(account: ActionAccount) {
    const actions = rowActions(account);
    return <div className="account-actions">{actions.primary}{actions.menu.length > 0 && <AccountActionsMenu name={account.display_name || account.email || ""} items={actions.menu} />}</div>;
  }
  return <ActionsContext.Provider value={renderActions}>
    {children}
    {(externalNotice || notice) && <p role="status" className="state-note account-notice">{externalNotice || notice}</p>}
    {sexTarget && <AdminSexCorrectionDialog principalId={sexTarget.principal_id} busy={busy} error={sexError}
      onClose={() => { if (!busy) setSexTarget(null); }}
      onSave={async sex => {
        setSexError("");
        if (await execute(() => correctAdminProfileSex(sexTarget.principal_id, { sex }), "edit", setSexError)) setSexTarget(null);
      }} />}
    {disableTarget && <FormDialog busy={busy} title="تعطيل المستخدم؟" onClose={() => { if (!busy) { setDisableTarget(null); setDisableError(""); } }}>
      {disableError && <p role="alert">{disableError}</p>}
      <div className="actions"><button className="btn" disabled={busy} onClick={() => { setDisableTarget(null); setDisableError(""); }}>إلغاء</button><button className="btn danger" disabled={busy} onClick={async () => {
        if (await execute(() => setAdminAccountEnabled(disableTarget.principal_id, false), "status", setDisableError)) setDisableTarget(null);
      }}>تعطيل المستخدم</button></div>
    </FormDialog>}

    {selected && mode && <FormDialog busy={busy} title={editorTitles[mode]} className="account-editor" onClose={closeEditor}>
      <form className="account-form" onSubmit={submitEditor}>
        {mode === "edit" ? <label>الاسم المعروض<input required value={displayName} onChange={event => setDisplayName(event.target.value)} /></label>
          : <PasswordInput label={mode === "password" ? "كلمة المرور الجديدة" : "كلمة المرور الأولية"} value={password} onChange={setPassword} />}
        {editorError && <p role="alert" className="account-dialog-error">{editorError}</p>}
        <div className="actions"><button type="button" className="btn" disabled={busy} onClick={closeEditor}>إلغاء</button><button type="submit" className="btn primary" disabled={busy}>{mode === "edit" ? "حفظ التغييرات" : mode === "password" ? "إعادة تعيين كلمة المرور" : "إعادة محاولة الإنشاء"}</button></div>
      </form>
    </FormDialog>}
    {deleteTarget && <DeleteDialog account={deleteTarget} onClose={() => setDeleteTarget(null)} onDelete={async confirmedEmail => {
      try {
        await deleteAdminAccount(deleteTarget.principal_id, confirmedEmail);
        setDeleteTarget(null); setNotice(accountActionSuccessMessage("delete")); onDeleted?.();
      } finally {
        await refreshAccounts();
      }
    }} />}
  </ActionsContext.Provider>;
}
