"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Users } from "lucide-react";
import Link from "next/link";
import { accountStatusLabels } from "@/lib/admin-display";
import { type AdminAccount, listAdminAccounts } from "@/lib/api";

// Lifecycle states that wait on an Admin retry.
const attentionStatuses: AdminAccount["status"][] = ["provisioning", "deleting"];

function AttentionCount({ status }: { status: AdminAccount["status"] }) {
  const query = useQuery({
    queryKey: ["admin-users", "accounts", { page: 1, search: "", status }],
    queryFn: () => listAdminAccounts({ status })
  });
  if (!query.data?.total) return null;
  return <span className={`account-status-badge account-status-${status}`}>
    {accountStatusLabels[status]}: <bdi dir="ltr">{query.data.total}</bdi>
  </span>;
}

export function AdminHomePage() {
  return <>
    <div className="page-head"><div><h1 className="page-title">الإدارة</h1><p className="page-kicker">إدارة الحسابات ومتابعة بيانات التغذية.</p></div></div>
    <div className="admin-home-grid">
      <Link className="section-panel admin-home-link" href="/admin/users">
        <Users aria-hidden="true" />
        <strong>إدارة المستخدمين</strong>
        <span className="admin-home-attention">{attentionStatuses.map(status => <AttentionCount key={status} status={status} />)}</span>
        <ChevronLeft className="admin-home-chevron" size={20} aria-hidden="true" />
      </Link>
    </div>
  </>;
}
