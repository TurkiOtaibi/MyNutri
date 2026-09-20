const root = (actorId: string) => ["labs", actorId] as const;

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
