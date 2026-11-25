"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight, Puzzle, Search } from "lucide-react";
import { useLang } from "@/lib/i18n";
import { L } from "@/lib/radar";
import { LangToggle } from "@/components/shell/AppShell";

/* Public demo page: the 1-minute walkthrough of the live product, for judges and anyone with the link. */
export default function DemoPage() {
  const { lang } = useLang();
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/check" className="flex items-center gap-2">
          <Image src="/icon-256.png" alt="" width={36} height={36} className="size-9 rounded-xl" />
          <span className="font-extrabold text-ink">ScamShield</span>
        </Link>
        <LangToggle />
      </header>

      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 pb-12">
        <p className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1 text-sm font-bold text-primary">
          {L(["Demo · 1 minute", "عرض توضيحي · دقيقة واحدة"], lang)}
        </p>
        <h1 className="mt-3 text-3xl font-extrabold leading-tight tracking-tight text-ink sm:text-4xl">
          {L(["ScamShield finds UAE scam websites before they find victims", "درع الاحتيال يكشف مواقع النصب في الإمارات قبل أن تصل إلى الضحايا"], lang)}
        </h1>
        <p className="mt-2 max-w-3xl text-ink-2">
          {L(
            ["A screen recording of the live system: checking a scam SMS, the browser extension blocking a fake site, and the Abu Dhabi Police console with its evidence. Arabic subtitles.", "تسجيل شاشة للنظام الفعلي: فحص رسالة احتيال، وإضافة المتصفح وهي تحظر موقعًا مزيفًا، ولوحة شرطة أبوظبي مع الأدلة. مع ترجمة عربية."],
            lang,
          )}
        </p>

        <div className="mt-6 overflow-hidden rounded-[22px] border border-line bg-black shadow-[0_30px_60px_-30px_rgba(30,27,46,0.55)]">
          <video controls playsInline preload="metadata" poster="/scamshield-demo.jpg" className="aspect-video w-full">
            <source src="/scamshield-demo.mp4" type="video/mp4" />
          </video>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/check" className="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-5 font-bold text-primary-ink hover:opacity-90">
            <Search aria-hidden className="size-4" />
            {L(["Try the checker", "جرّب الفاحص"], lang)}
          </Link>
          <Link href="/extension" className="inline-flex h-11 items-center gap-2 rounded-full border border-line-2 bg-surface px-5 font-bold text-ink hover:bg-surface-2">
            <Puzzle aria-hidden className="size-4" />
            {L(["Get the extension", "احصل على الإضافة"], lang)}
          </Link>
          <Link href="/" className="inline-flex h-11 items-center gap-2 rounded-full border border-line-2 bg-surface px-5 font-bold text-ink hover:bg-surface-2">
            {L(["Analyst console", "لوحة المحللين"], lang)}
            <ArrowUpRight aria-hidden className="size-4 rtl:-scale-x-100" />
          </Link>
        </div>
      </main>
    </div>
  );
}
