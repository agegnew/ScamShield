"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ALargeSmall, ClipboardList, FolderOpen, Languages, LogOut, Radar, ScanSearch, Share2, Smartphone, Target, UsersRound } from "lucide-react";
import { useLang } from "@/lib/i18n";
import { apiMode, me, onMode, useHealth } from "@/lib/api";
import { clearSession, getToken, getUser, setSession, type User } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function useSession() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    const read = () => setUser(getUser());
    read();
    window.addEventListener("scamshield:auth", read);
    // Confirm the stored token with the server once; a 401 inside apiFetch clears the session.
    const token = getToken();
    if (token) {
      me()
        .then((u) => setSession(token, u))
        .catch(() => {});
    }
    return () => window.removeEventListener("scamshield:auth", read);
  }, []);
  return user;
}

export function ModeBadge({ className }: { className?: string }) {
  const { t } = useLang();
  const [mode, setMode] = useState(apiMode);
  const { error } = useHealth();
  useEffect(() => onMode(setMode), []);
  if (error) {
    return (
      <span className={cn("inline-flex items-center gap-1.5 rounded-full bg-fraud-soft px-2.5 py-1 text-xs font-bold text-fraud", className)}>
        <span aria-hidden className="size-1.5 rounded-full bg-fraud" />
        {t("apiOffline")}
      </span>
    );
  }
  if (mode === "mock") {
    return (
      <span title={t("demoDataHint")} className={cn("inline-flex items-center gap-1.5 rounded-full bg-review-soft px-2.5 py-1 text-xs font-bold text-review", className)}>
        <span aria-hidden className="size-1.5 rounded-full bg-review" />
        {t("demoData")}
      </span>
    );
  }
  if (mode === "live") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 rounded-full bg-safe-soft px-2.5 py-1 text-xs font-bold text-safe", className)}>
        <span aria-hidden className="radar-dot size-1.5 rounded-full bg-accent" />
        {t("liveData")}
      </span>
    );
  }
  return null;
}

export function LangToggle({ className }: { className?: string }) {
  const { t, toggleLang } = useLang();
  return (
    <button
      type="button"
      onClick={toggleLang}
      aria-label={t("switchLang")}
      className={cn("inline-flex h-10 items-center gap-2 rounded-full border border-line-2 bg-surface px-3.5 text-sm font-bold text-ink hover:bg-surface-2", className)}
    >
      <Languages aria-hidden className="size-4 text-primary" />
      <span lang={t("language") === "English" ? "en" : "ar"}>{t("language")}</span>
    </button>
  );
}

export function TextSizeToggle({ className }: { className?: string }) {
  const { t, textSize, setTextSize } = useLang();
  const large = textSize === "large";
  return (
    <button
      type="button"
      onClick={() => setTextSize(large ? "normal" : "large")}
      aria-pressed={large}
      aria-label={large ? t("textNormal") : t("textLarger")}
      title={large ? t("textNormal") : t("textLarger")}
      className={cn("inline-grid size-10 place-items-center rounded-full border border-line-2 bg-surface text-ink hover:bg-surface-2", large && "bg-primary-soft border-primary-soft-2 text-primary", className)}
    >
      <ALargeSmall aria-hidden className="size-5" />
    </button>
  );
}

const NAV = [
  { href: "/", key: "navRadar", Icon: Radar },
  { href: "/cases", key: "navCases", Icon: FolderOpen },
  { href: "/graph", key: "navNetwork", Icon: Share2 },
  { href: "/accuracy", key: "navAccuracy", Icon: Target },
] as const;

