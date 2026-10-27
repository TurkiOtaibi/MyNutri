"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { getAdminUser } from "@/lib/api";

export function AdminSelectedUserBanner({ principalId }: { principalId: string }) {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id, accessToken = session?.access_token;
  const user = useQuery({
    queryKey: ["labs", actorId ?? "anonymous", "admin", principalId, "identity"],
    queryFn: ({ signal }) => getAdminUser(principalId, { accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken),
    staleTime: 0, refetchOnMount: "always", refetchOnWindowFocus: "always",
  });
  if (user.isPending) return <p role="status">جارٍ تحميل بيانات المستخدم...</p>;
  if (user.isError) return <p role="alert">تعذر تحميل بيانات المستخدم. <button className="btn" type="button" onClick={() => user.refetch()}>إعادة المحاولة</button></p>;
  return <div className="selected-user-banner"><strong>عرض مستخدم آخر: {user.data.account.display_name || user.data.account.email}</strong><span>وضع قراءة فقط</span></div>;
}
