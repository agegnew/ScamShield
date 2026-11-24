"use client";

import { Ban, CircleHelp, ShieldCheck, TriangleAlert } from "lucide-react";
import { useLang } from "@/lib/i18n";
import type { VerdictLabel } from "@/lib/api";
import { cn } from "@/lib/utils";

/* Verdict is the hero of every screen. Always icon + word + colour, never colour alone. */

export const verdictTone: Record<VerdictLabel, { fg: string; bg: string; line: string; Icon: typeof Ban }> = {
  FRAUD: { fg: "text-fraud", bg: "bg-fraud-soft", line: "border-fraud-line", Icon: Ban },
  SUSPICIOUS: { fg: "text-review", bg: "bg-review-soft", line: "border-review-line", Icon: TriangleAlert },
  LEGIT: { fg: "text-safe", bg: "bg-safe-soft", line: "border-safe-line", Icon: ShieldCheck },
  UNKNOWN: { fg: "text-unknown", bg: "bg-unknown-soft", line: "border-unknown-line", Icon: CircleHelp },
};

export const verdictHex: Record<VerdictLabel, string> = {
  FRAUD: "var(--fraud)",
  SUSPICIOUS: "var(--review)",
  LEGIT: "var(--safe)",
  UNKNOWN: "var(--unknown)",
};

export function VerdictChip({
  verdict,
  size = "md",
  className,
}: {
  verdict: VerdictLabel;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const { t } = useLang();
  const tone = verdictTone[verdict] ?? verdictTone.UNKNOWN;
  const Icon = tone.Icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-bold leading-none whitespace-nowrap",
        tone.fg,
        tone.bg,
        tone.line,
        size === "sm" && "px-2 py-1 text-xs",
        size === "md" && "px-2.5 py-1.5 text-sm",
        size === "lg" && "px-4 py-2.5 text-lg",
        className,
      )}
    >
      <Icon aria-hidden className={cn(size === "sm" ? "size-3.5" : size === "md" ? "size-4" : "size-5")} strokeWidth={2.5} />
      {t(verdict)}
    </span>
  );
}

/** Score 0–100 as a ring. The number is the content; the ring is just emphasis. */
export function ScoreRing({ score, verdict, size = 72, className }: { score: number | null | undefined; verdict: VerdictLabel; size?: number; className?: string }) {
  const { t } = useLang();
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const s = Math.max(0, Math.min(100, score ?? 0));
  const offset = circ * (1 - s / 100);
  const color = verdictHex[verdict] ?? verdictHex.UNKNOWN;
  return (
    <div
      className={cn("relative inline-grid place-items-center shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${t("riskScore")}: ${score ?? "—"} ${t("outOf100")}`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={6} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          className="ring-fill"
          style={{ ["--ring-circ" as string]: circ }}
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center font-extrabold tabular-nums ltr" style={{ fontSize: size * 0.32, color }}>
        {score ?? "—"}
      </span>
    </div>
  );
}

export function SourceTag({ source, className }: { source: string; className?: string }) {
  const { t } = useLang();
  const key = `src_${source}` as Parameters<typeof t>[0];
  const label = (() => {
    try {
      return t(key);
    } catch {
      return source;
    }
  })();
  const radar = ["lookalike", "ct", "nrd", "search", "search_ad", "maps"].includes(source);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap",
        radar ? "bg-primary-soft text-primary" : "bg-surface-2 text-ink-2",
        className,
      )}
    >
      {radar && <span aria-hidden className="size-1.5 rounded-full bg-accent" />}
      {label}
    </span>
  );
}

export function StatusTag({ status, className }: { status: "new" | "confirmed" | "dismissed"; className?: string }) {
  const { t } = useLang();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-bold whitespace-nowrap",
        status === "new" && "border-line-2 bg-surface text-ink-2",
        status === "confirmed" && "border-fraud-line bg-fraud-soft text-fraud",
        status === "dismissed" && "border-line bg-surface-2 text-muted line-through decoration-1",
        className,
      )}
    >
      {t(`st_${status}` as Parameters<typeof t>[0])}
    </span>
  );
}

export function BrandChip({ brandId, name, className }: { brandId: string | null | undefined; name?: string | null; className?: string }) {
  const { t } = useLang();
  if (!brandId) return <span className={cn("text-sm text-muted", className)}>{t("noBrand")}</span>;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-bold text-accent-text whitespace-nowrap", className)}>
      {name ?? brandId}
    </span>
  );
}
