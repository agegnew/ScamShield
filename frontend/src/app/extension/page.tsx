"use client";

import { BackButton } from "@/components/ui/BackButton";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Ban, Check, Copy, Download, Puzzle, FileWarning, MessageCircle, MousePointerClick, Share2, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useLang } from "@/lib/i18n";
import { L, type Pair } from "@/lib/radar";
import { Button } from "@/components/ui/primitives";
import { LangToggle } from "@/components/shell/AppShell";

/* Public page to get and share the ScamShield Guardian browser extension (Simeon's extension/ folder).
   Not in the Chrome Web Store yet, so install is "Load unpacked" — said plainly, with the 4 steps. */

const T = {
  kicker: ["Browser extension", "إضافة المتصفح"],
  title: ["ScamShield Guardian", "حارس درع الاحتيال"],
  lead: [
    "Warns you before you type your card, one-time code or password into a fake UAE website.",
    "ينبّهك قبل أن تُدخل بطاقتك أو رمز التحقق أو كلمة المرور في موقع إماراتي مزيف.",
  ],
  download: ["Download for Chrome and Edge", "تنزيل لمتصفح كروم وإيدج"],
  addToChrome: ["Add to Chrome", "أضف إلى كروم"],
  manual: ["Or download the file and install it yourself", "أو نزّل الملف وثبّته بنفسك"],
  f1t: ["Blocks known scam sites", "يحجب مواقع الاحتيال المعروفة"],
  f1d: ["Sites police analysts confirmed as fraud open a warning page instead, with a link to the real site.", "المواقع التي أكد المحللون أنها احتيال تفتح صفحة تحذير بدلًا منها مع رابط الموقع الحقيقي."],
  f2t: ["Check any site in one click", "افحص أي موقع بنقرة"],
  f2d: ["Click the shield icon to see the verdict, the reasons and what to do, in Arabic or English.", "انقر أيقونة الدرع لترى الحكم والأسباب وماذا تفعل، بالعربية أو الإنجليزية."],
  f3t: ["Warns on fake payment forms", "ينبّه عند نماذج الدفع المزيفة"],
  f3d: ["A red bar appears when a page asks for card, OTP, password or Emirates ID on a domain the brand doesn't own.", "يظهر شريط أحمر عندما تطلب صفحة بطاقة أو رمز تحقق أو كلمة مرور أو هوية على نطاق لا تملكه الجهة."],
  installTitle: ["Install in 4 steps", "التثبيت في 4 خطوات"],
  installNote: [
    "Guardian is not in the Chrome Web Store yet, so it installs in developer mode. It takes about a minute.",
    "الحارس غير متوفر في متجر كروم بعد، لذا يُثبّت بوضع المطور. يستغرق ذلك دقيقة تقريبًا.",
  ],
  s1: ["Download the file above and unzip it.", "نزّل الملف أعلاه وفك ضغطه."],
  s2: ["Open this address in Chrome or Edge:", "افتح هذا العنوان في كروم أو إيدج:"],
  s3: ["Turn on Developer mode (top right).", "فعّل وضع المطور (أعلى اليمين)."],
  s4: ["Click Load unpacked and choose the scamshield-guardian folder.", "انقر Load unpacked واختر مجلد scamshield-guardian."],
  copy: ["Copy", "نسخ"],
  copied: ["Copied", "تم النسخ"],
  shareTitle: ["Share it", "شاركها"],
  shareSub: ["Scan the code or send the link to family and colleagues.", "امسح الرمز أو أرسل الرابط للعائلة والزملاء."],
  shareBtn: ["Share", "مشاركة"],
  whatsapp: ["WhatsApp", "واتساب"],
  copyLink: ["Copy link", "نسخ الرابط"],
  shareText: [
    "ScamShield Guardian warns you before you type your card or OTP into a fake UAE website. Get it here:",
    "حارس درع الاحتيال ينبّهك قبل إدخال بطاقتك أو رمز التحقق في موقع إماراتي مزيف. احصل عليه هنا:",
  ],
  privacyTitle: ["What it sends", "ما الذي ترسله"],
  privacy: [
    "Only web addresses: the site you are on, and the full address when you click the icon. It never reads what you type into a form. Blocking happens inside your browser.",
    "عناوين المواقع فقط: الموقع الذي تزوره، والعنوان الكامل عند النقر على الأيقونة. لا تقرأ أبدًا ما تكتبه في النماذج. يتم الحجب داخل متصفحك.",
  ],
  footer: [
    "A CipherGuard project for the 42 Abu Dhabi × Abu Dhabi Police hackathon. Proposed pilot, not an official police service.",
    "مشروع CipherGuard لهاكاثون 42 أبوظبي × شرطة أبوظبي. تجربة مقترحة، ليست خدمة شرطية رسمية.",
  ],
} as const satisfies Record<string, Pair>;

