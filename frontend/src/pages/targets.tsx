import { useQuery } from "@tanstack/react-query";
import { LogIn, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { ExportMenu } from "@/components/explore/export-menu";
import { Button } from "@/components/ui/button";
import { VenueCard, VenueCardSkeleton } from "@/components/venue/venue-card";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueCard as Venue } from "@/lib/types";
import { useSession } from "@/providers/session";

export function Component() {
  useDocumentTitle("My target venues");
  const session = useSession();
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: keys.targets,
    queryFn: () => api.get<{ count: number; results: (Venue & { note: string })[] }>("/targets/"),
  });
  const upcoming = data?.results.filter((v) => v.next_deadline).length ?? 0;
  return (
    <PageContainer>
      <PageHeader
        icon={Star}
        title="My target venues"
        description={
          data?.count ? `${data.count} starred · ${upcoming} with an upcoming deadline, soonest first.` : "Star venues to collect their deadlines here."
        }
        actions={data?.count ? <ExportMenu query="" scope="targets" /> : null}
      />
      {!session.authenticated && !!data?.count && (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-primary/20 bg-brand-soft/60 px-4 py-3 text-sm">
          <LogIn className="size-4 text-brand-text" aria-hidden="true" />
          <p className="flex-1">Your targets are saved in this browser. Create a free account to sync them and get reminders before each deadline.</p>
          <Button size="sm" asChild>
            <Link to="/accounts/signup/?next=/targets/">Create account</Link>
          </Button>
        </div>
      )}
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <VenueCardSkeleton key={i} />
          ))}
        </div>
      ) : !data?.count ? (
        <EmptyState icon={Star} title="No targets yet" description="Tap the star on any venue to keep its deadlines, notes and countdown here.">
          <Button asChild>
            <Link to="/">Explore venues</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/recommend/">Get recommendations</Link>
          </Button>
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.results.map((v) => (
            <div key={v.slug} className="flex flex-col gap-2">
              <VenueCard venue={v} />
              {v.note && (
                <p className="line-clamp-2 rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">Note: </span>
                  {v.note}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
