"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { ArrowUpRight, Ban, ShieldCheck, TriangleAlert } from "lucide-react";
import type { CaseSummary } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { CATEGORIES, L } from "@/lib/radar";
import { cn, fmtAgo } from "@/lib/utils";

/* The interactive radar scope.
   Every blip is one site: its angle is the sector it imitates, its distance from the centre is risk
   (closest = highest score). Hover or focus shows the site; click (or Enter) opens the case.
   On touch, the first tap shows the card and the card's button opens the case. */

export type ScopeItem = CaseSummary & { brand_category?: string | null };

export const SCOPE_COLOR = { FRAUD: "#ff6b6b", SUSPICIOUS: "#f5b93f", LEGIT: "#34d399" } as const;
const COLOR = SCOPE_COLOR;
const ICON = { FRAUD: Ban, SUSPICIOUS: TriangleAlert, LEGIT: ShieldCheck } as const;

// One-word sector names for the scope's edge; the full name is in the hover card and the filter chips.
const SHORT: Record<string, [string, string]> = {
  government: ["Government", "الحكومة"],
  police: ["Police", "الشرطة"],
  transport: ["Roads", "الطرق"],
  bank: ["Banks", "البنوك"],
  delivery: ["Delivery", "التوصيل"],
  utility: ["Utilities", "الكهرباء"],
  telecom: ["Telecom", "الاتصالات"],
  shopping: ["Shopping", "التسوق"],
  travel: ["Travel", "السفر"],
  none: ["Other", "أخرى"],
};

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967295;
}

