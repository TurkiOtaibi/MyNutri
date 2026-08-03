"use client";

import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ApiError, getCurrentAccount, type CurrentAccount } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type AuthState = {
  session: Session | null;
  accountSubjectId: string | null;
  account: CurrentAccount | null;
  accountLoadingSubjectId: string | null;
  accountSettledSubjectId: string | null;
  initialized: boolean;
  signingOutSubjectId: string | null;
  reloadNonce: number;
  recoveryStatus: RecoveryStatus;
  recoverySubjectId: string | null;
};

export type RecoveryStatus = "checking" | "ready" | "invalid";
type RecoveryAttempt = "none" | "pending" | "invalid";

type AuthAction =
  | { type: "AUTH_CHANGED"; session: Session | null }
  | { type: "RECOVERY_EVENT"; event: AuthChangeEvent; session: Session | null; attempt: RecoveryAttempt }
  | { type: "ACCOUNT_REQUEST"; subjectId: string }
  | { type: "ACCOUNT_RECEIVED"; subjectId: string; account: CurrentAccount }
  | { type: "ACCOUNT_COMPLETE"; subjectId: string }
  | { type: "SIGNING_OUT"; subjectId: string }
  | { type: "RESTORE_AFTER_SIGNOUT_FAILURE"; subjectId: string };

const initialState: AuthState = {
  session: null,
  accountSubjectId: null,
  account: null,
  accountLoadingSubjectId: null,
  accountSettledSubjectId: null,
  initialized: false,
  signingOutSubjectId: null,
  reloadNonce: 0,
  recoveryStatus: "checking",
  recoverySubjectId: null
};

function reducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "AUTH_CHANGED": {
      const previousSubject = state.session?.user.id ?? null;
      const nextSubject = action.session?.user.id ?? null;
      const tokenChanged = state.session?.access_token !== action.session?.access_token;
      if (previousSubject !== nextSubject) {
        return {
          ...state,
          session: action.session,
          account: null,
          accountSubjectId: null,
          accountLoadingSubjectId: nextSubject,
          accountSettledSubjectId: null,
          signingOutSubjectId: null,
          initialized: true
        };
      }
      if (tokenChanged && state.signingOutSubjectId === nextSubject) {
        return {
          ...state,
          session: action.session,
          account: null,
          accountSubjectId: null,
          accountLoadingSubjectId: nextSubject,
          accountSettledSubjectId: null,
          signingOutSubjectId: null,
          initialized: true
        };
      }
      return {
        ...state,
        session: action.session,
        initialized: true,
        signingOutSubjectId: state.signingOutSubjectId === nextSubject ? state.signingOutSubjectId : null,
      };
    }
    case "RECOVERY_EVENT": {
      const nextSubject = action.session?.user.id ?? null;
      if (action.event === "PASSWORD_RECOVERY" && nextSubject) {
        return { ...state, recoveryStatus: "ready", recoverySubjectId: nextSubject };
      }
      if (action.event === "INITIAL_SESSION") {
        if (state.recoveryStatus === "ready" && state.recoverySubjectId === nextSubject) return state;
        return action.attempt === "pending"
          ? { ...state, recoveryStatus: "checking", recoverySubjectId: null }
          : { ...state, recoveryStatus: "invalid", recoverySubjectId: null };
      }
      if (action.event === "TOKEN_REFRESHED") {
        return state.recoverySubjectId === nextSubject
          ? state
          : { ...state, recoveryStatus: "invalid", recoverySubjectId: null };
      }
      if (action.event === "USER_UPDATED" || action.event === "SIGNED_OUT") {
        return { ...state, recoveryStatus: "invalid", recoverySubjectId: null };
      }
      if (action.event === "SIGNED_IN") {
        const sameRecoverySession = state.recoverySubjectId === nextSubject &&
          state.session?.access_token === action.session?.access_token;
        return sameRecoverySession
          ? state
          : { ...state, recoveryStatus: "invalid", recoverySubjectId: null };
      }
      return state;
    }
    case "ACCOUNT_REQUEST":
      return state.session?.user.id === action.subjectId && state.signingOutSubjectId !== action.subjectId
        ? { ...state, accountLoadingSubjectId: action.subjectId }
        : state;
    case "ACCOUNT_RECEIVED":
      return state.session?.user.id === action.subjectId && state.signingOutSubjectId !== action.subjectId
        ? { ...state, account: action.account, accountSubjectId: action.subjectId, accountSettledSubjectId: action.subjectId }
        : state;
    case "ACCOUNT_COMPLETE":
      return state.session?.user.id === action.subjectId
        ? { ...state, accountLoadingSubjectId: null, accountSettledSubjectId: action.subjectId }
        : state;
    case "SIGNING_OUT":
      return state.session?.user.id === action.subjectId
        ? { ...state, account: null, accountSubjectId: null, accountLoadingSubjectId: null, accountSettledSubjectId: null, signingOutSubjectId: action.subjectId }
        : state;
    case "RESTORE_AFTER_SIGNOUT_FAILURE":
      return state.session?.user.id === action.subjectId
        ? { ...state, accountLoadingSubjectId: action.subjectId, accountSettledSubjectId: null, signingOutSubjectId: null, reloadNonce: state.reloadNonce + 1 }
        : state;
  }
}

