"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "ar";

/* Every UI string, in both languages. Content from the API already arrives as *_en / *_ar pairs;
   this file only covers the chrome around it. */
const strings = {
  appName: ["ScamShield", "درع الاحتيال"],
  tagline: ["Check before you tap.", "تحقّق قبل أن تضغط."],
  teamName: ["by CipherGuard", "من فريق CipherGuard"],

  navRadar: ["Radar", "الرادار"],
  navCases: ["Cases", "الحالات"],
  navAccuracy: ["Accuracy", "الدقة"],
  navNetwork: ["Network", "الشبكة"],
  navChecker: ["Citizen checker", "فاحص الروابط"],
  navAudit: ["Audit log", "سجل التدقيق"],
  navUsers: ["Users", "المستخدمون"],
  adminOnly: ["Admin", "للمشرف"],

  auditTitle: ["Audit log", "سجل التدقيق"],
  auditSub: ["Every confirm and dismiss, newest first: who, when and why.", "كل تأكيد ورفض، الأحدث أولًا: من ومتى ولماذا."],
  colAction: ["Action", "الإجراء"],
  colReason: ["Reason", "السبب"],
  colBy: ["By", "بواسطة"],
  colWhen: ["When", "متى"],
  noDecisions: ["No decisions yet.", "لا قرارات بعد."],
  forbidden: ["Only admins can open this page.", "هذه الصفحة للمشرفين فقط."],

  usersTitle: ["Users", "المستخدمون"],
  usersSub: ["Analysts review cases. Admins also manage accounts and read the audit log.", "المحللون يراجعون الحالات. المشرفون يديرون الحسابات أيضًا ويقرؤون سجل التدقيق."],
  addUser: ["Add account", "إضافة حساب"],
  role: ["Role", "الدور"],
  created: ["Created", "تاريخ الإنشاء"],
  disabled: ["Disabled", "معطّل"],
  active: ["Active", "نشط"],
  passwordMin: ["At least 8 characters", "8 أحرف على الأقل"],
  userExists: ["That username already exists.", "اسم المستخدم موجود بالفعل."],
  userCreated: ["Account created", "تم إنشاء الحساب"],

  exportJson: ["Export evidence (JSON)", "تصدير الأدلة (JSON)"],
  pageKind_parked: ["Parked page", "صفحة محجوزة"],
  pageKind_for_sale: ["Domain for sale", "نطاق للبيع"],
  pageKind_expired: ["Expired", "منتهي"],
  pageKind_blocked: ["Blocked us", "حجب الزيارة"],
  pageKind_error: ["Error page", "صفحة خطأ"],
  pageKind_coming_soon: ["Coming soon page", "صفحة قريبًا"],
  pageKind_default_host_page: ["Default host page", "صفحة الاستضافة الافتراضية"],
  pageKind_empty: ["Empty page", "صفحة فارغة"],
  pageKindHint: ["A placeholder says nothing about the owner.", "الصفحة المؤقتة لا تقول شيئًا عن المالك."],
  navScan: ["Scan a URL", "افحص رابطًا"],
  signIn: ["Sign in", "تسجيل الدخول"],
  signOut: ["Sign out", "تسجيل الخروج"],
  skipToContent: ["Skip to content", "انتقل إلى المحتوى"],
  language: ["العربية", "English"],
  switchLang: ["Switch to Arabic", "التبديل إلى الإنجليزية"],
  textLarger: ["Larger text", "نص أكبر"],
  textNormal: ["Normal text", "نص عادي"],
  demoData: ["Demo data", "بيانات تجريبية"],
  demoDataHint: ["The API is serving seeded demo cases, not live findings.", "الواجهة تعرض حالات تجريبية، لا نتائج مباشرة."],
  liveData: ["Live", "مباشر"],
  apiOffline: ["Cannot reach the ScamShield API", "لا يمكن الوصول إلى خدمة درع الاحتيال"],
  apiOfflineHint: ["Start it with uvicorn on port 8000. This page reconnects on its own.", "شغّل الخدمة على المنفذ 8000 وستتصل الصفحة تلقائيًا."],
  retry: ["Try again", "أعد المحاولة"],
  loading: ["Loading", "جارٍ التحميل"],

  FRAUD: ["Fraud", "احتيال"],
  SUSPICIOUS: ["Suspicious", "مشبوه"],
  // LEGIT means "no warning signs", not "official": unrelated sites, parked pages and example.com score LEGIT too.
  // Same words as the API's citizen headline (backend/app/messages.py).
  LEGIT: ["No warning signs", "لا علامات تحذيرية"],
  UNKNOWN: ["Unknown", "غير معروف"],
  verdict: ["Verdict", "الحكم"],
  riskScore: ["Risk score", "درجة الخطورة"],
  outOf100: ["out of 100", "من 100"],
  targets: ["Imitates", "يقلّد"],
  noBrand: ["No brand named", "بدون علامة محددة"],

  src_lookalike: ["Lookalike domain", "نطاق مشابه"],
  src_ct: ["New certificate", "شهادة جديدة"],
  src_nrd: ["New domain", "نطاق جديد"],
  src_search: ["Search result", "نتيجة بحث"],
  src_search_ad: ["Search ad", "إعلان بحث"],
  src_maps: ["Maps listing", "قائمة خرائط"],
  src_manual: ["Analyst scan", "فحص محلل"],
  src_citizen: ["Citizen report", "بلاغ مواطن"],
  src_batch: ["Batch", "دفعة"],

  st_new: ["Needs review", "بانتظار المراجعة"],
  st_confirmed: ["Confirmed", "مؤكد"],
  st_dismissed: ["Dismissed", "مرفوض"],

  radarTitle: ["Radar", "الرادار"],
  radarLive: ["Radar running", "الرادار يعمل"],
  radarHeadline: ["The radar found {n} sites today.", "رصد الرادار {n} مواقع اليوم."],
  radarHeadlineFraud: ["{f} look like fraud.", "{f} منها تبدو احتيالية."],
  radarHeadlineNone: ["Nothing flagged yet.", "لم يُرصد شيء بعد."],
  radarSub: ["Found on its own: lookalike domains, new certificates, new registrations, Google Search and Maps. Nobody pasted anything.", "اكتُشفت تلقائيًا: نطاقات مشابهة، شهادات جديدة، تسجيلات جديدة، بحث جوجل والخرائط. لم يُدخل أحد شيئًا."],
  bySource: ["By source", "حسب المصدر"],
  allSources: ["All sources", "كل المصادر"],
  found: ["Found", "رُصد"],
  query: ["Query", "الاستعلام"],
  openCase: ["Open case", "افتح الحالة"],
  emptyRadar: ["The radar has not found anything yet. It checks every few minutes.", "لم يرصد الرادار شيئًا بعد. يفحص كل بضع دقائق."],

  casesTitle: ["Cases", "الحالات"],
  casesSub: ["Every URL the system has scored, from the radar, analysts and citizens.", "كل الروابط التي قيّمها النظام من الرادار والمحللين والمواطنين."],
  search: ["Search domain or URL", "ابحث عن نطاق أو رابط"],
  filterVerdict: ["Verdict", "الحكم"],
  filterSource: ["Source", "المصدر"],
  filterBrand: ["Brand", "العلامة"],
  filterStatus: ["Status", "الحالة"],
  all: ["All", "الكل"],
  clearFilters: ["Clear filters", "إزالة الفلاتر"],
  results: ["{n} cases", "{n} حالة"],
  noResults: ["No cases match these filters.", "لا توجد حالات تطابق هذه الفلاتر."],
  colDomain: ["Domain", "النطاق"],
  colVerdict: ["Verdict", "الحكم"],
  colSource: ["Source", "المصدر"],
  colBrand: ["Imitates", "يقلّد"],
  colFound: ["Found", "رُصد"],
  colStatus: ["Status", "الحالة"],

  backToRadar: ["Back", "رجوع"],
  caseId: ["Case", "الحالة"],
  whyFlagged: ["Why it was flagged", "لماذا تم رصده"],
  whyNotFlagged: ["What we checked", "ما الذي فحصناه"],
  reasonHint: ["Select a reason to highlight its evidence.", "اختر سببًا لتمييز دليله."],
  raisesRisk: ["raises risk", "يرفع الخطورة"],
  lowersRisk: ["lowers risk", "يخفض الخطورة"],
  evidence: ["Evidence", "الأدلة"],
  screenshot: ["Screenshot", "لقطة الشاشة"],
  screenshotHint: ["Captured on a UAE phone profile (Arabic, mobile).", "التُقطت بملف هاتف إماراتي (عربي، جوال)."],
  noScreenshot: ["No screenshot yet", "لا توجد لقطة بعد"],
  fetching: ["Visiting the page safely…", "جارٍ زيارة الصفحة بأمان…"],
  fetchFailed: ["The page could not be loaded. The URL was still scored.", "تعذّر تحميل الصفحة، ومع ذلك تم تقييم الرابط."],
  offlineSite: ["Site offline", "الموقع غير متاح"],
  redirects: ["Redirect path", "مسار التحويل"],
  noRedirects: ["Loaded directly, no redirects.", "تم التحميل مباشرة دون تحويلات."],
  pageTitle: ["Page title", "عنوان الصفحة"],
  pageText: ["What the page says", "ما تقوله الصفحة"],
  forms: ["Forms on the page", "النماذج في الصفحة"],
  noForms: ["No forms found.", "لا توجد نماذج."],
  asksFor: ["Asks for", "يطلب"],
  downloads: ["Downloads and apps", "التنزيلات والتطبيقات"],
  domain: ["Domain", "النطاق"],
  registered: ["Registered", "تاريخ التسجيل"],
  daysOld: ["{d} days before discovery", "قبل {d} يومًا من الرصد"],
  registrar: ["Registrar", "المسجّل"],
  abuseContact: ["Abuse contact", "جهة الإبلاغ"],
  hosting: ["Hosting", "الاستضافة"],
  ipAddress: ["IP address", "عنوان IP"],
  sharedHosting: ["Shared platform: age and registrar belong to the platform, not the scammer.", "منصة مشتركة: العمر والمسجّل يعودان للمنصة لا للمحتال."],
  mapsListing: ["Maps listing", "قائمة الخرائط"],
  listingName: ["Listing name", "اسم القائمة"],
  listedPhone: ["Listed phone", "الهاتف المدرج"],
  officialHelpline: ["Official helpline", "الخط الرسمي"],
  address: ["Address", "العنوان"],
  cloaking: ["Cloaking check", "فحص التخفي"],
  cloakingHint: ["Second visit as a foreign desktop browser, compared with the UAE phone visit.", "زيارة ثانية بمتصفح حاسوب أجنبي مقارنة بزيارة الهاتف الإماراتي."],
  visualMatch: ["Visual match", "تطابق بصري"],
  fingerprints: ["Site fingerprints", "بصمات الموقع"],
  trackers: ["Trackers", "أدوات التتبع"],
  contacts: ["Contacts on page", "جهات الاتصال في الصفحة"],
  scoredBy: ["Scored by {m}", "قُيّم بواسطة {m}"],
  decision: ["Analyst decision", "قرار المحلل"],
  confirm: ["Confirm fraud", "تأكيد الاحتيال"],
  dismiss: ["Dismiss", "رفض"],
  decisionReason: ["Why? This is kept in the log.", "السبب؟ يُحفظ في السجل."],
  decisionReasonPh: ["e.g. Card and OTP form on a lookalike domain", "مثال: نموذج بطاقة ورمز تحقق على نطاق مشابه"],
  decisionLog: ["Decision log", "سجل القرارات"],
  confirmedToast: ["Confirmed as fraud", "تم التأكيد كاحتيال"],
  dismissedToast: ["Dismissed", "تم الرفض"],
  cancel: ["Cancel", "إلغاء"],
  save: ["Save decision", "حفظ القرار"],
  shortcuts: ["Keys: C confirm, D dismiss, T takedown", "مفاتيح: C تأكيد، D رفض، T إزالة"],
  exportPdf: ["Export PDF", "تصدير PDF"],
  pdfSoon: ["The report could not be generated. Try again in a moment.", "تعذّر إنشاء التقرير. حاول بعد قليل."],
  takedown: ["Takedown request", "طلب إزالة"],
  takedownHint: ["Prefilled abuse email to the registrar and host, in English and Arabic.", "بريد إبلاغ معدّ مسبقًا للمسجّل والمستضيف بالإنجليزية والعربية."],
  copy: ["Copy", "نسخ"],
  copied: ["Copied", "تم النسخ"],
  openMail: ["Open in email", "افتح في البريد"],
  to: ["To", "إلى"],
  subject: ["Subject", "الموضوع"],
  close: ["Close", "إغلاق"],
  english: ["English", "الإنجليزية"],
  arabic: ["Arabic", "العربية"],

  scanTitle: ["Scan a URL", "افحص رابطًا"],
  scanHint: ["Paste any link. You get a quick verdict now and the full evidence in about a minute.", "الصق أي رابط. ستحصل على حكم سريع الآن والأدلة الكاملة خلال دقيقة."],
  scanButton: ["Scan", "افحص"],
  scanning: ["Scanning…", "جارٍ الفحص…"],
  batchTitle: ["Batch", "دفعة"],
  batchHint: ["One URL per line. You get a verdict for each.", "رابط في كل سطر. تحصل على حكم لكل رابط."],
  batchButton: ["Score all", "قيّم الكل"],
  downloadCsv: ["Download CSV", "تنزيل CSV"],

  accuracyTitle: ["Accuracy", "الدقة"],
  accuracySub: ["Measured on a held-out set of real phishing and legitimate URLs the model never saw in training.", "قيست على مجموعة اختبار من روابط تصيّد حقيقية وروابط سليمة لم يرها النموذج أثناء التدريب."],
  precision: ["Precision", "الدقة (Precision)"],
  precisionHint: ["Of everything we called fraud, how much really was.", "من كل ما وصفناه بالاحتيال، كم كان احتيالًا فعلًا."],
  recall: ["Recall", "الاستدعاء (Recall)"],
  recallHint: ["Of all real fraud, how much we caught.", "من كل الاحتيال الحقيقي، كم اكتشفنا."],
  fpr: ["False-positive rate", "نسبة الإنذارات الكاذبة"],
  fprHint: ["Legitimate sites we wrongly flagged.", "مواقع سليمة وصفناها خطأً بالاحتيال."],
  f1: ["F1", "F1"],
  f1Hint: ["Balance of precision and recall.", "التوازن بين الدقة والاستدعاء."],
  confusion: ["Confusion matrix", "مصفوفة الالتباس"],
  actualFraud: ["Actually fraud", "احتيال فعلي"],
  actualLegit: ["Actually legitimate", "سليم فعلي"],
  calledFraud: ["Called fraud", "وُصف بالاحتيال"],
  calledLegit: ["Called legitimate", "وُصف بالسليم"],
  caught: ["caught", "اكتُشف"],
  missed: ["missed", "فات"],
  falseAlarms: ["false alarms", "إنذار كاذب"],
  correctlyCleared: ["correctly cleared", "سُلّم بصحة"],
  bySourceAcc: ["By dataset", "حسب مجموعة البيانات"],
  correct: ["correct", "صحيح"],
  uaeOfficial: ["UAE official pages wrongly flagged", "صفحات رسمية إماراتية وُصفت خطأً"],
  of: ["of", "من"],
  dataset: ["Test set", "مجموعة الاختبار"],
  modelVersion: ["Model", "النموذج"],
  evaluatedAt: ["Evaluated", "تاريخ التقييم"],
  honestLimit: ["Honest limit", "حدود واضحة"],
  honestLimitText: ["These numbers are URL-only, with phishing feeds switched off, so they show detection rather than lookup. Phishing homepages with ordinary names are the main misses; the page fetch catches most of those.", "هذه الأرقام تعتمد على الرابط فقط مع إيقاف قوائم التصيّد، فتعكس الاكتشاف لا البحث في القوائم. أكثر ما يفوتنا صفحات تصيّد بأسماء عادية، ويكشف معظمها فحص الصفحة."],

  graphTitle: ["Scam network", "شبكة الاحتيال"],
  graphSub: ["Domains linked by shared infrastructure: same server, same registration day, same favicon, template, tracker or contact.", "نطاقات مرتبطة ببنية مشتركة: نفس الخادم، نفس يوم التسجيل، نفس الأيقونة أو القالب أو أداة التتبع أو جهة الاتصال."],
  edge_same_ip: ["Same IP", "نفس IP"],
  edge_same_registration_day: ["Registered same day", "سُجّل في اليوم نفسه"],
  edge_same_final_host: ["Same destination", "نفس الوجهة"],
  edge_same_favicon: ["Same favicon", "نفس الأيقونة"],
  edge_same_template: ["Same template", "نفس القالب"],
  edge_same_tracker: ["Same tracker", "نفس أداة التتبع"],
  edge_same_contact: ["Same contact", "نفس جهة الاتصال"],
  noEdges: ["No shared infrastructure found between the current cases.", "لم تُرصد بنية مشتركة بين الحالات الحالية."],
  links: ["{n} links", "{n} روابط"],

  loginTitle: ["Sign in to the analyst console", "تسجيل الدخول إلى لوحة المحلل"],
  loginSub: ["Abu Dhabi Police pilot. Demo accounts: admin / admin123 and analyst / analyst123.", "تجربة شرطة أبوظبي. حسابات تجريبية: admin / admin123 و analyst / analyst123."],
  username: ["Username", "اسم المستخدم"],
  password: ["Password", "كلمة المرور"],
  loginFailed: ["That username or password is not right.", "اسم المستخدم أو كلمة المرور غير صحيحة."],
  goCitizen: ["Just want to check a link? Use the public checker.", "تريد فحص رابط فقط؟ استخدم الفاحص العام."],
  role_admin: ["Admin", "مشرف"],
  role_analyst: ["Analyst", "محلل"],

  checkTitle: ["Is this link or number safe?", "هل هذا الرابط أو الرقم آمن؟"],
  checkSub: ["Paste a link or a phone number from a message. We check it against official UAE sites and helplines.", "الصق رابطًا أو رقم هاتف من رسالة. نقارنه بالمواقع والخطوط الرسمية في الإمارات."],
  checkPlaceholder: ["Link or phone number", "رابط أو رقم هاتف"],
  checkButton: ["Check", "تحقّق"],
  checking: ["Checking…", "جارٍ التحقق…"],
  checkAgain: ["Check another", "تحقّق من آخر"],
  whatToDo: ["What to do now", "ماذا تفعل الآن"],
  whyWeThink: ["Why we think so", "لماذا نعتقد ذلك"],
  readAloud: ["Read aloud", "اقرأ بصوت عالٍ"],
  stopReading: ["Stop", "إيقاف"],
  checkedInput: ["You checked", "تحققت من"],
  tryExample: ["Try an example", "جرّب مثالًا"],
  privacyNote: ["We only look at the link or number. Nothing you type is stored with your name.", "نفحص الرابط أو الرقم فقط. لا نحفظ ما تكتبه مع اسمك."],
  checkFooter: ["A CipherGuard project for the 42 Abu Dhabi × Abu Dhabi Police hackathon. Proposed pilot, not an official police service.", "مشروع CipherGuard لهاكاثون 42 أبوظبي × شرطة أبوظبي. تجربة مقترحة، ليست خدمة شرطية رسمية."],
  analystConsole: ["Analyst console", "لوحة المحلل"],
} as const;

