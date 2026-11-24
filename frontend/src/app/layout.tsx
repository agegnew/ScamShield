import type { Metadata, Viewport } from "next";
import { Nunito, Tajawal } from "next/font/google";
import "./globals.css";
import { LangProvider } from "@/lib/i18n";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  display: "swap",
});

const tajawal = Tajawal({
  variable: "--font-tajawal",
  subsets: ["arabic"],
  weight: ["400", "500", "700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "ScamShield", template: "%s · ScamShield" },
  description: "Finds UAE-brand scam sites before residents do. Check before you tap.",
  icons: { icon: "/icon-256.png" },
};

export const viewport: Viewport = {
  themeColor: "#6d28d9",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr" className={`${nunito.variable} ${tajawal.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col">
        <LangProvider>{children}</LangProvider>
      </body>
    </html>
  );
}
