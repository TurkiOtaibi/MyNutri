import type { Metadata, Viewport } from "next";
import "./globals.css";

import { AppNav } from "@/components/AppNav";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "myNutri",
  description: "متتبع تغذية شخصي يعمل دون اتصال.",
  manifest: "/manifest.json",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg"
  }
};

export const viewport: Viewport = {
  themeColor: "#0f766e"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <Providers>
          <div className="app-shell">
            <AppNav />
            <main className="main-surface">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
