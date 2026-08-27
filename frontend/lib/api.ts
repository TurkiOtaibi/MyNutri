import type {
  AdminDiaryPage,
  BehaviorGoalCommand,
  BehaviorGoalCommandResponse,
  BehaviorGoalCurrent,
  BehaviorGoalHistory,
  DiaryEntryInput,
  DiaryEntryResponse,
  DiaryDayStatusResponse,
  MealType,
  FoodInput,
  FoodListResponse,
  FoodPickerResponse,
  FoodResponse,
  FoodSort,
  ProfileInput,
  ProfileResponse,
  NutritionRegistryResponse,
  PatternAnalysisHistory,
  PatternAnalysisResponse,
  TargetResponse,
  TargetPlanActivationResponse,
  TargetPlanHistoryResponse,
  WeeklyPriorityResult,
  WeekSummary
} from "./types";
import type {
  AccountResponse,
  AdminUserDetail,
  AdminUserListResponse,
  AdminUserSummary as GeneratedAdminUserSummary,
  CalendarAuthorityResponse,
  FoodDeleteResponse
} from "./generated/openapi";
import { createClient } from "./supabase/client";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export type CurrentAccount = AccountResponse;
export type CalendarAuthority = CalendarAuthorityResponse;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
    public code?: string
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  return (await apiFetchWithResponse<T>(path, init)).body;
}

async function apiFetchWithResponse<T>(path: string, init: RequestInit = {}): Promise<{ body: T; response: Response }> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Authorization")) {
    const { data } = await createClient().auth.getSession();
    if (data.session?.access_token) {
      headers.set("Authorization", `Bearer ${data.session.access_token}`);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (response.status === 204) {
    return { body: undefined as T, response };
  }

  if (!response.ok) {
    let message = `API request failed with ${response.status}`;
    let detail: unknown = undefined;
    let code: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string | Record<string, unknown>; error?: { code?: string; message_ar?: string } };
      detail = body.detail;
      message = body.error?.message_ar ?? (typeof body.detail === "string" ? body.detail : message);
      const detailCode = typeof body.detail === "object" && body.detail !== null && typeof body.detail.code === "string"
        ? body.detail.code
        : undefined;
      code = body.error?.code ?? detailCode;
    } catch {
      // Keep the status-based message when the server has no JSON body.
    }
    throw new ApiError(message, response.status, detail, code);
  }

  return { body: await response.json() as T, response };
}

export function getCurrentAccount(options: { accessToken: string; signal?: AbortSignal }): Promise<CurrentAccount> {
  return apiFetch<CurrentAccount>("/account/me", {
    headers: { Authorization: `Bearer ${options.accessToken}` },
    signal: options.signal
  });
}

export function getCalendarAuthority(options: { accessToken: string; signal?: AbortSignal }): Promise<CalendarAuthority> {
  return apiFetch<CalendarAuthority>("/account/calendar", {
    headers: { Authorization: `Bearer ${options.accessToken}` },
    signal: options.signal
  });
}

function authorizedInit(
  accessToken: string | null | undefined,
  signal: AbortSignal | undefined,
  init: RequestInit = {}
): RequestInit {
  if (!accessToken) throw new ApiError("Authentication required", 401);
  return { ...init, signal, headers: { ...init.headers, Authorization: `Bearer ${accessToken}` } };
}

export async function getProfile(): Promise<ProfileResponse | null> {
  try {
    return await apiFetch<ProfileResponse>("/profile");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function saveProfile(payload: ProfileInput, accessToken: string | null | undefined, signal?: AbortSignal): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile", authorizedInit(accessToken, signal, {
    method: "PUT",
    body: JSON.stringify(payload)
  }));
}

export function previewProfile(payload: ProfileInput, accessToken: string | null | undefined, signal?: AbortSignal): Promise<TargetResponse> {
  return apiFetch<TargetResponse>("/profile/preview", authorizedInit(accessToken, signal, {
    method: "POST",
    body: JSON.stringify(payload)
  }));
}

export function activateTargetPlan(
  payload: ProfileInput,
  expectedPreviewHash: string,
  idempotencyKey: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<TargetPlanActivationResponse> {
  return apiFetch<TargetPlanActivationResponse>("/target-plans/activate", authorizedInit(accessToken, signal, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ ...payload, confirmed: true, expected_preview_hash: expectedPreviewHash })
  }));
}

export function replacePendingTargetPlan(
  payload: ProfileInput,
  expectedPreviewHash: string,
  idempotencyKey: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<TargetPlanActivationResponse> {
  return apiFetch<TargetPlanActivationResponse>("/target-plans/pending/replace", authorizedInit(accessToken, signal, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ ...payload, replace_confirmed: true, expected_preview_hash: expectedPreviewHash })
  }));
}

export function getNutritionRegistry(): Promise<NutritionRegistryResponse> {
  return apiFetch<NutritionRegistryResponse>("/nutrition/registry");
}

export function listTargetPlanHistory(cursor?: string | null, limit = 20): Promise<TargetPlanHistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<TargetPlanHistoryResponse>(`/target-plans?${params.toString()}`);
}

