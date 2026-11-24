"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ChevronRight, LayoutGrid, Share2 } from "lucide-react";
import { useGraph, type Graph } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { isLocalDemo, toCampaigns } from "@/lib/campaigns";
import { cn } from "@/lib/utils";
import { verdictHex, VerdictChip } from "@/components/ui/verdict";
import { ErrorState, Panel, PanelTitle, Skeleton } from "@/components/ui/primitives";

/* A small deterministic force layout: enough nodes to show the idea, no library needed. */
function layout(g: Graph, w: number, h: number) {
  const n = g.nodes.length;
  const pos = g.nodes.map((_, i) => {
    const a = (i / Math.max(1, n)) * Math.PI * 2;
    return { x: w / 2 + Math.cos(a) * Math.min(w, h) * 0.32, y: h / 2 + Math.sin(a) * Math.min(w, h) * 0.32, vx: 0, vy: 0 };
  });
  const idx = new Map(g.nodes.map((nd, i) => [nd.id, i]));
  for (let iter = 0; iter < 300; iter++) {
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const dx = pos[j].x - pos[i].x;
        const dy = pos[j].y - pos[i].y;
        const d2 = Math.max(100, dx * dx + dy * dy);
        const f = 9000 / d2;
        const d = Math.sqrt(d2);
        pos[i].vx -= (dx / d) * f;
        pos[i].vy -= (dy / d) * f;
        pos[j].vx += (dx / d) * f;
        pos[j].vy += (dy / d) * f;
      }
    for (const e of g.edges) {
      const a = idx.get(e.source);
      const b = idx.get(e.target);
      if (a === undefined || b === undefined) continue;
      const dx = pos[b].x - pos[a].x;
      const dy = pos[b].y - pos[a].y;
      const d = Math.max(1, Math.hypot(dx, dy));
      const f = (d - 130) * 0.02;
      pos[a].vx += (dx / d) * f;
      pos[a].vy += (dy / d) * f;
      pos[b].vx -= (dx / d) * f;
      pos[b].vy -= (dy / d) * f;
    }
    for (const p of pos) {
      p.vx += (w / 2 - p.x) * 0.003;
      p.vy += (h / 2 - p.y) * 0.003;
      p.x = Math.max(60, Math.min(w - 60, p.x + p.vx * 0.5));
      // Leave room under the bottom row for the label (circle radius up to 26 + label offset 14).
      p.y = Math.max(40, Math.min(h - 56, p.y + p.vy * 0.5));
      p.vx *= 0.6;
      p.vy *= 0.6;
    }
  }
  return pos;
}

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
  const { t } = useLang();
  const { data: full, error, isLoading, mutate } = useGraph();
  const [view, setView] = useState<"groups" | "map">("groups");
  const { campaigns, unlinked } = useMemo(() => toCampaigns(full), [full]);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3 pt-2">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("graphTitle")}</h1>
          <p className="mt-1 max-w-2xl text-muted">{t("graphSub")}</p>
        </div>
        <div role="tablist" aria-label={t("graphTitle")} className="inline-flex rounded-full bg-surface-2 p-1">
          {(
            [
              ["groups", t("viewGroups"), LayoutGrid],
              ["map", t("viewMap"), Share2],
            ] as const
          ).map(([v, label, Icon]) => (
            <button
              key={v}
              role="tab"
              type="button"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={cn("inline-flex h-9 items-center gap-1.5 rounded-full px-4 text-sm font-bold", view === v ? "bg-surface text-ink shadow-sm" : "text-muted")}
            >
              <Icon aria-hidden className="size-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : isLoading || !full ? (
        <Skeleton className="h-[520px] rounded-[16px]" />
      ) : view === "groups" ? (
        <Groups campaigns={campaigns} unlinked={unlinked} />
      ) : (
        <MapView full={full} campaigns={campaigns} unlinked={unlinked} />
      )}
    </div>
  );
}

