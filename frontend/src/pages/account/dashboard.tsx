import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Bell, Check, Clock, KanbanSquare, List, Plus, Search, Sparkles, Star, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip } from "@/components/ui/tooltip";
import { ProjectedBadge } from "@/components/venue/badges";
import { CountdownText, DeadlineTime } from "@/components/venue/countdown";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import { relativeTime } from "@/lib/time";
import type { Cycle, Notification, Recommendation, SavedSearch, Submission, VenueListSummary, VenueRef } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Dashboard {
  name: string;
  target_count: number;
  unread_count: number;
  upcoming: { venue: VenueRef & { rank_label: string }; cycle: Cycle }[];
  submissions: Submission[];
  status_counts: Record<string, number>;
  notifications: Notification[];
  lists: VenueListSummary[];
  saved_searches: SavedSearch[];
  recommendations: Recommendation[];
  onboarding: { label: string; done: boolean; url: string }[];
}

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export function Component() {
  useDocumentTitle("Dashboard");
  const qc = useQueryClient();
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.dashboard, queryFn: () => api.get<Dashboard>("/me/dashboard/") });
  const removeSearch = useMutation({
    mutationFn: (id: number) => api.delete(`/me/searches/${id}/`),
    onSuccess: () => {
      toast.success("Saved search deleted");
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (error)
    return (
      <PageContainer>
        <ErrorState error={error} onRetry={() => refetch()} />
      </PageContainer>
    );
  if (isLoading || !data)
    return (
      <PageContainer>
        <Skeleton className="h-10 w-72" />
        <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="mt-6 h-80 rounded-xl" />
      </PageContainer>
    );

  const done = data.onboarding.filter((o) => o.done).length;
  const stats = [
    { label: "Target venues", value: data.target_count, to: "/targets/", icon: Star },
    { label: "Active submissions", value: data.submissions.length, to: "/tracker/", icon: KanbanSquare },
    { label: "Unread notifications", value: data.unread_count, to: "/accounts/notifications/", icon: Bell },
    { label: "Venue lists", value: data.lists.length, to: "/accounts/lists/", icon: List },
  ];

  return (
    <PageContainer>
      <PageHeader
        title={`${greeting()}, ${data.name}`}
        description="Your deadlines, submissions and alerts at a glance."
        actions={
          <>
            <Button variant="secondary" asChild>
              <Link to="/recommend/">
                <Sparkles aria-hidden="true" /> Find venues
              </Link>
            </Button>
            <Button asChild>
              <Link to="/tracker/new/">
                <Plus aria-hidden="true" /> Track submission
              </Link>
            </Button>
          </>
        }
      />

      {done < data.onboarding.length && (
        <Card className="mb-6 overflow-hidden border-primary/20">
          <div className="bg-gradient-to-r from-brand-soft to-card p-5">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1">
                <h2 className="font-semibold">Get the most out of VenuePulse</h2>
                <p className="text-sm text-muted-foreground">
                  {done} of {data.onboarding.length} steps done
                </p>
              </div>
              <Progress value={(done / data.onboarding.length) * 100} className="w-40" label="Setup progress" />
            </div>
            <ol className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {data.onboarding.map((o, i) => (
                <li key={o.label}>
                  <Link
                    to={o.url}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5 text-sm transition-colors hover:border-primary/40",
                      o.done && "border-emerald-200 bg-emerald-50/70 text-emerald-900 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-200",
                    )}
                  >
                    <span
                      className={cn(
                        "grid size-5 shrink-0 place-items-center rounded-full text-[11px] font-bold",
                        o.done ? "bg-emerald-600 text-white" : "bg-muted text-muted-foreground",
                      )}
                      aria-hidden="true"
                    >
                      {o.done ? <Check className="size-3" strokeWidth={3} /> : i + 1}
                    </span>
                    <span className={cn(o.done && "line-through decoration-emerald-600/40")}>{o.label}</span>
                    <span className="sr-only">{o.done ? "(done)" : "(to do)"}</span>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        </Card>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map((s) => (
          <Link
            key={s.label}
            to={s.to}
            className="group rounded-xl border bg-card p-4 shadow-card transition-[box-shadow,border-color] hover:border-foreground/15 hover:shadow-lift"
          >
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-muted-foreground">{s.label}</span>
              <s.icon className="size-4 text-muted-foreground/70 transition-colors group-hover:text-brand-text" aria-hidden="true" />
            </div>
            <span className="mt-1.5 block text-3xl font-semibold tracking-tight">{s.value}</span>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>
              <Clock className="size-4 text-muted-foreground" aria-hidden="true" /> Your next 120 days
            </CardTitle>
            <Button variant="ghost" size="xs" asChild>
              <Link to="/targets/">
                All targets <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {data.upcoming.length ? (
              <ul className="divide-y">
                {data.upcoming.map(({ venue, cycle }) => (
                  <li key={cycle.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
                    <VenueMark acronym={venue.acronym} size="sm" />
                    <div className="min-w-0 flex-1">
                      <Link to={`/venue/${venue.slug}/`} className="font-semibold hover:text-brand-text">
                        {cycle.label}
                      </Link>
                      <DeadlineTime at={cycle.submission_deadline} className="block text-xs text-muted-foreground" />
                    </div>
                    {cycle.is_projected && <ProjectedBadge projected />}
                    <CountdownText at={cycle.submission_deadline} className="text-sm" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Nothing due in the next 120 days.{" "}
                <Link to="/" className="link">
                  Star a few venues
                </Link>{" "}
                to see their deadlines here.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>
              <Bell className="size-4 text-muted-foreground" aria-hidden="true" /> Notifications
            </CardTitle>
            <Button variant="ghost" size="xs" asChild>
              <Link to="/accounts/notifications/">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {data.notifications.length ? (
              <ul className="space-y-3">
                {data.notifications.map((n) => (
                  <li key={n.id}>
                    <Link to={n.url || "/accounts/notifications/"} className="block text-sm hover:text-brand-text">
                      {n.message}
                      <span className="mt-0.5 block text-xs text-muted-foreground">{relativeTime(n.created_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">You’re all caught up.</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>
              <KanbanSquare className="size-4 text-muted-foreground" aria-hidden="true" /> Active submissions
            </CardTitle>
            <Button variant="ghost" size="xs" asChild>
              <Link to="/tracker/">
                Open board <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {data.submissions.length ? (
              <ul className="divide-y">
                {data.submissions.map((s) => (
                  <li key={s.id}>
                    <Link to={`/tracker/s/${s.id}/`} className="flex flex-wrap items-center gap-3 py-3 hover:text-brand-text">
                      <span className="min-w-0 flex-1 truncate font-medium">{s.paper.title}</span>
                      <span className="text-sm text-muted-foreground">→ {s.venue.acronym}</span>
                      <Badge tone="neutral">{s.status_label}</Badge>
                      {s.days_left != null && (
                        <span className={cn("tnum text-xs font-semibold", s.days_left < 7 ? "text-rose-700 dark:text-rose-400" : "text-muted-foreground")}>
                          {s.days_left}d left
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No active submissions.{" "}
                <Link to="/tracker/new/" className="link">
                  Track one
                </Link>{" "}
                to get a venue-specific checklist.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Search className="size-4 text-muted-foreground" aria-hidden="true" /> Saved searches
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.saved_searches.length ? (
              <ul className="divide-y">
                {data.saved_searches.map((s) => (
                  <li key={s.id} className="flex items-center gap-2 py-2 text-sm">
                    <Link to={`/?${s.querystring}`} className="min-w-0 flex-1 truncate font-medium hover:text-brand-text">
                      {s.name}
                    </Link>
                    {s.alert && (
                      <Tooltip content="Alerts on">
                        <Bell className="size-3.5 text-amber-500" aria-label="Alerts on" />
                      </Tooltip>
                    )}
                    <Button variant="ghost" size="icon-sm" onClick={() => removeSearch.mutate(s.id)} aria-label={`Delete saved search ${s.name}`}>
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Save any filter combination from{" "}
                <Link to="/" className="link">
                  Explore
                </Link>{" "}
                and get alerted when new venues match.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              <Sparkles className="size-4 text-muted-foreground" aria-hidden="true" /> Recommended for your interests
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recommendations.length ? (
              <ul className="divide-y">
                {data.recommendations.map((r) => (
                  <li key={r.venue.slug}>
                    <Link to={`/venue/${r.venue.slug}/`} className="flex items-center gap-3 py-2.5 text-sm hover:text-brand-text">
                      <VenueMark acronym={r.venue.acronym} size="sm" />
                      <span className="w-24 font-semibold">{r.venue.acronym}</span>
                      <span className="min-w-0 flex-1 truncate text-muted-foreground">{r.venue.name}</span>
                      <span className="tnum text-xs font-semibold text-brand-text">{r.percent}%</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Add research interests to your{" "}
                <Link to="/accounts/profile/" className="link">
                  profile
                </Link>{" "}
                to get personalised venue suggestions.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
