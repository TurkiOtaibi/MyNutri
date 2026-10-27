"use client";

import { createContext, useCallback, useContext, useEffect, useReducer, useRef } from "react";
import { usePathname, useRouter, useSelectedLayoutSegment } from "next/navigation";
import { ApiError, changeAccountPassword, getCurrentAccount, loginAccount, logoutAccount, type CurrentAccount } from "@/lib/api";
import { normalizePostLoginPath } from "@/lib/auth-return-path";
import { clearSessionToken, readSessionToken, saveSessionToken, SESSION_CHANGED, SESSION_REJECTED, SESSION_TOKEN_KEY } from "@/lib/internal-session";
import { ForcedPasswordChange } from "./ForcedPasswordChange";

type BrowserSession = { access_token: string; user: { id: string } };
type State = { session: BrowserSession | null; account: CurrentAccount | null; initialized: boolean; failed: boolean; signOutFailed: boolean };
type Action = { type: "accept"; token: string; account: CurrentAccount } | { type: "restore" } | { type: "clear" } | { type: "failed" } | { type: "logout-failed" };
const initial: State = { session: null, account: null, initialized: false, failed: false, signOutFailed: false };
function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "accept": return { session: { access_token: action.token, user: { id: action.account.principal_id } }, account: action.account, initialized: true, failed: false, signOutFailed: false };
    case "restore": return initial;
    case "clear": return { ...initial, initialized: true };
    case "failed": return { ...initial, initialized: true, failed: true };
    case "logout-failed": return { ...state, signOutFailed: true };
  }
}
type AuthContextState = {
  session: BrowserSession | null; account: CurrentAccount | null; loading: boolean;
  signIn: (username: string, password: string, returnTo: string) => Promise<void>;
  signOut: () => Promise<void>;
  content: React.ReactNode; permitted: boolean; signOutFailed: boolean;
};
const AuthContext = createContext<AuthContextState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initial);
  const router = useRouter();
  const pathname = usePathname();
  const offlineShell = useSelectedLayoutSegment() === "offline";
  const generation = useRef(0);
  const activeToken = useRef<string | null>(null);
  const initialPassword = useRef<string | null>(null);
  const returnTo = useRef("/diary");
  const rejectionReason = useRef<string | null>(null);
  const loggingOut = useRef(false);
  const mounted = useRef(false);

  const restore = useCallback(async () => {
    const sequence = ++generation.current;
    initialPassword.current = null;
    const token = readSessionToken();
    activeToken.current = token;
    dispatch({ type: token ? "restore" : "clear" });
    if (!token) return;
    try {
      const account = await getCurrentAccount({ accessToken: token });
      if (mounted.current && sequence === generation.current && token === readSessionToken()) dispatch({ type: "accept", token, account });
    } catch (error) {
      if (!mounted.current || sequence !== generation.current) return;
      if (error instanceof ApiError && error.code === "PASSWORD_CHANGE_REQUIRED") {
        // The initial password is deliberately never persisted. Reload requires re-authentication.
        clearSessionToken(token);
      } else if (token === readSessionToken()) dispatch({ type: "failed" });
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const changed = () => { if (!offlineShell && readSessionToken() !== activeToken.current) void restore(); };
    const storage = (event: StorageEvent) => { if (event.key === SESSION_TOKEN_KEY || event.key === null) changed(); };
    const rejected = (event: Event) => {
      if (offlineShell) return;
      const reason = (event as CustomEvent<string>).detail === "ACCOUNT_DISABLED" ? "disabled" : "expired";
      rejectionReason.current = reason;
      const next = window.location.pathname.startsWith("/auth/")
        ? new URLSearchParams(window.location.search).get("next") ?? "/diary"
        : `${window.location.pathname}${window.location.search}${window.location.hash}`;
      router.replace(`/auth/login?reason=${reason}&next=${encodeURIComponent(normalizePostLoginPath(next, window.location.origin))}`);
    };
    window.addEventListener("storage", storage);
    window.addEventListener(SESSION_CHANGED, changed);
    window.addEventListener(SESSION_REJECTED, rejected);
    if (offlineShell) { activeToken.current = null; dispatch({ type: "clear" }); }
    else void restore();
    return () => {
      mounted.current = false;
      generation.current += 1;
      initialPassword.current = null;
      window.removeEventListener("storage", storage);
      window.removeEventListener(SESSION_CHANGED, changed);
      window.removeEventListener(SESSION_REJECTED, rejected);
    };
  }, [offlineShell, restore, router]);

  useEffect(() => {
    if (offlineShell || !state.initialized || state.failed || state.account?.must_change_password) return;
    if (!state.session && pathname !== "/auth/login") {
      const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      const reason = rejectionReason.current ? `reason=${rejectionReason.current}&` : "";
      router.replace(`/auth/login?${reason}next=${encodeURIComponent(next)}`);
    } else if (state.session && pathname === "/auth/login") router.replace(returnTo.current);
    else if (state.session) returnTo.current = "/diary";
  }, [offlineShell, pathname, router, state.account, state.failed, state.initialized, state.session]);

  const signIn = useCallback(async (username: string, password: string, requested: string) => {
    const sequence = ++generation.current;
    const result = await loginAccount({ username, password });
    if (!mounted.current || sequence !== generation.current) return;
    returnTo.current = normalizePostLoginPath(requested, window.location.origin);
    rejectionReason.current = null;
    initialPassword.current = result.account.must_change_password ? password : null;
    activeToken.current = result.access_token;
    saveSessionToken(result.access_token);
    dispatch({ type: "accept", token: result.access_token, account: result.account });
  }, []);

  const signOut = useCallback(async () => {
    if (loggingOut.current) return;
    const token = activeToken.current;
    if (!token) return;
    loggingOut.current = true;
    try {
      await logoutAccount(token);
      if (clearSessionToken(token)) router.replace("/auth/login");
    } catch {
      // Explicit logout always removes this browser's credential and private UI,
      // even when remote revocation could not be confirmed. Never clear a newer login.
      if (token === activeToken.current && clearSessionToken(token)) {
        dispatch({ type: "logout-failed" });
        router.replace("/auth/login");
      }
    } finally { loggingOut.current = false; }
  }, [router]);

  const changeInitialPassword = async (password: string) => {
    const sequence = generation.current;
    const token = activeToken.current;
    const current = initialPassword.current;
    if (!token || !current || !state.account) return;
    await changeAccountPassword({ current_password: current, new_password: password }, token);
    if (token !== activeToken.current || token !== readSessionToken() || sequence !== generation.current || !mounted.current) return;
    initialPassword.current = null;
    dispatch({ type: "accept", token, account: { ...state.account, must_change_password: false } });
    router.replace(returnTo.current);
  };
  const permitted = state.initialized && !state.failed && (state.session ? pathname !== "/auth/login" : pathname === "/auth/login");
  const content = state.failed ? <div className="state-note" role="alert"><p>تعذر الاتصال بالخادم. حاول مرة أخرى.</p><button className="btn" onClick={() => void restore()}>إعادة المحاولة</button></div>
    : state.account?.must_change_password ? <ForcedPasswordChange onSave={changeInitialPassword} onSignOut={signOut} /> : null;
  return <AuthContext.Provider value={{ session: state.session, account: state.account, loading: !state.initialized, signIn, signOut, content, permitted, signOutFailed: state.signOutFailed }}>{children}</AuthContext.Provider>;
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const offlineShell = useSelectedLayoutSegment() === "offline";
  const { content, permitted, signOutFailed } = useAuth();
  // The cached /offline document keeps its route tree even at a deep fallback URL.
  // It contains only the generic static shell, never account or domain data.
  if (offlineShell) return children;
  return <>
    {signOutFailed ? <p role="alert" className="state-note" dir="rtl">تعذر تسجيل الخروج. حاول مرة أخرى.</p> : null}
    {content ?? (permitted ? children : null)}
  </>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
