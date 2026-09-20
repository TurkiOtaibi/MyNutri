const root = (actorId: string) => ["labs", actorId] as const;

export function isOtherAdminSubjectQuery(
  queryKey: readonly unknown[],
  actorId: string,
  principalId: string,
): boolean {
  return queryKey[0] === "labs"
    && queryKey[1] === actorId
    && queryKey[2] === "admin"
    && typeof queryKey[3] === "string"
    && queryKey[3] !== principalId;
}

export const labsQueryKeys = {
  catalog: (actorId: string) => [...root(actorId), "catalog"] as const,
  ownerRoot: (actorId: string) => [...root(actorId), "owner"] as const,
  ownerOverview: (actorId: string) => [...root(actorId), "owner", "overview"] as const,
  ownerTest: (actorId: string, testKey: string) => (
    [...root(actorId), "owner", "test", testKey] as const
  ),
  adminOverview: (actorId: string, principalId: string) => (
    [...root(actorId), "admin", principalId, "overview"] as const
  ),
  adminTest: (actorId: string, principalId: string, testKey: string) => (
    [...root(actorId), "admin", principalId, "test", testKey] as const
  ),
};
