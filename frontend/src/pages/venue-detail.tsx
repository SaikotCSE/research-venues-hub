import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BookOpenCheck,
  CalendarPlus,
  ChevronDown,
  ChevronRight,
  Code2,
  FileCode2,
  Globe,
  History,
  KanbanSquare,
  Link2,
  ListChecks,
  MapPin,
  Send,
  Users,
} from "lucide-react";
import * as React from "react";
import { Link, useParams } from "react-router-dom";

import { CodeBlock } from "@/components/common/code-block";
import { CopyButton } from "@/components/common/copy-button";
import { ErrorState } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProjectedBadge, RankBadge, StatusBadge, TypeBadge } from "@/components/venue/badges";
import { CompareToggle } from "@/components/venue/compare-toggle";
import { CountdownBlocks, DeadlineTime } from "@/components/venue/countdown";
import { CyclesTable } from "@/components/venue/cycles-table";
import { ListsCard } from "@/components/venue/lists-card";
import { Milestones } from "@/components/venue/milestones";
import { NotesCard } from "@/components/venue/notes-card";
import { ReviewsSection } from "@/components/venue/reviews-section";
import { StarButton } from "@/components/venue/star-button";
import { SuggestDialog } from "@/components/venue/suggest-dialog";
import { VenueCard, deadlineProgress } from "@/components/venue/venue-card";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { useMinute } from "@/hooks/use-now";
import { ApiError, api } from "@/lib/api";
import { keys } from "@/lib/query";
import { rememberVenue } from "@/lib/recent";
import { formatAoE, formatDate, formatDateRange, relativeTime } from "@/lib/time";
import type { Cycle, VenueDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { NotFoundPage } from "@/pages/not-found";
import { useSession } from "@/providers/session";

function Metric({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border bg-surface px-3 py-2.5">
      <dt className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground" title={hint}>
        {label}
      </dt>
      <dd className="tnum mt-0.5 text-lg font-semibold tracking-tight">{value ?? <span className="text-muted-foreground">—</span>}</dd>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-8 sm:px-6 lg:px-8" aria-busy="true">
      <Skeleton className="h-4 w-40" />
      <div className="mt-6 flex gap-4">
        <Skeleton className="size-16 rounded-2xl" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96 max-w-full" />
        </div>
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-64 lg:col-span-2" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export function VenueDetailPage() {
  const { slug = "" } = useParams();
  const session = useSession();
  const now = useMinute();
  const [suggestFor, setSuggestFor] = React.useState<Cycle | null>(null);
  const { data: v, error, isLoading, refetch } = useQuery({ queryKey: keys.venue(slug), queryFn: () => api.get<VenueDetail>(`/venues/${slug}/`) });

  useDocumentTitle(v ? `${v.acronym}${v.next_cycle ? ` ${v.next_cycle.year}` : ""} deadlines, rank & submission guide` : null);
  React.useEffect(() => {
    if (v) rememberVenue({ slug: v.slug, acronym: v.acronym, name: v.name });
  }, [v]);

  if (isLoading) return <DetailSkeleton />;
  if (error instanceof ApiError && error.status === 404) return <NotFoundPage what="venue" />;
  if (error || !v)
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorState error={error} onRetry={() => refetch()} />
      </div>
    );

  const cycle = v.next_cycle;
  const nd = v.next_deadline;
  const progress = deadlineProgress(v, now);
  const location = [v.city, v.country].filter(Boolean).join(", ");
  const embedCode = `<iframe src="${v.urls.embed}" width="320" height="150" style="border:0;border-radius:12px" title="${v.acronym} deadline countdown" loading="lazy"></iframe>`;

  return (
    <div className="mx-auto max-w-screen-2xl px-4 pb-8 pt-6 sm:px-6 lg:px-8">
      <nav aria-label="Breadcrumb" className="mb-5 text-sm text-muted-foreground">
        <ol className="flex items-center gap-1.5">
          <li>
            <Link to="/" className="hover:text-foreground">
              Explore
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-3.5" />
          </li>
          <li>
            <Link to={`/?type=${encodeURIComponent(v.venue_type)}`} className="hover:text-foreground">
              {v.venue_type === "Journal" ? "Journals" : v.venue_type === "Conference" ? "Conferences" : "Workshops & symposia"}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-3.5" />
          </li>
          <li aria-current="page" className="font-medium text-foreground">
            {v.acronym}
          </li>
        </ol>
      </nav>

      {/* Header */}
      <header className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 gap-4">
          <VenueMark acronym={v.acronym} size="xl" className="max-sm:hidden" />
          <div className="min-w-0">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              {v.acronym}
              {cycle && !v.is_rolling && <span className="font-normal text-muted-foreground"> {cycle.year}</span>}
            </h1>
            <p className="mt-1 text-[15px] text-muted-foreground sm:text-base">{v.name}</p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <TypeBadge type={v.venue_type} />
              <RankBadge label={v.rank_label} core={v.core_rank} quartile={v.quartile} ccf={v.ccf_rank} />
              <StatusBadge status={v.status} />
              {cycle && !v.is_rolling && <ProjectedBadge projected={cycle.is_projected} verifiedAt={cycle.verified_at} />}
              {v.is_open_access && <Badge tone="violet">Open access</Badge>}
              <span className="ml-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="size-3.5" aria-hidden="true" />
                {v.tracking_count} tracking
              </span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StarButton slug={v.slug} acronym={v.acronym} starred={v.me.starred} variant="full" />
          <CompareToggle slug={v.slug} acronym={v.acronym} variant="full" />
          {(v.calendar_links.google || v.urls.ics) && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary">
                  <CalendarPlus aria-hidden="true" /> Add to calendar <ChevronDown className="opacity-60" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {v.calendar_links.google && (
                  <DropdownMenuItem asChild>
                    <a href={v.calendar_links.google} target="_blank" rel="noopener noreferrer">
                      Google Calendar
                    </a>
                  </DropdownMenuItem>
                )}
                {v.calendar_links.outlook && (
                  <DropdownMenuItem asChild>
                    <a href={v.calendar_links.outlook} target="_blank" rel="noopener noreferrer">
                      Outlook.com
                    </a>
                  </DropdownMenuItem>
                )}
                {v.urls.ics && (
                  <DropdownMenuItem asChild>
                    <a href={v.urls.ics} download>
                      Download .ics (all milestones)
                    </a>
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {v.submission_portal_url && (
            <Button asChild>
              <a href={v.submission_portal_url} target="_blank" rel="noopener noreferrer">
                <Send aria-hidden="true" /> Submit
              </a>
            </Button>
          )}
        </div>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_22rem] xl:grid-cols-[1fr_24rem]">
        <div className="min-w-0 space-y-6">
          {/* Countdown */}
          <Card className="overflow-hidden">
            <div className="relative bg-gradient-to-br from-brand-soft via-card to-card p-5 sm:p-6">
              {nd ? (
                <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                  <div>
                    <p className="eyebrow">
                      {nd.kind} deadline{cycle?.is_projected ? " · projected" : ""}
                    </p>
                    <CountdownBlocks at={nd.at} className="mt-3" />
                  </div>
                  <div className="text-sm md:text-right">
                    <DeadlineTime at={nd.at} className="font-medium" />
                    <p className="tnum text-muted-foreground">{formatAoE(nd.at)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Stored as an exact instant: {cycle?.timezone === "AoE" ? "23:59 Anywhere on Earth" : "UTC"}.
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="eyebrow">{v.is_rolling ? "Rolling submissions" : "No upcoming deadline"}</p>
                  <p className="mt-2 text-lg font-medium">
                    {v.is_rolling ? "Submit any time — decisions follow the journal’s review cycle." : "The next call for papers has not been announced yet."}
                  </p>
                  {!v.is_rolling && <p className="mt-1 text-sm text-muted-foreground">Star this venue to be notified when new dates are added.</p>}
                </div>
              )}
              {progress !== null && (
                <div className="mt-5">
                  <div className="mb-1.5 flex justify-between text-[11px] text-muted-foreground">
                    <span>{cycle?.submission_open_date ? `Call opened ${formatDate(cycle.submission_open_date)}` : "Submission window"}</span>
                    <span className="tnum">{Math.round(progress)}% elapsed</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-background/80">
                    <div
                      className={cn("h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500", progress > 85 && "from-orange-500 to-rose-500")}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            {v.steps.length > 0 && (
              <div className="border-t px-5 py-5 sm:px-6">
                <Milestones steps={v.steps} label={cycle?.label ?? v.acronym} />
              </div>
            )}
          </Card>

          {/* About */}
          <Card className="[contain-intrinsic-size:auto_320px] [content-visibility:auto]">
            <CardHeader>
              <CardTitle>About {v.acronym}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-[15px] leading-7 text-foreground/90">{v.description}</p>
              {v.scope && (
                <div>
                  <h3 className="text-sm font-semibold">Scope</h3>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{v.scope}</p>
                </div>
              )}
              {v.subfields.length > 0 && (
                <ul className="flex flex-wrap gap-1.5" aria-label="Topics">
                  {v.subfields.map((t) => (
                    <li key={t.slug}>
                      <Link
                        to={`/?tag=${t.slug}`}
                        className="inline-block rounded-md border bg-surface px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-brand-text"
                      >
                        {t.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Submission guide */}
          <Card className="[contain-intrinsic-size:auto_640px] [content-visibility:auto]">
            <CardHeader>
              <CardTitle>
                <ListChecks className="size-4 text-muted-foreground" aria-hidden="true" /> Submission guide
              </CardTitle>
              <CardDescription>Formatting rules and ready-to-paste snippets for your manuscript.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-6">
              <dl className="divide-y rounded-lg border">
                {v.checklist.map((item) => (
                  <div key={item.label} className="grid grid-cols-[8rem_1fr] gap-3 px-3 py-2.5 text-sm">
                    <dt className="text-muted-foreground">{item.label}</dt>
                    <dd className="min-w-0 break-words font-medium">
                      {item.value.startsWith("http") ? (
                        <a href={item.value} target="_blank" rel="noopener noreferrer" className="link inline-flex items-center gap-1">
                          Official template <ArrowUpRight className="size-3.5" aria-hidden="true" />
                        </a>
                      ) : (
                        item.value
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
              <Tabs defaultValue="latex" className="min-w-0">
                <TabsList>
                  <TabsTrigger value="latex">
                    <FileCode2 aria-hidden="true" /> LaTeX
                  </TabsTrigger>
                  <TabsTrigger value="bibtex">
                    <BookOpenCheck aria-hidden="true" /> BibTeX
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="latex">
                  <CodeBlock code={v.latex} label="LaTeX preamble" />
                </TabsContent>
                <TabsContent value="bibtex">
                  <CodeBlock code={v.bibtex} label="BibTeX entry" />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Cycles */}
          <Card className="[contain-intrinsic-size:auto_320px] [content-visibility:auto]">
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-2">
              <div>
                <CardTitle>
                  <History className="size-4 text-muted-foreground" aria-hidden="true" /> Editions & dates
                </CardTitle>
                <CardDescription>Shown in your timezone. Projected dates are extrapolated from earlier editions.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <CyclesTable cycles={v.cycles} onSuggest={session.authenticated ? setSuggestFor : undefined} />
              {!session.authenticated && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Spotted a wrong date?{" "}
                  <Link to={`/accounts/login/?next=${encodeURIComponent(`/venue/${v.slug}/`)}`} className="link">
                    Log in
                  </Link>{" "}
                  to suggest a correction.
                </p>
              )}
            </CardContent>
          </Card>

          {v.changes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Deadline changes</CardTitle>
                <CardDescription>Extensions and corrections logged for this venue.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  {v.changes.map((ch) => (
                    <li key={ch.id} className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                      <Badge tone={ch.delta_days && ch.delta_days > 0 ? "green" : ch.delta_days && ch.delta_days < 0 ? "red" : "neutral"}>
                        {ch.delta_days ? `${ch.delta_days > 0 ? "+" : ""}${ch.delta_days} days` : "Updated"}
                      </Badge>
                      <span className="font-medium">
                        {ch.cycle} · {ch.field_label}
                      </span>
                      <span className="tnum text-muted-foreground">
                        {formatDate(ch.old_value)} → {formatDate(ch.new_value)}
                      </span>
                      <span className="ml-auto text-xs text-muted-foreground">{relativeTime(ch.changed_at)}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <ReviewsSection venue={v} />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6" aria-label="Venue facts">
          <Card>
            <CardHeader>
              <CardTitle as="h2">Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-2">
                {v.venue_type === "Journal" ? (
                  <>
                    <Metric label="Impact factor" value={v.impact_factor?.toFixed(2)} hint="Journal Citation Reports" />
                    <Metric label="Quartile" value={v.quartile || null} />
                    <Metric label="CiteScore" value={v.citescore?.toFixed(1)} />
                    <Metric label="SJR" value={v.sjr?.toFixed(3)} />
                  </>
                ) : (
                  <>
                    <Metric label="CORE" value={v.core_rank !== "Unranked" ? v.core_rank : null} />
                    <Metric label="CCF" value={v.ccf_rank !== "Unranked" ? v.ccf_rank : null} />
                  </>
                )}
                <Metric label="h5-index" value={v.h5_index} hint="Google Scholar Metrics" />
                <Metric label="h5-median" value={v.h5_median} />
                <Metric label="Acceptance" value={v.acceptance_rate != null ? `${v.acceptance_rate.toFixed(1)}%` : null} />
                <Metric
                  label="APC"
                  value={v.apc_cost_usd ? `$${v.apc_cost_usd.toLocaleString()}` : v.is_open_access ? "None" : null}
                  hint="Article processing charge"
                />
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle as="h2">Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                {[
                  { label: "Location", value: location ? `${v.flag} ${location}` : null, icon: MapPin },
                  { label: "Format", value: v.attendance_mode },
                  { label: "Domain", value: v.primary_domain },
                  { label: "Publisher", value: v.publisher },
                  { label: "Peer review", value: v.review_process },
                  { label: "Page limit", value: v.page_limit },
                  { label: "ISSN", value: v.issn },
                  {
                    label: "Next event",
                    value: cycle?.event_start_date ? formatDateRange(cycle.event_start_date, cycle.event_end_date) : null,
                  },
                ]
                  .filter((r) => r.value)
                  .map((r) => (
                    <div key={r.label} className="flex justify-between gap-4">
                      <dt className="text-muted-foreground">{r.label}</dt>
                      <dd className="text-right font-medium">{r.value}</dd>
                    </div>
                  ))}
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                {v.official_website && (
                  <Button variant="secondary" size="sm" asChild>
                    <a href={v.official_website} target="_blank" rel="noopener noreferrer">
                      <Globe aria-hidden="true" /> Official website
                    </a>
                  </Button>
                )}
                <CopyButton text={v.urls.page} label="Copy link" size="sm" successMessage="Link copied" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-primary/20 bg-gradient-to-br from-brand-soft/70 to-card">
            <CardContent className="flex items-start gap-3 p-5">
              <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm">
                <KanbanSquare className="size-4" aria-hidden="true" />
              </span>
              <div>
                <p className="font-semibold">Submitting to {v.acronym}?</p>
                <p className="mt-0.5 text-sm text-muted-foreground">Track the paper with a checklist generated from this venue’s rules.</p>
                <Button size="sm" className="mt-3" asChild>
                  <Link
                    to={
                      session.authenticated ? `/tracker/new/?venue=${v.slug}` : `/accounts/signup/?next=${encodeURIComponent(`/tracker/new/?venue=${v.slug}`)}`
                    }
                  >
                    Track a submission
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          <NotesCard key={v.slug} slug={v.slug} initial={v.me.note} />
          {session.authenticated && v.me.lists && <ListsCard venue={v} />}

          <Card>
            <CardHeader>
              <CardTitle as="h2">
                <Code2 className="size-4 text-muted-foreground" aria-hidden="true" /> Embed & API
              </CardTitle>
              <CardDescription>Show a live countdown on your lab website.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <CodeBlock code={embedCode} label="HTML" wrap />
              <div className="flex flex-wrap gap-2 text-xs">
                <a href={v.urls.embed} target="_blank" rel="noopener noreferrer" className="link inline-flex items-center gap-1">
                  <Link2 className="size-3" aria-hidden="true" /> Preview widget
                </a>
                <a href={v.urls.api} className="link inline-flex items-center gap-1">
                  <Code2 className="size-3" aria-hidden="true" /> JSON
                </a>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      {v.related.length > 0 && (
        <section className="mt-12 [contain-intrinsic-size:auto_640px] [content-visibility:auto]" aria-labelledby="related-h">
          <h2 id="related-h" className="mb-4 text-lg font-semibold tracking-tight">
            Similar venues
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {v.related.map((r) => (
              <VenueCard key={r.slug} venue={r} />
            ))}
          </div>
        </section>
      )}

      <SuggestDialog cycle={suggestFor} onClose={() => setSuggestFor(null)} />
    </div>
  );
}

export const Component = VenueDetailPage;
