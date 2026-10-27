import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { request } from "@playwright/test";

export const SESSION_TOKEN_KEY = "mynutri-session-token";
export const ADMIN_EMAIL = "admin.e2e@example.test";
export const ADMIN_PASSWORD = "E2e-only-password-2026!";
const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

export function fixtureUsername(email: string): string {
  return `e2e_${createHash("sha256").update(email).digest("hex").slice(0, 28)}`;
}

export function seedInternalUser(email: string, password: string, mustChangePassword = false): void {
  const result = spawnSync(process.env.PLAYWRIGHT_PYTHON ?? "python", ["-m", "scripts.e2e_internal_auth"], {
    cwd: path.resolve(process.cwd(), "../backend"),
    input: JSON.stringify({ email, username: fixtureUsername(email), password, must_change_password: mustChangePassword }),
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status !== 0) throw new Error("Internal E2E fixture setup failed; verify the named disposable loopback database.");
}

export async function internalLogin(email: string, password: string) {
  if (!["127.0.0.1", "localhost"].includes(new URL(API_URL).hostname)) {
    throw new Error("Internal E2E login requires a loopback API.");
  }
  const client = await request.newContext();
  try {
    const response = await client.post(`${API_URL}/auth/login`, {
      data: { username: fixtureUsername(email), password },
    });
    if (!response.ok()) throw new Error(`Internal E2E login failed: ${response.status()}`);
    return await response.json() as {
      access_token: string;
      expires_at: string;
      account: { principal_id: string; role: string; must_change_password: boolean };
    };
  } finally {
    await client.dispose();
  }
}
