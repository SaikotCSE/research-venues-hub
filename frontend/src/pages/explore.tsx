import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowUpDown, CalendarDays, GanttChart, LayoutGrid, SearchX, SlidersHorizontal, Sparkles, Table2, X } from "lucide-react";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState } from "@/components/common/page";
import { Pagination } from "@/components/common/pagination";
import { CalendarView } from "@/components/explore/calendar-view";
import { ExportMenu } from "@/components/explore/export-menu";
import { FilterPanel } from "@/components/explore/filter-panel";
import { Hero } from "@/components/explore/hero";
import { QuickView } from "@/components/explore/quick-view";
import { SaveSearchDialog } from "@/components/explore/save-search-dialog";
import { TimelineView } from "@/components/explore/timeline-view";
import { VenueTable } from "@/components/explore/venue-table";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { VenueCard, VenueCardSkeleton } from "@/components/venue/venue-card";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { activeFilterCount, clearFilters, currentView, exportQuery, removeChip, type View } from "@/lib/filters";
import { exploreKey } from "@/lib/query";
import type { CalendarData, Chip, Paged, TimelineData, VenueCard as Venue } from "@/lib/types";
import { cn, pluralize } from "@/lib/utils";

const VIEWS: { value: View; label: string; icon: typeof LayoutGrid }[] = [
  { value: "grid", label: "Cards", icon: LayoutGrid },
  { value: "table", label: "Table", icon: Table2 },
  { value: "timeline", label: "Timeline", icon: GanttChart },
  { value: "calendar", label: "Calendar", icon: CalendarDays },
];

const SORTS = [
  { value: "deadline", label: "Next deadline" },
  { value: "rank", label: "Rank" },
  { value: "h5_index", label: "h5-index" },
  { value: "impact_factor", label: "Impact factor" },
  { value: "acceptance_rate", label: "Acceptance rate" },
  { value: "name", label: "Name" },
];

type ExploreData = Paged<Venue> | TimelineData | CalendarData;

function endpoint(view: View) {
  return view === "timeline" ? "/explore/timeline/" : view === "calendar" ? "/explore/calendar/" : "/explore/";
}

