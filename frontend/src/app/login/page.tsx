"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ShieldCheck, UserRound } from "lucide-react";
import { login } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import { Button, Input } from "@/components/ui/primitives";
import { LangToggle } from "@/components/shell/AppShell";

// The seeded demo accounts (backend/app/config.py). One click signs a judge or visitor straight in.
const DEMO_ACCOUNTS = [
  { username: "analyst", password: "analyst123", role: "analyst", Icon: UserRound },
  { username: "admin", password: "admin123", role: "admin", Icon: ShieldCheck },
] as const;

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const { t } = useLang();
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("");
  // Which button is working: "form" for the Sign in button, or a demo account's username.
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function signIn(user: string, pass: string, source: string) {
    setBusy(source);
    setErr(null);
    try {
      const r = await login(user.trim(), pass);
      setSession(r.access_token, r.user);
      router.replace(params.get("next") || "/");
    } catch {
      setErr(t("loginFailed"));
      setBusy(null);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    signIn(username, password, "form");
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      {/* Brand side */}
      <aside className="relative hidden overflow-hidden bg-primary text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div aria-hidden className="pointer-events-none absolute -end-32 -top-32 size-[28rem] rounded-full bg-white/10" />
        <div aria-hidden className="pointer-events-none absolute -bottom-40 -start-20 size-[30rem] rounded-full bg-accent/30 blur-2xl" />
        <div className="relative flex items-center gap-3">
          <Image src="/icon-256.png" alt="" width={44} height={44} className="size-11 rounded-xl" />
          <span className="text-lg font-extrabold">{t("appName")}</span>
        </div>
        <div className="relative max-w-md">
          <h2 className="text-4xl font-extrabold leading-tight tracking-tight">{t("tagline")}</h2>
          <p className="mt-4 text-lg text-white/80">{t("radarSub")}</p>
        </div>
        <p className="relative text-sm text-white/70">{t("teamName")}</p>
      </aside>

      {/* Form side */}
      <div className="flex flex-col px-6 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 lg:invisible">
            <Image src="/icon-256.png" alt="" width={32} height={32} className="size-8 rounded-lg" />
            <span className="font-extrabold">{t("appName")}</span>
          </Link>
          <LangToggle />
        </div>

        <form onSubmit={submit} className="my-auto w-full max-w-sm self-center py-10">
          <h1 className="text-2xl font-extrabold tracking-tight text-ink">{t("loginTitle")}</h1>
          <p className="mt-2 text-sm text-muted">{t("loginSub")}</p>

          <label className="mt-8 block text-sm font-bold text-ink" htmlFor="u">
            {t("username")}
          </label>
          <Input id="u" className="mt-1.5 ltr" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />

          <label className="mt-4 block text-sm font-bold text-ink" htmlFor="p">
            {t("password")}
          </label>
          <Input id="p" className="mt-1.5 ltr" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />

          {err && (
            <p role="alert" className="mt-3 rounded-xl bg-fraud-soft px-3 py-2 text-sm font-semibold text-fraud">
              {err}
            </p>
          )}

          <Button type="submit" size="lg" className="mt-6 w-full" loading={busy === "form"} disabled={!!busy}>
            {t("signIn")}
          </Button>

          <div className="mt-8 flex items-center gap-3 text-xs font-bold text-muted">
            <span aria-hidden className="h-px flex-1 bg-line-2" />
            {t("demoAccounts")}
            <span aria-hidden className="h-px flex-1 bg-line-2" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {DEMO_ACCOUNTS.map(({ username: u, password: p, role, Icon }) => (
              <Button
                key={u}
                type="button"
                variant="outline"
                className="h-auto flex-col gap-1 rounded-2xl py-3"
                loading={busy === u}
                disabled={!!busy}
                onClick={() => signIn(u, p, u)}
              >
                {busy !== u && <Icon aria-hidden className="size-5 text-primary" />}
                <span>{t("demoAs", { role: t(`role_${role}`) })}</span>
                <span className="ltr text-xs font-semibold text-muted">
                  {u} / {p}
                </span>
              </Button>
            ))}
          </div>

          <p className="mt-8 text-center text-sm text-muted">
            <Link href="/check" className="font-bold text-primary underline">
              {t("goCitizen")}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
