"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { ArrowUpRight, ChevronDown, ChevronRight, Search, X } from "lucide-react";
import { useBrands, useGraph, type Graph } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { isLocalDemo, toCampaigns, type Campaign } from "@/lib/campaigns";
import { L } from "@/lib/radar";
import { cn } from "@/lib/utils";
import { shortBrand } from "@/components/ui/verdict";
import { ErrorState, Panel, Skeleton } from "@/components/ui/primitives";
import { SCOPE_COLOR } from "@/components/radar/RadarScope";
import { Constellation, EDGE_ICON, EDGE_WHY, hubsOf, shortDetail, VerdictPill, type EdgeType } from "@/components/network/Constellation";

/* Scam network: operations (sites tied together by a shared fingerprint) drawn as constellations,
   then every site still working alone, grouped by the brand it copies. */

type Node = Graph["nodes"][number];
const EDGE_TYPES: EdgeType[] = ["same_template", "same_ip", "same_favicon", "same_contact", "same_tracker", "same_registration_day", "same_final_host"];
const colorOf = (v: string) => SCOPE_COLOR[v as keyof typeof SCOPE_COLOR] ?? "#b7b2ad";

function DomainName({ domain, className }: { domain: string; className?: string }) {
  const { t } = useLang();
  if (isLocalDemo(domain)) {
    return (
      <span className={cn("inline-flex items-center gap-1.5", className)}>
        <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-bold text-ink-2">{t("localDemo")}</span>
        <span className="ltr text-xs text-muted">{domain}</span>
      </span>
    );
  }
  return <span className={cn("ltr", className)}>{domain}</span>;
}

