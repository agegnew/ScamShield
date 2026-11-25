"use client";

import useSWR from "swr";
import { apiFetch, ApiError, type CaseSummary } from "./api";
import type { Lang } from "./i18n";

/* Radar v2 (docs/radar-ui.md). The backend adds these fields and endpoints next;
   until then the page derives what it can from today's data and shows the run
   scope as a labelled preview built from the plan's sample JSON. */

export type Pair = readonly [string, string];
export const L = (p: Pair, lang: Lang) => (lang === "ar" ? p[1] : p[0]);

export type RadarItem = CaseSummary & {
  brand_category?: string | null;
  source_details?: Record<string, unknown> | null;
};

export type RunSource = { name: string; status: "waiting" | "running" | "done" | "skipped" | "failed"; checked?: number; total?: number | null; new?: number; note?: string };
export type RadarRun = {
  id: string;
  trigger: "manual" | "schedule";
  started_by?: string | null;
  status: "running" | "done" | "failed";
  started_at: string;
  finished_at: string | null;
  sources: RunSource[];
  pages: { checked: number; total: number };
  verdicts: { FRAUD: number; SUSPICIOUS: number; LEGIT: number };
  error: string | null;
};
export type RadarStatus = {
  running: boolean;
  run: RadarRun | null;
  schedule?: { enabled: boolean; time: string; timezone: string; next_run_at: string };
  sources?: { name: string; enabled: boolean; needs_key: string | null; last_run_at: string | null; last_new: number }[];
};

/* ---- tabs: how it was found ---- */
export const TABS: { id: string; sources: string[]; label: Pair; explain: Pair }[] = [
  { id: "all", sources: [], label: ["All", "الكل"], explain: ["Every site the radar found.", "كل المواقع التي رصدها الرادار."] },
  {
    id: "lookalike",
    sources: ["lookalike"],
    label: ["Lookalike domains", "نطاقات مشابهة"],
    explain: ["Spelling tricks on official names that someone has registered.", "حيل إملائية على أسماء رسمية سجّلها أحدهم."],
  },
  {
    id: "ct",
    sources: ["ct"],
    label: ["New certificates", "شهادات أمان جديدة"],
    explain: ["A new HTTPS certificate was issued for a name containing a brand.", "صدرت شهادة HTTPS جديدة لاسم يحتوي علامة تجارية."],
  },
  {
    id: "nrd",
    sources: ["nrd"],
    label: ["New domains", "نطاقات مسجلة حديثًا"],
    explain: ["Registered in the last days with a brand name in it.", "سُجّلت في الأيام الأخيرة وتحمل اسم علامة تجارية."],
  },
  {
    id: "search",
    sources: ["search", "search_ad"],
    label: ["Search & ads", "البحث والإعلانات"],
    explain: ["Google results and paid ads for what victims type.", "نتائج جوجل والإعلانات المدفوعة لما يبحث عنه الضحايا."],
  },
  { id: "maps", sources: ["maps"], label: ["Maps", "الخرائط"], explain: ["Google Maps listings that use a brand name.", "قوائم خرائط جوجل التي تستخدم اسم علامة تجارية."] },
];

/* ---- chips: who it imitates ---- */
export const CATEGORIES: Record<string, Pair> = {
  government: ["Government services", "الخدمات الحكومية"],
  police: ["Police & fines", "الشرطة والمخالفات"],
  transport: ["Roads, tolls & parking", "الطرق والرسوم والمواقف"],
  bank: ["Banks & payments", "البنوك والدفع"],
  delivery: ["Delivery & post", "التوصيل والبريد"],
  utility: ["Electricity & water", "الكهرباء والمياه"],
  telecom: ["Telecom", "الاتصالات"],
  shopping: ["Shopping & offers", "التسوق والعروض"],
  travel: ["Airlines & travel", "الطيران والسفر"],
  none: ["No brand named", "بدون علامة"],
};

/* ---- lookalike trick labels ---- */
const VARIANTS: [string[], Pair][] = [
  [["addition", "dictionary"], ["Extra word", "كلمة مضافة"]],
  [["hyphenation"], ["Added hyphen", "شرطة مضافة"]],
  [["omission"], ["Letter missing", "حرف ناقص"]],
  [["insertion", "repetition"], ["Extra letter", "حرف زائد"]],
  [["replacement", "bitsquatting"], ["Letter changed", "حرف مُبدّل"]],
  [["transposition"], ["Letters swapped", "أحرف مقلوبة"]],
  [["vowel-swap"], ["Vowel changed", "حرف علة مُبدّل"]],
  [["homoglyph"], ["Look-alike letter", "حرف شبيه"]],
  [["tld-swap"], ["Different ending", "امتداد مختلف"]],
];
export function variantLabel(v: unknown): Pair | null {
  if (typeof v !== "string" || !v) return null;
  return VARIANTS.find(([keys]) => keys.includes(v))?.[1] ?? ["Similar name", "اسم مشابه"];
}

export const SOURCE_NAMES: Record<string, Pair> = {
  lookalikes: ["Lookalike domains", "نطاقات مشابهة"],
  lookalike: ["Lookalike domains", "نطاقات مشابهة"],
  ct: ["New certificates", "شهادات أمان جديدة"],
  nrd: ["New domains", "نطاقات مسجلة حديثًا"],
  search: ["Search & ads", "البحث والإعلانات"],
  maps: ["Maps", "الخرائط"],
};

/* ---- status: real endpoint if it exists, otherwise a labelled preview ---- */
export const SAMPLE_STATUS: RadarStatus = {
  running: true,
  run: {
    id: "run-sample",
    trigger: "manual",
    started_by: "analyst",
    status: "running",
    started_at: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
    finished_at: null,
    sources: [
      { name: "lookalikes", status: "running", checked: 41200, total: 56958, new: 280 },
      { name: "ct", status: "done", checked: 46, total: 46, new: 18 },
      { name: "nrd", status: "done", checked: 1, total: 1, new: 4 },
      { name: "search", status: "waiting" },
      { name: "maps", status: "waiting" },
    ],
    pages: { checked: 41, total: 312 },
    verdicts: { FRAUD: 9, SUSPICIOUS: 14, LEGIT: 18 },
    error: null,
  },
  schedule: { enabled: true, time: "03:00", timezone: "Asia/Dubai", next_run_at: "2026-11-26T03:00:00+04:00" },
};

export function useRadarStatus() {
  return useSWR<{ status: RadarStatus; preview: boolean }>(
    "/api/radar/status",
    async (path: string) => {
      try {
        return { status: await apiFetch<RadarStatus>(path), preview: false };
      } catch (e) {
        if (e instanceof ApiError && (e.status === 404 || e.status === 405)) return { status: SAMPLE_STATUS, preview: true };
        throw e;
      }
    },
    { refreshInterval: (d) => (d?.preview ? 0 : d?.status.running ? 2000 : 30000), revalidateOnFocus: false },
  );
}

export async function startRadar(sources?: string[]) {
  return apiFetch<{ run: RadarRun }>("/api/radar/run", { method: "POST", body: JSON.stringify(sources ? { sources } : {}) });
}
