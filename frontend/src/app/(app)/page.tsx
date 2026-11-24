"use client";

import Link from "next/link";
import { useMemo } from "react";
import { ArrowRight, Ban, ChevronRight, FolderOpen, Radar, ScanSearch, Share2, ShieldCheck, Smartphone, Target, TriangleAlert } from "lucide-react";
import { useBrands, useCases, useGraph, useMetrics, type CaseSummary } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { toCampaigns } from "@/lib/campaigns";
import { cn, fmtAgo, pct } from "@/lib/utils";
import { BrandChip, shortBrand, SourceTag, VerdictChip } from "@/components/ui/verdict";
import { ErrorState, Panel, Skeleton } from "@/components/ui/primitives";

/* Overview dashboard.
   Every number is a link to the cases behind it (Cases reads its filters from the URL).
   No live tickers, no invented totals: only what the API holds right now. */

const RADAR_SOURCES = ["lookalike", "ct", "nrd", "search", "search_ad", "maps"];
// Chart series for verdicts: separated by lightness as well as hue, validated for colour-blind readers.
const SERIES = [
  { key: "FRAUD", color: "#b91c1c", Icon: Ban },
  { key: "SUSPICIOUS", color: "#e0a030", Icon: TriangleAlert },
  { key: "LEGIT", color: "#15803d", Icon: ShieldCheck },
] as const;
type SeriesKey = (typeof SERIES)[number]["key"];

