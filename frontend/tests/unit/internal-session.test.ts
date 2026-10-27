import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { readSessionToken, saveSessionToken, clearSessionToken, SESSION_TOKEN_KEY } from "@/lib/internal-session";
import { normalizePostLoginPath } from "@/lib/auth-return-path";

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("window", { localStorage: {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  }, dispatchEvent: vi.fn() });
});
afterEach(() => vi.unstubAllGlobals());
it("persists only the opaque token, and clears the current session", () => {
  saveSessionToken("mn1_synthetic");
  expect(window.localStorage.getItem(SESSION_TOKEN_KEY)).toBe("mn1_synthetic");
  expect(readSessionToken()).toBe("mn1_synthetic");
  expect(clearSessionToken("mn1_synthetic")).toBe(true);
  expect(readSessionToken()).toBeNull();
});
it("does not let a late failure clear a newer session", () => {
  saveSessionToken("mn1_new");
  expect(clearSessionToken("mn1_old")).toBe(false);
  expect(readSessionToken()).toBe("mn1_new");
});
it("does not admit legacy or malformed storage tokens", () => {
  window.localStorage.setItem(SESSION_TOKEN_KEY, "legacy.jwt.value");
  expect(readSessionToken()).toBeNull();
});
it("cannot return into an auth redirect loop or an external origin", () => {
  for (const target of ["/auth/login", "/auth/forgot-password", "//outside.test", "https://outside.test"]) {
    expect(normalizePostLoginPath(target, "https://app.test")).toBe("/diary");
  }
  expect(normalizePostLoginPath("/diary?date=2026-10-27#summary", "https://app.test"))
    .toBe("/diary?date=2026-10-27#summary");
});
