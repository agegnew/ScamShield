"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Building2, Car, ChevronDown, ClipboardPaste, Globe2, Landmark, Package, Phone, PhoneCall, Puzzle, Search, ShieldAlert, TrendingUp, Volume2, VolumeX, type LucideIcon } from "lucide-react";
import { checkInput, type CheckResponse } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { L, type Pair } from "@/lib/radar";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { verdictTone } from "@/components/ui/verdict";
import { LangToggle, TextSizeToggle } from "@/components/shell/AppShell";

/* Public citizen checker. One input, one big answer, three lines of what to do.
   Mobile first: the result panel fills the phone screen in the verdict colour.
   Below the checker: the scams going around, what to do if you already paid, and how the check works. */

/** Turn UAE service numbers in advice text (Aman 8002626, 999, 2828…) into tap-to-call links. */
function withPhoneLinks(text: string) {
  const parts = text.split(/(\b(?:800\s?\d{3,5}|600\s?\d{2}\s?\d{4}|999|901|2828)\b)/);
  return parts.map((p, i) =>
    i % 2 === 1 ? (
      <a key={i} href={`tel:${p.replace(/\s/g, "")}`} className="ltr font-extrabold text-primary underline">
        {p}
      </a>
    ) : (
      p
    ),
  );
}

const EXAMPLES = ["https://tamm-fines-pay.test/pay?ref=AD-55120", "600 54 0000", "https://www.tamm.abudhabi/"];

const SCAMS: { icon: LucideIcon; title: Pair; story: Pair; flag: Pair }[] = [
  {
    icon: Car,
    title: ["“You have an unpaid traffic fine”", "«لديك مخالفة مرورية غير مدفوعة»"],
    story: ["An SMS says to pay within 24 hours through a link, or the fine doubles.", "رسالة نصية تطلب الدفع خلال 24 ساعة عبر رابط وإلا تتضاعف المخالفة."],
    flag: ["Pay fines only in the official app or site you open yourself.", "ادفع المخالفات فقط من التطبيق أو الموقع الرسمي الذي تفتحه بنفسك."],
  },
  {
    icon: Package,
    title: ["“Your parcel is on hold”", "«شحنتك معلّقة»"],
    story: ["A message asks for a small customs or delivery fee to release a parcel.", "رسالة تطلب رسومًا جمركية أو رسوم توصيل بسيطة للإفراج عن شحنة."],
    flag: ["Delivery companies don't ask for card details through an SMS link.", "شركات التوصيل لا تطلب بيانات البطاقة عبر رابط في رسالة نصية."],
  },
  {
    icon: Landmark,
    title: ["“Your bank account is blocked”", "«حسابك البنكي موقوف»"],
    story: ["Someone calls or texts as your bank and asks for the code you just received.", "شخص يتصل أو يراسلك باسم البنك ويطلب الرمز الذي وصلك للتو."],
    flag: ["Your bank will never ask for your OTP, PIN or card number.", "البنك لن يطلب أبدًا رمز التحقق أو الرقم السري أو رقم البطاقة."],
  },
  {
    icon: TrendingUp,
    title: ["“Easy money, guaranteed”", "«ربح سهل ومضمون»"],
    story: ["A job for liking videos, or an investment that promises a fixed high return.", "وظيفة مقابل الإعجاب بالفيديوهات، أو استثمار يَعِد بعائد مرتفع ثابت."],
    flag: ["If you must pay first to earn, it is a scam.", "إذا طُلب منك الدفع أولًا لتربح، فهو احتيال."],
  },
];

const HOW: { icon: LucideIcon; title: Pair; text: Pair }[] = [
  {
    icon: Building2,
    title: ["Official list", "قائمة رسمية"],
    text: ["We compare with the real websites and helplines of 53 UAE government bodies, banks and delivery companies.", "نقارن بالمواقع وأرقام الخدمة الحقيقية لـ 53 جهة حكومية وبنكًا وشركة توصيل في الإمارات."],
  },
  {
    icon: Globe2,
    title: ["Lookalike names", "أسماء مشابهة"],
    text: ["We catch names that copy a brand with one letter changed, an extra word or a different ending.", "نكشف الأسماء التي تقلّد علامة بتغيير حرف أو إضافة كلمة أو نهاية مختلفة."],
  },
  {
    icon: ShieldAlert,
    title: ["Page traps", "فخاخ الصفحة"],
    text: ["We read the page for card forms, fake urgency and tricks that hide where you really are.", "نقرأ الصفحة بحثًا عن نماذج البطاقات والاستعجال المزيف والحيل التي تخفي مكانك الحقيقي."],
  },
];

