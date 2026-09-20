"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { LabTestView } from "@/features/labs/lab-test-view";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { getAdminLabTest } from "@/lib/api";

export function AdminUserLabTestPage({ principalId, testKey }: { principalId: string; testKey: string }) {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id, accessToken = session?.access_token;
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: labsQueryKeys.adminTest(actorId ?? "anonymous", principalId, testKey),
    queryFn: ({ signal }) => getAdminLabTest(principalId, testKey, { accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken), staleTime: 0, refetchOnMount: "always", refetchOnWindowFocus: "always", retry: false,
  });
  return <div className={styles.labsPage}>
    <Link href={`/admin/users/${encodeURIComponent(principalId)}/labs`}>رجوع إلى تحاليل المستخدم</Link>
    {detail.isPending ? <p role="status">جارٍ تحميل تحاليل المستخدم...</p> : null}
    {detail.isError ? <div role="alert">تعذر تحميل تحاليل المستخدم.<button type="button" className="btn" onClick={() => void detail.refetch()}>إعادة تحميل التحاليل</button></div> : null}
    {detail.data ? <LabTestView detail={{ ...detail.data, read_only: true }} selectedResultId={selectedResultId} onSelectResult={setSelectedResultId} /> : null}
  </div>;
}
