import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { formatDate, formatDateTime } from "@/lib/time";
import type { CalendarData } from "@/lib/types";
import { useTimeZone } from "@/providers/timezone";

const KIND = {
  abstract: { label: "Abstract", tone: "amber" },
  submission: { label: "Paper", tone: "red" },
  notification: { label: "Notification", tone: "blue" },
  camera_ready: { label: "Camera-ready", tone: "green" },
} as const;

export function CalendarView({ data }: { data: CalendarData }) {
  const { timeZone } = useTimeZone();
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
      {data.months.map((m) => (
        <section key={`${m.year}-${m.month}`} className="flex flex-col rounded-xl border bg-card shadow-card" aria-labelledby={`month-${m.year}-${m.month}`}>
          <header className="flex items-center justify-between border-b px-4 py-3">
            <h3 id={`month-${m.year}-${m.month}`} className="text-sm font-semibold">
              {m.label}
            </h3>
            <span className="tnum rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">{m.events.length}</span>
          </header>
          {m.events.length ? (
            <ul className="scrollbar-thin max-h-80 flex-1 divide-y overflow-y-auto">
              {m.events.map((e, i) => (
                <li key={`${e.venue.slug}-${e.kind}-${i}`} className="flex items-center gap-3 px-4 py-2 text-sm">
                  <time dateTime={e.at} title={formatDateTime(e.at, timeZone)} className="tnum w-12 shrink-0 text-xs text-muted-foreground">
                    {formatDate(e.at, timeZone, true)}
                  </time>
                  <Link to={`/venue/${e.venue.slug}/`} className="min-w-0 flex-1 truncate font-medium hover:text-brand-text">
                    {e.venue.acronym}
                  </Link>
                  <Badge tone={KIND[e.kind].tone}>{KIND[e.kind].label}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="flex-1 px-4 py-6 text-center text-sm text-muted-foreground">No milestones</p>
          )}
        </section>
      ))}
    </div>
  );
}
