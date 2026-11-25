"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Info, Phone, Play, Search, X } from "lucide-react";
import { ApiError, useBrands, useRadarFeed } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { CATEGORIES, L, SOURCE_NAMES, startRadar, TABS, useRadarStatus, variantLabel, type Pair, type RadarItem, type RadarRun } from "@/lib/radar";
import { cn, fmtAgo, fmtTime } from "@/lib/utils";
import { useSession } from "@/components/shell/AppShell";
import { shortBrand, StatusTag, VerdictChip } from "@/components/ui/verdict";
import { Button, ErrorState, Input, Select, Skeleton } from "@/components/ui/primitives";
import { RadarScope } from "@/components/radar/RadarScope";

/* Radar v2 — docs/radar-ui.md. Tabs = how a site was found, chips = who it imitates.
   All filters live in the URL so a view can be shared or reloaded. */

const T = {
  title: ["Radar", "الرادار"],
  sub: ["Sites the radar found on its own, before anyone reported them.", "مواقع رصدها الرادار بنفسه قبل أن يبلغ عنها أحد."],
  run: ["Run radar now", "شغّل الرادار الآن"],
  allSources: ["All sources", "كل المصادر"],
  needsKey: ["needs key", "يحتاج مفتاح"],
  signInToRun: ["Sign in to run the radar", "سجّل الدخول لتشغيل الرادار"],
  lastRun: ["Last run", "آخر تشغيل"],
  nextRun: ["next automatic run", "التشغيل التلقائي القادم"],
  newSites: ["new sites", "مواقع جديدة"],
  never: ["The radar has not run yet", "لم يعمل الرادار بعد"],
  verdictAll: ["All", "الكل"],
  brandAll: ["All brands", "كل العلامات"],
  search: ["Search domain", "ابحث عن نطاق"],
  clear: ["Clear filters", "إزالة الفلاتر"],
  none: ["Nothing matches these filters.", "لا شيء يطابق هذه الفلاتر."],
  scopeTitle: ["Radar scope", "شاشة الرادار"],
  manual: ["Started by", "بدأه"],
  automatic: ["Automatic run", "تشغيل تلقائي"],
  checkingPages: ["Checking pages", "فحص الصفحات"],
  foundSoFar: ["Found so far", "رُصد حتى الآن"],
  fraud: ["fraud", "احتيال"],
  suspicious: ["suspicious", "مشبوه"],
  done: ["done", "اكتمل"],
  skipped: ["skipped", "تم تخطيه"],
  waiting: ["waiting", "بالانتظار"],
  failed: ["failed", "فشل"],
  finished: ["Run finished in {m} min: {n} new sites, {f} fraud, {s} suspicious.", "اكتمل التشغيل في {m} دقيقة: {n} موقعًا جديدًا، {f} احتيال، {s} مشبوه."],
  showFraud: ["Show the fraud", "اعرض الاحتيال"],
  preview: ["Preview with sample data. The live run connects when the radar backend is ready.", "معاينة ببيانات نموذجية. يتصل التشغيل المباشر عند جاهزية خادم الرادار."],
  previewBtn: ["Preview the scope", "معاينة الشاشة"],
  hide: ["Hide", "إخفاء"],
  notReady: ["The run button connects when the radar backend endpoint is ready.", "يتصل زر التشغيل عند جاهزية خادم الرادار."],
  alreadyRunning: ["A run is already going. Showing it.", "هناك تشغيل جارٍ بالفعل، يتم عرضه."],
  ad: ["Ad", "إعلان"],
  fakeHelpline: ["Fake helpline", "رقم خدمة مزيف"],
  saved: ["saved result", "نتيجة محفوظة"],
  issued: ["Issued", "صدرت"],
  registered: ["Registered", "سُجّل"],
  position: ["position", "الترتيب"],
  announce: ["{n} new sites found, {f} look like fraud.", "رُصد {n} موقعًا جديدًا، {f} منها تبدو احتيالية."],
} as const satisfies Record<string, Pair>;

export default function RadarPage() {
  return (
    <Suspense>
      <RadarInner />
    </Suspense>
  );
}