export default function GraphPage() {
  const { t, lang, pick } = useLang();
  const { data: full, error, isLoading, mutate } = useGraph();
  const { data: brands } = useBrands();
  const { campaigns, unlinked } = useMemo(() => toCampaigns(full), [full]);
  const brandName = useCallback(
    (id: string | null) => {
      if (!id) return null;
      const b = brands?.find((x) => x.id === id);
      return b ? shortBrand(pick(b as unknown as Record<string, unknown>, "name")) : id;
    },
    [brands, pick],
  );

  const linked = campaigns.reduce((n, c) => n + c.nodes.length, 0);
  const typeCounts = useMemo(() => {
    const m = new Map<EdgeType, number>();
    for (const e of full?.edges ?? []) m.set(e.type, (m.get(e.type) ?? 0) + 1);
    return m;
  }, [full]);

  if (error) return <ErrorState error={error} onRetry={() => mutate()} />;

  return (
    <div className="mx-auto max-w-7xl">
      {/* Headline: the finding, not the page name */}
      <header className="rise-in pt-2">
        <p className="inline-flex items-center gap-2 text-sm font-bold text-primary">
          <span aria-hidden className="radar-dot inline-block size-2 rounded-full bg-accent" />
          {t("graphTitle")}
        </p>
        {isLoading || !full ? (
          <Skeleton className="mt-3 h-10 w-2/3" />
        ) : (
          <h1 className="mt-2 max-w-4xl text-3xl font-extrabold leading-tight tracking-tight text-ink sm:text-4xl">
            {campaigns.length ? (
              <>
                <span className="text-[#ff6b6b]">
                  {campaigns.length === 1
                    ? L(["{n} sites are run by the same people.", "{n} مواقع تديرها الجهة نفسها."], lang).replace("{n}", String(linked))
                    : L(["{n} sites belong to {k} operations.", "{n} موقعًا تنتمي إلى {k} عمليات."], lang).replace("{n}", String(linked)).replace("{k}", String(campaigns.length))}
                </span>{" "}
                <span className="text-ink-2">{L(["{m} more work alone, for now.", "و{m} موقعًا آخر يعمل منفردًا حتى الآن."], lang).replace("{m}", unlinked.length.toLocaleString("en"))}</span>
              </>
            ) : (
              L(["No shared infrastructure yet.", "لا توجد بنية مشتركة بعد."], lang)
            )}
          </h1>
        )}
        <p className="mt-3 max-w-3xl text-ink-2">
          {L(
            [
              "Scammers reuse their tools. When two fake sites share a server, a page template, an icon or a phone number, we tie them together, so police can take down the whole operation instead of one site at a time.",
              "المحتالون يعيدون استخدام أدواتهم. عندما يتشارك موقعان مزيفان خادمًا أو قالب صفحة أو أيقونة أو رقم هاتف نربطهما معًا، لتتمكن الشرطة من إيقاف العملية كلها لا موقعًا واحدًا في كل مرة.",
            ],
            lang,
          )}
        </p>
      </header>

      {/* The seven fingerprints we compare */}
      <section aria-label={L(["How sites get linked", "كيف تُربط المواقع"], lang)} className="mt-6">
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7">
          {EDGE_TYPES.map((ty) => {
            const Icon = EDGE_ICON[ty];
            const n = typeCounts.get(ty) ?? 0;
            return (
              <li key={ty} title={L(EDGE_WHY[ty], lang)} className={cn("ops-panel flex items-center gap-2.5 rounded-2xl border border-line bg-surface px-3 py-2.5", n === 0 && "opacity-55")}>
                <span className={cn("grid size-9 shrink-0 place-items-center rounded-xl", n ? "bg-primary/15 text-primary" : "bg-surface-2 text-muted")}>
                  <Icon aria-hidden className="size-[18px]" />
                </span>
                <span className="min-w-0">
                  <span className="block text-xs font-bold leading-tight text-ink-2">{t(`edge_${ty}` as Parameters<typeof t>[0])}</span>
                  <span className="ltr block text-lg font-extrabold leading-tight tabular-nums text-ink">
                    {n} <span className="text-xs font-bold text-muted">{L(n === 1 ? ["link", "رابط"] : ["links", "روابط"], lang)}</span>
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      {isLoading || !full ? (
        <Skeleton className="mt-6 h-[480px] rounded-[20px]" />
      ) : (
        <>
          <section className="mt-8">
            <h2 className="text-xl font-extrabold text-ink">{L(["Operations", "العمليات"], lang)}</h2>
            <p className="mt-1 text-sm text-muted">{L(["Point at a site or a fingerprint to see it. Click a site to open the case.", "أشر إلى موقع أو بصمة لرؤيتها. انقر على موقع لفتح الحالة."], lang)}</p>
            {campaigns.length === 0 ? (
              <p className="mt-3 rounded-[20px] border border-dashed border-line-2 p-8 text-center text-sm text-muted">{t("noEdges")}</p>
            ) : (
              <div className="mt-4 flex flex-col gap-5">
                {campaigns.map((c, i) => (
                  <Operation key={i} index={i} c={c} brandName={brandName} />
                ))}
              </div>
            )}
          </section>

          {unlinked.length > 0 && <Alone nodes={unlinked} brandName={brandName} />}
        </>
      )}
    </div>
  );
}

/* ---- one operation: constellation + dossier ---- */

function Operation({ index, c, brandName }: { index: number; c: Campaign; brandName: (id: string | null) => string | null }) {
  const { t, lang } = useLang();
  const hubs = useMemo(() => hubsOf(c), [c]);
  const brandsHit = [...new Set(c.nodes.map((n) => brandName(n.brand_target)).filter(Boolean))] as string[];
  const verdicts = (["FRAUD", "SUSPICIOUS", "LEGIT"] as const).map((v) => [v, c.nodes.filter((n) => n.verdict === v).length] as const).filter(([, n]) => n > 0);
  const top = c.nodes[0];
  const stats: [string, number, string][] = [
    [L(["Sites", "مواقع"], lang), c.nodes.length, "#e3f2ec"],
    [L(["Top risk", "أعلى خطورة"], lang), c.maxScore, colorOf(top?.verdict ?? "")],
    [L(["Fingerprints", "بصمات"], lang), hubs.length, "#2ee59d"],
  ];

  return (
    <div className="rise-in" style={{ animationDelay: `${index * 80}ms` }}>
      <Panel className="ops-glow grid overflow-visible p-0 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="relative border-b border-line p-3 sm:p-6 lg:border-b-0 lg:border-e">
          <Constellation campaign={c} brandName={brandName} />
        </div>

        <div className="flex flex-col p-5">
          <p className="text-xs font-bold text-muted">{L(["Operation {n}", "العملية {n}"], lang).replace("{n}", String(index + 1))}</p>
          <h3 className="mt-1 text-xl font-extrabold leading-snug text-ink">
            {brandsHit.length ? L(["Copies {b}", "تقلّد {b}"], lang).replace("{b}", brandsHit.slice(0, 3).join(lang === "ar" ? "، " : ", ")) : L(["No brand named", "بدون علامة"], lang)}
          </h3>

          <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
            {stats.map(([label, n, col]) => (
              <div key={label} className="flex flex-col-reverse rounded-xl bg-surface-2 px-2 py-2.5">
                <dt className="text-[11px] font-bold text-muted">{label}</dt>
                <dd className="ltr text-2xl font-extrabold tabular-nums" style={{ color: col }}>
                  {n}
                </dd>
              </div>
            ))}
          </dl>
          <div className="mt-3 flex flex-wrap gap-3">
            {verdicts.map(([v, n]) => (
              <span key={v} className="inline-flex items-center gap-1.5 text-xs font-bold text-ink-2">
                <VerdictPill verdict={v} />
                <span className="ltr tabular-nums">{n}</span>
              </span>
            ))}
          </div>

          <h4 className="mt-5 text-sm font-extrabold text-ink">{L(["What ties them together", "ما يربطها معًا"], lang)}</h4>
          <ul className="mt-2 flex flex-col gap-2">
            {hubs.map((h) => {
              const Icon = EDGE_ICON[h.type];
              return (
                <li key={h.key} className="flex gap-2.5 rounded-xl border border-line bg-surface-2/60 p-2.5">
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/15 text-primary">
                    <Icon aria-hidden className="size-4" />
                  </span>
                  <span className="min-w-0 text-xs">
                    <span className="block font-extrabold text-ink">
                      {t(`edge_${h.type}` as Parameters<typeof t>[0])} <span className="ltr font-bold text-muted">· {shortDetail(h.detail)}</span>
                    </span>
                    <span className="mt-0.5 block leading-snug text-ink-2">{L(EDGE_WHY[h.type], lang)}</span>
                  </span>
                </li>
              );
            })}
          </ul>

          <h4 className="mt-5 text-sm font-extrabold text-ink">{L(["Sites", "المواقع"], lang)}</h4>
          <ul className="mt-1 flex flex-col">
            {c.nodes.map((n) => (
              <li key={n.id}>
                <Link href={`/cases/${n.id}`} className="group flex items-center gap-2.5 rounded-lg px-1.5 py-1.5 hover:bg-surface-2">
                  <span aria-hidden className="size-2 shrink-0 rounded-full" style={{ background: colorOf(n.verdict), boxShadow: `0 0 8px ${colorOf(n.verdict)}` }} />
                  <DomainName domain={n.domain} className="min-w-0 flex-1 truncate text-sm font-bold text-ink" />
                  <span className="ltr text-xs font-bold tabular-nums" style={{ color: colorOf(n.verdict) }}>
                    {n.score}
                  </span>
                  <ChevronRight aria-hidden className="size-4 text-muted rtl:rotate-180" />
                </Link>
              </li>
            ))}
          </ul>

          {top && (
            <Link href={`/cases/${top.id}`} className="mt-5 inline-flex items-center justify-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-sm font-extrabold text-primary-ink hover:brightness-110">
              {L(["Open the highest-risk case", "افتح الحالة الأعلى خطورة"], lang)}
              <ArrowUpRight aria-hidden className="size-4 rtl:-scale-x-100" />
            </Link>
          )}
        </div>
      </Panel>
    </div>
  );
}

/* ---- lone sites: a mosaic by brand, one dot per site ---- */

function Alone({ nodes, brandName }: { nodes: Node[]; brandName: (id: string | null) => string | null }) {
  const { lang } = useLang();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [all, setAll] = useState(false);

  const tiles = useMemo(() => {
    const m = new Map<string, Node[]>();
    for (const n of nodes) {
      const k = n.brand_target ?? "";
      m.set(k, [...(m.get(k) ?? []), n]);
    }
    const fraud = (l: Node[]) => l.filter((n) => n.verdict === "FRAUD").length;
    return [...m.entries()]
      .map(([k, list]) => ({ k, name: k ? brandName(k) ?? k : L(["No brand named", "بدون علامة"], lang), list: [...list].sort((a, b) => b.score - a.score) }))
      .sort((a, b) => fraud(b.list) - fraud(a.list) || b.list.length - a.list.length);
  }, [nodes, brandName, lang]);

  const hits = q.trim() ? nodes.filter((n) => n.domain.toLowerCase().includes(q.trim().toLowerCase())).slice(0, 60) : null;
  const shown = all ? tiles : tiles.slice(0, 12);

  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-extrabold text-ink">
            {L(["Working alone", "تعمل منفردة"], lang)} <span className="ltr text-muted tabular-nums">({nodes.length.toLocaleString("en")})</span>
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            {L(
              [
                "Not tied to other sites yet, grouped by the brand they copy. Each dot is one site: point at it to see the name, click to open it.",
                "غير مرتبطة بمواقع أخرى بعد، مجمّعة حسب العلامة التي تقلّدها. كل نقطة موقع: أشر إليها لرؤية الاسم وانقر لفتحها.",
              ],
              lang,
            )}
          </p>
        </div>
        <label className="relative w-full sm:w-72">
          <span className="sr-only">{L(["Find a domain", "ابحث عن نطاق"], lang)}</span>
          <Search aria-hidden className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={L(["Find a domain", "ابحث عن نطاق"], lang)}
            className="h-10 w-full rounded-full border border-line-2 bg-surface ps-9 pe-9 text-sm font-semibold text-ink placeholder:text-muted focus:border-primary"
          />
          {q && (
            <button type="button" onClick={() => setQ("")} aria-label={L(["Clear", "مسح"], lang)} className="absolute end-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-full text-muted hover:bg-surface-2">
              <X aria-hidden className="size-4" />
            </button>
          )}
        </label>
      </div>

      {hits ? (
        <Panel className="mt-4 p-2">
          {hits.length === 0 ? <p className="p-6 text-center text-sm text-muted">{L(["No domain matches.", "لا يوجد نطاق مطابق."], lang)}</p> : <SiteList list={hits} />}
        </Panel>
      ) : (
        <>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {shown.map((tile) => {
              const isOpen = open === tile.k;
              const f = tile.list.filter((n) => n.verdict === "FRAUD").length;
              const s = tile.list.filter((n) => n.verdict === "SUSPICIOUS").length;
              const total = tile.list.length;
              return (
                <li key={tile.k || "none"} className={cn("ops-panel rounded-[18px] border bg-surface p-4 transition-colors", isOpen ? "border-primary/50 sm:col-span-2 xl:col-span-3" : "border-line hover:border-line-2")}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-base font-extrabold text-ink">{tile.name}</p>
                      <p className="mt-0.5 text-xs font-bold tabular-nums text-muted">
                        {f > 0 && (
                          <span className="text-[#ff6b6b]">
                            {f} {L(["fraud", "احتيال"], lang)}
                          </span>
                        )}
                        {f > 0 && s > 0 && " · "}
                        {s > 0 && (
                          <span className="text-[#f5b93f]">
                            {s} {L(["suspicious", "مشبوه"], lang)}
                          </span>
                        )}
                        {(f > 0 || s > 0) && " · "}
                        {total} {L(["sites", "مواقع"], lang)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setOpen(isOpen ? null : tile.k)}
                      aria-expanded={isOpen}
                      className="inline-flex shrink-0 items-center gap-1 rounded-full border border-line-2 px-3 py-1.5 text-xs font-bold text-ink-2 hover:bg-surface-2"
                    >
                      {isOpen ? L(["Hide", "إخفاء"], lang) : L(["List", "القائمة"], lang)}
                      <ChevronDown aria-hidden className={cn("size-3.5 transition-transform", isOpen && "rotate-180")} />
                    </button>
                  </div>
                  {/* Verdict split */}
                  <div aria-hidden className="mt-3 flex h-1.5 gap-0.5 overflow-hidden rounded-full">
                    {f > 0 && <span style={{ flex: f, background: "#ff6b6b" }} />}
                    {s > 0 && <span style={{ flex: s, background: "#f5b93f" }} />}
                    {total - f - s > 0 && <span style={{ flex: total - f - s, background: "#34d399" }} />}
                  </div>
                  {/* One dot per site */}
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {tile.list.slice(0, isOpen ? 400 : 48).map((n) => (
                      <Link
                        key={n.id}
                        href={`/cases/${n.id}`}
                        tabIndex={-1}
                        aria-hidden
                        title={`${n.domain} · ${n.score}`}
                        className="size-3 rounded-full transition-transform hover:scale-150"
                        style={{ background: colorOf(n.verdict), boxShadow: n.verdict === "FRAUD" ? "0 0 8px #ff6b6b99" : undefined }}
                      />
                    ))}
                    {!isOpen && total > 48 && <span className="ltr text-xs font-bold text-muted">+{total - 48}</span>}
                  </div>
                  {isOpen && (
                    <div className="mt-4 border-t border-line pt-2">
                      <SiteList list={tile.list} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {tiles.length > 12 && (
            <button type="button" onClick={() => setAll(!all)} className="mt-4 inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline">
              {all ? L(["Show fewer brands", "اعرض علامات أقل"], lang) : L(["Show all {n} brands", "اعرض كل العلامات ({n})"], lang).replace("{n}", String(tiles.length))}
              <ChevronDown aria-hidden className={cn("size-4", all && "rotate-180")} />
            </button>
          )}
        </>
      )}
    </section>
  );
}

function SiteList({ list }: { list: Node[] }) {
  return (
    <ul className="grid gap-x-4 sm:grid-cols-2 lg:grid-cols-3">
      {list.map((n) => (
        <li key={n.id}>
          <Link href={`/cases/${n.id}`} className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-surface-2">
            <span aria-hidden className="size-2 shrink-0 rounded-full" style={{ background: colorOf(n.verdict) }} />
            <DomainName domain={n.domain} className="min-w-0 flex-1 truncate text-sm font-bold text-ink" />
            <span className="ltr text-xs font-bold tabular-nums" style={{ color: colorOf(n.verdict) }}>
              {n.score}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
