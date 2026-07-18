"use client";

import { CalendarDays, LogOut, Salad, Shield, UserRound, Utensils } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "./AuthProvider";

const links = [
  { href: "/diary", label: "اليوميات", icon: CalendarDays },
  { href: "/foods", label: "الأطعمة", icon: Utensils },
  { href: "/profile", label: "الملف", icon: UserRound }
];

export function AppNav() {
  const pathname = usePathname();
  const { account, loading, signOut } = useAuth();
  if (pathname.startsWith("/auth/")) return null;
  const visibleLinks = account?.role === "admin"
    ? [...links, { href: "/admin", label: "الإدارة", icon: Shield }]
    : links;

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        <Link className="brand" href="/diary">
          <span className="brand-mark" aria-hidden="true">
            <Salad size={21} />
          </span>
          <span>myNutri</span>
        </Link>
        <nav className="nav-links" aria-label="التنقل الرئيسي">
          {visibleLinks.map((link) => {
            const Icon = link.icon;
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                className={`nav-link ${active ? "active" : ""}`}
                href={link.href}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} />
                <span>{link.label}</span>
              </Link>
            );
          })}
          {!loading ? (
            <button className="nav-link nav-signout" type="button" onClick={() => void signOut()} title="تسجيل الخروج">
              <LogOut size={18} />
              <span className="sr-only">تسجيل الخروج</span>
            </button>
          ) : null}
        </nav>
      </div>
    </header>
  );
}
