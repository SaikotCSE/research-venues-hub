import { CalendarClock, CircleDot, Infinity as InfinityIcon, History, ShieldCheck, Sparkles } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import type { DeadlineStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tone = NonNullable<BadgeProps["tone"]>;

export function rankTone(core: string, quartile: string, ccf?: string): Tone {
  const best = core && core !== "Unranked" ? core : quartile || (ccf && ccf !== "Unranked" ? `CCF-${ccf}` : "");
  if (best === "A*" || best === "Q1" || best === "CCF-A") return "gold";
  if (best === "A" || best === "Q2" || best === "CCF-B") return "green";
  if (best === "B" || best === "Q3" || best === "CCF-C") return "blue";
  return "neutral";
}

export function RankBadge({ label, core, quartile, ccf, className }: { label: string; core: string; quartile: string; ccf?: string; className?: string }) {
  return (
    <Badge tone={rankTone(core, quartile, ccf)} className={className}>
      {label}
    </Badge>
  );
}

const STATUS: Record<DeadlineStatus, { label: string; tone: Tone; hint: string }> = {
  open: { label: "Open", tone: "green", hint: "The call for papers is open now" },
  upcoming: { label: "Opens soon", tone: "blue", hint: "The next submission window has not opened yet" },
  rolling: { label: "Rolling", tone: "violet", hint: "Submissions accepted year-round" },
  past: { label: "Closed", tone: "neutral", hint: "No upcoming deadline announced" },
};

export function StatusBadge({ status, className }: { status: DeadlineStatus; className?: string }) {
  const s = STATUS[status];
  return (
    <Badge tone={s.tone} className={className} title={s.hint}>
      {status === "open" ? (
        <span className="relative flex size-1.5" aria-hidden="true">
          <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-current" />
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      ) : status === "rolling" ? (
        <InfinityIcon aria-hidden="true" />
      ) : status === "upcoming" ? (
        <CalendarClock aria-hidden="true" />
      ) : (
        <CircleDot aria-hidden="true" />
      )}
      {s.label}
    </Badge>
  );
}

export function ProjectedBadge({ projected, verifiedAt, className }: { projected: boolean; verifiedAt?: string | null; className?: string }) {
  if (projected)
    return (
      <Tooltip content="Extrapolated from previous editions — confirm on the official website.">
        <Badge tone="amber" className={cn("cursor-help", className)}>
          <History aria-hidden="true" />
          Projected
        </Badge>
      </Tooltip>
    );
  return (
    <Tooltip content={verifiedAt ? `Checked against the official call` : "Dates confirmed"}>
      <Badge tone="green" className={cn("cursor-help", className)}>
        <ShieldCheck aria-hidden="true" />
        Verified
      </Badge>
    </Tooltip>
  );
}

export function TypeBadge({ type, className }: { type: string; className?: string }) {
  return (
    <Badge tone="outline" className={className}>
      {type === "Workshop/Symposium" ? "Symposium" : type}
    </Badge>
  );
}

export function NewBadge() {
  return (
    <Badge tone="brand">
      <Sparkles aria-hidden="true" />
      New
    </Badge>
  );
}
