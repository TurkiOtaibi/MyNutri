"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { useLabBatch } from "@/components/useLabBatch";
import { LabBatchDialog } from "@/features/labs/lab-batch-dialog";
import { LabTestView } from "@/features/labs/lab-test-view";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { getLabCatalog, getLabTest } from "@/lib/api";

export function LabTestPage({ testKey }: { testKey: string }) {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id, accessToken = session?.access_token;
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const batchOpener = useRef<HTMLElement | null>(null);
  const queryPolicy = { staleTime: 0, refetchOnMount: "always" as const, refetchOnWindowFocus: "always" as const, retry: false };
  const catalog = useQuery({
    queryKey: labsQueryKeys.catalog(actorId ?? "anonymous"),
    queryFn: ({ signal }) => getLabCatalog({ accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken), ...queryPolicy,
  });
  const detail = useQuery({
    queryKey: labsQueryKeys.ownerTest(actorId ?? "anonymous", testKey),
    queryFn: ({ signal }) => getLabTest(testKey, { accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken), ...queryPolicy,
  });
  const batch = useLabBatch(actorId, { accessToken: accessToken ?? "", signal: sessionSignal }, catalog.data, detail.data?.server_today);
  return <div className={styles.labsPage}>
    <Link href="/labs">رجوع إلى التحاليل</Link>
    {detail.isPending ? <p role="status">جارٍ تحميل التحاليل...</p> : null}
    {batch.opening ? <p role="status">جارٍ تحميل تاريخ التحاليل...</p> : null}
    {batch.openError ? <p role="alert">{batch.openError}</p> : null}
    {batch.phase?.kind === "saved" ? <p role="status">{batch.phase.replayed ? "تم تأكيد نجاح عملية الحفظ السابقة." : "تم حفظ النتائج."}</p> : null}
    {batch.refreshError || detail.isError || catalog.isError ? <div role="alert">تعذر تحميل التحاليل الحالية. حاول مرة أخرى.
      <button type="button" className="btn" onClick={() => { if (catalog.isError) void catalog.refetch(); void batch.refresh(); }}>إعادة تحميل التحاليل</button>
    </div> : null}
    {detail.data ? <LabTestView detail={detail.data} selectedResultId={selectedResultId} onSelectResult={setSelectedResultId}
      ownerActions={<button className="btn primary" type="button" disabled={batch.opening || !catalog.data} onClick={() => {
        batchOpener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        void batch.open([testKey]);
      }}>إضافة نتيجة</button>} /> : null}
    <LabBatchDialog phase={batch.phase} catalog={batch.catalog} returnFocusRef={batchOpener}
      onDate={(date) => batch.dispatch({ type: "EDIT_DATE", date })}
      onPanel={(key, selected) => { if (batch.catalog) batch.dispatch({ type: "PANEL", key, selected, catalog: batch.catalog }); }}
      onIndividual={(key, selected) => { if (batch.catalog) batch.dispatch({ type: "INDIVIDUAL", key, selected, catalog: batch.catalog }); }}
      onValue={(testKey, value) => batch.dispatch({ type: "EDIT_VALUE", testKey, value })}
      onUnit={(testKey, unit) => batch.dispatch({ type: "EDIT_UNIT", testKey, unit })}
      onNext={() => batch.dispatch({ type: "NEXT" })} onBack={() => batch.dispatch({ type: "BACK" })}
      onSave={batch.save} onRetry={batch.retry} onCancel={() => batch.dispatch({ type: "CANCEL" })} />
  </div>;
}
