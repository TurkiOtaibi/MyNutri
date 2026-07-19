"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAdminUsers } from "@/lib/api";

export function AdminUsersPage() {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["admin-users", search, page], queryFn: () => listAdminUsers(search, page) });
  return <>
    <div className="page-head"><div><h1 className="page-title">المستخدمون</h1><p className="page-kicker">عرض بيانات المستخدمين للمتابعة دون تعديلها.</p></div></div>
    <section className="section-panel">
      <form className="foods-search-field" onSubmit={(event) => { event.preventDefault(); setSearch(input.trim()); setPage(1); }}><Search size={18}/><input aria-label="البحث بالاسم أو البريد" value={input} onChange={(e) => setInput(e.target.value)} placeholder="ابحث بالاسم أو البريد..."/><button className="btn" type="submit">بحث</button></form>
      {query.isPending ? <div className="state-note">جارٍ تحميل المستخدمين...</div> : null}
      {query.isError ? <div className="state-note" role="alert">تعذر تحميل المستخدمين. <button className="btn" onClick={() => query.refetch()}>إعادة المحاولة</button></div> : null}
      {query.data?.total === 0 ? <div className="state-note">لا توجد نتائج.</div> : null}
      {query.data?.items.map((user) => <Link className="admin-user-row" href={`/admin/users/${user.principal_id}`} key={user.principal_id}>
        <div><strong>{user.display_name || "بدون اسم"}</strong><span dir="ltr">{user.email || "بريد غير متوفر"}</span></div>
        <div><span>{user.status === "active" ? "نشط" : "معطل"}</span><span>{user.profile_complete ? "الملف مكتمل" : "الملف غير مكتمل"}</span><time>{new Date(user.created_at).toLocaleDateString("ar-SA")}</time></div>
      </Link>)}
      {query.data && query.data.total_pages > 1 ? <div className="actions"><button className="btn" disabled={page <= 1} onClick={() => setPage((v) => v - 1)}>السابق</button><span>{page} / {query.data.total_pages}</span><button className="btn" disabled={page >= query.data.total_pages} onClick={() => setPage((v) => v + 1)}>التالي</button></div> : null}
    </section>
  </>;
}
