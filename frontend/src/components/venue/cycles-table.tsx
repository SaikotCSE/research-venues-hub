import { ExternalLink, Flag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatDate, formatDateRange } from "@/lib/time";
import type { Cycle } from "@/lib/types";
import { useTimeZone } from "@/providers/timezone";

import { ProjectedBadge } from "./badges";

export function CyclesTable({ cycles, onSuggest }: { cycles: Cycle[]; onSuggest?: (cycle: Cycle) => void }) {
  const { timeZone } = useTimeZone();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <caption className="sr-only">Every edition with its milestones</caption>
        <thead className="text-left text-xs text-muted-foreground">
          <tr className="border-b">
            {["Edition", "Abstract", "Paper", "Notification", "Camera-ready", "Event", "Dates"].map((h) => (
              <th key={h} scope="col" className="whitespace-nowrap px-3 py-2 font-medium first:pl-0">
                {h}
              </th>
            ))}
            {onSuggest && (
              <th scope="col" className="px-3 py-2">
                <span className="sr-only">Actions</span>
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y">
          {cycles.map((c) => (
            <tr key={c.id}>
              <th scope="row" className="whitespace-nowrap py-2.5 pr-3 text-left font-semibold">
                {c.label}
              </th>
              {[c.abstract_deadline, c.submission_deadline, c.notification_date, c.camera_ready_date].map((d, i) => (
                <td key={i} className="tnum whitespace-nowrap px-3 py-2.5 text-muted-foreground">
                  {d ? <time dateTime={d}>{formatDate(d, timeZone)}</time> : "—"}
                </td>
              ))}
              <td className="tnum whitespace-nowrap px-3 py-2.5 text-muted-foreground">{formatDateRange(c.event_start_date, c.event_end_date)}</td>
              <td className="whitespace-nowrap px-3 py-2.5">
                <span className="flex items-center gap-1.5">
                  <ProjectedBadge projected={c.is_projected} verifiedAt={c.verified_at} />
                  {c.source_url && (
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label={`Official call for ${c.label}`}
                    >
                      <ExternalLink className="size-3.5" aria-hidden="true" />
                    </a>
                  )}
                </span>
              </td>
              {onSuggest && (
                <td className="py-2.5 pl-3 text-right">
                  <Button variant="ghost" size="xs" onClick={() => onSuggest(c)} aria-label={`Suggest a correction for ${c.label}`}>
                    <Flag aria-hidden="true" /> Correct
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
