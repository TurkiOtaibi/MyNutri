"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Plus, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  type AdminAccount, createAdminAccount, listAdminAccounts
} from "@/lib/api";
import { accountActionErrorMessage, accountActionSuccessMessage } from "@/lib/admin-account-messages";
import { accountStatusLabels, formatAdminDate, adminResultsLabel } from "@/lib/admin-display";
import { reconcileAdminSearch } from "@/lib/admin-search";
import { AdminStatusBadge } from "./AdminStatusBadge";
import { useAuth } from "./AuthProvider";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AdminAccountActions, AdminAccountActionsProvider, FormDialog, PasswordInput } from "./AdminAccountActions";

type AccountStatus = AdminAccount["status"];
const filterStatuses = ["active", "disabled", "provisioning", "deleting"] as const;
// Only these states have read-only monitoring details; lifecycle-incomplete accounts have no data to monitor.
const monitoredStatuses: AccountStatus[] = ["active", "disabled"];

export function AdminUsersPage() {
  const client = useQueryClient();
  const { account: self } = useAuth();
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const rawPage = Number(params.get("page") || 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const search = params.get("search") ?? "";
  const rawStatus = params.get("status") as AccountStatus;
  const statusFilter = filterStatuses.some(status => status === rawStatus) ? rawStatus : "";
  const [searchInput, setSearchInput] = useState(search);
  const [lastUrlSearch, setLastUrlSearch] = useState(search);
  const [pendingSearches, setPendingSearches] = useState<string[]>([]);
  if (lastUrlSearch !== search) {
    setLastUrlSearch(search);
    const next = reconcileAdminSearch(search, searchInput, pendingSearches);
    setPendingSearches(next.pending);
    setSearchInput(next.draft);
  }
  const updateUrl = useCallback((next: { search?: string; status?: string; page?: number }) => {
    const values = { search, status: statusFilter, page, ...next };
    const query = new URLSearchParams();
    if (values.search) query.set("search", values.search);
    if (values.status) query.set("status", values.status);
    if (values.page > 1) query.set("page", String(values.page));
    if (values.search !== search) setPendingSearches(previous => [...previous, values.search]);
    router.replace(`${pathname}${query.size ? `?${query}` : ""}`, { scroll: false });
  }, [search, statusFilter, page, router, pathname]);
  useEffect(() => {
    const resetPending = () => setPendingSearches([]);
    window.addEventListener("popstate", resetPending);
    return () => window.removeEventListener("popstate", resetPending);
  }, []);
  useEffect(() => {
    if (searchInput.trim() === search) return;
    const timer = window.setTimeout(() => updateUrl({ search: searchInput.trim(), page: 1 }), 300);
    return () => window.clearTimeout(timer);
    // URL state is authoritative; typing only delays the search transition.
  }, [searchInput, search, updateUrl]);
  const returnQuery = params.toString();
  const query = useQuery({
    queryKey: ["admin-users", "accounts", { page, search, status: statusFilter }],
    queryFn: () => listAdminAccounts({ page, search, status: statusFilter || undefined })
  });
  const showSelf = Boolean(self) && page === 1 && !statusFilter && !searchInput.trim() && !search;
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
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  function closeCreate() {
    if (busy) return;
    setCreateOpen(false); setEmail(""); setCreateName(""); setCreatePassword(""); setCreateError(""); setKey(crypto.randomUUID());
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
  return <AdminAccountActionsProvider externalNotice={notice} onActionStart={() => setNotice("")}><div className="account-management">
    <div className="page-head">
      <div><h1 className="page-title">إدارة المستخدمين</h1></div>
      <button className="btn primary" type="button" onClick={() => { setCreateError(""); setNotice(""); setCreateOpen(true); }}><Plus size={18} aria-hidden="true" />إضافة مستخدم</button>
    </div>
    {query.data?.counts && <div className="admin-account-counts" aria-live="polite">
      {filterStatuses.map(status => ["active", "disabled"].includes(status) || (query.data!.counts[status] ?? 0) > 0 ? <span key={status} className={`account-status-badge account-status-${status}`}>
        {accountStatusLabels[status]}: <bdi dir="ltr">{query.data!.counts[status]}</bdi>{["provisioning", "deleting"].includes(status) ? " · تنتظر إعادة المحاولة" : ""}
      </span> : null)}
    </div>}
    <section className="section-panel" aria-label="إدارة المستخدمين">
      <div className="admin-list-controls">
        <form className="foods-search-field admin-search" onSubmit={event => { event.preventDefault(); updateUrl({ search: searchInput.trim(), page: 1 }); }}>
          <Search size={18} aria-hidden="true" />
          <input aria-label="البحث بالاسم أو البريد" value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder="ابحث بالاسم أو البريد..." />
          <button className="btn" type="submit">بحث</button>
          {searchInput && <button className="btn" type="button" onClick={() => { setSearchInput(""); updateUrl({ search: "", page: 1 }); }}>مسح البحث</button>}
        </form>
        <select className="admin-status-filter" aria-label="حالة الحساب" value={statusFilter} onChange={event => { updateUrl({ search: searchInput.trim(), status: event.target.value, page: 1 }); }}>
          <option value="">الكل</option>
          {filterStatuses.map(status => <option key={status} value={status}>{accountStatusLabels[status]}</option>)}
        </select>
      </div>
      {query.isPending && <p className="state-note">جارٍ تحميل المستخدمين...</p>}
      {query.isError && <p role="alert" className="state-note">تعذر تحميل المستخدمين. <button className="btn" onClick={() => query.refetch()}>إعادة المحاولة</button></p>}
      {query.data && <p aria-live="polite" className="admin-results-count">{adminResultsLabel(page, query.data.page_size, query.data.total)}</p>}
      {query.data?.total === 0 && !showSelf && <p className="state-note">لا توجد نتائج.</p>}
      {showSelf && self && <article className="account-row account-self-row" key={self.principal_id}>
        <div className="account-identity">
          <span className="account-name-line"><strong>{self.display_name}</strong><span className="account-self-marker">(أنت)</span><AdminStatusBadge status={self.status} /></span>
          <span className="account-email"><bdi dir="ltr">{self.email}</bdi></span>
        </div>
      </article>}
      {query.data?.items.map(account => {
        const identity = <>
          <span className="account-name-line"><strong>{account.display_name}</strong><AdminStatusBadge status={account.status} /></span>
          <span className="account-email"><bdi dir="ltr">{account.email}</bdi></span>
          {account.status === "disabled" && account.disabled_at && <span>معطّل منذ <time dateTime={account.disabled_at}>{formatAdminDate(account.disabled_at)}</time></span>}
          {["provisioning", "deleting"].includes(account.status) && <span className="account-meta">أعد المحاولة، أو احذف الحساب وأنشئه من جديد</span>}
          <span className="account-meta">تاريخ التسجيل: <time dateTime={account.created_at}>{formatAdminDate(account.created_at)}</time></span>
        </>;
        return <article className="account-row" key={account.principal_id}>
          {monitoredStatuses.includes(account.status)
            ? <Link className="account-identity" href={`/admin/users/${account.principal_id}${returnQuery ? `?${returnQuery}` : ""}`}>{identity}<ChevronLeft className="account-open-arrow" size={20} aria-hidden="true" /></Link>
            : <div className="account-identity">{identity}</div>}
          <AdminAccountActions account={account} />
        </article>;
      })}
      {query.data && query.data.total > query.data.page_size && <div className="actions">
        <button className="btn" disabled={page <= 1} onClick={() => updateUrl({ page: page - 1 })}>السابق</button>
        <span>{page} / {Math.ceil(query.data.total / query.data.page_size)}</span>
        <button className="btn" disabled={page * query.data.page_size >= query.data.total} onClick={() => updateUrl({ page: page + 1 })}>التالي</button>
      </div>}
    </section>
    {createOpen && <FormDialog title="إضافة مستخدم" className="account-create-dialog" busy={busy} onClose={closeCreate}>
      <form className="account-form" onSubmit={submitCreate}>
        <div className="account-field">
          <label>البريد الإلكتروني<input type="email" dir="ltr" autoComplete="off" required aria-describedby="account-email-note" value={email} onChange={event => { setEmail(event.target.value); setKey(crypto.randomUUID()); }} /></label>
          <small id="account-email-note" className="account-field-hint">لا يمكن تغيير البريد الإلكتروني بعد إنشاء المستخدم.</small>
        </div>
        <label>الاسم المعروض<input required value={createName} onChange={event => { setCreateName(event.target.value); setKey(crypto.randomUUID()); }} /></label>
        <PasswordInput label="كلمة المرور الأولية" value={createPassword} onChange={setCreatePassword} />
        {createError && <p role="alert" className="account-dialog-error">{createError}</p>}
        <div className="actions"><button type="button" className="btn" disabled={busy} onClick={closeCreate}>إلغاء</button><button className="btn primary" type="submit" disabled={busy}>إنشاء المستخدم</button></div>
      </form>
    </FormDialog>}
  </div></AdminAccountActionsProvider>;
}
