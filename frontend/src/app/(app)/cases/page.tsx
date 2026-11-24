"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { useBrands, useCases } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { fmtTime } from "@/lib/utils";
import { BrandChip, SourceTag, StatusTag, VerdictChip } from "@/components/ui/verdict";
import { Button, ErrorState, Input, Select, Skeleton } from "@/components/ui/primitives";

const SOURCES = ["lookalike", "ct", "nrd", "search", "search_ad", "maps", "manual", "citizen", "batch"];

export default function CasesPage() {
  return (
    <Suspense>
      <CasesInner />
    </Suspense>
  );
}

function CasesInner() {
  const { t, lang, pick } = useLang();
  const router = useRouter();
  const sp = useSearchParams();
  const { data: brands } = useBrands();

  const verdict = sp.get("verdict") ?? "";
  const source = sp.get("source") ?? "";
  const brand = sp.get("brand") ?? "";
  const status = sp.get("status") ?? "";
  const q = sp.get("q") ?? "";
  const [qDraft, setQDraft] = useState(q);

  const setParam = useCallback(
    (k: string, v: string) => {
      const n = new URLSearchParams(sp.toString());
      if (v) n.set(k, v);
      else n.delete(k);
      router.replace(`/cases${n.toString() ? `?${n}` : ""}`);
    },
    [sp, router],
  );

  useEffect(() => {
    const h = setTimeout(() => {
      if (qDraft !== q) setParam("q", qDraft);
    }, 300);
    return () => clearTimeout(h);
  }, [qDraft, q, setParam]);

  const { data, error, isLoading, mutate } = useCases({ verdict, source, brand, status, q, limit: 100 });
  const anyFilter = Boolean(verdict || source || brand || status || q);
  const brandName = (id: string | null) => {
    if (!id) return null;
    const b = brands?.find((x) => x.id === id);
    return b ? pick(b as unknown as Record<string, unknown>, "name") : id;
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("casesTitle")}</h1>
        <p className="mt-1 text-muted">{t("casesSub")}</p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[16rem] flex-1">
          <Search aria-hidden className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input aria-label={t("search")} placeholder={t("search")} value={qDraft} onChange={(e) => setQDraft(e.target.value)} className="h-10 ps-9 ltr" />
        </div>
        <Select aria-label={t("filterVerdict")} value={verdict} onChange={(e) => setParam("verdict", e.target.value)}>
          <option value="">{t("filterVerdict")}: {t("all")}</option>
          {(["FRAUD", "SUSPICIOUS", "LEGIT"] as const).map((v) => (
            <option key={v} value={v}>
              {t(v)}
            </option>
          ))}
        </Select>
        <Select aria-label={t("filterSource")} value={source} onChange={(e) => setParam("source", e.target.value)}>
          <option value="">{t("filterSource")}: {t("all")}</option>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {t(`src_${s}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </Select>
        <Select aria-label={t("filterBrand")} value={brand} onChange={(e) => setParam("brand", e.target.value)}>
          <option value="">{t("filterBrand")}: {t("all")}</option>
          {(brands ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {pick(b as unknown as Record<string, unknown>, "name")}
            </option>
          ))}
        </Select>
        <Select aria-label={t("filterStatus")} value={status} onChange={(e) => setParam("status", e.target.value)}>
          <option value="">{t("filterStatus")}: {t("all")}</option>
          {(["new", "confirmed", "dismissed"] as const).map((s) => (
            <option key={s} value={s}>
              {t(`st_${s}`)}
            </option>
          ))}
        </Select>
        {anyFilter && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setQDraft("");
              router.replace("/cases");
            }}
          >
            <X aria-hidden className="size-4" /> {t("clearFilters")}
          </Button>
        )}
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : isLoading && !data ? (
        <Skeleton className="h-96 rounded-[16px]" />
      ) : (
        <div className="overflow-hidden rounded-[16px] border border-line bg-surface">
          <p className="border-b border-line px-4 py-2.5 text-sm font-bold text-ink-2">{t("results", { n: data?.total ?? 0 })}</p>
          {(data?.items.length ?? 0) === 0 ? (
            <p className="p-10 text-center text-muted">{t("noResults")}</p>
          ) : (
            <div className="overflow-x-auto thin-scroll">
              <table className="w-full min-w-[46rem] text-sm">
                <thead>
                  <tr className="text-start text-xs text-muted">
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colVerdict")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colDomain")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colSource")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colBrand")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colFound")}</th>
                    <th scope="col" className="px-4 py-2.5 text-start font-bold">{t("colStatus")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data!.items.map((c) => (
                    <tr key={c.id} className="border-t border-line transition-colors hover:bg-surface-2">
                      <td className="px-4 py-3">
                        <VerdictChip verdict={c.verdict} size="sm" />
                        <span className="ltr ms-2 text-xs font-bold text-muted tabular-nums">{c.score}</span>
                      </td>
                      <td className="max-w-[20rem] px-4 py-3">
                        <Link href={`/cases/${c.id}`} className="ltr block truncate font-extrabold text-ink hover:underline">
                          {c.domain}
                        </Link>
                        <span className="ltr block truncate text-xs text-muted">{c.url}</span>
                      </td>
                      <td className="px-4 py-3">
                        <SourceTag source={c.source} />
                      </td>
                      <td className="px-4 py-3">
                        <BrandChip brandId={c.brand_target} name={brandName(c.brand_target)} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-ink-2 tabular-nums">{fmtTime(c.discovered_at, lang)}</td>
                      <td className="px-4 py-3">
                        <StatusTag status={c.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
