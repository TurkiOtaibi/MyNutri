import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";

import {
  createLabResults,
  deleteLabResult,
  getAdminLabs,
  getAdminLabTest,
  getLabCatalog,
  getLabs,
  getLabTest,
  updateLabResult,
  ApiError,
} from "@/lib/api";
import { filterLabs, nextLabsView, sortLabs, toLabListItems } from "@/features/labs/lab-model";
import { isOtherAdminSubjectQuery, labsQueryKeys } from "@/features/labs/lab-query-keys";
import { LabsViewTabs, OwnedLabsView } from "@/features/labs/labs-overview-view";
import type { LabOverviewResponse } from "@/lib/types";
import {
  catalogFixture,
  createFixture,
  historyFixture,
  overviewItem,
  resultFixture,
  zoneFixture,
} from "./fixtures/labs";

afterEach(() => vi.unstubAllGlobals());

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });
}

describe("Labs transport", () => {
  it("sends bearer, no-store, and the supplied signal on every read scope", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(jsonResponse(catalogFixture))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}));
    vi.stubGlobal("fetch", fetch);
    const signal = new AbortController().signal;
    const auth = { accessToken: "token-a", signal };

    await getLabCatalog(auth);
    await getLabs(auth);
    await getLabTest("Hb A1c/خاص", auth);
    await getAdminLabs("subject/a", auth);
    await getAdminLabTest("subject/a", "Hb A1c/خاص", auth);

    expect(fetch.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/labs/catalog",
      "/labs",
      "/labs/tests/Hb%20A1c%2F%D8%AE%D8%A7%D8%B5",
      "/admin/users/subject%2Fa/labs",
      "/admin/users/subject%2Fa/labs/tests/Hb%20A1c%2F%D8%AE%D8%A7%D8%B5",
    ]);
    for (const [, init] of fetch.mock.calls) {
      expect(init).toMatchObject({ cache: "no-store", signal });
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token-a");
    }
  });

  it("sends owner-derived mutations and reports idempotent replay headers", async () => {
    const updated = resultFixture("hba1c", "2026-09-18", "2026-09-19");
    const fetch = vi.fn()
      .mockResolvedValueOnce(jsonResponse(
        { receipt_version: 1, result_ids: [updated.id] },
        { headers: { "Idempotent-Replayed": "true" } },
      ))
      .mockResolvedValueOnce(jsonResponse(updated))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    const signal = new AbortController().signal;
    const auth = { accessToken: "token-a", signal };

    await expect(createLabResults(createFixture, "idem-1", auth)).resolves.toEqual({
      receipt: { receipt_version: 1, result_ids: [updated.id] },
      replayed: true,
    });
    await expect(updateLabResult(updated.id, {
      test_date: "2026-09-18",
      entered_value: "5.270",
      entered_unit: "%",
    }, auth)).resolves.toEqual(updated);
    await expect(deleteLabResult(updated.id, auth)).resolves.toBeUndefined();

    const [, createInit] = fetch.mock.calls[0];
    expect(createInit).toMatchObject({ method: "POST", cache: "no-store", signal });
    expect(new Headers(createInit?.headers).get("Idempotency-Key")).toBe("idem-1");
    expect(JSON.parse(String(createInit?.body))).toEqual(createFixture);
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: "PATCH", cache: "no-store", signal });
    expect(fetch.mock.calls[2][1]).toMatchObject({ method: "DELETE", cache: "no-store", signal });
    for (const [, init] of fetch.mock.calls) {
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token-a");
    }
    expect(JSON.stringify(fetch.mock.calls)).not.toContain("principal_id");
  });

  it("preserves the existing ApiError contract for structured Labs errors", async () => {
    const detail = [{
      loc: ["body", "results", 0, "entered_value"],
      field: "entered_value",
      test_key: "hba1c",
      code: "LAB_VALUE_INVALID",
      msg: "قيمة غير صالحة",
      type: "value_error",
    }];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(
      { detail },
      { status: 422 },
    )));

    const request = getLabs({ accessToken: "token-a", signal: new AbortController().signal });
    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({ status: 422, detail });
  });
});

