import { useClock, useNow } from "@/hooks/use-now";
import { compactCountdown, countdown, formatAoE, formatDateTime, pad, urgency, zoneLabel } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useTimeZone } from "@/providers/timezone";

import { Tooltip } from "../ui/tooltip";

const URGENCY_TEXT = {
  closed: "text-muted-foreground",
  critical: "text-rose-700 dark:text-rose-400",
  soon: "text-orange-700 dark:text-orange-400",
  normal: "text-foreground",
};

/** "12d 04h 33m" ticking every second, colour-coded by urgency. */
export function CountdownText({ at, className, seconds = false }: { at: string; className?: string; seconds?: boolean }) {
  // Re-render only when the visible text (or urgency) changes — once a minute for far-off deadlines.
  const snapshot = useClock((now) => {
    const parts = countdown(at, now);
    const label = seconds && !parts.done ? `${parts.days}d ${pad(parts.hours)}h ${pad(parts.minutes)}m ${pad(parts.seconds)}s` : compactCountdown(parts);
    return `${urgency(at, now)}|${label}`;
  });
  const [u, text] = snapshot.split("|") as [keyof typeof URGENCY_TEXT, string];
  return (
    <span className={cn("tnum font-semibold", URGENCY_TEXT[u], className)} role="timer" aria-live="off">
      {text}
    </span>
  );
}

/** Large segmented countdown for the venue page. */
export function CountdownBlocks({ at, className }: { at: string; className?: string }) {
  const now = useNow();
  const p = countdown(at, now);
  const u = urgency(at, now);
  const units = [
    ["days", p.days],
    ["hours", p.hours],
    ["min", p.minutes],
    ["sec", p.seconds],
  ] as const;
  if (p.done) return <p className={cn("text-2xl font-semibold text-muted-foreground", className)}>Deadline passed</p>;
  return (
    <div className={cn("flex gap-2", className)} role="timer" aria-label={`${p.days} days ${p.hours} hours ${p.minutes} minutes remaining`}>
      {units.map(([label, value]) => (
        <div
          key={label}
          className={cn(
            "flex min-w-[3.75rem] flex-col items-center rounded-xl border bg-background/60 px-2 py-2 shadow-sm backdrop-blur",
            u === "critical" && "border-rose-300/60 dark:border-rose-500/30",
          )}
        >
          <span className={cn("tnum text-2xl font-bold leading-8 tracking-tight sm:text-[28px]", URGENCY_TEXT[u])}>
            {label === "days" ? value : pad(value)}
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
        </div>
      ))}
    </div>
  );
}

/** Deadline in the visitor's zone, with the AoE equivalent in a tooltip. */
export function DeadlineTime({ at, className, showZone = true }: { at: string; className?: string; showZone?: boolean }) {
  const { timeZone } = useTimeZone();
  return (
    <Tooltip content={formatAoE(at)}>
      <time dateTime={at} className={cn("tnum cursor-help", className)}>
        {formatDateTime(at, timeZone)}
        {showZone && <span className="text-muted-foreground"> {zoneLabel(timeZone, new Date(at))}</span>}
      </time>
    </Tooltip>
  );
}
