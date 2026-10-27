// Own URL transitions must not overwrite a newer draft typed while they were pending.
export function reconcileAdminSearch(search: string, draft: string, pending: string[]) {
  const index = pending.indexOf(search);
  return index >= 0
    ? { draft, pending: pending.slice(index + 1) }
    : { draft: search, pending: [] as string[] };
}
