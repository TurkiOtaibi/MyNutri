export const SESSION_TOKEN_KEY = "mynutri-session-token";
export const SESSION_CHANGED = "mynutri-session-changed";
export const SESSION_REJECTED = "mynutri-session-rejected";

export function readSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
  return token && /^mn1_[A-Za-z0-9_-]+$/.test(token) ? token : null;
}

export function saveSessionToken(token: string): void {
  window.localStorage.setItem(SESSION_TOKEN_KEY, token);
  window.dispatchEvent(new Event(SESSION_CHANGED));
}

/** A stale response must never sign out a newer login. */
export function clearSessionToken(expected: string): boolean {
  if (readSessionToken() !== expected) return false;
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.dispatchEvent(new Event(SESSION_CHANGED));
  return true;
}

export function rejectSession(token: string, code: string): void {
  if (clearSessionToken(token)) {
    window.dispatchEvent(new CustomEvent(SESSION_REJECTED, { detail: code }));
  }
}
