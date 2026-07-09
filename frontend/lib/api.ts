import type {
  DiaryEntryInput,
  DiaryEntryResponse,
  FoodInput,
  FoodResponse,
  ProfileInput,
  ProfileResponse,
  TargetResponse,
  WeekSummary
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "dev-token";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (API_TOKEN && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${API_TOKEN}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let message = `API request failed with ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Keep the status-based message when the server has no JSON body.
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
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

export function saveProfile(payload: ProfileInput): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function previewProfile(payload: ProfileInput): Promise<TargetResponse> {
  return apiFetch<TargetResponse>("/profile/preview", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listFoods(query = ""): Promise<FoodResponse[]> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return apiFetch<FoodResponse[]>(`/foods${suffix}`);
}

export function createFood(payload: FoodInput & { id?: string }): Promise<FoodResponse> {
  return apiFetch<FoodResponse>("/foods", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateFood(foodId: string, payload: Partial<FoodInput>): Promise<FoodResponse> {
  return apiFetch<FoodResponse>(`/foods/${foodId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteFood(foodId: string): Promise<void> {
  return apiFetch<void>(`/foods/${foodId}`, { method: "DELETE" });
}

export function listDiaryEntries(entryDate: string): Promise<DiaryEntryResponse[]> {
  return apiFetch<DiaryEntryResponse[]>(`/diary?entry_date=${encodeURIComponent(entryDate)}`);
}

export function createDiaryEntry(payload: DiaryEntryInput): Promise<DiaryEntryResponse> {
  return apiFetch<DiaryEntryResponse>("/diary", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteDiaryEntry(entryId: string): Promise<void> {
  return apiFetch<void>(`/diary/${entryId}`, { method: "DELETE" });
}

export function getWeekSummary(start: string): Promise<WeekSummary> {
  return apiFetch<WeekSummary>(`/diary/week?start=${encodeURIComponent(start)}`);
}
