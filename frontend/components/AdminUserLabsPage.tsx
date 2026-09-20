"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { OwnedLabsView } from "@/features/labs/labs-overview-view";
import { filterLabs, sortLabs, toLabListItems, type LabSort } from "@/features/labs/lab-model";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { getAdminLabs, getLabCatalog } from "@/lib/api";

export function AdminUserLabsPage({ principalId }: { principalId: string }) {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id;
  const accessToken = session?.access_token;
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
    queryKey: labsQueryKeys.adminOverview(actorId ?? "anonymous", principalId),
    queryFn: ({ signal }) => getAdminLabs(principalId, { accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken),
    ...queryPolicy,
  });
  const rows = useMemo(() => {
    if (!catalog.data || !overview.data) return [];
    return sortLabs(filterLabs(toLabListItems(catalog.data, overview.data, "owned"), search, category), sort);
  }, [catalog.data, category, overview.data, search, sort]);

  if (catalog.isPending || overview.isPending) return <div className={styles.loading}>جارٍ تحميل تحاليل المستخدم...</div>;
  if (catalog.isError || overview.isError) return <div className={styles.loading} role="alert">تعذر تحميل تحاليل المستخدم.</div>;
  return <div className={styles.labsPage}>
    <header className={styles.heading}><div><h1>تحاليل المستخدم</h1><p>أحدث النتائج المحفوظة للمراقبة الإدارية.</p></div><Link className="btn" href={`/admin/users/${encodeURIComponent(principalId)}`}>رجوع</Link></header>
    <OwnedLabsView
      catalog={catalog.data}
      rows={rows}
      eligibility={overview.data.eligibility}
      search={search}
      category={category}
      sort={sort}
      readOnly={overview.data.read_only}
      detailHref={(testKey) => `/admin/users/${encodeURIComponent(principalId)}/labs/${encodeURIComponent(testKey)}`}
      onSearchChange={setSearch}
      onCategoryChange={setCategory}
      onSortChange={setSort}
    />
  </div>;
}
