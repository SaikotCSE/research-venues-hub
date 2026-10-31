import { AlertTriangle, type LucideIcon } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export function PageContainer({ className, children, size = "wide" }: { className?: string; children: React.ReactNode; size?: "wide" | "default" | "narrow" }) {
  const width = { wide: "max-w-screen-2xl", default: "max-w-6xl", narrow: "max-w-3xl" }[size];
  return <div className={cn("mx-auto w-full px-4 py-8 sm:px-6 lg:px-8 lg:py-10", width, className)}>{children}</div>;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  icon: Icon,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  eyebrow?: React.ReactNode;
  actions?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <header className={cn("mb-8 flex flex-wrap items-end gap-x-6 gap-y-4", className)}>
      <div className="min-w-0 flex-1">
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h1 className="flex items-center gap-3 text-2xl font-semibold tracking-tight sm:text-[28px] sm:leading-9">
          {Icon && (
            <span className="grid size-9 shrink-0 place-items-center rounded-lg border bg-card shadow-card">
              <Icon className="size-[18px] text-brand-text" aria-hidden="true" />
            </span>
          )}
          {title}
        </h1>
        {description && <p className="mt-2 max-w-2xl text-[15px] leading-6 text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  children,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center rounded-xl border border-dashed bg-card/50 px-6 py-14 text-center", className)}>
      <span className="grid size-12 place-items-center rounded-xl border bg-card shadow-card">
        <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-base font-semibold">{title}</h2>
      {description && <p className="mt-1.5 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>}
      {children && <div className="mt-6 flex flex-wrap justify-center gap-2">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center rounded-xl border border-destructive/25 bg-destructive/[0.03] px-6 py-12 text-center", className)}
    >
      <AlertTriangle className="size-6 text-destructive" aria-hidden="true" />
      <h2 className="mt-3 font-semibold">Couldn’t load this</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  icon: Icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl border bg-card p-4 shadow-card", className)}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
        {Icon && <Icon className="size-4 text-muted-foreground/70" aria-hidden="true" />}
      </div>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
