import { Link } from "react-router-dom";

import { Tooltip } from "@/components/ui/tooltip";
import { formatDate, formatDateTime } from "@/lib/time";
import type { TimelineData } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useTimeZone } from "@/providers/timezone";

const SEGMENT = {
  open: { label: "Call for papers open", className: "bg-sky-400/80 dark:bg-sky-500/60" },
  review: { label: "Under review", className: "bg-amber-400/80 dark:bg-amber-500/60" },
  camera: { label: "Camera-ready", className: "bg-emerald-400/80 dark:bg-emerald-500/60" },
  event: { label: "Event", className: "bg-violet-500 dark:bg-violet-400" },
} as const;

export function TimelineView({ data }: { data: TimelineData }) {
  const { timeZone } = useTimeZone();
  return (
    <div className="rounded-xl border bg-card shadow-card">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b px-4 py-3 text-xs text-muted-foreground">
        {Object.entries(SEGMENT).map(([key, s]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className={cn("h-2.5 w-5 rounded-sm", s.className)} aria-hidden="true" />
            {s.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rotate-45 rounded-[2px] bg-rose-500" aria-hidden="true" />
          Deadline
        </span>
        {data.rolling_hidden > 0 && <span className="ml-auto">{data.rolling_hidden} rolling journals hidden</span>}
      </div>
      <div className="scrollbar-thin overflow-x-auto">
        <div className="min-w-[760px]">
          <div className="grid grid-cols-[150px_1fr] border-b text-[11px] font-medium text-muted-foreground sm:grid-cols-[190px_1fr]">
            <div className="px-4 py-2">Venue</div>
            <div className="relative h-8">
              {data.ticks.map((t) => (
                <span key={`${t.label}-${t.left}`} className="absolute top-2 -translate-x-1/2 whitespace-nowrap" style={{ left: `${t.left}%` }}>
                  {t.label}
                  {t.year ? <span className="ml-0.5 text-foreground/70">’{String(t.year).slice(2)}</span> : null}
                </span>
              ))}
            </div>
          </div>
          <ol className="divide-y" aria-label="Venue timelines">
            {data.rows.map((row) => (
              <li key={row.venue.slug} className="grid grid-cols-[150px_1fr] items-center hover:bg-accent/30 sm:grid-cols-[190px_1fr]">
                <div className="min-w-0 px-4 py-2.5">
                  <Link to={`/venue/${row.venue.slug}/`} className="block truncate text-sm font-semibold hover:text-brand-text">
                    {row.venue.acronym}
                  </Link>
                  <p className="truncate text-[11px] text-muted-foreground">
                    {row.venue.rank_label}
                    {row.cycle.is_projected ? " · projected" : ""}
                  </p>
                  <span className="sr-only">{row.summary}</span>
                </div>
                <div className="relative h-11" aria-hidden="true">
                  {data.ticks.map((t) => (
                    <span key={t.left} className="absolute inset-y-0 w-px bg-border/60" style={{ left: `${t.left}%` }} />
                  ))}
                  <span className="absolute inset-y-0 z-10 w-0.5 bg-rose-500/70" style={{ left: `${data.today}%` }} />
                  {row.segments.map((s) => (
                    <Tooltip key={s.kind} content={`${s.label}: ${formatDate(s.start)} – ${formatDate(s.end)}`}>
                      <span
                        className={cn("absolute top-1/2 h-3 -translate-y-1/2 rounded-full", SEGMENT[s.kind].className)}
                        style={{ left: `${s.left}%`, width: `${s.width}%` }}
                      />
                    </Tooltip>
                  ))}
                  {row.markers.map((m) => (
                    <Tooltip key={m.label} content={`${m.label}: ${formatDateTime(m.at, timeZone)}`}>
                      <span
                        className="absolute top-1/2 z-20 size-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-[2px] bg-rose-500 ring-2 ring-card"
                        style={{ left: `${m.left}%` }}
                      />
                    </Tooltip>
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
