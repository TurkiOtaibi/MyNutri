import type {
  LabCatalogResponse,
  LabCatalogTest,
  LabOverviewResponse,
  LabResultResponse,
} from "@/lib/types";

export type LabListItem = {
  test_key: string;
  test: LabCatalogTest;
  latest: LabResultResponse | null;
  last_updated_at: string | null;
};

export type LabSort = "newest_updated" | "oldest_updated" | "name_asc" | "name_desc" | "category";

const arabicCollator = new Intl.Collator("ar");

function normalizeSearch(value: string): string {
  return value
    .normalize("NFKC")
    .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]/g, "")
    .replace(/[إأآٱ]/g, "ا")
    .toLocaleLowerCase()
    .trim();
}

function compareKey(left: LabListItem, right: LabListItem): number {
  return left.test_key.localeCompare(right.test_key);
}

function compareName(left: LabListItem, right: LabListItem): number {
  return arabicCollator.compare(left.test.name_ar, right.test.name_ar);
}

export function toLabListItems(
  catalog: LabCatalogResponse,
  overview: LabOverviewResponse,
  view: "owned" | "all",
): LabListItem[] {
  const categoryOrder = new Map(catalog.categories.map((category) => [category.key, category.order]));
  const activity = new Map(overview.items.map((item) => [item.test_key, item]));
  const orderedTests = catalog.tests
    .map((test, index) => ({ test, index }))
    .sort((left, right) => (
      (categoryOrder.get(left.test.primary_category) ?? Number.MAX_SAFE_INTEGER)
      - (categoryOrder.get(right.test.primary_category) ?? Number.MAX_SAFE_INTEGER)
      || left.index - right.index
    ));

  return orderedTests.flatMap(({ test }) => {
    const item = activity.get(test.test_key);
    if (view === "owned" && !item) return [];
    return [{
      test_key: test.test_key,
      test,
      latest: item?.latest ?? null,
      last_updated_at: item?.last_updated_at ?? null,
    }];
  });
}

export function filterLabs(
  items: LabListItem[],
  search: string,
  category: string | null,
): LabListItem[] {
  const needle = normalizeSearch(search);
  return items.filter((item) => {
    if (category && item.test.primary_category !== category) return false;
    if (!needle) return true;
    return [item.test.name_ar, item.test.name_en, item.test.abbreviation]
      .some((value) => value !== null && normalizeSearch(value).includes(needle));
  });
}

export function sortLabs(items: LabListItem[], sort: LabSort): LabListItem[] {
  const indexed = items.map((item, index) => ({ item, index }));
  indexed.sort((left, right) => {
    if (sort === "category") return left.index - right.index;
    if (sort === "name_asc" || sort === "name_desc") {
      const compared = compareName(left.item, right.item);
      return (sort === "name_asc" ? compared : -compared)
        || compareKey(left.item, right.item)
        || left.index - right.index;
    }
    const leftUpdated = left.item.last_updated_at;
    const rightUpdated = right.item.last_updated_at;
    if (leftUpdated === null) return rightUpdated === null ? left.index - right.index : 1;
    if (rightUpdated === null) return -1;
    const compared = leftUpdated.localeCompare(rightUpdated);
    return (sort === "newest_updated" ? -compared : compared) || left.index - right.index;
  });
  return indexed.map(({ item }) => item);
}
