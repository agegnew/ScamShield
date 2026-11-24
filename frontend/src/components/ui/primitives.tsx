"use client";

import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Loader2, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLang } from "@/lib/i18n";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg";

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean }>(
  ({ className, variant = "primary", size = "md", loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-bold transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none select-none",
        size === "sm" && "h-9 px-3.5 text-sm",
        size === "md" && "h-11 px-5 text-sm",
        size === "lg" && "h-14 px-7 text-base",
        variant === "primary" && "bg-primary text-primary-ink hover:bg-[#5b21b6] shadow-[0_6px_16px_-8px_rgba(109,40,217,0.6)]",
        variant === "secondary" && "bg-primary-soft text-primary hover:bg-primary-soft-2",
        variant === "outline" && "border border-line-2 bg-surface text-ink hover:bg-surface-2",
        variant === "ghost" && "text-ink-2 hover:bg-surface-2",
        variant === "danger" && "bg-fraud text-white hover:bg-[#a51818]",
        className,
      )}
      {...props}
    >
      {loading && <Loader2 aria-hidden className="size-4 animate-spin" />}
      {children}
    </button>
  ),
);
Button.displayName = "Button";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-11 w-full rounded-xl border border-line-2 bg-surface px-3.5 text-ink placeholder:text-muted/80 transition-colors focus:border-primary disabled:opacity-60",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full rounded-xl border border-line-2 bg-surface px-3.5 py-2.5 text-ink placeholder:text-muted/80 transition-colors focus:border-primary disabled:opacity-60",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 rounded-xl border border-line-2 bg-surface px-3 text-sm font-semibold text-ink transition-colors focus:border-primary",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Panel({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <section className={cn("rounded-[16px] border border-line bg-surface", className)} {...props}>
      {children}
    </section>
  );
}

export function PanelTitle({ children, className, hint }: { children: React.ReactNode; className?: string; hint?: string }) {
  return (
    <div className={cn("flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1", className)}>
      <h2 className="text-base font-extrabold text-ink">{children}</h2>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-lg bg-surface-2", className)} />;
}

export function KeyValue({ k, v, mono, className }: { k: string; v: React.ReactNode; mono?: boolean; className?: string }) {
  return (
    <div className={cn("grid grid-cols-[minmax(7rem,30%)_1fr] gap-3 py-2 text-sm", className)}>
      <dt className="text-muted">{k}</dt>
      <dd className={cn("min-w-0 break-words text-ink", mono && "ltr font-semibold tabular-nums")}>{v ?? "—"}</dd>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useLang();
  const msg = error instanceof Error ? error.message : String(error);
  const offline = /fetch|network|failed/i.test(msg);
  return (
    <div role="alert" className="rounded-[16px] border border-line bg-surface p-8 text-center">
      <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-surface-2 text-ink-2">
        <WifiOff aria-hidden className="size-6" />
      </div>
      <p className="font-extrabold text-ink">{offline ? t("apiOffline") : msg}</p>
      {offline && <p className="mt-1 text-sm text-muted">{t("apiOfflineHint")}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          {t("retry")}
        </Button>
      )}
    </div>
  );
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="inline-grid min-w-5 place-items-center rounded-md border border-line-2 bg-surface-2 px-1 font-sans text-[11px] font-bold text-ink-2">{children}</kbd>;
}