export default function CheckPage() {
  const { t, lang, pick } = useLang();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function run(value: string) {
    const v = value.trim();
    if (!v) return;
    setBusy(true);
    setErr(null);
    stopSpeaking();
    try {
      const r = await checkInput(v);
      setResult(r);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function paste() {
    try {
      const text = (await navigator.clipboard.readText()).trim();
      if (text) {
        setInput(text);
        inputRef.current?.focus();
      }
    } catch {
      inputRef.current?.focus();
    }
  }

  useEffect(() => {
    if (result) resultRef.current?.focus();
  }, [result]);

  function stopSpeaking() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    setSpeaking(false);
  }

  function speak() {
    if (!result || !("speechSynthesis" in window)) return;
    if (speaking) return stopSpeaking();
    const text = [pick(result as unknown as Record<string, unknown>, "headline"), ...(lang === "ar" ? result.advice_ar : result.advice_en)].join(". ");
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "ar" ? "ar-AE" : "en-GB";
    u.rate = 0.95;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }

  const verdict = result?.verdict ?? null;
  const tone = verdict ? verdictTone[verdict] : null;

  return (
    <div className="relative flex min-h-dvh flex-col overflow-x-clip bg-bg">
      {/* Backdrop: the radar's rings, quiet and in the citizen colours */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[760px] overflow-hidden">
        <div className="absolute left-1/2 top-[-260px] size-[1100px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(109,40,217,0.13)_0%,rgba(109,40,217,0.04)_45%,transparent_70%)]" />
        {[340, 560, 780, 1000].map((s) => (
          <div key={s} className="absolute left-1/2 -translate-x-1/2 rounded-full border border-primary/10" style={{ width: s, height: s, top: 300 - s / 2 }} />
        ))}
        <div className="absolute left-1/2 top-[-200px] size-[1000px] -translate-x-1/2 overflow-hidden rounded-full">
          <div
            className={cn("radar-sweep absolute inset-0", !busy && "radar-sweep-idle")}
            style={{ background: "conic-gradient(from 0deg, rgba(109,40,217,0.16), rgba(109,40,217,0) 55deg, transparent 360deg)" }}
          />
        </div>
      </div>

      <header className="relative mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/check" className="flex items-center gap-2">
          <Image src="/icon-256.png" alt="" width={36} height={36} className="size-9 rounded-xl" />
          <span className="leading-tight">
            <span className="block font-extrabold text-ink">{t("appName")}</span>
            <span className="block text-xs text-muted">{t("tagline")}</span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <TextSizeToggle />
          <LangToggle />
        </div>
      </header>

      <main id="main" className="relative w-full flex-1 pb-10">
        {!result && (
          <>
            <section className="rise-in mx-auto max-w-2xl px-4 pt-8 text-center sm:pt-16">
              <h1 className="text-4xl font-extrabold leading-[1.1] tracking-tight text-ink sm:text-5xl">{t("checkTitle")}</h1>
              <p className="mx-auto mt-4 max-w-lg text-lg text-ink-2">{t("checkSub")}</p>

              {/* The scanner */}
              <form
                className={cn("relative mt-8 rounded-[28px] border bg-surface p-2.5 text-start shadow-[0_24px_60px_-28px_rgba(76,29,149,0.45)] transition-[border-color,box-shadow] focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/15", busy ? "border-primary" : "border-line-2")}
                onSubmit={(e) => {
                  e.preventDefault();
                  run(input);
                }}
              >
                <label htmlFor="q" className="sr-only">
                  {t("checkPlaceholder")}
                </label>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  {/* Links and numbers read left to right, so the field keeps one layout in both languages. */}
                  <div className="relative flex-1" dir="ltr">
                    <Search aria-hidden className="pointer-events-none absolute start-4 top-1/2 size-5 -translate-y-1/2 text-muted" />
                    <input
                      ref={inputRef}
                      id="q"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={t("checkPlaceholder")}
                      inputMode="url"
                      autoComplete="off"
                      autoFocus
                      className="ltr h-14 w-full rounded-[20px] bg-transparent ps-12 pe-24 text-lg font-semibold text-ink placeholder:font-normal placeholder:text-muted scan-input"
                    />
                    <button
                      type="button"
                      onClick={paste}
                      className="absolute end-2 top-1/2 inline-flex h-9 -translate-y-1/2 items-center gap-1.5 rounded-full bg-surface-2 px-3 text-sm font-bold text-ink-2 hover:bg-primary-soft hover:text-primary"
                    >
                      <ClipboardPaste aria-hidden className="size-4" />
                      {L(["Paste", "لصق"], lang)}
                    </button>
                  </div>
                  <Button type="submit" size="lg" className="h-14 rounded-[20px] px-8 text-lg" loading={busy}>
                    {busy ? t("checking") : t("checkButton")}
                  </Button>
                </div>
                {busy && (
                  <div aria-hidden className="absolute inset-x-6 -bottom-px h-0.5 overflow-hidden rounded-full">
                    <div className="h-full w-1/3 animate-[scan-bar_1.1s_ease-in-out_infinite] rounded-full bg-primary" />
                  </div>
                )}
              </form>

              {err && (
                <p role="alert" className="mt-4 rounded-xl bg-fraud-soft px-3 py-2 text-sm font-semibold text-fraud">
                  {err}
                </p>
              )}

              <div className="mt-6">
                <p className="text-sm font-bold text-ink-2">{t("tryExample")}</p>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((ex) => (
                    <button
                      key={ex}
                      type="button"
                      onClick={() => {
                        setInput(ex);
                        run(ex);
                      }}
                      className="ltr inline-flex max-w-full items-center gap-1.5 rounded-full border border-line-2 bg-surface/80 px-3 py-1.5 text-sm font-semibold text-ink-2 backdrop-blur hover:border-primary/40 hover:bg-primary-soft"
                    >
                      {/^\+?[\d\s-]+$/.test(ex) ? <Phone aria-hidden className="size-3.5 shrink-0" /> : <Search aria-hidden className="size-3.5 shrink-0" />}
                      <span className="truncate">{ex}</span>
                    </button>
                  ))}
                </div>
              </div>
              <p className="mt-6 text-sm text-muted">{t("privacyNote")}</p>
            </section>

            {/* Scams going around */}
            <section className="mx-auto mt-16 max-w-5xl px-4 sm:mt-24">
              <h2 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">{L(["Scams going around in the UAE", "عمليات احتيال منتشرة في الإمارات"], lang)}</h2>
              <p className="mt-2 max-w-2xl text-ink-2">{L(["The message changes, the trick stays the same. Each one has a sign that gives it away.", "تتغير الرسالة وتبقى الحيلة نفسها. ولكل واحدة علامة تكشفها."], lang)}</p>
              <ul className="mt-6 grid gap-4 sm:grid-cols-2">
                {SCAMS.map((s) => (
                  <li key={s.title[0]} className="group relative overflow-hidden rounded-[22px] border border-line bg-surface p-5 transition-shadow hover:shadow-[0_18px_40px_-24px_rgba(76,29,149,0.4)]">
                    <div className="flex items-start gap-4">
                      <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary-soft text-primary">
                        <s.icon aria-hidden className="size-6" />
                      </span>
                      <div className="min-w-0">
                        <h3 className="text-lg font-extrabold leading-snug text-ink">{L(s.title, lang)}</h3>
                        <p className="mt-1 text-ink-2">{L(s.story, lang)}</p>
                      </div>
                    </div>
                    <p className="mt-4 flex items-start gap-2 rounded-2xl bg-fraud-soft px-3.5 py-2.5 text-sm font-bold text-fraud">
                      <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
                      {L(s.flag, lang)}
                    </p>
                  </li>
                ))}
              </ul>
            </section>

            {/* Already caught */}
            <section className="mx-auto mt-12 max-w-5xl px-4">
              <div className="overflow-hidden rounded-[26px] bg-[#1e1533] p-6 text-white sm:p-8">
                <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr] lg:items-center">
                  <div>
                    <h2 className="text-2xl font-extrabold leading-tight sm:text-3xl">{L(["Already paid or shared a code?", "هل دفعت أو شاركت رمزًا بالفعل؟"], lang)}</h2>
                    <p className="mt-2 text-white/75">{L(["Act in the first hour. Banks can often stop a payment that has not cleared yet.", "تصرّف خلال الساعة الأولى. يمكن للبنوك غالبًا إيقاف دفعة لم تُنفَّذ بعد."], lang)}</p>
                  </div>
                  <ol className="grid gap-3 sm:grid-cols-3">
                    {[
                      { n: 1, title: L(["Call your bank", "اتصل بالبنك"], lang), text: L(["Use the number on the back of your card. Ask them to block it.", "استخدم الرقم على ظهر بطاقتك واطلب إيقافها."], lang), tel: null },
                      { n: 2, title: L(["Report to Aman", "أبلغ خدمة أمان"], lang), text: L(["Abu Dhabi Police, free and confidential.", "شرطة أبوظبي، مجانية وسرية."], lang), tel: "8002626" },
                      { n: 3, title: L(["Emergency", "الطوارئ"], lang), text: L(["If you are in danger right now.", "إذا كنت في خطر الآن."], lang), tel: "999" },
                    ].map((s) => (
                      <li key={s.n} className="rounded-2xl bg-white/[0.07] p-4 ring-1 ring-white/10">
                        <span className="grid size-7 place-items-center rounded-full bg-accent text-sm font-extrabold text-white">{s.n}</span>
                        <p className="mt-3 font-extrabold">{s.title}</p>
                        <p className="mt-1 text-sm text-white/70">{s.text}</p>
                        {s.tel && (
                          <a href={`tel:${s.tel}`} className="ltr mt-3 inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-sm font-extrabold text-[#1e1533] hover:bg-accent-soft">
                            <PhoneCall aria-hidden className="size-4" />
                            {s.tel === "8002626" ? "800 2626" : s.tel}
                          </a>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </section>

            {/* How the check works */}
            <section className="mx-auto mt-16 max-w-5xl px-4">
              <h2 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">{L(["How we check", "كيف نتحقق"], lang)}</h2>
              <ul className="mt-6 grid gap-6 sm:grid-cols-3">
                {HOW.map((h) => (
                  <li key={h.title[0]}>
                    <span className="grid size-11 place-items-center rounded-2xl bg-surface text-primary ring-1 ring-line">
                      <h.icon aria-hidden className="size-5" />
                    </span>
                    <h3 className="mt-3 text-lg font-extrabold text-ink">{L(h.title, lang)}</h3>
                    <p className="mt-1 text-ink-2">{L(h.text, lang)}</p>
                  </li>
                ))}
              </ul>
            </section>

            {/* Extension */}
            <section className="mx-auto mt-16 max-w-5xl px-4">
              <Link href="/extension" className="group flex flex-col gap-4 rounded-[26px] border border-primary/25 bg-primary-soft p-6 transition-colors hover:border-primary/50 sm:flex-row sm:items-center sm:p-8">
                <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-primary text-white shadow-[0_10px_30px_-10px_rgba(109,40,217,0.8)]">
                  <Puzzle aria-hidden className="size-7" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xl font-extrabold text-ink">{L(["Get the warning before you open the link", "احصل على التحذير قبل أن تفتح الرابط"], lang)}</span>
                  <span className="mt-1 block text-ink-2">{L(["Add ScamShield to Chrome. It blocks known fake sites and warns you on payment pages.", "أضف درع الاحتيال إلى كروم. يحجب المواقع المزيفة المعروفة وينبّهك في صفحات الدفع."], lang)}</span>
                </span>
                <span className="inline-flex items-center gap-1.5 self-start rounded-full bg-primary px-5 py-2.5 font-extrabold text-white sm:self-center">
                  {L(["Get the extension", "احصل على الإضافة"], lang)}
                  <ArrowUpRight aria-hidden className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 rtl:-scale-x-100" />
                </span>
              </Link>
            </section>
          </>
        )}

        {result && tone && verdict && (
          <section ref={resultRef} tabIndex={-1} aria-live="polite" className={cn("rise-in mx-auto mt-4 max-w-xl overflow-hidden rounded-[24px] border-2 outline-none", tone.line, tone.bg)}>
            <div className="px-6 pt-8 pb-6 text-center">
              <tone.Icon aria-hidden className={cn("mx-auto size-16", tone.fg)} strokeWidth={2.25} />
              <p className={cn("mt-3 text-sm font-bold uppercase tracking-wide", tone.fg)}>{t(verdict)}</p>
              <h1 className={cn("mt-1 text-3xl font-extrabold leading-tight tracking-tight", tone.fg)}>{pick(result as unknown as Record<string, unknown>, "headline")}</h1>
              {/* When the answer is reassuring, say why up front ("This is an official Emirates NBD helpline"). */}
              {verdict === "LEGIT" && result.reasons?.find((r) => r.weight < 0) && (
                <p className={cn("mx-auto mt-2 max-w-sm text-base font-bold", tone.fg)}>{pick(result.reasons.find((r) => r.weight < 0) as unknown as Record<string, unknown>, "text")}</p>
              )}
              <p className="mt-4 text-sm text-ink-2">
                {t("checkedInput")} <span className="ltr font-bold text-ink break-all">{result.input}</span>
              </p>
            </div>

            <div className="mx-3 mb-3 rounded-[18px] bg-surface p-5">
              <h2 className="text-base font-extrabold text-ink">{t("whatToDo")}</h2>
              <ol className="mt-3 flex flex-col gap-3">
                {(lang === "ar" ? result.advice_ar : result.advice_en).map((a, i) => (
                  <li key={i} className="flex gap-3 text-base leading-snug text-ink">
                    <span aria-hidden className={cn("mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs font-extrabold text-white", verdict === "FRAUD" ? "bg-fraud" : verdict === "SUSPICIOUS" ? "bg-review" : "bg-primary")}>
                      {i + 1}
                    </span>
                    <span>{withPhoneLinks(a)}</span>
                  </li>
                ))}
              </ol>

              <div className="mt-5 flex flex-wrap gap-2">
                <Button variant="secondary" onClick={speak} aria-pressed={speaking}>
                  {speaking ? <VolumeX aria-hidden className="size-4" /> : <Volume2 aria-hidden className="size-4" />}
                  {speaking ? t("stopReading") : t("readAloud")}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setResult(null);
                    setInput("");
                    stopSpeaking();
                  }}
                >
                  {t("checkAgain")}
                </Button>
              </div>

              {result.reasons && result.reasons.length > 0 && (
                <details className="group mt-5 border-t border-line pt-4">
                  <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-bold text-ink-2">
                    {t("whyWeThink")}
                    <ChevronDown aria-hidden className="size-4 transition-transform group-open:rotate-180" />
                  </summary>
                  <ul className="mt-3 flex flex-col gap-2">
                    {result.reasons.map((r) => (
                      <li key={r.code} className="flex items-start gap-2 text-sm text-ink-2">
                        <span aria-hidden className={cn("mt-2 size-1.5 shrink-0 rounded-full", r.weight > 0 ? "bg-fraud" : "bg-safe")} />
                        {pick(r as unknown as Record<string, unknown>, "text")}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </section>
        )}
      </main>

      <footer className="relative mx-auto w-full max-w-5xl border-t border-line px-4 py-8 text-center text-xs text-muted">
        <p>{t("checkFooter")}</p>
        <div className="mt-2 flex justify-center gap-4">
          <Link href="/extension" className="font-bold text-primary underline">
            {t("navExtension")}
          </Link>
          <Link href="/login" className="font-bold text-primary underline">
            {t("analystConsole")}
          </Link>
        </div>
      </footer>
    </div>
  );
}