export function RadarScope({
  items,
  categoryOf,
  brandName,
  live = false,
  max = 60,
  className,
}: {
  items: ScopeItem[];
  categoryOf: (it: ScopeItem) => string;
  brandName: (id: string | null) => string | null;
  live?: boolean;
  /** Most dots drawn at once; more than this cannot be hovered one by one. */
  max?: number;
  className?: string;
}) {
  const { t, lang } = useLang();
  const router = useRouter();
  const [active, setActive] = useState<string | null>(null);
  const touchRef = useRef(false);
  const S = 600;
  const C = S / 2;
  const R = 232;

  // Sectors: only the categories that have sites, most populated first, so the scope reads as "who is being copied".
  const sectors = useMemo(() => {
    const counts = new Map<string, number>();
    for (const it of items) counts.set(categoryOf(it), (counts.get(categoryOf(it)) ?? 0) + 1);
    const keys = [...counts.keys()].sort((a, b) => (a === "none" ? 1 : b === "none" ? -1 : (counts.get(b) ?? 0) - (counts.get(a) ?? 0)));
    const span = (Math.PI * 2) / Math.max(1, keys.length);
    return keys.map((k, i) => ({ key: k, start: -Math.PI / 2 + i * span, span, count: counts.get(k) ?? 0 }));
  }, [items, categoryOf]);

  // Too many to hover one by one: take a mix of fraud, suspicious and safe, rotating through the sectors
  // inside each group so the scope shows every kind of brand being copied, not one crowded corner.
  const shown = useMemo(() => {
    if (items.length <= max) return items;
    const spread = (list: ScopeItem[]) => {
      const by = new Map<string, ScopeItem[]>();
      for (const it of [...list].sort((x, y) => y.score - x.score || y.discovered_at.localeCompare(x.discovered_at))) {
        const k = categoryOf(it);
        by.set(k, [...(by.get(k) ?? []), it]);
      }
      const queues = [...by.values()];
      const out: ScopeItem[] = [];
      for (let i = 0; out.length < list.length; i++) for (const q of queues) if (q[i]) out.push(q[i]);
      return out;
    };
    const groups = (["FRAUD", "SUSPICIOUS", "LEGIT"] as const).map((v) => spread(items.filter((it) => it.verdict === v)));
    const quota = [0.4, 0.3, 0.3].map((f) => Math.round(max * f));
    const picked = groups.map((g, i) => g.slice(0, quota[i]));
    // Hand unused places to the groups that still have sites, most urgent first.
    let left = max - picked.reduce((n, g) => n + g.length, 0);
    for (let i = 0; i < 3 && left > 0; i++) {
      const more = groups[i].slice(picked[i].length, picked[i].length + left);
      picked[i].push(...more);
      left -= more.length;
    }
    return picked.flat();
  }, [items, max, categoryOf]);

  const blips = useMemo(() => {
    const sec = new Map(sectors.map((s) => [s.key, s]));
    const pts = shown.map((it) => {
      const s = sec.get(categoryOf(it))!;
      const a = s.start + s.span * (0.08 + hash(it.id) * 0.84);
      // Risk 100 sits near the centre, risk 0 at the rim; a little jitter keeps ties apart.
      const rr = (0.14 + (1 - it.score / 100) * 0.62 + hash(it.id + "j") * 0.24) * R;
      return { it, x: C + Math.cos(a) * rr, y: C + Math.sin(a) * rr, color: COLOR[it.verdict as keyof typeof COLOR] ?? "#b7b2ad" };
    });
    // Push overlapping dots apart so every one can be hovered, then keep them inside the disc.
    const GAP = 20;
    for (let pass = 0; pass < 6; pass++) {
      for (let i = 0; i < pts.length; i++)
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[j].x - pts[i].x;
          const dy = pts[j].y - pts[i].y;
          const d = Math.hypot(dx, dy);
          if (d >= GAP) continue;
          const ux = d ? dx / d : Math.cos(i + j);
          const uy = d ? dy / d : Math.sin(i + j);
          const push = (GAP - d) / 2;
          pts[i].x -= ux * push;
          pts[i].y -= uy * push;
          pts[j].x += ux * push;
          pts[j].y += uy * push;
        }
      for (const p of pts) {
        const dx = p.x - C;
        const dy = p.y - C;
        const d = Math.hypot(dx, dy);
        if (d > R - 10) {
          p.x = C + (dx / d) * (R - 10);
          p.y = C + (dy / d) * (R - 10);
        }
      }
    }
    return pts;
  }, [shown, sectors, categoryOf, C]);

  const sel = blips.find((b) => b.it.id === active) ?? null;
  const open = (id: string) => router.push(`/cases/${id}`);

  return (
    <div className={cn("relative mx-auto aspect-square w-full", className)} onMouseLeave={() => !touchRef.current && setActive(null)}>
      {/* Sweep sits behind the SVG so blips stay crisp. */}
      <div aria-hidden className="pointer-events-none absolute inset-[11.33%] overflow-hidden rounded-full">
        <div
          className={cn("radar-sweep absolute inset-0 rounded-full", !live && "radar-sweep-idle")}
          style={{ background: "conic-gradient(from 0deg, rgba(46,229,157,0.42), rgba(46,229,157,0) 60deg, transparent 360deg)" }}
        />
      </div>

      <svg viewBox={`0 0 ${S} ${S}`} className="relative h-full w-full overflow-visible" role="group" aria-label={L(["Radar: each dot is a site, closer to the centre is higher risk", "الرادار: كل نقطة موقع، والأقرب إلى المركز أعلى خطورة"], lang)}>
        <defs>
          <radialGradient id="scope-bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0f3326" />
            <stop offset="70%" stopColor="#07120e" />
            <stop offset="100%" stopColor="#050a08" />
          </radialGradient>
          <filter id="blip-glow" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle cx={C} cy={C} r={R} fill="url(#scope-bg)" fillOpacity={0.92} stroke="#2ee59d" strokeOpacity={0.35} />
        {/* Risk rings, labelled once along the top */}
        {[0.25, 0.5, 0.75].map((f) => (
          <circle key={f} cx={C} cy={C} r={R * f} fill="none" stroke="#2ee59d" strokeOpacity={0.14} strokeDasharray="2 6" />
        ))}
        {[
          [0.2, L(["Fraud", "احتيال"], lang)],
          [0.5, L(["Suspicious", "مشبوه"], lang)],
          [0.86, L(["Low", "منخفض"], lang)],
        ].map(([f, label]) => (
          <text key={String(label)} x={C + 6} y={C - R * (f as number) + 5} fontSize={13} fill="#86a096" fontWeight={700} style={{ direction: "ltr" }}>
            {label as string}
          </text>
        ))}

        {/* Sector dividers and labels: who the sites imitate */}
        {sectors.map((s) => {
          const lx = C + Math.cos(s.start) * R;
          const ly = C + Math.sin(s.start) * R;
          const mid = s.start + s.span / 2;
          const tx = C + Math.cos(mid) * (R + 34);
          const ty = C + Math.sin(mid) * (R + 34);
          return (
            <g key={s.key}>
              {sectors.length > 1 && <line x1={C} y1={C} x2={lx} y2={ly} stroke="#2ee59d" strokeOpacity={0.12} />}
              <text x={tx} y={ty - 6} textAnchor="middle" fontSize={17} fontWeight={800} fill="#c9dcd4">
                {L(SHORT[s.key] ?? SHORT.none, lang)}
              </text>
              <text x={tx} y={ty + 13} textAnchor="middle" fontSize={14} fontWeight={700} fill="#86a096" style={{ direction: "ltr" }}>
                {s.count}
              </text>
            </g>
          );
        })}

        <circle cx={C} cy={C} r={6} fill="#f97316" filter="url(#blip-glow)" />

        {/* Blips */}
        {blips.map(({ it, x, y, color }, i) => {
          const on = active === it.id;
          const dim = active && !on;
          const r = it.verdict === "FRAUD" ? 7 : 6;
          return (
            <g
              key={it.id}
              role="link"
              tabIndex={0}
              aria-label={`${it.domain}: ${t(it.verdict)} ${it.score}. ${L(["Open case", "افتح الحالة"], lang)}`}
              className="cursor-pointer outline-none"
              style={{ opacity: dim ? 0.35 : 1, transition: "opacity 150ms" }}
              onPointerEnter={(e) => {
                touchRef.current = e.pointerType === "touch";
                if (!touchRef.current) setActive(it.id);
              }}
              onFocus={() => setActive(it.id)}
              onBlur={() => setActive((a) => (a === it.id ? null : a))}
              onClick={(e) => {
                const touch = (e.nativeEvent as PointerEvent).pointerType === "touch" || touchRef.current;
                if (touch && active !== it.id) return setActive(it.id);
                open(it.id);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  open(it.id);
                }
                if (e.key === "Escape") setActive(null);
              }}
            >
              {/* Big invisible hit target: easier than a 12px dot */}
              <circle cx={x} cy={y} r={11} fill="transparent" />
              {it.verdict === "FRAUD" && it.status === "new" && (
                <circle cx={x} cy={y} r={r + 6} fill="none" stroke={color} strokeOpacity={0.5} className="blip-ping" style={{ animationDelay: `${(i % 7) * 0.35}s` }} />
              )}
              {it.status === "confirmed" && <circle cx={x} cy={y} r={r + 4} fill="none" stroke={color} strokeWidth={1.5} />}
              <circle cx={x} cy={y} r={on ? r + 3 : r} fill={color} filter="url(#blip-glow)" style={{ transition: "r 150ms" }} />
              {on && <circle cx={x} cy={y} r={r + 9} fill="none" stroke="#e3f2ec" strokeWidth={1.5} />}
            </g>
          );
        })}
      </svg>

      {items.length > shown.length && (
        <p className="pointer-events-none absolute inset-x-0 bottom-0 text-center text-xs font-semibold text-muted">
          {L(["Showing the {n} most urgent of {t} sites", "يعرض أهم {n} من {t} موقعًا"], lang).replace("{n}", String(shown.length)).replace("{t}", items.length.toLocaleString("en"))}
        </p>
      )}

      {/* Hover / focus card */}
      {sel && <BlipCard sel={sel} size={S} brand={brandName(sel.it.brand_target)} category={categoryOf(sel.it)} onOpen={() => open(sel.it.id)} />}
    </div>
  );
}

