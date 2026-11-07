import type { QueryClient } from "@tanstack/react-query";
import type { FoodSort } from "@/lib/types";

export type FoodCatalogContext = { searchInput: string; search: string; category: string; sort: FoodSort; page: number };
const contextKey = ["food-catalog-navigation"] as const;
const emptyContext: FoodCatalogContext = { searchInput: "", search: "", category: "", sort: "name", page: 1 };

// UI navigation state only, in the existing session-scoped memory boundary.
// No Food responses, drafts, browser storage, or additional API caching.
export function readFoodCatalogContext(client: QueryClient): FoodCatalogContext {
  const context = client.getQueryData<FoodCatalogContext>(contextKey) ?? emptyContext;
  // A changed catalog can invalidate the previously accumulated mobile range.
  // Preserve its filters, but restart pagination instead of presenting missing pages.
  for (let page = 1; page <= context.page && context.page > 1; page += 1) {
    const state = client.getQueryState(["foods", "catalog", context.search, context.category, context.sort, page]);
    if (!state?.data || state.isInvalidated) return { ...context, page: 1 };
  }
  return context;
}

export function rememberFoodCatalogContext(client: QueryClient, context: FoodCatalogContext) {
  client.setQueryData(contextKey, context);
}
