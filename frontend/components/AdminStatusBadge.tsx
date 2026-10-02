import { accountStatusLabels } from "@/lib/admin-display";
import type { AdminAccount } from "@/lib/api";

export function AdminStatusBadge({ status }: { status: AdminAccount["status"] }) {
  return <span className={`account-status-badge account-status-${status}`}>{accountStatusLabels[status]}</span>;
}
