"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useGraph, type Graph } from "@/lib/api";
import { useLang } from "@/lib/i18n";
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

export default function GraphPage() {
  const { t } = useLang();
  const { data, error, isLoading, mutate } = useGraph();
  const [sel, setSel] = useState<string | null>(null);
  const W = 860;
  const H = 520;
  const pos = useMemo(() => (data ? layout(data, W, H) : []), [data]);

  if (error) return <ErrorState error={error} onRetry={() => mutate()} />;

  const idx = new Map((data?.nodes ?? []).map((n, i) => [n.id, i]));
  const connected = new Set(sel ? (data?.edges ?? []).filter((e) => e.source === sel || e.target === sel).flatMap((e) => [e.source, e.target]) : []);
  const selEdges = sel ? (data?.edges ?? []).filter((e) => e.source === sel || e.target === sel) : [];
  const selNode = data?.nodes.find((n) => n.id === sel);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("graphTitle")}</h1>
        <p className="mt-1 max-w-2xl text-muted">{t("graphSub")}</p>
      </div>

      {isLoading || !data ? (
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
                      {n.domain.length > 20 ? `${n.domain.slice(0, 17)}…` : n.domain}
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
                <h2 className="ltr mt-2 break-all text-lg font-extrabold">{selNode.domain}</h2>
                <Link href={`/cases/${selNode.id}`} className="text-sm font-bold text-primary underline">
                  {t("openCase")}
                </Link>
                <p className="mt-4 text-xs font-bold text-muted">{t("links", { n: selEdges.length })}</p>
                <ul className="mt-2 flex flex-col gap-2">
                  {selEdges.map((e, i) => {
                    const other = data.nodes.find((n) => n.id === (e.source === sel ? e.target : e.source));
                    return (
                      <li key={i} className="rounded-xl bg-surface-2 p-2.5 text-sm">
                        <span className="rounded-full bg-primary-soft px-2 py-0.5 text-xs font-bold text-primary">{t(`edge_${e.type}`)}</span>
                        <p className="ltr mt-1 font-bold">{other?.domain}</p>
                        <p className="ltr text-xs text-muted">{e.detail}</p>
                      </li>
                    );
                  })}
                </ul>
              </>
            ) : (
              <>
                <PanelTitle>{t("links", { n: data.edges.length })}</PanelTitle>
                {data.edges.length === 0 ? (
                  <p className="mt-2 text-sm text-muted">{t("noEdges")}</p>
                ) : (
                  <ul className="mt-3 flex flex-col gap-1.5">
                    {data.nodes.map((n) => (
                      <li key={n.id}>
                        <button type="button" onClick={() => setSel(n.id)} className={cn("flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-start hover:bg-surface-2")}>
                          <span className="ltr truncate text-sm font-bold">{n.domain}</span>
                          <span className="ltr text-xs tabular-nums" style={{ color: verdictHex[n.verdict] }}>
                            {n.score}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