describe("Labs query keys", () => {
  it("isolates every key by actor and admin keys by selected subject", () => {
    expect(labsQueryKeys.catalog("actor-a")).toEqual(["labs", "actor-a", "catalog"]);
    expect(labsQueryKeys.ownerRoot("actor-a")).toEqual(["labs", "actor-a", "owner"]);
    expect(labsQueryKeys.ownerOverview("actor-a")).toEqual(["labs", "actor-a", "owner", "overview"]);
    expect(labsQueryKeys.ownerTest("actor-a", "hba1c")).toEqual(["labs", "actor-a", "owner", "test", "hba1c"]);
    expect(labsQueryKeys.adminOverview("admin-a", "subject-a")).toEqual(["labs", "admin-a", "admin", "subject-a", "overview"]);
    expect(labsQueryKeys.adminTest("admin-a", "subject-a", "hba1c")).toEqual(["labs", "admin-a", "admin", "subject-a", "test", "hba1c"]);
    expect(labsQueryKeys.ownerOverview("actor-b")).not.toEqual(labsQueryKeys.ownerOverview("actor-a"));
    expect(labsQueryKeys.adminOverview("admin-a", "subject-b")).not.toEqual(labsQueryKeys.adminOverview("admin-a", "subject-a"));
  });

  it("removes only another selected user's Labs keys while preserving current and owner queries", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(labsQueryKeys.adminOverview("admin-a", "subject-a"), "old overview");
    queryClient.setQueryData(labsQueryKeys.adminTest("admin-a", "subject-a", "hba1c"), "old detail");
    queryClient.setQueryData(labsQueryKeys.adminOverview("admin-a", "subject-b"), "current overview");
    queryClient.setQueryData(labsQueryKeys.adminTest("admin-a", "subject-b", "hba1c"), "current detail");
    queryClient.setQueryData(labsQueryKeys.ownerOverview("admin-a"), "owner overview");

    queryClient.removeQueries({
      predicate: (query) => isOtherAdminSubjectQuery(query.queryKey, "admin-a", "subject-b"),
    });

    expect(queryClient.getQueryData(labsQueryKeys.adminOverview("admin-a", "subject-a"))).toBeUndefined();
    expect(queryClient.getQueryData(labsQueryKeys.adminTest("admin-a", "subject-a", "hba1c"))).toBeUndefined();
    expect(queryClient.getQueryData(labsQueryKeys.adminOverview("admin-a", "subject-b"))).toBe("current overview");
    expect(queryClient.getQueryData(labsQueryKeys.adminTest("admin-a", "subject-b", "hba1c"))).toBe("current detail");
    expect(queryClient.getQueryData(labsQueryKeys.ownerOverview("admin-a"))).toBe("owner overview");
  });
});