function RadarInner() {
  const { lang, pick } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  const router = useRouter();
  const sp = useSearchParams();
  const user = useSession();
  const { data: brands } = useBrands();
  const { data: statusData, mutate: mutateStatus } = useRadarStatus();
  const running = Boolean(statusData && !statusData.preview && statusData.status.running);
  const feed = useRadarFeed(500);
  // While a real run is going, refresh the feed every 2 s so new rows appear at the top.
  useEffect(() => {
    if (!running) return;
    const h = setInterval(() => feed.mutate(), 2000);
    return () => clearInterval(h);
  }, [running, feed]);

  const tab = sp.get("tab") ?? "all";
  const category = sp.get("category") ?? "";
  const verdict = sp.get("verdict") ?? "";
  const brand = sp.get("brand") ?? "";
  const q = sp.get("q") ?? "";
  const [qDraft, setQDraft] = useState(q);
  // The scope is the page's centrepiece: shown by default (last run when idle), hideable.
  const [scopeOpen, setScopeOpen] = useState(true);
  const [runMsg, setRunMsg] = useState<string | null>(null);

  const setParams = useCallback(
    (patch: Record<string, string>) => {
      const n = new URLSearchParams(sp.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v && !(k === "tab" && v === "all")) n.set(k, v);
        else n.delete(k);
      }
      router.replace(`/radar${n.toString() ? `?${n}` : ""}`, { scroll: false });
    },
    [sp, router],
  );
  useEffect(() => {
    const h = setTimeout(() => qDraft !== q && setParams({ q: qDraft }), 300);
    return () => clearTimeout(h);
  }, [qDraft, q, setParams]);

  const brandCat = useMemo(() => new Map((brands ?? []).map((b) => [b.id, b.category as string])), [brands]);
  const brandName = useCallback(
    (id: string | null) => {
      if (!id) return null;
      const b = brands?.find((x) => x.id === id);
      return b ? shortBrand(pick(b as unknown as Record<string, unknown>, "name")) : id;
    },
    [brands, pick],
  );
  const catOf = useCallback((it: RadarItem) => it.brand_category ?? (it.brand_target ? brandCat.get(it.brand_target) ?? "none" : "none"), [brandCat]);

  const all = useMemo(() => (feed.data?.items ?? []) as RadarItem[], [feed.data]);
  const feedExtra = feed.data as (typeof feed.data & { counts_by_category?: Record<string, number> }) | undefined;

  // Counts ignore the active filters so the numbers don't jump while filtering.
  const tabCounts = useMemo(() => {
    const c = feed.data?.counts_by_source ?? {};
    return Object.fromEntries(TABS.map((t) => [t.id, t.id === "all" ? all.length : t.sources.reduce((n, s) => n + (c[s] ?? 0), 0)]));
  }, [feed.data, all.length]);
  const catCounts = useMemo(() => {
    if (feedExtra?.counts_by_category) return feedExtra.counts_by_category;
    const m: Record<string, number> = {};
    for (const it of all) m[catOf(it)] = (m[catOf(it)] ?? 0) + 1;
    return m;
  }, [feedExtra, all, catOf]);

  const tabDef = TABS.find((t) => t.id === tab) ?? TABS[0];
  const rows = useMemo(
    () =>
      all.filter(
        (it) =>
          (tabDef.sources.length === 0 || tabDef.sources.includes(it.source)) &&
          (!category || catOf(it) === category) &&
          (!verdict || it.verdict === verdict) &&
          (!brand || it.brand_target === brand) &&
          (!q || it.domain.toLowerCase().includes(q.toLowerCase())),
      ),
    [all, tabDef, category, verdict, brand, q, catOf],
  );
  const anyFilter = Boolean(category || verdict || brand || q || tab !== "all");

  async function run(sources?: string[]) {
    setRunMsg(null);
    try {
      await startRadar(sources);
      setScopeOpen(true);
      mutateStatus();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setRunMsg(tr("alreadyRunning"));
        setScopeOpen(true);
        mutateStatus();
      } else if (e instanceof ApiError && (e.status === 404 || e.status === 405)) {
        setRunMsg(tr("notReady"));
        setScopeOpen(true);
      } else setRunMsg(e instanceof Error ? e.message : String(e));
    }
  }

  const status = statusData?.status;
  const showScope = running || scopeOpen;

  if (feed.error) return <ErrorState error={feed.error} onRetry={() => feed.mutate()} />;

  return (
    <div className="mx-auto max-w-6xl">
      {/* Header + run button + status line */}
      <div className="flex flex-wrap items-start justify-between gap-3 pt-2">
        <div className="min-w-0">
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">{tr("title")}</h1>
          <p className="mt-1 text-muted">{tr("sub")}</p>
          <StatusLine status={status} preview={statusData?.preview ?? false} />
        </div>
        <RunButton disabled={!user} onRun={run} sourcesInfo={status?.sources} />
      </div>
      {runMsg && (
        <p role="status" className="mt-3 flex items-start gap-2 rounded-xl bg-primary-soft px-3 py-2 text-sm text-primary">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
          {runMsg}
        </p>
      )}

      {/* Radar scope */}
      {showScope && status?.run ? (
        <Scope run={status.run} preview={statusData?.preview ?? false} items={all} categoryOf={catOf} brandName={brandName} onClose={() => setScopeOpen(false)} onShowFraud={() => setParams({ tab: "all", verdict: "FRAUD" })} />
      ) : (
        <button type="button" onClick={() => setScopeOpen(true)} className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline">
          <span aria-hidden className="radar-dot inline-block size-2 rounded-full bg-accent" />
          {tr("previewBtn")}
        </button>
      )}

      {/* Tabs: how it was found */}
      <div role="tablist" aria-label={tr("title")} className="mt-5 flex gap-2 overflow-x-auto thin-scroll pb-1">
        {TABS.map((t) => {
          const n = tabCounts[t.id] ?? 0;
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={on}
              onClick={() => setParams({ tab: t.id })}
              className={cn(
                "inline-flex h-10 shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-bold transition-colors",
                on ? "border-primary bg-primary text-primary-ink" : "border-line-2 bg-surface text-ink-2 hover:bg-surface-2",
                !on && n === 0 && "opacity-45",
              )}
            >
              {L(t.label, lang)}
              <span className={cn("ltr rounded-full px-1.5 text-xs tabular-nums", on ? "bg-white/20" : "bg-surface-2 text-muted")}>{n}</span>
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-muted">{L(tabDef.explain, lang)}</p>

      {/* Chips: who it imitates */}
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(CATEGORIES)
          .filter(([k]) => (catCounts[k] ?? 0) > 0)
          .sort((a, b) => (a[0] === "none" ? 1 : b[0] === "none" ? -1 : (catCounts[b[0]] ?? 0) - (catCounts[a[0]] ?? 0)))
          .map(([k, label]) => {
            const on = category === k;
            return (
              <button
                key={k}
                type="button"
                aria-pressed={on}
                onClick={() => setParams({ category: on ? "" : k })}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-sm font-bold transition-colors",
                  on ? "bg-accent-soft text-accent-text ring-2 ring-accent/60" : "bg-surface-2 text-ink-2 hover:bg-primary-soft",
                )}
              >
                {L(label, lang)}
                <span className="ltr text-xs tabular-nums opacity-70">{catCounts[k]}</span>
              </button>
            );
          })}
      </div>

      {/* Verdict, brand, search */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Verdict" className="inline-flex rounded-full bg-surface-2 p-1">
          {(["", "FRAUD", "SUSPICIOUS", "LEGIT"] as const).map((v) => (
            <button
              key={v || "all"}
              type="button"
              aria-pressed={verdict === v}
              onClick={() => setParams({ verdict: v })}
              className={cn("h-8 rounded-full px-3 text-sm font-bold", verdict === v ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}
            >
              {v === "" ? tr("verdictAll") : <VerdictWord v={v} />}
            </button>
          ))}
        </div>
        <Select aria-label={tr("brandAll")} value={brand} onChange={(e) => setParams({ brand: e.target.value })} className="w-full min-w-0 sm:w-auto sm:max-w-[16rem]">
          <option value="">{tr("brandAll")}</option>
          {(brands ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {shortBrand(pick(b as unknown as Record<string, unknown>, "name"))}
            </option>
          ))}
        </Select>
        <div className="relative min-w-[12rem] flex-1">
          <Search aria-hidden className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input aria-label={tr("search")} placeholder={tr("search")} value={qDraft} onChange={(e) => setQDraft(e.target.value)} className="ltr h-10 ps-9" />
        </div>
        {anyFilter && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setQDraft("");
              router.replace("/radar", { scroll: false });
            }}
          >
            <X aria-hidden className="size-4" /> {tr("clear")}
          </Button>
        )}
      </div>

      {/* List */}
      {feed.isLoading && !feed.data ? (
        <div className="mt-4 flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[72px] rounded-[16px]" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-4 rounded-[16px] border border-dashed border-line-2 p-10 text-center text-muted">{tr("none")}</p>
      ) : (
        <ol className="mt-4 overflow-hidden rounded-[16px] border border-line bg-surface">
          {rows.map((it, i) => (
            <RadarRow key={it.id} it={it} first={i === 0} brand={brandName(it.brand_target)} category={catOf(it)} />
          ))}
        </ol>
      )}
    </div>
  );
}

