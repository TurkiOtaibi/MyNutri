import { randomUUID } from "node:crypto";

import type { APIRequestContext, APIResponse } from "@playwright/test";

import type { ProfileInput } from "../lib/types";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

export async function applyProfileThroughTargetPlan(
  request: APIRequestContext,
  accessToken: string | { toString: () => string },
  payload: ProfileInput
): Promise<APIResponse> {
  const headers = { Authorization: `Bearer ${accessToken}` };
  const preview = await request.post(`${API_URL}/profile/preview`, { headers, data: payload });
  if (!preview.ok()) {
    throw new Error(`Profile preview failed with ${preview.status()}: ${await preview.text()}`);
  }
  const previewBody = await preview.json() as { preview_hash: string };

  const current = await request.get(`${API_URL}/profile`, { headers });
  if (current.status() !== 404 && !current.ok()) {
    throw new Error(`Profile read failed with ${current.status()}: ${await current.text()}`);
  }
  const hasPendingPlan = current.ok()
    && ((await current.json()) as { pending_plan?: unknown }).pending_plan != null;
  const path = hasPendingPlan ? "/target-plans/pending/replace" : "/target-plans/activate";
  const confirmation = hasPendingPlan ? { replace_confirmed: true } : { confirmed: true };
  const response = await request.post(`${API_URL}${path}`, {
    headers: { ...headers, "Idempotency-Key": `e2e-profile-${randomUUID()}` },
    data: {
      ...payload,
      ...confirmation,
      expected_preview_hash: previewBody.preview_hash
    }
  });
  if (!response.ok()) {
    throw new Error(`Profile activation failed with ${response.status()}: ${await response.text()}`);
  }
  return response;
}
