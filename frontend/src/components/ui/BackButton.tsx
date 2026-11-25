"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useLang } from "@/lib/i18n";
import { L } from "@/lib/radar";
import { cn } from "@/lib/utils";

/** Back that always does something: the previous page when the visit has one,
 *  otherwise `fallback` (a page opened in a new tab or from the browser extension has no history). */
export function BackButton({ fallback, onBack, className }: { fallback: string; onBack?: () => void; className?: string }) {
  const router = useRouter();
  const { lang } = useLang();
  return (
    <button
      type="button"
      onClick={() => {
        if (onBack) return onBack();
        const pages = Number(sessionStorage.getItem(NAV_KEY) || "0");
        if (pages > 1 && window.history.length > 1) router.back();
        else router.push(fallback);
      }}
      className={cn("inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-sm font-bold text-ink-2 hover:bg-surface-2 hover:text-ink", className)}
    >
      <ArrowLeft aria-hidden className="size-4 rtl:rotate-180" />
      {L(["Back", "رجوع"], lang)}
    </button>
  );
}

const NAV_KEY = "scamshield-pages-this-tab";

/** Counts pages opened in this tab (mounted once in the root layout), so Back knows whether there is one to go to. */
export function NavTracker() {
  const pathname = usePathname();
  useEffect(() => {
    sessionStorage.setItem(NAV_KEY, String(Number(sessionStorage.getItem(NAV_KEY) || "0") + 1));
  }, [pathname]);
  return null;
}