function VerdictWord({ v }: { v: "FRAUD" | "SUSPICIOUS" | "LEGIT" }) {
  const { t } = useLang();
  return <>{t(v)}</>;
}

function StatusLine({ status, preview }: { status?: { run: RadarRun | null; schedule?: { next_run_at: string } }; preview: boolean }) {
  const { lang } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  if (!status || preview) return null;
  const r = status.run;
  const newCount = r?.sources.reduce((n, s) => n + (s.new ?? 0), 0) ?? 0;
  return (
    <p className="mt-2 text-sm text-ink-2">
      {r ? (
        <>
          {tr("lastRun")} <span className="font-bold">{fmtTime(r.finished_at ?? r.started_at, lang)}</span> ·{" "}
          <span className="ltr font-bold tabular-nums">{newCount}</span> {tr("newSites")}
        </>
      ) : (
        tr("never")
      )}
      {status.schedule && (
        <>
          {" "}
          · {tr("nextRun")} <span className="font-bold">{fmtTime(status.schedule.next_run_at, lang)}</span>
        </>
      )}
    </p>
  );
}

function RunButton({ disabled, onRun, sourcesInfo }: { disabled: boolean; onRun: (s?: string[]) => void; sourcesInfo?: { name: string; enabled: boolean; needs_key: string | null }[] }) {
  const { lang } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);
  const names = ["lookalikes", "ct", "nrd", "search", "maps"];
  // "needs key" only when the server says the key is missing (enabled: false), not merely because the source uses one.
  const missingKey = (n: string) => sourcesInfo?.find((s) => s.name === n)?.enabled === false;
  return (
    <div ref={ref} className="relative" title={disabled ? tr("signInToRun") : undefined}>
      <div className="inline-flex overflow-hidden rounded-full shadow-[0_6px_20px_-8px_var(--glow)]">
        <Button disabled={disabled} onClick={() => onRun()} className="rounded-none rounded-s-full">
          <Play aria-hidden className="size-4" />
          {tr("run")}
        </Button>
        <Button disabled={disabled} aria-label={tr("allSources")} aria-expanded={open} onClick={() => setOpen((o) => !o)} className="rounded-none rounded-e-full border-s border-white/25 px-3">
          <ChevronDown aria-hidden className="size-4" />
        </Button>
      </div>
      {open && (
        <ul role="menu" className="absolute end-0 z-20 mt-2 w-60 rounded-xl border border-line bg-surface p-1 shadow-xl">
          <li>
            <button role="menuitem" type="button" onClick={() => (setOpen(false), onRun())} className="w-full rounded-lg px-3 py-2 text-start text-sm font-bold hover:bg-surface-2">
              {tr("allSources")}
            </button>
          </li>
          {names.map((n) => {
            const key = missingKey(n);
            return (
              <li key={n}>
                <button
                  role="menuitem"
                  type="button"
                  disabled={key}
                  onClick={() => (setOpen(false), onRun([n]))}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-start text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {L(SOURCE_NAMES[n], lang)}
                  {key && <span className="text-xs text-muted">({tr("needsKey")})</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ---- the radar scope: the demo moment ---- */


function Scope({ run, preview, items, categoryOf, brandName, onClose, onShowFraud }: { run: RadarRun; preview: boolean; items: RadarItem[]; categoryOf: (it: RadarItem) => string; brandName: (id: string | null) => string | null; onClose: () => void; onShowFraud: () => void }) {
  const { lang } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  const live = run.status === "running";
  const found = run.sources.reduce((n, s) => n + (s.new ?? 0), 0);
  const minutes = run.finished_at ? Math.max(1, Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 60000)) : 0;

  // Polite announcement at most every 10 s.
  const [announce, setAnnounce] = useState("");
  const last = useRef(0);
  useEffect(() => {
    const now = Date.now();
    if (now - last.current < 10000) return;
    last.current = now;
    setAnnounce(L(T.announce, lang).replace("{n}", String(found)).replace("{f}", String(run.verdicts.FRAUD ?? 0)));
  }, [found, run.verdicts.FRAUD, lang]);

  return (
    <section aria-label={tr("scopeTitle")} className="relative mt-4 overflow-hidden rounded-[20px] ops-glow border border-line bg-[#050a08] p-4 text-white sm:p-6">
      <p className="sr-only" aria-live="polite">
        {announce}
      </p>
      <div className="flex items-center justify-between gap-2">
        <p className="inline-flex items-center gap-2 text-sm font-bold text-white/80">
          <span aria-hidden className={cn("inline-block size-2 rounded-full bg-accent", live && "radar-dot")} />
          {tr("scopeTitle")} ·{" "}
          {run.trigger === "schedule" ? tr("automatic") : (
            <>
              {tr("manual")} {run.started_by ?? "—"}
            </>
          )}
        </p>
        <button type="button" onClick={onClose} aria-label={tr("hide")} className="grid size-8 place-items-center rounded-full text-white/70 hover:bg-white/10">
          <X aria-hidden className="size-4" />
        </button>
      </div>
      {preview && (
        <p className="mt-2 inline-flex items-start gap-2 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white/85">
          <Info aria-hidden className="mt-0.5 size-3.5 shrink-0" />
          {tr("preview")}
        </p>
      )}

      <div className="mt-4 grid items-center gap-6 lg:grid-cols-[420px_1fr]">
        {/* Scope: hover a dot for the site, click to open the case */}
        <RadarScope items={items} categoryOf={categoryOf} brandName={brandName} live={live} className="max-w-[420px]" />

        {/* Progress */}
        <div className="min-w-0">
          <ul className="flex flex-col gap-2.5">
            {run.sources.map((s) => {
              const ratio = s.total ? Math.min(1, (s.checked ?? 0) / s.total) : null;
              return (
                <li key={s.name} className="grid grid-cols-[minmax(7.5rem,34%)_1fr] items-center gap-3 text-sm">
                  <span className="truncate font-bold text-white/90">{L(SOURCE_NAMES[s.name] ?? [s.name, s.name], lang)}</span>
                  {s.status === "skipped" ? (
                    <span className="text-white/50">
                      {tr("skipped")}
                      {s.note === "needs_key" && <> · {tr("needsKey")}</>}
                    </span>
                  ) : (
                    <span className="flex items-center gap-3">
                      <span className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                        <span
                          className={cn("block h-full rounded-full", s.status === "failed" ? "bg-[#ff6b6b]" : s.status === "done" ? "bg-primary" : "bg-accent", ratio === null && s.status === "running" && "animate-pulse")}
                          style={{ width: `${ratio === null ? (s.status === "running" ? 40 : 100) : ratio * 100}%` }}
                        />
                      </span>
                      <span className="ltr w-36 shrink-0 text-end text-xs tabular-nums text-white/70">
                        {s.status === "done" ? (
                          <>
                            {tr("done")} · {s.new ?? 0}
                          </>
                        ) : s.status === "waiting" ? (
                          tr("waiting")
                        ) : s.status === "failed" ? (
                          tr("failed")
                        ) : s.total ? (
                          `${(s.checked ?? 0).toLocaleString()} / ${s.total.toLocaleString()}`
                        ) : (
                          "…"
                        )}
                      </span>
                    </span>
                  )}
                </li>
              );
            })}
            <li className="grid grid-cols-[minmax(7.5rem,34%)_1fr] items-center gap-3 border-t border-white/10 pt-2.5 text-sm">
              <span className="font-bold text-white/90">{tr("checkingPages")}</span>
              <span className="flex items-center gap-3">
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                  <span className="block h-full rounded-full bg-accent" style={{ width: `${run.pages.total ? (run.pages.checked / run.pages.total) * 100 : 0}%` }} />
                </span>
                <span className="ltr w-36 shrink-0 text-end text-xs tabular-nums text-white/70">
                  {run.pages.checked} / {run.pages.total}
                </span>
              </span>
            </li>
          </ul>
          <p className="mt-4 text-base font-bold">
            {tr("foundSoFar")}: <span className="ltr tabular-nums">{found}</span> · <span className="text-[#ff8a8a]">
              <span className="ltr tabular-nums">{run.verdicts.FRAUD ?? 0}</span> {tr("fraud")}
            </span>{" "}
            · <span className="text-[#f5b93f]">
              <span className="ltr tabular-nums">{run.verdicts.SUSPICIOUS ?? 0}</span> {tr("suspicious")}
            </span>
          </p>
          {run.status === "done" && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <p className="text-sm text-white/80">
                {L(T.finished, lang)
                  .replace("{m}", String(minutes))
                  .replace("{n}", String(found))
                  .replace("{f}", String(run.verdicts.FRAUD ?? 0))
                  .replace("{s}", String(run.verdicts.SUSPICIOUS ?? 0))}
              </p>
              <Button variant="danger" size="sm" onClick={onShowFraud}>
                {tr("showFraud")}
              </Button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

/* ---- one row ---- */

function RadarRow({ it, first, brand, category }: { it: RadarItem; first: boolean; brand: string | null; category: string }) {
  const { lang } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  const d = it.source_details ?? {};
  const replayed = d.replayed === true;

  let extra: React.ReactNode = null;
  if (it.source === "lookalike") {
    const v = variantLabel(d.variant);
    if (v) extra = <Tag>{L(v, lang)}</Tag>;
  } else if (it.source === "ct" && typeof d.issued_at === "string") {
    extra = (
      <span className="text-xs text-muted">
        {tr("issued")} {fmtAgo(d.issued_at, lang)}
      </span>
    );
  } else if (it.source === "nrd" && typeof d.registered_on === "string") {
    extra = (
      <span className="text-xs text-muted">
        {tr("registered")} <span className="ltr">{d.registered_on}</span>
      </span>
    );
  } else if (it.source === "search" || it.source === "search_ad") {
    const query = (typeof d.query === "string" && d.query) || it.query;
    extra = (
      <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
        {it.source === "search_ad" && <span className="rounded-full bg-accent-soft px-2 py-0.5 font-bold text-accent-text">{tr("ad")}</span>}
        {query && <q className="truncate">{query}</q>}
        {typeof d.position === "number" && (
          <span className="ltr">
            #{d.position} {tr("position")}
          </span>
        )}
      </span>
    );
  } else if (it.source === "maps") {
    extra = (
      <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
        {typeof d.listing_name === "string" && <span className="truncate">{d.listing_name}</span>}
        {typeof d.phone === "string" && (
          <span className="ltr inline-flex items-center gap-1">
            <Phone aria-hidden className="size-3" />
            {d.phone}
          </span>
        )}
        {d.helpline_mismatch === true && <span className="rounded-full bg-fraud-soft px-2 py-0.5 font-bold text-fraud">{tr("fakeHelpline")}</span>}
      </span>
    );
  }

  return (
    <li className={cn(!first && "border-t border-line")}>
      <Link href={`/cases/${it.id}`} className="group grid grid-cols-[auto_1fr_auto] items-center gap-x-4 gap-y-1 px-4 py-3.5 transition-colors hover:bg-surface-2 sm:grid-cols-[8.5rem_1fr_auto_auto] sm:px-5">
        <span className="flex flex-col items-start gap-1">
          <VerdictChip verdict={it.verdict} size="sm" />
          <span className="ltr ps-1 text-[11px] font-bold tabular-nums text-muted">{it.score}</span>
        </span>
        <span className="min-w-0">
          <span className="ltr block truncate text-[15px] font-extrabold text-ink">{it.domain}</span>
          <span className="mt-1 flex flex-wrap items-center gap-1.5">
            {brand ? (
              <span
                title={`${brand} · ${L(CATEGORIES[category] ?? CATEGORIES.none, lang)}`}
                className="max-w-full truncate rounded-full bg-accent-soft px-2 py-0.5 text-xs font-bold text-accent-text sm:max-w-[22rem]"
              >
                {brand} · {L(CATEGORIES[category] ?? CATEGORIES.none, lang)}
              </span>
            ) : (
              <span className="text-xs text-muted">{L(CATEGORIES.none, lang)}</span>
            )}
            {extra}
            {replayed && <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-bold text-muted">{tr("saved")}</span>}
          </span>
        </span>
        <span className="hidden flex-col items-end gap-1 sm:flex">
          <span className="text-sm font-bold text-ink tabular-nums">{fmtAgo(it.discovered_at, lang)}</span>
          <StatusTag status={it.status} />
        </span>
        <ChevronRight aria-hidden className="size-5 text-muted transition-transform group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5" />
      </Link>
    </li>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-primary-soft px-2 py-0.5 text-xs font-bold text-primary">{children}</span>;
}
