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
  const calendar = await request.get(`${API_URL}/account/calendar`, { headers });
  if (!calendar.ok()) {
    throw new Error(`Calendar authority failed with ${calendar.status()}: ${await calendar.text()}`);
  }
  const { current_diary_date: effectiveFrom } = await calendar.json() as { current_diary_date: string };
  const preview = await request.post(`${API_URL}/profile/preview`, {
    headers,
    data: { ...payload, effective_from: effectiveFrom }
  });
  if (!preview.ok()) {
    throw new Error(`Profile preview failed with ${preview.status()}: ${await preview.text()}`);
  }
  const previewBody = await preview.json() as { preview_hash: string };

  const response = await request.post(`${API_URL}/target-plans`, {
    headers: { ...headers, "Idempotency-Key": `e2e-profile-${randomUUID()}` },
    data: {
      ...payload,
      effective_from: effectiveFrom,
      confirmed: true,
      expected_preview_hash: previewBody.preview_hash
    }
  });
  if (!response.ok()) {
    throw new Error(`Target Plan write failed with ${response.status()}: ${await response.text()}`);
  }
  return response;
}
