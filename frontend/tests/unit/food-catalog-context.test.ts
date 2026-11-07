import { describe, expect, it } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { readFoodCatalogContext, rememberFoodCatalogContext } from "@/features/foods/food-catalog-context";

describe("catalog navigation memory", () => {
  it("retains search, filter, sort and page when the catalog remounts", () => {
    const client = new QueryClient();
    const context = { searchInput: " أرز ", search: "أرز", category: "grains", sort: "recent" as const, page: 3 };
    for (let page = 1; page <= 3; page += 1) client.setQueryData(["foods", "catalog", "أرز", "grains", "recent", page], { items: [] });
    rememberFoodCatalogContext(client, context);
    expect(readFoodCatalogContext(client)).toEqual(context);
    client.clear();
  });

  it("restarts an invalidated accumulated range while retaining search and filters", async () => {
    const client = new QueryClient();
    rememberFoodCatalogContext(client, { searchInput: "أرز", search: "أرز", category: "grains", sort: "recent", page: 2 });
    for (let page = 1; page <= 2; page += 1) client.setQueryData(["foods", "catalog", "أرز", "grains", "recent", page], { items: [] });
    await client.invalidateQueries({ queryKey: ["foods"] });
    expect(readFoodCatalogContext(client)).toEqual({ searchInput: "أرز", search: "أرز", category: "grains", sort: "recent", page: 1 });
    client.clear();
  });

  it("does not carry context across session boundaries or after cleanup", () => {
    const previous = new QueryClient();
    rememberFoodCatalogContext(previous, { searchInput: "أرز", search: "أرز", category: "grains", sort: "protein", page: 4 });
    const current = new QueryClient();
    expect(readFoodCatalogContext(current)).toEqual({ searchInput: "", search: "", category: "", sort: "name", page: 1 });
    previous.clear();
    expect(readFoodCatalogContext(previous).page).toBe(1);
    current.clear();
  });
});
