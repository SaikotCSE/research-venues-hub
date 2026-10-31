import { useQuery } from "@tanstack/react-query";
import { CalendarRange, Clock, Globe2, Lightbulb, ListOrdered } from "lucide-react";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { useFacets } from "@/components/explore/filter-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectedBadge } from "@/components/venue/badges";
import { DeadlineTime } from "@/components/venue/countdown";
import { StarButton } from "@/components/venue/star-button";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Cycle, Tag, VenueRef } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PlanRow {
  venue: VenueRef & { rank_label: string; primary_domain: string; subfields: Tag[]; starred: boolean };
  cycle: Cycle;
  slack_days: number;
}

const TIPS = [
  { icon: Clock, title: "Pick a realistic date", text: "Add a week of buffer for internal review, proofreading and the inevitable last-minute experiment." },
  {
    icon: Globe2,
    title: "Mind the time zone",
    text: "Most CS conferences close at 23:59 Anywhere on Earth (UTC−12) — already the next day in Europe and Asia.",
  },
  { icon: ListOrdered, title: "Abstracts come first", text: "Many venues require an abstract registration about a week before the paper deadline." },
];

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

export function Component() {
  useDocumentTitle("Deadline planner");
  const [params, setParams] = useSearchParams();
  const { data: facets } = useFacets();
  const ready = params.get("ready") ?? "";
  const [draft, setDraft] = React.useState(ready || isoDate(new Date(Date.now() + 30 * 86400_000)));
  const { data, error, isFetching, refetch } = useQuery({
    queryKey: keys.plan(params.toString()),
    queryFn: () => api.get<{ rows: PlanRow[]; ready: string | null }>("/plan/", params),
    enabled: !!ready,
  });
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (!value || value === "any") next.delete(key);
    else next.set(key, value);
    setParams(next);
  };
  const quick = [
    ["In 2 weeks", 14],
    ["In 1 month", 30],
    ["In 2 months", 60],
    ["In 3 months", 90],
  ] as const;

  return (
    <PageContainer size="default">
      <PageHeader
        icon={CalendarRange}
        title="Deadline planner"
        description="When will your paper be ready? See every venue you can still make, soonest first, with the slack you’ll have."
      />
      <Card className="mb-8">
        <CardContent className="p-5">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              set("ready", draft);
            }}
          >
            <div className="grid gap-1.5">
              <Label htmlFor="plan-ready">Paper ready on</Label>
              <Input id="plan-ready" type="date" value={draft} min={isoDate(new Date())} onChange={(e) => setDraft(e.target.value)} className="w-44" required />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="plan-domain">Domain</Label>
              <Select value={params.get("domain") ?? "any"} onValueChange={(v) => set("domain", v)}>
                <SelectTrigger id="plan-domain" className="w-52">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any domain</SelectItem>
                  {facets?.domains.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="plan-type">Type</Label>
              <Select value={params.get("type") ?? "any"} onValueChange={(v) => set("type", v)}>
                <SelectTrigger id="plan-type" className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any type</SelectItem>
                  {facets?.types.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" loading={isFetching}>
              Show venues
            </Button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
            {quick.map(([label, days]) => {
              const value = isoDate(new Date(Date.now() + days * 86400_000));
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => {
                    setDraft(value);
                    set("ready", value);
                  }}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    ready === value ? "border-primary/40 bg-brand-soft text-brand-text" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {!ready ? (
        <div className="grid gap-4 md:grid-cols-3">
          {TIPS.map((t) => (
            <Card key={t.title}>
              <CardContent className="p-5">
                <t.icon className="size-5 text-brand-text" aria-hidden="true" />
                <h2 className="mt-3 font-semibold">{t.title}</h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{t.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : data.rows.length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="No deadlines in that window"
          description="Nothing closes within nine months of that date for these filters. Try an earlier date or widen the filters."
        />
      ) : (
        <ol className="relative space-y-3 border-l border-dashed pl-6" aria-label="Venues you can still make">
          {data.rows.map((r) => (
            <li key={r.cycle.id} className="relative">
              <span className="absolute -left-[31px] top-5 size-2.5 rounded-full bg-primary ring-4 ring-background" aria-hidden="true" />
              <div className="flex flex-wrap items-center gap-4 rounded-xl border bg-card p-4 shadow-card">
                <VenueMark acronym={r.venue.acronym} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/venue/${r.venue.slug}/`} className="font-semibold hover:text-brand-text">
                      {r.cycle.label}
                    </Link>
                    <Badge tone="outline">{r.venue.rank_label}</Badge>
                    <ProjectedBadge projected={r.cycle.is_projected} />
                  </div>
                  <p className="truncate text-sm text-muted-foreground">{r.venue.name}</p>
                </div>
                <div className="text-right text-sm">
                  <DeadlineTime at={r.cycle.submission_deadline} showZone={false} className="font-medium" />
                  <p
                    className={cn(
                      "tnum text-xs font-semibold",
                      r.slack_days < 7 ? "text-orange-700 dark:text-orange-400" : "text-emerald-700 dark:text-emerald-400",
                    )}
                  >
                    {r.slack_days === 0 ? "Due the day it’s ready" : `${r.slack_days} days of slack`}
                  </p>
                </div>
                <StarButton slug={r.venue.slug} acronym={r.venue.acronym} starred={r.venue.starred} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </PageContainer>
  );
}
