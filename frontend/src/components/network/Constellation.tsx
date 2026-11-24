"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { ArrowUpRight, CalendarDays, Fingerprint, ImageIcon, LayoutTemplate, Phone, Route, Server, type LucideIcon } from "lucide-react";
import type { Graph } from "@/lib/api";
import type { Campaign } from "@/lib/campaigns";
import { useLang } from "@/lib/i18n";
import { L, type Pair } from "@/lib/radar";
import { SCOPE_COLOR } from "@/components/radar/RadarScope";

/* One scam operation drawn as a constellation: each shared fingerprint (template, server, favicon…) is a hub,
   each site orbits around and links to the hubs it shares. Hover a site or hub for details; click a site to open it. */

type Node = Graph["nodes"][number];
export type EdgeType = Graph["edges"][number]["type"];

export const EDGE_ICON: Record<EdgeType, LucideIcon> = {
  same_ip: Server,
  same_registration_day: CalendarDays,
  same_final_host: Route,
  same_favicon: ImageIcon,
  same_template: LayoutTemplate,
  same_tracker: Fingerprint,
  same_contact: Phone,
};

/** Why each kind of link matters, in plain words. */
export const EDGE_WHY: Record<EdgeType, Pair> = {
  same_ip: ["These sites live on the same server.", "هذه المواقع على الخادم نفسه."],
  same_registration_day: ["Registered on the same day, often by one buyer in bulk.", "سُجّلت في اليوم نفسه، غالبًا من مشترٍ واحد دفعة واحدة."],
  same_final_host: ["They all send visitors to the same final site.", "كلها توجّه الزوار إلى الموقع النهائي نفسه."],
  same_favicon: ["They use the exact same tab icon file.", "تستخدم ملف أيقونة التبويب نفسه تمامًا."],
  same_template: ["Built from the same page template: one scam kit made all of them.", "مبنية من قالب الصفحة نفسه: أداة احتيال واحدة صنعتها كلها."],
  same_tracker: ["They report to the same tracking account.", "ترسل البيانات إلى حساب التتبع نفسه."],
  same_contact: ["They show the same phone number or email.", "تعرض رقم الهاتف أو البريد نفسه."],
};

export type Hub = { key: string; type: EdgeType; detail: string; members: string[] };

export function hubsOf(c: Campaign): Hub[] {
  const m = new Map<string, Hub>();
  for (const e of c.edges) {
    const key = `${e.type}|${e.detail}`;
    const h = m.get(key) ?? { key, type: e.type, detail: e.detail, members: [] };
    for (const id of [e.source, e.target]) if (!h.members.includes(id)) h.members.push(id);
    m.set(key, h);
  }
  return [...m.values()].sort((a, b) => b.members.length - a.members.length);
}

/** Short, readable form of a fingerprint detail ("Same page template 4af32f29…" → "4af32f29"). */
export function shortDetail(d: string) {
  const last = d.split(/\s+/).pop() ?? d;
  return last.length > 18 ? `${last.slice(0, 16)}…` : last;
}

const W = 680;
const H = 440;
const CX = W / 2;
const CY = H / 2;