/* Once the extension is published, set NEXT_PUBLIC_CHROME_STORE_URL to its Chrome Web Store page:
   the main button becomes "Add to Chrome" (one click, installs in place) and the zip stays as a fallback. */
const STORE_URL = process.env.NEXT_PUBLIC_CHROME_STORE_URL ?? "";

export default function ExtensionPage() {
  const { lang } = useLang();
  const tr = (k: keyof typeof T) => L(T[k], lang);
  const [url, setUrl] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [canShare, setCanShare] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read the page address once in the browser
    setUrl(window.location.origin + "/extension");
    setCanShare(typeof navigator !== "undefined" && typeof navigator.share === "function");
  }, []);

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 1800);
    } catch {
      /* clipboard blocked: the text stays visible to select */
    }
  }

  const message = `${tr("shareText")} ${url}`;

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-2 px-4 py-4">
        <BackButton fallback="/check" className="-ms-3" />
        <Link href="/check" className="me-auto flex items-center gap-2">
          <Image src="/icon-256.png" alt="" width={36} height={36} className="size-9 rounded-xl" />
          <span className="font-extrabold text-ink">{L(["ScamShield", "درع الاحتيال"], lang)}</span>
        </Link>
        <LangToggle />
      </header>

      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 pb-12">
        {/* Hero */}
        <section className="mt-4 grid items-center gap-8 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1 text-sm font-bold text-primary">
              <ShieldCheck aria-hidden className="size-4" />
              {tr("kicker")}
            </p>
            <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl">{tr("title")}</h1>
            <p className="mt-3 max-w-xl text-lg leading-relaxed text-ink-2">{tr("lead")}</p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              {STORE_URL ? (
                <a
                  href={STORE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-14 items-center gap-2 rounded-full bg-primary px-7 text-base font-bold text-primary-ink shadow-[0_8px_24px_-10px_var(--glow)] hover:brightness-110"
                >
                  <Puzzle aria-hidden className="size-5" />
                  {tr("addToChrome")}
                </a>
              ) : (
                <a
                  href="/scamshield-guardian.zip"
                  download
                  className="inline-flex h-14 items-center gap-2 rounded-full bg-primary px-7 text-base font-bold text-primary-ink shadow-[0_8px_24px_-10px_var(--glow)] hover:brightness-110"
                >
                  <Download aria-hidden className="size-5" />
                  {tr("download")}
                </a>
              )}
              {STORE_URL && (
                <a href="/scamshield-guardian.zip" download className="text-sm font-bold text-primary underline">
                  {tr("manual")}
                </a>
              )}
              <span className="ltr text-sm text-muted">v0.2 · 65 KB</span>
            </div>
          </div>

          {/* Mock of the warning page, so people see what it does before installing */}
          <div aria-hidden className="relative mx-auto w-full max-w-md overflow-hidden rounded-[20px] border border-line bg-surface shadow-[0_30px_60px_-30px_rgba(30,27,46,0.45)]">
            <div className="flex items-center gap-1.5 border-b border-line bg-surface-2 px-3 py-2">
              <span className="size-2.5 rounded-full bg-fraud/60" />
              <span className="size-2.5 rounded-full bg-review/60" />
              <span className="size-2.5 rounded-full bg-safe/60" />
              <span className="ltr ms-2 truncate rounded-full bg-surface px-3 py-0.5 text-xs text-muted">moi-portal.com</span>
            </div>
            <div className="bg-fraud-soft px-6 py-8 text-center">
              <Ban className="mx-auto size-14 text-fraud" strokeWidth={2.25} />
              <p className="mt-3 text-xl font-extrabold text-fraud">{L(["This site was confirmed as a scam", "تم تأكيد أن هذا الموقع احتيالي"], lang)}</p>
              <p className="mt-2 text-sm text-ink-2">{L(["It imitates the Ministry of Interior. The real site is moi.gov.ae.", "ينتحل صفة وزارة الداخلية. الموقع الحقيقي هو moi.gov.ae."], lang)}</p>
              <div className="mt-4 flex justify-center gap-2">
                <span className="rounded-full bg-primary px-4 py-2 text-sm font-bold text-primary-ink">{L(["Go back", "رجوع"], lang)}</span>
                <span className="rounded-full border border-line-2 bg-surface px-4 py-2 text-sm font-bold text-ink">{L(["Open the real site", "افتح الموقع الحقيقي"], lang)}</span>
              </div>
            </div>
          </div>
        </section>

        {/* What it does */}
        <section className="mt-12 grid gap-4 md:grid-cols-3">
          {(
            [
              [Ban, "f1t", "f1d"],
              [MousePointerClick, "f2t", "f2d"],
              [FileWarning, "f3t", "f3d"],
            ] as const
          ).map(([Icon, t, d]) => (
            <div key={t} className="rounded-[16px] border border-line bg-surface p-5">
              <span className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary">
                <Icon aria-hidden className="size-5" />
              </span>
              <h2 className="mt-3 text-lg font-extrabold text-ink">{tr(t)}</h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-2">{tr(d)}</p>
            </div>
          ))}
        </section>

        <div className="mt-12 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
          {/* Install steps */}
          <section className="rounded-[16px] border border-line bg-surface p-5 sm:p-6">
            <h2 className="text-xl font-extrabold text-ink">{tr("installTitle")}</h2>
            <p className="mt-1 text-sm text-muted">{tr("installNote")}</p>
            <ol className="mt-4 flex flex-col gap-4">
              {(["s1", "s2", "s3", "s4"] as const).map((k, i) => (
                <li key={k} className="flex gap-3">
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary text-sm font-extrabold text-primary-ink">{i + 1}</span>
                  <div className="min-w-0 pt-0.5 text-ink">
                    {tr(k)}
                    {k === "s2" && (
                      <div className="mt-2 flex items-center gap-2">
                        <code className="ltr rounded-lg bg-surface-2 px-3 py-1.5 text-sm font-bold">chrome://extensions</code>
                        <button type="button" onClick={() => copy("chrome://extensions", "ext")} className="inline-flex h-8 items-center gap-1 rounded-full px-2.5 text-xs font-bold text-primary hover:bg-primary-soft">
                          {copied === "ext" ? <Check aria-hidden className="size-3.5" /> : <Copy aria-hidden className="size-3.5" />}
                          {copied === "ext" ? tr("copied") : tr("copy")}
                        </button>
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* Share: QR, share sheet, WhatsApp, copy */}
          <section className="rounded-[16px] border border-line bg-surface p-5 sm:p-6">
            <h2 className="text-xl font-extrabold text-ink">{tr("shareTitle")}</h2>
            <p className="mt-1 text-sm text-muted">{tr("shareSub")}</p>
            <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
              <div className="rounded-2xl border border-line bg-white p-3">
                {url ? <QRCodeSVG value={url} size={148} level="M" marginSize={0} fgColor="#1e1b2e" title={url} /> : <div className="size-[148px]" />}
              </div>
              <div className="flex w-full flex-col gap-2">
                {canShare && (
                  <Button onClick={() => navigator.share({ title: tr("title"), text: tr("shareText"), url }).catch(() => {})}>
                    <Share2 aria-hidden className="size-4" />
                    {tr("shareBtn")}
                  </Button>
                )}
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(message)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[#25d366] px-5 text-sm font-bold text-[#0b2e17] hover:brightness-105"
                >
                  <MessageCircle aria-hidden className="size-4" />
                  {tr("whatsapp")}
                </a>
                <Button variant="outline" onClick={() => copy(url, "link")}>
                  {copied === "link" ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />}
                  {copied === "link" ? tr("copied") : tr("copyLink")}
                </Button>
                <p className="ltr truncate text-center text-xs text-muted">{url}</p>
              </div>
            </div>
          </section>
        </div>

        <section className="mt-4 rounded-[16px] bg-surface-2 p-5">
          <h2 className="font-extrabold text-ink">{tr("privacyTitle")}</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-2">{tr("privacy")}</p>
        </section>
      </main>

      <footer className="mx-auto w-full max-w-5xl px-4 pb-8 text-center text-xs text-muted">{tr("footer")}</footer>
    </div>
  );
}
