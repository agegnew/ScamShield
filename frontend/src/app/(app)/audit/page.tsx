"use client";

import Link from "next/link";
import { useDecisions } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtTime } from "@/lib/utils";
import { useSession } from "@/components/shell/AppShell";
import { ErrorState, Skeleton } from "@/components/ui/primitives";

export default function AuditPage() {
  const { t, lang } = useLang();
  const user = useSession();
  const isAdmin = user?.role === "admin";
  const { data, error, isLoading, mutate } = useDecisions(isAdmin, 200);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("auditTitle")}</h1>
        <p className="mt-1 text-muted">{t("auditSub")}</p>
      </div>

      {user && !isAdmin ? (
        <p role="alert" className="rounded-[16px] border border-line bg-surface p-8 text-center text-muted">
          {t("forbidden")}
        </p>
      ) : error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : isLoading || !data ? (
        <Skeleton className="h-64 rounded-[16px]" />
      ) : data.length === 0 ? (
        <p className="rounded-[16px] border border-dashed border-line-2 p-10 text-center text-muted">{t("noDecisions")}</p>
      ) : (
        <div className="overflow-hidden rounded-[16px] border border-line bg-surface">
          <div className="overflow-x-auto thin-scroll">
            <table className="w-full min-w-[42rem] text-sm">
              <thead>
                <tr className="text-xs text-muted">
                  <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colWhen")}</th>
                  <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colAction")}</th>
                  <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colDomain")}</th>
                  <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colReason")}</th>
                  <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colBy")}</th>
                </tr>
              </thead>
              <tbody>
                {data.map((d, i) => (
                  <tr key={`${d.case_id}-${d.at}-${i}`} className="border-t border-line">
                    <td className="whitespace-nowrap px-4 py-3 text-ink-2 tabular-nums">
                      <time dateTime={d.at}>{fmtTime(d.at, lang)}</time>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("rounded-full px-2.5 py-1 text-xs font-bold", d.action === "confirm" ? "bg-fraud-soft text-fraud" : "bg-surface-2 text-ink-2")}>
                        {d.action === "confirm" ? t("st_confirmed") : t("st_dismissed")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/cases/${d.case_id}`} className="ltr font-extrabold text-ink hover:underline">
                        {d.domain}
                      </Link>
                      <span className="ltr block text-xs text-muted">{d.case_id}</span>
                    </td>
                    <td className="max-w-[24rem] px-4 py-3 text-ink-2">{d.reason}</td>
                    <td className="px-4 py-3 font-bold text-ink">{d.by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
