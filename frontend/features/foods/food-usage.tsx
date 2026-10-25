import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { getFoodUsage } from "@/lib/api";

export function useFoodUsage(foodId?: string) {
  const { account, session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  return useQuery({
    queryKey: ["food-usage", session?.user.id, foodId],
    queryFn: ({ signal }) => getFoodUsage(foodId!, session?.access_token, AbortSignal.any([signal, sessionSignal])),
    enabled: Boolean(foodId) && account?.role === "admin",
    retry: false,
    gcTime: 0,
  });
}

export function FoodUsageNotice({ usage, deletion = false }: { usage: ReturnType<typeof useFoodUsage>; deletion?: boolean }) {
  if (usage.isPending) return <p role="status">جارٍ تحميل أعداد السجلات المتأثرة…</p>;
  if (usage.isError) return <p role="alert">تعذر تحميل أعداد السجلات المتأثرة. يمكنك المتابعة دون الأعداد.</p>;
  if (deletion) return <p role="status">عدد سجلات اليوميات: {usage.data.diary_entries} · عدد المستخدمين المتأثرين: {usage.data.users}</p>;
  return usage.data.diary_entries > 0 ? <p role="status">هذا الطعام مسجّل في {usage.data.diary_entries} يوميات، والتعديل سيغيّر مجاميعها السابقة.</p> : null;
}
