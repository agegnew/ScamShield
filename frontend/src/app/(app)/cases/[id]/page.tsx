"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useBrands, useCase, type Case, type Reason } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtTime } from "@/lib/utils";
import { BrandChip, ScoreRing, SourceTag, StatusTag, VerdictChip } from "@/components/ui/verdict";
import { ErrorState, Panel, PanelTitle, Skeleton } from "@/components/ui/primitives";
import { CloakingPanel, DomainPanel, DownloadsPanel, FingerprintsPanel, FormsPanel, HostingPanel, MapsPanel, RedirectsPanel, ScreenshotPanel, TextPanel, refToBlock } from "@/components/case/Evidence";
import { DecisionPanel, ExportButtons, TakedownDialog } from "@/components/case/Actions";

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const { t, lang, pick } = useLang();
  const router = useRouter();
  const { data: brands } = useBrands();
  const [active, setActive] = useState<string | null>(null);
  const [takedownOpen, setTakedownOpen] = useState(false);

  // Poll every 2 s while the worker is still fetching the page.
  const { data, error, isLoading, mutate } = useCase(id, true);
  const c: Case | null = data ?? null;
  const onUpdated = (updated: Case) => mutate(updated, { revalidate: false });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key.toLowerCase() === "t") setTakedownOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const brand = useMemo(() => brands?.find((b) => b.id === c?.verdict.brand_target), [brands, c]);
  const brandName = brand ? pick(brand as unknown as Record<string, unknown>, "name") : c?.verdict.brand_target ?? null;

  if (error) return <ErrorState error={error} onRetry={() => mutate()} />;
  if (isLoading || !c) {
    return (
      <div className="mx-auto max-w-6xl">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="mt-4 h-10 w-2/3" />
        <div className="mt-6 grid gap-4 lg:grid-cols-[22rem_1fr]">
          <Skeleton className="h-[560px] rounded-[16px]" />
          <Skeleton className="h-[560px] rounded-[16px]" />
        </div>
      </div>
    );
  }

  const ev = c.evidence;
  const v = c.verdict;
  const offline = Boolean(ev?.fetch_error);
  const is = (block: string) => active === block;
  const select = (r: Reason) => {
    const block = refToBlock(r.evidence_ref);
    setActive((cur) => (cur === block ? null : block));
    if (block) document.getElementById(`ev-${block}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  return (
    <div className="mx-auto max-w-6xl">
      <button type="button" onClick={() => router.back()} className="inline-flex items-center gap-1.5 text-sm font-bold text-ink-2 hover:text-ink">
        <ArrowLeft aria-hidden className="size-4 rtl:rotate-180" />
        {t("backToRadar")}
      </button>

      {/* Header */}
      <header className={cn("mt-3 rounded-[16px] border p-4 sm:p-5 transition-[box-shadow] duration-300", is("url") ? "border-primary ring-4 ring-primary/15 bg-surface" : "border-line bg-surface")} id="ev-url">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span>
            {t("caseId")} <span className="ltr font-bold text-ink-2">{c.id}</span>
          </span>
          <span aria-hidden>·</span>
          <SourceTag source={c.candidate.source} />
          {c.candidate.query && (
            <span>
              {t("query")} <q className="font-semibold text-ink-2">{c.candidate.query}</q>
            </span>
          )}
          <span aria-hidden>·</span>
          <span>
            {t("found")} <time dateTime={c.candidate.discovered_at}>{fmtTime(c.candidate.discovered_at, lang)}</time>
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="ltr break-all text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">{c.domain}</h1>
            <p className="ltr mt-0.5 break-all text-sm text-muted">{c.candidate.url}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {v.brand_target && (
              <span className="text-sm text-muted">
                {t("targets")} <BrandChip brandId={v.brand_target} name={brandName} className="ms-1 text-sm" />
              </span>
            )}
            <StatusTag status={c.status} />
          </div>
        </div>
      </header>

      <div className="mt-4 grid gap-4 lg:grid-cols-[21rem_1fr] xl:grid-cols-[23rem_1fr]">
        {/* Left: what the page looked like */}
        <div className="flex flex-col gap-4 lg:sticky lg:top-6 lg:self-start">
          <ScreenshotPanel ev={ev} active={is("screenshot")} offline={offline} />
          <RedirectsPanel ev={ev} active={is("redirects")} />
        </div>

        {/* Right: verdict, reasons, evidence, actions */}
        <div className="flex flex-col gap-4">
          <Panel className="p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-4">
              <ScoreRing score={v.score} verdict={v.verdict} size={84} />
              <div className="min-w-0 flex-1">
                <VerdictChip verdict={v.verdict} size="lg" />
                <p className="mt-2 text-sm text-muted">
                  {t("riskScore")} <span className="ltr font-bold text-ink tabular-nums">{v.score}</span> {t("outOf100")} · {t("scoredBy", { m: v.model_version })} · <time dateTime={v.scored_at}>{fmtTime(v.scored_at, lang)}</time>
                </p>
              </div>
              <div className="w-full sm:w-auto">
                <ExportButtons c={c} onTakedown={() => setTakedownOpen(true)} />
              </div>
            </div>

            <div className="mt-5 border-t border-line pt-4">
              <PanelTitle hint={t("reasonHint")}>{v.verdict === "LEGIT" ? t("whyNotFlagged") : t("whyFlagged")}</PanelTitle>
              <ol className="mt-3 flex flex-col gap-1.5">
                {[...v.reasons]
                  .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
                  .map((r) => {
                    const block = refToBlock(r.evidence_ref);
                    const on = block !== null && active === block;
                    const up = r.weight > 0;
                    return (
                      <li key={r.code}>
                        <button
                          type="button"
                          onClick={() => select(r)}
                          aria-pressed={on}
                          disabled={!block}
                          className={cn(
                            "grid w-full grid-cols-[3.25rem_1fr] items-center gap-3 rounded-xl px-3 py-2.5 text-start transition-colors",
                            block ? "hover:bg-surface-2" : "cursor-default",
                            on && "bg-primary-soft",
                          )}
                        >
                          <span className="flex flex-col items-center">
                            <span className={cn("ltr text-sm font-extrabold tabular-nums", up ? "text-fraud" : "text-safe")}>
                              {up ? "+" : ""}
                              {r.weight}
                            </span>
                            <span className="mt-1 h-1 w-full overflow-hidden rounded-full bg-line">
                              <span className={cn("block h-full rounded-full", up ? "bg-fraud" : "bg-safe")} style={{ width: `${Math.min(100, (Math.abs(r.weight) / 50) * 100)}%` }} />
                            </span>
                          </span>
                          <span className="text-sm leading-snug text-ink">{pick(r as unknown as Record<string, unknown>, "text")}</span>
                        </button>
                      </li>
                    );
                  })}
              </ol>
            </div>
          </Panel>

          <div className="grid gap-4 md:grid-cols-2">
            <DomainPanel ev={ev} discoveredAt={c.candidate.discovered_at} active={is("domain")} />
            <HostingPanel ev={ev} active={is("hosting")} />
            <FormsPanel ev={ev} active={is("forms")} />
            <MapsPanel c={c} active={is("maps")} officialHelplines={brand?.helplines ?? []} />
            <TextPanel ev={ev} active={is("text")} />
            <DownloadsPanel ev={ev} active={is("downloads")} />
            <CloakingPanel ev={ev} active={is("cloaking")} />
            <FingerprintsPanel ev={ev} active={is("fingerprints")} />
          </div>

          <DecisionPanel c={c} onUpdated={onUpdated} />
        </div>
      </div>

      <TakedownDialog caseId={c.id} open={takedownOpen} onClose={() => setTakedownOpen(false)} />

      <p className="sr-only">
        <Link href="/">{t("navRadar")}</Link>
      </p>
    </div>
  );
}
