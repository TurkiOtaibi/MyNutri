import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";

import { AppNav } from "@/components/AppNav";
import { Providers } from "@/components/Providers";

// IBM Plex Sans Arabic (SIL OFL 1.1, see ./fonts) is self-hosted so builds need no font network access.
const plexArabic = localFont({
  src: [
    { path: "./fonts/IBMPlexSansArabic-Regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/IBMPlexSansArabic-Bold.woff2", weight: "700", style: "normal" }
  ],
  variable: "--font-plex-arabic",
  display: "swap"
});

export const metadata: Metadata = {
  title: "myNutri",
  description: "متتبع تغذية شخصي يعمل عبر الاتصال بالخادم.",
  manifest: "/manifest.json",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg"
  }
};

export const viewport: Viewport = {
  themeColor: "#0f766e",
  viewportFit: "cover"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={plexArabic.variable}>
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
