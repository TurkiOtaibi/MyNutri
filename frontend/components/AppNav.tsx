"use client";

import { CalendarDays, Salad, UserRound, Utensils } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/diary", label: "اليوميات", icon: CalendarDays },
  { href: "/foods", label: "الأطعمة", icon: Utensils },
  { href: "/profile", label: "الملف", icon: UserRound }
];

export function AppNav() {
  const pathname = usePathname();

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
          {links.map((link) => {
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
        </nav>
      </div>
    </header>
  );
}
