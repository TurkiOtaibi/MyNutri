"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { LabCatalogView, OwnedLabsView } from "@/features/labs/labs-overview-view";
import { filterLabs, sortLabs, toLabListItems, type LabSort } from "@/features/labs/lab-model";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { getLabCatalog, getLabs } from "@/lib/api";

export function LabsPage() {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id;
  const accessToken = session?.access_token;
  const [view, setView] = useState<"owned" | "all">("owned");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<LabSort>("newest_updated");
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
  });
  const rows = useMemo(() => {
    if (!catalog.data || !overview.data) return [];
    return sortLabs(filterLabs(toLabListItems(catalog.data, overview.data, view === "owned" ? "owned" : "all"), search, category), sort);
  }, [catalog.data, category, overview.data, search, sort, view]);

  if (catalog.isPending || overview.isPending) return <div className={styles.loading}>جارٍ تحميل التحاليل...</div>;
  if (catalog.isError || overview.isError) return <div className={styles.loading} role="alert">تعذر تحميل التحاليل. حاول مرة أخرى.</div>;
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
  };
  return <div className={styles.labsPage}>
    <header className={styles.heading}><div><h1>تحاليلك</h1><p>تابع أحدث نتيجة محفوظة لكل تحليل وفق القيم المرجعية للنظام.</p></div></header>
    <div className={styles.tabs} role="tablist" aria-label="عرض التحاليل">
      <button type="button" role="tab" aria-selected={view === "owned"} onClick={() => setView("owned")}>تحاليلك</button>
      <button type="button" role="tab" aria-selected={view === "all"} onClick={() => setView("all")}>كل التحاليل</button>
    </div>
    {view === "owned" ? <OwnedLabsView {...props} /> : <LabCatalogView {...props} />}
  </div>;
}
