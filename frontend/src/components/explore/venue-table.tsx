import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Link } from "react-router-dom";

import { RankBadge, StatusBadge } from "@/components/venue/badges";
import { CompareToggle } from "@/components/venue/compare-toggle";
import { CountdownText, DeadlineTime } from "@/components/venue/countdown";
import { StarButton } from "@/components/venue/star-button";
import { VenueMark } from "@/components/venue/venue-mark";
import type { VenueCard } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLUMNS: { key: string; label: string; sort?: string; defaultDir?: "asc" | "desc"; align?: "right"; className?: string }[] = [
  { key: "venue", label: "Venue", sort: "name", defaultDir: "asc" },
  { key: "rank", label: "Rank", sort: "rank", defaultDir: "desc" },
  { key: "if", label: "IF", sort: "impact_factor", defaultDir: "desc", align: "right", className: "max-md:hidden" },
  { key: "h5", label: "h5", sort: "h5_index", defaultDir: "desc", align: "right", className: "max-md:hidden" },
  { key: "acc", label: "Accept.", sort: "acceptance_rate", defaultDir: "asc", align: "right", className: "max-lg:hidden" },
  { key: "deadline", label: "Next deadline", sort: "deadline", defaultDir: "asc" },
  { key: "status", label: "Status", className: "max-sm:hidden" },
  { key: "actions", label: "Actions", className: "w-[84px]" },
];

export function VenueTable({
  venues,
  sort,
  dir,
  onSort,
}: {
  venues: VenueCard[];
  sort: string;
  dir: string;
  onSort: (sort: string, dir: "asc" | "desc") => void;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border bg-card shadow-card">
      <table className="w-full min-w-[640px] text-sm">
        <caption className="sr-only">Venues matching the current filters. Column headers sort the table.</caption>
        <thead className="border-b bg-surface text-xs text-muted-foreground">
          <tr>
            {COLUMNS.map((c) => {
              const active = c.sort && sort === c.sort;
              const currentDir = active ? dir || c.defaultDir : undefined;
              return (
                <th
                  key={c.key}
                  scope="col"
                  className={cn("whitespace-nowrap px-3 py-2.5 text-left font-medium first:pl-4 last:pr-4", c.align === "right" && "text-right", c.className)}
                  aria-sort={active ? (currentDir === "asc" ? "ascending" : "descending") : undefined}
                >
                  {c.key === "actions" ? (
                    <span className="sr-only">{c.label}</span>
                  ) : c.sort ? (
                    <button
                      type="button"
                      className={cn("inline-flex items-center gap-1 rounded hover:text-foreground", active && "text-foreground")}
                      onClick={() => onSort(c.sort!, active ? (currentDir === "asc" ? "desc" : "asc") : c.defaultDir!)}
                    >
                      {c.label}
                      {active ? (
                        currentDir === "asc" ? (
                          <ArrowUp className="size-3" aria-hidden="true" />
                        ) : (
                          <ArrowDown className="size-3" aria-hidden="true" />
                        )
                      ) : (
                        <ArrowUpDown className="size-3 opacity-40" aria-hidden="true" />
                      )}
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y">
          {venues.map((v) => (
            <tr key={v.slug} className="group transition-colors hover:bg-accent/40">
              <td className="py-2.5 pl-4 pr-3">
                <div className="flex items-center gap-3">
                  <VenueMark acronym={v.acronym} size="sm" />
                  <div className="min-w-0">
                    <Link to={`/venue/${v.slug}/`} className="font-semibold hover:text-brand-text">
                      {v.acronym}
                    </Link>
                    <p className="max-w-[18rem] truncate text-xs text-muted-foreground" title={v.name}>
                      {v.venue_type === "Journal" ? "Journal · " : ""}
                      {v.name}
                    </p>
                  </div>
                </div>
              </td>
              <td className="px-3 py-2.5">
                <RankBadge label={v.rank_label} core={v.core_rank} quartile={v.quartile} ccf={v.ccf_rank} />
              </td>
              <td className="tnum px-3 py-2.5 text-right max-md:hidden">
                {v.impact_factor != null ? v.impact_factor.toFixed(1) : <span className="text-muted-foreground">—</span>}
              </td>
              <td className="tnum px-3 py-2.5 text-right max-md:hidden">{v.h5_index ?? <span className="text-muted-foreground">—</span>}</td>
              <td className="tnum px-3 py-2.5 text-right max-lg:hidden">
                {v.acceptance_rate != null ? `${v.acceptance_rate.toFixed(0)}%` : <span className="text-muted-foreground">—</span>}
              </td>
              <td className="whitespace-nowrap px-3 py-2.5">
                {v.next_deadline ? (
                  <div>
                    <CountdownText at={v.next_deadline.at} className="text-[13px]" />
                    <DeadlineTime at={v.next_deadline.at} showZone={false} className="block text-xs text-muted-foreground" />
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground">{v.is_rolling ? "Rolling" : "Not announced"}</span>
                )}
              </td>
              <td className="px-3 py-2.5 max-sm:hidden">
                <StatusBadge status={v.status} />
              </td>
              <td className="py-2.5 pl-3 pr-4">
                <div className="flex justify-end">
                  <CompareToggle slug={v.slug} acronym={v.acronym} />
                  <StarButton slug={v.slug} acronym={v.acronym} starred={v.starred} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