export type StringKey = keyof typeof strings;

type Ctx = {
  lang: Lang;
  dir: "ltr" | "rtl";
  setLang: (l: Lang) => void;
  toggleLang: () => void;
  t: (key: StringKey, vars?: Record<string, string | number>) => string;
  /** Pick the *_en / *_ar field from an API object. */
  pick: (obj: Record<string, unknown>, base: string) => string;
  textSize: "normal" | "large";
  setTextSize: (s: "normal" | "large") => void;
};

const LangContext = createContext<Ctx | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [textSize, setTextSizeState] = useState<"normal" | "large">("normal");

  // Read the saved choice after hydration so server and first client render match.
  useEffect(() => {
    const saved = window.localStorage.getItem("scamshield.lang");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time read of persisted preference
    if (saved === "ar" || saved === "en") setLangState(saved);
    const ts = window.localStorage.getItem("scamshield.textsize");
    if (ts === "large") setTextSizeState("large");
  }, []);

  // Only sync the document here. Persisting happens in the setters, so React's
  // development double-run of effects can never overwrite the saved choice.
  useEffect(() => {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => {
    document.documentElement.dataset.text = textSize;
  }, [textSize]);

  const setLang = useCallback((l: Lang) => {
    window.localStorage.setItem("scamshield.lang", l);
    setLangState(l);
  }, []);
  const setTextSize = useCallback((s: "normal" | "large") => {
    window.localStorage.setItem("scamshield.textsize", s);
    setTextSizeState(s);
  }, []);

  const t = useCallback(
    (key: StringKey, vars?: Record<string, string | number>) => {
      const pair = strings[key] as readonly [string, string];
      let s = lang === "ar" ? pair[1] : pair[0];
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
      return s;
    },
    [lang],
  );

  const pick = useCallback(
    (obj: Record<string, unknown>, base: string) => {
      const v = obj[`${base}_${lang}`] ?? obj[`${base}_en`];
      return typeof v === "string" ? v : "";
    },
    [lang],
  );

  const value = useMemo<Ctx>(
    () => ({
      lang,
      dir: lang === "ar" ? "rtl" : "ltr",
      setLang,
      toggleLang: () => setLang(lang === "ar" ? "en" : "ar"),
      t,
      pick,
      textSize,
      setTextSize,
    }),
    [lang, t, pick, textSize, setLang, setTextSize],
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside LangProvider");
  return ctx;
}
