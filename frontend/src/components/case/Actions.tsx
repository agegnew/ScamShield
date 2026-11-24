"use client";

import { useEffect, useRef, useState } from "react";
import { Check, FileDown, FileJson, Mail, Send, X } from "lucide-react";
import { decide, downloadFile, exportJsonUrl, reportPdfUrl, useTakedown, type Case } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, fmtTime } from "@/lib/utils";
import { Button, Kbd, Panel, PanelTitle, Textarea } from "@/components/ui/primitives";
import { CopyButton } from "./Evidence";

export function DecisionPanel({ c, onUpdated }: { c: Case; onUpdated: (c: Case) => void }) {
  const { t, lang } = useLang();
  const [pending, setPending] = useState<"confirm" | "dismiss" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (pending) reasonRef.current?.focus();
  }, [pending]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key.toLowerCase() === "c") setPending("confirm");
      if (e.key.toLowerCase() === "d") setPending("dismiss");
      if (e.key === "Escape") setPending(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function save() {
    if (!pending) return;
    setBusy(true);
    try {
      const updated = await decide(c.id, pending, reason.trim());
      onUpdated(updated);
      setToast(pending === "confirm" ? t("confirmedToast") : t("dismissedToast"));
      setPending(null);
      setReason("");
      setTimeout(() => setToast(null), 2500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel className="p-4">
      <PanelTitle hint={t("shortcuts")}>{t("decision")}</PanelTitle>

      {!pending ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant={c.status === "confirmed" ? "outline" : "danger"} onClick={() => setPending("confirm")} disabled={c.status === "confirmed"}>
            <Check aria-hidden className="size-4" />
            {t("confirm")} <Kbd>C</Kbd>
          </Button>
          <Button variant="outline" onClick={() => setPending("dismiss")} disabled={c.status === "dismissed"}>
            <X aria-hidden className="size-4" />
            {t("dismiss")} <Kbd>D</Kbd>
          </Button>
          {toast && (
            <span role="status" className="inline-flex items-center gap-1.5 self-center rounded-full bg-safe-soft px-3 py-1 text-sm font-bold text-safe">
              <Check aria-hidden className="size-4" /> {toast}
            </span>
          )}
        </div>
      ) : (
        <form
          className="mt-3"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <label htmlFor="reason" className="text-sm font-bold text-ink">
            {t("decisionReason")}
          </label>
          <Textarea id="reason" ref={reasonRef} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder={t("decisionReasonPh")} className="mt-1.5" required />
          <div className="mt-3 flex gap-2">
            <Button type="submit" variant={pending === "confirm" ? "danger" : "primary"} loading={busy}>
              {pending === "confirm" ? t("confirm") : t("dismiss")}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setPending(null)}>
              {t("cancel")}
            </Button>
          </div>
        </form>
      )}

      {c.decisions && c.decisions.length > 0 && (
        <div className="mt-4 border-t border-line pt-3">
          <p className="text-xs font-bold text-muted">{t("decisionLog")}</p>
          <ul className="mt-2 flex flex-col gap-2">
            {c.decisions.map((d, i) => {
              const dd = d as unknown as Record<string, unknown>;
              const action = String(dd.action ?? "");
              return (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className={cn("mt-0.5 rounded-full px-2 py-0.5 text-xs font-bold", action === "confirm" ? "bg-fraud-soft text-fraud" : "bg-surface-2 text-ink-2")}>{action === "confirm" ? t("st_confirmed") : t("st_dismissed")}</span>
                  <span className="min-w-0 text-ink-2">
                    <span className="font-bold text-ink">{String(dd.by ?? dd.user ?? dd.username ?? "")}</span>
                    {dd.reason ? <> · {String(dd.reason)}</> : null}
                    <span className="block text-xs text-muted">{fmtTime(String(dd.at ?? dd.decided_at ?? dd.created_at ?? ""), lang)}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Panel>
  );
}

export function ExportButtons({ c, onTakedown }: { c: Case; onTakedown: () => void }) {
  const { t } = useLang();
  const [pdfMsg, setPdfMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<"pdf" | "json" | null>(null);

  async function download(kind: "pdf" | "json") {
    setBusy(kind);
    try {
      if (kind === "pdf") await downloadFile(reportPdfUrl(c.id), `scamshield-${c.id}.pdf`);
      else await downloadFile(exportJsonUrl(c.id), `scamshield-${c.id}.json`);
    } catch {
      setPdfMsg(t("pdfSoon"));
      setTimeout(() => setPdfMsg(null), 4000);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="secondary" onClick={() => download("pdf")} loading={busy === "pdf"}>
        <FileDown aria-hidden className="size-4" />
        {t("exportPdf")}
      </Button>
      <Button variant="outline" onClick={() => download("json")} loading={busy === "json"} title={t("exportJson")} aria-label={t("exportJson")}>
        <FileJson aria-hidden className="size-4" />
        JSON
      </Button>
      <Button variant="primary" onClick={onTakedown}>
        <Send aria-hidden className="size-4" />
        {t("takedown")} <Kbd>T</Kbd>
      </Button>
      {pdfMsg && (
        <span role="status" className="text-sm text-review">
          {pdfMsg}
        </span>
      )}
    </div>
  );
}

export function TakedownDialog({ caseId, open, onClose }: { caseId: string; open: boolean; onClose: () => void }) {
  const { t, lang } = useLang();
  const { data } = useTakedown(open ? caseId : null);
  // The email opens in the UI language; the analyst can flip it for this one dialog.
  const [tabOverride, setTab] = useState<"en" | "ar" | null>(null);
  const tab = tabOverride ?? lang;
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  const close = () => {
    setTab(null);
    onClose();
  };

  const body = data ? (tab === "ar" ? data.body_ar : data.body_en) : "";
  const recipients = data ? (data.recipients?.length ? data.recipients : [data.registrar_abuse_email, data.hosting_abuse_email].filter((x): x is string => Boolean(x))) : [];
  const to = recipients.join(", ");
  // The API's mailto carries the English body; build our own when the Arabic tab is showing.
  const mailto = data ? (tab === "en" && data.mailto ? data.mailto : `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(data.subject)}&body=${encodeURIComponent(body)}`) : "#";

  return (
    <dialog
      ref={ref}
      onClose={close}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
      className="m-auto w-[min(44rem,calc(100vw-2rem))] rounded-[20px] border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-ink/40 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-start justify-between gap-4 border-b border-line p-5">
        <div>
          <h2 className="text-lg font-extrabold">{t("takedown")}</h2>
          <p className="mt-0.5 text-sm text-muted">{t("takedownHint")}</p>
        </div>
        <button type="button" onClick={close} aria-label={t("close")} className="grid size-9 place-items-center rounded-full text-ink-2 hover:bg-surface-2">
          <X aria-hidden className="size-5" />
        </button>
      </div>

      {data ? (
        <div className="p-5">
          <dl className="text-sm">
            <div className="flex items-center gap-3 py-1.5">
              <dt className="w-16 shrink-0 text-muted">{t("to")}</dt>
              <dd className="ltr min-w-0 flex-1 truncate font-semibold">{to || "—"}</dd>
              {to && <CopyButton text={to} label={`${t("copy")} ${t("to")}`} />}
            </div>
            <div className="flex items-center gap-3 py-1.5">
              <dt className="w-16 shrink-0 text-muted">{t("subject")}</dt>
              <dd className="ltr min-w-0 flex-1 truncate font-semibold">{data.subject}</dd>
              <CopyButton text={data.subject} label={`${t("copy")} ${t("subject")}`} />
            </div>
          </dl>

          <div role="tablist" className="mt-4 inline-flex rounded-full bg-surface-2 p-1">
            {(["en", "ar"] as const).map((l) => (
              <button key={l} role="tab" type="button" aria-selected={tab === l} onClick={() => setTab(l)} className={cn("rounded-full px-4 py-1.5 text-sm font-bold", tab === l ? "bg-surface text-ink shadow-sm" : "text-muted")}>
                {l === "en" ? t("english") : t("arabic")}
              </button>
            ))}
          </div>

          <div className="relative mt-3">
            <pre dir={tab === "ar" ? "rtl" : "ltr"} className={cn("max-h-[40vh] overflow-auto thin-scroll whitespace-pre-wrap rounded-xl bg-surface-2 p-4 text-sm leading-relaxed text-ink", tab === "ar" ? "font-arabic" : "font-sans")}>
              {body}
            </pre>
            <div className="absolute end-2 top-2">
              <CopyButton text={body} label={t("copy")} />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <a href={mailto} className="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-5 text-sm font-bold text-primary-ink hover:brightness-110">
              <Mail aria-hidden className="size-4" />
              {t("openMail")}
            </a>
            <Button variant="outline" onClick={() => navigator.clipboard?.writeText(`${t("to")}: ${to}\n${t("subject")}: ${data.subject}\n\n${body}`)}>
              {t("copy")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="p-5 text-sm text-muted">{t("loading")}…</div>
      )}
    </dialog>
  );
}