describe("Labs list model", () => {
  const overview: LabOverviewResponse = {
    items: [
      { test_key: "hba1c", latest: resultFixture("hba1c", "2026-09-01", "2026-09-02"), last_updated_at: "2026-09-02T08:00:00Z" },
      { test_key: "ferritin", latest: resultFixture("ferritin", "2026-01-01", "2026-09-19"), last_updated_at: "2026-09-19T08:00:00Z" },
    ],
    eligibility: { allowed: true, reason: null },
    server_today: "2026-09-20",
    medical_rules_version: "labs-v1",
    read_only: false,
  };

  it("moves the two-tab selection with RTL arrows and Home/End", () => {
    expect(nextLabsView("owned", "ArrowLeft")).toBe("all");
    expect(nextLabsView("all", "ArrowRight")).toBe("owned");
    expect(nextLabsView("all", "Home")).toBe("owned");
    expect(nextLabsView("owned", "End")).toBe("all");
    expect(nextLabsView("owned", "Tab")).toBeNull();
  });

  it("connects each roving tab to its stable panel", () => {
    const html = renderToStaticMarkup(createElement(LabsViewTabs, {
      view: "owned",
      onViewChange: () => undefined,
    }));
    expect(html).toContain('role="tablist"');
    expect(html).toContain('id="labs-tab-owned"');
    expect(html).toContain('aria-controls="labs-panel-owned"');
    expect(html).toContain('aria-selected="true"');
    expect(html).toContain('tabindex="0"');
    expect(html).toContain('id="labs-tab-all"');
    expect(html).toContain('aria-controls="labs-panel-all"');
    expect(html).toContain('aria-selected="false"');
    expect(html).toContain('tabindex="-1"');
  });

  it("builds 120 valid unique ascending history dates covered by the zone span", () => {
    const dates = historyFixture(120).map((result) => result.test_date);

    expect(dates).toHaveLength(120);
    expect(new Set(dates).size).toBe(120);
    expect(dates).toEqual([...dates].sort());
    expect(dates.every((date) => /^\d{4}-\d{2}-\d{2}$/.test(date))).toBe(true);
    expect(dates.every((date) => new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date)).toBe(true);
    expect(dates.at(0)).toBe("2026-05-23");
    expect(dates.at(-1)).toBe("2026-09-19");
    expect(zoneFixture.at(0)?.from_date).toBe(dates.at(0));
    expect(zoneFixture.at(-1)?.to_date_exclusive).toBe("2026-09-20");
    expect(dates.at(-1)! < zoneFixture.at(-1)!.to_date_exclusive).toBe(true);
  });

  it("joins owned activity and all catalog tests without mutating inputs", () => {
    const owned = toLabListItems(catalogFixture, overview, "owned");
    const all = toLabListItems(catalogFixture, overview, "all");

    expect(owned.map((item) => item.test_key)).toEqual(["hba1c", "ferritin"]);
    expect(all.map((item) => item.test_key)).toEqual(["hba1c", "eosinophils_pct", "ferritin"]);
    expect(all.find((item) => item.test_key === "eosinophils_pct")).toMatchObject({ latest: null, last_updated_at: null });
    expect(catalogFixture.tests.map((item) => item.test_key)).toEqual(["ferritin", "eosinophils_pct", "hba1c"]);
    expect(toLabListItems({ ...catalogFixture, tests: [] }, overview, "all")).toEqual([]);
  });

  it("matches normalized Arabic, English names, and abbreviations with category filtering", () => {
    const items = toLabListItems(catalogFixture, overview, "all");
    expect(filterLabs(items, "  إلسُّكـر  ", null).map((item) => item.test_key)).toEqual(["hba1c"]);
    expect(filterLabs(items, "FERRITIN", null).map((item) => item.test_key)).toEqual(["ferritin"]);
    expect(filterLabs(items, "hba1c", null).map((item) => item.test_key)).toEqual(["hba1c"]);
    expect(filterLabs(items, "", "blood").map((item) => item.test_key)).toEqual(["eosinophils_pct"]);
  });

  it("keeps English case-insensitive search independent of the browser locale", () => {
    const localeLowerCase = String.prototype.toLocaleLowerCase;
    vi.spyOn(String.prototype, "toLocaleLowerCase").mockImplementation(function (this: string) {
      return localeLowerCase.call(this, "tr");
    });

    const items = toLabListItems(catalogFixture, overview, "all");
    expect(filterLabs(items, "FERRITIN", null).map((item) => item.test_key)).toEqual(["ferritin"]);
  });

  it("sorts latest activity without replacing latest result date", () => {
    const items = [
      overviewItem("hba1c", "2026-09-01", "2026-09-02"),
      overviewItem("ferritin", "2026-01-01", "2026-09-19"),
    ];
    expect(sortLabs(items, "newest_updated").map((item) => item.test_key)).toEqual(["ferritin", "hba1c"]);
    expect(items[0].latest!.test_date).toBe("2026-09-01");
  });

  it("puts missing activity last in both directions and keeps deterministic ties", () => {
    const base = toLabListItems(catalogFixture, overview, "all");
    expect(sortLabs(base, "newest_updated").map((item) => item.test_key)).toEqual(["ferritin", "hba1c", "eosinophils_pct"]);
    expect(sortLabs(base, "oldest_updated").map((item) => item.test_key)).toEqual(["hba1c", "ferritin", "eosinophils_pct"]);
    const tied = base.map((item) => ({ ...item, last_updated_at: "2026-09-19T08:00:00Z" }));
    expect(sortLabs(tied, "newest_updated").map((item) => item.test_key)).toEqual(["hba1c", "eosinophils_pct", "ferritin"]);
  });

  it("sorts Arabic names and catalog categories with stable key ties", () => {
    const base = toLabListItems(catalogFixture, overview, "all");
    const sameName = base.map((item) => ({ ...item, test: { ...item.test, name_ar: "اسم" } }));
    expect(sortLabs(base, "name_asc").map((item) => item.test_key)).toEqual(["hba1c", "ferritin", "eosinophils_pct"]);
    expect(sortLabs(base, "name_desc").map((item) => item.test_key)).toEqual(["eosinophils_pct", "ferritin", "hba1c"]);
    expect(sortLabs(sameName, "name_asc").map((item) => item.test_key)).toEqual(["eosinophils_pct", "ferritin", "hba1c"]);
    expect(sortLabs(sameName, "name_desc").map((item) => item.test_key)).toEqual(["eosinophils_pct", "ferritin", "hba1c"]);
    expect(sortLabs(base, "category").map((item) => item.test_key)).toEqual(["hba1c", "eosinophils_pct", "ferritin"]);
  });
});

