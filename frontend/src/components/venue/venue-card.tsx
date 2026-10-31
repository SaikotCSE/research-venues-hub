import { Eye, MapPin, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tooltip } from "@/components/ui/tooltip";
import * as React from "react";

import { useMinute } from "@/hooks/use-now";
import type { VenueCard as Venue } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ProjectedBadge, RankBadge, StatusBadge } from "./badges";
import { CompareToggle } from "./compare-toggle";
import { CountdownText, DeadlineTime } from "./countdown";
import { StarButton } from "./star-button";
import { VenueMark } from "./venue-mark";

export function deadlineProgress(v: Pick<Venue, "next_deadline" | "next_cycle">, now: number) {
  if (!v.next_deadline) return null;
  const end = new Date(v.next_deadline.at).getTime();
  const startIso = v.next_cycle?.submission_open_date;
  const start = startIso ? new Date(startIso).getTime() : end - 90 * 86400_000;
  if (end <= start) return null;
  return Math.max(2, Math.min(100, ((now - start) / (end - start)) * 100));
}

export const VenueCard = React.memo(function VenueCard({ venue, onQuickView }: { venue: Venue; onQuickView?: (slug: string) => void }) {
  const now = useMinute();
  const nd = venue.next_deadline;
  const progress = deadlineProgress(venue, now);
  const urgent = nd && new Date(nd.at).getTime() - now < 7 * 86400_000;
  const location = [venue.city, venue.country].filter(Boolean).join(", ");
  return (
    <article className="group relative flex flex-col rounded-xl border bg-card p-4 shadow-card transition-[box-shadow,transform,border-color] duration-200 [contain-intrinsic-size:auto_300px] [content-visibility:auto] hover:-translate-y-0.5 hover:border-foreground/15 hover:shadow-lift">
      <div className="flex items-start gap-3">
        <VenueMark acronym={venue.acronym} />
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-1.5 text-[15px] font-semibold leading-6 tracking-tight">
            <Link
              to={`/venue/${venue.slug}/`}
              className="truncate after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-ring"
            >
              {venue.acronym}
              {venue.next_cycle && !venue.is_rolling ? <span className="font-normal text-muted-foreground"> {venue.next_cycle.year}</span> : null}
            </Link>
          </h3>
          <p className="line-clamp-1 text-[13px] text-muted-foreground" title={venue.name}>
            {venue.name}
          </p>
        </div>
        <div className="relative z-10 -mr-1.5 -mt-1 flex items-center">
          {onQuickView && (
            <Tooltip content="Quick view">
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100 max-md:hidden"
                aria-label={`Quick view of ${venue.acronym}`}
                onClick={(e) => {
                  e.preventDefault();
                  onQuickView(venue.slug);
                }}
              >
                <Eye aria-hidden="true" />
              </Button>
            </Tooltip>
          )}
          <CompareToggle slug={venue.slug} acronym={venue.acronym} />
          <StarButton slug={venue.slug} acronym={venue.acronym} starred={venue.starred} />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <RankBadge label={venue.rank_label} core={venue.core_rank} quartile={venue.quartile} ccf={venue.ccf_rank} />
        <StatusBadge status={venue.status} />
        {venue.next_cycle && !venue.is_rolling && venue.status !== "past" && <ProjectedBadge projected={venue.next_cycle.is_projected} />}
      </div>

      <div
        className={cn("mt-4 rounded-lg border bg-surface px-3 py-2.5", urgent && "border-rose-200 bg-rose-50/60 dark:border-rose-500/20 dark:bg-rose-500/5")}
      >
        {nd ? (
          <>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs font-medium text-muted-foreground">{nd.kind} deadline</span>
              <CountdownText at={nd.at} className="text-sm" />
            </div>
            <DeadlineTime at={nd.at} className="mt-0.5 block text-xs" />
            {progress !== null && (
              <Progress
                value={progress}
                className="mt-2 h-1"
                label={`${Math.round(progress)}% of the submission window elapsed`}
                indicatorClassName={urgent ? "bg-rose-500" : undefined}
              />
            )}
          </>
        ) : venue.is_rolling ? (
          <p className="text-sm">
            <span className="font-medium">Rolling submissions</span>
            <span className="block text-xs text-muted-foreground">Submit any time{venue.impact_factor ? ` · IF ${venue.impact_factor.toFixed(1)}` : ""}</span>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">Next call not announced yet</p>
        )}
      </div>

      {venue.subfields.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1" aria-label="Topics">
          {venue.subfields.slice(0, 3).map((t) => (
            <li key={t.slug} className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
              {t.name}
            </li>
          ))}
          {venue.subfields.length > 3 && <li className="px-1 py-0.5 text-[11px] text-muted-foreground">+{venue.subfields.length - 3}</li>}
        </ul>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-3 text-xs text-muted-foreground [&:not(:first-child)]:mt-4">
        <span className="flex min-w-0 items-center gap-1">
          {venue.flag ? <span aria-hidden="true">{venue.flag}</span> : <MapPin className="size-3" aria-hidden="true" />}
          <span className="truncate">{location || venue.attendance_mode}</span>
        </span>
        {venue.h5_index != null && <span className="tnum">h5 {venue.h5_index}</span>}
        {venue.acceptance_rate != null && <span className="tnum">{venue.acceptance_rate.toFixed(0)}% accepted</span>}
        {!!venue.trackers && (
          <span className="tnum ml-auto flex items-center gap-1" title={`${venue.trackers} researchers track this venue`}>
            <Users className="size-3" aria-hidden="true" />
            {venue.trackers}
          </span>
        )}
      </div>
    </article>
  );
});

export function VenueCardSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-card" aria-hidden="true">
      <div className="flex gap-3">
        <div className="size-10 animate-pulse rounded-lg bg-muted" />
        <div className="flex-1 space-y-2 pt-0.5">
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
          <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
        </div>
      </div>
      <div className="mt-4 flex gap-1.5">
        <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
        <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
      </div>
      <div className="mt-4 h-[68px] animate-pulse rounded-lg bg-muted" />
      <div className="mt-4 h-3 w-2/3 animate-pulse rounded bg-muted" />
    </div>
  );
}
