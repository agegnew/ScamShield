"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Phone, Search, Volume2, VolumeX } from "lucide-react";
import { checkInput, type CheckResponse } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Button, Input } from "@/components/ui/primitives";
import { verdictTone } from "@/components/ui/verdict";
import { LangToggle, TextSizeToggle } from "@/components/shell/AppShell";

/* Public citizen checker. One input, one big answer, three lines of what to do.
   Mobile first: the result panel fills the phone screen in the verdict colour. */

const EXAMPLES = ["https://tamm-fines-pay.test/pay?ref=AD-55120", "600 54 0000", "https://www.tamm.abudhabi/"];

export default function CheckPage() {
  const { t, lang, pick } = useLang();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  async function run(value: string) {
    const v = value.trim();
    if (!v) return;
    setBusy(true);
    setErr(null);
    stopSpeaking();
    try {
      const r = await checkInput(v);
      setResult(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
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
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="mx-auto flex w-full max-w-xl items-center justify-between px-4 py-4">
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

      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-4 pb-10">
        {!result && (
          <section className="rise-in pt-6 sm:pt-12">
            <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-ink sm:text-4xl">{t("checkTitle")}</h1>
            <p className="mt-3 text-base text-ink-2">{t("checkSub")}</p>

            <form
              className="mt-8"
              onSubmit={(e) => {
                e.preventDefault();
                run(input);
              }}
            >
              <label htmlFor="q" className="sr-only">
                {t("checkPlaceholder")}
              </label>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Input
                  id="q"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={t("checkPlaceholder")}
                  inputMode="url"
                  autoComplete="off"
                  className="ltr h-14 flex-1 rounded-2xl text-lg"
                  autoFocus
                />
                <Button type="submit" size="lg" className="sm:px-8" loading={busy}>
                  {busy ? t("checking") : t("checkButton")}
                </Button>
              </div>
            </form>

            {err && (
              <p role="alert" className="mt-4 rounded-xl bg-fraud-soft px-3 py-2 text-sm font-semibold text-fraud">
                {err}
              </p>
            )}

            <div className="mt-6">
              <p className="text-sm font-bold text-ink-2">{t("tryExample")}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => {
                      setInput(ex);
                      run(ex);
                    }}
                    className="ltr inline-flex items-center gap-1.5 rounded-full border border-line-2 bg-surface px-3 py-1.5 text-sm font-semibold text-ink-2 hover:bg-surface-2"
                  >
                    {/^\+?[\d\s-]+$/.test(ex) ? <Phone aria-hidden className="size-3.5" /> : <Search aria-hidden className="size-3.5" />}
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <p className="mt-10 text-sm text-muted">{t("privacyNote")}</p>
          </section>
        )}

        {result && tone && verdict && (
          <section
            ref={resultRef}
            tabIndex={-1}
            aria-live="polite"
            className={cn("rise-in mt-4 overflow-hidden rounded-[24px] border-2 outline-none", tone.line, tone.bg)}
          >
            <div className="px-6 pt-8 pb-6 text-center">
              <tone.Icon aria-hidden className={cn("mx-auto size-16", tone.fg)} strokeWidth={2.25} />
              <p className={cn("mt-3 text-sm font-bold uppercase tracking-wide", tone.fg)}>{t(verdict)}</p>
              <h1 className={cn("mt-1 text-3xl font-extrabold leading-tight tracking-tight", tone.fg)}>{pick(result as unknown as Record<string, unknown>, "headline")}</h1>
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
                    {a}
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

      <footer className="mx-auto w-full max-w-xl px-4 pb-8 text-center text-xs text-muted">
        <p>{t("checkFooter")}</p>
        <Link href="/login" className="mt-2 inline-block font-bold text-primary underline">
          {t("analystConsole")}
        </Link>
      </footer>
    </div>
  );
}
