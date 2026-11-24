"use client";

import { useMetrics } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtTime, pct } from "@/lib/utils";
import { ErrorState, KeyValue, Panel, PanelTitle, Skeleton } from "@/components/ui/primitives";

export default function AccuracyPage() {
  const { t, lang } = useLang();
  const { data: m, error, isLoading, mutate } = useMetrics();

  if (error) return <ErrorState error={error} onRetry={() => mutate()} />;

  const uae = m?.by_source?.uae_official;
  const total = m ? m.n_fraud + m.n_legit : 0;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("accuracyTitle")}</h1>
        <p className="mt-1 max-w-2xl text-muted">{t("accuracySub")}</p>
      </div>

      {isLoading || !m ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-[16px]" />
          ))}
        </div>
      ) : (
        <>
          {/* The four numbers, each explained in one plain sentence */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label={t("precision")} value={pct(m.precision)} hint={t("precisionHint")} tone="good" />
            <Stat label={t("recall")} value={pct(m.recall)} hint={t("recallHint")} tone="good" />
            <Stat label={t("fpr")} value={pct(m.fpr)} hint={t("fprHint")} tone="low" />
            <Stat label={t("f1")} value={m.f1.toFixed(3)} hint={t("f1Hint")} tone="good" />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            {/* Confusion matrix drawn as four tiles whose size shows the proportion */}
            <Panel className="p-5">
              <PanelTitle hint={`${total.toLocaleString(lang === "ar" ? "ar-AE" : "en")} URLs`}>{t("confusion")}</PanelTitle>
              <div className="mt-4 grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
                <div />
                <p className="text-center text-xs font-bold text-muted">{t("calledFraud")}</p>
                <p className="text-center text-xs font-bold text-muted">{t("calledLegit")}</p>

                <p className="self-center text-xs font-bold text-muted [writing-mode:vertical-rl] rotate-180 rtl:rotate-0">{t("actualFraud")}</p>
                <Cell n={m.tp} total={total} label={t("caught")} tone="safe" />
                <Cell n={m.fn} total={total} label={t("missed")} tone="review" />

                <p className="self-center text-xs font-bold text-muted [writing-mode:vertical-rl] rotate-180 rtl:rotate-0">{t("actualLegit")}</p>
                <Cell n={m.fp} total={total} label={t("falseAlarms")} tone="fraud" />
                <Cell n={m.tn} total={total} label={t("correctlyCleared")} tone="safe" />
              </div>
            </Panel>

            <div className="flex flex-col gap-4">
              {uae && (
                <Panel className="border-safe-line bg-safe-soft p-5">
                  <p className="text-sm font-bold text-safe">{t("uaeOfficial")}</p>
                  <p className="mt-1 text-4xl font-extrabold tracking-tight text-safe tabular-nums ltr">
                    {uae.total - uae.correct} <span className="text-lg font-bold text-safe/70">{t("of")} {uae.total}</span>
                  </p>
                </Panel>
              )}
              <Panel className="p-5">
                <PanelTitle>{t("bySourceAcc")}</PanelTitle>
                <ul className="mt-3 flex flex-col gap-2.5">
                  {Object.entries(m.by_source ?? {}).map(([k, v]) => {
                    const r = v.total ? v.correct / v.total : 0;
                    return (
                      <li key={k}>
                        <div className="flex items-baseline justify-between gap-2 text-sm">
                          <span className="ltr font-semibold text-ink">{k}</span>
                          <span className="ltr text-xs text-muted tabular-nums">
                            {v.correct.toLocaleString()} / {v.total.toLocaleString()} {t("correct")}
                          </span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-2">
                          <div className={cn("h-full rounded-full", r >= 0.9 ? "bg-safe" : r >= 0.7 ? "bg-review" : "bg-fraud")} style={{ width: pct(r) }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </Panel>
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel className="p-5">
              <dl className="divide-y divide-line">
                <KeyValue k={t("dataset")} v={m.dataset} />
                <KeyValue k={t("modelVersion")} v={m.model_version} mono />
                <KeyValue k={t("evaluatedAt")} v={fmtTime(m.evaluated_at, lang, { year: "numeric" })} />
              </dl>
            </Panel>
            <Panel className="border-review-line bg-review-soft p-5">
              <p className="text-sm font-extrabold text-review">{t("honestLimit")}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-2">{t("honestLimitText")}</p>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, hint, tone }: { label: string; value: string; hint: string; tone: "good" | "low" }) {
  return (
    <Panel className="p-5">
      <p className="text-sm font-bold text-ink-2">{label}</p>
      <p className={cn("mt-1 text-4xl font-extrabold tracking-tight tabular-nums ltr", tone === "good" ? "text-primary" : "text-ink")}>{value}</p>
      <p className="mt-2 text-xs leading-snug text-muted">{hint}</p>
    </Panel>
  );
}

function Cell({ n, total, label, tone }: { n: number; total: number; label: string; tone: "safe" | "review" | "fraud" }) {
  const share = total ? n / total : 0;
  return (
    <div
      className={cn(
        "flex min-h-24 flex-col justify-between rounded-xl border p-3",
        tone === "safe" && "border-safe-line bg-safe-soft text-safe",
        tone === "review" && "border-review-line bg-review-soft text-review",
        tone === "fraud" && "border-fraud-line bg-fraud-soft text-fraud",
      )}
      style={{ opacity: 0.55 + Math.min(0.45, share * 1.2) }}
    >
      <span className="ltr text-2xl font-extrabold tabular-nums">{n.toLocaleString()}</span>
      <span className="text-xs font-bold">{label}</span>
    </div>
  );
}
