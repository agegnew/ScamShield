"use client";

import Link from "next/link";
import { useCallback, useMemo } from "react";
import { ArrowRight, Ban, ChevronRight, Radar, ScanSearch, Share2, Smartphone, TriangleAlert } from "lucide-react";
import { useBrands, useCases, useGraph, useMetrics, type CaseSummary } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { toCampaigns } from "@/lib/campaigns";
import { L, useRadarStatus } from "@/lib/radar";
import { cn, fmtAgo, pct } from "@/lib/utils";
import { RadarScope, type ScopeItem } from "@/components/radar/RadarScope";
import { shortBrand } from "@/components/ui/verdict";
import { ErrorState, Panel, Skeleton } from "@/components/ui/primitives";

/* Threat operations: the radar scope is the page; everything else orbits it.
   Every number links to the cases behind it. No invented series, no fake live counters. */

const RADAR_SOURCES = ["lookalike", "ct", "nrd", "search", "search_ad", "maps"];
const VCOL = { FRAUD: "#ff6b6b", SUSPICIOUS: "#f5b93f", LEGIT: "#34d399" } as const;
type V = keyof typeof VCOL;

export default function OverviewPage() {
  const { t, lang, pick } = useLang();
  const cases = useCases({ limit: 500 });
  const { data: brands } = useBrands();
  const { data: metrics } = useMetrics();
  const { data: graph } = useGraph();
  const { data: radarStatus } = useRadarStatus();
  const live = Boolean(radarStatus && !radarStatus.preview && radarStatus.status.running);

  const items = useMemo(() => (cases.data?.items ?? []) as ScopeItem[], [cases.data]);
  const brandCat = useMemo(() => new Map((brands ?? []).map((b) => [b.id, b.category as string])), [brands]);
  const categoryOf = useCallback((it: ScopeItem) => it.brand_category ?? (it.brand_target ? brandCat.get(it.brand_target) ?? "none" : "none"), [brandCat]);
  const brandName = useCallback(
    (id: string | null) => {
      if (!id) return null;
      const b = brands?.find((x) => x.id === id);
      return b ? shortBrand(pick(b as unknown as Record<string, unknown>, "name")) : id;
    },
    [brands, pick],
  );

  const s = useMemo(() => {
    const fraud = items.filter((c) => c.verdict === "FRAUD");
    const risky = items.filter((c) => c.verdict !== "LEGIT");
    const review = risky.filter((c) => c.status === "new").sort((a, b) => b.score - a.score || b.discovered_at.localeCompare(a.discovered_at));
    const decided = risky.filter((c) => c.status !== "new").length;
    const radar = items.filter((c) => RADAR_SOURCES.includes(c.source));
    const lastRadar = radar.map((c) => c.discovered_at).sort().at(-1) ?? null;
    const buckets = Array.from({ length: 10 }, () => 0);
    for (const c of items) buckets[Math.min(9, Math.floor(c.score / 10))] += 1;
    const byBrand = new Map<string, Record<V, number>>();
    for (const c of risky) {
      if (!c.brand_target) continue;
      const row = byBrand.get(c.brand_target) ?? { FRAUD: 0, SUSPICIOUS: 0, LEGIT: 0 };
      row[c.verdict as V] += 1;
      byBrand.set(c.brand_target, row);
    }
    const bySource = new Map<string, Record<V, number>>();
    for (const c of items) {
      const row = bySource.get(c.source) ?? { FRAUD: 0, SUSPICIOUS: 0, LEGIT: 0 };
      row[c.verdict as V] += 1;
      bySource.set(c.source, row);
    }
    const tot = (r: Record<V, number>) => r.FRAUD + r.SUSPICIOUS + r.LEGIT;
    return {
      fraud,
      risky,
      review,
      decided,
      lastRadar,
      buckets,
      brands: [...byBrand.entries()].sort((a, b) => tot(b[1]) - tot(a[1])).slice(0, 6),
      sources: [...bySource.entries()].sort((a, b) => tot(b[1]) - tot(a[1])),
      recent: [...items].sort((a, b) => b.discovered_at.localeCompare(a.discovered_at)).slice(0, 7),
    };
  }, [items]);

  const { campaigns } = useMemo(() => toCampaigns(graph), [graph]);

  if (cases.error) return <ErrorState error={cases.error} onRetry={() => cases.mutate()} />;
  const loading = cases.isLoading && !cases.data;
  const uae = metrics?.by_source?.uae_official;

  return (
    <div className="mx-auto max-w-[1360px]">
      {/* Command bar */}
      <header className="flex flex-wrap items-end justify-between gap-4 pt-1">
        <div className="min-w-0">
          <p className="inline-flex items-center gap-2 text-xs font-bold text-primary">
            <span aria-hidden className="radar-dot inline-block size-2 rounded-full bg-accent" />
            {L(["Threat operations · Abu Dhabi", "عمليات التهديد · أبوظبي"], lang)}
          </p>
          <h1 className="mt-1 text-[26px] font-extrabold leading-tight tracking-tight text-ink sm:text-[32px]">
            {loading ? (
              <Skeleton className="h-9 w-96 max-w-full" />
            ) : (
              <>
                <Link href="/cases?verdict=FRAUD" className="ops-num text-fraud hover:underline">
                  {t("ovHeadline", { f: s.fraud.length })}
                </Link>{" "}
                <Link href="/cases?status=new&risky=1" className="hover:underline">
                  {s.review.length > 0 ? t("ovHeadline2", { r: s.review.length }) : t("ovHeadlineClear")}
                </Link>
              </>
            )}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-2">
            {L(
              [
                "ScamShield finds fake UAE government, bank and delivery sites on its own, explains why in Arabic and English, and prepares the police evidence.",
                "يرصد درع الاحتيال المواقع المزيفة للجهات الحكومية والبنوك وشركات التوصيل تلقائيًا، ويشرح السبب بالعربية والإنجليزية، ويجهّز أدلة الشرطة.",
              ],
              lang,
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <StatusPill label={L(["Last radar find", "آخر رصد"], lang)} value={s.lastRadar ? fmtAgo(s.lastRadar, lang) : "—"} />
          {metrics && <StatusPill label={L(["Engine", "المحرك"], lang)} value={metrics.model_version} ltr />}
          <Link href="/radar" className="inline-flex h-9 items-center gap-1.5 rounded-full bg-primary px-4 text-sm font-extrabold text-primary-ink shadow-[0_6px_20px_-8px_var(--glow)] hover:brightness-110">
            <Radar aria-hidden className="size-4" />
            {L(["Open radar", "افتح الرادار"], lang)}
          </Link>
        </div>
      </header>

      {/* The scope, flanked by gauges and alerts */}
      <div className="mt-5 grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_310px]">
        <div className="order-2 grid gap-4 sm:grid-cols-2 xl:order-1 xl:grid-cols-1 xl:content-start">
          <Panel className="p-4">
            <PanelHead title={L(["Threat picture", "صورة التهديد"], lang)} />
            <div className="mt-3 grid grid-cols-2 gap-2">
              <RingGauge
                href="/cases?verdict=FRAUD"
                value={s.fraud.length}
                max={Math.max(1, items.length)}
                color={VCOL.FRAUD}
                label={L(["Fraud", "احتيال"], lang)}
                sub={L([`of ${items.length} sites`, `من ${items.length} موقعًا`], lang)}
                loading={loading}
              />
              <RingGauge
                href="/cases?status=new&risky=1"
                value={s.decided}
                max={Math.max(1, s.risky.length)}
                color="#2ee59d"
                label={L(["Reviewed", "تمت مراجعتها"], lang)}
                sub={L([`of ${s.risky.length} risky`, `من ${s.risky.length} خطرة`], lang)}
                loading={loading}
              />
            </div>
          </Panel>
          <Panel className="p-4">
            <PanelHead title={L(["Risk scores", "درجات الخطورة"], lang)} hint={L(["All sites, 0 to 100", "كل المواقع، من 0 إلى 100"], lang)} />
            <RiskHistogram buckets={s.buckets} loading={loading} />
          </Panel>
        </div>

        <Panel className="ops-glow order-1 overflow-visible p-3 sm:p-4 xl:order-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <PanelHead title={L(["Radar", "الرادار"], lang)} />
            <ul className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-2">
              {(["FRAUD", "SUSPICIOUS", "LEGIT"] as const).map((v) => (
                <li key={v} className="inline-flex items-center gap-1.5">
                  <span aria-hidden className="size-2.5 rounded-full" style={{ background: VCOL[v], boxShadow: `0 0 8px ${VCOL[v]}` }} />
                  {t(v)}
                </li>
              ))}
            </ul>
          </div>
          <p className="mt-1 text-xs text-muted">
            {L(
              ["Each dot is a site. Closer to the centre means higher risk. Point at a dot to see it, click to open the case.", "كل نقطة موقع. الأقرب إلى المركز أعلى خطورة. أشر إلى نقطة لتراها وانقر لفتح الحالة."],
              lang,
            )}
          </p>
          {loading ? (
            <Skeleton className="mx-auto mt-4 aspect-square w-full max-w-[560px] rounded-full" />
          ) : (
            <RadarScope items={items} categoryOf={categoryOf} brandName={brandName} live={live} className="mt-2 max-w-[600px]" />
          )}
        </Panel>

        <Panel className="order-3 flex flex-col p-4">
          <PanelHead title={L(["Priority alerts", "تنبيهات ذات أولوية"], lang)} hint={L(["Waiting for a decision", "بانتظار قرار"], lang)} />
          {loading ? (
            <div className="mt-3 flex flex-col gap-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))}
            </div>
          ) : s.review.length === 0 ? (
            <p className="mt-4 text-sm text-muted">{t("queueEmpty")}</p>
          ) : (
            <ol className="mt-3 flex flex-col gap-2">
              {s.review.slice(0, 7).map((c) => (
                <AlertRow key={c.id} c={c} brand={brandName(c.brand_target)} />
              ))}
            </ol>
          )}
          <Link href="/cases?status=new&risky=1" className="mt-auto inline-flex items-center gap-1.5 pt-3 text-sm font-bold text-primary hover:underline">
            {t("queueAll", { n: s.review.length })}
            <ArrowRight aria-hidden className="size-4 rtl:rotate-180" />
          </Link>
        </Panel>
      </div>

      {/* Lower deck */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel id="brands" className="scroll-mt-24 p-4">
          <PanelHead title={t("brandsTitle")} hint={t("brandsHint")} />
          <Bars
            rows={s.brands.map(([id, v]) => ({ key: id, label: brandName(id) ?? id, v, href: `/cases?brand=${encodeURIComponent(id)}` }))}
            series={["FRAUD", "SUSPICIOUS"]}
            hrefFor={(k, v) => `/cases?brand=${encodeURIComponent(k)}&verdict=${v}`}
          />
        </Panel>
        <Panel className="p-4">
          <PanelHead title={t("sourcesTitle")} hint={t("sourcesHint")} />
          <Bars
            rows={s.sources.map(([src, v]) => ({ key: src, label: t(`src_${src}` as Parameters<typeof t>[0]), v, href: `/cases?source=${encodeURIComponent(src)}` }))}
            series={["FRAUD", "SUSPICIOUS", "LEGIT"]}
            hrefFor={(k, v) => `/cases?source=${encodeURIComponent(k)}&verdict=${v}`}
          />
        </Panel>
        <Panel className="p-4">
          <PanelHead title={L(["Latest activity", "آخر النشاط"], lang)} />
          <ol className="relative mt-3 flex flex-col gap-3 border-s border-line-2 ps-4">
            {s.recent.map((c) => (
              <li key={c.id} className="relative">
                <span aria-hidden className="absolute -start-[21px] top-1.5 size-2.5 rounded-full" style={{ background: VCOL[c.verdict as V], boxShadow: `0 0 10px ${VCOL[c.verdict as V]}` }} />
                <Link href={`/cases/${c.id}`} className="group block">
                  <span className="text-xs text-muted">
                    {fmtAgo(c.discovered_at, lang)} · {t(`src_${c.source}` as Parameters<typeof t>[0])}
                  </span>
                  <span className="ltr block truncate text-sm font-extrabold text-ink group-hover:text-primary">{c.domain}</span>
                  <span className="text-xs font-bold" style={{ color: VCOL[c.verdict as V] }}>
                    {t(c.verdict)} {c.score}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 pb-2 lg:grid-cols-[1.2fr_1fr]">
        <Panel className="p-4">
          <PanelHead title={t("accTitle")} hint={t("accHint")} />
          {metrics ? (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label={t("precision")} value={pct(metrics.precision)} />
              <Metric label={t("recall")} value={pct(metrics.recall)} />
              <Metric label={t("fpr")} value={pct(metrics.fpr)} />
              {uae && <Metric label={L(["UAE official pages wrongly flagged", "صفحات رسمية وُصفت خطأً"], lang)} value={`${uae.total - uae.correct} / ${uae.total}`} good />}
            </div>
          ) : (
            <Skeleton className="mt-3 h-16 rounded-xl" />
          )}
          <Link href="/accuracy" className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline">
            {t("accLink")}
            <ArrowRight aria-hidden className="size-4 rtl:rotate-180" />
          </Link>
        </Panel>
        <Panel className="p-4">
          <PanelHead title={t("netTitle")} hint={t("netHint")} />
          {campaigns.length === 0 ? (
            <p className="mt-3 text-sm text-muted">{t("netNone")}</p>
          ) : (
            <ul className="mt-3 flex flex-col gap-2">
              {campaigns.slice(0, 2).map((c, i) => (
                <li key={i} className="rounded-xl border border-line bg-surface-2 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span className="font-extrabold text-ink">{t("campaign", { n: i + 1 })}</span>
                    <span className="text-xs font-bold text-muted">{t("campaignDomains", { n: c.nodes.length })}</span>
                  </div>
                  <p className="ltr mt-0.5 truncate text-xs text-ink-2">{c.nodes.map((n) => n.domain).join(" · ")}</p>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <QuickLink href="/graph" icon={<Share2 aria-hidden className="size-4" />} label={t("netLink")} />
            <QuickLink href="/scan" icon={<ScanSearch aria-hidden className="size-4" />} label={t("navScan")} />
            <QuickLink href="/check" icon={<Smartphone aria-hidden className="size-4" />} label={t("navChecker")} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

/* ---------- pieces ---------- */

function StatusPill({ label, value, ltr }: { label: string; value: string; ltr?: boolean }) {
  return (
    <span className="inline-flex h-9 items-center gap-2 rounded-full border border-line-2 bg-surface px-3">
      <span className="text-muted">{label}</span>
      <span className={cn("font-extrabold text-ink", ltr && "ltr")}>{value}</span>
    </span>
  );
}

function PanelHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
      <h2 className="text-[15px] font-extrabold text-ink">{title}</h2>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

function RingGauge({ value, max, color, label, sub, href, loading }: { value: number; max: number; color: string; label: string; sub: string; href: string; loading: boolean }) {
  const r = 40;
  const c = 2 * Math.PI * r;
  const f = Math.min(1, value / max);
  return (
    <Link href={href} className="group flex flex-col items-center rounded-xl p-2 text-center transition-colors hover:bg-surface-2">
      <div className="relative size-[104px]" role="img" aria-label={`${label}: ${value} ${sub}`}>
        <svg viewBox="0 0 100 100" className="size-full -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="#1a2b25" strokeWidth="8" />
          {!loading && (
            <circle
              cx="50"
              cy="50"
              r={r}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={c}
              strokeDashoffset={c * (1 - f)}
              className="ring-fill"
              style={{ ["--ring-circ" as string]: c, filter: `drop-shadow(0 0 6px ${color})` }}
            />
          )}
        </svg>
        <span className="ltr absolute inset-0 grid place-items-center text-[26px] font-extrabold tabular-nums" style={{ color, textShadow: `0 0 18px ${color}80` }}>
          {loading ? "—" : value}
        </span>
      </div>
      <span className="mt-1 text-sm font-extrabold text-ink">{label}</span>
      <span className="text-[11px] text-muted">{sub}</span>
    </Link>
  );
}

function RiskHistogram({ buckets, loading }: { buckets: number[]; loading: boolean }) {
  const { lang } = useLang();
  const max = Math.max(1, ...buckets);
  const zone = (i: number) => (i >= 7 ? VCOL.FRAUD : i >= 3 ? VCOL.SUSPICIOUS : VCOL.LEGIT);
  if (loading) return <Skeleton className="mt-3 h-28 rounded-xl" />;
  return (
    <figure className="mt-3">
      <div className="flex h-28 items-end gap-1.5" style={{ direction: "ltr" }}>
        {buckets.map((n, i) => (
          <div key={i} className="group relative flex h-full flex-1 flex-col justify-end">
            <span className="pointer-events-none absolute -top-6 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-line-2 bg-surface-2 px-1.5 py-0.5 text-[11px] font-bold text-ink group-hover:block">
              {i * 10}–{i === 9 ? 100 : i * 10 + 9}: {n}
            </span>
            <div
              className="w-full rounded-t-[4px] transition-[filter] group-hover:brightness-125"
              style={{ height: `${Math.max(n ? 6 : 2, (n / max) * 100)}%`, background: n ? zone(i) : "#1a2b25", boxShadow: n ? `0 0 14px -2px ${zone(i)}` : undefined }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-muted" style={{ direction: "ltr" }}>
        <span>0</span>
        <span>30</span>
        <span>70</span>
        <span>100</span>
      </div>
      <figcaption className="mt-2 text-[11px] text-muted">{L(["Green below 30 · amber 30–69 · red 70 and above", "أخضر أقل من 30 · برتقالي 30–69 · أحمر 70 فأكثر"], lang)}</figcaption>
    </figure>
  );
}

function AlertRow({ c, brand }: { c: CaseSummary; brand: string | null }) {
  const { t, lang } = useLang();
  const col = VCOL[c.verdict as V];
  const Icon = c.verdict === "FRAUD" ? Ban : TriangleAlert;
  return (
    <li>
      <Link
        href={`/cases/${c.id}`}
        className="group relative flex items-center gap-3 overflow-hidden rounded-xl border border-line bg-surface-2/60 py-2.5 pe-2 ps-3.5 transition-colors hover:border-line-2 hover:bg-surface-2"
      >
        <span aria-hidden className="absolute inset-y-0 start-0 w-[3px]" style={{ background: col, boxShadow: `0 0 12px ${col}` }} />
        <Icon aria-hidden className="size-4 shrink-0" style={{ color: col }} strokeWidth={2.5} />
        <span className="min-w-0 flex-1">
          <span className="ltr block truncate text-sm font-extrabold text-ink">{c.domain}</span>
          <span className="flex flex-wrap items-center gap-x-1.5 text-[11px] text-muted">
            {brand && <span className="font-bold text-accent-text">{brand}</span>}
            <span>· {fmtAgo(c.discovered_at, lang)}</span>
          </span>
        </span>
        <span className="flex flex-col items-end">
          <span className="ltr text-lg font-extrabold leading-none tabular-nums" style={{ color: col }}>
            {c.score}
          </span>
          <span className="text-[10px] font-bold" style={{ color: col }}>
            {t(c.verdict)}
          </span>
        </span>
        <ChevronRight aria-hidden className="size-4 text-muted rtl:rotate-180" />
      </Link>
    </li>
  );
}

function Bars({ rows, series, hrefFor }: { rows: { key: string; label: string; v: Record<V, number>; href: string }[]; series: V[]; hrefFor: (k: string, v: V) => string }) {
  const { t } = useLang();
  const totals = rows.map((r) => series.reduce((n, k) => n + r.v[k], 0));
  const max = Math.max(1, ...totals);
  if (!rows.length) return <p className="mt-3 text-sm text-muted">—</p>;
  return (
    <ul className="mt-3 flex flex-col gap-2.5">
      {rows.map((row, i) => (
        <li key={row.key} className="grid grid-cols-[minmax(5.5rem,32%)_1fr_1.75rem] items-center gap-3">
          <Link href={row.href} className="truncate text-sm font-semibold text-ink hover:text-primary" title={row.label}>
            {row.label}
          </Link>
          <div className="flex h-3.5 items-stretch gap-[2px]" style={{ width: `${(totals[i] / max) * 100}%` }}>
            {series
              .filter((k) => row.v[k] > 0)
              .map((k, j, arr) => (
                <Link
                  key={k}
                  href={hrefFor(row.key, k)}
                  aria-label={`${row.label} · ${t(k)}: ${row.v[k]}`}
                  title={`${t(k)}: ${row.v[k]}`}
                  className={cn("min-w-[5px] hover:brightness-125", j === 0 && "rounded-s-[4px]", j === arr.length - 1 && "rounded-e-[4px]")}
                  style={{ flexGrow: row.v[k], background: VCOL[k], boxShadow: `0 0 10px -3px ${VCOL[k]}` }}
                />
              ))}
          </div>
          <span className="ltr text-end text-sm font-bold tabular-nums text-ink-2">{totals[i]}</span>
        </li>
      ))}
    </ul>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="rounded-xl border border-line bg-surface-2 px-3 py-2.5">
      <p className="truncate text-[11px] font-bold text-muted" title={label}>
        {label}
      </p>
      <p className={cn("ltr mt-0.5 text-xl font-extrabold tabular-nums", good ? "text-safe" : "text-primary")} style={{ textShadow: "0 0 16px var(--glow)" }}>
        {value}
      </p>
    </div>
  );
}

function QuickLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="inline-flex h-9 items-center gap-1.5 rounded-full border border-line-2 bg-surface-2 px-3.5 text-sm font-bold text-ink hover:bg-primary-soft">
      <span className="text-primary">{icon}</span>
      {label}
    </Link>
  );
}