export function listFoods(query = ""): Promise<FoodResponse[]> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return apiFetch<FoodResponse[]>(`/foods${suffix}`);
}

export function listFoodPicker(
  options: {
    accessToken: string | null | undefined;
    search?: string;
    cursor?: string | null;
    limit?: number;
    signal?: AbortSignal;
  }
): Promise<FoodPickerResponse> {
  const params = new URLSearchParams({ limit: String(options.limit ?? 30) });
  if (options.search?.trim()) params.set("search", options.search.trim());
  if (options.cursor) params.set("cursor", options.cursor);
  return apiFetch<FoodPickerResponse>(
    `/foods/picker?${params.toString()}`,
    authorizedInit(options.accessToken, options.signal)
  );
}

export interface FoodListOptions {
  search?: string;
  category?: string;
  sort?: FoodSort;
  page?: number;
  pageSize?: number;
  status?: "active" | "archived";
}

export async function listAdminFoodsPage(options: FoodListOptions = {}): Promise<FoodListResponse> {
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    page_size: String(options.pageSize ?? 20),
    sort: options.sort ?? "name"
  });
  if (options.search?.trim()) params.set("search", options.search.trim());
  if (options.category) params.set("category", options.category);
  if (options.status) params.set("status", options.status);
  return apiFetch<FoodListResponse>(`/admin/foods?${params.toString()}`);
}

export async function listFoodsPage(options: FoodListOptions = {}): Promise<FoodListResponse> {
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    page_size: String(options.pageSize ?? 20),
    sort: options.sort ?? "name"
  });
  if (options.search?.trim()) params.set("search", options.search.trim());
  if (options.category) params.set("category", options.category);
  const result = await apiFetch<FoodListResponse | FoodResponse[]>(`/foods?${params.toString()}`);
  if (!Array.isArray(result)) return result;

  const page = options.page ?? 1;
  const pageSize = options.pageSize ?? 20;
  const start = (page - 1) * pageSize;
  const categories = [...new Set(result.map((food) => food.food_category_key))].sort();
  return {
    items: result.slice(start, start + pageSize),
    total: result.length,
    page,
    page_size: pageSize,
    total_pages: result.length ? Math.ceil(result.length / pageSize) : 0,
    categories,
    uncategorized_count: 0
  };
}

export function getFood(foodId: string): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/foods/${foodId}`);
}

export function getAdminFood(foodId: string): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/admin/foods/${foodId}`);
}

export function createFood(payload: FoodInput & { id?: string }, accessToken: string | null | undefined, signal?: AbortSignal): Promise<FoodResponse> {
  return apiFetch<FoodResponse>("/foods", authorizedInit(accessToken, signal, {
    method: "POST",
    body: JSON.stringify(payload)
  }));
}

export function updateFood(foodId: string, payload: Partial<FoodInput>, accessToken: string | null | undefined, signal?: AbortSignal): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/foods/${foodId}`, authorizedInit(accessToken, signal, {
    method: "PUT",
    body: JSON.stringify(payload)
  }));
}

export function deleteFood(foodId: string, accessToken: string | null | undefined, signal?: AbortSignal): Promise<FoodDeleteResponse> {
  return apiFetch<FoodDeleteResponse>(`/admin/foods/${foodId}`, authorizedInit(accessToken, signal, { method: "DELETE" }));
}

export function archiveFood(foodId: string, accessToken: string | null | undefined, signal?: AbortSignal): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/admin/foods/${foodId}/archive`, authorizedInit(accessToken, signal, { method: "POST" }));
}

