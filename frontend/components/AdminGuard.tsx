"use client";

import { useAuth } from "./AuthProvider";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { account, loading } = useAuth();
  if (loading) return <div className="state-note">جارٍ التحقق من الصلاحية...</div>;
  if (account?.role !== "admin") {
    return <div className="state-note" role="alert">هذه الصفحة متاحة للمشرف فقط.</div>;
  }
  return children;
}
