"use client";

import type { Session } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ApiError, getCurrentAccount, type CurrentAccount } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type AuthState = {
  session: Session | null;
  account: CurrentAccount | null;
  loading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [account, setAccount] = useState<CurrentAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      if (!data.session) setLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (!nextSession) {
        setAccount(null);
        setLoading(false);
      }
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!session) return;
    setLoading(true);
    getCurrentAccount()
      .then(setAccount)
      .catch(async (error) => {
        if (error instanceof ApiError && error.status === 401) {
          await createClient().auth.signOut();
          router.replace(`/auth/login?next=${encodeURIComponent(pathname)}`);
        }
      })
      .finally(() => setLoading(false));
  }, [session?.access_token, pathname, router]);

  const value = useMemo<AuthState>(
    () => ({
      session,
      account,
      loading,
      signOut: async () => {
        await createClient().auth.signOut();
        setAccount(null);
        router.replace("/auth/login");
      }
    }),
    [session, account, loading, router]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