export function restoreFood(foodId: string, accessToken: string | null | undefined, signal?: AbortSignal): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/admin/foods/${foodId}/restore`, authorizedInit(accessToken, signal, { method: "POST" }));
}

export type AdminUserSummary = GeneratedAdminUserSummary;
export type AdminUserList = AdminUserListResponse;

export function listAdminUsers(search = "", page = 1): Promise<AdminUserList> {
  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  if (search.trim()) params.set("search", search.trim());
  return apiFetch<AdminUserList>(`/admin/users?${params}`);
}

export function getAdminUser(principalId: string): Promise<AdminUserDetail> {
  return apiFetch<AdminUserDetail>(`/admin/users/${principalId}`);
}

export function getAdminUserDiary(
  principalId: string,
  cursor?: string | null,
  limit = 50,
  entryDate?: string
): Promise<AdminDiaryPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  if (entryDate) params.set("entry_date", entryDate);
  return apiFetch<AdminDiaryPage>(`/admin/users/${principalId}/diary?${params.toString()}`);
}

export function listDiaryEntries(entryDate: string): Promise<DiaryEntryResponse[]> {
  return apiFetch<DiaryEntryResponse[]>(`/diary/entries?entry_date=${encodeURIComponent(entryDate)}`);
}

export function listDiaryHistory(): Promise<DiaryEntryResponse[]> {
  return apiFetch<DiaryEntryResponse[]>("/diary");
}

export function createDiaryEntry(payload: DiaryEntryInput, dayVersion: number, accessToken: string | null | undefined, signal?: AbortSignal): Promise<DiaryEntryResponse> {
  return apiFetch<DiaryEntryResponse>("/diary/entries", authorizedInit(accessToken, signal, {
    method: "POST",
    headers: { "If-Match": `"day-${dayVersion}"` },
    body: JSON.stringify(payload)
  }));
}

export function updateDiaryEntry(entryId: string, quantity: number, mealType: MealType, dayVersion: number, accessToken: string | null | undefined, signal?: AbortSignal): Promise<DiaryEntryResponse> {
  return apiFetch<DiaryEntryResponse>(`/diary/entries/${entryId}`, authorizedInit(accessToken, signal, {
    method: "PATCH",
    headers: { "If-Match": `"day-${dayVersion}"` },
    body: JSON.stringify({ quantity, meal_type: mealType })
  }));
}

export function deleteDiaryEntry(entryId: string, dayVersion: number, accessToken: string | null | undefined, signal?: AbortSignal): Promise<void> {
  return apiFetch<void>(`/diary/entries/${entryId}`, authorizedInit(accessToken, signal, {
    method: "DELETE",
    headers: { "If-Match": `"day-${dayVersion}"` }
  }));
}

export function getDiaryDayStatus(
  diaryDate: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<DiaryDayStatusResponse> {
  return apiFetch<DiaryDayStatusResponse>(
    `/diary/days/${diaryDate}/status`,
    authorizedInit(accessToken, signal)
  );
}

export function setDiaryDayStatus(
  diaryDate: string,
  action: "complete" | "reopen",
  expectedVersion: number,
  idempotencyKey: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<DiaryDayStatusResponse> {
  return apiFetch<DiaryDayStatusResponse>(`/diary/days/${diaryDate}/${action}`, authorizedInit(accessToken, signal, {
    method: "PUT",
    headers: {
      "Idempotency-Key": idempotencyKey,
      "If-Match": `"day-${expectedVersion}"`
    },
    body: JSON.stringify({ expected_version: expectedVersion })
  }));
}

export function getWeekSummary(start: string): Promise<WeekSummary> {
  return apiFetch<WeekSummary>(`/diary/week?start=${encodeURIComponent(start)}`);
}

export async function getCurrentPatternAnalysis(
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<PatternAnalysisResponse | null> {
  try {
    return await apiFetch<PatternAnalysisResponse>(
      "/progress/nutrition-analysis/current",
      authorizedInit(accessToken, signal)
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && error.code === "ANALYSIS_NOT_FOUND") {
      return null;
    }
    throw error;
  }
}

export function listPatternAnalysisHistory(
  accessToken: string | null | undefined,
  cursor?: string | null,
  limit = 20,
  signal?: AbortSignal
): Promise<PatternAnalysisHistory> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<PatternAnalysisHistory>(
    `/progress/nutrition-analysis/history?${params.toString()}`,
    authorizedInit(accessToken, signal)
  );
}

export function evaluatePatternAnalysis(
  expectedRevision: number | null,
  etag: string | null,
  idempotencyKey: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<PatternAnalysisResponse> {
  return apiFetch<PatternAnalysisResponse>(
    "/progress/nutrition-analysis/evaluate",
    authorizedInit(accessToken, signal, {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
        "If-Match": etag ?? '"analysis-none"'
      },
      body: JSON.stringify({ expected_current_revision: expectedRevision })
    })
  );
}

export async function getCurrentWeeklyPriority(
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<WeeklyPriorityResult | null> {
  try {
    return await apiFetch<WeeklyPriorityResult>(
      "/progress/weekly-priorities/current",
      authorizedInit(accessToken, signal)
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 503 && error.code === "PRIORITY_EVIDENCE_UNAVAILABLE") {
      return null;
    }
    throw error;
  }
}

export function getCurrentBehaviorGoal(
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<BehaviorGoalCurrent> {
  return apiFetch<BehaviorGoalCurrent>(
    "/progress/behavior-goals/current",
    authorizedInit(accessToken, signal)
  );
}

export function listBehaviorGoalHistory(
  accessToken: string | null | undefined,
  cursor?: string | null,
  limit = 20,
  signal?: AbortSignal
): Promise<BehaviorGoalHistory> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<BehaviorGoalHistory>(
    `/progress/behavior-goals/history?${params.toString()}`,
    authorizedInit(accessToken, signal)
  );
}

export function commandBehaviorGoal(
  goalId: string,
  command: BehaviorGoalCommand,
  idempotencyKey: string,
  accessToken: string | null | undefined,
  signal?: AbortSignal
): Promise<BehaviorGoalCommandResponse & { idempotent_replayed: boolean }> {
  return apiFetchWithResponse<BehaviorGoalCommandResponse>(
    `/progress/behavior-goals/${goalId}/commands`,
    authorizedInit(accessToken, signal, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(command)
    })
  ).then(({ body, response }) => ({
    ...body,
    idempotent_replayed: response.headers.get("Idempotent-Replayed") === "true"
  }));
}
