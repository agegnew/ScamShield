"use client";

import { useState } from "react";
import { Check, Plus } from "lucide-react";
import { ApiError, createUser, useUsers } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtTime } from "@/lib/utils";
import { useSession } from "@/components/shell/AppShell";
import { Button, ErrorState, Input, Panel, PanelTitle, Select, Skeleton } from "@/components/ui/primitives";

export default function UsersPage() {
  const { t, lang } = useLang();
  const user = useSession();
  const isAdmin = user?.role === "admin";
  const { data, error, isLoading, mutate } = useUsers(isAdmin);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "analyst">("analyst");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await createUser(username.trim(), password, role);
      setMsg({ ok: true, text: t("userCreated") });
      setUsername("");
      setPassword("");
      mutate();
    } catch (ex) {
      const status = ex instanceof ApiError ? ex.status : 0;
      setMsg({ ok: false, text: status === 409 ? t("userExists") : ex instanceof Error ? ex.message : String(ex) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("usersTitle")}</h1>
        <p className="mt-1 text-muted">{t("usersSub")}</p>
      </div>

      {user && !isAdmin ? (
        <p role="alert" className="rounded-[16px] border border-line bg-surface p-8 text-center text-muted">
          {t("forbidden")}
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
          {error ? (
            <ErrorState error={error} onRetry={() => mutate()} />
          ) : isLoading || !data ? (
            <Skeleton className="h-48 rounded-[16px]" />
          ) : (
            <div className="overflow-hidden rounded-[16px] border border-line bg-surface">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-muted">
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("username")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("role")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("filterStatus")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("created")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((u) => (
                    <tr key={u.username} className="border-t border-line">
                      <td className="ltr px-4 py-3 font-extrabold text-ink">{u.username}</td>
                      <td className="px-4 py-3">
                        <span className={cn("rounded-full px-2.5 py-1 text-xs font-bold", u.role === "admin" ? "bg-primary-soft text-primary" : "bg-surface-2 text-ink-2")}>{t(`role_${u.role}`)}</span>
                      </td>
                      <td className="px-4 py-3 text-ink-2">{u.disabled ? t("disabled") : t("active")}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-ink-2 tabular-nums">{fmtTime(u.created_at, lang, { year: "numeric" })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Panel className="h-fit p-4">
            <PanelTitle>{t("addUser")}</PanelTitle>
            <form onSubmit={submit} className="mt-3 flex flex-col gap-3">
              <label className="text-sm font-bold text-ink" htmlFor="nu">
                {t("username")}
                <Input id="nu" className="ltr mt-1.5" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="off" />
              </label>
              <label className="text-sm font-bold text-ink" htmlFor="np">
                {t("password")}
                <Input id="np" className="ltr mt-1.5" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" placeholder={t("passwordMin")} />
              </label>
              <label className="text-sm font-bold text-ink" htmlFor="nr">
                {t("role")}
                <Select id="nr" className="mt-1.5 w-full" value={role} onChange={(e) => setRole(e.target.value as "admin" | "analyst")}>
                  <option value="analyst">{t("role_analyst")}</option>
                  <option value="admin">{t("role_admin")}</option>
                </Select>
              </label>
              {msg && (
                <p role="status" className={cn("flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold", msg.ok ? "bg-safe-soft text-safe" : "bg-fraud-soft text-fraud")}>
                  {msg.ok && <Check aria-hidden className="size-4" />}
                  {msg.text}
                </p>
              )}
              <Button type="submit" loading={busy}>
                <Plus aria-hidden className="size-4" />
                {t("addUser")}
              </Button>
            </form>
          </Panel>
        </div>
      )}
    </div>
  );
}
