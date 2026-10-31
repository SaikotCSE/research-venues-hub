import { Check } from "lucide-react";

import { formatDate, formatDateTime } from "@/lib/time";
import type { VenueDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useTimeZone } from "@/providers/timezone";

export function Milestones({ steps, label }: { steps: VenueDetail["steps"]; label: string }) {
  const { timeZone } = useTimeZone();
  if (!steps.length) return null;
  return (
    <ol className="grid gap-4 sm:flex sm:gap-0" aria-label={`${label} milestones`}>
      {steps.map((s, i) => (
        <li
          key={s.label}
          className="relative flex items-start gap-3 sm:flex-1 sm:flex-col sm:items-center sm:text-center"
          aria-current={s.state === "current" ? "step" : undefined}
        >
          {i < steps.length - 1 && (
            <span
              aria-hidden="true"
              className={cn(
                "absolute left-[11px] top-7 h-[calc(100%-4px)] w-0.5 sm:left-[calc(50%+14px)] sm:top-3 sm:h-0.5 sm:w-[calc(100%-28px)]",
                s.state === "done" ? "bg-primary" : "bg-border",
              )}
            />
          )}
          <span
            aria-hidden="true"
            className={cn(
              "relative z-10 grid size-6 shrink-0 place-items-center rounded-full text-[11px] font-bold",
              s.state === "done" && "bg-primary text-primary-foreground",
              s.state === "current" &&
                "bg-background text-brand-text ring-[3px] ring-primary/30 ring-offset-0 [box-shadow:inset_0_0_0_2px_hsl(var(--primary))]",
              s.state === "upcoming" && "border bg-muted text-muted-foreground",
            )}
          >
            {s.state === "done" ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
          </span>
          <div className="sm:mt-2.5">
            <p className={cn("text-[13px] font-semibold", s.state === "current" && "text-brand-text", s.state === "done" && "text-muted-foreground")}>
              {s.label}
              <span className="sr-only"> ({s.state})</span>
            </p>
            <p className="tnum text-xs text-muted-foreground">{s.is_date ? formatDate(s.when) : formatDateTime(s.when, timeZone)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
