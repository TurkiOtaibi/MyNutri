"use client";

import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { useLabBatch } from "@/components/useLabBatch";
import { LabBatchDialog } from "@/features/labs/lab-batch-dialog";
import { LabCatalogView, LabsViewTabs, OwnedLabsView } from "@/features/labs/labs-overview-view";
import { filterLabs, sortLabs, toLabListItems, type LabSort, type LabsView } from "@/features/labs/lab-model";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { getLabCatalog, getLabs } from "@/lib/api";

export function LabsPage() {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id;
  const accessToken = session?.access_token;
  const [view, setView] = useState<LabsView>("owned");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<LabSort>("newest_updated");
  const [viewOwner, setViewOwner] = useState(actorId);
  if (viewOwner !== actorId) {
    setViewOwner(actorId);
    setView("owned"); setSearch(""); setCategory(null); setSort("newest_updated");
  }
  const batchOpener = useRef<HTMLElement | null>(null);
  const queryPolicy = { staleTime: 0, refetchOnMount: "always" as const, refetchOnWindowFocus: "always" as const };
  const catalog = useQuery({
    queryKey: labsQueryKeys.catalog(actorId ?? "anonymous"),
    queryFn: ({ signal }) => getLabCatalog({ accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken),
    ...queryPolicy,
  });
  const overview = useQuery({
    queryKey: labsQueryKeys.ownerOverview(actorId ?? "anonymous"),
    queryFn: ({ signal }) => getLabs({ accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken),
    ...queryPolicy,
    retry: false,
  });
  const batch = useLabBatch(actorId, { accessToken: accessToken ?? "", signal: sessionSignal }, catalog.data, overview.data?.server_today);
  function openBatch(keys: string[] = []) {
    batchOpener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    void batch.open(keys);
  }
  const rows = useMemo(() => {
    if (!catalog.data || !overview.data) return [];
    return sortLabs(filterLabs(toLabListItems(catalog.data, overview.data, view === "owned" ? "owned" : "all"), search, category), sort);
  }, [catalog.data, category, overview.data, search, sort, view]);

  if (catalog.isPending || overview.isPending) return <div className={styles.loading}>جارٍ تحميل التحاليل...</div>;
  if (!catalog.data || !overview.data) return <div className={styles.loading} role="alert">تعذر تحميل التحاليل. حاول مرة أخرى.</div>;
  const props = {
    catalog: catalog.data,
    rows,
    eligibility: overview.data.eligibility,
    search,
    category,
    sort,
    readOnly: overview.data.read_only,
    onSearchChange: setSearch,
    onCategoryChange: setCategory,
    onSortChange: setSort,
    onAddTest: (testKey: string) => openBatch([testKey]),
    detailHref: (testKey: string) => `/labs/${encodeURIComponent(testKey)}`,
  };
  return <div className={styles.labsPage}>
    <header className={styles.heading}><div><h1>تحاليلك</h1><p>تابع أحدث نتيجة محفوظة لكل تحليل وفق القيم المرجعية للنظام.</p></div>
      {!overview.data.read_only && overview.data.eligibility.allowed ? <button className="btn primary" type="button" disabled={batch.opening} onClick={() => openBatch()}>إضافة نتائج</button> : null}
    </header>
    {batch.opening ? <p role="status">جارٍ تحميل تاريخ التحاليل...</p> : null}
    {batch.openError ? <p role="alert">{batch.openError}</p> : null}
    {batch.phase?.kind === "saved" ? <p role="status">{batch.phase.replayed ? "تم تأكيد نجاح عملية الحفظ السابقة." : "تم حفظ النتائج."}</p> : null}
    {batch.refreshError || overview.isError || catalog.isError ? <div role="alert">تعذر تحميل التحاليل الحالية. حاول مرة أخرى.
      <button className="btn" type="button" onClick={() => { if (catalog.isError) void catalog.refetch(); void batch.refresh(); }}>إعادة تحميل التحاليل</button>
    </div> : null}
    <LabsViewTabs view={view} onViewChange={setView} />
    <div id="labs-panel-owned" role="tabpanel" aria-labelledby="labs-tab-owned" tabIndex={view === "owned" ? 0 : -1} hidden={view !== "owned"}>
      {view === "owned" ? <OwnedLabsView {...props} /> : null}
    </div>
    <div id="labs-panel-all" role="tabpanel" aria-labelledby="labs-tab-all" tabIndex={view === "all" ? 0 : -1} hidden={view !== "all"}>
      {view === "all" ? <LabCatalogView {...props} /> : null}
    </div>
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