const ADMIN_NAV = [
  { href: "/audit", key: "navAudit", Icon: ClipboardList },
  { href: "/users", key: "navUsers", Icon: UsersRound },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { t } = useLang();
  const pathname = usePathname();
  const router = useRouter();
  const user = useSession();

  useEffect(() => {
    if (user === null) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [user, pathname, router]);

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <a href="#main" className="skip-link">
        {t("skipToContent")}
      </a>

      {/* Side rail (desktop) */}
      <nav aria-label="Main" className="hidden lg:flex lg:w-60 lg:shrink-0 lg:flex-col lg:border-e lg:border-line lg:bg-surface lg:px-4 lg:py-5 lg:sticky lg:top-0 lg:h-dvh">
        <Link href="/" className="flex items-center gap-3 rounded-xl px-2 py-1.5">
          <Image src="/icon-256.png" alt="" width={40} height={40} className="size-10 rounded-xl" priority />
          <span className="leading-tight">
            <span className="block text-base font-extrabold text-ink">{t("appName")}</span>
            <span className="block text-xs text-muted">{t("analystConsole")}</span>
          </span>
        </Link>

        <ul className="mt-6 flex flex-col gap-1">
          {NAV.map(({ href, key, Icon }) => (
            <li key={href}>
              <Link
                href={href}
                aria-current={isActive(href) ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-colors",
                  isActive(href) ? "bg-primary-soft text-primary" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
                )}
              >
                <Icon aria-hidden className="size-5" strokeWidth={2.25} />
                {t(key)}
              </Link>
            </li>
          ))}
          <li className="mt-2 border-t border-line pt-2">
            <Link href="/scan" aria-current={isActive("/scan") ? "page" : undefined} className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-colors", isActive("/scan") ? "bg-primary-soft text-primary" : "text-ink-2 hover:bg-surface-2 hover:text-ink")}>
              <ScanSearch aria-hidden className="size-5" strokeWidth={2.25} />
              {t("navScan")}
            </Link>
          </li>
          <li>
            <Link href="/check" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink">
              <Smartphone aria-hidden className="size-5" strokeWidth={2.25} />
              {t("navChecker")}
            </Link>
          </li>
          {user?.role === "admin" && (
            <>
              <li className="mt-2 border-t border-line px-3 pt-3 text-xs font-bold text-muted">{t("adminOnly")}</li>
              {ADMIN_NAV.map(({ href, key, Icon }) => (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={isActive(href) ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-colors",
                      isActive(href) ? "bg-primary-soft text-primary" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
                    )}
                  >
                    <Icon aria-hidden className="size-5" strokeWidth={2.25} />
                    {t(key)}
                  </Link>
                </li>
              ))}
            </>
          )}
        </ul>

        <div className="mt-auto flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <LangToggle className="flex-1" />
            <TextSizeToggle />
          </div>
          {user && (
            <div className="flex items-center justify-between gap-2 rounded-xl bg-surface-2 px-3 py-2">
              <div className="min-w-0 leading-tight">
                <p className="truncate text-sm font-bold text-ink">{user.username}</p>
                <p className="text-xs text-muted">{t(`role_${user.role}`)}</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  clearSession();
                  router.replace("/login");
                }}
                aria-label={t("signOut")}
                title={t("signOut")}
                className="grid size-9 place-items-center rounded-full text-ink-2 hover:bg-surface hover:text-ink"
              >
                <LogOut aria-hidden className="size-4" />
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Top bar (mobile) */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-surface/90 px-4 py-3 backdrop-blur lg:hidden">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/icon-256.png" alt="" width={32} height={32} className="size-8 rounded-lg" />
          <span className="text-base font-extrabold">{t("appName")}</span>
        </Link>
        <div className="flex items-center gap-2">
          <ModeBadge />
          <LangToggle />
        </div>
      </header>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="hidden items-center justify-end gap-3 px-8 pt-5 lg:flex">
          <ModeBadge />
        </div>
        <main id="main" className="flex-1 px-4 pb-24 pt-4 sm:px-6 lg:px-8 lg:pb-10 lg:pt-3">
          {children}
        </main>
      </div>

      {/* Bottom nav (mobile) */}
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface px-1 py-1.5 lg:hidden">
        {[...NAV, { href: "/scan", key: "navScan", Icon: ScanSearch } as const].map(({ href, key, Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(href) ? "page" : undefined}
            className={cn("flex flex-col items-center gap-0.5 rounded-xl py-1.5 text-[11px] font-bold", isActive(href) ? "text-primary" : "text-muted")}
          >
            <Icon aria-hidden className="size-5" strokeWidth={2.25} />
            <span className="truncate">{t(key)}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