export default function OverviewPage() {
  const { t, lang, pick } = useLang();
  const cases = useCases({ limit: 500 });
  const { data: brands } = useBrands();
  const { data: metrics } = useMetrics();
  const { data: graph } = useGraph();

  const items = useMemo(() => cases.data?.items ?? [], [cases.data]);
  const brandName = (id: string | null) => {
    if (!id) return null;
    const b = brands?.find((x) => x.id === id);
    return b ? pick(b as unknown as Record<string, unknown>, "name") : id;
  };

  const s = useMemo(() => {
    const fraud = items.filter((c) => c.verdict === "FRAUD");
    const review = items.filter((c) => c.status === "new" && c.verdict !== "LEGIT");
    const radar = items.filter((c) => RADAR_SOURCES.includes(c.source));
    const risky = items.filter((c) => c.verdict !== "LEGIT");
    const brandIds = new Set(risky.map((c) => c.brand_target).filter(Boolean));
    const lastRadar = radar.map((c) => c.discovered_at).sort().at(-1) ?? null;

    const byBrand = new Map<string, Record<SeriesKey, number>>();
    for (const c of risky) {
      if (!c.brand_target) continue;
      const row = byBrand.get(c.brand_target) ?? { FRAUD: 0, SUSPICIOUS: 0, LEGIT: 0 };
      row[c.verdict as SeriesKey] += 1;
      byBrand.set(c.brand_target, row);
    }
    const bySource = new Map<string, Record<SeriesKey, number>>();
    for (const c of items) {
      const row = bySource.get(c.source) ?? { FRAUD: 0, SUSPICIOUS: 0, LEGIT: 0 };
      row[c.verdict as SeriesKey] += 1;
      bySource.set(c.source, row);
    }
    const total = (r: Record<SeriesKey, number>) => r.FRAUD + r.SUSPICIOUS + r.LEGIT;
    return {
      fraud,
      confirmed: fraud.filter((c) => c.status === "confirmed").length,
      review: [...review].sort((a, b) => b.score - a.score),
      radar,
      brandCount: brandIds.size,
      lastRadar,
      brands: [...byBrand.entries()].sort((a, b) => total(b[1]) - total(a[1]) || b[1].FRAUD - a[1].FRAUD).slice(0, 7),
      sources: [...bySource.entries()].sort((a, b) => total(b[1]) - total(a[1])),
    };
  }, [items]);

  const { campaigns, unlinked } = useMemo(() => toCampaigns(graph), [graph]);

  if (cases.error) return <ErrorState error={cases.error} onRetry={() => cases.mutate()} />;
  const loading = cases.isLoading && !cases.data;
  const uae = metrics?.by_source?.uae_official;

  return (
    <div className="mx-auto max-w-6xl">
      {/* Headline band: the one bold moment on the page */}
      <section className="relative mt-2 overflow-hidden rounded-[20px] bg-[#1e1b2e] px-5 py-6 text-white sm:px-8 sm:py-8">
        <RadarRings />
        <div className="relative max-w-2xl">
          <p className="inline-flex items-center gap-2 text-sm font-bold text-white/70">
            <span aria-hidden className="radar-dot inline-block size-2 rounded-full bg-accent" />
            {t("ovKicker")}
          </p>
          {loading ? (
            <div className="mt-3 flex flex-col gap-2">
              <div className="h-9 w-3/4 animate-pulse rounded-lg bg-white/10" />
              <div className="h-9 w-2/3 animate-pulse rounded-lg bg-white/10" />
            </div>
          ) : (
            <h1 className="mt-2 text-[28px] font-extrabold leading-[1.15] tracking-tight sm:text-[40px]">
              <Link href="/cases?verdict=FRAUD" className="text-[#ff8a8a] underline-offset-[6px] hover:underline">
                {t("ovHeadline", { f: s.fraud.length })}
              </Link>{" "}
              {s.review.length > 0 ? (
                <Link href="/cases?status=new&risky=1" className="text-white underline-offset-[6px] hover:underline">
                  {t("ovHeadline2", { r: s.review.length })}
                </Link>
              ) : (
                <span>{t("ovHeadlineClear")}</span>
              )}
            </h1>
          )}
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-white/70">{t("ovSub")}</p>
          <dl className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <div className="flex gap-2">
              <dt className="text-white/55">{t("ovLastFind")}</dt>
              <dd className="font-bold">{s.lastRadar ? fmtAgo(s.lastRadar, lang) : "—"}</dd>
            </div>
            {metrics && (
              <div className="flex gap-2">
                <dt className="text-white/55">{t("ovEngine")}</dt>
                <dd className="ltr font-bold">{metrics.model_version}</dd>
              </div>
            )}
          </dl>
        </div>
      </section>

      {/* KPI tiles: each one opens the cases behind it */}
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi i={0} href="/cases?status=new&risky=1" label={t("kpiReview")} value={s.review.length} hint={t("kpiReviewHint")} loading={loading} icon={<FolderOpen aria-hidden className="size-4" />} />
        <Kpi
          i={1}
          href="/cases?verdict=FRAUD"
          label={t("kpiFraud")}
          value={s.fraud.length}
          hint={t("kpiFraudHint", { c: s.confirmed })}
          loading={loading}
          tone="fraud"
          icon={<Ban aria-hidden className="size-4" />}
        />
        <Kpi
          i={2}
          href="/radar"
          label={t("kpiRadar")}
          value={s.radar.length}
          hint={t("kpiRadarHint", { t: items.length })}
          loading={loading}
          icon={<Radar aria-hidden className="size-4" />}
        />
        <Kpi
          i={3}
          href="#brands"
          label={t("kpiBrands")}
          value={s.brandCount}
          hint={t("kpiBrandsHint", { t: brands?.length ?? 23 })}
          loading={loading}
          icon={<Target aria-hidden className="size-4" />}
        />
      </div>

      {/* Work queue first, then the evidence that the engine can be trusted */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.45fr_1fr]">
        <Panel className="flex flex-col p-4 sm:p-5">
          <PanelHead title={t("queueTitle")} hint={t("queueHint")} />
          {loading ? (
            <div className="mt-3 flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))}
            </div>
          ) : s.review.length === 0 ? (
            <p className="mt-4 rounded-xl border border-dashed border-line-2 p-6 text-center text-sm text-muted">{t("queueEmpty")}</p>
          ) : (
            <ol className="mt-2 flex flex-col">
              {s.review.slice(0, 6).map((c, i) => (
                <QueueRow key={c.id} c={c} brand={brandName(c.brand_target)} first={i === 0} />
              ))}
            </ol>
          )}
          {s.review.length > 6 && (
            <Link href="/cases?status=new&risky=1" className="mt-auto inline-flex items-center gap-1.5 self-start pt-3 text-sm font-bold text-primary hover:underline">
              {t("queueAll", { n: s.review.length })}
              <ArrowRight aria-hidden className="size-4 rtl:rotate-180" />
            </Link>
          )}
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel className="p-4 sm:p-5">
            <PanelHead title={t("accTitle")} hint={t("accHint")} />
            {metrics ? (
              <>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <Metric label={t("precision").split(" (")[0]} value={pct(metrics.precision)} />
                  <Metric label={t("recall").split(" (")[0]} value={pct(metrics.recall)} />
                  <Metric label={t("fpr")} value={pct(metrics.fpr)} />
                </div>
                {uae && (
                  <p className="mt-3 flex items-center gap-2 rounded-xl bg-safe-soft px-3 py-2 text-sm text-safe">
                    <ShieldCheck aria-hidden className="size-4 shrink-0" />
                    <span>
                      <span className="ltr font-extrabold tabular-nums">
                        {uae.total - uae.correct} / {uae.total}
                      </span>{" "}
                      {t("uaeOfficial")}
                    </span>
                  </p>
                )}
                <Link href="/accuracy" className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline">
                  {t("accLink")}
                  <ArrowRight aria-hidden className="size-4 rtl:rotate-180" />
                </Link>
              </>
            ) : (
              <Skeleton className="mt-3 h-24 rounded-xl" />
            )}
          </Panel>

          <Panel className="p-4 sm:p-5">
            <PanelHead title={t("netTitle")} hint={t("netHint")} />
            {!graph ? (
              <Skeleton className="mt-3 h-20 rounded-xl" />
            ) : campaigns.length === 0 ? (
              <p className="mt-3 text-sm text-muted">{t("netNone")}</p>
            ) : (
              <>
                <p className="mt-2 text-sm font-bold text-ink">
                  {t(campaigns.length === 1 ? "netGroup1" : "netGroups", { g: campaigns.length, d: campaigns.reduce((n, c) => n + c.nodes.length, 0) })}
                </p>
                <ul className="mt-2 flex flex-col gap-2">
                  {campaigns.slice(0, 2).map((c, i) => (
                    <li key={i} className="rounded-xl bg-surface-2 px-3 py-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-extrabold text-ink">{t("campaign", { n: i + 1 })}</span>
                        <span className="text-xs font-bold text-muted">{t("campaignDomains", { n: c.nodes.length })}</span>
                      </div>
                      <p className="ltr mt-0.5 truncate text-xs text-ink-2">{c.nodes.map((n) => n.domain).join(", ")}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {c.types.map((ty) => (
                          <span key={ty} className="rounded-full bg-primary-soft px-2 py-0.5 text-[11px] font-bold text-primary">
                            {t(`edge_${ty}` as Parameters<typeof t>[0])}
                          </span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-muted">
                  {t("unlinkedTitle")}: <span className="font-bold tabular-nums">{unlinked.length}</span>
                </p>
              </>
            )}
            <Link href="/graph" className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline">
              {t("netLink")}
              <ArrowRight aria-hidden className="size-4 rtl:rotate-180" />
            </Link>
          </Panel>
        </div>
      </div>

      {/* Breakdowns: every bar segment opens the matching filtered list */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel id="brands" className="scroll-mt-24 p-4 sm:p-5">
          <PanelHead title={t("brandsTitle")} hint={t("brandsHint")} />
          <Legend keys={["FRAUD", "SUSPICIOUS"]} />
          {loading ? (
            <Skeleton className="mt-3 h-48 rounded-xl" />
          ) : (
            <StackedBars
              rows={s.brands.map(([id, v]) => ({ key: id, label: shortBrand(brandName(id) ?? id), values: v, href: `/cases?brand=${encodeURIComponent(id)}` }))}
              series={["FRAUD", "SUSPICIOUS"]}
              hrefFor={(row, k) => `/cases?brand=${encodeURIComponent(row.key)}&verdict=${k}`}
            />
          )}
        </Panel>

        <Panel className="p-4 sm:p-5">
          <PanelHead title={t("sourcesTitle")} hint={t("sourcesHint")} />
          <Legend keys={["FRAUD", "SUSPICIOUS", "LEGIT"]} />
          {loading ? (
            <Skeleton className="mt-3 h-48 rounded-xl" />
          ) : (
            <StackedBars
              rows={s.sources.map(([src, v]) => ({
                key: src,
                label: t(`src_${src}` as Parameters<typeof t>[0]),
                values: v,
                href: `/cases?source=${encodeURIComponent(src)}`,
              }))}
              series={["FRAUD", "SUSPICIOUS", "LEGIT"]}
              hrefFor={(row, k) => `/cases?source=${encodeURIComponent(row.key)}&verdict=${k}`}
            />
          )}
        </Panel>
      </div>

      {/* Quick actions */}
      <nav aria-label={t("actionsTitle")} className="mt-4 grid grid-cols-2 gap-3 pb-2 sm:grid-cols-4">
        <Action href="/radar" icon={<Radar aria-hidden className="size-5" />} label={t("navRadar")} />
        <Action href="/scan" icon={<ScanSearch aria-hidden className="size-5" />} label={t("navScan")} />
        <Action href="/graph" icon={<Share2 aria-hidden className="size-5" />} label={t("navNetwork")} />
        <Action href="/check" icon={<Smartphone aria-hidden className="size-5" />} label={t("navChecker")} />
      </nav>
    </div>
  );
}

/* ---------- pieces ---------- */

function RadarRings() {
  // Static rings: the radar is a place, not a fake animation. Mirrors with the layout direction.
  return (
    <svg aria-hidden viewBox="0 0 400 400" className="pointer-events-none absolute -end-24 -top-20 size-[420px] opacity-60 sm:-end-10 sm:-top-28 sm:size-[520px] rtl:-scale-x-100">
      <defs>
        <radialGradient id="ov-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6d28d9" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#6d28d9" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="200" cy="200" r="200" fill="url(#ov-glow)" />
      {[180, 135, 90, 45].map((r) => (
        <circle key={r} cx="200" cy="200" r={r} fill="none" stroke="#b79cff" strokeOpacity="0.28" strokeWidth="1" />
      ))}
      <line x1="20" y1="200" x2="380" y2="200" stroke="#b79cff" strokeOpacity="0.18" />
      <line x1="200" y1="20" x2="200" y2="380" stroke="#b79cff" strokeOpacity="0.18" />
      <circle cx="200" cy="200" r="5" fill="#f97316" />
      <circle cx="262" cy="120" r="4" fill="#ff8a8a" />
      <circle cx="128" cy="260" r="4" fill="#ff8a8a" />
      <circle cx="300" cy="238" r="4" fill="#fbbf24" />
    </svg>
  );
}

function Kpi({
  i,
  href,
  label,
  value,
  hint,
  icon,
  loading,
  tone,
}: {
  i: number;
  href: string;
  label: string;
  value: number;
  hint: string;
  icon: React.ReactNode;
  loading: boolean;
  tone?: "fraud";
}) {
  return (
    <Link
      href={href}
      className="rise-in group flex min-h-[124px] flex-col rounded-[16px] border border-line bg-surface p-4 transition-[border-color,box-shadow] hover:border-primary-soft-2 hover:shadow-[0_8px_24px_-14px_rgba(109,40,217,0.45)]"
      style={{ animationDelay: `${i * 60}ms` }}
    >
      <span className={cn("inline-flex items-center gap-1.5 text-[13px] font-bold", tone === "fraud" ? "text-fraud" : "text-ink-2")}>
        {icon}
        {label}
      </span>
      {loading ? (
        <span className="mt-2 h-9 w-14 animate-pulse rounded-lg bg-surface-2" />
      ) : (
        <span className={cn("ltr mt-1 text-[34px] font-extrabold leading-none tracking-tight tabular-nums", tone === "fraud" ? "text-fraud" : "text-ink")}>{value}</span>
      )}
      <span className="mt-auto flex items-end justify-between gap-2 pt-2 text-xs leading-snug text-muted">
        {hint}
        <ChevronRight aria-hidden className="size-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5" />
      </span>
    </Link>
  );
}

function PanelHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
      <h2 className="text-base font-extrabold text-ink">{title}</h2>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-2 px-3 py-2.5">
      <p className="truncate text-xs font-bold text-muted">{label}</p>
      <p className="ltr mt-0.5 text-xl font-extrabold tabular-nums text-ink">{value}</p>
    </div>
  );
}

function QueueRow({ c, brand, first }: { c: CaseSummary; brand: string | null; first: boolean }) {
  const { lang } = useLang();
  return (
    <li className={cn(!first && "border-t border-line")}>
      <Link href={`/cases/${c.id}`} className="group grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 rounded-xl px-2 py-3 transition-colors hover:bg-surface-2">
        <span className="flex flex-col items-center gap-1">
          <VerdictChip verdict={c.verdict} size="sm" />
          <span className="ltr text-[11px] font-bold tabular-nums text-muted">{c.score}</span>
        </span>
        <span className="min-w-0">
          <span className="ltr block truncate text-[15px] font-extrabold text-ink">{c.domain}</span>
          <span className="mt-1 flex flex-wrap items-center gap-1.5">
            {c.brand_target && <BrandChip brandId={c.brand_target} name={brand} />}
            <SourceTag source={c.source} className="hidden sm:inline-flex" />
            <span className="text-xs text-muted">{fmtAgo(c.discovered_at, lang)}</span>
          </span>
        </span>
        <ChevronRight aria-hidden className="size-5 text-muted transition-transform group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5" />
      </Link>
    </li>
  );
}

function Legend({ keys }: { keys: SeriesKey[] }) {
  const { t } = useLang();
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {SERIES.filter((sr) => keys.includes(sr.key)).map(({ key, color, Icon }) => (
        <li key={key} className="inline-flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-[3px]" style={{ background: color }} />
          <Icon aria-hidden className="size-3.5 text-muted" />
          {t(key)}
        </li>
      ))}
    </ul>
  );
}

type BarRow = { key: string; label: string; values: Record<SeriesKey, number>; href: string };

function StackedBars({ rows, series, hrefFor }: { rows: BarRow[]; series: SeriesKey[]; hrefFor: (row: BarRow, k: SeriesKey) => string }) {
  const { t } = useLang();
  const totals = rows.map((r) => series.reduce((n, k) => n + r.values[k], 0));
  const max = Math.max(1, ...totals);
  if (rows.length === 0) return <p className="mt-3 text-sm text-muted">—</p>;
  return (
    <ul className="mt-3 flex flex-col gap-2.5">
      {rows.map((row, i) => (
        <li key={row.key} className="grid grid-cols-[minmax(6.5rem,34%)_1fr_2rem] items-center gap-3">
          <Link href={row.href} className="truncate text-sm font-semibold text-ink hover:text-primary hover:underline" title={row.label}>
            {row.label}
          </Link>
          <div className="flex h-5 items-stretch gap-[2px]" style={{ width: `${(totals[i] / max) * 100}%` }}>
            {series
              .filter((k) => row.values[k] > 0)
              .map((k, j, arr) => {
                const sr = SERIES.find((x) => x.key === k)!;
                const label = `${row.label} · ${t(k)}: ${row.values[k]}`;
                return (
                  <Link
                    key={k}
                    href={hrefFor(row, k)}
                    aria-label={label}
                    className={cn(
                      "group/seg relative min-w-[6px] transition-opacity hover:opacity-85 focus-visible:opacity-85",
                      j === 0 && "rounded-s-[4px]",
                      j === arr.length - 1 && "rounded-e-[4px]",
                    )}
                    style={{ flexGrow: row.values[k], background: sr.color }}
                  >
                    <span
                      role="tooltip"
                      className="pointer-events-none absolute bottom-full start-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg bg-ink px-2.5 py-1.5 text-xs font-bold text-white shadow-lg group-hover/seg:block group-focus-visible/seg:block rtl:translate-x-1/2"
                    >
                      {t(k)}: <span className="ltr tabular-nums">{row.values[k]}</span>
                    </span>
                  </Link>
                );
              })}
          </div>
          <span className="ltr text-end text-sm font-bold tabular-nums text-ink-2">{totals[i]}</span>
        </li>
      ))}
    </ul>
  );
}

function Action({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="flex min-h-14 items-center gap-3 rounded-[16px] border border-line bg-surface px-4 py-3 text-sm font-bold text-ink transition-colors hover:bg-surface-2">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary">{icon}</span>
      {label}
    </Link>
  );
}