function Groups({ campaigns, unlinked }: ReturnType<typeof toCampaigns>) {
  const { t } = useLang();
  return (
    <div className="flex flex-col gap-6">
      <section>
        <PanelTitle hint={t("campaignsSub")}>{t("campaignsTitle")}</PanelTitle>
        {campaigns.length === 0 ? (
          <p className="mt-3 rounded-[16px] border border-dashed border-line-2 p-8 text-center text-sm text-muted">{t("noEdges")}</p>
        ) : (
          <div className="mt-3 grid gap-4 lg:grid-cols-2">
            {campaigns.map((c, i) => {
              const details = [...new Map(c.edges.map((e) => [`${e.type}|${e.detail}`, e])).values()];
              return (
                <Panel key={i} className="p-4 sm:p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="text-lg font-extrabold text-ink">
                      {t("campaign", { n: i + 1 })} <span className="text-muted">·</span> <span className="text-ink-2">{t("campaignDomains", { n: c.nodes.length })}</span>
                    </h2>
                    <div className="flex flex-wrap gap-1.5">
                      {c.types.map((ty) => (
                        <span key={ty} className="rounded-full bg-primary-soft px-2.5 py-1 text-xs font-bold text-primary">
                          {t(`edge_${ty}` as Parameters<typeof t>[0])}
                        </span>
                      ))}
                    </div>
                  </div>
                  <ul className="mt-3 flex flex-col">
                    {c.nodes.map((n, j) => (
                      <li key={n.id} className={cn(j > 0 && "border-t border-line")}>
                        <Link href={`/cases/${n.id}`} className="group flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-surface-2">
                          <VerdictChip verdict={n.verdict} size="sm" />
                          <span className="ltr text-xs font-bold tabular-nums text-muted">{n.score}</span>
                          <DomainName domain={n.domain} className="min-w-0 flex-1 truncate text-sm font-extrabold text-ink" />
                          <ChevronRight aria-hidden className="size-4 text-muted rtl:rotate-180" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <details className="group mt-2 border-t border-line pt-2">
                    <summary className="cursor-pointer list-none text-sm font-bold text-ink-2 hover:text-ink">
                      {t(details.length === 1 ? "link1" : "links", { n: details.length })}
                    </summary>
                    <ul className="mt-2 flex flex-col gap-1.5">
                      {details.map((e, k) => (
                        <li key={k} className="flex flex-wrap items-baseline gap-2 text-xs">
                          <span className="rounded-full bg-surface-2 px-2 py-0.5 font-bold text-ink-2">{t(`edge_${e.type}` as Parameters<typeof t>[0])}</span>
                          <span className="ltr break-all text-muted">{e.detail}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                </Panel>
              );
            })}
          </div>
        )}
      </section>

      {unlinked.length > 0 && (
        <section>
          <PanelTitle hint={t("unlinkedSub")}>
            {t("unlinkedTitle")} <span className="ltr text-muted tabular-nums">({unlinked.length})</span>
          </PanelTitle>
          <ul className="mt-3 grid gap-x-4 rounded-[16px] border border-line bg-surface p-2 sm:grid-cols-2 lg:grid-cols-3">
            {unlinked.map((n) => (
              <li key={n.id}>
                <Link href={`/cases/${n.id}`} className="flex items-center gap-2.5 rounded-xl px-2 py-2 hover:bg-surface-2">
                  <VerdictChip verdict={n.verdict} size="sm" />
                  <DomainName domain={n.domain} className="min-w-0 flex-1 truncate text-sm font-bold text-ink" />
                  <span className="ltr text-xs tabular-nums text-muted">{n.score}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/* The map draws only linked domains, so the groups stand out; lone domains stay in the side list. */
function MapView({ full, campaigns, unlinked }: { full: Graph } & ReturnType<typeof toCampaigns>) {
  const { t } = useLang();
  const [sel, setSel] = useState<string | null>(null);
  const W = 860;
  const H = 520;
  const data = useMemo<Graph>(() => {
    const ids = new Set(campaigns.flatMap((c) => c.nodes.map((n) => n.id)));
    return { nodes: full.nodes.filter((n) => ids.has(n.id)), edges: full.edges.filter((e) => ids.has(e.source) && ids.has(e.target)) };
  }, [full, campaigns]);
  const pos = useMemo(() => layout(data, W, H), [data]);
  const isLoading = false;

  const idx = new Map(data.nodes.map((n, i) => [n.id, i]));
  const connected = new Set(sel ? (data?.edges ?? []).filter((e) => e.source === sel || e.target === sel).flatMap((e) => [e.source, e.target]) : []);
  const selEdges = sel ? (data?.edges ?? []).filter((e) => e.source === sel || e.target === sel) : [];
  const selNode = data?.nodes.find((n) => n.id === sel);

  return (
    <div>
      {isLoading ? (
        <Skeleton className="h-[520px] rounded-[16px]" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <Panel className="overflow-hidden p-2">
            <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={t("graphTitle")} style={{ direction: "ltr" }}>
              {data.edges.map((e, i) => {
                const a = idx.get(e.source);
                const b = idx.get(e.target);
                if (a === undefined || b === undefined) return null;
                const hot = sel === e.source || sel === e.target;
                return <line key={i} x1={pos[a].x} y1={pos[a].y} x2={pos[b].x} y2={pos[b].y} stroke={hot ? "var(--primary)" : "var(--line-2)"} strokeWidth={hot ? 3 : 1.5} strokeOpacity={sel && !hot ? 0.3 : 1} />;
              })}
              {data.nodes.map((n, i) => {
                const dim = sel && sel !== n.id && !connected.has(n.id);
                const r = 14 + (n.score / 100) * 12;
                return (
                  <g key={n.id} transform={`translate(${pos[i].x},${pos[i].y})`} opacity={dim ? 0.3 : 1} className="cursor-pointer" onClick={() => setSel(sel === n.id ? null : n.id)} tabIndex={0} role="button" aria-label={`${n.domain}: ${t(n.verdict)} ${n.score}`} onKeyDown={(e) => e.key === "Enter" && setSel(sel === n.id ? null : n.id)}>
                    <circle r={r} fill={verdictHex[n.verdict]} fillOpacity={0.15} stroke={verdictHex[n.verdict]} strokeWidth={sel === n.id ? 4 : 2} />
                    <text y={r + 14} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">
                      {/* Long hacked-site names would run into their neighbours; the side list has the full name. */}
                      {isLocalDemo(n.domain) ? t("localDemo") : n.domain.length > 20 ? `${n.domain.slice(0, 17)}…` : n.domain}
                    </text>
                  </g>
                );
              })}
            </svg>
          </Panel>

          <Panel className="p-4">
            {selNode ? (
              <>
                <VerdictChip verdict={selNode.verdict} />
                <h2 className="mt-2 break-all text-lg font-extrabold">
                  <DomainName domain={selNode.domain} />
                </h2>
                <Link href={`/cases/${selNode.id}`} className="text-sm font-bold text-primary underline">
                  {t("openCase")}
                </Link>
                <p className="mt-4 text-xs font-bold text-muted">{t(selEdges.length === 1 ? "link1" : "links", { n: selEdges.length })}</p>
                <ul className="mt-2 flex flex-col gap-2">
                  {selEdges.map((e, i) => {
                    const other = data.nodes.find((n) => n.id === (e.source === sel ? e.target : e.source));
                    return (
                      <li key={i} className="rounded-xl bg-surface-2 p-2.5 text-sm">
                        <span className="rounded-full bg-primary-soft px-2 py-0.5 text-xs font-bold text-primary">{t(`edge_${e.type}`)}</span>
                        <p className="mt-1 font-bold">{other && <DomainName domain={other.domain} />}</p>
                        <p className="ltr text-xs text-muted">{e.detail}</p>
                      </li>
                    );
                  })}
                </ul>
              </>
            ) : (
              <>
                <PanelTitle>{t(data.edges.length === 1 ? "link1" : "links", { n: data.edges.length })}</PanelTitle>
                {data.edges.length === 0 ? (
                  <p className="mt-2 text-sm text-muted">{t("noEdges")}</p>
                ) : (
                  <ul className="mt-3 flex flex-col gap-1.5">
                    {data.nodes.map((n) => (
                      <li key={n.id}>
                        <button type="button" onClick={() => setSel(n.id)} className={cn("flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-start hover:bg-surface-2")}>
                          <DomainName domain={n.domain} className="truncate text-sm font-bold" />
                          <span className="ltr text-xs tabular-nums" style={{ color: verdictHex[n.verdict] }}>
                            {n.score}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {unlinked.length > 0 && (
                  <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
                    {t("unlinkedTitle")}: <span className="font-bold tabular-nums">{unlinked.length}</span>
                  </p>
                )}
              </>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
