import type { QueryClient } from "@tanstack/react-query";

export const FOOD_DELETED_NOTICE = "تم حذف الطعام نهائيًا.";
const noticeKey = (principalId: string) => ["food-delete-notice", principalId] as const;

export function rememberFoodDeletion(client: QueryClient, principalId: string) {
  client.setQueryData(noticeKey(principalId), FOOD_DELETED_NOTICE);
}

export function readFoodDeletionNotice(client: QueryClient, principalId: string | undefined): string {
  return principalId ? client.getQueryData<string>(noticeKey(principalId)) ?? "" : "";
}

export function clearFoodDeletionNotice(client: QueryClient, principalId: string | undefined) {
  if (principalId) client.removeQueries({ queryKey: noticeKey(principalId), exact: true });
}