type AuthContextState = {
  session: Session | null;
  account: CurrentAccount | null;
  loading: boolean;
  recoveryStatus: RecoveryStatus;
  signOut: () => Promise<void>;
};

type E2eWindow = Window & {
  __mynutriE2ERefreshSession?: () => ReturnType<ReturnType<typeof createClient>["auth"]["refreshSession"]>;
  __mynutriE2ESignOut?: () => ReturnType<ReturnType<typeof createClient>["auth"]["signOut"]>;
  __mynutriE2ESignInWithPassword?: (email: string, password: string) => ReturnType<ReturnType<typeof createClient>["auth"]["signInWithPassword"]>;
  __mynutriE2EDuplicateSession?: () => Promise<void>;
  __mynutriE2EHoldFingerprint?: () => Promise<void>;
  __mynutriE2EVerifyRecoveryOtp?: (email: string, token: string) => ReturnType<ReturnType<typeof createClient>["auth"]["verifyOtp"]>;
};

const AuthContext = createContext<AuthContextState | null>(null);

function allowE2eAuthControl() {
  return (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY === "e2e-public-key";
}

function recoveryAttemptFromLocation(): RecoveryAttempt {
  if (typeof window === "undefined") return "none";
  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  if (search.has("error") || search.has("error_code") || hash.has("error") || hash.has("error_code")) return "invalid";
  if (search.has("code") || search.get("type") === "recovery" || hash.get("type") === "recovery") return "pending";
  return "none";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const router = useRouter();
  const pathname = usePathname();
  const pathnameRef = useRef(pathname);
  const mountedRef = useRef(true);
  const subjectRef = useRef<string | null>(null);
  const accessTokenRef = useRef<string | null>(null);
  const acceptedSessionSubjectRef = useRef<string | null>(null);
  const acceptedAccessTokenRef = useRef<string | null>(null);
  const hasAcceptedSessionRef = useRef(false);
  const requestGeneration = useRef(0);
  const recoveryAttemptRef = useRef<RecoveryAttempt>("none");

  useEffect(() => {
    pathnameRef.current = pathname;
  }, [pathname]);

  useEffect(() => {
    recoveryAttemptRef.current = recoveryAttemptFromLocation();
    const supabase = createClient();
    const e2eWindow = window as E2eWindow;
    const e2eAuthControlAllowed = allowE2eAuthControl();
    let active = true;
    mountedRef.current = true;
    const acceptSession = (nextSession: Session | null) => {
      const nextSubject = nextSession?.user.id ?? null;
      const nextAccessToken = nextSession?.access_token ?? null;
      if (
        hasAcceptedSessionRef.current &&
        acceptedSessionSubjectRef.current === nextSubject &&
        acceptedAccessTokenRef.current === nextAccessToken
      ) return;
      hasAcceptedSessionRef.current = true;
      acceptedSessionSubjectRef.current = nextSubject;
      acceptedAccessTokenRef.current = nextAccessToken;
      subjectRef.current = nextSubject;
      accessTokenRef.current = nextAccessToken;
      requestGeneration.current += 1;
      dispatch({ type: "AUTH_CHANGED", session: nextSession });
    };
    const initialGeneration = requestGeneration.current;
    void supabase.auth.getSession().then(({ data }) => {
      if (active && requestGeneration.current === initialGeneration) acceptSession(data.session);
    });
    const { data } = supabase.auth.onAuthStateChange((event, nextSession) => {
      dispatch({ type: "RECOVERY_EVENT", event, session: nextSession, attempt: recoveryAttemptRef.current });
      acceptSession(nextSession);
    });
    if (e2eAuthControlAllowed) {
      e2eWindow.__mynutriE2ERefreshSession = () => supabase.auth.refreshSession();
      e2eWindow.__mynutriE2ESignOut = () => supabase.auth.signOut();
      e2eWindow.__mynutriE2ESignInWithPassword = (email, password) => supabase.auth.signInWithPassword({ email, password });
      e2eWindow.__mynutriE2EDuplicateSession = async () => {
        const { data } = await supabase.auth.getSession();
        acceptSession(data.session);
      };
      e2eWindow.__mynutriE2EVerifyRecoveryOtp = (email, token) => supabase.auth.verifyOtp({ email, token, type: "recovery" });
    }
    return () => {
      active = false;
      mountedRef.current = false;
      requestGeneration.current += 1;
      data.subscription.unsubscribe();
      if (e2eAuthControlAllowed) {
        delete e2eWindow.__mynutriE2ERefreshSession;
        delete e2eWindow.__mynutriE2ESignOut;
        delete e2eWindow.__mynutriE2ESignInWithPassword;
        delete e2eWindow.__mynutriE2EDuplicateSession;
        delete e2eWindow.__mynutriE2EVerifyRecoveryOtp;
      }
    };
  }, []);

  const subjectId = state.session?.user.id ?? null;
  const accessToken = state.session?.access_token;
  useEffect(() => {
    if (!subjectId || !accessToken || state.signingOutSubjectId === subjectId) return;
    const generation = ++requestGeneration.current;
    const controller = new AbortController();
    const isCurrent = () => !controller.signal.aborted && mountedRef.current && requestGeneration.current === generation && subjectRef.current === subjectId;
    void (async () => {
      const marker = document.cookie.split("; ").find((value) => value.startsWith("mynutri-auth-invalid-token="))?.split("=")[1];
      const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(accessToken));
      const fingerprint = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
      if (!isCurrent()) return;
      if (marker === fingerprint) {
        dispatch({ type: "SIGNING_OUT", subjectId });
        return;
      }
      dispatch({ type: "ACCOUNT_REQUEST", subjectId });
      return getCurrentAccount({ accessToken, signal: controller.signal });
    })()
      .then((account) => {
        if (!account) return;
        if (!isCurrent()) return;
        if (account.auth_user_id !== subjectId) throw new ApiError("Account identity mismatch", 401);
        dispatch({ type: "ACCOUNT_RECEIVED", subjectId, account });
      })
      .catch(async (error: unknown) => {
        if (controller.signal.aborted || !isCurrent()) return;
        if (error instanceof ApiError && error.status === 401) {
          requestGeneration.current += 1;
          const signingOutGeneration = requestGeneration.current;
          dispatch({ type: "SIGNING_OUT", subjectId });
          if (subjectRef.current === subjectId) {
            if (allowE2eAuthControl()) {
              try {
                await (window as E2eWindow).__mynutriE2EHoldFingerprint?.();
              } catch {
                // Test instrumentation must never alter production 401 recovery.
              }
            }
            const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(accessToken));
            const fingerprint = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
            if (
              !mountedRef.current ||
              requestGeneration.current !== signingOutGeneration ||
              subjectRef.current !== subjectId ||
              accessTokenRef.current !== accessToken
            ) return;
            document.cookie = `mynutri-auth-invalid-token=${fingerprint}; Path=/; Max-Age=60; SameSite=Lax`;
            window.location.assign(`/auth/login?next=${encodeURIComponent(pathnameRef.current)}`);
          }
        }
      })
      .finally(() => {
        if (isCurrent()) dispatch({ type: "ACCOUNT_COMPLETE", subjectId });
      });
    return () => controller.abort();
  }, [accessToken, state.reloadNonce, state.signingOutSubjectId, subjectId, router]);

  const exposedAccount = state.accountSubjectId === subjectId && state.signingOutSubjectId !== subjectId ? state.account : null;
  const loading = !state.initialized || Boolean(subjectId && (
    state.accountLoadingSubjectId === subjectId ||
    (state.accountSubjectId !== subjectId && state.accountSettledSubjectId !== subjectId)
  ));
  const value = useMemo<AuthContextState>(() => ({
    session: state.session,
    account: exposedAccount,
    loading,
    recoveryStatus: state.recoveryStatus,
    signOut: async () => {
      const currentSubject = subjectRef.current;
      if (!currentSubject) {
        router.replace("/auth/login");
        return;
      }
      requestGeneration.current += 1;
      dispatch({ type: "SIGNING_OUT", subjectId: currentSubject });
      let signOutError: unknown = null;
      try {
        signOutError = (await createClient().auth.signOut()).error;
      } catch (signOutFailure) {
        signOutError = signOutFailure;
      }
      if (!signOutError) {
        router.replace("/auth/login");
        return;
      }
      const { data } = await createClient().auth.getSession();
      if (data.session?.user.id === currentSubject && subjectRef.current === currentSubject) {
        dispatch({ type: "RESTORE_AFTER_SIGNOUT_FAILURE", subjectId: currentSubject });
      } else if (!data.session) {
        router.replace("/auth/login");
      }
    }
  }), [exposedAccount, loading, router, state.recoveryStatus, state.session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
