"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";
import { useBrands, useRadarFeed, type CaseSummary } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtAgo } from "@/lib/utils";
import { BrandChip, SourceTag, StatusTag, VerdictChip } from "@/components/ui/verdict";
import { ErrorState, Skeleton } from "@/components/ui/primitives";

const SOURCE_ORDER = ["lookalike", "ct", "nrd", "search", "search_ad", "maps"];

export default function RadarPage() {
  const { t, lang, pick } = useLang();
  const { data, error, isLoading, mutate } = useRadarFeed(50);
  const { data: brands } = useBrands();
  const [source, setSource] = useState<string | null>(null);

  const brandName = (id: string | null) => {
    if (!id) return null;
    const b = brands?.find((x) => x.id === id);
    return b ? pick(b as unknown as Record<string, unknown>, "name") : id;
  };

  const items = useMemo(() => {
    const all = data?.items ?? [];
    return source ? all.filter((i) => i.source === source) : all;
  }, [data, source]);

  const total = data?.items.length ?? 0;
  const fraud = data?.items.filter((i) => i.verdict === "FRAUD").length ?? 0;

  return (
    <div className="mx-auto max-w-6xl">
      {/* Headline: a sentence, not a stat row */}
      <div className="mb-6 flex flex-col gap-2 pt-2">
        <p className="inline-flex items-center gap-2 text-sm font-bold text-ink-2">
          <span aria-hidden className="radar-dot inline-block size-2.5 rounded-full bg-accent" />
          {t("radarLive")}
        </p>
        <h1 className="max-w-3xl text-3xl font-extrabold leading-[1.15] tracking-tight text-ink sm:text-4xl">
          {isLoading ? (
            <Skeleton className="h-10 w-3/4" />
          ) : total === 0 ? (
            t("radarHeadlineNone")
          ) : (
            <>
              {t("radarHeadline", { n: total })}{" "}
              {fraud > 0 && <span className="text-fraud">{t("radarHeadlineFraud", { f: fraud })}</span>}
            </>
          )}
        </h1>
        <p className="max-w-2xl text-base text-muted">{t("radarSub")}</p>
      </div>

      {/* Source filter: counts the radar actually produced */}
      <div role="group" aria-label={t("bySource")} className="mb-4 flex flex-wrap gap-2">
        <FilterChip active={source === null} onClick={() => setSource(null)} count={total}>
          {t("allSources")}
        </FilterChip>
        {SOURCE_ORDER.map((s) => {
          const n = data?.counts_by_source?.[s] ?? 0;
          return (
            <FilterChip key={s} active={source === s} onClick={() => setSource(source === s ? null : s)} count={n} disabled={n === 0}>
              {t(`src_${s}` as Parameters<typeof t>[0])}
            </FilterChip>
          );
        })}
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[76px] rounded-[16px]" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-[16px] border border-dashed border-line-2 p-10 text-center text-muted">{t("emptyRadar")}</div>
      ) : (
        <ol className="overflow-hidden rounded-[16px] border border-line bg-surface">
          {items.map((c, i) => (
            <RadarRow key={c.id} c={c} brand={brandName(c.brand_target)} lang={lang} first={i === 0} />
          ))}
        </ol>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, count, disabled, children }: { active: boolean; onClick: () => void; count: number; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      disabled={disabled}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-full border px-3.5 text-sm font-bold transition-colors disabled:opacity-40",
        active ? "border-primary bg-primary text-primary-ink" : "border-line-2 bg-surface text-ink-2 hover:bg-surface-2",
      )}
    >
      {children}
      <span className={cn("rounded-full px-1.5 text-xs tabular-nums ltr", active ? "bg-white/20" : "bg-surface-2 text-muted")}>{count}</span>
    </button>
  );
}

function RadarRow({ c, brand, lang, first }: { c: CaseSummary; brand: string | null; lang: "en" | "ar"; first: boolean }) {
  const { t } = useLang();
  return (
    <li className={cn(!first && "border-t border-line")}>
      <Link
        href={`/cases/${c.id}`}
        className="group grid grid-cols-[auto_1fr_auto] items-center gap-x-4 gap-y-2 px-4 py-4 transition-colors hover:bg-surface-2 focus-visible:bg-surface-2 sm:grid-cols-[8.5rem_1fr_auto_auto] sm:px-5"
      >
        <VerdictChip verdict={c.verdict} size="md" className="justify-self-start" />

        <div className="min-w-0">
          <p className="ltr truncate text-base font-extrabold text-ink">{c.domain}</p>
          <p className="ltr truncate text-sm text-muted">{c.url}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 sm:hidden">
            <SourceTag source={c.source} />
            <BrandChip brandId={c.brand_target} name={brand} />
          </div>
        </div>

        <div className="hidden flex-col items-end gap-1.5 sm:flex">
          <SourceTag source={c.source} />
          {c.brand_target ? (
            <span className="text-xs text-muted">
              {t("targets")} <BrandChip brandId={c.brand_target} name={brand} className="ms-1" />
            </span>
          ) : (
            <span className="text-xs text-muted">{t("noBrand")}</span>
          )}
        </div>

        <div className="flex items-center gap-3 justify-self-end">
          <div className="hidden text-end sm:block">
            <p className="text-sm font-bold text-ink tabular-nums">{fmtAgo(c.discovered_at, lang)}</p>
            <StatusTag status={c.status} className="mt-1" />
          </div>
          <ChevronRight aria-hidden className="size-5 text-muted transition-transform group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5" />
        </div>
      </Link>
    </li>
  );
}