export function Constellation({ campaign, brandName }: { campaign: Campaign; brandName: (id: string | null) => string | null }) {
  const { t, lang } = useLang();
  const router = useRouter();
  const [active, setActive] = useState<{ kind: "node" | "hub"; id: string } | null>(null);
  const touch = useRef(false);
  const hubs = useMemo(() => hubsOf(campaign), [campaign]);

  const geo = useMemo(() => {
    const k = hubs.length;
    const hubPos = hubs.map((h, i) => {
      if (k === 1) return { h, x: CX, y: CY };
      const a = -Math.PI / 2 + (i / k) * Math.PI * 2;
      const r = k === 2 ? 56 : 74;
      return { h, x: CX + Math.cos(a) * r, y: CY + Math.sin(a) * r };
    });
    // Sites that share a hub sit next to each other on the ring.
    const first = (n: Node) => hubs.findIndex((h) => h.members.includes(n.id));
    const order = [...campaign.nodes].sort((a, b) => first(a) - first(b) || b.score - a.score);
    const nodePos = order.map((n, i) => {
      const a = -Math.PI / 2 + (i / order.length) * Math.PI * 2 + (order.length % 2 ? 0 : Math.PI / order.length);
      return { n, a, x: CX + Math.cos(a) * 190, y: CY + Math.sin(a) * 150 };
    });
    return { hubPos, nodePos };
  }, [hubs, campaign.nodes]);

  const lit = useMemo(() => {
    if (!active) return null;
    if (active.kind === "hub") {
      const h = hubs.find((x) => x.key === active.id);
      return { hubs: new Set([active.id]), nodes: new Set(h?.members ?? []) };
    }
    const mine = hubs.filter((h) => h.members.includes(active.id));
    return { hubs: new Set(mine.map((h) => h.key)), nodes: new Set([active.id, ...mine.flatMap((h) => h.members)]) };
  }, [active, hubs]);

  const showLabels = campaign.nodes.length <= 14;
  const open = (id: string) => router.push(`/cases/${id}`);
  const selNode = active?.kind === "node" ? geo.nodePos.find((p) => p.n.id === active.id) : null;
  const selHub = active?.kind === "hub" ? geo.hubPos.find((p) => p.h.key === active.id) : null;

  return (
    <div className="relative w-full" style={{ aspectRatio: `${W} / ${H}` }} onMouseLeave={() => !touch.current && setActive(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 h-full w-full overflow-visible" role="group" aria-label={L(["Sites in this operation and what links them", "مواقع هذه العملية وما يربطها"], lang)} style={{ direction: "ltr" }}>
        <defs>
          <radialGradient id="cn-bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2ee59d" stopOpacity={0.14} />
            <stop offset="60%" stopColor="#2ee59d" stopOpacity={0.03} />
            <stop offset="100%" stopColor="#2ee59d" stopOpacity={0} />
          </radialGradient>
          <filter id="cn-glow" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <ellipse cx={CX} cy={CY} rx={260} ry={200} fill="url(#cn-bg)" />
        <ellipse cx={CX} cy={CY} rx={190} ry={150} fill="none" stroke="#2ee59d" strokeOpacity={0.12} strokeDasharray="2 7" />
        <ellipse cx={CX} cy={CY} rx={95} ry={75} fill="none" stroke="#2ee59d" strokeOpacity={0.08} strokeDasharray="2 7" />

        {/* Links: a faint base line plus dashes travelling toward the shared fingerprint */}
        {geo.hubPos.map(({ h, x: hx, y: hy }) =>
          h.members.map((id) => {
            const p = geo.nodePos.find((q) => q.n.id === id);
            if (!p) return null;
            const mx = (p.x + hx) / 2;
            const my = (p.y + hy) / 2;
            const len = Math.hypot(hx - p.x, hy - p.y) || 1;
            const cx = mx + (-(hy - p.y) / len) * 14;
            const cy = my + ((hx - p.x) / len) * 14;
            const d = `M${p.x},${p.y} Q${cx},${cy} ${hx},${hy}`;
            const on = !lit || (lit.hubs.has(h.key) && lit.nodes.has(id) && (active?.kind === "hub" || active?.id === id || lit.hubs.has(h.key)));
            const strong = lit && on;
            return (
              <g key={`${h.key}-${id}`} style={{ opacity: on ? 1 : 0.15, transition: "opacity 150ms" }}>
                <path d={d} fill="none" stroke="#2ee59d" strokeOpacity={strong ? 0.5 : 0.2} strokeWidth={strong ? 2 : 1.25} />
                <path d={d} fill="none" stroke={SCOPE_COLOR[p.n.verdict as keyof typeof SCOPE_COLOR] ?? "#2ee59d"} strokeOpacity={0.9} strokeWidth={strong ? 2.5 : 1.75} className="link-flow" />
              </g>
            );
          }),
        )}

        {/* Hubs: the shared fingerprints */}
        {geo.hubPos.map(({ h, x, y }) => {
          const Icon = EDGE_ICON[h.type];
          const on = !lit || lit.hubs.has(h.key);
          const hex = Array.from({ length: 6 }, (_, i) => {
            const a = Math.PI / 6 + (i * Math.PI) / 3;
            return `${x + Math.cos(a) * 26},${y + Math.sin(a) * 26}`;
          }).join(" ");
          return (
            <g
              key={h.key}
              tabIndex={0}
              role="button"
              aria-label={`${t(`edge_${h.type}` as Parameters<typeof t>[0])}: ${h.detail}`}
              className="cursor-pointer outline-none"
              style={{ opacity: on ? 1 : 0.3, transition: "opacity 150ms" }}
              onPointerEnter={(e) => {
                touch.current = e.pointerType === "touch";
                setActive({ kind: "hub", id: h.key });
              }}
              onFocus={() => setActive({ kind: "hub", id: h.key })}
              onBlur={() => setActive(null)}
              onClick={() => setActive({ kind: "hub", id: h.key })}
            >
              <circle cx={x} cy={y} r={30} fill="none" stroke="#2ee59d" strokeOpacity={0.5} className="blip-ping" />
              <polygon points={hex} fill="#0b2219" stroke="#2ee59d" strokeWidth={2} filter="url(#cn-glow)" />
              <Icon x={x - 11} y={y - 11} width={22} height={22} color="#2ee59d" strokeWidth={2} aria-hidden />
              {geo.hubPos.length <= 3 && (
                <>
                  <text x={x} y={y + 46} textAnchor="middle" fontSize={13} fontWeight={800} fill="#e3f2ec" className="max-sm:text-[22px]">
                    {t(`edge_${h.type}` as Parameters<typeof t>[0])}
                  </text>
                  <text x={x} y={y + 64} textAnchor="middle" fontSize={11} fontWeight={700} fill="#86a096" className="max-sm:hidden">
                    {shortDetail(h.detail)}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {/* Sites */}
        {geo.nodePos.map(({ n, a, x, y }) => {
          const color = SCOPE_COLOR[n.verdict as keyof typeof SCOPE_COLOR] ?? "#b7b2ad";
          const on = !lit || lit.nodes.has(n.id);
          const sel = active?.kind === "node" && active.id === n.id;
          const r = 8 + (n.score / 100) * 5;
          const cos = Math.cos(a);
          const anchor = cos > 0.3 ? "start" : cos < -0.3 ? "end" : "middle";
          const lx = x + (anchor === "start" ? r + 9 : anchor === "end" ? -(r + 9) : 0);
          const ly = anchor === "middle" ? (Math.sin(a) < 0 ? y - r - 10 : y + r + 18) : y + 4;
          return (
            <g
              key={n.id}
              role="link"
              tabIndex={0}
              aria-label={`${n.domain}: ${t(n.verdict)} ${n.score}. ${L(["Open case", "افتح الحالة"], lang)}`}
              className="cursor-pointer outline-none"
              style={{ opacity: on ? 1 : 0.3, transition: "opacity 150ms" }}
              onPointerEnter={(e) => {
                touch.current = e.pointerType === "touch";
                if (!touch.current) setActive({ kind: "node", id: n.id });
              }}
              onFocus={() => setActive({ kind: "node", id: n.id })}
              onBlur={() => setActive(null)}
              onClick={() => {
                if (touch.current && !sel) return setActive({ kind: "node", id: n.id });
                open(n.id);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  open(n.id);
                }
              }}
            >
              <circle cx={x} cy={y} r={r + 10} fill="transparent" />
              <circle cx={x} cy={y} r={r + 5} fill={color} fillOpacity={0.12} />
              <circle cx={x} cy={y} r={sel ? r + 2 : r} fill={color} filter="url(#cn-glow)" />
              {sel && <circle cx={x} cy={y} r={r + 8} fill="none" stroke="#e3f2ec" strokeWidth={1.5} />}
              {showLabels && (
                <text x={lx} y={ly} textAnchor={anchor} fontSize={13} fontWeight={800} fill="#e3f2ec" className="max-sm:hidden">
                  {n.domain.length > 24 ? `${n.domain.slice(0, 22)}…` : n.domain}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {selNode && (
        <Card x={selNode.x} y={selNode.y}>
          <div className="flex items-center justify-between gap-2">
            <VerdictPill verdict={selNode.n.verdict} />
            <span className="ltr text-2xl font-extrabold tabular-nums" style={{ color: SCOPE_COLOR[selNode.n.verdict as keyof typeof SCOPE_COLOR] }}>
              {selNode.n.score}
            </span>
          </div>
          <p className="ltr mt-2 break-all text-[15px] font-extrabold text-ink">{selNode.n.domain}</p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted">{L(["Imitates", "يقلّد"], lang)}</dt>
            <dd className="truncate font-bold text-ink-2">{brandName(selNode.n.brand_target) ?? L(["No brand named", "بدون علامة"], lang)}</dd>
            <dt className="text-muted">{L(["Linked by", "مرتبط عبر"], lang)}</dt>
            <dd className="font-bold text-ink-2">
              {hubs
                .filter((h) => h.members.includes(selNode.n.id))
                .map((h) => t(`edge_${h.type}` as Parameters<typeof t>[0]))
                .join(", ")}
            </dd>
          </dl>
          <button type="button" onClick={() => open(selNode.n.id)} className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-primary px-3 py-2 text-xs font-extrabold text-primary-ink hover:brightness-110">
            {L(["Open case", "افتح الحالة"], lang)}
            <ArrowUpRight aria-hidden className="size-3.5 rtl:-scale-x-100" />
          </button>
        </Card>
      )}
      {selHub && (
        <Card x={selHub.x} y={selHub.y}>
          <p className="text-xs font-bold text-primary">{L(["Shared fingerprint", "بصمة مشتركة"], lang)}</p>
          <p className="mt-1 text-[15px] font-extrabold text-ink">{t(`edge_${selHub.h.type}` as Parameters<typeof t>[0])}</p>
          <p className="ltr mt-1 break-all rounded-lg bg-surface-2 px-2 py-1 text-xs text-ink-2">{selHub.h.detail}</p>
          <p className="mt-2 text-xs leading-snug text-ink-2">{L(EDGE_WHY[selHub.h.type], lang)}</p>
          <p className="mt-2 text-xs font-bold text-muted">{L(["Shared by {n} sites", "تتشاركها {n} مواقع"], lang).replace("{n}", String(selHub.h.members.length))}</p>
        </Card>
      )}
    </div>
  );
}

function Card({ x, y, children }: { x: number; y: number; children: React.ReactNode }) {
  const { lang } = useLang();
  const left = (x / W) * 100;
  const top = (y / H) * 100;
  return (
    <div
      role="tooltip"
      className="pointer-events-auto absolute z-20 w-64 rounded-2xl border border-line-2 bg-[#0b1512]/95 p-3.5 text-start shadow-[0_20px_50px_-20px_rgba(0,0,0,0.9),0_0_0_1px_rgba(46,229,157,0.12)] backdrop-blur-md"
      style={{
        left: `${left}%`,
        top: `${top}%`,
        transform: `translate(${left > 50 ? "calc(-100% - 20px)" : "20px"}, ${top > 55 ? "calc(-100% + 10px)" : "-10px"})`,
        direction: lang === "ar" ? "rtl" : "ltr",
      }}
    >
      {children}
    </div>
  );
}

export function VerdictPill({ verdict }: { verdict: string }) {
  const { t } = useLang();
  const color = SCOPE_COLOR[verdict as keyof typeof SCOPE_COLOR] ?? "#b7b2ad";
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-extrabold" style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}>
      <span aria-hidden className="size-1.5 rounded-full" style={{ background: color }} />
      {t(verdict as Parameters<typeof t>[0])}
    </span>
  );
}