function BlipCard({
  sel,
  size,
  brand,
  category,
  onOpen,
}: {
  sel: { it: ScopeItem; x: number; y: number; color: string };
  size: number;
  brand: string | null;
  category: string;
  onOpen: () => void;
}) {
  const { t, lang } = useLang();
  const { it, x, y, color } = sel;
  const Icon = ICON[it.verdict as keyof typeof ICON] ?? ShieldCheck;
  const left = (x / size) * 100;
  const top = (y / size) * 100;
  const flipX = left > 55;
  const flipY = top > 62;
  return (
    <div
      role="tooltip"
      className="pointer-events-auto absolute z-20 w-64 rounded-2xl border border-line-2 bg-[#0b1512]/95 p-3.5 text-start shadow-[0_20px_50px_-20px_rgba(0,0,0,0.9),0_0_0_1px_rgba(46,229,157,0.12)] backdrop-blur-md"
      style={{
        left: `${left}%`,
        top: `${top}%`,
        transform: `translate(${flipX ? "calc(-100% - 18px)" : "18px"}, ${flipY ? "calc(-100% + 10px)" : "-10px"})`,
        direction: lang === "ar" ? "rtl" : "ltr",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-extrabold" style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}>
          <Icon aria-hidden className="size-3.5" strokeWidth={2.5} />
          {t(it.verdict)}
        </span>
        <span className="ltr text-2xl font-extrabold tabular-nums" style={{ color, textShadow: `0 0 16px ${color}80` }}>
          {it.score}
        </span>
      </div>
      <p className="ltr mt-2 break-all text-[15px] font-extrabold text-ink">{it.domain}</p>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-muted">{L(["Imitates", "يقلّد"], lang)}</dt>
        <dd className="truncate font-bold text-ink-2">{brand ?? L(["No brand named", "بدون علامة"], lang)}</dd>
        <dt className="text-muted">{L(["Sector", "القطاع"], lang)}</dt>
        <dd className="truncate font-bold text-ink-2">{L(CATEGORIES[category] ?? CATEGORIES.none, lang)}</dd>
        <dt className="text-muted">{L(["Found by", "رُصد عبر"], lang)}</dt>
        <dd className="truncate font-bold text-ink-2">{t(`src_${it.source}` as Parameters<typeof t>[0])}</dd>
        <dt className="text-muted">{L(["When", "متى"], lang)}</dt>
        <dd className="font-bold text-ink-2">{fmtAgo(it.discovered_at, lang)}</dd>
      </dl>
      <button
        type="button"
        onClick={onOpen}
        className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-primary px-3 py-2 text-xs font-extrabold text-primary-ink hover:brightness-110"
      >
        {L(["Open case", "افتح الحالة"], lang)}
        <ArrowUpRight aria-hidden className="size-3.5 rtl:-scale-x-100" />
      </button>
    </div>
  );
}
