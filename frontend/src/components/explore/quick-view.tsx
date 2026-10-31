import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectedBadge, RankBadge, StatusBadge, TypeBadge } from "@/components/venue/badges";
import { CompareToggle } from "@/components/venue/compare-toggle";
import { CountdownBlocks, DeadlineTime } from "@/components/venue/countdown";
import { StarButton } from "@/components/venue/star-button";
import { VenueMark } from "@/components/venue/venue-mark";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatAoE } from "@/lib/time";
import type { VenueDetail } from "@/lib/types";

export function QuickView({ slug, onClose }: { slug: string | null; onClose: () => void }) {
  const { data: v, isLoading } = useQuery({
    queryKey: keys.venue(slug ?? ""),
    queryFn: () => api.get<VenueDetail>(`/venues/${slug}/`),
    enabled: !!slug,
  });
  return (
    <Dialog open={!!slug} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl gap-0 p-0">
        {isLoading || !v ? (
          <div className="space-y-4 p-6" aria-busy="true">
            <DialogTitle className="sr-only">Loading venue</DialogTitle>
            <DialogDescription className="sr-only">Loading venue details</DialogDescription>
            <Skeleton className="h-12 w-2/3" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : (
          <>
            <div className="flex items-start gap-4 border-b p-6 pr-14">
              <VenueMark acronym={v.acronym} size="lg" />
              <div className="min-w-0">
                <DialogTitle className="text-xl">
                  {v.acronym} {v.next_cycle && !v.is_rolling ? <span className="font-normal text-muted-foreground">{v.next_cycle.year}</span> : null}
                </DialogTitle>
                <DialogDescription className="mt-0.5">{v.name}</DialogDescription>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  <TypeBadge type={v.venue_type} />
                  <RankBadge label={v.rank_label} core={v.core_rank} quartile={v.quartile} ccf={v.ccf_rank} />
                  <StatusBadge status={v.status} />
                  {v.next_cycle && !v.is_rolling && <ProjectedBadge projected={v.next_cycle.is_projected} />}
                </div>
              </div>
            </div>
            <div className="grid gap-6 p-6 sm:grid-cols-[1.2fr_1fr]">
              <div>
                {v.next_deadline ? (
                  <>
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{v.next_deadline.kind} deadline</p>
                    <CountdownBlocks at={v.next_deadline.at} className="mt-2" />
                    <p className="mt-3 text-sm">
                      <DeadlineTime at={v.next_deadline.at} />
                    </p>
                    <p className="text-xs text-muted-foreground">{formatAoE(v.next_deadline.at)}</p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {v.is_rolling ? "Rolling submissions — submit any time." : "The next call has not been announced yet."}
                  </p>
                )}
                <p className="mt-4 line-clamp-4 text-sm leading-6 text-muted-foreground">{v.description}</p>
              </div>
              <dl className="grid grid-cols-2 content-start gap-x-4 gap-y-3 text-sm">
                {[
                  ["h5-index", v.h5_index],
                  ["Impact factor", v.impact_factor?.toFixed(1)],
                  ["Acceptance", v.acceptance_rate != null ? `${v.acceptance_rate.toFixed(1)}%` : null],
                  ["Review", v.review_process],
                  ["Page limit", v.page_limit],
                  ["Location", [v.flag, v.city, v.country].filter(Boolean).join(" ")],
                ].map(([label, value]) => (
                  <div key={label as string}>
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="tnum font-medium">{value || "—"}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="flex flex-wrap items-center gap-2 border-t bg-surface px-6 py-4">
              <StarButton slug={v.slug} acronym={v.acronym} starred={v.me.starred} variant="full" />
              <CompareToggle slug={v.slug} acronym={v.acronym} variant="full" />
              {v.official_website && (
                <Button variant="ghost" asChild>
                  <a href={v.official_website} target="_blank" rel="noopener noreferrer">
                    Website <ExternalLink aria-hidden="true" />
                  </a>
                </Button>
              )}
              <Button asChild className="ml-auto">
                <Link to={`/venue/${v.slug}/`} onClick={onClose}>
                  Full details <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
