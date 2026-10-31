import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Radar, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatDate, relativeTime } from "@/lib/time";
import type { DeadlineChange } from "@/lib/types";

export function Component() {
  useDocumentTitle("Deadline radar");
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.radar, queryFn: () => api.get<{ results: DeadlineChange[] }>("/radar/") });
  return (
    <PageContainer size="default">
      <PageHeader
        icon={Radar}
        title="Deadline radar"
        description="Every extension, shift and correction to a venue’s dates, as soon as an editor confirms it. Star a venue to get these as notifications."
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <EmptyState icon={Radar} title="No changes yet" description="When a deadline is extended or corrected it appears here, with the old and new dates." />
      ) : (
        <ul className="divide-y rounded-xl border bg-card shadow-card">
          {data.results.map((c) => {
            const later = (c.delta_days ?? 0) > 0;
            const earlier = (c.delta_days ?? 0) < 0;
            return (
              <li key={c.id} className="flex flex-wrap items-center gap-4 p-4">
                <VenueMark acronym={c.venue.acronym} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    <Link to={`/venue/${c.venue.slug}/`} className="hover:text-brand-text">
                      {c.cycle}
                    </Link>{" "}
                    <span className="text-muted-foreground">· {c.field_label}</span>
                  </p>
                  <p className="tnum mt-0.5 flex items-center gap-1.5 text-sm text-muted-foreground">
                    <span className="line-through decoration-muted-foreground/50">{formatDate(c.old_value)}</span>
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                    <span className="font-medium text-foreground">{formatDate(c.new_value)}</span>
                  </p>
                </div>
                <Badge tone={later ? "green" : earlier ? "red" : "neutral"}>
                  {later ? <TrendingUp aria-hidden="true" /> : earlier ? <TrendingDown aria-hidden="true" /> : null}
                  {c.delta_days ? `${later ? "Extended " : "Moved "}${Math.abs(c.delta_days)} days${earlier ? " earlier" : ""}` : "Updated"}
                </Badge>
                <span className="w-24 text-right text-xs text-muted-foreground">{relativeTime(c.changed_at)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </PageContainer>
  );
}
