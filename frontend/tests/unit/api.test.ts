import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DiaryEntryInput, ProfileInput } from "@/lib/types";

const getSession = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { getSession } }),
}));

import {
  ApiError,
  createDiaryEntry,
  deleteFood,
  getAdminUserDiary,
  getFood,
  getProfile,
  listFoodPicker,
  listFoodsPage,
  previewProfile,
  writeTargetPlan,
} from "@/lib/api";

const profile: ProfileInput = {
  sex: "male",
  birth_date: "1990-01-01",
  height_cm: 180,
  weight_kg: 80,
  activity_level: "moderate",
  goal: "maintain",
  selected_cut_intensity: 0.2,
  protein_per_kg: 1.2,
  fat_pct: 0.25,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestAt(fetchMock: ReturnType<typeof vi.fn>, index = 0) {
  const [input, init] = fetchMock.mock.calls[index] as [string, RequestInit];
  return { url: new URL(input), init, headers: new Headers(init.headers) };
}

describe("API transport behavior", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    getSession.mockReset();
    getSession.mockResolvedValue({ data: { session: { access_token: "session-token" } } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds session authorization, no-store caching, and catalog query parameters", async () => {
    fetchMock.mockResolvedValue(jsonResponse({
      items: [], total: 0, page: 3, page_size: 40, total_pages: 0, categories: [],
    }));

    await listFoodsPage({ search: "  brown rice  ", category: "grains", sort: "recent", page: 3, pageSize: 40 });

    const request = requestAt(fetchMock);
    expect(request.url.pathname).toBe("/foods");
    expect(Object.fromEntries(request.url.searchParams)).toEqual({
      page: "3",
      page_size: "40",
      sort: "recent",
      search: "brown rice",
      category: "grains",
    });
    expect(request.headers.get("Authorization")).toBe("Bearer session-token");
    expect(request.init.cache).toBe("no-store");
  });

  it("sends explicit authorization, JSON, and idempotency metadata for Profile writes", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ preview_hash: "preview-hash" }))
      .mockResolvedValueOnce(jsonResponse({ plan: {} }));

    await previewProfile(profile, "2026-09-20", "explicit-token");
    await writeTargetPlan(profile, "2026-09-20", "preview-hash", "idempotency-key", "explicit-token");

    const preview = requestAt(fetchMock, 0);
    expect(preview.url.pathname).toBe("/profile/preview");
    expect(preview.init.method).toBe("POST");
    expect(preview.headers.get("Authorization")).toBe("Bearer explicit-token");
    expect(preview.headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(preview.init.body))).toEqual({ ...profile, effective_from: "2026-09-20" });

    const write = requestAt(fetchMock, 1);
    expect(write.url.pathname).toBe("/target-plans");
    expect(write.headers.get("Idempotency-Key")).toBe("idempotency-key");
    expect(JSON.parse(String(write.init.body))).toEqual({
      ...profile,
      effective_from: "2026-09-20",
      confirmed: true,
      expected_preview_hash: "preview-hash",
    });
    expect(getSession).not.toHaveBeenCalled();
  });

  it("uses the documented picker, Admin Diary, and Diary mutation paths", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ items: [], next_cursor: null }))
      .mockResolvedValueOnce(jsonResponse({ items: [], next_cursor: null }))
      .mockResolvedValueOnce(jsonResponse({ id: "entry" }));

    await listFoodPicker({ accessToken: "explicit-token", search: "  rice  ", cursor: "next", limit: 10 });
    await getAdminUserDiary("principal-id", "cursor", 25, "2026-09-20");
    await createDiaryEntry({
      food_id: "food-id",
      entry_date: "2026-09-20",
      quantity: 2,
      meal_type: "breakfast",
    } as DiaryEntryInput, "explicit-token");

    const picker = requestAt(fetchMock, 0);
    expect(picker.url.pathname).toBe("/foods/picker");
    expect(Object.fromEntries(picker.url.searchParams)).toEqual({ limit: "10", search: "rice", cursor: "next" });

    const adminDiary = requestAt(fetchMock, 1);
    expect(adminDiary.url.pathname).toBe("/admin/users/principal-id/diary");
    expect(Object.fromEntries(adminDiary.url.searchParams)).toEqual({
      limit: "25", cursor: "cursor", entry_date: "2026-09-20",
    });

    const mutation = requestAt(fetchMock, 2);
    expect(mutation.url.pathname).toBe("/diary/entries");
    expect(mutation.init.method).toBe("POST");
    expect(mutation.headers.get("Authorization")).toBe("Bearer explicit-token");
  });

  it("maps API errors, handles documented 204 deletes, and fails closed without a mutation token", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({
        detail: { code: "FOOD_IN_USE" },
        error: { code: "FOOD_IN_USE", message_ar: "الطعام مستخدم" },
      }, 409))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(getFood("food-id")).rejects.toMatchObject({
      message: "الطعام مستخدم",
      status: 409,
      detail: { code: "FOOD_IN_USE" },
      code: "FOOD_IN_USE",
    } satisfies Partial<ApiError>);
    await expect(deleteFood("food-id", "explicit-token")).resolves.toBeUndefined();
    expect(() => deleteFood("food-id", null)).toThrowError(
      expect.objectContaining({
        message: "Authentication required",
        status: 401,
      } satisfies Partial<ApiError>),
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("maps a missing Profile to null without hiding other failures", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ detail: "missing" }, 404))
      .mockResolvedValueOnce(new Response("not-json", { status: 503 }));

    await expect(getProfile()).resolves.toBeNull();
    await expect(getProfile()).rejects.toMatchObject({
      message: "API request failed with 503",
      status: 503,
    } satisfies Partial<ApiError>);
  });
});
