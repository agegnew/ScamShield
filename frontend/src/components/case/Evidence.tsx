"use client";

import Image from "next/image";
import { ArrowDown, Camera, CircleAlert, Globe, MapPin, Server, Download, Fingerprint, EyeOff, Copy as CopyIcon } from "lucide-react";
import type { Case, Evidence as EvidenceT } from "@/lib/api";
import { screenshotUrl } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn, daysBetween, fmtTime } from "@/lib/utils";
import { KeyValue, Panel, PanelTitle } from "@/components/ui/primitives";

/* Which evidence block a reason's evidence_ref points at. */
export function refToBlock(ref: string | null | undefined): string | null {
  if (!ref) return null;
  if (ref === "url" || ref.startsWith("final_url")) return "url";
  if (ref.startsWith("screenshot") || ref.startsWith("visual")) return "screenshot";
  if (ref.startsWith("rdap") || ref.startsWith("domain") || ref.startsWith("shared_hosting")) return "domain";
  if (ref.startsWith("ip") || ref.startsWith("asn") || ref.startsWith("hosting")) return "hosting";
  if (ref.startsWith("forms")) return "forms";
  if (ref.startsWith("redirect")) return "redirects";
  if (ref.startsWith("text") || ref.startsWith("title") || ref.startsWith("theme") || ref.startsWith("keywords")) return "text";
  if (ref.startsWith("candidate") || ref.startsWith("brands.helplines") || ref.startsWith("maps")) return "maps";
  if (ref.startsWith("download")) return "downloads";
  if (ref.startsWith("cloaking")) return "cloaking";
  if (ref.startsWith("fingerprint")) return "fingerprints";
  return null;
}

const hl = (on: boolean) => cn("transition-[box-shadow,border-color] duration-300", on && "border-primary ring-4 ring-primary/15");

function pageKindLabel(kind: string, t: ReturnType<typeof useLang>["t"]) {
  const key = `pageKind_${kind}` as Parameters<typeof t>[0];
  try {
    return t(key);
  } catch {
    return kind.replaceAll("_", " ");
  }
}

export function ScreenshotPanel({ ev, active, offline }: { ev: EvidenceT | null | undefined; active: boolean; offline: boolean }) {
  const { t } = useLang();
  const src = screenshotUrl(ev?.screenshot_path);
  return (
    <Panel id="ev-screenshot" className={cn("p-4", hl(active))}>
      <PanelTitle hint={ev?.screenshot_path ? t("screenshotHint") : undefined}>{t("screenshot")}</PanelTitle>
      <div className="mx-auto mt-4 max-w-[300px]">
        <div className="phone-frame">
          <div className="screen relative grid place-items-center bg-surface-2">
            {src ? (
              // Plain img: screenshots come from the API host, sizes vary, no optimisation wanted.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={src} alt={ev?.title ? `${t("screenshot")}: ${ev.title}` : t("screenshot")} className="h-full w-full object-cover object-top" />
            ) : (
              <div className="flex flex-col items-center gap-2 p-6 text-center text-sm text-muted">
                <Camera aria-hidden className="size-8" />
                {!ev ? t("fetching") : offline ? t("offlineSite") : t("noScreenshot")}
              </div>
            )}
          </div>
        </div>
      </div>
      {ev?.screenshot_sha256 && (
        <p className="ltr mt-3 truncate text-center text-[11px] text-muted" title={ev.screenshot_sha256}>
          sha256 {ev.screenshot_sha256}
        </p>
      )}
      {ev?.page_kind && ev.page_kind !== "content" && (
        <p className="mt-3 flex items-start gap-2 rounded-xl bg-unknown-soft px-3 py-2 text-sm text-unknown" title={t("pageKindHint")}>
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          <span>
            <span className="font-bold">{pageKindLabel(ev.page_kind, t)}</span>
            <span className="block text-xs">{t("pageKindHint")}</span>
          </span>
        </p>
      )}
      {ev?.fetch_error && (
        <p className="mt-3 flex items-start gap-2 rounded-xl bg-review-soft px-3 py-2 text-sm text-review">
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {t("fetchFailed")}
        </p>
      )}
    </Panel>
  );
}