function hexChannels(value: string): [number, number, number] {
  return [1, 3, 5].map((index) => Number.parseInt(value.slice(index, index + 2), 16)) as [number, number, number];
}

function relativeLuminance(value: string): number {
  const channels = hexChannels(value).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string): number {
  const [lighter, darker] = [relativeLuminance(foreground), relativeLuminance(background)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

function mixWithWhite(value: string, percentage: number): string {
  const mixed = hexChannels(value).map((channel) => Math.round(channel * percentage + 255 * (1 - percentage)));
  return `#${mixed.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

describe("Labs governed status presentation", () => {
  it("maps caution and outside response tones to readable warning and danger chips", () => {
    const caution = {
      ...resultFixture("hba1c", "2026-09-19", "2026-09-19"),
      status: { code: "prediabetes_range", label_ar: "نطاق ما قبل السكري", tone: "caution" },
    };
    const outside = {
      ...resultFixture("ferritin", "2026-09-18", "2026-09-18"),
      status: { code: "low", label_ar: "منخفض", tone: "outside" },
    };
    const response: LabOverviewResponse = {
      items: [
        { test_key: "hba1c", latest: caution, last_updated_at: caution.updated_at },
        { test_key: "ferritin", latest: outside, last_updated_at: outside.updated_at },
      ],
      eligibility: { allowed: true, reason: null },
      server_today: "2026-09-20",
      medical_rules_version: "labs-v1",
      read_only: false,
    };
    const html = renderToStaticMarkup(createElement(OwnedLabsView, {
      catalog: catalogFixture,
      rows: toLabListItems(catalogFixture, response, "owned"),
      eligibility: response.eligibility,
      search: "",
      category: null,
      sort: "newest_updated",
      readOnly: false,
      onSearchChange: () => undefined,
      onCategoryChange: () => undefined,
      onSortChange: () => undefined,
    }));

    expect(html).toContain('data-tone="caution"');
    expect(html).toContain('data-tone="outside"');

    const moduleCss = readFileSync(resolve(process.cwd(), "features/labs/labs.module.css"), "utf8");
    const globalsCss = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
    const expectations = [
      { tone: "caution", palette: "--warning", mix: 0.13 },
      { tone: "outside", palette: "--danger", mix: 0.11 },
    ] as const;

    for (const expected of expectations) {
      const rule = moduleCss.match(new RegExp(`\\.status\\[data-tone="${expected.tone}"\\]\\s*\\{([^}]*)\\}`));
      expect(rule, `${expected.tone} must have an explicit governed-tone rule`).not.toBeNull();
      const declarations = rule?.[1] ?? "";
      expect(declarations).toContain(`background: color-mix(in srgb, var(${expected.palette}) ${expected.mix * 100}%, white)`);
      const foreground = declarations.match(/(?:^|;)\s*color:\s*(#[0-9a-f]{6})/i)?.[1];
      const palette = globalsCss.match(new RegExp(`${expected.palette}:\\s*(#[0-9a-f]{6})`, "i"))?.[1];
      expect(foreground).toBeDefined();
      expect(palette).toBeDefined();
      const background = mixWithWhite(palette!, expected.mix);
      expect(contrastRatio(foreground!, background)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
