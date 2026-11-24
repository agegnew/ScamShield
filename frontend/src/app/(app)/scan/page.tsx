"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Download } from "lucide-react";
import { batchUrls, scanUrl, type BatchResponse } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { VerdictChip } from "@/components/ui/verdict";
import { Button, Input, Panel, PanelTitle, Textarea } from "@/components/ui/primitives";

export default function ScanPage() {
  const { t, pick } = useLang();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [batch, setBatch] = useState("");
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchRes, setBatchRes] = useState<BatchResponse | null>(null);

  async function scan(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await scanUrl(url.trim());
      router.push(`/cases/${r.case_id}`);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
      setBusy(false);
    }
  }

  async function runBatch(e: React.FormEvent) {
    e.preventDefault();
    const urls = batch
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!urls.length) return;
    setBatchBusy(true);
    try {
      setBatchRes(await batchUrls(urls));
    } finally {
      setBatchBusy(false);
    }
  }

  function csv() {
    if (!batchRes) return;
    const items = batchRes.items as unknown as Array<Record<string, unknown>>;
    const rows = [["url", "verdict", "score", "brand_target", "reasons"], ...items.map((i) => [String(i.url ?? ""), String(i.verdict ?? ""), String(i.score ?? ""), String(i.brand_target ?? ""), ((i.reasons as Array<Record<string, string>>) ?? []).map((r) => r.text_en).join(" | ")])];
    const text = rows.map((r) => r.map((c) => `"${String(c).replaceAll('"', '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = "scamshield-batch.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 pt-2">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{t("scanTitle")}</h1>
        <p className="mt-1 text-muted">{t("scanHint")}</p>
      </div>

      <form onSubmit={scan} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="url" className="sr-only">
          URL
        </label>
        <Input id="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" inputMode="url" required className="ltr h-12 flex-1 text-base" />
        <Button type="submit" size="lg" className="h-12" loading={busy}>
          {busy ? t("scanning") : t("scanButton")}
        </Button>
      </form>
      {err && (
        <p role="alert" className="mt-3 rounded-xl bg-fraud-soft px-3 py-2 text-sm font-semibold text-fraud">
          {err}
        </p>
      )}

      <Panel className="mt-8 p-5">
        <PanelTitle hint={t("batchHint")}>{t("batchTitle")}</PanelTitle>
        <form onSubmit={runBatch} className="mt-3">
          <Textarea value={batch} onChange={(e) => setBatch(e.target.value)} rows={6} className="ltr font-sans text-sm" placeholder={"https://example.test/login\nhttps://another.test/pay"} />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="submit" variant="secondary" loading={batchBusy}>
              {t("batchButton")}
            </Button>
            {batchRes && (
              <Button type="button" variant="outline" onClick={csv}>
                <Download aria-hidden className="size-4" /> {t("downloadCsv")}
              </Button>
            )}
          </div>
        </form>

        {batchRes && (
          <ul className="mt-4 divide-y divide-line">
            {(batchRes.items as unknown as Array<Record<string, unknown>>).map((i, k) => (
              <li key={k} className="flex items-center gap-3 py-2.5">
                <VerdictChip verdict={(i.verdict as "FRAUD" | "SUSPICIOUS" | "LEGIT") ?? "UNKNOWN"} size="sm" />
                <span className="ltr text-xs font-bold text-muted tabular-nums">{String(i.score ?? "")}</span>
                <span className="ltr min-w-0 flex-1 truncate text-sm text-ink">{String(i.url)}</span>
                {Array.isArray(i.reasons) && i.reasons[0] && <span className="hidden max-w-[40%] truncate text-xs text-muted sm:block">{pick(i.reasons[0] as Record<string, unknown>, "text")}</span>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