export function RedirectsPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  const chain = ev?.redirect_chain ?? [];
  return (
    <Panel id="ev-redirects" className={cn("p-4", hl(active))}>
      <PanelTitle>{t("redirects")}</PanelTitle>
      {chain.length <= 1 ? (
        <p className="mt-2 text-sm text-muted">{ev ? t("noRedirects") : "…"}</p>
      ) : (
        <ol className="mt-3 flex flex-col">
          {chain.map((hop, i) => (
            <li key={i} className="relative flex flex-col">
              <div className="flex items-start gap-3">
                <span className={cn("mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs font-extrabold tabular-nums", i === chain.length - 1 ? "bg-fraud-soft text-fraud" : "bg-surface-2 text-ink-2")}>{i + 1}</span>
                <div className="min-w-0">
                  <p className="ltr break-all text-sm font-semibold text-ink">{hop.url}</p>
                  <p className="text-xs text-muted tabular-nums">HTTP {hop.status}</p>
                </div>
              </div>
              {i < chain.length - 1 && <ArrowDown aria-hidden className="my-1 ms-1.5 size-3 text-muted" />}
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

export function DomainPanel({ ev, discoveredAt, active }: { ev: EvidenceT | null | undefined; discoveredAt: string; active: boolean }) {
  const { t, lang } = useLang();
  const age = daysBetween(ev?.rdap?.created, discoveredAt);
  return (
    <Panel id="ev-domain" className={cn("p-4", hl(active))}>
      <PanelTitle>
        <span className="inline-flex items-center gap-2">
          <Globe aria-hidden className="size-4 text-primary" />
          {t("domain")}
        </span>
      </PanelTitle>
      <dl className="mt-2 divide-y divide-line">
        <KeyValue
          k={t("registered")}
          v={
            ev?.rdap?.created ? (
              <span className="flex flex-col items-start gap-1">
                <span className="ltr">{fmtTime(ev.rdap.created, lang, { hour: undefined, minute: undefined, year: "numeric" })}</span>
                {age !== null && <span className={cn("whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-bold", age <= 30 ? "bg-fraud-soft text-fraud" : "bg-surface-2 text-ink-2")}>{t("daysOld", { d: age })}</span>}
              </span>
            ) : null
          }
        />
        <KeyValue k={t("registrar")} v={ev?.rdap?.registrar} />
        <KeyValue k={t("abuseContact")} v={ev?.rdap?.abuse_email} mono />
      </dl>
      {ev?.shared_hosting && (
        <p className="mt-2 flex items-start gap-2 rounded-xl bg-review-soft px-3 py-2 text-xs text-review">
          <CircleAlert aria-hidden className="mt-0.5 size-3.5 shrink-0" />
          {t("sharedHosting")}
        </p>
      )}
    </Panel>
  );
}

export function HostingPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  return (
    <Panel id="ev-hosting" className={cn("p-4", hl(active))}>
      <PanelTitle>
        <span className="inline-flex items-center gap-2">
          <Server aria-hidden className="size-4 text-primary" />
          {t("hosting")}
        </span>
      </PanelTitle>
      <dl className="mt-2 divide-y divide-line">
        <KeyValue k={t("ipAddress")} v={ev?.ip} mono />
        <KeyValue k="ASN" v={ev?.asn ? `AS${ev.asn}` : null} mono />
        <KeyValue k={t("hosting")} v={ev?.hosting_org} />
        <KeyValue k={t("abuseContact")} v={ev?.hosting_abuse_email} mono />
      </dl>
    </Panel>
  );
}

export function FormsPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  const forms = ev?.forms ?? [];
  const SENSITIVE = ["password", "card", "cvv", "otp", "pin", "emirates", "id", "iban", "account"];
  return (
    <Panel id="ev-forms" className={cn("p-4", hl(active))}>
      <PanelTitle>{t("forms")}</PanelTitle>
      {forms.length === 0 ? (
        <p className="mt-2 text-sm text-muted">{ev ? t("noForms") : "…"}</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {forms.map((f, i) => {
            const fields = [...(f.sensitive ?? []), ...(f.field_hints ?? [])].filter((x, idx, arr) => arr.indexOf(x) === idx);
            return (
              <li key={i} className="rounded-xl bg-surface-2 p-3">
                <p className="text-xs font-bold text-muted">{t("asksFor")}</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {fields.map((h) => {
                    const hot = SENSITIVE.some((s) => h.toLowerCase().includes(s)) || (f.input_types ?? []).includes("password");
                    return (
                      <span key={h} className={cn("rounded-full px-2.5 py-1 text-xs font-bold", hot ? "bg-fraud-soft text-fraud" : "bg-surface text-ink-2")}>
                        {h}
                      </span>
                    );
                  })}
                </div>
                {f.action && <p className="ltr mt-2 truncate text-xs text-muted">{f.action}</p>}
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

export function TextPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  if (!ev?.title && !ev?.text_excerpt) return null;
  return (
    <Panel id="ev-text" className={cn("p-4", hl(active))}>
      <PanelTitle>{t("pageText")}</PanelTitle>
      {ev.title && <p className="mt-2 font-bold text-ink">{ev.title}</p>}
      {ev.text_excerpt && <blockquote className="mt-2 max-h-40 overflow-auto thin-scroll border-s-2 border-line-2 ps-3 text-sm text-ink-2">{ev.text_excerpt}</blockquote>}
    </Panel>
  );
}

export function MapsPanel({ c, active, officialHelplines }: { c: Case; active: boolean; officialHelplines: string[] }) {
  const { t } = useLang();
  const x = c.candidate.extra;
  if (!x?.listing_name && !x?.phone) return null;
  return (
    <Panel id="ev-maps" className={cn("p-4", hl(active))}>
      <PanelTitle>
        <span className="inline-flex items-center gap-2">
          <MapPin aria-hidden className="size-4 text-primary" />
          {t("mapsListing")}
        </span>
      </PanelTitle>
      <dl className="mt-2 divide-y divide-line">
        <KeyValue k={t("listingName")} v={x.listing_name} />
        <KeyValue k={t("listedPhone")} v={x.phone ? <span className="rounded-full bg-fraud-soft px-2.5 py-0.5 font-bold text-fraud">{x.phone}</span> : null} mono />
        {officialHelplines.length > 0 && <KeyValue k={t("officialHelpline")} v={<span className="rounded-full bg-safe-soft px-2.5 py-0.5 font-bold text-safe">{officialHelplines.join(" · ")}</span>} mono />}
        <KeyValue k={t("address")} v={x.address} />
        {c.candidate.query && <KeyValue k={t("query")} v={<q>{c.candidate.query}</q>} />}
      </dl>
    </Panel>
  );
}

export function DownloadsPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  const d = ev?.download_signals ?? [];
  if (d.length === 0) return null;
  return (
    <Panel id="ev-downloads" className={cn("p-4", hl(active))}>
      <PanelTitle>
        <span className="inline-flex items-center gap-2">
          <Download aria-hidden className="size-4 text-primary" />
          {t("downloads")}
        </span>
      </PanelTitle>
      <ul className="mt-2 flex flex-col gap-2">
        {d.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            <span className="rounded-full bg-fraud-soft px-2 py-0.5 text-xs font-bold text-fraud">{s.kind}</span>
            <span className="min-w-0 truncate text-ink-2">{s.text || s.href}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function CloakingPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  const c = ev?.cloaking as (Record<string, unknown> & { signals?: string[] }) | null | undefined;
  if (!c) return null;
  const signals = c.signals ?? [];
  return (
    <Panel id="ev-cloaking" className={cn("p-4", hl(active))}>
      <PanelTitle hint={t("cloakingHint")}>
        <span className="inline-flex items-center gap-2">
          <EyeOff aria-hidden className="size-4 text-primary" />
          {t("cloaking")}
        </span>
      </PanelTitle>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {signals.length === 0 ? <span className="text-sm text-muted">—</span> : signals.map((s) => <span key={s} className="rounded-full bg-fraud-soft px-2.5 py-1 text-xs font-bold text-fraud">{s.replaceAll("_", " ")}</span>)}
      </div>
    </Panel>
  );
}

export function FingerprintsPanel({ ev, active }: { ev: EvidenceT | null | undefined; active: boolean }) {
  const { t } = useLang();
  const f = ev?.fingerprints;
  if (!f) return null;
  const contacts = (f.contacts ?? {}) as Record<string, string[] | undefined>;
  const contactList = Object.entries(contacts).flatMap(([k, v]) => (v ?? []).map((x) => `${k}: ${x}`));
  return (
    <Panel id="ev-fingerprints" className={cn("p-4", hl(active))}>
      <PanelTitle>
        <span className="inline-flex items-center gap-2">
          <Fingerprint aria-hidden className="size-4 text-primary" />
          {t("fingerprints")}
        </span>
      </PanelTitle>
      <dl className="mt-2 divide-y divide-line">
        <KeyValue k="Favicon" v={f.favicon_mmh3 != null ? String(f.favicon_mmh3) : null} mono />
        <KeyValue k="Template" v={f.dom_hash ? f.dom_hash.slice(0, 16) : null} mono />
        <KeyValue k={t("trackers")} v={(f.tracking_ids ?? []).length ? (f.tracking_ids ?? []).join(", ") : null} mono />
        <KeyValue k={t("contacts")} v={contactList.length ? contactList.join(", ") : null} mono />
      </dl>
    </Panel>
  );
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const { t } = useLang();
  return (
    <button
      type="button"
      onClick={() => navigator.clipboard?.writeText(text)}
      aria-label={label}
      title={t("copy")}
      className="inline-grid size-8 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-ink"
    >
      <CopyIcon aria-hidden className="size-4" />
    </button>
  );
}

export { Image };