export function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  const [quickView, setQuickView] = React.useState<string | null>(null);
  const view = currentView(params);
  const filters = activeFilterCount(params);
  const page = Number(params.get("page") || 1);
  const showHero = filters === 0 && page === 1;
  useDocumentTitle("VenuePulse · Conference & journal deadlines with live countdowns", { raw: true });

  const query = useQuery({
    queryKey: exploreKey(params),
    queryFn: () => api.get<ExploreData>(endpoint(view), params),
    placeholderData: keepPreviousData,
  });

  const update = React.useCallback(
    (next: URLSearchParams, opts?: { replace?: boolean }) => setParams(next, { replace: opts?.replace, preventScrollReset: true }),
    [setParams],
  );
  const setView = (v: string) => {
    if (!v) return;
    const next = new URLSearchParams(params);
    if (v === "grid") next.delete("view");
    else next.set("view", v);
    next.delete("page");
    update(next);
  };
  const setSort = (sort: string, dir?: "asc" | "desc") => {
    const next = new URLSearchParams(params);
    next.set("sort", sort);
    if (dir) next.set("dir", dir);
    else next.delete("dir");
    next.delete("page");
    update(next);
  };
  const goPage = (p: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(p));
    update(next);
    document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const data = query.data;
  const chips: Chip[] = data?.chips ?? [];
  const total = data?.total ?? 0;
  const stale = query.isPlaceholderData;

  return (
    <>
      {showHero && <Hero />}
      <div id="results" className="mx-auto max-w-screen-2xl scroll-mt-16 px-4 py-8 sm:px-6 lg:px-8">
        <div className="lg:grid lg:grid-cols-[17rem_1fr] lg:gap-8 xl:grid-cols-[18rem_1fr]">
          <aside className="hidden lg:block" aria-label="Filters">
            <div className="scrollbar-thin sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pb-6 pr-1">
              <FilterPanel params={params} onChange={update} />
            </div>
          </aside>

          <section aria-labelledby="results-heading" className="min-w-0">
            {!showHero && (
              <h1 id="results-heading" className="mb-1 text-2xl font-semibold tracking-tight">
                {params.get("q") ? `Results for “${params.get("q")}”` : "Explore venues"}
              </h1>
            )}
            {showHero && (
              <h2 id="results-heading" className="sr-only">
                All venues
              </h2>
            )}

            <div className="mb-4 flex flex-wrap items-center gap-2">
              <p className="mr-auto text-sm text-muted-foreground" role="status" aria-live="polite">
                {data ? (
                  <>
                    <span className="tnum font-semibold text-foreground">{pluralize(total, "venue")}</span>
                    {"num_pages" in data && "page_size" in data && data.num_pages > 1 && (
                      <span>
                        {" "}
                        · page {data.page} of {data.num_pages}
                      </span>
                    )}
                    {view === "timeline" && "row_count" in data && <span> · {data.row_count} with dated cycles</span>}
                  </>
                ) : (
                  "Loading venues…"
                )}
              </p>
              <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setFiltersOpen(true)}>
                <SlidersHorizontal aria-hidden="true" />
                Filters
                {filters > 0 && <span className="tnum rounded-full bg-primary px-1.5 text-[10px] font-bold leading-4 text-primary-foreground">{filters}</span>}
              </Button>
              {(view === "grid" || view === "table") && (
                <Select value={params.get("sort") || "deadline"} onValueChange={(v) => setSort(v)}>
                  <SelectTrigger className="h-8 w-auto gap-1.5 text-[13px]" aria-label="Sort by">
                    <ArrowUpDown className="size-3.5 text-muted-foreground" aria-hidden="true" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end">
                    {SORTS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <ToggleGroup type="single" value={view} onValueChange={setView} aria-label="View">
                {VIEWS.map((v) => (
                  <ToggleGroupItem key={v.value} value={v.value} aria-label={`${v.label} view`} title={`${v.label} view`}>
                    <v.icon aria-hidden="true" />
                    <span className="max-xl:hidden">{v.label}</span>
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
              <ExportMenu query={exportQuery(params)} />
              <SaveSearchDialog query={exportQuery(params)} chips={chips} />
            </div>

            {chips.length > 0 && (
              <div className="mb-5 flex flex-wrap items-center gap-1.5" aria-label="Active filters">
                {chips.map((c) => (
                  <button
                    key={`${c.name}-${c.value}`}
                    type="button"
                    onClick={() => update(removeChip(params, c.name, c.value))}
                    className="group inline-flex items-center gap-1 rounded-full border bg-card py-0.5 pl-2.5 pr-1.5 text-xs font-medium shadow-sm transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 dark:hover:border-rose-500/40 dark:hover:bg-rose-500/10 dark:hover:text-rose-300"
                    aria-label={`Remove filter: ${c.label}`}
                  >
                    {c.label}
                    <X className="size-3 opacity-60 group-hover:opacity-100" aria-hidden="true" />
                  </button>
                ))}
                <Button variant="link" size="xs" className="ml-1 h-auto text-xs" onClick={() => update(clearFilters(params))}>
                  Clear all
                </Button>
              </div>
            )}

            <div className={cn("transition-opacity duration-200", stale && "pointer-events-none opacity-60")} aria-busy={query.isFetching}>
              {query.isError && !data ? (
                <ErrorState error={query.error} onRetry={() => query.refetch()} />
              ) : !data ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <VenueCardSkeleton key={i} />
                  ))}
                </div>
              ) : total === 0 ? (
                <EmptyState
                  icon={SearchX}
                  title="No venues match these filters"
                  description="Try removing a filter, widening the deadline window, or searching for a broader topic."
                >
                  <Button onClick={() => update(clearFilters(params))}>Reset filters</Button>
                  <Button variant="secondary" asChild>
                    <Link to="/recommend/">
                      <Sparkles aria-hidden="true" /> Try the recommender
                    </Link>
                  </Button>
                </EmptyState>
              ) : view === "timeline" && "rows" in data ? (
                <>
                  <TimelineView data={data} />
                  <Pagination page={data.page} numPages={data.num_pages} onPage={goPage} />
                </>
              ) : view === "calendar" && "months" in data ? (
                <CalendarView data={data} />
              ) : "results" in data ? (
                <>
                  {view === "table" ? (
                    <VenueTable venues={data.results} sort={params.get("sort") || "deadline"} dir={params.get("dir") || ""} onSort={setSort} />
                  ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                      {data.results.map((v) => (
                        <VenueCard key={v.slug} venue={v} onQuickView={setQuickView} />
                      ))}
                    </div>
                  )}
                  <Pagination page={data.page} numPages={data.num_pages} onPage={goPage} />
                </>
              ) : null}
            </div>
          </section>
        </div>
      </div>

      <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
        <SheetContent side="left" className="gap-0 overflow-y-auto p-0">
          <SheetHeader>
            <SheetTitle>Filters</SheetTitle>
            <SheetDescription>{data ? `${pluralize(total, "venue")} match` : "Narrow down the catalogue"}</SheetDescription>
          </SheetHeader>
          <div className="p-4">
            <FilterPanel params={params} onChange={update} />
          </div>
          <div className="sticky bottom-0 mt-auto border-t bg-popover p-4">
            <Button className="w-full" onClick={() => setFiltersOpen(false)}>
              Show {data ? pluralize(total, "venue") : "results"}
            </Button>
          </div>
        </SheetContent>
      </Sheet>
      <QuickView slug={quickView} onClose={() => setQuickView(null)} />
    </>
  );
}

export const Component = ExplorePage;
