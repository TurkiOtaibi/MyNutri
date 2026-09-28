import { randomUUID } from "node:crypto";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const AUTH_URL = process.env.PLAYWRIGHT_SUPABASE_URL ?? "http://127.0.0.1:8765";

/** Prepare a synthetic account through the production Admin route in disposable E2E. */
export async function provisionUser(email: string, password: string): Promise<void> {
  if (email === "admin.e2e@example.test") return;
  const adminLogin = await fetch(`${AUTH_URL}/auth/v1/token?grant_type=password`, {
    method: "POST", headers: { apikey: "e2e-public-key", "Content-Type": "application/json" },
    body: JSON.stringify({ email: "admin.e2e@example.test", password: "E2e-only-password-2026!" })
  });
  if (!adminLogin.ok) throw new Error(`Synthetic Admin sign-in failed: ${adminLogin.status}`);
  const admin = await adminLogin.json() as { access_token: string };
  const response = await fetch(`${API_URL}/admin/accounts`, {
    method: "POST",
    headers: { Authorization: `Bearer ${admin.access_token}`, "Content-Type": "application/json", "Idempotency-Key": randomUUID() },
    body: JSON.stringify({ email, display_name: "مستخدم الاختبار", initial_password: password })
  });
  if (response.status !== 201 && response.status !== 409) {
    throw new Error(`Synthetic account provision failed: ${response.status}`);
  }
}
